# schema version: v7.0
"""Seo 2014 Eq.(1) — 6-parameter sigmoid-product model for pump n(V).

    n(V) = ns + (no − ns) · σ₁(V) · σ₂(V)
    σ_k(V) = 1 / (1 + exp(−α_k · (V − V_k)))

Reference: Seo et al. (2014). NOT to be confused with Schoinas 2024 Eq.(1)
(MSE formula). See memory/scientific_references.md.

Fitting is done in n(V) space (per bo-gpr-post-plot §6.2); η = log10|n-1|
is computed from the fitted n(V) for overlay plots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np
from scipy.optimize import curve_fit


def seo_model_n(V, alpha1, V1, alpha2, V2, ns, no):
    V = np.asarray(V, dtype=float)
    # Clip exponents to prevent overflow when fitter wanders into large α.
    a1 = np.clip(-alpha1 * (V - V1), -500.0, 500.0)
    a2 = np.clip(-alpha2 * (V - V2), -500.0, 500.0)
    s1 = 1.0 / (1.0 + np.exp(a1))
    s2 = 1.0 / (1.0 + np.exp(a2))
    return ns + (no - ns) * s1 * s2


@dataclass
class SeoFitResult:
    success: bool
    popt: Optional[tuple] = None          # (alpha1, V1, alpha2, V2, ns, no)
    V_model: Optional[np.ndarray] = None
    n_model: Optional[np.ndarray] = None
    eta_model: Optional[np.ndarray] = None
    V_opt: Optional[float] = None
    eta_E_min: Optional[float] = None     # min of η_model (not an asymptote)
    rms: Optional[float] = None           # in n-domain
    n_fit_pts: int = 0
    message: str = ''


def seo_fit(V, n, V_best: Optional[float] = None) -> SeoFitResult:
    """Fit Seo 2014 Eq.(1) in n(V) space.

    Physical bounds enforce:
        alpha1 > 0 (loading edge rises), alpha2 < 0 (emission edge falls),
        ns near 0, no in [0.5, 3.0].
    """
    V = np.asarray(V, dtype=float)
    n = np.asarray(n, dtype=float)
    mask = np.isfinite(V) & np.isfinite(n)
    N = int(mask.sum())
    if N < 7:
        return SeoFitResult(False, n_fit_pts=N,
                            message=f'insufficient fit pts (N={N}<7)')

    Vf = V[mask]; nf = n[mask]
    V_low, V_high = float(Vf.min()), float(Vf.max())
    V_span = max(V_high - V_low, 1e-6)
    if V_best is None:
        V_best = float(Vf[np.argmin(np.abs(nf - 1.0))])

    p0 = [200.0, V_best - 0.25 * V_span,
          -200.0, V_best + 0.25 * V_span,
          0.0, 1.0]
    lb = [1.0,   V_low,  -1e5, V_low,  -0.5, 0.5]
    ub = [1e5,   V_high, -1.0, V_high,  0.5, 3.0]

    try:
        popt, _ = curve_fit(seo_model_n, Vf, nf,
                            p0=p0, bounds=(lb, ub), maxfev=20000)
    except (RuntimeError, ValueError) as e:
        return SeoFitResult(False, n_fit_pts=N,
                            message=f'curve_fit failed: {e}')

    V_model = np.linspace(V_low, V_high, 800)
    n_model = seo_model_n(V_model, *popt)
    dev = np.abs(n_model - 1.0)
    dev = np.where(dev > 1e-12, dev, 1e-12)  # avoid log(0)
    eta_model = np.log10(dev)
    i_opt = int(np.argmin(eta_model))
    V_opt = float(V_model[i_opt])
    eta_E_min = float(eta_model[i_opt])
    resid = nf - seo_model_n(Vf, *popt)
    rms = float(np.sqrt(np.mean(resid ** 2)))

    return SeoFitResult(True, popt=tuple(float(p) for p in popt),
                        V_model=V_model, n_model=n_model, eta_model=eta_model,
                        V_opt=V_opt, eta_E_min=eta_E_min, rms=rms,
                        n_fit_pts=N)
