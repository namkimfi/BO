# schema version: v7.0
"""CLI: python main.py <run_dir> [--eta-fit-upper -0.5] ...

Per bo-gpr-post-plot SKILL.md §§5, 7, 8:
  * Reads a BO+GPR run folder (read-only).
  * Produces <run_dir>_postplot/ with fig_E1/E2/M1/M2/T + fit_results.json
    + fit_curves.csv + postplot_config.json.
  * Original run folder is never modified.

Terminology (memory/scientific_references.md):
  * "Schoinas fit" = 2024 asymptote model (Appl. Phys. Lett. 125, 124001)
  * "Seo 2014 Eq.(1)" = 6-param sigmoid — NOT Schoinas Eq.(1)
"""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import numpy as np
import pandas as pd

from load_run import load_run, pumpmap_slice_at_V_ent, eta_map_row_at_V_ent
from eta_refit import (
    compute_eta, find_eta_noise_2stage, schoinas_fit, schoinas_fit_2d,
)
from seo_fit import seo_fit
from gpr_refit import fit_local_gpr_1d
from plot_publication import (
    PlotStyle, _save, _audit_text,
    fig_C_iv_trace,
    fig_E1_eta_extrapolation, fig_E2_schoinas_vs_seo,
    fig_M1_eta_2d, fig_M2_bo_trajectory, fig_T_timing_table,
)

__version__ = '1.0'


@dataclass
class PostPlotConfig:
    # η_noise (§3)
    eta_noise_cutoff_upper: float = -0.6
    eta_noise_plateau_band_V: float = 0.3
    eta_noise_min_samples: int = 5
    # Schoinas fit (§4)
    eta_fit_upper: float = -0.5
    eta_fit_lower_margin: float = 0.1  # actual lower = η_noise + margin
    gpr_sigma_max: float = 0.05
    # V_ent slice tolerance for 1D cuts (§5)
    v_ent_slice_tol_V: float = 0.005
    # Seo 2014 fit
    seo_fit_enabled: bool = True
    # Output
    dpi: int = 300
    save_pdf: bool = True
    save_png: bool = True


def _parse_args():
    p = argparse.ArgumentParser(
        description='BO+GPR post-plot generator (Layer C).')
    p.add_argument('run_dir', type=str,
                   help='Path to data/BO_pump_GPR_<TS>/ folder')
    p.add_argument('--out-dir', type=str, default=None,
                   help='Override output folder (default: <run_dir>_postplot)')
    p.add_argument('--eta-fit-upper', type=float, default=None)
    p.add_argument('--eta-fit-lower-margin', type=float, default=None)
    p.add_argument('--eta-noise-band', type=float, default=None,
                   dest='eta_noise_plateau_band_V')
    p.add_argument('--eta-noise-cutoff', type=float, default=None,
                   dest='eta_noise_cutoff_upper')
    p.add_argument('--gpr-sigma-max', type=float, default=None)
    p.add_argument('--v-ent-tol-mV', type=float, default=None,
                   help='V_ent slice tolerance in mV (default: 5.0)')
    p.add_argument('--no-pdf', action='store_true')
    p.add_argument('--no-seo', action='store_true')
    return p.parse_args()


def _apply_overrides(cfg: PostPlotConfig, args) -> PostPlotConfig:
    for key in ('eta_fit_upper', 'eta_fit_lower_margin',
                'eta_noise_plateau_band_V', 'eta_noise_cutoff_upper',
                'gpr_sigma_max'):
        v = getattr(args, key, None)
        if v is not None:
            setattr(cfg, key, v)
    if args.v_ent_tol_mV is not None:
        cfg.v_ent_slice_tol_V = args.v_ent_tol_mV / 1000.0
    if args.no_pdf:
        cfg.save_pdf = False
    if args.no_seo:
        cfg.seo_fit_enabled = False
    return cfg


def _snapshot_mtimes(run_dir: Path) -> dict:
    return {p.name: p.stat().st_mtime
            for p in run_dir.iterdir() if p.is_file()}


def _verify_mtimes_unchanged(snap: dict, run_dir: Path):
    now = _snapshot_mtimes(run_dir)
    changed = [k for k in snap if k in now and now[k] != snap[k]]
    missing = [k for k in snap if k not in now]
    if changed or missing:
        raise RuntimeError(
            f'Original run folder was modified (changed={changed}, '
            f'missing={missing}). This violates bo-gpr-post-plot §7 read-only.')


