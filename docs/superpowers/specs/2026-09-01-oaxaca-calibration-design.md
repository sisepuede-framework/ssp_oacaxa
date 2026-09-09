# SISEPUEDE Oaxaca Calibration — Design

**Date:** 2026-09-01
**Goal:** a SISEPUEDE **baseline run (strategy 0, no transformations)** whose **2013**
emissions reproduce **Tabla 7 del PECC Oaxaca 2016–2022** (Inventario estatal de GEI, 2013).
**Method:** the CDMX calibration methodology, re-specified for Oaxaca's very different
emissions structure.

---

## 1. The target — Tabla 7 (miles t CO₂e, 2013)

Source: *Programa Especial de Cambio Climático del Estado de Oaxaca 2016–2022*, Tabla 7,
p. 78–79. Attributed to **CMM, 2014**. GWP-100 (IPCC AR4, per Tabla 9: CH₄ 25, N₂O 298).

| Categoría IPCC | CO₂ | CH₄ | N₂O | HFC | **Total** |
|---|---:|---:|---:|---:|---:|
| **1 Energía** | 8,179 | 194 | 104 | NA | **8,476** |
| 1A1 Industrias de la energía | 3,673 | 3 | 5 | NA | 3,681 |
| · 1A1b Refinación del petróleo | 3,673 | 3 | 5 | NA | 3,681 |
| 1A2 Industrias manufactureras y de construcción | 603 | 13 | 20 | NA | 636 |
| · 1A2c Sustancias químicas | | | | NA | 1 |
| · 1A2d Pulpa, papel e imprenta | 149 | | | NA | 149 |
| · 1A2e Procesamiento de alimentos, bebidas y tabaco | 62 | 13 | 18 | NA | 93 |
| · 1A2f Minerales no metálicos | 391 | | | NA | 392 |
| · 1A2j Madera y productos de la madera | | | | NA | ~0 |
| · 1A2m Ladrilleras | NA | | | NA | 1 |
| 1A3 Transporte | 3,566 | 28 | 47 | NA | 3,641 |
| · 1A3a Aviación | 212 | | | NA | 212 |
| · 1A3b Transporte terrestre | 3,069 | 27 | 43 | NA | 3,139 |
| · 1A3c Ferrocarriles | 12 | | 1 | NA | 13 |
| · 1A3d Navegación marítima y fluvial | 2 | | | NA | 2 |
| · 1A3eiii Maquinaria de construcción | 9 | | | NA | 9 |
| · 1A3eiii Tractores y maquinaria agrícola | 261 | 1 | 2 | NA | 264 |
| 1A4 Otros sectores | 337 | 132 | 31 | NA | 501 |
| · 1A4a Combustión Comercial/Institucional | 49 | | | NA | 49 |
| · 1A4b Combustión Residencial de GLP | 287 | | | NA | 287 |
| · 1A4b Combustión Residencial de leña | NA | 131 | 31 | NA | 162 |
| · 1A4b Combustión Agrícola | 2 | | | NA | 2 |
| 1B Emisiones fugitivas | NA | 17 | NA | NA | **17** |
| · 1B2aiii.4 Refinación del petróleo | NA | 17 | NA | NA | 17 |
| **2 Procesos industriales y uso de productos** | 749 | NA | NA | 93 | **842** |
| · 2A1 Producción de cemento | 749 | NA | NA | NA | 749 |
| · 2F1 Refrigeración y aire acondicionado (HFC) | NA | NA | NA | 93 | 93 |
| **3 AFOLU** | 2,447 | 3,278 | 2,271 | NA | **7,996** |
| · 3A1 Fermentación entérica | NA | 2,627 | NA | NA | 2,627 |
| · 3A2 Manejo de estiércol | NA | 312 | 106 | NA | 418 |
| · 3C1a Quemado de biomasa en tierras forestales | 1,143 | 78 | 44 | NA | 1,265 |
| · 3C1a Quemado de biomasa en tierras de cultivo | 1,304 | 193 | 60 | NA | 1,557 |
| · 3C4 Emisiones directas de N₂O de suelos gestionados | NA | NA | 1,862 | NA | 1,862 |
| · 3C5 Emisiones indirectas de N₂O de suelos gestionados | NA | NA | 199 | NA | 199 |
| · 3C7 Cultivo de arroz | NA | 68 | NA | NA | 68 |
| **4 Desechos** | NA | 589 | 65 | NA | **654** |
| · 4A Eliminación de desechos sólidos | NA | 242 | NA | NA | 242 |
| · 4D1 Aguas residuales domésticas | NA | 212 | 65 | NA | 276 |
| · 4D2 Aguas residuales industriales | NA | 136 | NA | NA | 136 |
| **Emisiones de las categorías IPCC** | **11,375** | **4,060** | **2,440** | **93** | **17,968** |
| Emisiones indirectas por consumo de energía eléctrica | 1,216 | 1 | 5 | NA | 1,223 |
| **Emisión bruta** | **12,591** | **4,061** | **2,445** | **93** | **19,191** |

