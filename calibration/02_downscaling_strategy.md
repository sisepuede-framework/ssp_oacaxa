# Estrategia de downscaling — Oaxaca

**Benchmark:** PECC Oaxaca 2016–2022, Tabla 7 = **17,968 kt CO2e** (categorías IPCC), 2013.
**Datos de referencia:** [01_oaxaca_data/oaxaca_reference_values.csv](01_oaxaca_data/oaxaca_reference_values.csv).
**Objetivos legibles por máquina:** [01_oaxaca_data/oaxaca_targets_tabla7.csv](01_oaxaca_data/oaxaca_targets_tabla7.csv).

## 0. Principios generales

Misma taxonomía que en CDMX; sólo cambian los denominadores.

| Tipo | Ejemplos | Tratamiento |
|---|---|---|
| **Drivers** (socioeconómicos) | población, PIB, hogares, superficie | **Sustitución directa** por valores/trayectorias de Oaxaca |
| **Niveles de actividad** | proceso de refinería, producción de cemento, vkm, cabezas de ganado, tonelaje de residuos, superficie | **Directo** donde existe cifra estatal; si no, **downscale por participación** |
| **Factores técnicos** | `ef_*`, `frac_*`, eficiencias, densidades energéticas, MCF | **Se conservan nacionales** (química del combustible y tecnología idénticas) |

**Calibración inversa** reservada para subsectores donde el objetivo domina y no hay
actividad estatal publicada. Cada caso queda marcado en la columna `method` de
`data_sources.csv`.

## 1. Oaxaca invierte casi todos los supuestos de CDMX

Esta es la diferencia central del proyecto y la razón por la que no basta con cambiar cifras:

| | CDMX | Oaxaca |
|---|---|---|
| Participación poblacional | 7.3 % | **3.20 %** |
| Participación en PIB | 15.0 % (≈2× la poblacional) | **1.55 %** (≈½ la poblacional) |
| Perfil territorial | 100 % urbano, población **decreciente** | **52 % rural**, población **creciente** (pero más lento que el país) |
| Sector dominante | Transporte, 76 % | **AFOLU, 44 %** |
| ENTC | → ~0 (importa 99.9 % de su electricidad) | **3,681 kt de refinación** (Salina Cruz) |
| FGTV | → ~0 | 17 kt (sólo refinación) |
| IPPU | → ~0 (sin industria pesada) | **842 kt** (cemento Cruz Azul + HFC) |
| AFOLU | ~67 kt | **7,996 kt** |
| Electricidad | importador casi total | **exportador** (eólica del Istmo) |
| Residuos | exportados a rellenos sanitarios del Edomex | dispuestos en **tiraderos a cielo abierto** propios |

**Consecuencia práctica:** en CDMX el trabajo consistía en *colapsar* sectores a cero.
En Oaxaca hay que *reconstruirlos con la estructura correcta* — una refinería, una
cementera, un hato ganadero grande y un territorio forestal enorme.

## 2. Orden de calibración (por apalancamiento)

1. **gnrl** (socioeconómico) — base de todo lo demás. Primero, siempre.
2. **afolu** — 7,996 kt = 44 %. En CDMX iba al final; aquí va segundo.
3. **energy-supply** (entc/enfu/fgtv) — la refinería, 3,698 kt, y generación renovable → ~0.
4. **transport** (trns/trde) — 3,641 kt.
5. **ippu** — 842 kt; **además arrastra a INEN** (la energía industrial se calcula por
   tonelada producida), así que debe ir antes que buildings-industry.
6. **buildings-industry** (scoe/inen) — 1,137 kt.
7. **waste** (waso/trww/wali) — 654 kt.

## 3. Palancas por subsector

