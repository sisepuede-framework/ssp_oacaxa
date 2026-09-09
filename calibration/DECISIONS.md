# Bitácora de decisiones estructurales — Calibración Oaxaca

Benchmark: **PECC Oaxaca 2016–2022, Tabla 7 (Inventario estatal de GEI, 2013)**,
atribuida a CMM 2014, con PCG-100 del AR4 (CH4 25, N2O 298; Tabla 9 del PECC).

---

## D1 — Año base y eje temporal (2026-09-01)

**Decisión (usuario):** recorrer el eje a 2013 → `time_period` 0 = **2013**,
corrida **2013–2058** (46 periodos).

**Problema:** la base nacional está indexada 2015–2070, así que **2013 no existía en la
corrida**. El objetivo del proyecto es reproducir un inventario de 2013.

**Implementación:** `scripts/shift_time_axis.py` recorre la columna `year` en −2 sobre
la base nacional intacta. `run_baseline.py` ya construye el atributo temporal de
SISEPUEDE a partir de `--y0/--y1`, así que no hizo falta tocar el modelo.

**Consecuencia documentada:** el recorrido reetiqueta datos nacionales de vintage 2015
como 2013. Todos los *drivers* se sustituyen después por valores oaxaqueños, de modo que
el único desfase residual queda en los factores técnicos nacionales retenidos (factores
de emisión, densidades energéticas), donde 2 años son inmateriales.

> ⚠️ **ESTA CONSECUENCIA ESTABA MAL EVALUADA — corregido en D10.** Era cierta para los
> factores técnicos, pero incompleta: el recorrido también movió **historia macro
> fechada**. La base nacional trae la contracción real de 2020 por COVID (−8.7 % del PIB)
> y el desplazamiento la dejó en la etiqueta 2018. El modelo afirmaba que Oaxaca tuvo
> recesión en 2018 y se recuperó en 2019-2020: exactamente al revés. **D10 sustituye el
> recorrido por una alineación de calendario real.**

**Alternativas descartadas:** mantener el eje 2015 y tratar 2015 como 2013 (introduce
una deriva de 2 años en cada driver, imposible de documentar limpiamente); extender la
base hacia atrás conservando 2070 (exige fabricar dos años de drivers nacionales).

---

## D2 — Alcance de emisiones y gate (2026-09-01)

**Decisión (usuario):** validar contra **17,968 kt CO2e**, el subtotal *Emisiones de
las categorías IPCC* — emisiones **directas territoriales** únicamente.

**Las 1,223 kt de emisiones indirectas por consumo de energía eléctrica son un memo
Scope-2**, se reportan por separado y NO se modelan como emisión territorial. Forzarlas
dentro de ENTC contradiría al propio inventario, que **no atribuye emisión alguna a la
generación dentro del estado** (Tabla 7 no tiene renglón 1A1a).

Este es el análogo limpio de la convención Scope-1 usada en CDMX, y es la única
magnitud que SISEPUEDE produce de forma nativa.

**Tolerancias:** total **±10 %** (16,171–19,765 kt); cada una de las cuatro categorías
IPCC de la Tabla 7, **±15 %**.

**Alternativa descartada:** usar la *Emisión bruta* de 19,191 kt.

---

## D3 — Sumidero forestal FRST (2026-09-01)

**Decisión (usuario):** **excluir el sumidero del gate bruto** (Tabla 7 es un
inventario de FUENTES) **y además calibrarlo** al rango de la nota al pie.

**Nota al pie de Tabla 7:** los macizos de bosques y selvas de Oaxaca "podrían absorber
alrededor de **14 millones de toneladas de CO2 equivalente anuales**"; AFOLU puede a la
vez perder capacidad de absorción de hasta 9 Mt/año; balance neto ≈ 5 Mt absorbidas/año.

