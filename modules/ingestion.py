# modules/ingestion.py
from typing import IO
import pandas as pd

def read_csv(file_like: IO) -> pd.DataFrame:
    return pd.read_csv(file_like)

def df_to_event_log(df: pd.DataFrame, case_id_col: str, timestamp_col: str, label_col: str) -> pd.DataFrame:
    event_log = df.copy()
    return event_log
