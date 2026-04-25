# BO+GPR Post-Plot Code (Layer C)

Publication-quality figures from a saved BO+GPR quantum-pump run. Consumes
the CSV/JSON artifacts written by `BO_pump_GPR.ipynb` v7.0+ — the notebook
is **not** re-run.

Specified by `.claude/skills/bo-gpr-post-plot/SKILL.md`. Style and
algorithms inherit from `lab-plot-style`, `schoinas-eta-extrapolation`,
and the memory terminology note (`memory/scientific_references.md`).

## Usage

```bash
# From repo root
python dev_BO_plotting_code/main.py data/BO_pump_GPR_20260422_165539
```

Outputs land in `data/BO_pump_GPR_20260422_165539_postplot/`:

```
fig_C_iv_trace.{png,pdf}              # I vs V_exit trace at best_V_ent (panel c)
fig_E1_eta_extrapolation.{png,pdf}    # η_E extrapolation, GPR-grid source
fig_E2_schoinas_vs_seo.{png,pdf}      # Schoinas vs Seo 2014 Eq.(1) overlay
fig_M1_eta_2d.{png,pdf}               # 2D η_E map
fig_M2_bo_trajectory.{png,pdf}        # BO history + phase4 overlay on map
fig_T_timing_table.{png,pdf}          # Run timing / measurement count table
fit_results_<TS>.json                 # η_noise, popt, η_E^min, RMS
fit_curves_<TS>.csv                   # V, η_schoinas, η_seo, n_seo
postplot_config_<TS>.json             # hyperparameters actually used
```

The original run folder is never modified (§7); `main.py` snapshots and
verifies file mtimes on exit.

## Hyperparameters

All values are CLI-tunable. Defaults match `bo-gpr-post-plot` §3.2 and §4.2
and are validated against run `20260422_165539`.

| CLI flag                   | Default     | Code field                     | Meaning                                                    |
|----------------------------|-------------|--------------------------------|------------------------------------------------------------|
| `--eta-noise-cutoff`       | `-0.6`      | `eta_noise_cutoff_upper`       | Stage-1 upper cutoff (excludes transition region)          |
| `--eta-noise-band`         | `0.3`       | `eta_noise_plateau_band_V`     | Stage-2 median band (η units) around rough estimate        |
| (none)                     | `5`         | `eta_noise_min_samples`        | Stage-2 fallback threshold                                 |
| `--eta-fit-upper`          | `-0.5`      | `eta_fit_upper`                | Schoinas fit data upper bound                              |
| `--eta-fit-lower-margin`   | `0.1`       | `eta_fit_lower_margin`         | Lower bound = η_noise + margin                             |
| `--gpr-sigma-max`          | `0.05`      | `gpr_sigma_max`                | GPR σ gate (applied only when σ column present)            |
| `--v-ent-tol-mV`           | `5.0`       | `v_ent_slice_tol_V`            | ±tolerance for phase4 slice at best_V_ent                  |
| `--no-seo`                 | —           | `seo_fit_enabled`              | Skip Seo 2014 Eq.(1) fit                                   |
| `--no-pdf`                 | —           | `save_pdf`                     | Skip PDF output (PNG only)                                 |

Example sweep:

```bash
python dev_BO_plotting_code/main.py data/BO_pump_GPR_20260422_165539 \
    --eta-fit-upper -0.4 --eta-noise-band 0.4
```

## File Layout

```
dev_BO_plotting_code/
├── load_run.py           # parse run folder into a dict
├── eta_refit.py          # 2-stage η_noise + Schoinas fit
├── seo_fit.py            # Seo 2014 Eq.(1) 6-param sigmoid fit
├── plot_publication.py   # PlotStyle + figure generators (§6)
├── main.py               # CLI entry point
├── README.md             # this file
└── HANDOFF.md            # prior-session context (do not edit)
```

## Terminology (do not regress)

* **Schoinas fit** = Schoinas et al. 2024, *Appl. Phys. Lett. 125, 124001* —
  double-asymptote η model `η(V) = log₁₀(10^(a₁V+b₁) + 10^(a₂V+b₂))`.
* **Seo 2014 Eq.(1)** = Seo et al. 2014 — 6-parameter sigmoid product
  `n(V) = ns + (no − ns) · σ₁(V) · σ₂(V)`.
* Never write unqualified "Eq.(1)". See `memory/scientific_references.md`.

## Regression Targets (run `20260422_165539`)

Per `bo-gpr-post-plot` §9:

| Check                                    | Expected                        |
|------------------------------------------|---------------------------------|
| `η_noise`                                | `∈ [-2.50, -2.40]` (notebook: −2.45) |
| `η_E^min < η_noise`                      | `True` (physical)               |
| `fig_E1` fit pts (GPR grid, σ-gated)     | `∈ [15, 19]` (notebook (d): 17) |
| Schoinas asymptotes                      | `a₁ < 0`, `a₂ > 0`              |
| Original run folder mtime                | unchanged                       |

`main.py` prints this checklist at the end of every run.

## Input Data Contract

Required files in `<run_dir>/` (schema version v7.0):

```
summary_*.json           phase1_V_ent_*.csv    phase3_map_*.csv
config_*.json            phase1_V_exit_*.csv   eta_E_map_*.csv
eta_summary_*.json       phase2_bo_*.csv       phase4_pumpmap_*.csv
```

Optional: `phase3_quality_*.csv`, `phase3a_vp_quality_*.csv`,
`panel_*.png`, `pump_map_13panel_*.png`. See `bo-gpr-post-plot` §2 for
full schema.
