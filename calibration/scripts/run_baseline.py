#!/usr/bin/env python
"""Reproducible SISEPUEDE baseline run (strategy 0, no transformations).

Runs the national Mexico input database through the SISEPUEDE models directly
(SISEPUEDEModels.__call__) with the electricity/energy model enabled, and exports
the wide output plus a tidy subsector-emissions summary. This is the clean
validation baseline for the CDMX calibration (Phase 0 gate / Phase 4 reference).

Unlike the notebook, this does NOT apply the INEN/SCOE/TRNS pre-transformers that
build the notebook's `df_mexico_adj`, and does NOT apply the manual ENTC
capital-cost edits. Those are scenario/analysis choices; the calibration baseline
must be the raw driver inputs run through the model as-is.

Usage:
    /Users/fabianfuentes/miniconda3/envs/ssp_mex_env/bin/python run_baseline.py \
        [--input <path>] [--no-energy] [--out-dir <dir>] [--label mex]

Env: ssp_mex_env
"""
import argparse
import logging
import os
import pathlib
import sys

import numpy as np
import pandas as pd

# --- Resolve repo paths from this script's location ---
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent          # calibration/scripts
REPO_DIR = SCRIPT_DIR.parent.parent                            # repo root
SSP_MODELING_DIR = REPO_DIR / "ssp_modeling"
NOTEBOOKS_DIR = SSP_MODELING_DIR / "notebooks"
DATA_DIR = SSP_MODELING_DIR / "input_data"
CONFIG_DIR = SSP_MODELING_DIR / "config_files"

# make the notebook's `utils` and handler importable
sys.path.insert(0, str(NOTEBOOKS_DIR))

import warnings
warnings.filterwarnings("ignore")

from ssp_transformations_handler.GeneralUtils import GeneralUtils

import sisepuede.core.attribute_table as att
import sisepuede.core.support_classes as sc
import sisepuede.manager.sisepuede_examples as sxl
import sisepuede.manager.sisepuede_file_structure as sfs
import sisepuede.manager.sisepuede_models as sm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("baseline")


def get_file_structure(y0: int = 2015, y1: int = 2060):
    """SISEPUEDE file structure with a time-period attribute for [y0, y1]."""
    file_struct = sfs.SISEPUEDEFileStructure(initialize_directories=False)
    key_tp = file_struct.model_attributes.dim_time_period
    key_year = file_struct.model_attributes.field_dim_year
    years = np.arange(y0, y1 + 1).astype(int)
    attr_tp = att.AttributeTable(
        pd.DataFrame({key_tp: range(len(years)), key_year: years}),
        key_tp,
    )
    file_struct.model_attributes.update_dimensional_attribute_table(attr_tp)
    return file_struct, attr_tp


def build_inputs(input_path, country_name, examples, g_utils,
                 set_lndu_realloc_zero: bool):
    """Replicate the notebook's baseline input prep (cells 8-15, 47)."""
    df_raw = pd.read_csv(input_path)
    df_example = examples("input_data_frame")

    if "time_period" not in df_raw.columns and "period" in df_raw.columns:
        df_raw = df_raw.rename(columns={"period": "time_period"})

    df = g_utils.add_missing_cols(df_example, df_raw.copy())
    df["region"] = country_name
    df = df[df["time_period"].between(0, 45)].reset_index(drop=True)

    if set_lndu_realloc_zero and "lndu_reallocation_factor" in df.columns:
        df["lndu_reallocation_factor"] = 0

    log.info("inputs: %d rows x %d cols, region=%s, tp %s-%s",
             len(df), df.shape[1], df["region"].unique(),
             int(df["time_period"].min()), int(df["time_period"].max()))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="input CSV (default: from config)")
    ap.add_argument("--no-energy", action="store_true", help="disable ENTC/Julia energy model")
    ap.add_argument("--out-dir", default=str(REPO_DIR / "calibration" / "reference_mexico"))
    ap.add_argument("--label", default="mex", help="output filename tag")
    ap.add_argument("--y0", type=int, default=2015)
    ap.add_argument("--y1", type=int, default=2060)
    args = ap.parse_args()

    g_utils = GeneralUtils()
    cfg = g_utils.read_yaml(str(CONFIG_DIR / "config.yaml"))
    country_name = cfg["country_name"]
    input_path = args.input or str(DATA_DIR / cfg["ssp_input_file_name"])
    include_energy = (not args.no_energy) and cfg.get("energy_model_flag", True)
    set_lndu_zero = cfg.get("set_lndu_reallocation_factor_to_zero", False)

    log.info("country=%s input=%s energy=%s", country_name, input_path, include_energy)

    file_struct, _ = get_file_structure(args.y0, args.y1)
    matt = file_struct.model_attributes
    examples = sxl.SISEPUEDEExamples()

    df_in = build_inputs(input_path, country_name, examples, g_utils, set_lndu_zero)

    models = sm.SISEPUEDEModels(
        matt,
        allow_electricity_run=include_energy,
        fp_julia=file_struct.dir_jl,
        fp_nemomod_reference_files=file_struct.dir_ref_nemo,
        initialize_julia=include_energy,
    )

    log.info("running model (include_electricity_in_energy=%s) ...", include_energy)
    df_out = models(df_in, include_electricity_in_energy=include_energy)
    log.info("model done: %d rows x %d cols", len(df_out), df_out.shape[1])

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # merge inputs+outputs wide, and write
    df_wide = pd.concat([df_in.reset_index(drop=True), df_out.reset_index(drop=True)], axis=1)
    df_wide = df_wide.loc[:, ~df_wide.columns.duplicated()]
    wide_path = out_dir / f"baseline_{args.label}_wide.csv"
    df_wide.to_csv(wide_path, index=False)
    log.info("wrote %s", wide_path)

    # tidy subsector emission totals
    emis_fields = [f for f in matt.get_all_subsector_emission_total_fields()
                   if f in df_out.columns]
    year_col = df_in["year"].values if "year" in df_in.columns else None
    df_emis = df_out[emis_fields].copy()
    df_emis.insert(0, "time_period", df_in["time_period"].values)
    if year_col is not None:
        df_emis.insert(1, "year", year_col)
    emis_path = out_dir / f"baseline_{args.label}_emissions_by_subsector.csv"
    df_emis.to_csv(emis_path, index=False)
    log.info("wrote %s (%d emission fields)", emis_path, len(emis_fields))

    # base-year total (MT CO2e) summary to stdout
    base = df_emis.iloc[0]
    total = float(df_emis[emis_fields].iloc[0].sum())
    log.info("BASE YEAR %s total emissions = %.2f (model units, MT CO2e)",
             int(base.get("year", args.y0)), total)
    log.info("DONE")


if __name__ == "__main__":
    main()
