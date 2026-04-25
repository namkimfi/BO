# schema version: v7.1 (adds optional sigma_n_gpr + n_gpr_mean 2D maps)
"""Parse a BO+GPR run folder (BO_pump_GPR_<TS>/) into a dict.

Per bo-gpr-post-plot SKILL.md §2. Post-plot code depends only on CSV/JSON
artifacts — notebook is not re-run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import json

import numpy as np
import pandas as pd


def _latest(folder: Path, pattern: str) -> Optional[Path]:
    hits = sorted(folder.glob(pattern))
    return hits[-1] if hits else None


def _read_json(p: Optional[Path]) -> Optional[dict]:
    if p is None or not p.exists():
        return None
    with open(p, 'r') as f:
        return json.load(f)


def _read_csv(p: Optional[Path]) -> Optional[pd.DataFrame]:
    if p is None or not p.exists():
        return None
    return pd.read_csv(p)


def _read_eta_map(p: Optional[Path]) -> Optional[pd.DataFrame]:
    if p is None or not p.exists():
        return None
    df = pd.read_csv(p, index_col=0)
    df.columns = df.columns.astype(float)
    df.index = df.index.astype(float)
    return df


def load_run(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir).expanduser().resolve()
    if not run_dir.is_dir():
        raise FileNotFoundError(f'run_dir not found: {run_dir}')

    out: dict[str, Any] = {'run_dir': run_dir}

    out['summary']      = _read_json(_latest(run_dir, 'summary_*.json'))
    out['config']       = _read_json(_latest(run_dir, 'config_*.json'))
    out['eta_summary']  = _read_json(_latest(run_dir, 'eta_summary_*.json'))

    out['phase1_V_ent']       = _read_csv(_latest(run_dir, 'phase1_V_ent_*.csv'))
    out['phase1_V_exit']      = _read_csv(_latest(run_dir, 'phase1_V_exit_*.csv'))
    out['phase2_bo']          = _read_csv(_latest(run_dir, 'phase2_bo_*.csv'))
    out['phase3a_vp_quality'] = _read_csv(_latest(run_dir, 'phase3a_vp_quality_*.csv'))
    out['phase3_map']         = _read_csv(_latest(run_dir, 'phase3_map_*.csv'))
    out['phase3_quality']     = _read_csv(_latest(run_dir, 'phase3_quality_*.csv'))
    out['phase4_pumpmap']     = _read_csv(_latest(run_dir, 'phase4_pumpmap_*.csv'))
    out['eta_E_map']          = _read_eta_map(_latest(run_dir, 'eta_E_map_*.csv'))
    # v7.1 optional artifacts (None on older runs; post-plot falls back gracefully)
    out['sigma_n_gpr']        = _read_eta_map(_latest(run_dir, 'sigma_n_gpr_*.csv'))
    out['n_gpr_mean']         = _read_eta_map(_latest(run_dir, 'n_gpr_mean_*.csv'))

    s = out['summary'] or {}
    out['timestamp']    = s.get('timestamp')
    out['best_V_ent']   = s.get('best_V_ent')
    out['best_V_exit']  = s.get('best_V_exit')
    out['V_p_used']     = s.get('V_p_used')
    out['version']      = s.get('version')
    out['timing']       = s.get('timing')
    out['measurements'] = s.get('measurements')

    if out['summary'] is None:
        raise FileNotFoundError(f'summary_*.json missing in {run_dir}')
    if out['phase4_pumpmap'] is None:
        raise FileNotFoundError(f'phase4_pumpmap_*.csv missing in {run_dir}')
    if out['eta_E_map'] is None:
        raise FileNotFoundError(f'eta_E_map_*.csv missing in {run_dir}')

    return out


def pumpmap_slice_at_V_ent(pumpmap: pd.DataFrame,
                           V_ent_target: float,
                           tol_V: float = 0.005) -> pd.DataFrame:
    m = np.abs(pumpmap['V_ent'].to_numpy() - V_ent_target) <= tol_V
    return pumpmap.loc[m].copy().sort_values('V_exit').reset_index(drop=True)


def eta_map_row_at_V_ent(eta_map: pd.DataFrame, V_ent_target: float) -> pd.Series:
    idx_vals = eta_map.index.to_numpy(dtype=float)
    i = int(np.argmin(np.abs(idx_vals - V_ent_target)))
    return eta_map.iloc[i]
