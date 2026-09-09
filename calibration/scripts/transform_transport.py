#!/usr/bin/env python
"""Oaxaca transporte: trns, trde.

Tabla 7 objetivo: 1A3 = 3,641 kt (20% del inventario). En CDMX el transporte era el
76% del total y el sector decisivo; en Oaxaca es el segundo, por detras de AFOLU.

Desglose Tabla 7 (kt CO2e):
    1A3a Aviacion                            212
    1A3b Transporte terrestre              3,139   <- dominante
    1A3c Ferrocarriles                        13
    1A3d Navegacion maritima y fluvial          2
    1A3eiii Maquinaria de construccion          9
    1A3eiii Tractores y maquinaria agricola   264

Oaxaca tiene una tasa de motorizacion muy baja (estado rural, disperso, de bajos
ingresos): su transporte per capita esta por debajo de su participacion poblacional
(2.75% del transporte nacional vs 3.20% de la poblacion). Los escalares de demanda
trde recogen esa diferencia sobre los drivers gnrl ya aplicados.

Usage: python transform_transport.py [--io <working OAX csv>]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "transport"

# Escalares de demanda de transporte, calibrados contra 1A3 = 3,641 kt.
# El transporte de carga se escala menos que el de pasajeros: Oaxaca es origen y
# destino de poca carga industrial, pero es cruce de la ruta al Istmo.
DEMSCALAR = {
    "trde_private_and_public": 0.081,
    "trde_freight":            0.081,
    "trde_regional":           0.081,
}

SRC = ("INEGI Vehiculos de motor registrados en circulacion (Oaxaca); PECC Oaxaca "
       "2016-2022 Tabla 7 (1A3); PECC Grafica 6 consumo de gasolinas")
URL = "https://www.inegi.org.mx/programas/vehiculosmotor/"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    rows = []
    for key, val in DEMSCALAR.items():
        col = f"demscalar_{key}"
        if col not in df.columns:
            continue
        orig = base[col].values[0]
        L.set_col(df, col, val)
        rows.append(dict(variable=col, subsector="trde",
                         original_value_mex=orig, new_value_oax=val,
                         year=L.BASE_YEAR,
                         method="escalar de demanda calibrado contra Tabla 7 1A3 "
                                "(baja motorizacion estatal)",
                         source_name=SRC, source_url=URL, agent=AGENT))

    L.save(df, args.io)
    L.log_change(rows)
    print(f"[transport] demscalar trde = {DEMSCALAR['trde_private_and_public']} "
          f"(objetivo 1A3 = 3,641 kt)")
    print(f"[transport] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
