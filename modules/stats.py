# modules/stats.py
from typing import Dict
import pandas as pd
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.statistics.variants.log import get as variants_module


def compute_basic_stats(event_log: pd.DataFrame, case_id_col: str, activity_col: str, timestamp_col: str, label_col: str) -> Dict:
    """
    Compute statistics using pm4py.
    
    Returns:
        Dictionary with:
        - num_events: total number of events
        - num_cases: number of distinct cases
        - num_activities: number of distinct activities
        - num_variants: number of process variants
        - avg_case_duration: average case duration (in hours)
        - median_case_duration: median case duration (in hours)
        - label_distribution: distribution of labels with counts and percentages
    """
    # Basic counts
    num_rows = len(event_log)
    num_cols = len(event_log.columns)
    num_cases = event_log[case_id_col].nunique() if case_id_col in event_log.columns else 0
    num_activities = event_log[activity_col].nunique() if activity_col in event_log.columns else 0
    
    # Convert to pm4py format
    df_pm4py = event_log.rename(
        columns={
            case_id_col: "case:concept:name",
            timestamp_col: "time:timestamp",
            activity_col: "concept:name"
        }
    )
    
    # Ensure timestamp is datetime
    if "time:timestamp" in df_pm4py.columns:
        df_pm4py["time:timestamp"] = pd.to_datetime(df_pm4py["time:timestamp"], errors="coerce")
    
    df_pm4py = dataframe_utils.convert_timestamp_columns_in_df(df_pm4py)
    log = log_converter.apply(df_pm4py)
    
    # Calculate number of variants
    variants = variants_module.get_variants(log)
    num_variants = len(variants)
    
    # Calculate case durations
    case_durations = []
    for trace in log:
        if len(trace) > 0:
            start_time = trace[0]["time:timestamp"]
            end_time = trace[-1]["time:timestamp"]
            duration = (end_time - start_time).total_seconds()  # Keep in seconds
            case_durations.append(duration)
    
    # Calculate average and median durations
    if case_durations:
        avg_seconds = sum(case_durations) / len(case_durations)
        median_seconds = pd.Series(case_durations).median()
        
        # Convert to hours, minutes, seconds
        avg_case_duration = {
            "hours": int(avg_seconds // 3600),
            "minutes": int((avg_seconds % 3600) // 60),
            "seconds": round(avg_seconds % 60, 2)
        }
        median_case_duration = {
            "hours": int(median_seconds // 3600),
            "minutes": int((median_seconds % 3600) // 60),
            "seconds": round(median_seconds % 60, 2)
        }
    else:
        avg_case_duration = {"hours": 0, "minutes": 0, "seconds": 0}
        median_case_duration = {"hours": 0, "minutes": 0, "seconds": 0}
    
    # Label distribution grouped by cases
    label_distribution = {}
    if label_col in event_log.columns:
        # Get first label per case (assuming label is consistent within a case)
        case_labels = event_log.groupby(case_id_col)[label_col].first()
        label_counts = case_labels.value_counts()
        total_cases_with_label = label_counts.sum()
        
        label_distribution = {
            "counts": label_counts.to_dict(),
            "percentages": {
                label: round(count / total_cases_with_label * 100, 2) 
                for label, count in label_counts.items()
            }
        }
    
    return {
        "num_rows": num_rows,
        "num_cols": num_cols,
        "num_cases": num_cases,
        "num_activities": num_activities,
        "num_variants": num_variants,
        "avg_case_duration": avg_case_duration,
        "median_case_duration": median_case_duration,
        "label_distribution": label_distribution,
    }
