# Casablanca-SUMO v2.2

A synthetic one-year, 5-minute resolution traffic, air-quality and meteorology time
series for Casablanca (Morocco), generated from SUMO microsimulations on the real
OpenStreetMap road network, together with the network, the demand files and the
scenario configurations needed to rerun the microsimulations.

- Author: Mehdi Attioui, LMIAD, ENS, Hassan II University of Casablanca
- Version: 2.2 (2026-10-22). Changes from v2.1: see `CHANGELOG.md`
- DOI of this version: 10.5281/zenodo.<DOI-v2.2>
- Licence: CC BY 4.0 (`LICENSE`)

## Contents

| Path | Content |
|---|---|
| `network/casablanca_real.net.xml.gz` | SUMO road network (netconvert 1.26.0 from OpenStreetMap, UTM projection). 34,841 edges, 13,336 junctions, 461 signalised intersections, 1,918 km of edges, 10.6 km × 9.9 km. SUMO reads the gzipped file directly. SHA-256 of the uncompressed file: `819f3120d9f32eaa51b7e949b81511c5a638fa58105ef0fbbb96bc8e04c0e2c2` |
| `routes/*.rou.xml` | One-hour demand for the five archetypes (randomTrips.py + duarouter) |
| `scenarios/*.sumocfg` | SUMO configurations linking network, routes and outputs |
| `output/*_summary.xml` | SUMO summary outputs of the five archetype runs |
| `casablanca_sumo_OSM_365days_v2.2.csv` | Annual table, 105,120 rows (2023, 5-min steps), 27 columns |
| `scripts/make_v2_2_flags.py` | Derives the v2.2 table from v2.1 (calendar-flag corrections only) |
| `CHECKSUMS.sha256` | SHA-256 of every file in this release |

## Demand archetypes

| Archetype | File stem | Departures per hour |
|---|---|---|
| Normal weekday | `normal` | 3,600 |
| Morning rush hour | `rush_hour` | 6,000 |
| Friday midday prayer | `friday_prayer` | 1,125 |
| Ramadan, before iftar | `ramadan_iftar` | 6,546 |
| Night | `night` | 900 |

Run one archetype with:

```
cd scenarios
sumo -c normal.sumocfg
```

## Annual table

The annual table is a scenario-based expansion of the five one-hour archetypes, not a
year of continuous microsimulation. Each 5-minute row is assigned an archetype
(`scenario_sumo`); traffic variables are drawn from the summary output of that
archetype, and air-quality variables are computed from traffic and meteorology.

Calendar columns: `timestamp`, `date`, `hour`, `minute`, `day_of_week` (0 = Monday),
`month`, `is_weekend` (Saturday or Sunday), `is_friday_prayer` (Friday 12:00 to
14:55), `is_ramadan` (Ramadan 1444 AH according to the Moroccan official calendar:
23 March to 21 April 2023).

Traffic: `vehicles_running`, `mean_speed_kmh`, `waiting_time_s`, `halting_vehicles`,
`congestion_level` (composite index), `congestion_class` (0 to 3, empirical-quantile
thresholds 0.095 / 0.22 / 0.365).

Air quality: `pm25_ugm3`, `no2_ugm3`, `co_mgm3`, `o3_ugm3`, `aqi_composite` (US-EPA).

Meteorology: `temperature_c`, `humidity_pct`, `wind_speed_ms`, `precipitation_mm`,
`boundary_layer_m`.

`osm_network` is `real` on every row.

## Known limitations

- The `ramadan_iftar` archetype is assigned to 15:00-17:55 and 20:00-22:55 on every
  day of March and April 2023, including 2,232 rows that fall outside Ramadan 1444.
  Their traffic and air-quality values are those of the Ramadan archetype. Users who
  need Ramadan rows should filter on `is_ramadan == 1` as well as on `scenario_sumo`.
  Correcting the assignment would change the numeric columns and is left to a later
  major version.
- `is_friday_prayer` uses a fixed 12:00-14:55 window rather than a window around the
  local Dhuhr time.
- TODO-AUTHOR: state the time zone of `timestamp` (UTC, or Moroccan civil time
  with or without the change to UTC+0 during Ramadan).

## Citation

Attioui, M. (2026). Casablanca-SUMO v2.2 [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.<DOI-v2.2>
