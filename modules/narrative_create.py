from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json
import urllib.error
import urllib.request

import pandas as pd

from local_functions import load_config


PROMPT_FILE = Path(__file__).resolve().parent / "narrative_prompt.txt"
ProgressCallback = Callable[[int, int, int, int], bool]


def _load_prompt(prompt_path: Path) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def _to_text(value: Any) -> str:
    if pd.isna(value):
        return "-"
    return str(value)


def _build_case_event_text(case_df: pd.DataFrame, timestamp_col: str) -> str:
    ordered = case_df.sort_values(by=timestamp_col) if timestamp_col in case_df.columns else case_df
    lines: List[str] = []

    for _, row in ordered.iterrows():
        parts = [f"{col}: {_to_text(row[col])}" for col in ordered.columns]
        lines.append(" | ".join(parts))

    return "\n".join(lines)


def _call_ollama_chat(
    *,
    model: str,
    endpoint_url: str,
    system_prompt: str,
    user_content: str,
    request_timeout_seconds: int,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 1,
            # -1 asks Ollama to avoid hard truncation and stop only when model decides to end.
            "num_predict": -1,
        },
    }

    request = urllib.request.Request(
        url=endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=request_timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach Ollama at {endpoint_url}: {exc}") from exc

    parsed = json.loads(response_body)
    message = parsed.get("message", {})
    content = message.get("content", "")
    return content.strip()


def _safe_total_cases(input_path: Path, csv_sep: str, case_col: str) -> Optional[int]:
    try:
        cases_df = pd.read_csv(input_path, sep=csv_sep, usecols=[case_col])
        return int(cases_df[case_col].nunique())
    except Exception:
        return None


def generate_narratives_file(force: bool = False, progress_callback: Optional[ProgressCallback] = None) -> Dict[str, Any]:
    """
    Generate narrative CSV from input event log if output does not already exist.

    Returns a dictionary with metadata about the execution outcome.
    """
    config = load_config()

    event_log_dir = Path(config["event_log_directory"])
    event_log_file = config["event_log_file"]
    csv_sep = config.get("csv_separator", ";")

    input_path = event_log_dir / event_log_file

    narrative_dir = Path(config["event_log_narrative_dir"])
    narrative_file = config["event_log_narrative_file"]
    output_path = narrative_dir / narrative_file

    columns_cfg = config["columns"]
    case_col = columns_cfg["case_id"]
    ts_col = columns_cfg["timestamp"]
    label_col = columns_cfg["label"]

    narrative_columns_cfg = config["narrative_columns"]
    out_case_col = narrative_columns_cfg["case_id"]
    out_narrative_col = narrative_columns_cfg["narrative"]
    out_label_col = narrative_columns_cfg["label"]

    service_cfg = config.get("narrative_service", {})
    model = service_cfg.get("model", "llama3.2")
    endpoint_url = service_cfg.get("ollama_url", "http://localhost:11434/api/chat")
    max_workers = int(service_cfg.get("max_workers", 3))
    request_timeout_seconds = int(service_cfg.get("request_timeout_seconds", 1800))

    prompt_path_cfg = service_cfg.get("prompt_file")
    if prompt_path_cfg:
        prompt_path = Path(prompt_path_cfg)
        if not prompt_path.is_absolute():
            prompt_path = Path(__file__).resolve().parent.parent / prompt_path
    else:
        prompt_path = PROMPT_FILE

    total_cases = _safe_total_cases(input_path=input_path, csv_sep=csv_sep, case_col=case_col)

    if output_path.exists() and output_path.stat().st_size > 0 and not force:
        return {
            "status": "already_exists",
            "output_path": str(output_path),
            "generated_rows": 0,
            "skipped_rows": None,
            "failed_cases": [],
            "model": model,
            "total_cases": total_cases,
        }

    if not input_path.exists():
        raise FileNotFoundError(f"Input event log not found: {input_path}")

    prompt_text = _load_prompt(prompt_path)

    df = pd.read_csv(input_path, sep=csv_sep)
    required_columns = {case_col, ts_col, label_col}
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in input CSV: {sorted(missing)}")

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    df = df.sort_values(by=[case_col, ts_col], kind="stable").reset_index(drop=True)

    grouped = list(df.groupby(case_col, sort=False))
    total_cases = len(grouped)
    failed_cases: List[str] = []
    results: List[Dict[str, Any]] = []
    completed_cases = 0
    cancelled = False

    def _process_case(case_id: Any, group: pd.DataFrame) -> Dict[str, Any]:
        case_events = _build_case_event_text(group, ts_col)
        narrative = _call_ollama_chat(
            model=model,
            endpoint_url=endpoint_url,
            system_prompt=prompt_text,
            user_content=case_events,
            request_timeout_seconds=request_timeout_seconds,
        )

        label_value = group[label_col].iloc[0] if not group.empty else "-"
        return {
            out_case_col: str(case_id),
            out_narrative_col: narrative,
            out_label_col: _to_text(label_value),
        }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        next_idx = 0
        future_to_case: Dict[Any, Any] = {}

        def _submit_one() -> bool:
            nonlocal next_idx
            if next_idx >= total_cases:
                return False
            case_id, group = grouped[next_idx]
            next_idx += 1
            future = executor.submit(_process_case, case_id, group.copy())
            future_to_case[future] = case_id
            return True

        initial = min(max_workers, total_cases)
        for _ in range(initial):
            _submit_one()

        while future_to_case:
            done_futures, _ = wait(set(future_to_case.keys()), return_when=FIRST_COMPLETED)

            for future in done_futures:
                case_id = future_to_case.pop(future)
                try:
                    results.append(future.result())
                except Exception:
                    failed_cases.append(str(case_id))
                finally:
                    completed_cases += 1

                keep_running = True
                if progress_callback is not None:
                    try:
                        keep_running = bool(progress_callback(completed_cases, total_cases, len(results), len(failed_cases)))
                    except Exception:
                        keep_running = False

                if not keep_running:
                    cancelled = True
                    break

                _submit_one()

            if cancelled:
                for pending_future in future_to_case.keys():
                    pending_future.cancel()
                break

    output_df = pd.DataFrame(results, columns=[out_case_col, out_narrative_col, out_label_col])

    if not output_df.empty:
        output_df = output_df.sort_values(by=out_case_col, kind="stable").reset_index(drop=True)

    narrative_dir.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, sep=csv_sep, index=False)

    status = "cancelled" if cancelled else "generated"

    return {
        "status": status,
        "output_path": str(output_path),
        "generated_rows": int(len(output_df)),
        "skipped_rows": int(len(grouped) - len(output_df)),
        "failed_cases": failed_cases,
        "model": model,
        "total_cases": total_cases,
        "completed_cases": completed_cases,
    }
