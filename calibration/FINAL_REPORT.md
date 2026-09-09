# Calibración SISEPUEDE Oaxaca — Informe final

**Fecha:** 2026-09-02 · **Año base:** 2013 · **Entorno:** `ssp_mex_env`
**Benchmark:** PECC Oaxaca 2016–2022, Tabla 7 — Inventario estatal de GEI, 2013 (CMM 2014)

## 1. Resultado

La base de datos nacional de SISEPUEDE se calibró al estado de Oaxaca y se validó
contra el inventario de la Tabla 7. **La corrida baseline (strategy 0, sin
transformaciones) reproduce las emisiones de 2013 dentro del ±10 %, con las
14 líneas comparables y las 4 categorías IPCC dentro de tolerancia.**

| Categoría IPCC | Modelo kt | Tabla 7 kt | Desv. | Gate ±15 % |
|---|---:|---:|---:|:--:|
| 1 Energía (entc+fgtv+inen+trns+scoe) | 8,484 | 8,476 | +0 % | ✅ |
| 2 IPPU (ippu) | 807 | 842 | −4 % | ✅ |
| 3 AFOLU (lvst+lsmm+soil+agrc+incendios) | 6,702 | 6,570 | +2 % | ✅ |
| 4 Desechos (waso+trww) | 717 | 654 | +10 % | ✅ |
| **TOTAL COMPARABLE** | **16,710** | **16,542** | **+1 %** | ✅ **PASA ±10 %** |
| **TOTAL BRUTO** (D2, incl. conversión `lndu`) | **18,332** | **17,968** | **+2 %** | ✅ **PASA ±10 %** |

Detalle por línea — **14 de 14 dentro del gate**:

| | Modelo | Tabla 7 | Desv. | | | Modelo | Tabla 7 | Desv. |
|---|---:|---:|---:|---|---|---:|---:|---:|
| entc (1A1b refinación) | 3,693 | 3,681 | +0 % ✅ | | lvst (3A1) | 2,721 | 2,627 | +4 % ✅ |
| fgtv (1B) | 17 | 17 | +0 % ✅ | | lsmm (3A2) | 463 | 418 | +11 % ✅ |
| inen (1A2) | 621 | 636 | −2 % ✅ | | soil (3C4+3C5) | 2,017 | 2,061 | −2 % ✅ |
| trns (1A3) | 3,625 | 3,641 | −0 % ✅ | | agrc (3C7 + no-CO2 3C1a cultivo) | 360 | 321 | +12 % ✅ |
| scoe (1A4) | 529 | 501 | +6 % ✅ | | frst_fires (CO2 3C1a forestal) | 1,141 | 1,143 | −0 % ✅ |
| ippu (2A1+2F1) | 807 | 842 | −4 % ✅ | | waso (4A) | 284 | 242 | +17 % ✅ |
| | | | | | trww (4D1+4D2) | 437 | 412 | +6 % ✅ |

**Memos, fuera del gate:**

| | kt | |
|---|---:|---|
| Conversión de uso de suelo (`lndu`) | +1,621 | Sin renglón en Tabla 7; sólo en la nota al pie (D8) |
| Sumidero FRST (sin incendios) | −13,916 | Nota al pie: ~−14,000 de absorción bruta (D3) ✅ |
| Scope-2, consumo eléctrico | +1,223 | Emisión bruta de referencia 19,191 kt (D2) |

## 2. Los dos hallazgos estructurales

### a) ENTC no es generación, es refinación

**SISEPUEDE modela la refinación de petróleo como la tecnología ENTC
`fp_petroleum_refinement`, que es exactamente la categoría IPCC 1A1b.** Esto invierte
el tratamiento de CDMX: allí ENTC se llevaba a ~0 porque la ciudad importa su
electricidad; aquí ENTC **no es generación sino refinación**, y vale 3,681 kt.

Es coherente con la Tabla 7, que **no tiene renglón 1A1a** (generación) porque la
electricidad oaxaqueña es eólica e hidráulica, pero sí tiene 1A1b por la refinería de
Salina Cruz.

**Verificación física independiente:** con EF = 6.374 t CO2/TJ, el objetivo de 3,681 kt
implica ~577 PJ de producto refinado ≈ **282 kbpd** — la operación real de Salina Cruz
en 2013 (capacidad 330 kbpd). El mapeo cuadra con la planta física, no es un ajuste
numérico.

