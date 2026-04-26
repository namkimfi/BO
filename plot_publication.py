# schema version: v7.2
"""Publication-quality figure generators for BO+GPR post-plot (Layer C).

Follows lab-plot-style §1 (Full PlotStyle tier) and bo-gpr-post-plot §6.

Axis label convention: V_ent / V_exit (physical gate names), never V_1 / V_2.
Terminology (corrected 2026-04-26 — see memory/scientific_references.md):
  * "Schoinas fit"        = Schoinas 2024 η-asymptote model (4-param).
  * "Seo 2014 Eq.(1)"     = Kashcheyevs decay-cascade Gumbel-sum (4-param).
  * "Sigmoid plateau fit" = phenomenological 6-param Fermi-product
                            (formerly mislabeled "Seo 2014 Eq.(1)").
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from eta_refit import SchoinasFitResult, compute_eta
from sigmoid_plateau_fit import SigmoidPlateauFitResult
from decay_cascade_fit import DecayCascadeFitResult


# ─────────────────────────────────────────────────────────────────────────────
# PlotStyle — lab-plot-style §1 Full tier
# ─────────────────────────────────────────────────────────────────────────────

class PlotStyle:
    """Base plotting style. Every field is per-panel-overridable in main.py
    via the `PANEL_STYLES` dict (see STYLE_GUIDE.md).
    """
    # ─── Figure dimensions (inches) ──────────────────────────────────────
    # Single source of truth: fig_w × fig_h is the final figure size.
    # APL single-column = 3.37 in, double-column = 7.0 in.
    fig_w  = 7.0
    #fig_h  = 3.6
    fig_h  = 7.6

    # ─── Font ────────────────────────────────────────────────────────────
    font_family  = 'Arial'
    label_size   = 12     # axis labels (x, y)
    tick_size    = 10     # axis tick labels
    legend_size  = 10    # legend entries
    title_size   = 12
    cbar_size    = 10
    annot_size   = 10    # in-axes text annotations
    panel_size   = 11    # panel label "(E1)", "(a)", ...
    panel_weight = 'bold'

    # ─── Line ────────────────────────────────────────────────────────────
    lw         = 1.2     # generic line
    lw_model   = 1.5     # fit model curve
    lw_asym    = 1.0     # asymptote / reference line
    lw_contour = 0.8

    # ─── Per-symbol marker sizes ─────────────────────────────────────────
    # Each data series has its OWN size knob. Override per panel via PANELS.
    # Legacy aliases (ms / ms_fit / ms_best) are kept for back-compat only.
    # ms_bo            = 3   # BO-sampled η scatter   (fig_E1, fig_E2, fig_E3)
    # ms_gpr_grid      = 3   # GPR grid η scatter     (fig_E1)
    # ms_fit_pts       = 5   # open-circle fit-point highlight (fig_E1)
    # ms_best          = 12  # generic "best point" star (fig_E1, fig_M1, fig_M2)
    # ms_schoinas_star = 12  # Schoinas η_E^min star  (fig_E2, fig_E3)
    # ms_sigmoid_star  = 12  # sigmoid-plateau η_E^min star (fig_E2)
    # ms_decay_star    = 12  # decay-cascade η_E^min star   (fig_E3)
    # ms_bo_iv         = 5   # BO sampling pts in I-vs-V_exit trace (fig_C)
    # ms_phase4        = 3   # phase4 stage markers   (fig_M2)
    # ms_bo_history    = 18  # scatter s= for BO history (fig_M2; uses scatter)
    # # Legacy aliases (don't use directly in new code).
    # ms         = 3
    # ms_fit     = 5

     # ─── Per-symbol marker sizes ─────────────────────────────────────────
    # Each data series has its OWN size knob. Override per panel via PANELS.
    # Legacy aliases (ms / ms_fit / ms_best) are kept for back-compat only.
    ms_bo            = 4   # BO-sampled η scatter   (fig_E1, fig_E2, fig_E3)
    ms_gpr_grid      = 4   # GPR grid η scatter     (fig_E1)
    ms_fit_pts       = 6   # open-circle fit-point highlight (fig_E1)
    ms_best          = 12  # generic "best point" star (fig_E1, fig_M1, fig_M2)
    ms_schoinas_star = 12  # Schoinas η_E^min star  (fig_E2, fig_E3)
    ms_sigmoid_star  = 12  # sigmoid-plateau η_E^min star (fig_E2)
    ms_decay_star    = 12  # decay-cascade η_E^min star   (fig_E3)
    ms_bo_iv         = 5   # BO sampling pts in I-vs-V_exit trace (fig_C)
    ms_phase4        = 3   # phase4 stage markers   (fig_M2)
    ms_bo_history    = 18  # scatter s= for BO history (fig_M2; uses scatter)
    # Legacy aliases (don't use directly in new code).
    ms         = 3
    ms_fit     = 5

    # ─── Panel label (e.g., "(E1)") placement ────────────────────────────
    panel_label_text = None   # None → each fig uses its default ('E1','E2',...)
    panel_label      = False   # master on/off
    panel_label_x    = 0.02   # axes-relative; lab default is inside upper-left
    panel_label_y    = 0.97
    panel_label_ha   = 'left'
    panel_label_va   = 'top'

    # ─── Legend control ──────────────────────────────────────────────────
    legend_loc            = 'upper center'
    legend_ncol           = 3
    legend_bbox_to_anchor = (0.5, -0.34)   # default: below xlabel, outside axes
    legend_framealpha     = 0.92
    legend_handlelength   = None           # None = matplotlib default
    legend_handletextpad  = None
    legend_labelspacing   = None
    legend_borderpad      = None
    legend_borderaxespad  = 0.3

    # ─── Title pad ───────────────────────────────────────────────────────
    title_pad = 8

    # ─── Audit strip (postplot provenance) ───────────────────────────────
    # audit_loc selects coordinate system; (audit_x, audit_y) is the anchor:
    #   'figure'   → figure coords [0..1]   — origin = page bottom-left.
    #                Use y near 0 for bottom (e.g., 0.005) or near 1 for top
    #                (e.g., 0.995); ha/va decide which corner of the text
    #                anchors at (x, y).
    #   'axes_top' → axes coords [0..1+]    — relative to plot box.
    #                default (0.01, 1.02) sits just above the axis frame.
    #   'off'      → no audit drawn
    audit_show       = True
    audit_loc        = 'figure'
    audit_x          = 0.5
    audit_y          = 0.005
    audit_ha         = 'center'
    audit_va         = 'bottom'
    audit_size_delta = -2          # font size = max(annot_size + delta, 5)
    audit_color      = '#555555'

    # ─── Page margins (applied AFTER tight_layout) ──────────────────────
    # Use these to carve out room for figure-coord audit strips, or to widen
    # the gap between x-axis label and figure bottom edge. Each is a fraction
    # of figure height/width in [0..1]. None → leave tight_layout result alone.
    #   bottom_margin → fig.subplots_adjust(bottom=value)  (raises x-label up)
    #   top_margin    → fig.subplots_adjust(top=value)     (lowers title down)
    #   left_margin   → fig.subplots_adjust(left=value)
    #   right_margin  → fig.subplots_adjust(right=value)
    bottom_margin = None
    top_margin    = None
    left_margin   = None
    right_margin  = None

    # ─── Output ──────────────────────────────────────────────────────────
    show_title = True              # E1/E2 etc. carry context in titles
    out_fmt    = ['pdf', 'png']
    dpi        = 300
    out_dir    = None

    # ─── Per-panel overrides ─────────────────────────────────────────────
    # Each key (E1, E2, C, M1, M2, T) → dict of PlotStyle field names → values.
    # Anything not listed inherits the class-level default above.
    # Full field catalogue + recipes + warnings: see STYLE_GUIDE.md.
    # PANELS = {
    #     'E1': {
    #         'fig_w': 7.0, 'fig_h': 3.8,
    #     },
    #     'E2': {
    #         'fig_w': 7.0, 'fig_h': 3.6,
    #         'legend_ncol': 2,
    #     },
    #     'C': {
    #         'fig_w': 7.0, 'fig_h': 4.4,
    #         'legend_ncol': 3,
    #         'legend_bbox_to_anchor': (0.5, -0.22),
    #     },
    #     'M1': {
    #         'fig_w': 7.0, 'fig_h': 4.2,
    #         'legend_loc': 'upper right',
    #         'legend_ncol': 1,
    #         'legend_bbox_to_anchor': None,   # anchor inside axes
    #         'audit_loc': 'axes_top',
    #     },
    #     'M2': {
    #         'fig_w': 7.0, 'fig_h': 4.6,
    #         'legend_ncol': 3,
    #         'legend_bbox_to_anchor': (0.5, -0.22),
    #         'audit_loc': 'axes_top',
    #     },
    #     'T': {
    #         'fig_w': 7.0, 'fig_h': 3.2,
    #         'audit_loc': 'axes_top',
    #     },
    # }

    PANELS = {
        # 'E1': {
        #     'fig_w': 7.0, 'fig_h': 7.0,
        #     # Legend: inside axes, upper-right (see STYLE_GUIDE §5)
        #     'legend_loc': 'upper right',
        #     'legend_bbox_to_anchor': (0.5, 0.5),
        #     'legend_ncol': 1,
        #     # Audit: page bottom-left. For top instead, use y≈0.995 + va='top'.
        #     'audit_loc': 'figure',
        #     'audit_x': 0.01, 'audit_y': 0.005,
        #     'audit_ha': 'left', 'audit_va': 'bottom',
        #     'audit_size_delta': -3,
        #     # Lift x-label off the page-bottom edge (carve out 12% from below).
        #     'bottom_margin': 0.12,
        # },
        'E1': {
            'fig_w': 7.0, 'fig_h': 7.0,
            # Legend: inside axes, upper-right (see STYLE_GUIDE §5)
            'legend_loc': 'upper right',
            'legend_bbox_to_anchor': (0.5, 0.6),
            'legend_ncol': 1,
            # Audit: page bottom-left. For top instead, use y≈0.995 + va='top'.
            'audit_loc': 'figure',
            'audit_x': 0.01, 'audit_y': 0.005,
            'audit_ha': 'left', 'audit_va': 'bottom',
            'audit_size_delta': -3,
            # Lift x-label off the page-bottom edge (carve out 12% from below).
            'bottom_margin': 0.12,
        },
        'E2': {
            'fig_w': 7.0, 'fig_h': 7.0,
            # Legend: inside axes, lower-left (see STYLE_GUIDE §5)
            'legend_loc': 'lower left',
            'legend_bbox_to_anchor': (0.02, 0.02),
            'legend_ncol': 1,
            # Audit: left-aligned at page bottom-left to avoid x-label overlap.
            'audit_loc': 'figure',
            'audit_x': 0.01, 'audit_y': 0.005,
            'audit_ha': 'left', 'audit_va': 'bottom',
            'audit_size_delta': -3,
            'bottom_margin': 0.12,
        },
        'E3': {
            'fig_w': 7.0, 'fig_h': 7.0,
            'legend_loc': 'lower left',
            'legend_bbox_to_anchor': (0.02, 0.02),
            'legend_ncol': 1,
            'audit_loc': 'figure',
            'audit_x': 0.01, 'audit_y': 0.005,
            'audit_ha': 'left', 'audit_va': 'bottom',
            'audit_size_delta': -3,
            'bottom_margin': 0.12,
        },
        'C': {
            'fig_w': 7.0, 'fig_h': 4.4,
            'legend_ncol': 3,
            'legend_bbox_to_anchor': (0.5, -0.22),
        },
        # 'M1': {
        #     'fig_w': 7.0, 'fig_h': 4.2,
        #     'legend_loc': 'upper right',
        #     'legend_ncol': 1,
        #     'legend_bbox_to_anchor': None,   # anchor inside axes
        #     'audit_loc': 'axes_top',
        #     'audit_x': 0.01, 'audit_y': 1.02, 'audit_ha': 'left',
        'M1': {
            'fig_w': 7.0, 'fig_h': 4.2,
            'legend_loc': 'upper right',
            'legend_ncol': 1,
            'legend_bbox_to_anchor': None,   # anchor inside axes
            'audit_loc': 'figure',
            'audit_x': 0.5, 'audit_y': 0.005, 'audit_va': 'bottom',
            'audit_size_delta': -3,
            'bottom_margin': 0.12
        },
        'M2': {
            'fig_w': 7.0, 'fig_h': 4.6,
            'legend_ncol': 1,
            'legend_bbox_to_anchor': (0.3, 0.5),
            'audit_loc': 'figure',
            'audit_x': 0.5, 'audit_y': 0.005, 'audit_va': 'bottom',
            'audit_size_delta': -3,
            'bottom_margin': 0.12
        },
        'T': {
            'fig_w': 7.0, 'fig_h': 3.2,
            'audit_loc': 'axes_top',
            'audit_x': 0.01, 'audit_y': 1.02, 'audit_ha': 'left',
        },
    }
    @classmethod
    def for_panel(cls, key: str) -> 'PlotStyle':
        """Return a fresh PlotStyle instance with cls.PANELS[key] applied.

        Fields not present in PANELS[key] inherit from PlotStyle defaults.
        """
        st = cls()
        for field_name, value in cls.PANELS.get(key, {}).items():
            setattr(st, field_name, value)
        return st


# ─────────────────────────────────────────────────────────────────────────────
# Standard helpers (lab-plot-style §6)
# ─────────────────────────────────────────────────────────────────────────────

def _panel_label(ax, label, st):
    """Draw '(label)' at axes-relative (panel_label_x, panel_label_y).

    Default placement is inside upper-left (axes coords 0.02, 0.97).
    Override via PANEL_STYLES: panel_label_x/y/ha/va, or set
    panel_label=False to suppress.
    """
    if not st.panel_label:
        return
    text = st.panel_label_text if st.panel_label_text is not None else label
    ax.text(st.panel_label_x, st.panel_label_y, '(' + text + ')',
            transform=ax.transAxes,
            fontsize=st.panel_size, fontweight=st.panel_weight,
            va=st.panel_label_va, ha=st.panel_label_ha)


def _apply_style(fig, axes_list, st):
    mpl.rcParams['font.family'] = st.font_family
    for ax in axes_list:
        ax.tick_params(labelsize=st.tick_size)
        ax.xaxis.label.set_size(st.label_size)
        ax.yaxis.label.set_size(st.label_size)
        if ax.get_title():
            ax.title.set_fontsize(st.title_size)
    # When any page-margin override is set, pass it via tight_layout(rect=...)
    # so that colorbars/legends/etc. are repositioned together with the main
    # axes. `subplots_adjust` would shift only the main axes, leaving colorbars
    # mis-aligned (M2 has 2 colorbars; this matters).
    has_margin = any(m is not None for m in (st.bottom_margin, st.top_margin,
                                             st.left_margin, st.right_margin))
    if has_margin:
        rect = (st.left_margin   if st.left_margin   is not None else 0.0,
                st.bottom_margin if st.bottom_margin is not None else 0.0,
                st.right_margin  if st.right_margin  is not None else 1.0,
                st.top_margin    if st.top_margin    is not None else 1.0)
        fig.tight_layout(pad=0.4, rect=rect)
    else:
        fig.tight_layout(pad=0.4)


def _place_legend(ax, st):
    """Apply PlotStyle legend_* fields to ax.legend()."""
    kwargs = dict(loc=st.legend_loc,
                  ncol=st.legend_ncol,
                  fontsize=st.legend_size,
                  framealpha=st.legend_framealpha)
    # bbox_to_anchor only makes sense when anchoring outside axes
    if st.legend_bbox_to_anchor is not None:
        kwargs['bbox_to_anchor'] = st.legend_bbox_to_anchor
    if st.legend_handlelength  is not None: kwargs['handlelength']  = st.legend_handlelength
    if st.legend_handletextpad is not None: kwargs['handletextpad'] = st.legend_handletextpad
    if st.legend_labelspacing  is not None: kwargs['labelspacing']  = st.legend_labelspacing
    if st.legend_borderpad     is not None: kwargs['borderpad']     = st.legend_borderpad
    if st.legend_borderaxespad is not None: kwargs['borderaxespad'] = st.legend_borderaxespad
    leg = ax.legend(**kwargs)
    leg.set_in_layout(True)
    return leg


def _place_audit(fig, ax, audit, st):
    """Draw the audit strip.

    Honors per-panel fields (override via PlotStyle.PANELS):
      audit_loc        — 'figure' | 'axes_top' | 'off'
      audit_x, audit_y — anchor point ('figure': page coords [0..1];
                         'axes_top': axes coords [0..1+])
      audit_ha, audit_va  — text alignment
      audit_size_delta    — font size delta vs annot_size (clamped ≥ 5)
      audit_color         — text color
    """
    if (not st.audit_show) or st.audit_loc == 'off' or not audit:
        return
    valid = ('figure', 'axes_top', 'off')
    if st.audit_loc not in valid:
        raise ValueError(
            f"audit_loc={st.audit_loc!r} not in {valid}. "
            "Use 'figure' for page coords (top/bottom controlled by audit_y "
            "+ audit_va), 'axes_top' for axes-relative, or 'off'.")
    fontsize = max(st.annot_size + st.audit_size_delta, 5)
    if st.audit_loc == 'axes_top':
        ax.text(st.audit_x, st.audit_y, audit, transform=ax.transAxes,
                ha=st.audit_ha, va=st.audit_va,
                fontsize=fontsize, color=st.audit_color)
    else:   # 'figure' — fig coords [0..1]
        fig.text(st.audit_x, st.audit_y, audit,
                 ha=st.audit_ha, va=st.audit_va,
                 fontsize=fontsize, color=st.audit_color)


def _save(fig, fname, st, out_dir):
    """Save figure. When *_margin is set, bbox_inches='tight' is disabled —
    otherwise the deliberate page-margin we just carved out via
    tight_layout(rect=...) gets cropped right back off, which un-does the
    visual effect (axes drift to figure center, colorbars mis-align).
    """
    has_margin = any(getattr(st, m) is not None for m in
                     ('bottom_margin', 'top_margin',
                      'left_margin',   'right_margin'))
    bbox = None if has_margin else 'tight'
    saved = []
    for fmt in st.out_fmt:
        path = os.path.join(out_dir, fname + '.' + fmt)
        fig.savefig(path, dpi=st.dpi, bbox_inches=bbox)
        saved.append(path)
        print('  saved -> ' + path)
    return saved


def _audit_text(run_timestamp: str, postplot_version: str, cfg) -> str:
    return ('run: BO_pump_GPR_' + str(run_timestamp) +
            '  |  postplot: ' + postplot_version +
            '  |  eta_fit_upper=' + f'{cfg.eta_fit_upper:+.2f}' +
            '  band=' + f'{cfg.eta_noise_plateau_band_V:.2f}')


# ─────────────────────────────────────────────────────────────────────────────
# LBL constants (lab-pump-measurement §11.1; lab-plot-style §9)
# ─────────────────────────────────────────────────────────────────────────────

LBL_VXIT = r'$V_{\mathrm{exit}}$ (V)'
LBL_VENT = r'$V_{\mathrm{ent}}$ (V)'
LBL_ETA  = r'$\eta = \log_{10}|n-1|$'
LBL_N    = r'$\langle n \rangle$'


# ─────────────────────────────────────────────────────────────────────────────
# fig_E1 — η_E extrapolation (schoinas-eta-extrapolation §5; post-plot §6.1)
# ─────────────────────────────────────────────────────────────────────────────

def fig_E1_eta_extrapolation(V_bo: np.ndarray,
                             eta_bo: np.ndarray,
                             V_grid: np.ndarray,
                             eta_grid: np.ndarray,
                             fit_result: SchoinasFitResult,
                             eta_noise: float,
                             eta_fit_upper: float,
                             eta_fit_lower: float,
                             source_label: str,
                             audit: str,
                             st,
                             best_V_ent: Optional[float] = None,
                             V_p_used: Optional[float] = None,
                             sigma_used: bool = False) -> plt.Figure:
    """Plot η vs V_exit with Schoinas fit + asymptotes + η_noise.

    V_bo/eta_bo: BO-sampled measurement points (context scatter).
    V_grid/eta_grid: GPR grid source (fit target when source_label='GPR grid').
    fit_result: whichever source was fit.
    """
    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))

    # ── data points ────────────────────────────────────────────────────────
    if V_bo is not None and len(V_bo) > 0:
        ax.plot(V_bo, eta_bo, 'o', color='#555555',
                ms=st.ms_bo, mec='none',
                label=r'BO-sampled $\eta$ data')
    if V_grid is not None and len(V_grid) > 0:
        ax.plot(V_grid, eta_grid, 's', color='#4a6fa5',
                ms=st.ms_gpr_grid, mec='black', mew=0.25, alpha=0.85,
                label=r'GPR grid $\eta$ data')

    # ── fit-point highlight ────────────────────────────────────────────────
    if fit_result.success and fit_result.fit_mask is not None:
        Vs, es = (V_grid, eta_grid) if source_label == 'GPR grid' else (V_bo, eta_bo)
        Vs = np.asarray(Vs); es = np.asarray(es)
        m = fit_result.fit_mask
        ax.plot(Vs[m], es[m], 'o', mfc='none', mec='red',
                ms=st.ms_fit_pts, mew=1.2,
                label=f'fit points (N={fit_result.n_fit_pts})')

    # ── η_noise + fit band ─────────────────────────────────────────────────
    ax.axhline(eta_noise, ls='--', color='gray', lw=st.lw_asym,
               label=rf'$\eta_{{\mathrm{{noise}}}} = {eta_noise:+.2f}$')
    ax.axhline(eta_fit_upper, ls=':', color='#666666',
               lw=st.lw_asym - 0.2,
               label=rf'ETA_FIT_UPPER $={eta_fit_upper:+.2f}$')
    ax.axhline(eta_fit_lower, ls=':', color='#aa8833',
               lw=st.lw_asym - 0.2,
               label=rf'ETA_FIT_LOWER $={eta_fit_lower:+.2f}$')

    # ── Schoinas fit curve + asymptotes ────────────────────────────────────
    if fit_result.success:
        ax.plot(fit_result.V_model, fit_result.eta_model,
                '-', color='red', lw=st.lw_model,
                label=f'Schoinas fit (RMS={fit_result.rms:.3f})')
        a1, b1, a2, b2 = fit_result.popt
        Vm = fit_result.V_model
        ax.plot(Vm, a1 * Vm + b1, '--', color='red', lw=st.lw_asym,
                label=rf'loading ($a_1={a1:+.1f}$)')
        ax.plot(Vm, a2 * Vm + b2, '--', color='red', lw=st.lw_asym,
                label=rf'emission ($a_2={a2:+.1f}$)')
        ax.plot([fit_result.V_opt], [fit_result.eta_E_min],
                marker='*', color='darkred', ms=st.ms_best,
                mec='black', mew=0.4, ls='',
                label=(rf'$\eta_E^{{\min}}={fit_result.eta_E_min:+.2f}$ '
                       rf'@ {fit_result.V_opt * 1000:.1f} mV'))

    # ── axes + title ───────────────────────────────────────────────────────
    ax.set_xlabel(LBL_VXIT)
    ax.set_ylabel(LBL_ETA)
    if st.show_title:
        title_main = f'η_E extrapolation ({source_label} source'
        if sigma_used:
            title_main += ', σ-gated'
        title_main += ')'
        ctx_bits = []
        if best_V_ent is not None:
            ctx_bits.append(rf'best $V_{{\mathrm{{ent}}}}={best_V_ent:+.4f}$ V')
        if V_p_used is not None:
            ctx_bits.append(rf'$V_p={V_p_used:+.4f}$ V')
        if ctx_bits:
            ax.set_title(title_main + '\n' + '   '.join(ctx_bits),
                         fontsize=st.title_size, pad=st.title_pad)
        else:
            ax.set_title(title_main, fontsize=st.title_size, pad=st.title_pad)

    # ── y-limits (clip extrapolated asymptotes) ────────────────────────────
    y_lo_candidates = [eta_noise - 0.3, eta_fit_lower - 0.3]
    if fit_result.success:
        y_lo_candidates.append(fit_result.eta_E_min - 0.3)
    y_hi_candidates = [eta_fit_upper + 0.3, 0.2]
    ax.set_ylim(min(y_lo_candidates), max(y_hi_candidates))

    _panel_label(ax, 'E1', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_E2 — Schoinas vs phenomenological sigmoid-plateau (post-plot §6.2)
#
# NOTE: Prior to v7.2 this was named fig_E2_schoinas_vs_seo; the sigmoid
# fit was incorrectly attributed to "Seo 2014 Eq.(1)". The actual Seo 2014
# Eq.(1) is the decay-cascade Gumbel-sum (see fig_E3).
# ─────────────────────────────────────────────────────────────────────────────

def fig_E2_schoinas_vs_sigmoid(V_data: np.ndarray,
                               n_data: np.ndarray,
                               schoinas: SchoinasFitResult,
                               sigmoid: SigmoidPlateauFitResult,
                               eta_noise: float,
                               audit: str,
                               st) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))

    eta_data = compute_eta(n_data)

    ax.plot(V_data, eta_data, 'o', color='#888888',
            ms=st.ms_bo, mec='none',
            label=r'BO-sampled $\eta$ data')

    if schoinas.success:
        ax.plot(schoinas.V_model, schoinas.eta_model,
                '-', color='red', lw=st.lw_model,
                label=rf'Schoinas ($\eta_E^{{\min}}={schoinas.eta_E_min:+.2f}$, '
                      rf'RMS={schoinas.rms:.3f})')
        ax.plot([schoinas.V_opt], [schoinas.eta_E_min],
                marker='*', ls='', color='darkred',
                ms=st.ms_schoinas_star, mec='black', mew=0.4,
                label=r'Schoinas $\eta_E^{\min}$')

    if sigmoid.success:
        ax.plot(sigmoid.V_model, sigmoid.eta_model,
                '-', color='blue', lw=st.lw_model,
                label=r'Sigmoid plateau (6-param) ($\eta_E^{\min}$='
                      f'{sigmoid.eta_E_min:+.2f}, RMS_n={sigmoid.rms:.3f})')
        ax.plot([sigmoid.V_opt], [sigmoid.eta_E_min],
                marker='*', ls='', color='darkblue',
                ms=st.ms_sigmoid_star, mec='black', mew=0.4,
                label=r'Sigmoid plateau $\eta_E^{\min}$')
    else:
        ax.text(0.02, 0.02, 'Sigmoid fit: ' + sigmoid.message,
                transform=ax.transAxes, fontsize=st.annot_size - 1,
                color='blue', ha='left', va='bottom')

    ax.axhline(eta_noise, ls='--', color='gray', lw=st.lw_asym,
               label=rf'$\eta_{{\mathrm{{noise}}}} = {eta_noise:+.2f}$')

    ax.set_xlabel(LBL_VXIT)
    ax.set_ylabel(LBL_ETA)
    y_lo = min(eta_noise - 0.3,
               (schoinas.eta_E_min - 0.3) if schoinas.success else eta_noise - 0.3,
               (sigmoid.eta_E_min - 0.3) if sigmoid.success else eta_noise - 0.3)
    ax.set_ylim(y_lo, 0.2)

    if st.show_title:
        ax.set_title('Schoinas vs sigmoid-plateau (6-param phenomenological)',
                     fontsize=st.title_size, pad=st.title_pad)

    _panel_label(ax, 'E2', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_E3 — Schoinas vs Seo 2014 Eq.(1) decay-cascade
#
# The decay-cascade curve IS the actual Seo 2014 Eq.(1) (Kashcheyevs Gumbel-sum
# form, 4-param `(a, b, Γ₁, Γ₂)`, FoM δ₂ = ln(Γ₂/Γ₁)).
# ─────────────────────────────────────────────────────────────────────────────

def fig_E3_schoinas_vs_decay_cascade(V_data: np.ndarray,
                                     n_data: np.ndarray,
                                     schoinas: SchoinasFitResult,
                                     decay_cascade: Optional[DecayCascadeFitResult],
                                     eta_noise: float,
                                     audit: str,
                                     st) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))

    eta_data = compute_eta(n_data)

    ax.plot(V_data, eta_data, 'o', color='#888888',
            ms=st.ms_bo, mec='none',
            label=r'BO-sampled $\eta$ data')

    if schoinas.success:
        ax.plot(schoinas.V_model, schoinas.eta_model,
                '-', color='red', lw=st.lw_model,
                label=rf'Schoinas ($\eta_E^{{\min}}={schoinas.eta_E_min:+.2f}$, '
                      rf'RMS={schoinas.rms:.3f})')
        ax.plot([schoinas.V_opt], [schoinas.eta_E_min],
                marker='*', ls='', color='darkred',
                ms=st.ms_schoinas_star, mec='black', mew=0.4)

    if decay_cascade is not None and decay_cascade.success:
        d2 = decay_cascade.delta2 if decay_cascade.delta2 is not None else float('nan')
        ax.plot(decay_cascade.V_model, decay_cascade.eta_model,
                '-', color='green', lw=st.lw_model,
                label=r'Seo 2014 Eq.(1), decay-cascade '
                      rf'($\eta_E^{{\min}}={decay_cascade.eta_E_min:+.2f}$, '
                      rf'$\delta_2={d2:.2f}$, RMS_n={decay_cascade.rms:.3f})')
        ax.plot([decay_cascade.V_opt], [decay_cascade.eta_E_min],
                marker='*', ls='', color='darkgreen',
                ms=st.ms_decay_star, mec='black', mew=0.4)
    elif decay_cascade is not None:
        ax.text(0.02, 0.06, 'Decay-cascade fit: ' + decay_cascade.message,
                transform=ax.transAxes, fontsize=st.annot_size - 1,
                color='green', ha='left', va='bottom')

    ax.axhline(eta_noise, ls='--', color='gray', lw=st.lw_asym,
               label=rf'$\eta_{{\mathrm{{noise}}}} = {eta_noise:+.2f}$')

    ax.set_xlabel(LBL_VXIT)
    ax.set_ylabel(LBL_ETA)
    y_lo_candidates = [eta_noise - 0.3]
    if schoinas.success:
        y_lo_candidates.append(schoinas.eta_E_min - 0.3)
    if decay_cascade is not None and decay_cascade.success:
        y_lo_candidates.append(decay_cascade.eta_E_min - 0.3)
    ax.set_ylim(min(y_lo_candidates), 0.2)

    if st.show_title:
        ax.set_title('Schoinas vs Seo 2014 Eq.(1) (decay-cascade)',
                     fontsize=st.title_size, pad=st.title_pad)

    _panel_label(ax, 'E3', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_M1 — 2D η_E map (post-plot §6.3)
# ─────────────────────────────────────────────────────────────────────────────

def fig_M1_eta_2d(eta_map: pd.DataFrame,
                  best_V_ent: float,
                  best_V_exit: float,
                  eta_noise: float,
                  audit: str,
                  st) -> plt.Figure:
    V_ent_vals  = eta_map.index.to_numpy(dtype=float)
    V_exit_vals = eta_map.columns.to_numpy(dtype=float)
    Z = eta_map.to_numpy(dtype=float)

    finite = Z[np.isfinite(Z)]
    vmax = -0.5
    vmin = float(min(np.nanmin(finite) if finite.size else -3.0,
                     eta_noise - 0.2))

    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))

    extent = [V_exit_vals.min(), V_exit_vals.max(),
              V_ent_vals.min(), V_ent_vals.max()]
    im = ax.imshow(Z, origin='lower', aspect='auto',
                   extent=extent, vmin=vmin, vmax=vmax,
                   cmap='RdYlGn_r', interpolation='nearest')

    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label(LBL_ETA, fontsize=st.label_size)
    cbar.ax.tick_params(labelsize=st.cbar_size)

    try:
        VE, VX = np.meshgrid(V_exit_vals, V_ent_vals)
        cs = ax.contour(VE, VX, Z, levels=[eta_noise],
                        colors='white', linewidths=st.lw_contour,
                        linestyles='--')
        ax.clabel(cs, inline=True, fontsize=st.annot_size - 1,
                  fmt={eta_noise: r'$\eta_{\mathrm{noise}}$'})
    except Exception:
        pass

    ax.plot([best_V_exit], [best_V_ent], marker='*', ls='',
            color='yellow', mec='black', mew=0.6, ms=st.ms_best,
            label=(rf'best: $V_{{\mathrm{{exit}}}}={best_V_exit * 1000:.1f}$ mV, '
                   rf'$V_{{\mathrm{{ent}}}}={best_V_ent * 1000:.1f}$ mV'))

    ax.set_xlabel(LBL_VXIT)
    ax.set_ylabel(LBL_VENT)
    if st.show_title:
        ax.set_title('2D η map', fontsize=st.title_size, pad=st.title_pad)

    _panel_label(ax, 'M1', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_M2 — BO trajectory + phase4 overlay on η map (post-plot §6.4)
# ─────────────────────────────────────────────────────────────────────────────

def fig_M2_bo_trajectory(eta_map: pd.DataFrame,
                         phase2_bo: Optional[pd.DataFrame],
                         phase4_pumpmap: Optional[pd.DataFrame],
                         best_V_ent: float,
                         best_V_exit: float,
                         audit: str,
                         st) -> plt.Figure:
    V_ent_vals  = eta_map.index.to_numpy(dtype=float)
    V_exit_vals = eta_map.columns.to_numpy(dtype=float)
    Z = eta_map.to_numpy(dtype=float)
    finite = Z[np.isfinite(Z)]
    vmin = float(np.nanmin(finite) if finite.size else -3.0)
    vmax = -0.5

    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))
    extent = [V_exit_vals.min(), V_exit_vals.max(),
              V_ent_vals.min(), V_ent_vals.max()]
    im = ax.imshow(Z, origin='lower', aspect='auto', extent=extent,
                   vmin=vmin, vmax=vmax, cmap='RdYlGn_r',
                   interpolation='nearest', alpha=0.55)
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label(LBL_ETA, fontsize=st.label_size)
    cbar.ax.tick_params(labelsize=st.cbar_size)

    if phase2_bo is not None and len(phase2_bo) > 0:
        iters = np.arange(len(phase2_bo))
        ax.scatter(phase2_bo['V_exit'].to_numpy(),
                   phase2_bo['V_ent'].to_numpy(),
                   c=iters, cmap='viridis',
                   s=st.ms_bo_history, edgecolor='black', linewidth=0.3,
                   label=f'BO history (n={len(phase2_bo)}, viridis early→late)')

    if phase4_pumpmap is not None and len(phase4_pumpmap) > 0:
        for stage, marker, color in [('lhs', 'v', '#1f77b4'),
                                     ('rhs', '^', '#9467bd'),
                                     ('top', 's', '#2ca02c'),
                                     ('bot', 'D', '#e377c2'),
                                     ('center', 'x', '#7f7f7f'),
                                     ('gpr_grid', '.', '#17becf')]:
            m = phase4_pumpmap['stage'].astype(str) == stage
            if not m.any():
                continue
            ax.plot(phase4_pumpmap.loc[m, 'V_exit'].to_numpy(),
                    phase4_pumpmap.loc[m, 'V_ent'].to_numpy(),
                    marker=marker, ls='', ms=st.ms_phase4, color=color,
                    mec='black', mew=0.2,
                    label=f'phase4 {stage} (n={int(m.sum())})')

    ax.plot([best_V_exit], [best_V_ent], marker='*', ls='',
            color='yellow', mec='black', mew=0.6, ms=st.ms_best,
            label=r'best point')

    ax.set_xlabel(LBL_VXIT)
    ax.set_ylabel(LBL_VENT)
    if st.show_title:
        ax.set_title('BO trajectory + phase4 overlay',
                     fontsize=st.title_size, pad=st.title_pad)

    _panel_label(ax, 'M2', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_C — I vs V_exit trace at best_V_ent (notebook panel (c) reproduction)
# Source: phase3_map_*.csv sliced by |V_ent - best_V_ent| ≤ v_ent_slice_tol.
# Dual axis: left = I (nA); right = <n> = I / (e·f) (I_nA / I_ref_nA).
# ─────────────────────────────────────────────────────────────────────────────

def fig_C_iv_trace(V_gpr_V: np.ndarray,
                   I_gpr_mean_nA: np.ndarray,
                   I_gpr_std_nA: Optional[np.ndarray],
                   V_bo_V: np.ndarray,
                   I_bo_nA: np.ndarray,
                   best_V_ent: float,
                   best_V_exit: float,
                   V_p_used: float,
                   I_ref_nA: float,
                   audit: str,
                   st) -> plt.Figure:
    """Reproduces notebook panel (C): I vs V_exit with GPR mean + σ band +
    BO sampling points + n=1/n=2 references.

    All input V arrays are in Volts; axis is rendered in mV to match notebook.
    """
    V_gpr_mV = np.asarray(V_gpr_V) * 1000.0
    V_bo_mV  = np.asarray(V_bo_V)  * 1000.0

    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))

    # GPR ±σ variance band
    if I_gpr_std_nA is not None and np.all(np.isfinite(I_gpr_std_nA)):
        ax.fill_between(V_gpr_mV,
                        I_gpr_mean_nA - I_gpr_std_nA,
                        I_gpr_mean_nA + I_gpr_std_nA,
                        color='#7070ff', alpha=0.18,
                        label=r'GPR $\pm 1\sigma$ variance')

    # GPR mean (thin blue line)
    ax.plot(V_gpr_mV, I_gpr_mean_nA, '-', color='#4040ff',
            lw=st.lw, alpha=0.85,
            label=rf'GPR mean ($V_{{\mathrm{{ent}}}}={best_V_ent:.4f}$V)')

    # BO sampling points (red filled circles)
    ax.plot(V_bo_mV, I_bo_nA, 'o', color='#d62728',
            ms=st.ms_bo_iv, mec='black', mew=0.3,
            label=f'BO sampling pts ({len(V_bo_mV)} pts)',
            ls='')

    # n=1 and n=2 reference currents (cyan / orange, matching notebook)
    ax.axhline(I_ref_nA, ls='--', color='#17becf', lw=st.lw_asym + 0.2,
               label=rf'$n=1$ reference ($I_{{\mathrm{{ref}}}}=ef={I_ref_nA:.4f}$ nA)')
    ax.axhline(2 * I_ref_nA, ls='--', color='#ff9e0a', lw=st.lw_asym,
               label=rf'$n=2$ reference ($2I_{{\mathrm{{ref}}}}={2*I_ref_nA:.4f}$ nA)')

    # I=0 gray dotted (notebook has this thin horizontal)
    ax.axhline(0.0, ls=':', color='#999999', lw=st.lw_asym - 0.3,
               label=r'$I = 0$')

    # Best V_exit vertical marker (carry forward from previous fig_C)
    ax.axvline(best_V_exit * 1000.0, ls='-.', color='gray', lw=st.lw_asym,
               label=rf'best $V_{{\mathrm{{exit}}}}={best_V_exit*1000:.1f}$ mV')

    ax.set_xlabel(r'$V_{\mathrm{exit}}$ (mV)')
    ax.set_ylabel(r'$I$ (nA)')

    # Notebook-matching 2-line panel title (always shown, regardless of
    # st.show_title — this is informational content, not a decoration).
    title_line1 = (rf'(C)  $I$ vs $V_{{\mathrm{{EXIT}}}}$  (BO emphasis)  '
                   rf'at best $V_{{\mathrm{{ENT}}}}={best_V_ent:.4f}$V, '
                   rf'$V_p={V_p_used:.4f}$V')
    title_line2 = r'blue thin = GPR  |  red filled = BO pts'
    ax.set_title(title_line1 + '\n' + title_line2,
                 fontsize=st.title_size, fontweight='bold',
                 color='#223366', pad=8)

    # Secondary y-axis = <n> (carry forward from previous fig_C)
    ax2 = ax.twinx()
    if np.isfinite(I_ref_nA) and I_ref_nA != 0:
        lo, hi = ax.get_ylim()
        ax2.set_ylim(lo / I_ref_nA, hi / I_ref_nA)
    ax2.set_ylabel(LBL_N, fontsize=st.label_size)
    ax2.tick_params(labelsize=st.tick_size)

    ax.grid(True, alpha=0.25, linestyle='-', lw=0.4)

    _panel_label(ax, 'C', st)
    _place_legend(ax, st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# fig_T — Timing & measurement table (post-plot §6.5)
# ─────────────────────────────────────────────────────────────────────────────

def fig_T_timing_table(summary: dict, audit: str, st) -> plt.Figure:
    timing = (summary or {}).get('timing') or {}
    meas   = (summary or {}).get('measurements') or {}

    phases = ['phase1', 'phase2', 'phase3a', 'phase3', 'phase4']
    rows = []
    for p in phases:
        sec = timing.get(p + '_s')
        n   = meas.get(p)
        rows.append([p,
                     '—' if sec is None else f'{sec:6.1f} s',
                     '—' if n   is None else f'{n}'])
    total_s = timing.get('total_s')
    total_n = meas.get('total')
    total_hms = timing.get('total_hms', '—')
    rows.append(['total',
                 '—' if total_s is None else f'{total_s:6.1f} s  ({total_hms})',
                 '—' if total_n is None else f'{total_n}'])

    fig, ax = plt.subplots(figsize=(st.fig_w, st.fig_h))
    ax.axis('off')

    tbl = ax.table(cellText=rows,
                   colLabels=['phase', 'wall time', 'measurements'],
                   loc='center', cellLoc='center',
                   colWidths=[0.22, 0.38, 0.25])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(st.label_size)
    tbl.scale(1.0, 1.6)

    if st.show_title:
        ax.set_title('Run timing & measurements',
                     fontsize=st.title_size, pad=st.title_pad)

    _panel_label(ax, 'T', st)
    _place_audit(fig, ax, audit, st)
    _apply_style(fig, [ax], st)
    return fig
