from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules.narrative_create import generate_narratives_file


st.set_page_config(page_title="Narrative generation", layout="wide")
st.title("Narrative generation")
st.caption("Generate narrative CSV from the configured event log using Ollama llama3.2.")

components.html(
        """
        <script>
        window.onbeforeunload = function () {
            return "Narrative generation is still running. Leaving this page may interrupt the process.";
        };
        </script>
        """,
        height=0,
)

st.warning("If you close or leave this page during generation, the process will be interrupted at the next safe checkpoint.")

force_raw = str(st.query_params.get("force", "0")).lower()
force = force_raw in {"1", "true", "yes"}

progress_text = st.empty()
progress_bar = st.progress(0.0)


def _on_progress(done: int, total: int, created: int, failed: int) -> bool:
    try:
        fraction = 0.0 if total == 0 else done / total
        progress_bar.progress(fraction)
        progress_text.info(f"Cases created: {created}/{total} (processed: {done}/{total}, failed: {failed})")
        return True
    except Exception:
        # If UI update fails (for example session/browser is gone), request cancellation.
        return False

with st.spinner("Running narrative generation service..."):
    try:
        result = generate_narratives_file(force=force, progress_callback=_on_progress)
    except Exception as exc:
        st.error(f"Narrative generation failed: {exc}")
        st.stop()

status = result.get("status")
output_path = Path(result.get("output_path", ""))
model = result.get("model", "llama3.2")

if status == "already_exists":
    progress_bar.progress(0.0)
    total_cases = result.get("total_cases")
    if total_cases is not None:
        progress_text.info(f"Cases created: 0/{total_cases} (output already exists)")
    else:
        progress_text.info("Cases created: 0/? (output already exists)")
    st.info(f"Output file already exists, no generation executed: {output_path}")
    st.write(f"Model configured: {model}")
else:
    total_cases = int(result.get("total_cases", 0))
    created_cases = int(result.get("generated_rows", 0))
    completed_cases = int(result.get("completed_cases", created_cases))
    status = result.get("status", "generated")

    if status == "cancelled":
        progress_text.warning(f"Generation interrupted. Cases created: {created_cases}/{total_cases}")
        progress_bar.progress(0.0 if total_cases == 0 else completed_cases / total_cases)
        st.warning("Generation was interrupted before completion.")
    else:
        progress_bar.progress(1.0)
        progress_text.success(f"Cases created: {created_cases}/{total_cases}")
        st.success(f"Narrative file generated: {output_path}")

    st.write(f"Created cases: {created_cases}/{total_cases}")
    st.write(f"Processed cases: {completed_cases}/{total_cases}")
    st.write(f"Generated rows: {result.get('generated_rows', 0)}")
    st.write(f"Skipped rows: {result.get('skipped_rows', 0)}")
    failed = result.get("failed_cases", [])
    if failed:
        st.warning(f"Failed cases: {len(failed)}")
        st.write(", ".join(failed[:50]))
    st.write(f"Model used: {model}")

if output_path.exists() and output_path.stat().st_size > 0:
    st.subheader("Output preview")
    try:
        preview_df = pd.read_csv(output_path, sep=";").head(20)
        st.dataframe(preview_df, use_container_width=True)
    except Exception as exc:
        st.warning(f"Cannot preview output file: {exc}")

st.caption("Use query parameter ?force=1 to force regeneration.")