**Nota al pie (Tabla 7):** los macizos de bosques y selvas de Oaxaca podrían absorber
~**14 Mt CO₂e/año**; AFOLU puede a la vez perder capacidad de absorción de hasta
**9 Mt/año**; balance neto promedio de los últimos 18 años ≈ **5 Mt CO₂e absorbidas/año**.

**Contexto (p. 77):** 19 Mt CO₂e = **2.8 %** de las emisiones nacionales; intensidad de
carbono 1,000 USD/tCO₂e; emisión per cápita **4.8 tCO₂e**.

---

## 2. Structural decisions

### D1 — Base year and time axis
`time_period 0 = 2013`; the run covers **2013–2058** (46 periods, matching the current
46-period run length). The Mexico national input DB is indexed 2015–2070; the Oaxaca DB
shifts the `year` column by **−2** so the target year exists literally in the run.
`run_baseline.py` already builds the SISEPUEDE time attribute from `--y0/--y1`, so no
model-side change is required beyond passing `--y0 2013 --y1 2058`.

*Rejected:* keeping the 2015 axis and treating model-2015 as the 2013 benchmark (adds an
undocumentable 2-year drift to every driver); extending the DB backwards to 2013 while
keeping 2070 (requires fabricating two years of national drivers).

### D2 — Emissions scope and gate
**Gate against 17,968 kt CO₂e** — the *Emisiones de las categorías IPCC* subtotal, i.e.
direct territorial emissions only. This is the clean analogue of the CDMX Scope-1
convention and the only quantity SISEPUEDE produces natively.

The **1,223 kt of indirect electricity-consumption emissions are a Scope-2 memo item**,
reported separately, not modeled as territorial emissions. Forcing them into ENTC would
contradict the inventory itself, which attributes **no** emissions to in-state generation.

**Tolerances:** total **±10 %** (≈16,171–19,765 kt); each of Tabla 7's four IPCC
categories **±15 %**.

### D3 — FRST sink
The FRST sink is **excluded from the gross gate** (Tabla 7 is a source-only inventory),
**and calibrated** so the modeled absorption lands in the range the Tabla 7 footnote
gives: ~14 Mt/yr gross forest absorption, net balance ~5 Mt/yr absorbed. Reported as a
separate line in the validation table.

### D4 — Electricity
Oaxaca is a net electricity **exporter** (Istmo de Tehuantepec wind, hydro), yet Tabla 7
has **no 1A1a generation row** — because that generation is overwhelmingly renewable.
The model must therefore produce **~0 emissions from power generation** while ENTC still
carries the refinery (see §3). Electricity *demand* remains needed for the energy balance.

### D5 — Repository structure
`calibration/` is rewritten for Oaxaca (the CDMX calibration lives in a separate
repository folder maintained by the user). The untouched national baseline
`calibration/reference_mexico/sisepuede_adj_inputs_MEX.baseline.csv` is **preserved** —
it is the seed for every rebuild. Output: `ssp_modeling/input_data/sisepuede_adj_inputs_OAX.csv`.

---

## 3. Subsector mapping and per-sector targets

The single most important structural finding: SISEPUEDE's **ENTC includes
`fp_petroleum_refinement`** as a fuel-production technology with its own
`nemomod_entc_emissions_activity_ratio_fuel_production_fp_petroleum_refinement_tonne_{co2,ch4,n2o}_per_tj`.
The Salina Cruz refinery therefore maps **natively** onto ENTC — which is exactly IPCC
category 1A1b. **Oaxaca's ENTC target is not zero**, inverting the CDMX treatment.

