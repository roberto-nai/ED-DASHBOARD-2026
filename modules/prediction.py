# modules/prediction.py
from typing import Dict
import pandas as pd

def predict_outcome(case_df: pd.DataFrame, model_type: str) -> Dict:
    return {
        "model_type": model_type,
        "predicted_outcome": "Discharged home",
        "probability": 0.78,
        "notes": "Placeholder prediction."
    }
