# schema version: v7.1
"""η_noise 2-stage robust estimation + Schoinas asymptote fit.

Parent skill: schoinas-eta-extrapolation (§2 model, §4 η_noise).
Extended by bo-gpr-post-plot:
  - §3: 2-stage η_noise (rough 10th pct → median inside plateau band)
  - §4: triple-condition fit data mask (η bounds + optional σ gate)
  - §5 (v7.1): schoinas_fit_2d — iterate §4 over every V_ent slice of
    an eta_E_map grid and return the global η_E^min (matches notebook
    "authoritative FoM" computation but reproducible from CSV artifacts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from scipy.optimize import curve_fit


def compute_eta(n) -> np.ndarray:
    n = np.asarray(n, dtype=float)
    dev = np.abs(n - 1.0)
    dev = np.where(dev > 0, dev, np.nan)  # avoid log(0) at n == 1 exactly
    return np.log10(dev)


def find_eta_noise_2stage(eta,
                          cutoff_upper: float = -0.6,
                          band: float = 0.3,
                          min_samples: int = 5) -> tuple[float, str]:
    """bo-gpr-post-plot §3 algorithm.

    Returns (eta_noise, stage_used).
    """
    eta = np.asarray(eta, dtype=float)
    valid = eta[np.isfinite(eta) & (eta < cutoff_upper)]
    if valid.size < 3:
        return float(cutoff_upper), 'fallback_too_few'
    rough = float(np.percentile(valid, 10))
    in_band = (valid > rough - band) & (valid < rough + band)
    if int(in_band.sum()) < min_samples:
        return rough, 'stage1_rough'
    refined = float(np.median(valid[in_band]))
    return refined, 'stage2_refined'


def _schoinas_model(V, a1, b1, a2, b2):
    V = np.asarray(V, dtype=float)
    L = a1 * V + b1
    R = a2 * V + b2
    m = np.maximum(L, R)
    return m + np.log10(10.0 ** (L - m) + 10.0 ** (R - m))


@dataclass
class SchoinasFitResult:
    success: bool
    popt: Optional[tuple] = None
    V_opt: Optional[float] = None
    eta_E_min: Optional[float] = None
    rms: Optional[float] = None
    n_fit_pts: int = 0
    fit_mask: Optional[np.ndarray] = None
    V_model: Optional[np.ndarray] = None
    eta_model: Optional[np.ndarray] = None
    message: str = ''

    def asymptotes(self):
        if not self.success:
            return None, None
        a1, b1, a2, b2 = self.popt
        return (a1, b1), (a2, b2)


def schoinas_fit(V, eta,
                 eta_noise: Optional[float] = None,
                 eta_fit_upper: float = -0.5,
                 eta_fit_lower_margin: float = 0.1,
                 sigma: Optional[np.ndarray] = None,
                 gpr_sigma_max: float = 0.05) -> SchoinasFitResult:
    """bo-gpr-post-plot §4 triple-condition fit.

    Parameters
    ----------
    V, eta      : arrays of same length. η = log10|n-1|.
    eta_noise   : used to set lower bound = η_noise + eta_fit_lower_margin.
                  None disables the lower bound.
    sigma       : optional GPR σ array; mask points with σ < gpr_sigma_max.
                  Skip entirely when sigma is None (BO-sampled source).
    """
    V = np.asarray(V, dtype=float)
    eta = np.asarray(eta, dtype=float)
    mask = np.isfinite(V) & np.isfinite(eta) & (eta < eta_fit_upper)
    if eta_noise is not None:
        mask &= eta > (eta_noise + eta_fit_lower_margin)
    if sigma is not None:
        sigma = np.asarray(sigma, dtype=float)
        mask &= np.isfinite(sigma) & (sigma < gpr_sigma_max)

    N = int(mask.sum())
    if N < 4:
        return SchoinasFitResult(False, n_fit_pts=N, fit_mask=mask,
                                 message=f'insufficient fit pts (N={N}<4)')

    Vf = V[mask]; ef = eta[mask]
    i_cen = int(np.argmin(ef))
    V_cen = Vf[i_cen]
    left = Vf <= V_cen
    right = Vf >= V_cen
    if left.sum() >= 2:
        sL, bL = np.polyfit(Vf[left], ef[left], 1)
    else:
        sL, bL = -1.0, float(np.mean(ef))
    if right.sum() >= 2:
        sR, bR = np.polyfit(Vf[right], ef[right], 1)
    else:
        sR, bR = 1.0, float(np.mean(ef))

    try:
        popt, _ = curve_fit(_schoinas_model, Vf, ef,
                            p0=[sL, bL, sR, bR], maxfev=10000)
    except (RuntimeError, ValueError) as e:
        return SchoinasFitResult(False, n_fit_pts=N, fit_mask=mask,
                                 message=f'curve_fit failed: {e}')

    a1, b1, a2, b2 = popt
    if a1 == a2:
        return SchoinasFitResult(False, popt=tuple(popt), n_fit_pts=N,
                                 fit_mask=mask,
                                 message='degenerate asymptotes (a1=a2)')

    V_opt = float((b2 - b1) / (a1 - a2))
    eta_E_min = float(a1 * V_opt + b1)
    V_model = np.linspace(float(V.min()), float(V.max()), 400)
    eta_model = _schoinas_model(V_model, *popt)
    resid = ef - _schoinas_model(Vf, *popt)
    rms = float(np.sqrt(np.mean(resid ** 2)))

    msg = ''
    if a1 >= 0 or a2 <= 0:
        msg = f'nonphysical asymptote (a1={a1:.3g}, a2={a2:.3g})'

    return SchoinasFitResult(True, popt=tuple(float(p) for p in popt),
                             V_opt=V_opt, eta_E_min=eta_E_min,
                             rms=rms, n_fit_pts=N, fit_mask=mask,
                             V_model=V_model, eta_model=eta_model,
                             message=msg)


@dataclass
class SchoinasFit2DResult:
    """2D iterated Schoinas result. Global η_E^min is the minimum over all
    per-V_ent slice fits that satisfy physical-asymptote constraints.
    """
    success: bool
    V_ent_grid: Optional[np.ndarray] = None
    eta_E_min_per_vent: Optional[np.ndarray] = None      # shape (n_vent,)
    V_exit_opt_per_vent: Optional[np.ndarray] = None     # shape (n_vent,)
    n_fit_pts_per_vent: Optional[np.ndarray] = None      # int count per slice
    slice_success: Optional[np.ndarray] = None           # bool mask per slice
    eta_E_min_global: Optional[float] = None
    V_ent_at_min: Optional[float] = None
    V_exit_at_min: Optional[float] = None
    n_slices_fitted: int = 0
    sigma_used: bool = False
    message: str = ''


def schoinas_fit_2d(eta_map,
                    sigma_map=None,
                    eta_noise: Optional[float] = None,
                    eta_fit_upper: float = -0.5,
                    eta_fit_lower_margin: float = 0.1,
                    gpr_sigma_max: float = 0.05,
                    physical_only: bool = True) -> SchoinasFit2DResult:
    """Iterate `schoinas_fit` over every V_ent row of an eta_E_map grid.

    Parameters
    ----------
    eta_map   : DataFrame — index=V_ent (V), columns=V_exit (V), values=η.
    sigma_map : optional DataFrame of GPR σ(n) on the same grid; when present,
                the σ-gate is applied per-slice and `sigma_used=True`.
    physical_only : if True, slices that fail (a1<0, a2>0) are excluded from
                    the global minimum search (prevents nonphysical outliers).

    The global η_E^min is typically much closer to the notebook's reported FoM
    than the single-row BO-slice fit because the asymptote intersection does
    not always sit at the BO best_V_ent.
    """
    import pandas as pd  # localized import to keep module stdlib-ish
    if eta_map is None:
        return SchoinasFit2DResult(False, message='eta_map is None')

    V_ent_arr = eta_map.index.to_numpy(dtype=float)
    V_exit_arr = eta_map.columns.to_numpy(dtype=float)
    eta_2d = eta_map.to_numpy(dtype=float)

    sigma_used = False
    if sigma_map is not None:
        sigma_used = True
        sigma_2d = sigma_map.reindex(
            index=eta_map.index, columns=eta_map.columns).to_numpy(dtype=float)
    else:
        sigma_2d = None

    n_vent = V_ent_arr.size
    eta_min_per = np.full(n_vent, np.nan)
    Vx_opt_per = np.full(n_vent, np.nan)
    n_pts_per = np.zeros(n_vent, dtype=int)
    ok_per = np.zeros(n_vent, dtype=bool)

    for i in range(n_vent):
        eta_row = eta_2d[i, :]
        sig_row = sigma_2d[i, :] if sigma_2d is not None else None
        res = schoinas_fit(V_exit_arr, eta_row,
                           eta_noise=eta_noise,
                           eta_fit_upper=eta_fit_upper,
                           eta_fit_lower_margin=eta_fit_lower_margin,
                           sigma=sig_row, gpr_sigma_max=gpr_sigma_max)
        n_pts_per[i] = res.n_fit_pts
        if res.success and res.eta_E_min is not None:
            a1, _, a2, _ = res.popt
            physical = (a1 < 0) and (a2 > 0)
            if (not physical_only) or physical:
                eta_min_per[i] = res.eta_E_min
                Vx_opt_per[i] = res.V_opt
                ok_per[i] = True

    if not ok_per.any():
        return SchoinasFit2DResult(False,
            V_ent_grid=V_ent_arr,
            eta_E_min_per_vent=eta_min_per,
            V_exit_opt_per_vent=Vx_opt_per,
            n_fit_pts_per_vent=n_pts_per,
            slice_success=ok_per,
            n_slices_fitted=0, sigma_used=sigma_used,
            message='no physical-asymptote slice succeeded')

    i_best = int(np.nanargmin(eta_min_per))
    return SchoinasFit2DResult(True,
        V_ent_grid=V_ent_arr,
        eta_E_min_per_vent=eta_min_per,
        V_exit_opt_per_vent=Vx_opt_per,
        n_fit_pts_per_vent=n_pts_per,
        slice_success=ok_per,
        eta_E_min_global=float(eta_min_per[i_best]),
        V_ent_at_min=float(V_ent_arr[i_best]),
        V_exit_at_min=float(Vx_opt_per[i_best]),
        n_slices_fitted=int(ok_per.sum()),
        sigma_used=sigma_used)
