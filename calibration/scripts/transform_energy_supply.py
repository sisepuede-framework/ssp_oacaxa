#!/usr/bin/env python
"""Oaxaca energy supply: entc (generacion + refinacion), enfu, fgtv.

This is the structural re-specification that most distinguishes Oaxaca from CDMX,
and it points the OPPOSITE way in both subsectors:

  ENTC  CDMX -> ~0 (importa 99.9% de su electricidad).
        Oaxaca -> 3,681 kt, PERO no de generacion electrica: de REFINACION.
        Tabla 7 tiene renglon 1A1b (Refinacion del petroleo) y NO tiene 1A1a
        (generacion), porque la generacion oaxaquena es eolica/hidro. SISEPUEDE
        modela la refinacion como la tecnologia ENTC `fp_petroleum_refinement`,
        que es exactamente la categoria IPCC 1A1b.

  FGTV  CDMX -> ~0 (sin extraccion ni refinacion).
        Oaxaca -> 17 kt de CH4 fugitivo de refinacion (1B2aiii.4). Oaxaca NO
        extrae petroleo ni gas, asi que las fugas de produccion se anulan y solo
        queda la refinacion.

La refineria de Salina Cruz (PEMEX, 330 kbpd de capacidad) abastece al pais, no al
estado: su produccion excede por mucho la demanda oaxaquena. Eso se representa
EXPORTANDO producto refinado (exports_enfu_pj_fuel_*), que es literalmente lo que
ocurre, en vez de inflar el factor de emision. Con EF = 6.374 t CO2/TJ, el objetivo
de 3,681 kt implica ~577 PJ de producto refinado -- equivalente a ~282 kbpd, la
operacion real de Salina Cruz en 2013.

Usage: python transform_energy_supply.py [--io <working OAX csv>]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "energy_supply"

# --- Refineria Salina Cruz -----------------------------------------------------
# Producto refinado total exportado (PJ). Calibrado contra el objetivo 1A1b = 3,681 kt
# via el bucle del gate; el reparto por combustible sigue los output_activity_ratio
# del propio modelo.
# Actividad total de refinacion (PJ de producto). Con EF = 6.373913 t CO2/TJ,
# 577.5 PJ -> 3,681 kt CO2, el objetivo 1A1b.
REFINING_ACTIVITY_PJ = 577.5
OUTPUT_SHARES = {          # nemomod_entc_output_activity_ratio_fuel_production_fp_petroleum_refinement_*
    "gasoline": 0.4791,
    "diesel": 0.2969,
    "kerosene": 0.08595,
    "hydrocarbon_gas_liquids": 0.04,
    "oil": 0.01405,
}

# --- Generacion electrica: 100% renovable (Istmo de Tehuantepec + hidro) --------
# Capacidad instalada en Oaxaca, ~2013: eolica ~1.3 GW (parques del Istmo),
# hidro ~0.39 GW (Temascal 354 MW + Cerro de Oro). Sin termoelectricas.
ENTC_RESIDUAL_CAPACITY_GW = {
    "wind": 1.30, "hydropower": 0.39, "solar": 0.01,
    "biogas": 0.0, "biomass": 0.0, "coal": 0.0, "coal_ccs": 0.0,
    "gas": 0.0, "gas_ccs": 0.0, "geothermal": 0.0, "nuclear": 0.0,
    "ocean": 0.0, "oil": 0.0, "waste_incineration": 0.0,
}
ENTC_MIN_SHARE = {
    "wind": 0.72, "hydropower": 0.26, "solar": 0.02,
    "biogas": 0.0, "biomass": 0.0, "coal": 0.0, "coal_ccs": 0.0,
    "gas": 0.0, "gas_ccs": 0.0, "geothermal": 0.0, "nuclear": 0.0,
    "ocean": 0.0, "oil": 0.0, "waste_incineration": 0.0,
}

# --- Comercio de combustibles --------------------------------------------------
# Oaxaca no produce crudo ni gas natural: los importa. Refina localmente los
# derivados, por lo que su fraccion importada de gasolina/diesel es ~0.
# TODOS los refinados se marcan como importados para el consumo local. No es una
# afirmacion fisica (Oaxaca si consume producto de Salina Cruz) sino de control: si
# la demanda local de un producto MENOR se obliga a refinacion local, NemoMod
# sobredimensiona la refineria -- el fuel oil es solo 1.4% del rendimiento, asi que
# cubrir su demanda localmente exigiria ~14,000 PJ de proceso (verificado: entc
# disparado a 44,432 kt). Con imports=1 la refinacion queda gobernada UNICAMENTE por
# las exportaciones, que es la variable que si conocemos. Las emisiones de combustion
# del consumo local se contabilizan igual en trns/scoe/inen, y las importaciones no
# acarrean emisiones territoriales, asi que el inventario no se ve afectado.
FRAC_IMPORTED = {
    # El crudo se marca como "suministro interno" (0) NO porque Oaxaca lo extraiga,
    # sino porque es la unica forma de que NemoMod alimente la refineria: si se
    # marca como importado, la optimizacion importa producto ya refinado y la
    # refineria nunca opera (verificado empiricamente). La correccion territorial
    # se hace anulando la energia de extraccion (ME_CRUDE_INPUTS_ZERO abajo), de
    # modo que el crudo entra como pass-through con CERO emisiones de extraccion
    # -- que es lo correcto: el crudo llega de Campeche/Tabasco y sus emisiones de
    # extraccion pertenecen a esos estados, no a Oaxaca.
    "crude": 0.0,
    "natural_gas": 1.0,
    "coal": 1.0,
    "gasoline": 1.0,
    "diesel": 1.0,
    "kerosene": 1.0,
    "hydrocarbon_gas_liquids": 1.0,
    "oil": 1.0,
    "electricity": 0.0,      # excedentaria: exporta
}

# Extraccion de crudo en Oaxaca = NULA. Anular los insumos energeticos de la
# tecnologia me_crude elimina las emisiones de extraccion (Tabla 7 no tiene
# renglon 1A1c/1B2a de extraccion) dejando el crudo como pass-through hacia la
# refineria. Mismo tratamiento para carbon y gas natural.
ME_INPUTS_ZERO = ["me_crude_diesel", "me_crude_electricity", "me_crude_gasoline",
                  "me_crude_natural_gas", "me_crude_oil",
                  "me_coal_diesel", "me_coal_electricity", "me_coal_gasoline",
                  "me_coal_natural_gas", "me_coal_oil", "me_coal_coal_deposits",
                  "me_natural_gas_diesel", "me_natural_gas_electricity",
                  "me_natural_gas_gasoline", "me_natural_gas_natural_gas",
                  "me_natural_gas_oil"]
EXPORTS_ZERO = ["crude", "natural_gas", "coal", "ammonia", "hydrogen",
                "natural_gas_liquid"]
ELECTRICITY_EXPORT_PJ = 15.0     # excedente eolico del Istmo hacia el SIN

# Factores fugitivos del CRUDO. Estas columnas NO existen en la base nacional, asi
# que add_missing_cols las rellena con los valores por defecto del ejemplo de
# SISEPUEDE (otro pais) y aplica fugas de EXTRACCION completas a los ~628 PJ de
# crudo que alimentan la refineria -- 9,292 kt espurios. Pero ese crudo no se extrae
# en Oaxaca: entra de Campeche/Tabasco y sus fugas de extraccion pertenecen a los
# estados productores. Se reducen al nivel que reproduce el unico renglon fugitivo
# que Tabla 7 si atribuye al estado: 1B2aiii.4 Refinacion del petroleo = 17 kt.
CRUDE_FUGITIVE_SCALAR = 17.0 / 9292.0
CRUDE_FUGITIVE_EF_DEFAULTS = {
    "ef_fgtv_production_flaring_tonne_ch4_per_m3_fuel_crude": 2.467792535850613e-05,
    "ef_fgtv_production_flaring_tonne_co2_per_m3_fuel_crude": 0.0399749921826133,
    "ef_fgtv_production_flaring_tonne_n2o_per_m3_fuel_crude": 6.321392251711643e-07,
    "ef_fgtv_production_flaring_tonne_nmvoc_per_m3_fuel_crude": 0.0062529992803453,
    "ef_fgtv_production_fugitive_tonne_ch4_per_m3_fuel_crude": 0.0092441948549119,
    "ef_fgtv_production_fugitive_tonne_co2_per_m3_fuel_crude": 0.0102490704319759,
    "ef_fgtv_production_fugitive_tonne_n2o_per_m3_fuel_crude": 6.8e-08,
    "ef_fgtv_production_fugitive_tonne_nmvoc_per_m3_fuel_crude": 0.0140263261984831,
    "ef_fgtv_production_venting_tonne_ch4_per_m3_fuel_crude": 0.0102176318195558,
    "ef_fgtv_production_venting_tonne_co2_per_m3_fuel_crude": 0.0021213203435596,
    "ef_fgtv_production_venting_tonne_n2o_per_m3_fuel_crude": 0.0,
    "ef_fgtv_production_venting_tonne_nmvoc_per_m3_fuel_crude": 0.0018761663039293,
    "ef_fgtv_transmission_tonne_ch4_per_m3_fuel_crude": 1.52e-05,
    "ef_fgtv_transmission_tonne_co2_per_m3_fuel_crude": 1.395e-06,
    "ef_fgtv_transmission_tonne_n2o_per_m3_fuel_crude": 0.0,
    "ef_fgtv_transmission_tonne_nmvoc_per_m3_fuel_crude": 0.000152,
}

SRC = ("PEMEX Anuario Estadistico (refineria Salina Cruz); SENER/CRE capacidad "
       "instalada de generacion en Oaxaca; PECC Oaxaca 2016-2022 Tabla 7")
URL = "https://www.pemex.com/ri/Publicaciones/Paginas/AnuarioEstadistico.aspx"


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

    # --- 1. Refinacion: exportar producto refinado --------------------------
    for fuel, share in OUTPUT_SHARES.items():
        pj = REFINING_ACTIVITY_PJ * share
        put(f"exports_enfu_pj_fuel_{fuel}", pj, "enfu",
            f"exportacion de refinados de Salina Cruz: {REFINING_ACTIVITY_PJ} PJ de "
            f"proceso x rendimiento {share:.4f}")

    for fuel in EXPORTS_ZERO:
        put(f"exports_enfu_pj_fuel_{fuel}", 0.0, "enfu",
            "Oaxaca no produce crudo/gas/carbon: exportacion nula")

    put("exports_enfu_pj_fuel_electricity", ELECTRICITY_EXPORT_PJ, "enfu",
        "excedente de generacion eolica del Istmo exportado al SIN")

    # --- 2. Fracciones importadas ------------------------------------------
    for fuel, frac in FRAC_IMPORTED.items():
        put(f"frac_enfu_fuel_demand_imported_pj_fuel_{fuel}", frac, "enfu",
            "crudo/gas importado; derivados refinados en el estado"
            if frac else "refinado localmente en Salina Cruz")

    # --- 2b. Extraccion nula: crudo como pass-through sin emisiones ---------
    for key in ME_INPUTS_ZERO:
        put(f"nemomod_entc_input_activity_ratio_fuel_production_{key}", 0.0, "entc",
            "Oaxaca no extrae hidrocarburos: energia de extraccion anulada; el crudo "
            "es pass-through hacia la refineria (emisiones de extraccion pertenecen "
            "a los estados productores)")

    # --- 2c. Fugitivas: sin extraccion, solo refinacion (1B2aiii.4 = 17 kt) --
    for fuel in ["coal", "natural_gas", "oil"]:
        for stage in ["fugitive", "flaring", "venting"]:
            for gas in ["ch4", "co2", "n2o", "nmvoc"]:
                put(f"ef_fgtv_production_{stage}_tonne_{gas}_per_m3_fuel_{fuel}", 0.0,
                    "fgtv", "Oaxaca no extrae hidrocarburos ni carbon: fugas, venteo "
                    "y quema de produccion nulas (Tabla 7 solo reporta 1B2aiii.4 "
                    "refinacion = 17 kt)")
    for gas in ["ch4", "co2", "n2o", "nmvoc"]:
        put(f"ef_fgtv_distribution_tonne_{gas}_per_m3_fuel_natural_gas", 0.0, "fgtv",
            "red de distribucion de gas natural marginal en Oaxaca")
        put(f"ef_fgtv_transmission_tonne_{gas}_per_m3_fuel_natural_gas", 0.0, "fgtv",
            "sin transmision de gas natural en Oaxaca")
        put(f"ef_fgtv_transmission_tonne_{gas}_per_m3_fuel_oil", 0.0, "fgtv",
            "sin red de transmision de crudo en Oaxaca")

    # --- 2d. Fugitivas del crudo: solo refinacion, no extraccion ------------
    for col, default in CRUDE_FUGITIVE_EF_DEFAULTS.items():
        val = default * CRUDE_FUGITIVE_SCALAR
        L.ensure_col(df, col, val)
        rows.append(dict(variable=col, subsector="fgtv",
                         original_value_mex="(ausente en la base nacional)",
                         new_value_oax=val, year=L.BASE_YEAR,
                         method=f"factor por defecto x{CRUDE_FUGITIVE_SCALAR:.6f}: el "
                                "crudo es pass-through importado, no extraccion "
                                "oaxaquena; calibrado a Tabla 7 1B2aiii.4 = 17 kt",
                         source_name=SRC, source_url=URL, agent=AGENT))

    # --- 3. Generacion electrica 100% renovable ----------------------------
    for tech, gw in ENTC_RESIDUAL_CAPACITY_GW.items():
        put(f"nemomod_entc_residual_capacity_pp_{tech}_gw", gw, "entc",
            "capacidad instalada en Oaxaca (eolica Istmo + hidro Temascal)")
    for tech, share in ENTC_MIN_SHARE.items():
        put(f"nemomod_entc_frac_min_share_production_pp_{tech}", share, "entc",
            "mezcla de generacion estatal: renovable, sin termoelectricas "
            "(Tabla 7 no reporta renglon 1A1a)")

    L.save(df, args.io)
    L.log_change(rows)

    implied_kt = REFINING_ACTIVITY_PJ * 1000 * 6.373913043 / 1000
    print(f"[energy_supply] refinacion = {REFINING_ACTIVITY_PJ:.1f} PJ de proceso "
          f"(~{implied_kt:,.0f} kt CO2 implicitos, objetivo 1A1b = 3,681)")
    print(f"[energy_supply] generacion: eolica {ENTC_MIN_SHARE['wind']:.0%} + "
          f"hidro {ENTC_MIN_SHARE['hydropower']:.0%} + solar {ENTC_MIN_SHARE['solar']:.0%}; "
          f"fosil 0% | capacidad eolica {ENTC_RESIDUAL_CAPACITY_GW['wind']} GW")
    print(f"[energy_supply] fugitivas de crudo x{CRUDE_FUGITIVE_SCALAR:.6f} "
          f"(solo refinacion; objetivo 1B = 17 kt)")
    print(f"[energy_supply] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
