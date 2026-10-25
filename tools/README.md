# tools/ — regeneration and verification scripts for Casablanca-SUMO v2.2

These scripts were added to `main` after the v2.2 release. They do not modify any
file of the release: the data, `README.md`, `CHANGELOG.md` and `CHECKSUMS.sha256` at
the repository root remain identical to the Zenodo record
(doi:10.5281/zenodo.21794792) and to the tag `v2.2`.

| Script | Purpose |
|---|---|
| `generate_annual_table.py` | Stand-alone port of the aggregation and annual-synthesis cells of the original notebook (NumPy seed 42, v2.1 quantile thresholds 0.095 / 0.22 / 0.365). Fed with `output/*_summary.xml`, it produces the v2.1 table. |
| `verify_release_v2_2.py` | Recomputes every statistic quoted in the data descriptor and checks that the regenerated table is byte-identical to `casablanca_sumo_OSM_365days_v2.2.csv`. |
| `make_figures.py` | Figures of the data descriptor. |

Regenerate and check (from the repository root; Python 3, numpy, pandas):

```
python tools/generate_annual_table.py . v2_1.csv
python scripts/make_v2_2_flags.py v2_1.csv v2_2.csv
sha256sum v2_2.csv casablanca_sumo_OSM_365days_v2.2.csv   # identical hashes
python tools/verify_release_v2_2.py .
python tools/make_figures.py --csv casablanca_sumo_OSM_365days_v2.2.csv \
       --net network/casablanca_real.net.xml.gz --outdir figures
```

Checked on 2026-10-25 with Python 3.13 and NumPy 2.5.

## Notes on the v2.2 data (complements the root README)

- Weekend: the generator reduces demand (x0.70-0.85 on running vehicles) on Saturdays
  only. `is_weekend` marks Saturday and Sunday, but Sunday traffic follows the weekday
  profile (mean 404 running vehicles, against 314 on Saturdays and 401-405 from Monday
  to Thursday). Condition on `day_of_week` to study weekend effects.
- `timestamp` is a naive local time on a uniform 5-minute grid with no clock change;
  Morocco's seasonal clock changes, including the return to UTC+0 during Ramadan, are
  not represented.
- The `rush_hour` archetype is scheduled at 07:00-09:55 and 17:00-20:55, and
  `ramadan_iftar` at 15:00-17:55 and 20:00-22:55 on every day of March and April.

Data descriptor: Attioui, M., Lahby, M. (2026). Casablanca-SUMO v2.2: a synthetic
one-year traffic, air-quality and meteorology time series built from SUMO
microsimulations on the real OpenStreetMap network of Casablanca. arXiv:XXXX.XXXXX
