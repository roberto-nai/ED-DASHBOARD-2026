# Emergency Department Dashboard

Streamlit dashboard for clinical event log exploration, with modules for statistics, case exploration, narrative generation, prediction, and explainability.

## 1) Activate the virtual environment

If the virtual environment does not exist yet, create it with Python 3.10 and name it `venv310`:

```bash
python3.10 -m venv venv310
```

Then activate it from the project root:

```bash
source venv310/bin/activate
```

Optional check:

```bash
python --version
which python
```

## 2) Run setup

With the environment active, install the project and dependencies:

```bash
pip install --upgrade pip
pip install -e .
```

The `-e` (editable) mode is recommended during development, because code changes are immediately reflected.

## 3) Start the application

Start the Streamlit dashboard:

```bash
streamlit run app.py
```

After startup, open the URL shown in the terminal in your browser (typically for local deployment in http://localhost:8501).

## 4) Narrative creation service

The service page is also available to create the narratives file:

http://localhost:8501/narrative_create

To force regeneration even when the file already exists:

http://localhost:8501/narrative_create?force=1

## 5) Data directory overview

- `event_log`: stores the source event log files used as dashboard input.
- `event_log_dfg`: stores generated Directly-Follows Graph (DFG) outputs for case exploration (for example, JSON/PNG artefacts).
- `event_log_narratives`: stores generated narrative text outputs per case.
- `event_log_predictions`: stores model prediction outputs used by the Outcome Prediction page.
- `event_log_predictions_shap`: stores SHAP explainability outputs and related visual artefacts for model interpretation.

These folders are intentionally kept in the repository structure with `.gitkeep`, while generated data files can remain local.

## 6) Project structure overview

### Main directories

- `modules`: core Python modules containing reusable dashboard logic (data ingestion, statistics, case view/DFG, narrative generation, prediction, XAI, and style loading).
- `.streamlit`: Streamlit configuration files, including page navigation setup (for example, sidebar page labels/order).
- `pages`: additional Streamlit pages beyond the main app (for example, the narrative generation service page).

### Main files in the repository root

- `app.py`: main Streamlit entry point for the dashboard.
- `config.yml`: central configuration file for paths, column names, feature flags, and service settings.
- `local_functions.py`: shared helper functions used across the project (for example, config and event log loading).
- `style.css`: dashboard visual style customisation.
- `setup.py`: package metadata and dependency definition for installation.
- `README.md`: project documentation and usage instructions.
- `.gitignore`: Git tracking rules to keep generated or local-only files out of the public repository.


