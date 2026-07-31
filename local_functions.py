# local_functions.py
from pathlib import Path
from typing import Any, Dict, Optional, Union
import pandas as pd
import yaml


def load_config(config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Load the YAML configuration file and return it as a Python dictionary.

    If config_path is not provided, the function assumes that 'config.yml'
    is located in the same directory as this file.
    """
    if config_path is None:
        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / "config.yml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Basic sanity checks or default values can be added here if needed
    return config


def load_event_log(path: Path, sep: str, caseid_col: str, activity_col: str, ts_col: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=sep, dtype={caseid_col: str, activity_col: str})
    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    return df