| SISEPUEDE | Tabla 7 rows | Target (kt CO₂e) | vs CDMX |
|---|---|---:|---|
| `entc` | 1A1b Refinación 3,681 + 1A1a generación 0 | **3,681** | ⚠️ inverted (CDMX → 0) |
| `fgtv` | 1B2aiii.4 Refinación | **17** | ⚠️ inverted (CDMX → 0) |
| `inen` | 1A2 Manufactureras y construcción | **636** | similar magnitude |
| `trns` | 1A3 Transporte | **3,641** | 20 % of total, not 76 % |
| `scoe` | 1A4 Otros sectores | **501** | leña (162) is new |
| `ippu` | 2A1 Cemento 749 + 2F1 HFC 93 | **842** | ⚠️ inverted (CDMX → 0) |
| `lvst` | 3A1 Fermentación entérica | **2,627** | ⚠️ inverted (CDMX ~0) |
| `lsmm` | 3A2 Manejo de estiércol | **418** | ⚠️ inverted |
| `soil` | 3C4 1,862 + 3C5 199 | **2,061** | ⚠️ inverted |
| `agrc` | 3C7 arroz 68 + 3C1a quema cultivos 1,557 | **1,625** | ⚠️ inverted |
| `lndu` | 3C1a quema biomasa tierras forestales | **1,265** | ⚠️ inverted |
| `waso` | 4A Eliminación de desechos sólidos | **242** | |
| `trww` | 4D1 276 + 4D2 136 | **412** | |
| `enfu`, `enst`, `wali`, `ccsq` | (no direct emissions) | — | supporting |
| **TOTAL** | | **17,968** | |
| `frst` | — (excluded from gate, D3) | ~−14,000 memo | |

**Open mapping question (resolve empirically in Phase 3):** whether SISEPUEDE routes
biomass-burning emissions for forest land through `lndu` or `frst`, and cropland burning
through `agrc` or `lndu`. The split of the 2,822 kt of 3C1a burning between `lndu`/`agrc`
will be assigned to whichever subsectors actually carry it in model output.

**Rolled up to Tabla 7's four categories (gate ±15 % each):**

| Categoría | SISEPUEDE subsectors | Target |
|---|---|---:|
| Energía | entc + fgtv + inen + trns + scoe | 8,476 |
| IPPU | ippu | 842 |
| AFOLU | lvst + lsmm + soil + agrc + lndu | 7,996 |
| Desechos | waso + trww | 654 |

---

## 4. Downscaling method

Identical in kind to CDMX; only the denominators change.

| Kind | Examples | Treatment |
|---|---|---|
| **Drivers** | population, GDP, households | **Direct replace** with Oaxaca values/trajectories |
| **Activity** | refinery throughput, cement output, vkm, livestock heads, burned area, waste tonnage, land area | **Direct** where an Oaxaca figure exists; else **share-downscale** national × matched share |
| **Technical factors** | `ef_*`, `frac_*`, efficiencies, energy densities, MCF | **Keep national** (fuel chemistry / technology identical) |

**Known anchors:**
- Superficie estatal **9,395,972.535 ha** (Marco Geoestadístico, feb 2018).
- Población ~**3.9 M** (INEGI intercensal 2015); 2013 ≈ 3.86 M → ≈ **3.26 %** nacional.
  Cross-check from the PDF: 19,191 kt ÷ 4.8 tCO₂e per cápita ≈ 4.0 M ✓.
- Emisiones = **2.8 %** de las nacionales (PDF p. 77) — a useful sanity bound: the national
  2013 baseline scaled flat would give ~2.8 %, but the *composition* differs sharply.
- PIB estatal ≈ **1.5 %** nacional (to be confirmed from INEGI PIBE in Phase 1).

**Inverse calibration is reserved** for subsectors where the Tabla 7 target dominates and
observed Oaxaca activity is unpublished — expected: transporte terrestre, quema de
biomasa, aguas residuales industriales. Each such case is flagged as `inverse` in the
`method` column of `data_sources.csv`.

