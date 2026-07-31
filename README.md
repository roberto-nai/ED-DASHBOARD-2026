# Emergency Department Dashboard

Streamlit dashboard for clinical event log exploration, with modules for statistics, case exploration, narrative generation, prediction, and explainability.

## 1) Activate the virtual environment

From the terminal, move to the project folder:

```bash
cd "/Volumes/SAMSUNG-PHD/PhD/Articoli MIEI/Knoweledge and Information System 2026 (ex ACM 2025)/ED_dashboard"
```

Activate the virtual environment already included in the project:

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