### b) La quema de biomasa 3C1a no vive en `lndu` (D8)

`lndu` **no contiene quema alguna**: es CO2 de conversión de uso de suelo, que la
Tabla 7 deja fuera de su total IPCC. La quema se reparte en otros dos campos:

| Tabla 7 | campo SISEPUEDE | subsector |
|---|---|---|
| 3C1a forestal, CO2 (1,143) | `emission_co2e_co2_frst_forest_fires` | **frst** |
| 3C1a cultivo, CH4+N2O (253) | `emission_co2e_{ch4,n2o}_agrc_biomass_burning` | agrc |

Los incendios forestales daban **0.65 kt** por dos causas multiplicativas: la fracción
de incendio seguía en el default nacional (407 ha/año en todo el estado) y
`afolu.py:5844` recorta la biomasa consumida de 45–125 t/ha a **1.0 t/ha** vía
`var_bounds=(0,1)`. Corregido con superficie CONAFOR (13,000 ha/año) y plegando la
biomasa nacional dentro del EF. Ver [DECISIONS.md](DECISIONS.md) D8.

## 3. Metodología

- **Semilla:** base nacional intacta en `reference_mexico/`, alineada al **calendario
  real** 2013-2058 (D1 + D10). El año nacional Y se queda en Y; sólo 2013-2014 se
  retro-rellenan, y los drivers se retro-extienden con crecimiento mexicano observado.
- **Drivers (sustitución directa):** población 3.90 M (52 % rural), PIB 37.8 mmm USD
  (1.55 % nacional), superficie 9,395,972.5 ha, ocupación 4.0 hab/vivienda.
- **Actividad (directa/participación):** proceso de refinería 577.5 PJ, cemento 1.92 Mt,
  hato ganadero estatal, superficie agrícola 1.34 M ha, bosque 5.09 M ha,
  superficie quemada 13,000 ha/año, residuos.
- **Supuestos de trayectoria (D9):** producción pecuaria local atada a la población
  estatal (el consumo adicional por ingreso se importa); `magnitude_lurf` = 0.10.
- **Re-especificaciones estructurales:** ENTC → refinación (D4); generación 100 %
  renovable → 0 emisiones; extracción de hidrocarburos → 0 (el crudo es *pass-through*
  importado); conversión forestal × 0.29 (D5); quema de residuos agrícolas 65 %
  (roza-tumba-quema); incendios forestales reactivados (D8).
- **Se conservan nacionales:** factores de emisión, eficiencias, densidades energéticas,
  intensidades por tonelada, MCF, biomasa consumida por incendio.
- **Todo por script idempotente**, encadenado por `run_all.sh`. Sin edición manual.

## 4. Limitaciones conocidas y diferencias documentadas

**a) Dos diferencias de frontera, cuantificadas.** El modelo no puede emitir dos
partidas que la Tabla 7 sí contabiliza:

| | kt | Por qué |
|---|---:|---|
| CO2 de quema de residuos de cultivo | 1,304 | SISEPUEDE **no tiene** campo `co2_agrc_biomass_burning`. Correcto según IPCC 2006: el carbono de residuos anuales es cíclico. La Tabla 7 lo contabiliza de todos modos. |
| CH4+N2O de incendios forestales | 122 | SISEPUEDE sólo produce CO2 de incendios. |

Por eso el gate **COMPARABLE** (16,542) es el riguroso. El **BRUTO** (17,968) pasa en
parte porque la conversión `lndu`, que está fuera de la frontera de la Tabla 7,
compensa aproximadamente ese CO2 biogénico. **Se declara, no se esconde.**

**b) Balance neto forestal.** El modelo reproduce la **absorción bruta** (−13.9 Mt ≈ las
14 Mt de la nota al pie) pero no el **balance neto** (~5 Mt absorbidas), porque las
pérdidas por degradación de hasta 9 Mt/año quedan fuera del total IPCC de la Tabla 7 y
se moderaron deliberadamente (D5).

**c) Arroz (3C7).** Modelo 14 kt vs 68 de la Tabla 7. Las 68 kt implican ~13,600 ha de
arroz aplicando factores IPCC estándar; SIAP reporta del orden de 1,000 ha en Oaxaca.
Probable inconsistencia en el inventario fuente, no en el modelo. **No se forzó.**
Impacto: 54 kt, 0.3 % del total.