def run(args):
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        print(f'error: run_dir not found: {run_dir}', file=sys.stderr)
        return 1

    cfg = PostPlotConfig()
    cfg = _apply_overrides(cfg, args)

    out_dir = (Path(args.out_dir).expanduser().resolve()
               if args.out_dir
               else run_dir.parent / (run_dir.name + '_postplot'))
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'[post-plot v{__version__}] run: {run_dir.name}')
    print(f'  out: {out_dir}')

    snap = _snapshot_mtimes(run_dir)
    data = load_run(run_dir)
    ts = data.get('timestamp') or 'unknown'
    best_Vent = float(data['best_V_ent'])
    best_Vexit = float(data['best_V_exit'])

    # ── η_noise (2-stage) on phase4 measurements ────────────────────────────
    pm = data['phase4_pumpmap']
    eta_all = compute_eta(pm['n'].to_numpy())
    eta_noise, stage_used = find_eta_noise_2stage(
        eta_all,
        cutoff_upper=cfg.eta_noise_cutoff_upper,
        band=cfg.eta_noise_plateau_band_V,
        min_samples=cfg.eta_noise_min_samples)
    print(f'  η_noise = {eta_noise:+.4f}  ({stage_used})')

    eta_fit_lower = eta_noise + cfg.eta_fit_lower_margin

    # ── BO-sampled 1D slice at best_V_ent ───────────────────────────────────
    bo_slice = pumpmap_slice_at_V_ent(pm, best_Vent, tol_V=cfg.v_ent_slice_tol_V)
    V_bo = bo_slice['V_exit'].to_numpy()
    n_bo = bo_slice['n'].to_numpy()
    eta_bo = compute_eta(n_bo)

    # ── GPR grid slice at best_V_ent ────────────────────────────────────────
    grid_row = eta_map_row_at_V_ent(data['eta_E_map'], best_Vent)
    V_grid = grid_row.index.to_numpy(dtype=float)
    eta_grid = grid_row.to_numpy(dtype=float)

    # v7.1: σ map is a separate CSV — pull the row matching best_V_ent
    sigma_grid = None
    if data.get('sigma_n_gpr') is not None:
        sig_row = eta_map_row_at_V_ent(data['sigma_n_gpr'], best_Vent)
        sigma_grid = sig_row.to_numpy(dtype=float)
        print(f'  σ map loaded (shape {data["sigma_n_gpr"].shape}); '
              f'σ gate active at σ<{cfg.gpr_sigma_max:.3g}')

    # ── Fits ───────────────────────────────────────────────────────────────
    schoinas_grid = schoinas_fit(
        V_grid, eta_grid,
        eta_noise=eta_noise,
        eta_fit_upper=cfg.eta_fit_upper,
        eta_fit_lower_margin=cfg.eta_fit_lower_margin,
        sigma=sigma_grid, gpr_sigma_max=cfg.gpr_sigma_max)

    schoinas_bo = schoinas_fit(
        V_bo, eta_bo,
        eta_noise=eta_noise,
        eta_fit_upper=cfg.eta_fit_upper,
        eta_fit_lower_margin=cfg.eta_fit_lower_margin,
        sigma=None)

    # 2D iterated Schoinas fit — global η_E^min across the eta_E_map grid.
    # This is the "authoritative FoM" matching the notebook's -2.6 class
    # result; the 1D best_V_ent-only fit above is for panel continuity.
    schoinas_2d = schoinas_fit_2d(
        data['eta_E_map'],
        sigma_map=data.get('sigma_n_gpr'),
        eta_noise=eta_noise,
        eta_fit_upper=cfg.eta_fit_upper,
        eta_fit_lower_margin=cfg.eta_fit_lower_margin,
        gpr_sigma_max=cfg.gpr_sigma_max,
        physical_only=True)
    if schoinas_2d.success:
        gate = 'σ-gated' if schoinas_2d.sigma_used else 'η-only'
        print(f'  Schoinas 2D (iterated, {gate}): '
              f'{schoinas_2d.n_slices_fitted}/{len(schoinas_2d.V_ent_grid)} '
              f'slices physical; global η_E^min='
              f'{schoinas_2d.eta_E_min_global:+.3f} @ '
              f'V_ent={schoinas_2d.V_ent_at_min*1000:+.1f} mV, '
              f'V_exit={schoinas_2d.V_exit_at_min*1000:+.1f} mV')
    else:
        print(f'  Schoinas 2D: FAILED — {schoinas_2d.message}')

    seo_res = None
    if cfg.seo_fit_enabled:
        seo_res = seo_fit(V_bo, n_bo, V_best=best_Vexit)

    # ── Print fit summary ──────────────────────────────────────────────────
    for name, r in [('Schoinas (GPR grid)', schoinas_grid),
                    ('Schoinas (BO-sampled)', schoinas_bo)]:
        if r.success:
            print(f'  {name}: N={r.n_fit_pts}, RMS={r.rms:.3f}, '
                  f'η_E^min={r.eta_E_min:+.3f} @ V_opt={r.V_opt*1000:.1f} mV'
                  + (f'  [{r.message}]' if r.message else ''))
        else:
            print(f'  {name}: FAILED — {r.message}')
    if seo_res is not None:
        if seo_res.success:
            print(f'  Seo 2014 Eq.(1): N={seo_res.n_fit_pts}, RMS_n='
                  f'{seo_res.rms:.3f}, η_E^min={seo_res.eta_E_min:+.3f} '
                  f'@ V_opt={seo_res.V_opt*1000:.1f} mV')
        else:
            print(f'  Seo 2014 Eq.(1): FAILED — {seo_res.message}')

    # ── Plot style ─────────────────────────────────────────────────────────
    st = PlotStyle()
    st.dpi = cfg.dpi
    fmts = []
    if cfg.save_pdf: fmts.append('pdf')
    if cfg.save_png: fmts.append('png')
    st.out_fmt = fmts or ['png']

    audit = _audit_text(ts, f'v{__version__}', cfg)

    # ── Figures ────────────────────────────────────────────────────────────
    V_p_used_E1 = (data.get('summary') or {}).get('V_p_used')
    V_p_used_E1 = float(V_p_used_E1) if V_p_used_E1 is not None else None

    st_E1 = PlotStyle.for_panel('E1')
    st_E1.dpi = st.dpi; st_E1.out_fmt = st.out_fmt
    fig = fig_E1_eta_extrapolation(
        V_bo=V_bo, eta_bo=eta_bo,
        V_grid=V_grid, eta_grid=eta_grid,
        fit_result=schoinas_grid,
        eta_noise=eta_noise,
        eta_fit_upper=cfg.eta_fit_upper,
        eta_fit_lower=eta_fit_lower,
        source_label='GPR grid',
        audit=audit, st=st_E1,
        best_V_ent=best_Vent, V_p_used=V_p_used_E1,
        sigma_used=(sigma_grid is not None))
    _save(fig, 'fig_E1_eta_extrapolation', st_E1, str(out_dir))
    import matplotlib.pyplot as plt
    plt.close(fig)

    if seo_res is not None:
        st_E2 = PlotStyle.for_panel('E2')
        st_E2.dpi = st.dpi; st_E2.out_fmt = st.out_fmt
        fig = fig_E2_schoinas_vs_seo(
            V_data=V_bo, n_data=n_bo,
            schoinas=schoinas_bo, seo=seo_res,
            eta_noise=eta_noise, audit=audit, st=st_E2)
        _save(fig, 'fig_E2_schoinas_vs_seo', st_E2, str(out_dir))
        plt.close(fig)

    # fig_C — I vs V_exit trace at best_V_ent (notebook panel (C) reproduction)
    # Sources: phase4_pumpmap = BO-sampled actual measurements (red pts);
    # phase3_map provides the V_exit grid; GPR refit (sklearn) gives mean+σ.
    if data.get('phase4_pumpmap') is not None and len(data['phase4_pumpmap']) > 0:
        I_ref_nA = float((data['summary'] or {}).get('I_ref_nA', np.nan))
        V_p_used = float((data['summary'] or {}).get('V_p_used', np.nan))

        # Wider V_ent tolerance for display (notebook panel (C) shows ~37 pts)
        bo_tol_V = cfg.v_ent_slice_tol_V * 2.0  # default 10 mV
        pm_all = data['phase4_pumpmap']
        bo_mask = np.abs(pm_all['V_ent'].to_numpy() - best_Vent) <= bo_tol_V
        # Exclude 'lhs' stage (initial random scan, points far from best region)
        # to match notebook's panel (C) which shows only adaptive/refine points
        if 'stage' in pm_all.columns:
            bo_mask &= pm_all['stage'].astype(str) != 'lhs'
        bo_sel = pm_all.loc[bo_mask].copy().sort_values('V_exit').reset_index(drop=True)
        V_bo = bo_sel['V_exit'].to_numpy()
        # Compute I (nA) from n and I_ref: I = n * I_ref (exact) if I_nA missing
        if 'I_nA' in bo_sel.columns and bo_sel['I_nA'].notna().all():
            I_bo = bo_sel['I_nA'].to_numpy()
        else:
            I_bo = bo_sel['n'].to_numpy() * I_ref_nA

        # GPR prediction grid — from phase3_map if available, else linspace
        if data.get('phase3_map') is not None and len(data['phase3_map']) > 0:
            p3 = data['phase3_map']
            p3_slice = p3.loc[np.abs(p3['V_ent'] - best_Vent) < 0.02
                              ].sort_values('V_exit').reset_index(drop=True)
            V_pred = np.unique(p3_slice['V_exit'].to_numpy())
            if V_pred.size < 20:
                V_pred = np.linspace(V_bo.min(), V_bo.max(), 200)
        else:
            V_pred = np.linspace(V_bo.min() * 0.5, V_bo.max() * 1.1, 200)

        gpr_res = fit_local_gpr_1d(V_bo, I_bo, V_pred)
        if gpr_res.success:
            print(f'  GPR refit (fig_C): N_train={gpr_res.n_train}, '
                  f'kernel={gpr_res.kernel_repr}')
            gpr_mean = gpr_res.mean
            gpr_std = gpr_res.std
        else:
            print(f'  [warn] GPR refit failed: {gpr_res.message}')
            # Fallback: use phase3_map as mean, no band
            gpr_mean = np.interp(V_pred, V_bo, I_bo)
            gpr_std = None

        st_C = PlotStyle.for_panel('C')
        st_C.dpi = st.dpi; st_C.out_fmt = st.out_fmt
        fig = fig_C_iv_trace(
            V_gpr_V=V_pred, I_gpr_mean_nA=gpr_mean, I_gpr_std_nA=gpr_std,
            V_bo_V=V_bo, I_bo_nA=I_bo,
            best_V_ent=best_Vent, best_V_exit=best_Vexit,
            V_p_used=V_p_used, I_ref_nA=I_ref_nA,
            audit=audit, st=st_C)
        _save(fig, 'fig_C_iv_trace', st_C, str(out_dir))
        plt.close(fig)
    else:
        print('  [warn] phase4_pumpmap missing — skipping fig_C')

    st_M1 = PlotStyle.for_panel('M1')
    st_M1.dpi = st.dpi; st_M1.out_fmt = st.out_fmt
    fig = fig_M1_eta_2d(
        eta_map=data['eta_E_map'],
        best_V_ent=best_Vent, best_V_exit=best_Vexit,
        eta_noise=eta_noise, audit=audit, st=st_M1)
    _save(fig, 'fig_M1_eta_2d', st_M1, str(out_dir))
    plt.close(fig)

    st_M2 = PlotStyle.for_panel('M2')
    st_M2.dpi = st.dpi; st_M2.out_fmt = st.out_fmt
    fig = fig_M2_bo_trajectory(
        eta_map=data['eta_E_map'],
        phase2_bo=data.get('phase2_bo'),
        phase4_pumpmap=pm,
        best_V_ent=best_Vent, best_V_exit=best_Vexit,
        audit=audit, st=st_M2)
    _save(fig, 'fig_M2_bo_trajectory', st_M2, str(out_dir))
    plt.close(fig)

    st_T = PlotStyle.for_panel('T')
    st_T.dpi = st.dpi; st_T.out_fmt = st.out_fmt
    fig = fig_T_timing_table(data['summary'], audit=audit, st=st_T)
    _save(fig, 'fig_T_timing_table', st_T, str(out_dir))
    plt.close(fig)

    # ── Persisted results ──────────────────────────────────────────────────
    def _fit_dict(r, include_curve=False):
        if r is None:
            return None
        d = {
            'success': bool(r.success),
            'n_fit_pts': int(r.n_fit_pts),
            'popt': (list(r.popt) if r.popt is not None else None),
            'V_opt': r.V_opt,
            'eta_E_min': r.eta_E_min,
            'rms': r.rms,
            'message': r.message or '',
        }
        return d

    fit_results = {
        'postplot_version': __version__,
        'run_timestamp': ts,
        'eta_noise': float(eta_noise),
        'eta_noise_stage': stage_used,
        'eta_fit_lower': float(eta_fit_lower),
        'best_V_ent': best_Vent,
        'best_V_exit': best_Vexit,
        'schoinas_gpr_grid': _fit_dict(schoinas_grid),
        'schoinas_bo_sampled': _fit_dict(schoinas_bo),
        'schoinas_2d_iterated': ({
            'success': bool(schoinas_2d.success),
            'sigma_used': bool(schoinas_2d.sigma_used),
            'n_slices_fitted': int(schoinas_2d.n_slices_fitted),
            'eta_E_min_global': schoinas_2d.eta_E_min_global,
            'V_ent_at_min': schoinas_2d.V_ent_at_min,
            'V_exit_at_min': schoinas_2d.V_exit_at_min,
            'message': schoinas_2d.message or '',
        } if schoinas_2d is not None else None),
        'seo_2014_eq1': _fit_dict(seo_res) if seo_res is not None else None,
        # cross-check vs notebook
        'notebook_eta_noise': (data.get('eta_summary') or {}).get('eta_noise'),
        'notebook_eta_E_min': (data.get('eta_summary') or {}).get('eta_E_min'),
    }
    with open(out_dir / f'fit_results_{ts}.json', 'w') as f:
        json.dump(fit_results, f, indent=2)
    print(f'  saved -> {out_dir / ("fit_results_" + ts + ".json")}')

    with open(out_dir / f'postplot_config_{ts}.json', 'w') as f:
        json.dump({'postplot_version': __version__, **asdict(cfg)}, f, indent=2)

    # Fit curves CSV
    curve_cols = {}
    if schoinas_grid.success:
        curve_cols['V_grid'] = schoinas_grid.V_model
        curve_cols['eta_schoinas_grid'] = schoinas_grid.eta_model
    if schoinas_bo.success:
        # Put BO-sampled Schoinas curve on a separate V axis if it differs
        curve_cols['V_bo_fit'] = schoinas_bo.V_model
        curve_cols['eta_schoinas_bo'] = schoinas_bo.eta_model
    if seo_res is not None and seo_res.success:
        curve_cols['V_seo'] = seo_res.V_model
        curve_cols['n_seo'] = seo_res.n_model
        curve_cols['eta_seo'] = seo_res.eta_model
    if curve_cols:
        # pad to common length for DataFrame
        L = max(len(v) for v in curve_cols.values())
        for k, v in curve_cols.items():
            if len(v) < L:
                pad = np.full(L - len(v), np.nan)
                curve_cols[k] = np.concatenate([v, pad])
        pd.DataFrame(curve_cols).to_csv(
            out_dir / f'fit_curves_{ts}.csv', index=False)
        print(f'  saved -> {out_dir / ("fit_curves_" + ts + ".csv")}')

    # ── Read-only verification (§7, §9) ────────────────────────────────────
    _verify_mtimes_unchanged(snap, run_dir)
    print('  ✓ original run folder unmodified')

    # ── Validation checklist (§9) ──────────────────────────────────────────
    print('\n[validation checklist]')
    # Authoritative η_E^min = 2D iterated (matches notebook FoM),
    # fall back to 1D GPR-grid slice when 2D unavailable.
    if schoinas_2d.success:
        eta_E_min_auth = schoinas_2d.eta_E_min_global
        source = f'2D iterated ({"σ-gated" if schoinas_2d.sigma_used else "η-only"})'
    elif schoinas_grid.success:
        eta_E_min_auth = schoinas_grid.eta_E_min
        source = '1D GPR-grid slice'
    else:
        eta_E_min_auth = None
        source = 'none'
    physical = (eta_E_min_auth is not None and eta_E_min_auth < eta_noise)
    print(f'  η_E^min ({source}) = '
          f'{eta_E_min_auth if eta_E_min_auth is None else f"{eta_E_min_auth:+.3f}"}'
          f'  <  η_noise={eta_noise:+.3f}:     {physical}')
    nb_en = (data.get('eta_summary') or {}).get('eta_noise')
    nb_em = (data.get('eta_summary') or {}).get('eta_E_min')
    if nb_en is not None:
        diff = abs(eta_noise - nb_en)
        print(f'  notebook η_noise={nb_en:+.4f}, diff={diff:.4f} '
              f'({"OK" if diff <= 0.05 else "OUT OF TOL"})')
    if nb_em is not None and eta_E_min_auth is not None:
        demin = abs(eta_E_min_auth - nb_em)
        print(f'  notebook η_E^min={nb_em:+.4f}, diff={demin:.4f} '
              f'({"OK" if demin <= 0.10 else "OUT OF TOL"})')
    print(f'  fig_E1 fit pts (GPR grid, 1D): {schoinas_grid.n_fit_pts}')
    if schoinas_2d.success:
        print(f'  2D slices fitted (physical): '
              f'{schoinas_2d.n_slices_fitted}/{len(schoinas_2d.V_ent_grid)}')
    return 0


if __name__ == '__main__':
    sys.exit(run(_parse_args()))