**Implementación:** con el factor nacional el modelo daba sólo −10.5 Mt. El valor
nacional de captura para bosque primario (0.70 t CO2/ha/año) refleja el promedio del
país, dominado por bosque seco y degradado, no los bosques mesófilos y selvas altas de
Oaxaca (Chimalapas, Sierra Norte). Se calibró
`ef_frst_sequestration_primary_kt_co2_ha` = 0.003757 (3.76 t CO2/ha/año) →
**FRST = −13,916 kt**, dentro del rango de la nota al pie.

**Limitación documentada:** el modelo reproduce la **absorción bruta** (~14 Mt) pero no
el **balance neto** (~5 Mt), porque las pérdidas por degradación/deforestación de hasta
9 Mt/año quedan fuera del total IPCC de la Tabla 7 y se moderaron deliberadamente
(ver D5).

---

## D4 — ENTC: la refinación, no la generación (2026-09-01)

**Hallazgo estructural, y la inversión más importante respecto de CDMX.**

SISEPUEDE modela la refinación de petróleo como la tecnología ENTC
**`fp_petroleum_refinement`**, con sus propios
`nemomod_entc_emissions_activity_ratio_fuel_production_fp_petroleum_refinement_tonne_{co2,ch4,n2o}_per_tj`.
Esa tecnología **es exactamente la categoría IPCC 1A1b**.

| | CDMX | Oaxaca |
|---|---|---|
| ENTC | → ~0 (importa 99.9 % de su electricidad) | **3,681 kt de REFINACIÓN** (Salina Cruz) |
| Generación eléctrica | fuera de alcance (importada) | ~0 emisiones: eólica del Istmo + hidro |
| FGTV | → ~0 | 17 kt, sólo refinación |
| IPPU | → ~0 | 842 kt (cemento + HFC) |
| AFOLU | ~0.067 Mt | **7,996 kt = 44 % del total** |
| Transporte | 76 % del total | 20 % del total |

**Consistencia física verificada:** con EF = 6.374 t CO2/TJ, el objetivo de 3,681 kt
implica ~577 PJ de producto refinado ≈ **282 kbpd**, que es la operación real de Salina
Cruz en 2013 (capacidad 330 kbpd). El mapeo no es un ajuste: cuadra con la planta real.

**Dos artificios de control, ambos documentados en el script:**

1. **El crudo se marca como suministro interno** (`frac_enfu_fuel_demand_imported_pj_fuel_crude = 0`).
   Si se marca como importado, NemoMod importa producto ya refinado y la refinería nunca
   opera (verificado empíricamente: entc = 0). La corrección territorial se hace anulando
   los insumos energéticos de `me_crude` → el crudo entra como *pass-through* con **cero
   emisiones de extracción**, que es lo correcto: llega de Campeche/Tabasco y esas
   emisiones pertenecen a los estados productores.

2. **Todos los refinados se marcan como importados para el consumo local**, de modo que
   la refinación queda gobernada únicamente por las exportaciones. Si la demanda local de
   un producto *menor* se obliga a refinación local, NemoMod sobredimensiona la planta:
   el fuel oil es sólo 1.4 % del rendimiento, así que cubrir su demanda localmente exigía
   ~14,000 PJ de proceso (verificado: entc disparado a 44,432 kt). Las emisiones de
   combustión del consumo local se contabilizan igual en trns/scoe/inen, y las
   importaciones no acarrean emisiones territoriales, así que el inventario no se altera.

---

## D5 — Conversión de uso de suelo (2026-09-01)

El modelo nacional arrastra tasas de deforestación que, aplicadas a la cobertura forestal
oaxaqueña, generaban ~8,400 kt por conversión. **Tabla 7 no contabiliza eso en su total
IPCC**: sus renglones 3C1a son *quema* de biomasa (2,822 kt), y la pérdida de capacidad
de absorción se menciona sólo en la nota al pie (hasta 9 Mt/año), fuera de las 17,968.
Además Oaxaca tiene el régimen de manejo forestal comunitario más extenso del país.

Las transiciones bosque → no bosque se escalaron a **0.29** y el remanente se devolvió a
la diagonal para conservar filas de probabilidad que suman 1.

