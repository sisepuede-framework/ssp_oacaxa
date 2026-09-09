#!/usr/bin/env python
"""Print the Oaxaca 2013 validation gate: model output vs PECC Tabla 7.

Reads a `baseline_<label>_emissions_by_subsector.csv` produced by run_baseline.py
(units: Mt CO2e), plus the matching `_wide.csv` for the fields that are not
subsector totals, and compares the base-year row against the Tabla 7 targets.

MAPPING OF 3C1a BIOMASS BURNING -- corrected, see DECISIONS.md D8.
Burning is NOT in lndu. It splits into:
  - forest fires -> emission_co2e_co2_frst_forest_fires, i.e. inside FRST. Gated
    here as its own line against the CO2 part of 3C1a forestal (1,143 kt). The
    122 kt of CH4/N2O from forest fires have no field in SISEPUEDE.
  - crop residues -> emission_co2e_{ch4,n2o}_agrc_biomass_burning. There is no CO2
    counterpart (IPCC 2006: annual crop-residue carbon is cyclical), so agrc is
    gated against the non-CO2 part of 3C1a cultivo only (68 + 253 = 321 kt).
lndu carries LAND-CONVERSION CO2, which has no row in Tabla 7's IPCC total at all
(it appears only in the footnote). It is a memo, like the FRST sink.

Two gates are printed:
  COMPARABLE -- like-for-like, against 16,542 kt = 17,968 - 1,304 (biogenic CO2 of
      crop burning) - 122 (non-CO2 of forest fires). This is the rigorous one.
  BRUTO      -- the headline chosen in D2: everything incl. lndu conversion vs the
      full 17,968 kt. Passes only because lndu (out of Tabla 7's boundary) roughly
      offsets the biogenic CO2 the model cannot emit. Reported for continuity, with
      that offset stated rather than hidden.

Usage:
    python diagnose_2013.py --emis <path to *_emissions_by_subsector.csv>
"""
import argparse
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

FIELD = "emission_co2e_subsector_total_{}"
FIRE_FIELD = "emission_co2e_co2_frst_forest_fires"

# Model line -> Tabla 7 target (kt CO2e). See design spec section 3 and D8.
SUBSECTOR_TARGETS = {
    "entc":       3681,   # 1A1b Refinacion del petroleo (+1A1a generacion = 0)
    "fgtv":         17,   # 1B2aiii.4 Refinacion
    "inen":        636,   # 1A2 Manufactureras y construccion
    "trns":       3641,   # 1A3 Transporte
    "scoe":        501,   # 1A4 Otros sectores
    "ippu":        842,   # 2A1 Cemento + 2F1 HFC
    "lvst":       2627,   # 3A1 Fermentacion enterica
    "lsmm":        418,   # 3A2 Manejo de estiercol
    "soil":       2061,   # 3C4 + 3C5 N2O suelos gestionados
    "agrc":        321,   # 3C7 arroz (68) + parte NO-CO2 de 3C1a cultivo (253)
    "frst_fires": 1143,   # parte CO2 de 3C1a quema en tierras forestales
    "waso":        242,   # 4A Eliminacion de desechos solidos
    "trww":        412,   # 4D1 + 4D2 aguas residuales
    "ccsq":          0,
}

CATEGORIES = {
    "1 Energia":  (["entc", "fgtv", "inen", "trns", "scoe"], 8476),
    "2 IPPU":     (["ippu"], 842),
    "3 AFOLU":    (["lvst", "lsmm", "soil", "agrc", "frst_fires"], 6570),
    "4 Desechos": (["waso", "trww"], 654),
}

TOTAL_TARGET = 17968              # Emisiones de las categorias IPCC (D2)
CO2_BIOGENICO_CULTIVO = 1304      # 3C1a cultivo, CO2: sin campo en SISEPUEDE
NOCO2_INCENDIOS = 122             # 3C1a forestal, CH4+N2O: sin campo en SISEPUEDE
COMPARABLE_TARGET = TOTAL_TARGET - CO2_BIOGENICO_CULTIVO - NOCO2_INCENDIOS
TOL_TOTAL = 0.10
TOL_CATEGORY = 0.15


