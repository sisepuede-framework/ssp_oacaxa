#!/usr/bin/env python
"""Oaxaca residuos: waso, trww, wali.

Tabla 7 objetivos (kt CO2e):
    4A  Eliminacion de desechos solidos          242   -> waso
    4D1 Aguas residuales domesticas              276   -> trww
    4D2 Aguas residuales industriales            136   -> trww
    Total 4 Desechos                             654

Realidad oaxaquena, opuesta a la de CDMX en varios puntos:
- CDMX exportaba TODOS sus residuos a rellenos sanitarios bien gestionados del
  Edomex. Oaxaca los dispone dentro del estado, pero mayoritariamente en
  TIRADEROS A CIELO ABIERTO, no en rellenos sanitarios: menor factor de correccion
  de metano (MCF 0.5 vs 0.66) porque son someros y aerobios en superficie.
- Generacion per capita muy por debajo del promedio nacional (0.355 t/hab/ano):
  estado rural, disperso y de bajos ingresos, con menor consumo material.
- Cobertura de recoleccion baja: en el 52% rural buena parte de los residuos no
  llega a ningun sitio de disposicion (se quema o entierra en el predio), por lo
  que no genera CH4 anaerobio.

Usage: python transform_waste.py [--io <working OAX csv>]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "waste"

# --- Residuos solidos ----------------------------------------------------------
# Residuos que EFECTIVAMENTE llegan a un sitio de disposicion, no residuos generados.
# Oaxaca tiene una de las coberturas de recoleccion mas bajas del pais: en el 52%
# rural y disperso buena parte de los residuos se quema o entierra en el predio y
# nunca ingresa a un SWDS, por lo que no genera CH4 anaerobio y queda fuera de 4A.
WASTE_PER_CAPITA_TONNE = 0.10
INDUSTRIAL_WASTE_KT_PER_MMM_GDP = 8.0    # nacional 30; Oaxaca casi sin industria pesada
FRAC_INCINERATED = 0.0             # Oaxaca no tiene incineracion ni waste-to-energy
FRAC_LANDFILLED = 0.15             # pocos rellenos sanitarios controlados
FRAC_OPEN_DUMP = 0.85              # tiraderos a cielo abierto (predominan)
MCF_OPEN_DUMP = 0.4                # IPCC: sitio no gestionado somero (<5 m)

# --- Aguas residuales ----------------------------------------------------------
TRWW_FACTOR = 0.55                 # calibrado contra 4D1+4D2 = 412 kt

SRC = ("INEGI Censo Nacional de Gobiernos Municipales (residuos solidos); CONAGUA "
       "Inventario de plantas de tratamiento de aguas residuales; SEMARNAT "
       "Diagnostico Basico para la Gestion Integral de los Residuos; PECC Oaxaca Tabla 7")
URL = "https://www.inegi.org.mx/programas/cngmd/"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    rows = []

    def put(col, val, subsector, method):
        if col not in df.columns:
            return
        orig = base[col].values[0] if col in base.columns else None
        L.set_col(df, col, val)
        rows.append(dict(variable=col, subsector=subsector,
                         original_value_mex=orig, new_value_oax=val,
                         year=L.BASE_YEAR, method=method,
                         source_name=SRC, source_url=URL, agent=AGENT))

    def scale(col, factor, subsector, method):
        if col not in df.columns or col not in base.columns:
            return
        orig = base[col].values[0]
        L.set_col(df, col, base[col].values[:len(df)] * factor)
        rows.append(dict(variable=col, subsector=subsector,
                         original_value_mex=orig, new_value_oax=orig * factor,
                         year=L.BASE_YEAR, method=method,
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- waso: generacion y destino ----------------------------------------
    put("qty_waso_initial_municipal_waste_tonne_per_capita", WASTE_PER_CAPITA_TONNE,
        "waso", "generacion per capita estatal (~0.74 kg/hab/dia)")
    put("qty_waso_industrial_waste_kt_per_mmm_gdp", INDUSTRIAL_WASTE_KT_PER_MMM_GDP,
        "waso", "residuos industriales por PIB (sin industria pesada)")

    for col, val, note in [
        ("frac_waso_non_recycled_incinerated", FRAC_INCINERATED,
         "sin incineracion ni waste-to-energy en el estado"),
        ("frac_waso_non_recycled_landfilled", FRAC_LANDFILLED,
         "pocos rellenos sanitarios controlados"),
        ("frac_waso_non_recycled_open_dump", FRAC_OPEN_DUMP,
         "tiraderos a cielo abierto (predominan en Oaxaca)"),
        ("frac_waso_msw_incinerated_recovered_for_energy", 0.0,
         "sin recuperacion energetica"),
        ("frac_waso_isw_incinerated_recovered_for_energy", 0.0,
         "sin recuperacion energetica"),
        ("mcf_waso_average_open_dump", MCF_OPEN_DUMP,
         "factor de correccion de metano para sitio no gestionado somero"),
    ]:
        put(col, val, "waso", f"destino de residuos: {note}")

    # --- trww/wali: aguas residuales ---------------------------------------
    for col in [c for c in df.columns
                if c.startswith(("gasrf_trww_", "mcf_trww_"))]:
        scale(col, TRWW_FACTOR, "trww",
              f"factor de calibracion x{TRWW_FACTOR} contra Tabla 7 4D1+4D2 "
              "(baja cobertura de alcantarillado y tratamiento)")

    L.save(df, args.io)
    L.log_change(rows)
    print(f"[waste] {WASTE_PER_CAPITA_TONNE} t/hab/ano dispuestos | "
          f"{FRAC_OPEN_DUMP:.0%} tiradero a cielo abierto (MCF {MCF_OPEN_DUMP}), "
          f"sin incineracion (objetivo 4A = 242 kt)")
    print(f"[waste] aguas residuales x{TRWW_FACTOR} (objetivo 4D1+4D2 = 412 kt)")
    print(f"[waste] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
