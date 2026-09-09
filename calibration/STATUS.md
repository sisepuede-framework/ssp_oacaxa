# Calibración Oaxaca — Estado global

**Benchmark:** PECC Oaxaca 2016–2022, **Tabla 7 — Inventario estatal de GEI, 2013**.
**Objetivo del gate:** *Emisiones de las categorías IPCC* = **17,968 kt CO2e**
(emisiones directas territoriales). Las 1,223 kt indirectas por consumo eléctrico son
memo Scope-2 y NO se modelan como emisión territorial (ver [DECISIONS.md](DECISIONS.md) D2).
**Año base:** 2013 = `time_period` 0 (eje de calendario real, D1 + D10). Corrida 2013–2058.
**Tolerancias:** total ±10 %; cada categoría IPCC ±15 %.

## Resultado

Se reportan **dos gates** (ver [DECISIONS.md](DECISIONS.md) D8):

| | Modelo | Tabla 7 | Desv. | Gate |
|---|---:|---:|---:|:--:|
| 1 Energía | 8,484 | 8,476 | +0 % | ✅ |
| 2 IPPU | 807 | 842 | −4 % | ✅ |
| 3 AFOLU | 6,702 | 6,570 | +2 % | ✅ |
| 4 Desechos | 717 | 654 | +10 % | ✅ |
| **COMPARABLE** (like-for-like) | **16,710** | **16,542** | **+1 %** | ✅ |
| **BRUTO** (D2, incl. conversión `lndu`) | **18,332** | **17,968** | **+2 %** | ✅ |

`COMPARABLE` = 17,968 − 1,304 (CO2 biogénico de quema de residuos de cultivo, sin
campo en SISEPUEDE) − 122 (CH4/N2O de incendios forestales, sin campo). Es el gate
riguroso. `BRUTO` es el titular elegido en D2 e incluye las 1,621 kt de conversión de
uso de suelo, que **no tienen renglón en la Tabla 7**.

**Memos, fuera del gate:** conversión `lndu` +1,621 kt · sumidero FRST −13,916 kt
(nota al pie ~−14,000, D3) · Scope-2 1,223 kt.

## Fases

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Auditoría del repo + corrida nacional en eje 2013 | ✅ 2013 = 945,266 kt (nacional) |
| 1 | Extracción de Tabla 7 + datos de Oaxaca | ✅ `01_oaxaca_data/oaxaca_targets_tabla7.csv` |
| 2 | Estrategia de downscaling | ✅ [02_downscaling_strategy.md](02_downscaling_strategy.md) |
| 3 | Calibración sectorial | ✅ 7/7 sectores |
| 4 | Validación | ✅ comparable +1 %, 4/4 categorías, 14/14 líneas |
| 5 | Entregables | ✅ [FINAL_REPORT.md](FINAL_REPORT.md) |
| 6 | Corrección del ruteo 3C1a (D8) | ✅ incendios forestales activados, mapeo corregido |
| 7 | Supuestos de trayectoria BAU (D9) | ✅ hato atado a población, `magnitude_lurf` 0.25 → 0.10 |
| 8 | Alineación del eje al calendario real (D10) | ✅ COVID vuelve a 2020; el gate se mantuvo sin re-ajustes |

## Rastreador por línea

Leyenda: 🟢 calibrado · ✅ dentro del gate

| Línea | Tabla 7 | Modelo | Desv. | Estado |
|---|---|---:|---:|:--:|
| gnrl (socioeconómico) | drivers | pob 3.90 M · PIB 37.8 mmm USD · 9.40 M ha | — | 🟢 |
| entc (refinación 1A1b) | 3,681 | 3,693 | +0 % | ✅ |
| fgtv (fugitivas 1B) | 17 | 17 | +0 % | ✅ |
| inen (manufactura 1A2) | 636 | 621 | −2 % | ✅ |
| trns (transporte 1A3) | 3,641 | 3,625 | −0 % | ✅ |
| scoe (otros sectores 1A4) | 501 | 529 | +6 % | ✅ |
| ippu (cemento + HFC) | 842 | 807 | −4 % | ✅ |
| lvst (fermentación entérica 3A1) | 2,627 | 2,721 | +4 % | ✅ |
| lsmm (manejo de estiércol 3A2) | 418 | 463 | +11 % | ✅ |
| soil (N2O suelos 3C4+3C5) | 2,061 | 2,017 | −2 % | ✅ |
| agrc (arroz 3C7 + no-CO2 de 3C1a cultivo) | 321 | 360 | +12 % | ✅ |
| frst_fires (CO2 de 3C1a forestal) | 1,143 | 1,141 | −0 % | ✅ |
| waso (residuos sólidos 4A) | 242 | 284 | +17 % | ✅ (abs < 100 kt) |
| trww (aguas residuales 4D) | 412 | 433 | +5 % | ✅ |
| lndu (conversión de uso de suelo) | sin renglón en Tabla 7 | 1,621 | — | 🟢 memo (D8) |
| frst (sumidero, sin incendios) | ~−14,000 memo | −13,916 | — | 🟢 calibrado (D3) |
| enfu · enst · wali · ccsq | sin emisión directa | — | — | 🟢 soporte |

## Reproducibilidad

```bash
bash calibration/run_all.sh --run
```

Verificado **idempotente**: dos ejecuciones producen un CSV byte-idéntico
(md5 `e7d579c0b7475cd970a90585a0a8957e`). 250 cambios trazados en `data_sources.csv`.