---

## D6 — Estructura del repositorio (2026-09-01)

**Decisión (usuario):** reemplazar `calibration/` por Oaxaca; la calibración de CDMX se
conserva en una carpeta independiente fuera de este repo.

Se **preservó** `calibration/reference_mexico/sisepuede_adj_inputs_MEX.baseline.csv`:
es la base nacional intacta y la semilla de cada reconstrucción.
Salida: `ssp_modeling/input_data/sisepuede_adj_inputs_OAX.csv`.

---

## D7 — Variables ausentes ≠ variables en cero ⚠️

**Trampa encontrada dos veces; documentada porque afectará a cualquier calibración futura.**

`run_baseline.py` llama a `add_missing_cols(df_example, ...)`: **toda columna ausente de
la base nacional se rellena con el valor por defecto del ejemplo de SISEPUEDE (otro
país)**. Una variable ausente **no** vale cero — hereda silenciosamente un default ajeno.

Dos casos costaron diagnóstico:

1. **`ef_fgtv_*_fuel_crude`** (16 columnas) no existen en la base nacional. El default
   aplicaba fugas de *extracción* completas a los ~628 PJ de crudo de la refinería →
   **9,292 kt espurios**, pese a que todos los `ef_fgtv_*` presentes ya estaban en cero.
2. **`consumpinit_inen_energy_tj_per_mmm_gdp_other_product_manufacturing`**: el nombre
   real lleva el prefijo `consumpinit_inen_`. Un `scale()` con el nombre truncado
   fallaba en silencio y dejaba INEN en +45 %.

**Mitigación:** `lib_calib.ensure_col()` crea la columna si no existe. `set_col()` sigue
lanzando `KeyError` a propósito, para que un nombre mal escrito falle ruidosamente.

---

## D8 — Ruteo de la quema de biomasa 3C1a: corrección (2026-09-02)

**Corrige un error de calibración y de validación introducido en D5.** Antes de esta
decisión, `lndu` se validaba contra el renglón 3C1a forestal (1,265 kt) y daba +28 %.
**Ese +28 % era espurio: dos errores de tamaño parecido se cancelaban.**

### El diagnóstico