def gate(model_kt, target_kt, tol):
    """Return (deviation string, pass/fail mark). Absolute-tolerant near zero."""
    if target_kt == 0:
        ok = abs(model_kt) < 50           # 50 kt absolute floor
        return f"abs {model_kt:+.0f}", "OK" if ok else "X"
    dev = (model_kt - target_kt) / target_kt
    # percentages are meaningless on tiny targets; allow a 100 kt absolute pass
    ok = abs(dev) <= tol or abs(model_kt - target_kt) < 100
    return f"{dev:+.0%}", "OK" if ok else "X"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emis", required=True, help="baseline_*_emissions_by_subsector.csv")
    ap.add_argument("--wide", help="baseline_*_wide.csv (default: derived from --emis)")
    ap.add_argument("--year", type=int, default=L.BASE_YEAR)
    args = ap.parse_args()

    df = pd.read_csv(args.emis)
    row = df[df["year"] == args.year]
    if not len(row):
        row = df.iloc[[0]]
        print(f"[warn] year {args.year} not found; using first row "
              f"(year={row['year'].iloc[0]:.0f})")
    row = row.iloc[0]

    wide_path = args.wide or str(args.emis).replace(
        "_emissions_by_subsector.csv", "_wide.csv")
    fires_kt = 0.0
    if pathlib.Path(wide_path).exists():
        dw = pd.read_csv(wide_path)
        rw = dw[dw["year"] == args.year] if "year" in dw.columns else dw.iloc[[0]]
        if len(rw) and FIRE_FIELD in dw.columns:
            fires_kt = float(rw.iloc[0][FIRE_FIELD]) * 1000.0
    else:
        print(f"[warn] wide file not found ({wide_path}); frst_fires = 0")

    def kt(sub):
        if sub == "frst_fires":
            return fires_kt
        f = FIELD.format(sub)
        return float(row[f]) * 1000.0 if f in row.index else 0.0

    print(f"\n=== Oaxaca {args.year} vs PECC Tabla 7 (kt CO2e) ===\n")
    print(f"{'linea':<12}{'model':>10}{'Tabla 7':>10}{'dev':>9}  gate")
    print("-" * 47)
    comparable_model = 0.0
    for sub, tgt in SUBSECTOR_TARGETS.items():
        m_kt = kt(sub)
        comparable_model += m_kt
        dev, mark = gate(m_kt, tgt, TOL_CATEGORY)
        print(f"{sub:<12}{m_kt:>10,.0f}{tgt:>10,.0f}{dev:>9}  {mark}")
    print("-" * 47)

    print(f"\n{'categoria IPCC':<14}{'model':>10}{'Tabla 7':>10}{'dev':>9}  gate (+/-15%)")
    print("-" * 55)
    for name, (subs, tgt) in CATEGORIES.items():
        m_kt = sum(kt(s) for s in subs)
        dev, mark = gate(m_kt, tgt, TOL_CATEGORY)
        print(f"{name:<14}{m_kt:>10,.0f}{tgt:>10,.0f}{dev:>9}  {mark}")
    print("-" * 55)

    dev, mark = gate(comparable_model, COMPARABLE_TARGET, TOL_TOTAL)
    lo, hi = COMPARABLE_TARGET * (1 - TOL_TOTAL), COMPARABLE_TARGET * (1 + TOL_TOTAL)
    print(f"{'COMPARABLE':<14}{comparable_model:>10,.0f}{COMPARABLE_TARGET:>10,.0f}"
          f"{dev:>9}  {mark}   gate +/-10% = [{lo:,.0f}, {hi:,.0f}]")
    print(f"{'':14}{'':>10}{'':>10}{'':>9}       = 17,968 - {CO2_BIOGENICO_CULTIVO:,} "
          f"(CO2 biogenico quema cultivos) - {NOCO2_INCENDIOS} (no-CO2 incendios)")

    lndu_kt = kt("lndu")
    bruto_model = comparable_model + lndu_kt
    dev_b, mark_b = gate(bruto_model, TOTAL_TARGET, TOL_TOTAL)
    lo_b, hi_b = TOTAL_TARGET * (1 - TOL_TOTAL), TOTAL_TARGET * (1 + TOL_TOTAL)
    print(f"{'BRUTO (D2)':<14}{bruto_model:>10,.0f}{TOTAL_TARGET:>10,.0f}"
          f"{dev_b:>9}  {mark_b}   gate +/-10% = [{lo_b:,.0f}, {hi_b:,.0f}]")
    print(f"{'':14}{'':>10}{'':>10}{'':>9}       incluye lndu conversion "
          f"{lndu_kt:+,.0f} kt, que NO tiene renglon en Tabla 7")

    frst_total = kt("frst")
    print(f"\nMEMOS (fuera del gate)")
    print(f"  lndu conversion de uso de suelo : {lndu_kt:>10,.0f} kt   "
          f"Tabla 7 la deja en la nota al pie (hasta -9,000 kt de capacidad), no en el total")
    print(f"  FRST sumidero (sin incendios)   : {frst_total - fires_kt:>10,.0f} kt   "
          f"nota Tabla 7: ~-14,000 kt de absorcion bruta (D3)")
    print(f"  Scope-2 indirectas electricidad : {1223:>10,.0f} kt   "
          f"emision bruta de referencia 19,191 kt (D2)\n")


if __name__ == "__main__":
    main()