**Every changed value → one row in `data_sources.csv`** (variable, subsector,
original_value_mex, new_value_oax, year, method, source_name, source_url, agent, date).
All changes via idempotent scripts in `calibration/scripts/` — no manual CSV edits.

---

## 5. Calibration order (by leverage)

1. **gnrl** (socioeconomic) — foundation for every downscaled value.
2. **afolu** (`lvst`, `lsmm`, `soil`, `agrc`, `lndu`, `frst`) — **7,996 kt = 44 %**, the
   dominant sector. CDMX did this last; Oaxaca does it second.
3. **energy-supply** (`entc`, `enfu`, `fgtv`) — the refinery, 3,698 kt, plus renewable
   generation → ~0.
4. **transport** (`trns`, `trde`) — 3,641 kt.
5. **ippu** — 842 kt (cemento + HFC).
6. **buildings-industry** (`scoe`, `inen`) — 1,137 kt.
7. **waste** (`waso`, `trww`, `wali`) — 654 kt.

---

## 6. Components

Each is a single-purpose, independently runnable unit reading and writing the same working
CSV in place, mutating only its own subsector's columns, and idempotent (absolute values,
never incremental scaling).

| Component | Responsibility |
|---|---|
| `scripts/lib_calib.py` | shared load/save/set/log helpers + `data_sources.csv` writer |
| `scripts/shift_time_axis.py` | seed OAX CSV from the MEX baseline and shift `year` by −2 |
| `scripts/transform_socioeconomic.py` | `gnrl` drivers |
| `scripts/transform_afolu.py` | `lvst`, `lsmm`, `soil`, `agrc`, `lndu`, `frst` |
| `scripts/transform_energy_supply.py` | `entc` (refinería + generación renovable), `enfu`, `fgtv` |
| `scripts/transform_transport.py` | `trns`, `trde` |
| `scripts/transform_ippu.py` | `ippu` |
| `scripts/transform_buildings_industry.py` | `scoe`, `inen` |
| `scripts/transform_waste.py` | `waso`, `trww`, `wali` |
| `scripts/run_baseline.py` | run SISEPUEDE (strategy 0) with `--y0 2013 --y1 2058` |
| `scripts/diagnose_2013.py` | print the gate table: model vs Tabla 7, per subsector and per IPCC category |
| `run_all.sh` | seed → chain transforms → (`--run`) run model + print gate |
| `01_oaxaca_data/oaxaca_targets.csv` | Tabla 7 machine-readable |
| `01_oaxaca_data/oaxaca_reference_values.csv` | curated Oaxaca activity/driver values with sources |

**Data flow:** `MEX.baseline.csv` → `shift_time_axis` → `sisepuede_adj_inputs_OAX.csv`
→ (7 transform scripts, in place) → `run_baseline.py` → `baseline_oax_emissions_by_subsector.csv`
→ `diagnose_2013.py` → gate table.

---

## 7. Verification

- **Gate:** total 2013 emissions within ±10 % of 17,968 kt; each IPCC category within ±15 %.
- **Convergence log:** total after each sector script, appended to
  `04_validation/convergence_log.csv`, so every step's contribution is visible.
- **Idempotence check:** running `run_all.sh` twice produces a byte-identical OAX CSV.
- **Traceability check:** every column the scripts touch has a row in `data_sources.csv`.
- **Sanity bound:** Oaxaca total ≈ 2.8 % of the national baseline total (PDF p. 77).

## 8. Known risks

- **Biomass burning routing** (§3) — 2,822 kt, 16 % of the target, mapped to
  `lndu`/`agrc` pending empirical confirmation of where the model reports it.
- **Refinery in NemoMod** — `fp_petroleum_refinement` is driven by fuel demand; forcing a
  fixed 3,681 kt may require constraining refinery throughput rather than the EF, so the
  optimization stays internally consistent.
- **Renewable generation** — ENTC must satisfy demand with wind/hydro to reproduce zero
  generation emissions; NemoMod may substitute fossil capacity unless capacity/min-share
  is constrained.
- **2013 vs 2015 national drivers** — shifting the axis re-labels 2015 national data as
  2013; drivers are replaced with Oaxaca values anyway, but retained national technical
  factors carry a 2-year vintage offset (documented, immaterial for EFs).