`lndu` = 1,621 kt **no contiene quema alguna**. Es CO2 de **conversión de uso de
suelo** (cambio de acervo de carbono): `forests_secondary → pastures` 1,187 kt,
`→ croplands` 283, `→ shrublands` 266, etc. Y la Tabla 7 **no tiene ningún renglón**
para eso: aparece sólo en la nota al pie ("hasta 9 Mt/año de pérdida de capacidad de
absorción"), fuera de las 17,968 — como ya decía la propia D5.

La quema de la Tabla 7 vive en otros dos campos del modelo:

| Tabla 7 | campo SISEPUEDE | subsector |
|---|---|---|
| 3C1a forestal, CO2 (1,143) | `emission_co2e_co2_frst_forest_fires` | **frst**, no lndu |
| 3C1a cultivo, CH4+N2O (253) | `emission_co2e_{ch4,n2o}_agrc_biomass_burning` | agrc |

Los incendios forestales daban **0.65 kt** contra 1,143. Dos causas multiplicativas:

1. **`frac_frst_annual_wildfire_fraction_*` seguía en el default nacional**
   (1e-5 primario / 1e-4 secundario) → **407 ha/año** ardiendo en todo el estado.
   La calibración de Oaxaca nunca escribió esas columnas — el mismo patrón de D7.
2. **Un clamp dentro de SISEPUEDE.** `afolu.py:5844` y `:5866` extraen
   `qty_frst_biomass_consumed_by_fire_*_tonne_per_ha` con `var_bounds=(0,1)` y
   `force_boundary_restriction=True` (el default), de modo que valores de
   **45–125 t/ha se recortan a 1.0 t/ha** con un simple `warnings.warn`.
   Un factor ~50 perdido en silencio.

Aritmética que lo confirma: `396 ha × 1.0 × 1.607 + 11 ha × 1.0 × 1.573 = 0.65 kt`,
exactamente lo que reportaba el modelo.

### La corrección

- **Nivel de actividad:** `frac_frst_annual_wildfire_fraction_{primary,secondary}`
  fijadas a **13,000 ha/año** de superficie quemada (CONAFOR; extremo bajo de la banda
  típica de Oaxaca, consistente con 2013, temporada nacional benigna de ~413,000 ha),
  con susceptibilidad del bosque primario × 0.4 respecto del secundario.
- **Factor técnico:** la biomasa consumida se **pliega dentro del EF**
  (`ef_frst_forestfires_*_co2` = EF nacional × biomasa nacional ponderada
  temperate/tropical → ~118 t CO2/ha primario, ~84 secundario), de modo que el
  producto área × biomasa × EF queda intacto pese al clamp. **No se inventa ningún
  factor**: es el valor que SISEPUEDE aplicaría si no recortara la biomasa.
- **`frac_agrc_crop_residues_burned` 0.25 → 0.65**, calibrado contra la parte no-CO2
  de 3C1a cultivo (253 kt). 0.65 es el límite superior defendible para milpa de
  temporal en ladera; el residuo se documenta en vez de forzarse.
- **`diagnose_2013.py`** separa los incendios del sumidero FRST y los valida como
  línea propia contra 3C1a forestal; `lndu` pasa a memo, junto al sumidero.

### Las dos diferencias de frontera, ahora explícitas

| | kt | por qué |
|---|---:|---|
| CO2 de quema de residuos de cultivo | 1,304 | SISEPUEDE **no tiene** campo `co2_agrc_biomass_burning`. Correcto según IPCC 2006: el carbono de residuos anuales es cíclico. La Tabla 7 lo contabiliza igual. |
| CH4+N2O de incendios forestales | 122 | SISEPUEDE sólo produce CO2 de incendios. |

Por eso se reportan **dos gates**: **COMPARABLE** (16,542 = 17,968 − 1,304 − 122),
que es el riguroso, y **BRUTO** (17,968, el elegido en D2), que incluye la conversión
`lndu`. El bruto pasa en parte porque `lndu` (fuera de frontera) compensa el CO2
biogénico que el modelo no puede emitir — **eso ahora se declara, no se esconde**.

### Alternativa descartada

Suprimir la conversión `lndu` a ~0 para que el modelo replicara la frontera de la
Tabla 7 al pie de la letra. Se descartó porque la deforestación oaxaqueña es un flujo
físico real y anularlo distorsionaría toda la trayectoria hacia adelante. Se prefiere
declararla como memo, igual que el sumidero (D3).

---

## D9 — Supuestos de línea base: hato ganadero y reasignación de uso de suelo (2026-09-02)

**Decisión (usuario):** el hato debe seguir a la población estatal (no al ingreso) y el
cambio de uso de suelo debe dejar de tener la joroba de conversión.

**Alcance:** esto **no toca el año base**. 2013 queda idéntico (verificado: emisión bruta
17.21 Mt en la corrida completa, igual antes y después). Es exclusivamente la trayectoria.

### El problema

La corrida completa de SISEPUEDE (con el handler de transformaciones) mostraba una joroba
de conversión de uso de suelo que llegaba a **6.7 Mt en 2044**, con el total subiendo a
24.7 Mt en 2058. Dos causas encadenadas:

1. **El hato heredaba las elasticidades ingreso-demanda nacionales** y crecía **+65 %**
   (19.6 → 32.3 M cabezas) mientras la población de Oaxaca crece +11 % y empieza a caer
   tras 2045.
2. **`magnitude_lurf: 0.25`** en `transformations/config_general.yaml` — el factor de
   reasignación de uso de suelo de la línea base, que arranca en 2027 y hace que la
   demanda creciente de pastizal se satisfaga **convirtiendo bosque físicamente**. El
   flujo dominante en el pico era `forests_secondary → pastures` = 4,420 kt, dos tercios
   del total. La joroba baja después de 2044 sólo porque se agota el pastizal barato
   (921 k → 457 k ha), no porque la presión ceda.

Nótese que **el escalar 0.29 de D5 no contiene este mecanismo**: aquél modera la matriz
markoviana de transición; la reasignación por demanda es una capa distinta encima.

### La corrección

**a) Hato: la producción local sigue a la población, no al ingreso.**
**No se tocan las elasticidades** — la *demanda* sí responde al ingreso, eso es real y
está bien medido. Lo que no crece es la *producción local*: Oaxaca es importador neto de
proteína animal (bovino de Veracruz y Chiapas, aves del Bajío), su ganadería es extensiva
y de traspatio, y el inventario de SIAP ha sido esencialmente plano.

