"""Runner headless equivalente a oaxaca_manager.ipynb (celdas 0-42),
SALTANDO las celdas 26/27/32 que regeneran los YAML y la fila de estrategia
desde el Excel de scenario_mapping. Uso: correr desde ssp_modeling/notebooks."""
import logging, os, pathlib, sys, time, warnings
from typing import Tuple
import numpy as np, pandas as pd

from utils.logger_utils import setup_clean_logger, mute_external_loggers
import sisepuede.core.support_classes as sc
import sisepuede.transformers as trf
import sisepuede.utilities._toolbox as sf
import sisepuede.core.attribute_table as att
import sisepuede.manager.sisepuede_examples as sxl
import sisepuede.manager.sisepuede_file_structure as sfs

warnings.filterwarnings("ignore")
logger = setup_clean_logger("runner", logging.INFO)
mute_external_loggers(["sisepuede"])

CURR = pathlib.Path(os.getcwd())
SSP_MODELING_DIR_PATH = CURR.parent
DATA_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("input_data")
CONFIG_DIR_PATH = SSP_MODELING_DIR_PATH.joinpath("config_files")

from ssp_transformations_handler.GeneralUtils import GeneralUtils
g_utils = GeneralUtils()
cfg = g_utils.read_yaml(os.path.join(CONFIG_DIR_PATH, "config.yaml"))
country_name = cfg["country_name"]
energy_model_flag = cfg["energy_model_flag"]

def get_file_structure(y0=2015, y1=2060):
    fsx = sfs.SISEPUEDEFileStructure(initialize_directories=False)
    ktp = fsx.model_attributes.dim_time_period
    ky = fsx.model_attributes.field_dim_year
    years = np.arange(y0, y1 + 1).astype(int)
    atp = att.AttributeTable(
        pd.DataFrame({ktp: range(len(years)), ky: years}), ktp,
    )
    fsx.model_attributes.update_dimensional_attribute_table(atp)
    return fsx, atp

_EXAMPLES = sxl.SISEPUEDEExamples()
_FILE_STRUCTURE, _ATTR_TP = get_file_structure()
matt = _FILE_STRUCTURE.model_attributes

df_inputs_raw = pd.read_csv(DATA_DIR_PATH.joinpath(cfg["ssp_input_file_name"]))
df_example_input = _EXAMPLES("input_data_frame")
if "time_period" not in df_inputs_raw.columns:
    df_inputs_raw = df_inputs_raw.rename(columns={"period": "time_period"})
df_in = g_utils.add_missing_cols(df_example_input, df_inputs_raw.copy())
df_in["region"] = country_name
df_in = df_in[df_in["time_period"].between(0, 45)]

# FIX: add_missing_cols rellena desde un df de ejemplo con solo 36 periodos (0-35).
# Oaxaca corre 0-45 -> las columnas ausentes del input quedan NaN en tp 36-45.
# Un NaN en cualquier frac_* de una categoria envenena todo el simplex y anula
# silenciosamente las transformaciones que la tocan (p.ej. TRNS marítimo, FGTV flare).
_nan_cols = df_in.columns[df_in.isna().any()].tolist()
if _nan_cols:
    logger.info(f"ffill de cola NaN en {len(_nan_cols)} columnas: {_nan_cols}")
    df_in = df_in.sort_values("time_period").ffill()
if cfg["set_lndu_reallocation_factor_to_zero"]:
    df_in["lndu_reallocation_factor"] = 0

transformations = trf.Transformations(
    SSP_MODELING_DIR_PATH.joinpath("transformations"),
    attr_time_period=_ATTR_TP,
    df_input=df_in,
)
t0 = time.time()
strategies = trf.Strategies(transformations, export_path="transformations", prebuild=True)
logger.info(f"strategies prebuilt in {sf.get_time_elapsed(t0)}s")

import sys
strategies_to_run = [0] + [int(x) for x in (sys.argv[1:] or ["6003"])]
strategies.build_strategies_to_templates(strategies=strategies_to_run)

import sisepuede as si
ssp = si.SISEPUEDE(
    "calibrated", db_type="csv",
    initialize_as_dummy=not energy_model_flag,
    regions=[country_name],
    strategies=strategies,
    attribute_time_period=_ATTR_TP,
)
ssp.project_scenarios(
    {ssp.key_design: [0], ssp.key_future: [0], ssp.key_strategy: strategies_to_run},
    save_inputs=True,
    include_electricity_in_energy=energy_model_flag,
)
logger.info(f"DONE id={ssp.id_fs_safe}")
print("RUN_ID:", ssp.id_fs_safe)
