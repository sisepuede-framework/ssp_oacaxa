#!/usr/bin/env bash
# Rebuild the Oaxaca SISEPUEDE input database from the untouched Mexico national
# baseline, reproducibly, by chaining the per-sector transformation scripts in
# calibration order. Idempotent: each script sets absolute Oaxaca values on its own
# columns, so running this twice produces a byte-identical file.
#
# Usage:  bash calibration/run_all.sh [--run]
#   (default) rebuild Oaxaca inputs only.
#   --run     also execute the SISEPUEDE model and print the 2013 gate table.
#
# Benchmark: PECC Oaxaca 2016-2022, Tabla 7 = 17,968 kt CO2e (categorias IPCC), 2013.
# Env: ssp_mex_env (NOT the env named in environment.yml -- that one is broken).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="/Users/fabianfuentes/miniconda3/envs/ssp_mex_env/bin/python"
WORKING="$REPO/ssp_modeling/input_data/sisepuede_adj_inputs_OAX.csv"
SCRIPTS="$REPO/calibration/scripts"

echo "[run_all] seeding Oaxaca inputs from the untouched Mexico baseline (eje calendario real 2013-2058)"
"$PY" "$SCRIPTS/align_time_axis.py" --out "$WORKING"

# Calibration order, by leverage over the Tabla 7 target:
#   gnrl (drivers) -> afolu (7,996 kt, 44%) -> energy supply (refineria 3,698)
#   -> transport (3,641) -> ippu (842, y arrastra inen) -> buildings/industry
#   -> waste (654)
for t in socioeconomic afolu energy_supply transport ippu buildings_industry waste; do
  echo "[run_all] applying transform_$t"
  "$PY" "$SCRIPTS/transform_$t.py" --io "$WORKING"
done
echo "[run_all] Oaxaca inputs rebuilt -> $WORKING"

if [[ "${1:-}" == "--run" ]]; then
  echo "[run_all] running SISEPUEDE model (energy on; ~3 min)"
  "$PY" "$SCRIPTS/run_baseline.py" --input "$WORKING" --label oax \
        --out-dir "$REPO/calibration/04_validation" --y0 2013 --y1 2058
  "$PY" "$SCRIPTS/diagnose_2013.py" \
        --emis "$REPO/calibration/04_validation/baseline_oax_emissions_by_subsector.csv"
fi