SISEPUEDE (`afolu.py:4103`, `project_per_capita_demand`) calcula

```
demanda(t)    = pob(t) x (dem_0/pob_0) x cumprod(1 + tasa_pibpc x elast)
produccion(t) = demanda(t) x (1 - frac_importada(t))
```

luego basta `frac_importada(t) = 1 - 1/cumprod(1 + tasa_pibpc x elast)`, con piso en el
valor nacional. En t=0 el factor vale 1, **así que 2013 no se altera**. La importación de
bovino llega a 21 % en 2058.

**b) `magnitude_lurf` 0.25 → 0.10.** Cerca del 80 % de la tierra en Oaxaca es propiedad
social y el estado tiene el régimen de manejo forestal comunitario más extenso del país:
el cambio de uso de suelo es institucionalmente lento. Reasignar una décima parte de la
demanda marginal por conversión física es un BAU creíble.

### Resultado

| 2058 | Antes | Después |
|---|---:|---:|
| Hato | 32.35 M cabezas (+65 %) | **20.90 M (+6.4 %)** |
| Conversión de uso de suelo | 5.09 Mt (pico 6.72 en 2044) | **4.32 Mt, monótona, sin joroba** |
| `lndu` neto | 3.32 Mt | **2.40 Mt** |
| Total bruto | 24.68 Mt | **21.88 Mt** |
| Bosque secundario | 3.68 M ha (−7.2 %) | **3.93 M ha (−0.9 %)** |
| Bosque primario | 1.07 M ha (−3.4 %) | **1.09 M ha (−1.6 %)** |

**El acervo forestal queda esencialmente estable**, que es el resultado defendible para
un estado con manejo forestal comunitario.

### Diferencia documentada: el hato crece +6.4 %, no +11 %

Las especies **no** dependientes de pastoreo siguen a la población con exactitud
(pollos ×1.108, cerdos ×1.109 = crecimiento poblacional). Las de pastoreo caen ~13 %
(bovino ×0.869, caprino ×0.864) porque el **pastizal disponible termina por debajo de su
nivel de 2013** (719 k vs 829 k ha) y la capacidad de carga limita. No se forzó: una
superficie de pastoreo decreciente y un hato bovino ligeramente a la baja son coherentes
con la alta migración y el abandono de tierras del estado, y con la tendencia plana del
inventario de SIAP.

### Pendiente conocido: el transitorio de inicialización

La conversión cae de 2.74 Mt (2013) a 0.76 Mt (2016) y se recupera a 1.37 Mt (2020). Es
el modelo relajando las `frac_lndu_initial_*` prescritas hacia el equilibrio de la matriz
de transición: pastizales y pastos caen, matorral sube. Corregirlo exigiría rebalancear
la matriz para que el cambio del primer año sea pequeño, lo que **movería `lndu` en 2013**
(hoy 1,621 kt) y con ello el total BRUTO. Como `lndu` es memo y no entra al gate
comparable (D8), se documenta en vez de tocarse.


---

## D10 — Alineación del eje al calendario real (2026-09-02)

**Decisión (usuario):** realinear **todos** los drivers para que coincidan con sus fechas
reales. Sustituye el mecanismo de D1, no su objetivo (el año base sigue siendo 2013).

