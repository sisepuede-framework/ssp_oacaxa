#!/usr/bin/env python
"""Oaxaca AFOLU: lvst, lsmm, soil, agrc, lndu, frst.

DOMINANT SECTOR -- 7,996 kt = 44% of the Tabla 7 target, the exact inverse of CDMX
(where AFOLU was ~0.067 Mt and calibrated last). Here it is calibrated second, right
after the socioeconomic drivers.

Tabla 7 targets (kt CO2e, 2013):
    3A1 Fermentacion enterica          2,627  -> lvst
    3A2 Manejo de estiercol              418  -> lsmm
    3C4 N2O directo suelos gestionados 1,862  -> soil
    3C5 N2O indirecto suelos             199  -> soil
    3C7 Cultivo de arroz                  68  -> agrc
    3C1a Quema biomasa tierras cultivo 1,557  -> agrc  (solo la parte no-CO2: 253)
    3C1a Quema biomasa tierras forest. 1,265  -> frst  (solo la parte CO2: 1,143)

ROUTING OF 3C1a BIOMASS BURNING -- corrected, see DECISIONS.md D8.
Burning does NOT live in lndu. It splits across two model fields:
  - crop residues -> emission_co2e_{ch4,n2o}_agrc_biomass_burning. There is NO
    co2 counterpart: per IPCC 2006 the carbon in annual crop residues is cyclical.
    Tabla 7's 1,304 kt of cropland-burning CO2 therefore has no model field and is
    reported as an out-of-boundary item, not forced into the model.
  - forest fires -> emission_co2e_co2_frst_forest_fires, i.e. in FRST, not lndu.
    Conversely the 122 kt of CH4/N2O from forest fires have no model field.
lndu carries LAND-CONVERSION CO2 (carbon-stock change), which has no row in Tabla 7's
IPCC total at all -- it appears only in the footnote ("hasta 9 Mt/ano de perdida de
capacidad de absorcion"). It is a documented memo, like the FRST sink.

FRST is excluded from the gross gate (decision D3) but calibrated so absorption lands
near the Tabla 7 footnote range (~14 Mt/yr gross forest absorption). Its FIRE component
is separated out by diagnose_2013.py and IS gated, against 3C1a forestal.

Usage: python transform_afolu.py [--io <working OAX csv>]
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "afolu"

# --- Livestock inventory, Oaxaca (cabezas) --------------------------------------
# SIAP/SIACON inventario ganadero estatal, orden de magnitud 2013. Oaxaca is a
# large-herd / low-productivity livestock state: dual-purpose cattle in Papaloapan
# and Costa, goats in the Mixteca.
LVST_HEADS = {
    "cattle_nondairy": 1_300_000,
    "cattle_dairy":       50_000,
    "pigs":            1_000_000,
    "sheep":             500_000,
    "goats":           1_200_000,
    "chickens":       15_000_000,
    "horses":            350_000,
    "mules":             250_000,
    "buffalo":                 0,
}

# --- Land cover, Oaxaca (fracciones de 9,395,972.5 ha) --------------------------
# Oaxaca is ~2/3 forested (bosque templado + selva), the most floristically diverse
# state in Mexico. Normalised to 1.0 in code.
LNDU_FRACS = {
    "croplands":          0.145,   # ~1.36 M ha (SIAP superficie agricola)
    "forests_primary":    0.120,
    "forests_secondary":  0.430,   # bosque + selva ~5.2 M ha combinados
    "forests_mangroves":  0.0022,  # manglares costeros (Chacahua, Huatulco)
    "grasslands":         0.100,
    "pastures":           0.090,
    "shrublands":         0.100,
    "settlements":        0.008,
    "other":              0.020,
    "wetlands":           0.002,
    "flooded":            0.0028,
}

# --- Calibration scalars (tuned against the gate; see 04_validation) ------------
# Oaxaca practica agricultura mayoritariamente de TEMPORAL y de subsistencia, con
# uso de fertilizante sintetico muy por debajo del promedio nacional (dominado por
# el riego intensivo del noroeste). Calibrado contra 3C4+3C5 = 2,061 kt.
SOIL_FERTILIZER_SCALAR = 0.09
SOIL_LIMING_SCALAR = 0.09

# --- Conversion de uso de suelo -------------------------------------------------
# El modelo nacional arrastra tasas de deforestacion que, aplicadas a la cobertura
# forestal oaxaquena, generan ~8,400 kt de emisiones por conversion. Tabla 7 NO
# contabiliza eso en su total IPCC: sus renglones 3C1a son QUEMA de biomasa
# (2,822 kt), y la perdida de capacidad de absorcion se menciona solo en la nota al
# pie (hasta 9 Mt/ano), fuera de las 17,968. Ademas Oaxaca tiene el regimen de
# manejo forestal comunitario mas extenso del pais, con deforestacion neta menor
# que la media nacional. Las transiciones bosque -> no bosque se escalan y el
# remanente se devuelve a la diagonal para conservar filas que suman 1.
FOREST_CONVERSION_FACTOR = 0.29
FOREST_CLASSES = ["forests_primary", "forests_secondary", "forests_mangroves"]

# --- Sumidero forestal (decision D3) --------------------------------------------
# Excluido del gate bruto (Tabla 7 es un inventario de FUENTES), pero calibrado al
# rango que da la nota al pie de la Tabla 7: "los macizos de bosques y selvas
# presentes en Oaxaca... podrian absorber alrededor de 14 millones de toneladas de
# CO2 equivalente anuales". Con el factor nacional el modelo daba solo -10.5 Mt: el
# valor nacional para bosque primario (0.7 t CO2/ha/ano) refleja el promedio del
# pais, dominado por bosque seco y degradado, no los bosques mesofilos y selvas
# altas de Oaxaca (Chimalapas, Sierra Norte), mucho mas productivos.
FRST_SEQUESTRATION_PRIMARY_KT_CO2_HA = 0.003757

# --- Incendios forestales (3C1a quema de biomasa en tierras forestales) ---------
# Superficie afectada por incendios en Oaxaca, 2013. CONAFOR reporta ~413,000 ha a
# nivel nacional ese ano (temporada relativamente benigna); Oaxaca aporta tipicamente
# 3-8%. Se ancla en 13,000 ha, extremo bajo de esa banda, consistente con 2013.
FIRE_BURNED_AREA_HA = 13_000
# El bosque primario (remoto, en areas protegidas y bajo manejo comunitario) arde
# menos por hectarea que el secundario/degradado.
FIRE_PRIMARY_SUSCEPTIBILITY = 0.4

# --- Quema de residuos agricolas ------------------------------------------------
# El valor nacional (2.5%) refleja la agricultura mecanizada del norte. Oaxaca
# practica roza-tumba-quema de forma extendida en la agricultura de temporal y de
# ladera, con quema habitual de residuos y de acahual antes de la siembra.
# Calibrado contra la parte NO-CO2 de 3C1a cultivo (CH4 193 + N2O 60 = 253 kt): con
# 0.25 el modelo daba 93 kt. 0.65 es el limite superior defendible para milpa de
# temporal en ladera; el residuo (~5%) se documenta en vez de forzarse.
FRAC_CROP_RESIDUES_BURNED = 0.65

SRC = "SIAP/SIACON inventario ganadero y superficie agricola estatal; INEGI Marco Geoestadistico; INEGI Uso de Suelo y Vegetacion serie VI"
URL = "https://www.gob.mx/siap"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    rows = []

    # --- lvst: initial herd sizes -------------------------------------------
    for animal, heads in LVST_HEADS.items():
        col = f"pop_lvst_initial_{animal}"
        if col not in df.columns:
            continue
        orig = base[col].values[0]
        L.set_col(df, col, heads)
        rows.append(dict(variable=col, subsector="lvst",
                         original_value_mex=orig, new_value_oax=heads,
                         year=L.BASE_YEAR,
                         method="direct replace (inventario ganadero estatal)",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- lvst: la produccion local sigue a la poblacion, no al ingreso ------
    # El hato heredaba las elasticidades ingreso-demanda NACIONALES y crecia +65%
    # al 2058 (19.6 -> 32.3 M cabezas) mientras la poblacion de Oaxaca crece +11%
    # y empieza a caer despues de 2045. No es defendible: el inventario de SIAP
    # para Oaxaca ha sido esencialmente plano, la ganaderia es extensiva y de
    # traspatio, limitada por tierra y agua, y el estado ya es importador neto de
    # proteina animal (bovino de Veracruz y Chiapas, aves del Bajio).
    #
    # NO se tocan las elasticidades: la DEMANDA si responde al ingreso, eso es
    # real y esta bien medido. Lo que no crece es la PRODUCCION local. El consumo
    # adicional se cubre con importacion -- el mecanismo fisico correcto, y ademas
    # sin emisiones territoriales, que es como lo trata el inventario.
    #
    # SISEPUEDE (afolu.py:4103 project_per_capita_demand) calcula
    #     demanda(t)    = pob(t) x (dem_0/pob_0) x cumprod(1 + tasa_pibpc x elast)
    #     produccion(t) = demanda(t) x (1 - frac_importada(t))
    # asi que para que la produccion local siga EXACTAMENTE a la poblacion basta
    #     frac_importada(t) = 1 - 1/cumprod(1 + tasa_pibpc x elast)
    # con piso en el valor nacional original (no se eliminan importaciones ya
    # existentes). En t=0 el factor vale 1, asi que 2013 queda intacto y la
    # calibracion del ano base no se toca.
    pop_cols = [c for c in df.columns if c.startswith("population_gnrl_")]
    pop_tot = df[pop_cols].sum(axis=1).values
    gdppc = (df["gdp_mmm_usd"].values * 1e9) / pop_tot
    rates = gdppc[1:] / gdppc[:-1] - 1.0

    for animal in LVST_HEADS:
        ecol = f"elasticity_lvst_{animal}_demand_to_gdppc"
        icol = f"frac_lvst_livestock_demand_imported_{animal}"
        if ecol not in df.columns or icol not in df.columns:
            continue
        elast = df[ecol].values
        scale = np.concatenate([[1.0], np.cumprod(1.0 + rates * elast[:-1])])
        frac = 1.0 - 1.0 / scale
        orig_vec = base[icol].values[:len(df)]
        frac = np.clip(np.maximum(frac, orig_vec), 0.0, 0.95)
        L.set_col(df, icol, frac)
        rows.append(dict(variable=icol, subsector="lvst",
                         original_value_mex=orig_vec[0], new_value_oax=frac[-1],
                         year=L.BASE_YEAR,
                         method="produccion local sigue a la poblacion estatal; el consumo "
                                "adicional por ingreso se cubre con importacion de otros "
                                "estados (Oaxaca es importador neto de proteina animal). "
                                "2013 sin cambio",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- lndu: initial land-cover fractions ---------------------------------
    total = sum(LNDU_FRACS.values())
    for cls, frac in LNDU_FRACS.items():
        col = f"frac_lndu_initial_{cls}"
        if col not in df.columns:
            continue
        orig = base[col].values[0]
        val = frac / total                       # normalise to 1.0
        L.set_col(df, col, val)
        rows.append(dict(variable=col, subsector="lndu",
                         original_value_mex=orig, new_value_oax=val,
                         year=L.BASE_YEAR,
                         method=f"direct replace (cobertura estatal, normalizada; {val * L.OAX_AREA_HA:,.0f} ha)",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- soil: fertilizer / liming intensity --------------------------------
    for col, scalar, note in [
        ("demscalar_soil_fertilizer_n_per_area", SOIL_FERTILIZER_SCALAR,
         "intensidad de fertilizacion N por ha (agricultura de temporal/subsistencia)"),
        ("demscalar_soil_liming_per_area", SOIL_LIMING_SCALAR,
         "intensidad de encalado por ha"),
    ]:
        if col not in df.columns:
            continue
        orig = base[col].values[0]
        L.set_col(df, col, scalar)
        rows.append(dict(variable=col, subsector="soil",
                         original_value_mex=orig, new_value_oax=scalar,
                         year=L.BASE_YEAR, method=f"scalar calibrado - {note}",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- agrc: quema de residuos (roza-tumba-quema) -------------------------
    for col, val in [("frac_agrc_crop_residues_burned", FRAC_CROP_RESIDUES_BURNED),
                     ("frac_agrc_crop_residues_removed", 1 - FRAC_CROP_RESIDUES_BURNED)]:
        if col not in df.columns:
            continue
        orig = base[col].values[0]
        L.set_col(df, col, val)
        rows.append(dict(variable=col, subsector="agrc",
                         original_value_mex=orig, new_value_oax=val,
                         year=L.BASE_YEAR,
                         method="quema de residuos agricolas (roza-tumba-quema "
                                "extendida en agricultura de temporal y de ladera)",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- frst: sumidero calibrado a la nota al pie de Tabla 7 ---------------
    col = "ef_frst_sequestration_primary_kt_co2_ha"
    if col in df.columns:
        orig = base[col].values[0]
        L.set_col(df, col, FRST_SEQUESTRATION_PRIMARY_KT_CO2_HA)
        rows.append(dict(variable=col, subsector="frst",
                         original_value_mex=orig,
                         new_value_oax=FRST_SEQUESTRATION_PRIMARY_KT_CO2_HA,
                         year=L.BASE_YEAR,
                         method="tasa de captura de bosque primario calibrada a la nota "
                                "al pie de Tabla 7 (~14 Mt CO2e/ano de absorcion); el "
                                "valor nacional subestima los bosques mesofilos y "
                                "selvas altas de Oaxaca",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- lndu: moderar la conversion forestal -------------------------------
    for src_cls in FOREST_CLASSES:
        cols = [c for c in df.columns if c.startswith(f"pij_lndu_{src_cls}_to_")]
        diag = f"pij_lndu_{src_cls}_to_{src_cls}"
        if diag not in cols:
            continue
        freed = 0.0
        for c in cols:
            if c == diag:
                continue
            orig = base[c].values[0]
            new = orig * FOREST_CONVERSION_FACTOR
            freed += orig - new
            L.set_col(df, c, base[c].values[:len(df)] * FOREST_CONVERSION_FACTOR)
            rows.append(dict(variable=c, subsector="lndu",
                             original_value_mex=orig, new_value_oax=new,
                             year=L.BASE_YEAR,
                             method=f"transicion forestal x{FOREST_CONVERSION_FACTOR} "
                                    "(manejo forestal comunitario; Tabla 7 excluye "
                                    "conversion de su total IPCC)",
                             source_name=SRC, source_url=URL, agent=AGENT))
        orig_diag = base[diag].values[0]
        L.set_col(df, diag, base[diag].values[:len(df)] + freed)
        rows.append(dict(variable=diag, subsector="lndu",
                         original_value_mex=orig_diag, new_value_oax=orig_diag + freed,
                         year=L.BASE_YEAR,
                         method="diagonal rebalanceada para que la fila sume 1",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- frst: incendios forestales (3C1a quema en tierras forestales) ------
    # DOS FALLAS ACUMULADAS -- ver DECISIONS.md D8. El modelo daba 0.65 kt donde
    # Tabla 7 reporta 1,143 kt de CO2:
    #   1) frac_frst_annual_wildfire_fraction_* seguian en el default NACIONAL
    #      (1e-5 primary / 1e-4 secondary) => 407 ha/ano ardiendo en todo el estado.
    #      La calibracion de Oaxaca nunca escribio estas columnas.
    #   2) SISEPUEDE extrae qty_frst_biomass_consumed_by_fire_* con
    #      var_bounds=(0,1) y force_boundary_restriction=True (afolu.py:5844 y
    #      :5866), de modo que 45-125 t/ha se RECORTAN a 1.0 t/ha. Un factor ~50
    #      perdido en silencio, con un simple warnings.warn.
    #
    # Correccion: (1) fijar la superficie quemada con el dato de CONAFOR, y (2)
    # plegar la biomasa consumida DENTRO del EF usando los propios valores
    # nacionales de la base, de forma que el producto area x biomasa x EF quede
    # intacto pese al clamp. No se inventa ningun factor tecnico: el EF resultante
    # (~118 t CO2/ha en primario, ~84 en secundario) es el que SISEPUEDE habria
    # aplicado si no recortara la biomasa.
    area_p = LNDU_FRACS["forests_primary"] / total * L.OAX_AREA_HA
    area_s = LNDU_FRACS["forests_secondary"] / total * L.OAX_AREA_HA
    f_s = FIRE_BURNED_AREA_HA / (area_s + FIRE_PRIMARY_SUSCEPTIBILITY * area_p)
    f_p = FIRE_PRIMARY_SUSCEPTIBILITY * f_s

    fire_co2_t = 0.0
    for cls, frac_burn, area_cls in [("primary", f_p, area_p),
                                     ("secondary", f_s, area_s),
                                     ("mangroves", 0.0, 0.0)]:
        col_frac = f"frac_frst_annual_wildfire_fraction_{cls}"
        col_ef = f"ef_frst_forestfires_{cls}_co2"
        if col_frac not in df.columns or col_ef not in df.columns:
            continue

        # biomasa efectiva por ha = suma ponderada temperate/tropical (valores
        # nacionales retenidos). Las dos categorias temperate comparten el mismo
        # array de biomasa en afolu.py, por eso ambas usan qty_..._temperate_*.
        f_tnp = base.get(f"frac_frst_{cls}_cl1_temperate_nutrient_poor",
                         pd.Series([0.0])).values[0]
        f_tnr = base.get(f"frac_frst_{cls}_cl1_temperate_nutrient_rich",
                         pd.Series([0.0])).values[0]
        f_tro = base.get(f"frac_frst_{cls}_cl1_tropical",
                         pd.Series([0.0])).values[0]
        bio_tmp = base.get(f"qty_frst_biomass_consumed_by_fire_temperate_{cls}_tonne_per_ha",
                           pd.Series([0.0])).values[0]
        bio_tro = base.get(f"qty_frst_biomass_consumed_by_fire_tropical_{cls}_tonne_per_ha",
                           pd.Series([0.0])).values[0]
        bio_eff = (f_tnp + f_tnr) * bio_tmp + f_tro * bio_tro

        orig_frac = base[col_frac].values[0]
        L.set_col(df, col_frac, frac_burn)
        rows.append(dict(variable=col_frac, subsector="frst",
                         original_value_mex=orig_frac, new_value_oax=frac_burn,
                         year=L.BASE_YEAR,
                         method=f"superficie quemada estatal {FIRE_BURNED_AREA_HA:,} ha/ano "
                                f"(susceptibilidad primario x{FIRE_PRIMARY_SUSCEPTIBILITY}); "
                                "el default nacional dejaba 407 ha en todo el estado",
                         source_name="CONAFOR Reporte semanal de incendios forestales 2013",
                         source_url="https://www.gob.mx/conafor", agent=AGENT))

        orig_ef = base[col_ef].values[0]
        ef_eff = orig_ef * bio_eff
        L.set_col(df, col_ef, ef_eff)
        rows.append(dict(variable=col_ef, subsector="frst",
                         original_value_mex=orig_ef, new_value_oax=ef_eff,
                         year=L.BASE_YEAR,
                         method=f"EF nacional x biomasa consumida nacional ({bio_eff:.1f} t/ha) "
                                "plegados en un solo factor, para sortear el clamp "
                                "var_bounds=(0,1) de afolu.py:5844 que recorta la biomasa a 1 t/ha",
                         source_name=SRC, source_url=URL, agent=AGENT))
        fire_co2_t += area_cls * frac_burn * ef_eff

    L.save(df, args.io)
    L.log_change(rows)

    cropland_ha = LNDU_FRACS["croplands"] / total * L.OAX_AREA_HA
    forest_ha = (LNDU_FRACS["forests_primary"] + LNDU_FRACS["forests_secondary"]
                 + LNDU_FRACS["forests_mangroves"]) / total * L.OAX_AREA_HA
    print(f"[afolu] bovinos={sum(v for k, v in LVST_HEADS.items() if 'cattle' in k):,} "
          f"caprinos={LVST_HEADS['goats']:,} porcinos={LVST_HEADS['pigs']:,}")
    print(f"[afolu] cropland={cropland_ha:,.0f} ha | bosque+selva={forest_ha:,.0f} ha "
          f"({forest_ha / L.OAX_AREA_HA:.0%} del territorio)")
    imp58 = df[df["year"] == L.Y1]["frac_lvst_livestock_demand_imported_cattle_nondairy"].values[0]
    print(f"[afolu] hato: produccion local atada a la poblacion; importacion de bovino "
          f"0% (2013) -> {imp58:.0%} (2058)")
    print(f"[afolu] incendios: {FIRE_BURNED_AREA_HA:,} ha/ano quemadas "
          f"({f_p:.5f} primario / {f_s:.5f} secundario) -> {fire_co2_t / 1000:,.0f} kt CO2 "
          f"(objetivo 3C1a forestal CO2 = 1,143)")
    print(f"[afolu] quema de residuos agricolas = {FRAC_CROP_RESIDUES_BURNED:.0%} "
          f"(objetivo 3C1a cultivo no-CO2 = 253 kt)")
    print(f"[afolu] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
