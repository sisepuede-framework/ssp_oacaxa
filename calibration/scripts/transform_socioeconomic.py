#!/usr/bin/env python
"""Oaxaca socioeconomic drivers (gnrl): population, GDP, area, occupancy.

Calibration priority #1 -- SISEPUEDE derives most demand (buildings energy, waste,
wastewater, transport, product use) from population and GDP, so every other sector's
downscaling depends on these being right first.

Key differences vs the CDMX calibration:
- Oaxaca is majority RURAL (~52%), the national DB is ~79% urban and CDMX was ~100%
  urban. This matters for scoe (lena/GLP residencial) and waste collection coverage.
- Oaxaca's population GROWS modestly (unlike CDMX, which declines), but slower than
  the nation, so its share drifts down over the horizon.
- Oaxaca's GDP share (~1.55%) is HALF its population share (~3.20%) -- the inverse of
  CDMX, where GDP share (15%) was double population share (7.3%).

Usage: python transform_socioeconomic.py [--io <working OAX csv>]
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "socioeconomic"

# --- Oaxaca anchors (see 01_oaxaca_data/oaxaca_reference_values.csv) ------------
POP_2013 = 3_901_517          # interp. INEGI Censo 2010 (3,801,962) - Intercensal 2015 (3,967,889)
FRAC_RURAL = 0.523            # INEGI: ~52% en localidades rurales; PDF: 7 de cada 10 en loc. <10,000
GDP_SHARE = 0.0155            # PIBE Oaxaca / PIB nacional (INEGI, ~1.5-1.6%)
AREA_HA = L.OAX_AREA_HA       # 9,395,972.535 ha - Marco Geoestadistico INEGI feb 2018
OCCUPANCY = 4.0               # personas por vivienda, INEGI Censo 2010 Oaxaca

# Population share of the nation: 3.20% (2013) -> 2.84% (2058). Oaxaca grows, but
# slower than the country (high out-migration), so its share drifts down.
SHARE_2013 = 0.032018
SHARE_2058 = 0.02840

SRC = "INEGI Censo de Poblacion y Vivienda 2010 / Encuesta Intercensal 2015; INEGI PIBE; Marco Geoestadistico feb 2018"
URL = "https://www.inegi.org.mx/programas/intercensal/2015/"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    n = len(df)
    nat_rural = base["population_gnrl_rural"].values[:n]
    nat_urban = base["population_gnrl_urban"].values[:n]
    nat_total = (nat_rural + nat_urban).astype(float)
    nat_gdp = base["gdp_mmm_usd"].values[:n].astype(float)

    # --- Retro-extension de los dos años que la base nacional no trae (D10) ------
    # aligned_baseline() copia la fila de 2015 en 2013 y 2014 (correcto para factores
    # tecnicos, que varian despacio). Para los DRIVERS eso dejaria el PIB y la
    # poblacion planos tres años, asi que aqui se retro-extienden con crecimiento
    # mexicano observado (INEGI, precios constantes). Indices: 0=2013, 1=2014, 2=2015.
    i15 = L.NAT_Y0 - L.Y0
    for i, yr in zip(range(i15 - 1, -1, -1), range(L.NAT_Y0, L.Y0, -1)):
        nat_gdp[i] = nat_gdp[i + 1] / (1.0 + L.NAT_GDP_GROWTH[yr])
        nat_total[i] = nat_total[i + 1] / (1.0 + L.NAT_POP_GROWTH[yr])

    # Oaxaca population trajectory: national curve x a linearly declining share,
    # renormalised so that 2013 lands exactly on the observed POP_2013.
    share = np.linspace(SHARE_2013, SHARE_2058, n)
    oax_total = nat_total * share
    oax_total = oax_total * (POP_2013 / oax_total[0])

    rows = []
    orig_rural, orig_urban = nat_rural[0], nat_urban[0]

    L.set_col(df, "population_gnrl_rural", oax_total * FRAC_RURAL)
    L.set_col(df, "population_gnrl_urban", oax_total * (1 - FRAC_RURAL))
    rows += [
        dict(variable="population_gnrl_rural", subsector="gnrl",
             original_value_mex=orig_rural, new_value_oax=oax_total[0] * FRAC_RURAL,
             year=L.BASE_YEAR, method="direct replace (trayectoria CONAPO/INEGI, 52.3% rural)",
             source_name=SRC, source_url=URL, agent=AGENT),
        dict(variable="population_gnrl_urban", subsector="gnrl",
             original_value_mex=orig_urban, new_value_oax=oax_total[0] * (1 - FRAC_RURAL),
             year=L.BASE_YEAR, method="direct replace (trayectoria CONAPO/INEGI, 47.7% urbana)",
             source_name=SRC, source_url=URL, agent=AGENT),
    ]

    # GDP: keep the national growth shape, rebase to Oaxaca's ~1.55% share.
    orig_gdp = base["gdp_mmm_usd"].values[0]
    L.set_col(df, "gdp_mmm_usd", nat_gdp * GDP_SHARE)
    rows.append(dict(variable="gdp_mmm_usd", subsector="gnrl",
                     original_value_mex=orig_gdp, new_value_oax=orig_gdp * GDP_SHARE,
                     year=L.BASE_YEAR, method=f"share-downscale x {GDP_SHARE} (PIBE Oaxaca/nacional)",
                     source_name=SRC, source_url=URL, agent=AGENT))

    # Territory and household occupancy.
    orig_area = base["area_gnrl_country_ha"].values[0]
    L.set_col(df, "area_gnrl_country_ha", AREA_HA)
    rows.append(dict(variable="area_gnrl_country_ha", subsector="gnrl",
                     original_value_mex=orig_area, new_value_oax=AREA_HA,
                     year=L.BASE_YEAR, method="direct replace (superficie estatal)",
                     source_name="INEGI Marco Geoestadistico feb 2018", source_url=URL, agent=AGENT))

    orig_occ = base["occrateinit_gnrl_occupancy"].values[0]
    L.set_col(df, "occrateinit_gnrl_occupancy", OCCUPANCY)
    rows.append(dict(variable="occrateinit_gnrl_occupancy", subsector="gnrl",
                     original_value_mex=orig_occ, new_value_oax=OCCUPANCY,
                     year=L.BASE_YEAR, method="direct replace (ocupantes por vivienda)",
                     source_name="INEGI Censo 2010 Oaxaca", source_url=URL, agent=AGENT))

    L.save(df, args.io)
    L.log_change(rows)
    print(f"[socioeconomic] eje calendario real: PIB nacional {L.Y0}={nat_gdp[0]:,.0f} "
          f"{L.NAT_Y0}={nat_gdp[i15]:,.0f} mmm USD (choque COVID en 2020, no en 2018)")
    print(f"[socioeconomic] pob {L.BASE_YEAR} = {oax_total[0]:,.0f} "
          f"({FRAC_RURAL:.0%} rural) -> {oax_total[-1]:,.0f} en {L.Y1}")
    print(f"[socioeconomic] PIB = {nat_gdp[0] * GDP_SHARE:,.2f} mmm USD "
          f"({GDP_SHARE:.2%} nacional) | area = {AREA_HA:,.0f} ha | ocupacion = {OCCUPANCY}")


if __name__ == "__main__":
    main()