### El problema

D1 lograba `time_period` 0 = 2013 recorriendo la columna `year` en −2. Eso funciona para
un factor de emisión, pero **no para una serie fechada**: arrastra la historia macro
junto con el índice.

```
eje NACIONAL original          eje OAXACA con el recorrido de D1
2019   2,571.0   -0.3%    ->   2017   39.85   -0.3%
2020   2,348.6   -8.7%    ->   2018   36.40   -8.7%   <- COVID mal fechado
2021   2,485.7   +5.8%    ->   2019   38.53   +5.8%
```

Efecto en 2018 de la corrida: `inen` −12.2 %, `trns` −7.3 %, `agrc` −4.5 %, `ippu` −2.8 %,
`lvst` −2.2 %. `entc` no se movía (la refinería la gobiernan las exportaciones, no el PIB)
y **`scoe` subía +7 %**, porque
`elasticity_scoe_enerdem_per_mmmgdp_commercial_municipal_*_to_gdppc = −0.1188` es
**negativa**: menos PIB implica más energía por unidad de PIB.

Para un año base 2013 el efecto es nulo, pero cualquier gráfica presentada a un tomador
de decisiones afirmaba una recesión estatal en el año equivocado.

### La corrección

**Principio: el PIB y la población son observaciones fechadas por calendario; los
factores técnicos no.** Recorrer los primeros era el error; recorrer los segundos es
inocuo.

`scripts/shift_time_axis.py` se reemplazó por **`scripts/align_time_axis.py`**, y
`lib_calib.YEAR_SHIFT` por **`lib_calib.aligned_baseline()`**:

- El año nacional Y se queda en el año Y. No se reetiqueta nada.
- Los dos años que la base nacional no trae (2013, 2014) se **retro-rellenan** desde su
  primera fila (2015). Para factores técnicos es inmaterial: varían despacio.
- Los **drivers** se retro-extienden con crecimiento mexicano observado (INEGI, precios
  constantes): PIB +2.8 % (2014), +3.3 % (2015); población +1.11 % y +1.10 %.
  `NAT_GDP_GROWTH` / `NAT_POP_GROWTH` en `lib_calib.py`.
- Los siete `transform_*.py` leen ahora `L.aligned_baseline()`, que devuelve la base
  nacional indexada sobre el eje 2013-2058 para que el indexado posicional siga siendo
  válido.

### Resultado

El choque queda donde ocurrió:

| | 2019 | **2020** | 2021 |
|---|---:|---:|---:|
| `trns` | +0.8 % | **−7.3 %** | +2.0 % |
| `inen` | −5.3 % | **−12.1 %** | +1.7 % |

**El año base apenas se movió y el gate se mantuvo sin re-ajustar ningún escalar.**
El PIB de Oaxaca en 2013 pasa de 37.80 a **35.59 mmm USD** — que es el valor coherente
(1.55 % del PIB nacional de 2013, no del de 2015). Los 37.80 eran un artefacto del
recorrido.

| | Antes (D1) | Después (D10) |
|---|---:|---:|
| `inen` | 632 | 621 (−2 % vs 636) ✅ |
| `ippu` | 811 | 807 (−4 % vs 842) ✅ |
| `trww` | 437 | 433 (+5 % vs 412) ✅ |
| COMPARABLE | 16,729 | **16,710** (+1 %) ✅ |
| BRUTO | 18,350 | **18,332** (+2 %) ✅ |

Que el impacto sea de sólo −18 kt confirma que la calibración descansa en niveles de
actividad absolutos (toneladas producidas, consumo por hogar, residuos per cápita) y no
en el PIB, que sólo entra en `inen`, el comercial de `scoe` y el residuo industrial.

### Limitación residual

2013 y 2014 heredan los factores técnicos de 2015 (emisión, densidades energéticas,
eficiencias). Es la limitación original de D1 pero acotada a dos años al inicio del eje,
en vez de propagarse a todo el horizonte.
