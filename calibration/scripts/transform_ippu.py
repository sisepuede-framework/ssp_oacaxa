#!/usr/bin/env python
"""Oaxaca IPPU: procesos industriales y uso de productos.

Tabla 7 objetivo: 842 kt = 2A1 Produccion de cemento (749, CO2) + 2F1 Refrigeracion
y aire acondicionado (93, HFC). No hay mas: Oaxaca no tiene siderurgia, petroquimica
ni vidrio. Es el mismo colapso que en CDMX en cuanto a industria pesada, pero CON
una excepcion importante: Oaxaca SI tiene cemento (planta de Cruz Azul en Lagunas),
mientras que CDMX se llevaba a ~0.

IPPU tambien arrastra a INEN: la demanda de energia industrial se calcula por tonelada
de produccion (energy_tj_per_tonne_production_*), asi que fijar prodinit_ippu_* aqui
es lo que hace bajar INEN al orden correcto.

Objetivo 2A1 = 749 kt CO2. Con un factor de clinker tipico (~0.52 t CO2/t cemento)
eso implica ~1.44 Mt de cemento al ano, consistente con una sola planta.

Usage: python transform_ippu.py [--io <working OAX csv>]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import lib_calib as L

AGENT = "ippu"

# --- Produccion industrial de Oaxaca (toneladas/ano) ----------------------------
# Solo el cemento tiene emisiones de proceso relevantes en Tabla 7. El resto se
# lleva a niveles marginales: Oaxaca no tiene siderurgia, petroquimica ni vidrio.
PRODINIT_TONNE = {
    "cement":                    1_920_000,   # Cruz Azul, Lagunas (2A1 = 749 kt CO2)
    "chemicals":                         0,   # sin petroquimica de proceso
    "electronics":                       0,
    "glass":                             0,
    "lime_and_carbonite":                0,   # sin produccion de cal relevante
    "metals":                            0,   # sin siderurgia
    "mining":                      500_000,   # mineria metalica menor
    "paper":                        50_000,   # residual (Tuxtepec)
    "plastic":                           0,
    "rubber_and_leather":                0,
    "textiles":                     10_000,
    "wood":                        300_000,   # aserraderos / forestal comunitario
    "recycled_glass":                    0,
    "recycled_metals":                   0,
    "recycled_paper":                    0,
    "recycled_plastic":                  0,
    "recycled_rubber_and_leather":       0,
    "recycled_textiles":                 0,
}

# Uso de productos (HFC, lubricantes, ceras): escala con poblacion, no con PIB
# industrial. 2F1 Refrigeracion y aire acondicionado = 93 kt.
# Calibrado contra 2F1 = 93 kt. Queda por encima de la participacion poblacional
# (3.2%) porque el inventario del PECC contabiliza el banco de HFC en refrigeracion
# comercial y de transporte (cadena de frio agroalimentaria y pesquera) con un
# criterio mas amplio que un simple prorrateo por habitantes.
PRODUCT_USE_SCALAR = 0.096

SRC = ("INEGI Censos Economicos / Anuario estadistico de la mineria; PECC Oaxaca "
       "2016-2022 Tabla 7 (2A1 cemento, 2F1 HFC)")
URL = "https://www.inegi.org.mx/programas/ce/2019/"


def main():
    args = L.cli_io()
    df = L.load(args.io)
    base = L.aligned_baseline()          # eje calendario real (D10)

    rows = []

    def put(col, val, method):
        if col not in df.columns:
            return
        orig = base[col].values[0] if col in base.columns else None
        L.set_col(df, col, val)
        rows.append(dict(variable=col, subsector="ippu",
                         original_value_mex=orig, new_value_oax=val,
                         year=L.BASE_YEAR, method=method,
                         source_name=SRC, source_url=URL, agent=AGENT))

    for cat, tonnes in PRODINIT_TONNE.items():
        put(f"prodinit_ippu_{cat}_tonne", tonnes,
            "produccion industrial estatal (direct replace)")

    # Uso de productos -> escala poblacional
    for cat in ["product_use_ods_refrigeration", "product_use_ods_other",
                "product_use_lubricants", "product_use_paraffin_wax",
                "product_use_other"]:
        put(f"demscalar_ippu_{cat}", PRODUCT_USE_SCALAR,
            f"uso de productos calibrado contra Tabla 7 2F1 ({PRODUCT_USE_SCALAR:.3%})")

    # Materiales por hogar: la construccion sigue a la poblacion, ya reflejada en
    # los drivers gnrl, asi que se conservan los valores nacionales por hogar.

    L.save(df, args.io)
    L.log_change(rows)
    print(f"[ippu] cemento = {PRODINIT_TONNE['cement']:,} t "
          f"(objetivo 2A1 = 749 kt CO2) | resto de industria pesada -> 0")
    print(f"[ippu] uso de productos (HFC) x {PRODUCT_USE_SCALAR:.4f} "
          f"(objetivo 2F1 = 93 kt)")
    print(f"[ippu] {len(rows)} variables escritas")


if __name__ == "__main__":
    main()
