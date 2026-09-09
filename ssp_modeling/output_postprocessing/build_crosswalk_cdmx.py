#!/usr/bin/env python
"""Build a CDMX-specific SSP->inventory crosswalk that reconciles EXACTLY.

The generic (Morocco) crosswalk does not map 100% of SISEPUEDE's emission detail
variables, leaving a ~0.2 Mt gap vs the authoritative subsector totals. This
builder guarantees the mapped emissions sum EXACTLY to
``sum(emission_co2e_subsector_total_*)`` by construction:

- For the 10 subsectors whose detail variables reconcile cleanly to their
  ``emission_co2e_subsector_total_<s>`` (inen, scoe, trns, ippu, waso, trww,
  lvst, lsmm, agrc, soil), it maps every detail var, grouped by (subsector, gas)
  — preserving the gas breakdown.
- For the rest (entc, enfu, fgtv, trde, wali, lndu, frst, ccsq), whose detail
  either contains NaNs (entc/fgtv/frst) or does not sum to the total because of
  SISEPUEDE internal land-use netting (lndu/frst), it maps the authoritative
  ``emission_co2e_subsector_total_<s>`` field directly (single row, dominant-gas
  label). This is what makes the total reconcile to the penny.

Output: output_postprocessing/data/invent/crosswalk_cdmx_ssp.csv, also copied to
emission_targets_mex_2022.csv (the filename run_tableau_postprocessing loads).

Usage:
  python build_crosswalk_cdmx.py [--run-dir <sisepuede_results_dir>]
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(__file__)
OUT_DIR = os.path.join(HERE, "data", "invent")

DETAIL = ["inen", "scoe", "trns", "ippu", "waso", "trww", "lvst", "lsmm", "agrc", "soil"]
TOTAL = ["entc", "enfu", "fgtv", "trde", "wali", "lndu", "frst", "ccsq"]

SECTOR = {**{s: "1 - Energy" for s in ["entc", "enfu", "fgtv", "inen", "scoe", "trns", "trde"]},
          "ippu": "2 - IPPU",
          **{s: "3 - AFOLU" for s in ["agrc", "lvst", "lsmm", "soil", "frst", "lndu"]},
          **{s: "4 - Waste" for s in ["waso", "trww", "wali"]}, "ccsq": "5 - CCSQ"}
SUBSEC = {"entc": "1.A.1 - Energy Industries", "inen": "1.A.2 - Manufacturing and Construction",
          "trns": "1.A.3 - Transport", "trde": "1.A.3 - Transport", "scoe": "1.A.4 - Buildings and Other",
          "enfu": "1.A - Fuel Combustion", "fgtv": "1.B - Fugitive Emissions", "ippu": "2 - IPPU",
          "lvst": "3.A.1 - Enteric Fermentation", "lsmm": "3.A.2 - Manure Management",
          "agrc": "3.C - Agriculture (aggregate)", "soil": "3.C.4-6 - Managed Soils",
          "frst": "3.B - Forest Land", "lndu": "3.B - Land Use", "waso": "4.A - Solid Waste Disposal",
          "trww": "4.D - Wastewater", "wali": "4.D - Wastewater (water)", "ccsq": "5 - CCSQ"}
GAS_LABEL = {"entc": "CO2", "enfu": "CO2", "fgtv": "CH4", "trde": "CO2", "wali": "CH4",
             "lndu": "CO2", "frst": "CO2", "ccsq": "CO2"}


def latest_wide():
    runs = sorted(glob.glob(os.path.join(HERE, "..", "ssp_run_output", "sisepuede_results_*")),
                  key=os.path.getmtime)
    wides = glob.glob(os.path.join(runs[-1], "*_WIDE_INPUTS_OUTPUTS.csv"))
    return wides[-1]


def subof(col):
    for s in DETAIL + TOTAL:
        if f"_{s}_" in col:
            return s
    return None


def build(wide_path):
    w = pd.read_csv(wide_path)
    det = [c for c in w.columns if c.startswith("emission_co2e_") and "subsector_total" not in c]
    rows = []
    groups = {}
    for c in det:
        s = subof(c)
        if s in DETAIL:
            gas = c.replace("emission_co2e_", "").split("_")[0].upper()
            groups.setdefault((s, gas), []).append(c)
    for (s, g), cols in sorted(groups.items()):
        if float(np.nansum(np.abs(w[cols].to_numpy()))) <= 1e-9:
            continue
        rows.append({"subsector_ssp": s, "sector": SECTOR[s], "subsector": SUBSEC[s],
                     "gas": g, "ID": f"{SUBSEC[s]}:{g}", "vars": ":".join(sorted(cols))})
    for s in TOTAL:
        tc = f"emission_co2e_subsector_total_{s}"
        if tc in w.columns and float(np.nansum(np.abs(w[tc]))) > 1e-9:
            rows.append({"subsector_ssp": s, "sector": SECTOR[s], "subsector": SUBSEC[s],
                         "gas": GAS_LABEL[s], "ID": f"{SUBSEC[s]}:{GAS_LABEL[s]}", "vars": tc})
    cw = pd.DataFrame(rows)

    # verify exact reconciliation on the baseline, latest year available
    r = w[(w["primary_id"] == 0)].sort_values("time_period").iloc[len(w[w.primary_id == 0]) // 2]
    cw_tot = sum(float(np.nansum([r[v] for v in row["vars"].split(":") if v in w.columns]))
                 for _, row in cw.iterrows())
    auth = float(np.nansum([r[c] for c in w.columns if c.startswith("emission_co2e_subsector_total_")]))
    assert abs(cw_tot - auth) < 1e-4, f"crosswalk {cw_tot} != authoritative {auth}"
    return cw, cw_tot, auth


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    a = ap.parse_args()
    wide = (glob.glob(os.path.join(a.run_dir, "*_WIDE_INPUTS_OUTPUTS.csv"))[-1]
            if a.run_dir else latest_wide())
    cw, cw_tot, auth = build(wide)
    os.makedirs(OUT_DIR, exist_ok=True)
    cw.to_csv(os.path.join(OUT_DIR, "crosswalk_cdmx_ssp.csv"), index=False)
    cw.to_csv(os.path.join(OUT_DIR, "emission_targets_mex_2022.csv"), index=False)
    print(f"crosswalk_cdmx_ssp.csv written: {len(cw)} rows")
    print(f"reconciliation check: crosswalk={cw_tot:.5f}  authoritative={auth:.5f}  "
          f"diff={cw_tot - auth:+.6f}  {'OK EXACT' if abs(cw_tot - auth) < 1e-4 else 'FAIL'}")


if __name__ == "__main__":
    main()
