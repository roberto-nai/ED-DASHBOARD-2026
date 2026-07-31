# modules/case_view.py
from typing import List, Dict, Optional, Tuple
import pandas as pd
from pathlib import Path
import json
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.statistics.start_activities.log import get as start_activities_module
from pm4py.statistics.end_activities.log import get as end_activities_module
from pm4py.visualization.dfg import visualizer as dfg_visualization
import tempfile
import shutil

def get_all_case_ids(event_log: pd.DataFrame, case_id_col: str) -> List:
    return list(event_log[case_id_col].dropna().unique())

def get_case_trace(event_log: pd.DataFrame, case_id_col: str, case_id_value, timestamp_col: str) -> pd.DataFrame:
    case_df = event_log[event_log[case_id_col] == case_id_value].copy()
    if timestamp_col in case_df.columns:
        case_df = case_df.sort_values(by=timestamp_col)
    return case_df

def compute_case_dfg(case_df: pd.DataFrame, case_id_col: str, activity_col: str, timestamp_col: str, 
                     dfg_dir: Optional[str] = None) -> Optional[str]:
    """
    Compute and visualize DFG for a single case using PM4Py.
    
    Args:
        case_df: DataFrame containing events for a single case
        case_id_col: Name of the case ID column
        activity_col: Name of the activity column
        timestamp_col: Name of the timestamp column
        dfg_dir: Directory to save DFG images and JSON files (optional)
    
    Returns:
        Path to the generated DFG visualization image, or None if generation fails
    """
    if activity_col not in case_df.columns or len(case_df) == 0:
        return None
    
    try:
        # Get case ID for file naming
        case_id = case_df[case_id_col].iloc[0] if case_id_col in case_df.columns else "unknown"
        
        # Convert to PM4Py format
        df_pm4py = case_df.rename(
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
        
        # Discover DFG
        dfg = dfg_discovery.apply(log)
        
        # Get start and end activities using correct modules
        start_activities = start_activities_module.get_start_activities(log)
        end_activities = end_activities_module.get_end_activities(log)
        
        # Visualize DFG
        parameters = {
            dfg_visualization.Variants.FREQUENCY.value.Parameters.FORMAT: "png",
            dfg_visualization.Variants.FREQUENCY.value.Parameters.START_ACTIVITIES: start_activities,
            dfg_visualization.Variants.FREQUENCY.value.Parameters.END_ACTIVITIES: end_activities
        }
        gviz = dfg_visualization.apply(dfg, log=log, parameters=parameters)
        
        # Determine save path
        if dfg_dir:
            dfg_path = Path(dfg_dir)
            dfg_path.mkdir(parents=True, exist_ok=True)
            
            # Save image with case_id as filename
            image_path = dfg_path / f"{case_id}.png"
            dfg_visualization.save(gviz, str(image_path))
            
            # Save DFG graph as JSON
            dfg_json = {
                "case_id": str(case_id),
                "edges": [
                    {
                        "source": str(edge[0]),
                        "target": str(edge[1]),
                        "frequency": int(edge[2])
                    }
                    for edge in [(k[0], k[1], v) for k, v in dfg.items()]
                ],
                "start_activities": {str(k): int(v) for k, v in start_activities.items()},
                "end_activities": {str(k): int(v) for k, v in end_activities.items()}
            }
            
            json_path = dfg_path / f"{case_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dfg_json, f, indent=2, ensure_ascii=False)
            
            return str(image_path)
        else:
            # Save to temporary file if no directory specified
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                dfg_visualization.save(gviz, tmp_file.name)
                return tmp_file.name
            
    except Exception as e:
        print(f"Error generating DFG: {e}")
        return None
