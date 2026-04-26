# schema version: v7.2
"""Seo 2014 Eq.(1) — Kashcheyevs–Kaestner decay-cascade Gumbel-sum model.

    ⟨n⟩_fit(V) = Σ_{i=1..2} exp[−exp(−a·V_exit − b + c_i)]
                = exp[−Γ₁·exp(−(aV+b))] + exp[−Γ₂·exp(−(aV+b))]

with c_i ≡ ln Γ_i (back-tunneling rate of the i-th electron).

Reference: Seo et al., Phys. Rev. B 90, 085307 (2014), Eq.(1) on page 3.
That equation is itself the closed-form decay-cascade prediction of
Kashcheyevs & Kaestner, PRL 104, 186805 (2010).

Fitting is done in n(V) space; η = log10|n−1| is computed from the fitted
n(V) for overlay plots. The figure-of-merit δ₂ = c₂ − c₁ = ln(Γ₂/Γ₁) is
returned directly — wider δ₂ ↔ wider n=1 plateau ↔ better pump accuracy.

NOT to be confused with `sigmoid_plateau_fit.py` (a phenomenological
sigmoid-product 6-parameter model, formerly mislabeled "Seo 2014 Eq.(1)").
See memory/scientific_references.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np
from scipy.optimize import curve_fit


def decay_cascade_n(V, a, b, c1, c2):
    """Seo 2014 Eq.(1) in (a, b, c_i = ln Γ_i) parameterization.

    The c-form keeps the fit unconstrained (no positivity on Γ) while
    remaining mathematically identical to the published form.
    """
    V = np.asarray(V, dtype=float)
    z = -a * V - b
    arg1 = np.clip(z + c1, -500.0, 50.0)   # exp(arg) safe range; >50 saturates
    arg2 = np.clip(z + c2, -500.0, 50.0)
    return np.exp(-np.exp(arg1)) + np.exp(-np.exp(arg2))


@dataclass
class DecayCascadeFitResult:
    success: bool
    popt: Optional[tuple] = None          # (a, b, c1, c2) with c_i = ln Γ_i
    V_model: Optional[np.ndarray] = None
    n_model: Optional[np.ndarray] = None
    eta_model: Optional[np.ndarray] = None
    V_opt: Optional[float] = None         # V at min |n−1| inside data range
    eta_E_min: Optional[float] = None     # min of η_model (NOT an asymptote)
    delta2: Optional[float] = None        # ln(Γ₂/Γ₁) — Seo 2014 FoM
    rms: Optional[float] = None           # n-domain RMS residual
    n_fit_pts: int = 0
    message: str = ''


def _initial_guess(V, n):
    """Heuristic initial guess for (a, b, c1, c2).

    We expect ⟨n⟩(V) to rise monotonically through the n=1 plateau toward 2.
    Half-rise of term i sits at a·V + b = c_i (because exp(−exp(0)) = 1/e ≈ 0.37,
    but the true 50%-rise of a Gumbel CDF is at z = −ln(ln 2) ≈ 0.367 — close
    enough for an initial guess). Use n=0.5 and n=1.5 crossings as anchors.
    """
    V = np.asarray(V, dtype=float)
    n = np.asarray(n, dtype=float)
    order = np.argsort(V)
    Vs = V[order]; ns = n[order]
    # Crossings (linear interpolation against monotone-ish data).
    def cross(target):
        idx = np.where(ns >= target)[0]
        if idx.size == 0:
            return float(Vs[-1])
        i = idx[0]
        if i == 0:
            return float(Vs[0])
        n0, n1 = ns[i - 1], ns[i]
        if n1 == n0:
            return float(Vs[i])
        f = (target - n0) / (n1 - n0)
        return float(Vs[i - 1] + f * (Vs[i] - Vs[i - 1]))
    V_at_05 = cross(0.5)
    V_at_15 = cross(1.5)
    # If n=1.5 not reached in the data, fall back to using span/2 spacing.
    span = max(Vs[-1] - Vs[0], 1e-6)
    if V_at_15 <= V_at_05:
        V_at_15 = V_at_05 + 0.3 * span
    # a maps a unit change in (aV+b) to one e-fold of the inner exp.
    # Width of one Gumbel rise ~ 1/a in V; pick a so that |V_at_15 − V_at_05|
    # spans ~ 1 e-fold (rough; fitter refines).
    a0 = 1.0 / max(V_at_15 - V_at_05, 1e-6) * 2.0
    # c_i = a·V_50_i + b at half-rise; pick b so first c lands at 0.
    c1 = 0.0
    b0 = -a0 * V_at_05  # so that −a·V_at_05 − b = 0 → first term half-rise here
    c2 = a0 * (V_at_15 - V_at_05)
    return a0, b0, c1, c2


def decay_cascade_fit(V, n,
                      n_max_expected: float = 2.5) -> DecayCascadeFitResult:
    """Fit Seo 2014 Eq.(1) (decay-cascade) to n(V) data.

    Parameters
    ----------
    V, n           : 1D arrays of same length (V in Volts, n dimensionless).
    n_max_expected : sanity cap; data with n > this is dropped before fitting
                     to avoid contamination from outliers / partial cycles.

    Notes
    -----
    Requires data spanning at least the rise from n≈0 through n≈1; if the
    n→2 transition is fully outside the data range, c₂ may be only weakly
    determined (fit still succeeds but δ₂ uncertainty is large — caller
    should treat δ₂ as a lower bound).
    """
    V = np.asarray(V, dtype=float)
    n = np.asarray(n, dtype=float)
    mask = np.isfinite(V) & np.isfinite(n) & (n < n_max_expected) & (n > -0.1)
    N = int(mask.sum())
    if N < 5:
        return DecayCascadeFitResult(False, n_fit_pts=N,
            message=f'insufficient fit pts (N={N}<5)')

    Vf = V[mask]; nf = n[mask]
    a0, b0, c1_0, c2_0 = _initial_guess(Vf, nf)

    V_low, V_high = float(Vf.min()), float(Vf.max())
    V_span = max(V_high - V_low, 1e-6)
    # Bounds: a > 0 (rising). c_i in a generous band centered at initial guess.
    lb = [1e-3,        -1e4,  c1_0 - 20.0,  c2_0 - 20.0]
    ub = [1e4 / V_span, 1e4,  c1_0 + 20.0,  c2_0 + 20.0]
    p0 = [a0, b0, c1_0, c2_0]
    # Clip p0 into bounds in case heuristic produced an out-of-bound seed.
    p0 = [min(max(pi, li + 1e-9), ui - 1e-9) for pi, li, ui in zip(p0, lb, ub)]

    try:
        popt, _ = curve_fit(decay_cascade_n, Vf, nf,
                            p0=p0, bounds=(lb, ub), maxfev=20000)
    except (RuntimeError, ValueError) as e:
        return DecayCascadeFitResult(False, n_fit_pts=N,
            message=f'curve_fit failed: {e}')

    a, b, c1, c2 = popt
    # Order so that c1 ≤ c2 (i.e. Γ₁ ≤ Γ₂ — first electron more bound).
    if c1 > c2:
        c1, c2 = c2, c1
        popt = (a, b, c1, c2)
    delta2 = float(c2 - c1)

    V_model = np.linspace(V_low, V_high, 800)
    n_model = decay_cascade_n(V_model, *popt)
    dev = np.abs(n_model - 1.0)
    dev = np.where(dev > 1e-12, dev, 1e-12)
    eta_model = np.log10(dev)
    i_opt = int(np.argmin(eta_model))
    V_opt = float(V_model[i_opt])
    eta_E_min = float(eta_model[i_opt])
    resid = nf - decay_cascade_n(Vf, *popt)
    rms = float(np.sqrt(np.mean(resid ** 2)))

    msg = ''
    if delta2 < 0.5:
        msg = f'small δ₂={delta2:.2f} — plateau may be poorly resolved'

    return DecayCascadeFitResult(True,
        popt=tuple(float(p) for p in popt),
        V_model=V_model, n_model=n_model, eta_model=eta_model,
        V_opt=V_opt, eta_E_min=eta_E_min, delta2=delta2,
        rms=rms, n_fit_pts=N, message=msg)
