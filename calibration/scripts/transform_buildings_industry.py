#!/usr/bin/env python
"""Oaxaca energia de edificios e industria: scoe, inen.

Tabla 7 objetivos (kt CO2e):
    1A4 Otros sectores (scoe)                  501
        1A4a Comercial/Institucional            49
        1A4b Residencial GLP                   287
        1A4b Residencial lena                  162   <- CH4 + N2O; el CO2 de biomasa no cuenta
        1A4b Agricola                            2
    1A2 Manufactureras y de construccion (inen) 636
        pulpa/papel 149 - alimentos 93 - minerales no metalicos 392 - resto ~2

Oaxaca tiene el consumo energetico residencial per capita mas bajo del pais: alta
ruralidad (52%), baja penetracion de gas natural (practicamente nula, sin red) y uso
extendido de lena. Por eso las intensidades de consumo se bajan bien por debajo del
promedio nacional en vez de escalarse solo por poblacion.

INEN cae principalmente por efecto de transform_ippu.py, que fija la produccion
industrial estatal: la demanda de energia industrial se calcula por tonelada
producida (energy_tj_per_tonne_production_*). Aqui se ajusta el residuo ligado al PIB.

Usage: python transform_buildings_industry.py [--io <working OAX csv>]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "buildings_industry"

# --- SCOE: intensidades de consumo estacionario --------------------------------
# Factores sobre la intensidad nacional, calibrados contra 1A4 = 501 kt.
SCOE_RESIDENTIAL_HEAT_FACTOR = 0.50    # hogares oaxaquenos: menor consumo, mucha lena
SCOE_RESIDENTIAL_ELEC_FACTOR = 0.45    # menor equipamiento electrodomestico
SCOE_COMMERCIAL_FACTOR = 0.50          # sector comercial pequeno y poco intensivo

# --- INEN: residuo ligado al PIB manufacturero ---------------------------------
# Intensidad energetica de "other product manufacturing", el mayor componente de
# INEN (477 kt de 920). Oaxaca tiene manufactura ligera, artesanal y de pequena
# escala, no la industria mediana que refleja el promedio nacional.
INEN_GDP_ENERGY_FACTOR = 0.40

# Energia agricola dentro de INEN. El valor nacional (106.1 PJ) aplicado a Oaxaca
# generaba 6,361 kt, el 85% de todo INEN. Oaxaca practica agricultura de temporal
# con muy baja mecanizacion y escaso bombeo de riego; ademas Tabla 7 contabiliza
# tractores y maquinaria agricola en 1A3eiii (transporte, 264 kt), no en 1A2, de
# modo que dejarlo alto duplicaria la contabilidad.
INEN_AGRICULTURE_ENERGY_PJ = 2.5

SRC = ("INEGI Encuesta Nacional de Consumo de Energeticos en Viviendas (ENCEVI); "
       "INEGI Censos Economicos Oaxaca; PECC Oaxaca 2016-2022 Tabla 7 (1A2, 1A4)")
URL = "https://www.inegi.org.mx/programas/encevi/2018/"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    rows = []

    def scale(col, factor, subsector, method):
        """Set col to the PRISTINE national value x factor (idempotent)."""
        if col not in df.columns or col not in base.columns:
            return
        orig = base[col].values[0]
        L.set_col(df, col, base[col].values[:len(df)] * factor)
        rows.append(dict(variable=col, subsector=subsector,
                         original_value_mex=orig, new_value_oax=orig * factor,
                         year=L.BASE_YEAR, method=method,
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- SCOE ---------------------------------------------------------------
    scale("consumpinit_scoe_gj_per_hh_residential_heat_energy",
          SCOE_RESIDENTIAL_HEAT_FACTOR, "scoe",
          f"intensidad residencial de calor x{SCOE_RESIDENTIAL_HEAT_FACTOR} "
          "(menor consumo por hogar; alta ruralidad, sin red de gas natural)")
    scale("consumpinit_scoe_gj_per_hh_residential_elec_appliances",
          SCOE_RESIDENTIAL_ELEC_FACTOR, "scoe",
          f"intensidad residencial electrica x{SCOE_RESIDENTIAL_ELEC_FACTOR} "
          "(menor equipamiento de electrodomesticos)")
    for col in ["consumpinit_scoe_tj_per_mmmgdp_commercial_municipal_heat_energy",
                "consumpinit_scoe_tj_per_mmmgdp_commercial_municipal_elec_appliances"]:
        scale(col, SCOE_COMMERCIAL_FACTOR, "scoe",
              f"intensidad comercial/institucional x{SCOE_COMMERCIAL_FACTOR}")

    # --- INEN ---------------------------------------------------------------
    col = "consumpinit_inen_energy_total_pj_agriculture_and_livestock"
    if col in df.columns:
        orig = base[col].values[0]
        L.set_col(df, col, INEN_AGRICULTURE_ENERGY_PJ)
        rows.append(dict(variable=col, subsector="inen",
                         original_value_mex=orig, new_value_oax=INEN_AGRICULTURE_ENERGY_PJ,
                         year=L.BASE_YEAR,
                         method="energia agricola estatal (baja mecanizacion; los "
                                "tractores se contabilizan en 1A3eiii, no en 1A2)",
                         source_name=SRC, source_url=URL, agent=AGENT))

    scale("consumpinit_inen_energy_tj_per_mmm_gdp_other_product_manufacturing",
          INEN_GDP_ENERGY_FACTOR, "inen",
          f"intensidad energetica de manufactura ligada al PIB x{INEN_GDP_ENERGY_FACTOR} "
          "(manufactura ligera)")

    L.save(df, args.io)
    L.log_change(rows)
    print(f"[buildings_industry] scoe: residencial calor x{SCOE_RESIDENTIAL_HEAT_FACTOR}, "
          f"elec x{SCOE_RESIDENTIAL_ELEC_FACTOR}, comercial x{SCOE_COMMERCIAL_FACTOR} "
          f"(objetivo 1A4 = 501 kt)")
    print(f"[buildings_industry] inen: agricola {INEN_AGRICULTURE_ENERGY_PJ} PJ, "
          f"intensidad PIB x{INEN_GDP_ENERGY_FACTOR} "
          f"(objetivo 1A2 = 636 kt)")
    print(f"[buildings_industry] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
