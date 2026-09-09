"""Shared helpers for the Oaxaca sector transformation scripts.

Design contract for every sector script:
- It is IDEMPOTENT: it sets ABSOLUTE Oaxaca values on its own columns, never
  incrementally scaling whatever is already there. Running it twice = running once.
- It mutates ONLY its sector's columns; all other columns are left untouched.
- It reads and writes the same working Oaxaca CSV (--io), in place.
- Every changed variable is logged to calibration/data_sources.csv via log_change().

The working file starts as a copy of the untouched Mexico national baseline with the
time axis shifted so time_period 0 = 2013 (see shift_time_axis.py); run_all.sh chains
the sector scripts in calibration order.

Benchmark: PECC Oaxaca 2016-2022, Tabla 7 (Inventario estatal de GEI, 2013).
Gate: 17,968 kt CO2e (IPCC categories only), +/-10%. See docs/superpowers/specs/.
"""
import csv
import datetime as dt
import pathlib

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parent.parent.parent          # repo root
CALIB = REPO / "calibration"
BASELINE = CALIB / "reference_mexico" / "sisepuede_adj_inputs_MEX.baseline.csv"
WORKING = REPO / "ssp_modeling" / "input_data" / "sisepuede_adj_inputs_OAX.csv"
DATA_SOURCES = CALIB / "data_sources.csv"
TARGETS = CALIB / "01_oaxaca_data" / "oaxaca_targets_tabla7.csv"

# --- Base year / time axis (decisions D1 + D10) --------------------------------
# The national DB is indexed by CALENDAR year 2015-2070; the Oaxaca run needs
# 2013-2058. D1 originally shifted every `year` label by -2. D10 REPLACED that with a
# true calendar alignment, because the shift also moved dated macro history: the real
# 2020 COVID contraction (-8.7% national GDP) was landing on the label 2018, so the
# model claimed Oaxaca had a recession in 2018 and recovered in 2019-2020.
# Now national year Y stays at year Y; only 2013-2014 are back-filled.
BASE_YEAR = 2013
Y0, Y1 = 2013, 2058
NAT_Y0 = 2015                       # first year present in the national DB
# Real Mexican growth used to back-extend the two missing years (INEGI, constant prices)
NAT_GDP_GROWTH = {2014: 0.028, 2015: 0.033}
NAT_POP_GROWTH = {2014: 0.0111, 2015: 0.0110}

DATA_SOURCES_COLS = ["variable", "subsector", "original_value_mex", "new_value_oax",
                     "year", "method", "source_name", "source_url", "agent", "date"]

# --- Oaxaca reference anchors ---------------------------------------------------
# Sources documented in 01_oaxaca_data/oaxaca_reference_values.csv.
OAX_AREA_HA = 9_395_972.535     # Marco Geoestadistico INEGI, feb 2018
OAX_POP_2013 = 3_861_000        # interpolated INEGI/CONAPO; ~3.9M at intercensal 2015
NATIONAL_POP_2013 = 118_395_000
POP_SHARE = OAX_POP_2013 / NATIONAL_POP_2013          # ~0.0326


def aligned_baseline():
    """National baseline reindexed onto the Oaxaca calendar axis Y0..Y1 (D10).

    Row i corresponds to year Y0+i, so the sector scripts can keep indexing `base`
    positionally against the working frame. The two years the national DB does not
    carry (2013, 2014) are back-filled from its first row: retained technical factors
    vary slowly, and every socioeconomic DRIVER is rebuilt explicitly by
    transform_socioeconomic.py, which back-extends them with real observed growth.
    """
    b = pd.read_csv(BASELINE)
    b = b[(b["year"] >= NAT_Y0) & (b["year"] <= Y1)].sort_values("year")
    pre = [b[b["year"] == NAT_Y0].assign(year=y) for y in range(Y0, NAT_Y0)]
    out = (pd.concat(pre + [b], ignore_index=True)
             .sort_values("year")
             .reset_index(drop=True))
    out["time_period"] = range(len(out))
    return out


def load(io_path):
    return pd.read_csv(io_path)


def save(df, io_path):
    df.to_csv(io_path, index=False)


def baseline_value(df_base, col, year=BASE_YEAR):
    """Original Mexico value of a column at a given (shifted) year, for logging."""
    row = df_base[df_base["year"] == year]
    if col in df_base.columns and len(row):
        return row[col].iloc[0]
    return None


def set_col(df, col, value):
    """Set an entire column to a scalar or an array-like aligned to df rows."""
    if col not in df.columns:
        raise KeyError(f"column not in inputs: {col}")
    df[col] = value
    return df


def scale_cols(df, cols, factor):
    """Multiply a list of columns by a scalar factor. Returns the columns touched.

    NOTE: only safe inside a script that reseeds those columns from the pristine
    baseline first -- otherwise it is not idempotent. Prefer set_col where possible.
    """
    touched = [c for c in cols if c in df.columns]
    for c in touched:
        df[c] = df[c] * factor
    return touched


def cols_for(df, subsector):
    """All input columns belonging to a SISEPUEDE subsector."""
    tag = f"_{subsector}_"
    return [c for c in df.columns
            if tag in c or c.startswith(f"{subsector}_")]


def targets():
    """Tabla 7 targets as a DataFrame."""
    return pd.read_csv(TARGETS)


def target_for(code):
    """Total kt CO2e for one Tabla 7 row code (e.g. '1A1b', '3A1', 'TOTAL_IPCC')."""
    t = targets()
    row = t[t["ipcc_code"] == code]
    if not len(row):
        raise KeyError(f"no Tabla 7 row with ipcc_code={code}")
    return float(row["total_kt"].iloc[0])


def ensure_col(df, col, value):
    """Set a column, CREATING it if the national DB lacks it.

    Necessary because run_baseline.py calls add_missing_cols(df_example, ...), which
    backfills any absent column from SISEPUEDE's example (i.e. another country's)
    defaults. A variable that is absent is therefore NOT zero -- it silently inherits
    a foreign default. Writing it explicitly is the only way to control it.
    """
    df[col] = value
    return df


def log_change(rows):
    """Append rows (dicts with DATA_SOURCES_COLS keys) to data_sources.csv.

    Idempotent-friendly: removes any prior rows for the same (variable, agent)
    before appending, so re-runs don't duplicate.
    """
    today = dt.date.today().isoformat()
    for r in rows:
        r.setdefault("date", today)
        for k in DATA_SOURCES_COLS:
            r.setdefault(k, "")
    existing = []
    if DATA_SOURCES.exists():
        with open(DATA_SOURCES) as fh:
            existing = list(csv.DictReader(fh))
    new_vars = {(r["variable"], r["agent"]) for r in rows}
    existing = [row for row in existing
                if (row.get("variable"), row.get("agent")) not in new_vars]
    with open(DATA_SOURCES, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=DATA_SOURCES_COLS)
        w.writeheader()
        for row in existing + rows:
            w.writerow({k: row.get(k, "") for k in DATA_SOURCES_COLS})


def cli_io():
    """Standard --io argument for sector scripts (defaults to WORKING)."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--io", default=str(WORKING), help="working Oaxaca CSV (in place)")
    return ap.parse_args()
