"""
tableau_postprocessing.py
-------------------------
Produce Tableau-ready CSVs from a SISEPUEDE run, adapted for Oaxaca.

Port of the Egypt pipeline: Oaxaca uses the **raw** SSP output — no
intertemporal decomposition, no rescaling against the inventory — and reports
emissions in SISEPUEDE's own sector / subsector taxonomy rather than IPCC
inventory categories. Consequences:

  * the emissions table reads `*WIDE_INPUTS_OUTPUTS.csv`, not
    `decomposed_ssp_output.csv`;
  * there is no historical (NIR) series — the output is SISEPUEDE only;
  * there is no HP smoothing (it existed to damp rescaling artefacts).

Two things differ from Egypt and are exposed as parameters:

  * `base_year` — Oaxaca's time axis starts at **2013** (PECC Tabla 7 base
    year), not 2015, so `Year = time_period + base_year`.
  * `model_region` — SISEPUEDE only knows the region label `"mexico"`
    (`attribute_region` has no "oaxaca"), so the WIDE file is filtered on
    `model_region` and every output is labelled with `region`.

Usage from a manager notebook:

    from shared_scripts.tableau_postprocessing import run_tableau_postprocessing

    run_tableau_postprocessing(
        run_dir      = RUN_ID_OUTPUT_DIR_PATH,
        project_dir  = PROJECT_DIR,
        region       = "oaxaca",     # output label
        model_region = "mexico",     # label inside the WIDE file
        iso_code3    = "OAX",
        year_ref     = 2013,
        base_year    = 2013,
    )

Outputs land in `<project_dir>/ssp_modeling/tableau/data/`:
  - emissions_<region>.csv               (raw SSP emissions, SSP taxonomy)
  - drivers_<region>.csv                 (driver variables + GDP history)
  - tableau_levers_table_complete.csv    (levers + stakeholder merge)
  - jobs_demand_<region>.csv             (employment subset)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# SISEPUEDE sector / subsector classification (canonical)
#
# This is the authoritative table, transcribed from the SISEPUEDE docs. It is
# NOT derived from driver_variables_taxonomy_*.csv: that file lags the model
# (its fgtv entries still carry pre-dtp/venting/flaring field names), so it is
# validated against this map rather than trusted as the source.
#
# Only 15 of the 21 subsectors emit; the rest appear in the drivers table.
# ---------------------------------------------------------------------------
SSP_SUBSECTORS: dict[str, tuple[str, str]] = {
    "agrc": ("AFOLU",            "Agriculture"),
    "frst": ("AFOLU",            "Forest"),
    "lndu": ("AFOLU",            "Land Use"),
    "lsmm": ("AFOLU",            "Livestock Manure Management"),
    "lvst": ("AFOLU",            "Livestock"),
    "soil": ("AFOLU",            "Soil Management"),
    "wali": ("Circular Economy", "Liquid Waste"),
    "waso": ("Circular Economy", "Solid Waste"),
    "trww": ("Circular Economy", "Wastewater Treatment"),
    "ccsq": ("Energy",           "Carbon Capture and Sequestration"),
    "enfu": ("Energy",           "Energy Fuels"),
    "enst": ("Energy",           "Energy Storage"),
    "entc": ("Energy",           "Energy Technology"),
    "fgtv": ("Energy",           "Fugitive Emissions"),
    "inen": ("Energy",           "Industrial Energy"),
    "scoe": ("Energy",           "Stationary Combustion and Other Energy"),
    "trns": ("Energy",           "Transportation"),
    "trde": ("Energy",           "Transportation Demand"),
    "ippu": ("IPPU",             "IPPU"),
    "econ": ("Socioeconomic",    "Economy"),
    "gnrl": ("Socioeconomic",    "General"),
}

# `subsector` is too coarse to slice on: it pools families whose boundaries
# matter (entc mixes power generation with fuel extraction and refining; waso
# mixes engineered landfill with open dumping). `subsector_detail` is the
# mid-level cut a policy analyst actually reasons about -- coarser than
# `category`, finer than `subsector`.
#
# Rules are matched as ordered prefixes against the category, after the
# gas-accounting prefixes are stripped (see _strip_accounting_prefix). Order
# matters where one rule is a prefix of another: `biomass_burning` must precede
# the generic `biomass_` crop rule.
#
# A subsector with no rules falls back to its own name, so a newly emitting
# subsector degrades gracefully instead of breaking the build. A subsector that
# HAS rules must match every category it carries, or the build raises -- adding a
# category upstream is then a deliberate classification decision, not a silent
# repartition.
SUBSECTOR_DETAIL_RULES: dict[str, tuple[tuple[str, str], ...]] = {
    "agrc": (
        ("anaerobicdom_rice",         "Rice Cultivation"),
        ("biomass_burning",           "Biomass Burning"),
        ("crop_residues",             "Crop Residues"),
        ("biomass_",                  "Crop Biomass"),
    ),
    "ccsq": (
        ("direct_air_capture",        "Direct Air Capture"),
    ),
    "entc": (
        ("generation_pp_",            "Electricity Generation"),
        ("mining_and_extraction_",    "Fuel Extraction"),
        ("processing_and_refinement_", "Fuel Processing and Refining"),
    ),
    "fgtv": (
        ("dtp_",                      "Distribution, Transmission and Processing"),
        ("flaring_",                  "Flaring"),
        ("venting_",                  "Venting"),
    ),
    "frst": (
        ("forest_fires",              "Forest Fires"),
        ("harvested_wood_products",   "Harvested Wood Products"),
        ("methane_",                  "Forest Methane"),
        ("sequestration_",            "Forest Sequestration"),
    ),
    "inen": (
        ("recycled_",                 "Recycling"),
        ("agriculture_and_livestock", "Agriculture and Livestock"),
        ("mining",                    "Mining"),
        ("cement",                    "Manufacturing"),
        ("chemicals",                 "Manufacturing"),
        ("electronics",               "Manufacturing"),
        ("glass",                     "Manufacturing"),
        ("lime_and_carbonite",        "Manufacturing"),
        ("metals",                    "Manufacturing"),
        ("other_product_manufacturing", "Manufacturing"),
        ("paper",                     "Manufacturing"),
        ("plastic",                   "Manufacturing"),
        ("rubber_and_leather",        "Manufacturing"),
        ("textiles",                  "Manufacturing"),
        ("wood",                      "Manufacturing"),
    ),
    "ippu": (
        ("production_",               "Industrial Production"),
        ("product_use_",              "Product Use"),
    ),
    "lndu": (
        ("conversion_",               "Land Use Conversion"),
        ("biomass_sequestration_",    "Biomass Sequestration"),
        ("drained_organic_soils_",    "Drained Organic Soils"),
        ("wetlands",                  "Wetlands"),
    ),
    # Bare categories carry the CH4 of manure management; `direct_`/`indirect_`
    # carry the two N2O pathways, matching the IPCC 3.A.2 split.
    "lsmm": (
        ("direct_",                   "Manure N2O (Direct)"),
        ("indirect_",                 "Manure N2O (Indirect)"),
        ("anaerobic_digester",        "Manure CH4"),
        ("anaerobic_lagoon",          "Manure CH4"),
        ("composting",                "Manure CH4"),
        ("daily_spread",              "Manure CH4"),
        ("deep_bedding",              "Manure CH4"),
        ("dry_lot",                   "Manure CH4"),
        ("incineration",              "Manure CH4"),
        ("liquid_slurry",             "Manure CH4"),
        ("paddock_pasture_range",     "Manure CH4"),
        ("poultry_manure",            "Manure CH4"),
        ("storage_solid",             "Manure CH4"),
    ),
    "lvst": (
        ("entferm_",                  "Enteric Fermentation"),
    ),
    "scoe": (
        ("residential",               "Residential"),
        ("commercial_municipal",      "Commercial and Municipal"),
        ("other_se",                  "Other Stationary"),
    ),
    "soil": (
        ("fertilizer",                "Synthetic and Organic Inputs"),
        ("urea_use",                  "Synthetic and Organic Inputs"),
        ("lime_use",                  "Synthetic and Organic Inputs"),
        ("soc_mineral_soils",         "Mineral Soils"),
        ("mineral_soils",             "Mineral Soils"),
        ("organic_soils",             "Organic Soils"),
        ("paddock_pasture_range",     "Grazing"),
    ),
    "trns": (
        ("road_",                     "Road"),
        ("public",                    "Road"),
        ("powered_bikes",             "Road"),
        ("human_powered",             "Non-motorised"),
        ("rail_",                     "Rail"),
        ("aviation",                  "Aviation"),
        ("water_borne",               "Water-borne"),
    ),
    "trww": (
        ("treated_",                  "Treated Wastewater"),
        ("untreated_",                "Untreated Wastewater"),
    ),
    "waso": (
        ("landfilled_",               "Landfill"),
        ("open_dump_",                "Open Dump"),
        ("compost_",                  "Composting"),
        ("biogas_",                   "Anaerobic Digestion"),
        ("incineration",              "Incineration"),
    ),
}

# `bmass_`/`nbmass_` mark biogenic vs non-biogenic CO2 and `fuel_` marks the
# CH4/N2O variant of a fuel family; none of them is part of the category. They
# leak into the parsed category because the field regex captures the gas
# non-greedily, which is why `cement`, `bmass_cement` and `nbmass_cement` all
# appear. Stripping them keeps one grouping rule per real category.
_ACCOUNTING_PREFIXES = ("nbmass_", "bmass_", "fuel_")


def _strip_accounting_prefix(category: str) -> str:
    for prefix in _ACCOUNTING_PREFIXES:
        if category.startswith(prefix):
            return category[len(prefix):]
    return category


def subsector_detail(code: str, category: str, subsector: str) -> str | None:
    """Mid-level grouping. None means the category matched no rule."""
    rules = SUBSECTOR_DETAIL_RULES.get(code)
    if not rules:
        return subsector
    stripped = _strip_accounting_prefix(category)
    for marker, label in rules:
        if stripped.startswith(marker):
            return label
    return None


# Matches emission_co2e_<gas>_<subsector code>_<category>. The gas group is
# non-greedy so multi-token gases (other_fcs) resolve correctly.
EMISSION_FIELD_RE = re.compile(
    r"^emission_co2e_(?P<gas>.+?)_(?P<sub>"
    + "|".join(SSP_SUBSECTORS)
    + r")_(?P<cat>.+)$"
)


# ---------------------------------------------------------------------------
# SSP emission taxonomy
# ---------------------------------------------------------------------------

# Emission fields that restate other fields from a different angle. Summing
# them alongside the originals double counts, so they are dropped:
#   entc_generation_for_*   the same generated electricity as entc_generation_pp_*,
#                           re-attributed to the sector that consumes it
#   lndu_conversion_away_*  roll-up of the lndu_conversion_<from>_to_<to> pairs
# With these excluded, the emission fields sum exactly to
# emission_co2e_subsector_total_*. build_emissions_table re-checks that identity
# on every run (_assert_reconciles), so if SISEPUEDE adds another parallel view
# the build fails loudly instead of silently inflating the totals.
DOUBLE_COUNTING_PATTERNS = (
    "_entc_generation_for_",
    "_lndu_conversion_away_",
)


def is_double_counted(field: str) -> bool:
    return any(pat in field for pat in DOUBLE_COUNTING_PATTERNS)


def load_taxonomy_labels(taxonomy_path: Path) -> pd.DataFrame:
    """Per-field taxonomy rows, after checking its labels against SSP_SUBSECTORS.

    The taxonomy supplies the nice-to-have labels (model_variable,
    category_value, gas_name). Its sector/subsector columns are only used to
    verify it still agrees with the canonical map; a mismatch means either the
    table here or the upstream taxonomy has moved and needs reconciling.
    """
    tax = pd.read_csv(taxonomy_path)

    canonical = {pair for pair in SSP_SUBSECTORS.values()}
    declared = set(map(tuple, tax[["sector", "subsector"]].drop_duplicates().values))
    drifted = declared - canonical
    if drifted:
        raise ValueError(
            f"taxonomy declares sector/subsector pairs absent from "
            f"SSP_SUBSECTORS: {sorted(drifted)}"
        )

    return tax.drop_duplicates(subset=["field"]).set_index("field")


# Tableau needs a filter with a handful of entries, not the ~33 individual
# halocarbons SISEPUEDE reports. Everything that is not CO2/CH4/N2O collapses
# into one F-gas bucket; the precise species stays in `Gas`.
def gas_group(gas: str) -> str:
    g = str(gas).upper()
    return g if g in ("CO2", "CH4", "N2O") else "F-gases"


def _assert_reconciles(wide_path: Path, region: str, fields: list, tol: float = 1e-6) -> None:
    """Kept emission fields must sum to emission_co2e_subsector_total_*."""
    hdr = list(pd.read_csv(wide_path, nrows=0).columns)
    totals = [c for c in hdr if c.startswith("emission_co2e_subsector_total_")]
    if not totals:
        return
    df = pd.read_csv(wide_path, usecols=["region", "primary_id", "time_period"] + fields + totals)
    df = df[df["region"] == region]
    got = df[fields].sum(axis=1)
    want = df[totals].sum(axis=1)
    worst = float((got - want).abs().max())
    if worst > tol:
        bad = (got - want).abs().idxmax()
        raise ValueError(
            f"emission fields do not reconcile to subsector totals "
            f"(worst row off by {worst:.6f} MtCO2e at index {bad}). "
            f"A new double-counting field family probably needs adding to "
            f"DOUBLE_COUNTING_PATTERNS."
        )
    print(f"[emissions] reconciles to subsector totals (max diff {worst:.2e})")


def build_emissions_table(
    wide_path: Path,
    run_dir: Path,
    taxonomy_path: Path,
    iso_code3: str,
    region: str,
    out_path: Path,
    base_year: int = 2015,
    model_region: str | None = None,
) -> pd.DataFrame:
    """Raw SSP emissions, long format, labelled with SISEPUEDE's own taxonomy.

    No decomposition, no inventory rescaling, no historical series: `value` is
    exactly what the model wrote to the WIDE_INPUTS_OUTPUTS file, and `strategy`
    carries only the strategies actually simulated. External benchmarks stay out
    of this table so a strategy filter never mixes model output with reference
    trajectories.

    `model_region` is the region label written by SISEPUEDE (defaults to
    `region`); `region` is the label emitted for Tableau. `base_year` is the
    calendar year of time_period 0.
    """
    model_region = model_region or region
    tax_by_field = load_taxonomy_labels(taxonomy_path)

    hdr = list(pd.read_csv(wide_path, nrows=0).columns)
    fields = [
        c for c in hdr
        if c.startswith("emission_co2e_")
        and "_subsector_total_" not in c
        and not is_double_counted(c)
    ]

    # -- classify first, so an unrecognised field is reported as such rather
    #    than surfacing later as an unexplained reconciliation gap ------------
    parsed = pd.DataFrame({"variable": fields})
    m = parsed["variable"].map(EMISSION_FIELD_RE.match)
    unparsed = parsed.loc[m.isna(), "variable"].tolist()
    if unparsed:
        raise ValueError(
            f"{len(unparsed)} emission field(s) carry a subsector code absent "
            f"from SSP_SUBSECTORS and would be dropped: {unparsed[:5]}. "
            f"Add the code to SSP_SUBSECTORS (and check whether it restates an "
            f"existing family, in which case it belongs in "
            f"DOUBLE_COUNTING_PATTERNS instead)."
        )

    _assert_reconciles(wide_path, model_region, fields)

    id_vars = ["region", "time_period", "primary_id"]
    data = pd.read_csv(wide_path, usecols=id_vars + fields)
    data = data[data["region"] == model_region].copy()
    if data.empty:
        raise ValueError(
            f"no rows for region={model_region!r} in {wide_path.name}. "
            f"Pass model_region= the label SISEPUEDE actually wrote."
        )

    long_df = data.melt(id_vars=id_vars, value_vars=fields,
                        var_name="variable", value_name="value")

    # -- labels ---------------------------------------------------------------
    parsed["gas"]      = [x.group("gas") for x in m]
    parsed["code"]     = [x.group("sub") for x in m]
    parsed["category"] = [x.group("cat") for x in m]
    parsed["sector"]    = parsed["code"].map(lambda c: SSP_SUBSECTORS[c][0])
    parsed["subsector"] = parsed["code"].map(lambda c: SSP_SUBSECTORS[c][1])
    parsed["subsector_detail"] = [
        subsector_detail(c, cat, sub_)
        for c, cat, sub_ in zip(parsed["code"], parsed["category"], parsed["subsector"])
    ]

    unclassified = sorted(
        set(zip(parsed.loc[parsed["subsector_detail"].isna(), "code"],
                parsed.loc[parsed["subsector_detail"].isna(), "category"]))
    )
    if unclassified:
        raise ValueError(
            f"{len(unclassified)} categor(y/ies) match no SUBSECTOR_DETAIL_RULES "
            f"entry: {unclassified[:5]}. Add a rule so the grouping stays a "
            f"deliberate choice rather than a silent repartition."
        )

    no_rules = sorted(
        {SSP_SUBSECTORS[c][1] for c in parsed["code"].unique()
         if c not in SUBSECTOR_DETAIL_RULES}
    )
    if no_rules:
        print(f"[emissions] no subsector_detail rules for {no_rules} - "
              f"falling back to the subsector name")

    # richer labels where the taxonomy covers the field (it lags on fgtv)
    for col in ("model_variable", "category_value", "gas_name"):
        parsed[col] = parsed["variable"].map(
            tax_by_field[col] if col in tax_by_field.columns else {}
        )
    parsed["Gas"] = parsed["gas"].str.upper()
    parsed["gas_group"] = parsed["Gas"].map(gas_group)

    long_df = long_df.merge(parsed.drop(columns=["code"]), on="variable", how="left")

    # -- run metadata ---------------------------------------------------------
    long_df["Year"] = long_df["time_period"] + base_year
    long_df = long_df.drop(columns=["time_period", "region"])

    att_primary = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    long_df = long_df.merge(att_primary, on="primary_id", how="left")

    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")[["strategy_id", "strategy"]]
    long_df = long_df.merge(att_strategy, on="strategy_id", how="left")

    long_df["ID"]      = long_df["subsector"] + ":" + long_df["Gas"]
    long_df["Code"]    = iso_code3
    long_df["Country"] = region
    long_df["source"]  = "SISEPUEDE"

    out_cols = [
        "strategy_id", "primary_id", "design_id", "future_id", "strategy",
        "ID", "sector", "subsector", "subsector_detail", "category", "variable", "model_variable",
        "category_value", "gas", "Gas", "gas_group", "gas_name", "Year", "value",
        "Code", "Country", "source",
    ]
    out = long_df[[c for c in out_cols if c in long_df.columns]].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"[emissions] {out_path}  ({len(out):,} rows, {len(fields)} fields, "
          f"{out['subsector'].nunique()} subsectors)")
    return out


# ---------------------------------------------------------------------------
# Drivers table (data_prep_drivers.r)
# ---------------------------------------------------------------------------

def build_drivers_table(
    wide_inputs_outputs_path: Path,
    run_dir: Path,
    drivers_taxonomy_path: Path,
    iso_code3: str,
    region: str,
    year_ref: int,
    out_path: Path,
    base_year: int = 2015,
    model_region: str | None = None,
) -> pd.DataFrame:
    """Driver variables in long format, straight from the raw SSP output."""

    model_region = model_region or region
    data = pd.read_csv(wide_inputs_outputs_path)
    data = data[data["region"] == model_region].copy()
    id_vars = ["region", "time_period", "primary_id"]
    measure_cols = [c for c in data.columns if c not in id_vars]
    long_df = data.melt(id_vars=id_vars, value_vars=measure_cols,
                        var_name="variable", value_name="value")

    drivers = load_taxonomy_labels(drivers_taxonomy_path).reset_index()
    drivers = drivers.rename(columns={"field": "variable"})

    long_df = long_df[long_df["variable"].isin(drivers["variable"].unique())].copy()
    long_df = long_df.merge(drivers, on="variable", how="left")

    long_df["Year"] = long_df["time_period"] + base_year
    long_df = long_df.drop(columns=["time_period"])
    long_df = long_df[long_df["Year"] >= year_ref].copy()

    att_primary = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    long_df = long_df.merge(att_primary, on="primary_id", how="left")

    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")[["strategy_id", "strategy"]]
    long_df = long_df.merge(att_strategy, on="strategy_id", how="left")

    long_df["Units"]           = "NA"
    long_df["Data_Type"]       = "sisepuede simulation"
    long_df["iso_code3"]       = iso_code3
    long_df["Country"]         = region
    long_df["output_type"]     = "drivers"
    long_df["gas"]             = np.nan
    long_df = long_df.drop(columns=[c for c in ("region", "subsector_total_field",
                                                "model_variable_information") if c in long_df.columns])

    # energy_subsector classification
    energy_keywords = {
        "ccsq": "Carbon Capture and Sequestration",
        "inen": "Industrial Energy",
        "entc": "Power(electricity/heat)",
        "trns": "Transportation",
        "scoe": "Buildings",
    }
    long_df["energy_subsector"] = pd.Series(pd.NA, index=long_df.index, dtype=object)
    energy_mask = long_df["variable"].str.contains("energy", regex=False, na=False)
    es = pd.Series("TBD", index=long_df.index, dtype=object)
    for kw, label in energy_keywords.items():
        es = es.where(~long_df["variable"].str.contains(kw, regex=False, na=False), label)
    long_df.loc[energy_mask, "energy_subsector"] = es[energy_mask]

    # GDP history
    gdp = pd.read_csv(wide_inputs_outputs_path, usecols=["primary_id", "time_period", "gdp_mmm_usd"])
    gdp = gdp[gdp["primary_id"] == 0].copy()
    gdp["year"] = gdp["time_period"] + base_year
    gdp = gdp[gdp["year"] <= year_ref][["year", "gdp_mmm_usd"]]

    strategies_df = (
        long_df[["strategy_id", "design_id", "future_id", "strategy"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    gdp = gdp.assign(_k=1).rename(columns={"year": "Year", "gdp_mmm_usd": "value"})
    strategies_df = strategies_df.assign(_k=1)
    drivers_hist = strategies_df.merge(gdp, on="_k").drop(columns="_k")
    drivers_hist["variable"]         = "gdp_mmm_usd"
    drivers_hist["primary_id"]       = 0
    drivers_hist["sector"]           = "Socioeconomic"
    drivers_hist["subsector"]        = "Economy"
    drivers_hist["model_variable"]   = "GDP"
    drivers_hist["category_value"]   = "('', '')"
    drivers_hist["category_name"]    = "cat_economy"
    drivers_hist["gas"]              = np.nan
    drivers_hist["gas_name"]         = ""
    drivers_hist["Units"]            = "NA"
    drivers_hist["Data_Type"]        = "historical"
    drivers_hist["iso_code3"]        = iso_code3
    drivers_hist["Country"]          = region
    drivers_hist["output_type"]      = "drivers"
    drivers_hist["energy_subsector"] = np.nan

    years_in_sim = long_df.loc[long_df["variable"] == "gdp_mmm_usd", "Year"].dropna().unique()
    if len(years_in_sim):
        last_year_in_sim = int(min(years_in_sim))
        drivers_hist = drivers_hist[drivers_hist["Year"] < last_year_in_sim].copy()

    out_cols = [
        "variable", "strategy_id", "primary_id", "value", "sector", "subsector",
        "model_variable", "category_value", "category_name", "gas", "gas_name",
        "Year", "design_id", "future_id", "strategy", "Units", "Data_Type",
        "iso_code3", "Country", "output_type", "energy_subsector",
    ]
    for c in out_cols:
        if c not in long_df.columns:
            long_df[c] = np.nan
        if c not in drivers_hist.columns:
            drivers_hist[c] = np.nan

    final = pd.concat([long_df[out_cols], drivers_hist[out_cols]], ignore_index=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f"[drivers]   {out_path}  ({len(final):,} rows)")
    return final


# ---------------------------------------------------------------------------
# Levers table
# ---------------------------------------------------------------------------

# R make.names() converts spaces and parentheses to dots.
_R_MAKE_NAMES_RENAME = {
    "Sector (output)":            "Sector..output.",
    "Subsector (output)":         "Subsector..output.",
    "Example government policies": "Example.government.policies",
}


def build_levers_table(
    run_dir: Path,
    descriptions_path: Path,
    stakeholder_codes_path: Path,
    out_path: Path,
    levers_filename: str = "tableau_levers_table.csv",
) -> pd.DataFrame:
    """Merges levers_implementation_<region>.csv with descriptions + stakeholder codes."""

    ssp_table = pd.read_csv(run_dir / levers_filename)
    ssp_table["transformation_code"] = ssp_table["transformer_code"].str.replace("TFR:", "", regex=False)

    desp = pd.read_csv(descriptions_path)
    scodes = pd.read_csv(stakeholder_codes_path).rename(columns=_R_MAKE_NAMES_RENAME)
    scodes["transformation_code"] = scodes["transformation_code"].str.replace("TX:", "", regex=False)

    merged = ssp_table.merge(desp, on="transformation_code", how="inner")
    merged = merged.merge(
        scodes[["transformation_code", "transformation_name_stakeholder",
                "Sector..output.", "Subsector..output.", "Example.government.policies"]],
        on="transformation_code",
        how="inner",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out_path, index=False)
    print(f"[levers]    {out_path}  ({len(merged):,} rows)")
    return merged


# ---------------------------------------------------------------------------
# Jobs table
# ---------------------------------------------------------------------------

def build_jobs_table(
    employment_path: Path,
    iso_code3: str,
    out_path: Path,
) -> pd.DataFrame:
    """Splits the ":"-encoded Strategy column and filters to country."""

    jobs = pd.read_csv(employment_path)
    parts = jobs["Strategy"].astype(str).str.split(":", n=1, expand=True)
    jobs["ssp_sector"]                 = parts[0]
    jobs["ssp_transformation_name"]    = parts[1] if parts.shape[1] > 1 else ""
    jobs = jobs[jobs["Country"] == iso_code3].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    jobs.to_csv(out_path, index=False)
    print(f"[jobs]      {out_path}  ({len(jobs):,} rows)")
    return jobs


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def run_tableau_postprocessing(
    run_dir: str | Path,
    project_dir: str | Path,
    region: str,
    iso_code3: str,
    year_ref: int,
    base_year: int = 2015,
    model_region: str | None = None,
    wide_inputs_outputs_filename: str | None = None,
    out_dir: str | Path | None = None,
    drivers_taxonomy_filename: str = "driver_variables_taxonomy_20251013.csv",
    levers_filename: str | None = None,
) -> dict:
    """Generate every Tableau-ready CSV in one call (raw SSP output, no rescaling).

    Parameters
    ----------
    run_dir : run output directory. Must contain the WIDE_INPUTS_OUTPUTS file,
        ATTRIBUTE_PRIMARY.csv and ATTRIBUTE_STRATEGY.csv (plus the levers table
        if you want that export). `decomposed_ssp_output.csv` is NOT used —
        this pipeline reports raw model values.
    project_dir : repo root.
    region : label emitted for Tableau, e.g. "oaxaca".
    model_region : region label SISEPUEDE actually wrote into the WIDE file
        (Oaxaca runs as "mexico"). Defaults to `region`.
    iso_code3 : 3-letter code used in the `Code` column, e.g. "OAX".
    year_ref : cut-off year for the historical GDP series in the drivers table.
    base_year : calendar year of time_period 0 (Oaxaca: 2013).
    wide_inputs_outputs_filename : explicit filename inside run_dir; auto-detected
        when None.
    out_dir : where to write the CSVs (defaults to
        <project_dir>/ssp_modeling/tableau/data).
    drivers_taxonomy_filename : taxonomy file under output_postprocessing/data/.
    levers_filename : defaults to levers_implementation_<region>.csv.
    """
    run_dir     = Path(run_dir)
    project_dir = Path(project_dir)
    out_dir     = Path(out_dir) if out_dir else project_dir / "ssp_modeling" / "tableau" / "data"

    if wide_inputs_outputs_filename is None:
        candidates = sorted(run_dir.glob("*WIDE_INPUTS_OUTPUTS.csv"))
        if not candidates:
            raise FileNotFoundError(f"No *WIDE_INPUTS_OUTPUTS.csv found in {run_dir}")
        wide_path = candidates[-1]
    else:
        wide_path = run_dir / wide_inputs_outputs_filename

    pp_root    = project_dir / "ssp_modeling" / "output_postprocessing"
    pp_data    = pp_root / "data"
    levers_dir = pp_root / "levers_and_jobs_table"

    taxonomy_path          = pp_data / drivers_taxonomy_filename
    descriptions_path      = levers_dir / "ssp_descriptions.csv"
    stakeholder_codes_path = levers_dir / "stakeholder_codes.csv"
    employment_path        = levers_dir / "Sisepuede - Employment Results - WB (SECTOR).csv"

    # the manager notebook writes the levers table as tableau_levers_table.csv;
    # other regions name it levers_implementation_<region>.csv. Accept both.
    if levers_filename is None:
        for cand in (f"levers_implementation_{region}.csv", "tableau_levers_table.csv"):
            if (run_dir / cand).exists():
                levers_filename = cand
                break
        else:
            levers_filename = f"levers_implementation_{region}.csv"

    emissions = build_emissions_table(
        wide_path        = wide_path,
        run_dir          = run_dir,
        taxonomy_path    = taxonomy_path,
        iso_code3        = iso_code3,
        region           = region,
        out_path         = out_dir / f"emissions_{region}.csv",
        base_year        = base_year,
        model_region     = model_region,
    )
    drivers = build_drivers_table(
        wide_inputs_outputs_path = wide_path,
        run_dir                  = run_dir,
        drivers_taxonomy_path    = taxonomy_path,
        iso_code3                = iso_code3,
        region                   = region,
        year_ref                 = year_ref,
        out_path                 = out_dir / f"drivers_{region}.csv",
        base_year                = base_year,
        model_region             = model_region,
    )

    # levers + jobs are OPTIONAL: they need reference files (levers
    # implementation table, stakeholder codes, employment results) that Oaxaca
    # may not have. Skip gracefully when absent.
    levers = None
    if (run_dir / levers_filename).exists() and descriptions_path.exists() and stakeholder_codes_path.exists():
        levers = build_levers_table(
            run_dir                = run_dir,
            descriptions_path      = descriptions_path,
            stakeholder_codes_path = stakeholder_codes_path,
            out_path               = out_dir / "tableau_levers_table_complete.csv",
            levers_filename        = levers_filename,
        )
    else:
        print("[levers]    skipped (reference files not present)")

    jobs = None
    if employment_path.exists():
        jobs = build_jobs_table(
            employment_path = employment_path,
            iso_code3       = iso_code3,
            out_path        = out_dir / f"jobs_demand_{region}.csv",
        )
    else:
        print("[jobs]      skipped (employment file not present)")

    return {"emissions": emissions, "drivers": drivers, "levers": levers, "jobs": jobs}
