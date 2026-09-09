#!/usr/bin/env python
"""Seed the Oaxaca working CSV from the untouched Mexico national baseline, on the
REAL CALENDAR axis 2013-2058 (decisions D1 + D10).

The national input DB is indexed by calendar year 2015-2070. The Oaxaca benchmark is
the PECC Tabla 7 inventory for 2013, so the run must start two years earlier.

D1 originally did this by shifting every `year` label by -2. That was wrong for any
CALENDAR-DATED series: the national DB carries the observed 2020 COVID contraction
(-8.7% national GDP), and the shift moved it onto the label 2018 -- so the model
claimed Oaxaca had a recession in 2018 (-7.3% transport, -12.2% industry) and
recovered in 2019-2020. Exactly backwards.

D10 replaces the shift with a true alignment: national year Y stays at year Y, and
only the two years the DB does not carry (2013, 2014) are back-filled from its first
row. Retained technical factors (emission factors, energy densities, efficiencies)
vary slowly, so holding them flat for two years is immaterial -- and every
socioeconomic DRIVER is rebuilt explicitly by transform_socioeconomic.py, which
back-extends population and GDP with real observed Mexican growth.

Usage:
    python align_time_axis.py [--out <path>]
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(L.WORKING))
    args = ap.parse_args()

    df = L.aligned_baseline()

    # sanity: the benchmark year must exist at time_period 0, on its real calendar date
    tp0 = df.loc[df["time_period"] == 0, "year"]
    assert len(tp0) == 1 and int(tp0.iloc[0]) == L.BASE_YEAR, (
        f"time_period 0 must be {L.BASE_YEAR}, got {tp0.tolist()}")
    assert int(df["year"].max()) == L.Y1, f"axis must end at {L.Y1}"
    assert len(df) == L.Y1 - L.Y0 + 1, "one row per calendar year"

    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    L.save(df, args.out)
    print(f"[align_time_axis] eje calendario {L.Y0}-{L.Y1} "
          f"(time_period 0 = {L.BASE_YEAR}); {L.Y0}-{L.NAT_Y0 - 1} retro-rellenados "
          f"desde el primer año nacional ({L.NAT_Y0})")
    print(f"[align_time_axis] seeded {len(df)} rows x {df.shape[1]} cols -> {args.out}")


if __name__ == "__main__":
    main()
