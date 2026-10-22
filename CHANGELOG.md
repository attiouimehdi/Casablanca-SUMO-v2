# Changelog

## v2.2 (2026-10-22)
- Added the road network `network/casablanca_real.net.xml.gz`. It was listed in the
  v2.1 checksum manifest but absent from the published repository. The uncompressed
  file has SHA-256 `819f3120d9f32eaa51b7e949b81511c5a638fa58105ef0fbbb96bc8e04c0e2c2`
  (netconvert 1.26.0, generated 2026-04-24). The gzipped file is new and has a new
  checksum.
- Corrected `is_weekend`: v2.1 flagged Friday and Saturday; v2.2 flags Saturday and
  Sunday, the Moroccan weekend (30,240 rows changed). Friday-prayer rows are no
  longer flagged as weekend.
- Corrected `is_ramadan`: v2.1 flagged all of March and April 2023; v2.2 flags
  Ramadan 1444 AH as set by the Moroccan Ministry of Habous and Islamic Affairs,
  23 March to 21 April 2023 inclusive (8,928 rows changed).
- Renamed the table to `casablanca_sumo_OSM_365days_v2.2.csv`. All other columns are
  byte-identical to v2.1; `scripts/make_v2_2_flags.py` regenerates v2.2 from v2.1 and
  checks this.
- Added a full `README.md` with a column dictionary and known limitations.
- Regenerated `CHECKSUMS.sha256` so that it lists exactly the files of the release.
- Removed `SUMO_Casablanca_OSM_Dataset_v2.ipynb` from the manifest: it was listed in
  the v2.1 manifest but not included in the published files.
- Routes, scenario configurations and summary outputs are unchanged from v2.1.

## v2.1 (2026-07-24)
- Recalibrated congestion-class thresholds from fixed values (0.15/0.35/0.55) to empirical quantiles (0.095/0.22/0.365), achieving the intended 47.1/27.9/18.9/6.0% distribution (severe class: 6,344 samples vs 40 in v2).
- Only the `congestion_class` column differs from v2 (42.1% of rows reclassified); all 26 other columns are bit-identical.
- Notebook cell 6 and header updated accordingly; regeneration verified bit-exact from the included summary files (seed 42).

## v2 (2026-04-24)
- Multi-pollutant air-quality module (PM2.5, NO₂, CO, O₃) with composite US-EPA AQI, replacing the single-pollutant proxy of v1.
- Atmospheric coupling: wind-driven dispersion, diurnal boundary-layer (nocturnal-inversion) profile, precipitation washout.
- Composite congestion index (speed degradation + halting ratio + normalized waiting time) with 4 ordinal classes.
- Extended to 27 columns; 105,120 rows (full year 2023 at 5-min resolution).
- Known deviation from design intent: severe-congestion class ended at 0.04% instead of the targeted ~6%.

## v1 (initial notebook)
- Single-pollutant air-quality proxy; simpler congestion labeling; same network-extraction pipeline.
