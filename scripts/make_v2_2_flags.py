"""Derive casablanca_sumo_OSM_365days_v2.2.csv from the v2.1 table.

Only two calendar flags change; every other column and every row order is kept
bit-identical (the script checks this before writing).

  is_weekend  v2.1: Friday and Saturday flagged (Gulf convention), Sunday not.
              v2.2: Saturday and Sunday, the Moroccan weekend.
  is_ramadan  v2.1: all of March and April 2023 (61 days).
              v2.2: 1-30 Ramadan 1444 AH as fixed by the Moroccan Ministry of
                    Habous and Islamic Affairs: 23 March to 21 April 2023
                    inclusive (30 days); Eid al-Fitr fell on 22 April 2023.

Usage: python make_v2_2_flags.py casablanca_sumo_OSM_365days_v2.1.csv \
                                 casablanca_sumo_OSM_365days_v2.2.csv
"""
import sys
import datetime as dt
import pandas as pd

RAMADAN_1444_MA = (dt.date(2023, 3, 23), dt.date(2023, 4, 21))  # inclusive


def main(src, dst):
    raw = pd.read_csv(src, dtype=str, keep_default_na=False)
    ts = pd.to_datetime(raw["timestamp"])
    out = raw.copy()
    out["is_weekend"] = ts.dt.dayofweek.isin([5, 6]).astype(int).astype(str)
    d = ts.dt.date
    out["is_ramadan"] = ((d >= RAMADAN_1444_MA[0]) & (d <= RAMADAN_1444_MA[1])).astype(int).astype(str)

    changed = [c for c in raw.columns if not raw[c].equals(out[c])]
    assert set(changed) <= {"is_weekend", "is_ramadan"}, changed
    for c in changed:
        n = int((raw[c] != out[c]).sum())
        print(f"{c}: {n} of {len(raw)} rows changed")
    out.to_csv(dst, index=False, lineterminator="\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
