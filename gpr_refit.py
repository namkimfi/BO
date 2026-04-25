# schema version: v7.0
"""Local GPR refit for visualization of GPR mean + σ variance band.

The notebook stores only the GPR mean grid (phase3_map_*.csv); σ is not
persisted. This module refits a small GPR on the BO-sampled points near
best_V_ent to recover the variance band for figures like panel (C).

This is a VISUALIZATION helper only. It is NOT the BO-loop GPR (Layer B2):
kernel hyperparameters are set for display-quality smoothness, not for
acquisition-function optimization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class GPRRefit:
    success: bool
    V_pred: Optional[np.ndarray] = None
    mean: Optional[np.ndarray] = None
    std: Optional[np.ndarray] = None
    n_train: int = 0
    kernel_repr: str = ''
    message: str = ''


def fit_local_gpr_1d(V_train: np.ndarray,
                     y_train: np.ndarray,
                     V_pred: np.ndarray,
                     length_scale_init: float = 0.02) -> GPRRefit:
    """Fit a 1D GPR on (V_train, y_train) and predict mean ± std on V_pred.

    Kernel: Constant × Matern(ν=2.5) + WhiteKernel (for measurement noise).
    """
    try:
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import (
            ConstantKernel, Matern, WhiteKernel)
    except ImportError:
        return GPRRefit(False, message='sklearn not available — skipping GPR refit')

    V_train = np.asarray(V_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    mask = np.isfinite(V_train) & np.isfinite(y_train)
    V_train = V_train[mask]; y_train = y_train[mask]
    N = int(V_train.size)
    if N < 4:
        return GPRRefit(False, n_train=N, message=f'insufficient training pts (N={N}<4)')

    # Sort for numerical stability
    order = np.argsort(V_train)
    V_train = V_train[order]; y_train = y_train[order]

    # Estimate reasonable noise from local variability (|y - running median|)
    y_std = float(np.std(y_train))
    noise_init = max(y_std * 0.05, 1e-6)

    kernel = (ConstantKernel(1.0, (1e-5, 1e5))
              * Matern(length_scale=length_scale_init,
                       length_scale_bounds=(1e-4, 5e-1),
                       nu=2.5)
              + WhiteKernel(noise_level=noise_init ** 2,
                            noise_level_bounds=(1e-12, 1e-2)))
    gpr = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                   n_restarts_optimizer=3, alpha=0.0)
    try:
        gpr.fit(V_train.reshape(-1, 1), y_train)
    except Exception as e:
        return GPRRefit(False, n_train=N, message=f'GPR fit failed: {e}')

    V_pred = np.asarray(V_pred, dtype=float)
    try:
        mean, std = gpr.predict(V_pred.reshape(-1, 1), return_std=True)
    except Exception as e:
        return GPRRefit(False, n_train=N, message=f'GPR predict failed: {e}')

    return GPRRefit(True, V_pred=V_pred, mean=mean, std=std, n_train=N,
                    kernel_repr=str(gpr.kernel_))
