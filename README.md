# Changelog

## v2.1 (2026-07-24) — this record
- Recalibrated congestion-class thresholds from fixed values (0.15/0.35/0.55) to empirical quantiles (0.095/0.22/0.365), achieving the intended 47.1/27.9/18.9/6.0% distribution (severe class: 6,344 samples vs 40 in v2).
- Only the `congestion_class` column differs from v2 (42.1% of rows reclassified); all 26 other columns are bit-identical.
- Notebook cell 6 and header updated accordingly; regeneration verified bit-exact from the included summary files (seed 42).

## v2 (2026-04-24) — this record
- Multi-pollutant air-quality module (PM2.5, NO₂, CO, O₃) with composite US-EPA AQI, replacing the single-pollutant proxy of v1.
- Atmospheric coupling: wind-driven dispersion, diurnal boundary-layer (nocturnal-inversion) profile, precipitation washout.
- Composite congestion index (speed degradation + halting ratio + normalized waiting time) with 4 ordinal classes.
- Extended to 27 columns; 105,120 rows (full year 2023 at 5-min resolution).
- Known deviation from design intent: severe-congestion class ended at 0.04% instead of the targeted ~6%.

## v1 (initial notebook)
- Single-pollutant air-quality proxy; simpler congestion labeling; same network-extraction pipeline.