| Subsector | Objetivo | Palanca principal |
|---|---:|---|
| gnrl | drivers | `population_gnrl_{rural,urban}`, `gdp_mmm_usd`, `area_gnrl_country_ha`, `occrateinit_gnrl_occupancy` |
| entc | 3,681 | `exports_enfu_pj_fuel_*` (dimensiona la refinería) + mezcla de generación 100 % renovable vía `nemomod_entc_frac_min_share_production_pp_*` y `residual_capacity` |
| fgtv | 17 | `ef_fgtv_*_fuel_crude` (columnas **creadas**, ver D7) + anulación de fugas de producción |
| inen | 636 | `prodinit_ippu_*` (vía IPPU) + `consumpinit_inen_energy_tj_per_mmm_gdp_other_product_manufacturing` + `consumpinit_inen_energy_total_pj_agriculture_and_livestock` |
| trns | 3,641 | `demscalar_trde_{private_and_public,freight,regional}` = 0.081 |
| scoe | 501 | `consumpinit_scoe_gj_per_hh_residential_*`, `consumpinit_scoe_tj_per_mmmgdp_commercial_*` |
| ippu | 842 | `prodinit_ippu_cement_tonne` = 1.92 M t; resto de industria pesada → 0; `demscalar_ippu_product_use_*` = 0.096 |
| lvst / lsmm | 2,627 / 418 | `pop_lvst_initial_*` (hato estatal real) |
| soil | 2,061 | `demscalar_soil_fertilizer_n_per_area` = 0.09 (agricultura de temporal) |
| agrc | 321 (3C7 + no-CO2 de 3C1a cultivo) | `frac_agrc_crop_residues_burned` = 0.65 (roza-tumba-quema) |
| frst_fires | 1,143 (CO2 de 3C1a forestal) | `frac_frst_annual_wildfire_fraction_*` (13,000 ha/año, CONAFOR) + `ef_frst_forestfires_*_co2` con la biomasa plegada (D8) |
| lndu | memo, sin renglón en Tabla 7 | `frac_lndu_initial_*` + `pij_lndu_forests_*` × 0.29 |
| frst | ~−14,000 memo | `ef_frst_sequestration_primary_kt_co2_ha` = 0.003757 |
| waso | 242 | `qty_waso_initial_municipal_waste_tonne_per_capita`, `frac_waso_non_recycled_*`, `mcf_waso_average_open_dump` |
| trww | 412 | `gasrf_trww_*` / `mcf_trww_*` × 0.55 |

## 4. Advertencia crítica: variables ausentes ≠ variables en cero

`add_missing_cols` rellena toda columna ausente con el **default del ejemplo de
SISEPUEDE (otro país)**. Poner en cero los `ef_fgtv_*` presentes **no** anuló las
fugitivas, porque los factores del crudo simplemente no existían en la base nacional y
se rellenaron solos con 9,292 kt espurios. Usar `lib_calib.ensure_col()` para crear la
columna. Ver [DECISIONS.md](DECISIONS.md) D7.

## 4b. Advertencia crítica: SISEPUEDE recorta insumos en silencio

`extract_model_variable(..., var_bounds=(0,1))` corre con
`force_boundary_restriction=True` por defecto: **todo valor fuera del rango se recorta
y sólo se emite un `warnings.warn`**. En `afolu.py:5844` y `:5866` esto aplica a
`qty_frst_biomass_consumed_by_fire_*_tonne_per_ha`, cuyos valores reales (45–125 t/ha)
quedan en **1.0 t/ha** — un factor ~50 perdido sin error. Combinado con una fracción de
incendio nunca calibrada, los incendios forestales daban 0.65 kt contra 1,143.

**Regla práctica:** antes de dar por bueno un subsector cercano al objetivo, verificar
que los campos de salida que lo componen son los que uno cree. En `lndu` el número
cuadraba a +28 % midiendo un fenómeno distinto del de la Tabla 7.
Ver [DECISIONS.md](DECISIONS.md) D8.

## 5. Trazabilidad

Todo valor modificado genera una fila en `data_sources.csv` (variable, subsector, valor
MEX original, valor OAX, año, método, fuente, URL, agente, fecha). Todos los cambios
pasan por scripts idempotentes en `scripts/`; **no hay edición manual del CSV**.
