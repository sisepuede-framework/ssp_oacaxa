"""
data_loading.py
---------------
Thin utilities for loading SSP run artefacts from a run output directory.
"""

import pandas as pd
from pathlib import Path


def load_attribute_tables(run_dir: Path) -> tuple:
    """Return (att_primary, att_strategy) DataFrames from *run_dir*."""
    run_dir = Path(run_dir)
    att_primary  = pd.read_csv(run_dir / "ATTRIBUTE_PRIMARY.csv")
    att_strategy = pd.read_csv(run_dir / "ATTRIBUTE_STRATEGY.csv")
    return att_primary, att_strategy