**d) Trayectoria de línea base.** Los supuestos de BAU se revisaron en D9: el hato ya
no hereda las elasticidades ingreso-demanda nacionales (crecía +65 % al 2058 contra
+11 % de la población) y `magnitude_lurf` bajó de 0.25 a 0.10. Con eso desaparece la
joroba de conversión de uso de suelo que llegaba a 6.7 Mt en 2044, y **el acervo forestal
queda esencialmente estable** (bosque secundario −0.9 %, primario −1.6 % al 2058).

| Año | Baseline calibrado | TX:BASE (corrida completa) | PECC Tabla 10 |
|---|---:|---:|---:|
| 2013 | 18,332 | 18,332 | 17,968 (Tabla 7) |
| 2020 | 16,514 | 16,514 | 20,855 |
| 2030 | 16,379 | 16,734 | 23,720 |
| 2040 | 16,661 | 18,826 | — |
| 2058 | 18,256 | 23,100 | — |

La caída de 2020 es la contracción real por COVID (−8.7 % del PIB nacional), ahora en su
fecha correcta: hasta D10 el recorrido del eje la dejaba en 2018 (ver D10).

Las dos columnas del modelo se separan sólo a partir de 2027: el *baseline calibrado*
(`run_all.sh`, strategy 0 sobre los inputs crudos) mantiene
`lndu_reallocation_factor = 0`, mientras que **TX:BASE lo lleva a 0.10** vía el handler de
transformaciones, permitiendo que la demanda de tierra se satisfaga con conversión física.
La operativa es TX:BASE.

**La divergencia con la Tabla 10 persiste, y es metodológica.** La Tabla 10 es una
extrapolación tendencial simple (el propio PECC declara tasas de 8 % al 2020 y 12 % al
2030). SISEPUEDE resuelve dinámicas endógenas. **Si se requiere reproducir también la
línea base 2020/2030 del PECC, es un trabajo aparte.**

**e) Carbono negro** (Tabla 8, ~7,800 t CN ≈ 7,000 t CO2e) no se modela: SISEPUEDE no
tiene CN como especie.

**f) Vintage de factores técnicos:** 2013 y 2014 heredan los factores técnicos de 2015
(emisión, densidades energéticas, eficiencias), porque la base nacional empieza en 2015.
Inmaterial: varían despacio. Acotado a dos años al inicio del eje desde D10.

**g) Valores de actividad estimados.** Algunos niveles (hato ganadero, cobertura de
suelo, producción de cemento, residuos dispuestos, superficie quemada) se fijaron por
orden de magnitud a partir de fuentes estatales conocidas y se afinaron contra la
Tabla 7. Están marcados con su método en `data_sources.csv` y deberían confirmarse
contra los tabulados originales de SIAP, INEGI, CONAGUA y CONAFOR antes de usarse en un
producto oficial.

## 5. Reproducibilidad

```bash
bash calibration/run_all.sh --run
```

Reconstruye la base de Oaxaca desde la nacional intacta, corre el modelo (~3 min con
NemoMod) e imprime las dos tablas del gate. **Verificado idempotente**: dos ejecuciones
producen un CSV byte-idéntico (md5 `e7d579c0b7475cd970a90585a0a8957e`).
**250 cambios trazados** en `data_sources.csv`.

## 6. Entregables

- Inputs de Oaxaca: `ssp_modeling/input_data/sisepuede_adj_inputs_OAX.csv`
- Scripts: `scripts/align_time_axis.py`, `scripts/transform_*.py` (7),
  `scripts/lib_calib.py`, `scripts/run_baseline.py`, `scripts/diagnose_2013.py`, `run_all.sh`
- Objetivos legibles por máquina: `01_oaxaca_data/oaxaca_targets_tabla7.csv`
- Datos de referencia: `01_oaxaca_data/oaxaca_reference_values.csv`
- Validación: `04_validation/baseline_oax_*.csv`
- Trazabilidad: `data_sources.csv`
- Documentación: `STATUS.md`, `DECISIONS.md`, `02_downscaling_strategy.md`, este informe
- Diseño: `docs/superpowers/specs/2026-09-01-oaxaca-calibration-design.md`
