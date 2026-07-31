# app.py
from pathlib import Path
import streamlit as st
import pandas as pd
from modules import ingestion, stats, case_view, narrative, prediction, xai
from modules.style_manager import load_css
from local_functions import load_config, load_event_log
import matplotlib.pyplot as plt

# -------------------------------------------------------------------------
# Load configuration from YAML
# -------------------------------------------------------------------------
CONFIG = load_config()

# Column names are centralised in the configuration file
CASE_ID_COL = CONFIG["columns"]["case_id"]
TIMESTAMP_COL = CONFIG["columns"]["timestamp"]
ACTIVITY_COL = CONFIG["columns"]["activity"]
LABEL_COL = CONFIG["columns"]["label"]

EVENT_LOG_DIRECTORY = CONFIG["event_log_directory"]
EVENT_LOG_FILE = CONFIG["event_log_file"]
EVENT_LOG_PATH = Path(EVENT_LOG_DIRECTORY) / EVENT_LOG_FILE
CSV_SEPARATOR = CONFIG["csv_separator"]

# DFG
DFG_DIR = CONFIG.get("event_log_dfg_dir")

# NARRATIVES
NARRATIVE_DIR = CONFIG.get("event_log_narrative_dir")
NARRATIVE_FILE = CONFIG.get("event_log_narrative_file")
NARRATIVE_PATH = Path(NARRATIVE_DIR) / NARRATIVE_FILE
NARRATIVE_COL_CASE_ID = CONFIG["narrative_columns"]["case_id"]
NARRATIVE_COL_TEXT = CONFIG["narrative_columns"]["narrative"]
NARRATIVE_COL_LABEL = CONFIG["narrative_columns"]["label"]

# PREDICTIONS
PREDICTIONS_DIR = CONFIG.get("event_log_predictions_dir")
PREDICTIONS_FILE = CONFIG.get("event_log_predictions_file")
PREDICTIONS_PATH = Path(PREDICTIONS_DIR) / PREDICTIONS_FILE

# XAI SHAP explanations
XAI_SHAP_DIR = CONFIG.get("event_log_predictions_shap_dir")
XAI_SHAP_FILE = CONFIG.get("event_log_predictions_shap_file")
XAI_SHAP_PATH = Path(XAI_SHAP_DIR) / XAI_SHAP_FILE
XAI_TOP_FEATURES = CONFIG.get("xai_top_features", 5)
XAI_FEATURE_COL = CONFIG.get("xai_feature_col", "original_name")
XAI_IMPORTANCE_COL = CONFIG.get("xai_importance_col", "importance")
XAI_PLOT_WIDTH = CONFIG.get("xai_plot_width", 12)
XAI_PLOT_HEIGHT = CONFIG.get("xai_plot_height", 6)

# Tab enable/disable flags from configuration
TAB_FLAGS = CONFIG.get("tabs", {})
PAGE_TITLE = CONFIG["page_title"]
STYLE_FILE = CONFIG["style_file"]

# -------------------------------------------------------------------------
# Page configuration and initial session state
# -------------------------------------------------------------------------
st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide"
)

# Load custom CSS for theme and styling
load_css(STYLE_FILE)

def ensure_session_state() -> None:
    """
    Ensure that all required variables exist in Streamlit's session state.
    This avoids KeyError when accessing them for the first time.
    """
    if "raw_df" not in st.session_state:
        st.session_state.raw_df = None
    if "event_log" not in st.session_state:
        st.session_state.event_log = None
    if "selected_case_id" not in st.session_state:
        st.session_state.selected_case_id = None


ensure_session_state()

# -------------------------------------------------------------------------
# Page title and short description
# -------------------------------------------------------------------------
# st.title(PAGE_TITLE)

# Display logo centred using CSS class
# Centre logo using Streamlit, style the container via CSS
st.markdown('<div class="dashboard-logo">', unsafe_allow_html=True)
st.image("logo.png", width=64)
st.markdown('</div>', unsafe_allow_html=True)

# Dashboard Title using CSS class
st.markdown(
    """
    <div class="dashboard-title">""" + PAGE_TITLE + """</div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    # """ This dashboard provides a modular pipeline following the tabs below."""
    """ Select one of the tabs below """
)

# -------------------------------------------------------------------------
# Define tabs (Case Table + DFG in one tab)
# -------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "> Import Data ",
    "> Global Statistics ",
    "> Case Exploration ",
    "> Narrative Generation ",
    "> Outcome Prediction ",
    "> Outcome Explanation "
])

# -------------------------------------------------------------------------
# TAB 1 – Import & Event Log
# -------------------------------------------------------------------------
with tab1:
    if not TAB_FLAGS.get("import_event_log", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Import Data")

        uploaded_file = st.file_uploader(
            "Upload CSV file",
            type=["csv"],
            help="Select a CSV file containing clinical process data."
        )

        if uploaded_file is not None:
            # Load raw CSV via ingestion module
            raw_df: pd.DataFrame = ingestion.read_csv(uploaded_file)
            st.session_state.raw_df = raw_df

            st.subheader("Preview of uploaded CSV")
            st.dataframe(raw_df.head())

            st.write("---")
            st.markdown("**Event log conversion (placeholder)**")

            # Convert raw DataFrame into event log through a dedicated module
            event_log = ingestion.df_to_event_log(
                raw_df,
                case_id_col=CASE_ID_COL,
                timestamp_col=TIMESTAMP_COL,
                label_col=LABEL_COL
            )
            st.session_state.event_log = event_log

            st.subheader("Preview of event log (placeholder)")
            st.dataframe(event_log.head())
        else:
            # st.info("Please upload a CSV file to start the pipeline.")
            st.info(f"Event log imported and saved to '{EVENT_LOG_PATH}'. Context features added: DAY_, CONCURRENT-ESI-, SHIFT")
            event_log = load_event_log(
                path=EVENT_LOG_PATH,
                sep=CSV_SEPARATOR,
                caseid_col=CASE_ID_COL,
                activity_col=ACTIVITY_COL,
                ts_col=TIMESTAMP_COL
            )
            st.session_state.event_log = event_log
            
            # Mostra shape e preview del dataframe caricato
            st.write(f"**Shape:** {event_log.shape[0]} rows × {event_log.shape[1]} columns")
            
            # Prepara il dataframe per la visualizzazione
            PREVIEW_HEAD = 20
            df_preview = event_log.head(PREVIEW_HEAD).copy()
            
            # Formatta le colonne con decimali se esistono
            if 'CASE_DURATION_sec' in df_preview.columns:
                df_preview['CASE_DURATION_sec'] = df_preview['CASE_DURATION_sec'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
            if 'REMAINING_TIME_sec' in df_preview.columns:
                df_preview['REMAINING_TIME_sec'] = df_preview['REMAINING_TIME_sec'].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
            
            # Sostituisci tutti i valori NaN/None con "-"
            df_preview = df_preview.fillna("-")
            
            # Applica styling con sfondo grigio chiaro e nascondi l'indice
            styled_df = df_preview.style.set_properties(**{'text-align': 'left'}).hide(axis='index')
            st.table(styled_df)

# -------------------------------------------------------------------------
# TAB 2 – Global Statistics
# -------------------------------------------------------------------------
with tab2:
    if not TAB_FLAGS.get("global_statistics", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Global Statistics")

        if st.session_state.event_log is None:
            st.warning("No event log available. Please upload a CSV in the first tab.")
        else:
            event_log = st.session_state.event_log

            # st.write("This section reports basic statistics over the event log.")
            st.subheader("Basic statistics")

            # The stats module returns a dictionary with aggregates
            basic_stats = stats.compute_basic_stats(
                event_log,
                case_id_col=CASE_ID_COL,
                activity_col = ACTIVITY_COL,
                timestamp_col=TIMESTAMP_COL,
                label_col=LABEL_COL
            )

            # First row with 3 columns
            col1, col2, col3 = st.columns(3)
            with col1:
                shape = f"{basic_stats['num_rows']} × {basic_stats['num_cols']}"
                st.metric("Event log shape \n (rows × columns)", shape)
            with col2:
                st.metric("Number of cases", basic_stats["num_cases"])
            with col3:
                st.metric("Number of activities", basic_stats["num_activities"])
            
            # Second row with 3 columns
            col4, col5, col6 = st.columns(3)
            with col4:
                st.metric("Number of variants", basic_stats["num_variants"])
            with col5:
                avg_dur = basic_stats["avg_case_duration"]
                avg_dur_str = f"{avg_dur['hours']}h {avg_dur['minutes']}m {avg_dur['seconds']}s"
                st.metric("Average case duration", avg_dur_str)
            with col6:
                med_dur = basic_stats["median_case_duration"]
                med_dur_str = f"{med_dur['hours']}h {med_dur['minutes']}m {med_dur['seconds']}s"
                st.metric("Median case duration", med_dur_str)

            # st.write("---")
            st.subheader("Label distribution")
            # st.write(basic_stats["label_distribution"]) # JSON-like dict
            label_dist = basic_stats["label_distribution"]
            if label_dist and "counts" in label_dist and "percentages" in label_dist:
                # Create a DataFrame from the label distribution
                df_labels = pd.DataFrame({
                    "Label": list(label_dist["counts"].keys()),
                    "Counts": list(label_dist["counts"].values()),
                    "Percentages": [f"{p}%" for p in label_dist["percentages"].values()]
                })
                df_labels.index = df_labels.index + 1
                df_labels.index.name = "#"
                
                # Style the table with left alignment for all columns
                styled_df = df_labels.style.set_properties(**{'text-align': 'left'})
                st.table(styled_df)
            else:
                st.info("No label distribution available.")
            


# -------------------------------------------------------------------------
# TAB 3 – Case View (Table + DFG)
# -------------------------------------------------------------------------
with tab3:
    if not TAB_FLAGS.get("case_view", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Case Exploration")

        if st.session_state.event_log is None:
            st.warning("No event log available. Please upload a CSV in the first tab.")
        else:
            event_log = st.session_state.event_log

            st.markdown(
                '<p style="margin-bottom: -5px; margin-top: 0px;">Select a case identifier to inspect its sequence of events and visualise the corresponding directly-follows graph (DFG).</p>',
                unsafe_allow_html=True
            )

            # Custom CSS per modificare lo stile della selectbox
            st.markdown(
                """
                <style>
                /* Stile per la selectbox in tab3 */
                div[data-baseweb="select"] > div {
                    background-color: #f0f0f0 !important;
                    color: #000000 !important;
                }
                div[data-baseweb="select"] input {
                    color: #000000 !important;
                }
                div[data-baseweb="select"] svg {
                    color: #000000 !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            if CASE_ID_COL not in event_log.columns:
                st.error(
                    f"Column '{CASE_ID_COL}' not found in the event log. "
                    "Please adapt the configuration to match your schema."
                )
            else:
                # Ask the case_view module for all distinct case identifiers
                all_case_ids = case_view.get_all_case_ids(
                    event_log,
                    case_id_col=CASE_ID_COL
                )

                selected_case_id = st.selectbox(
                    " ", # empty label (mandatory) to reduce clutter
                    options=all_case_ids,
                    index=0 if len(all_case_ids) > 0 else None
                )
                st.session_state.selected_case_id = selected_case_id

                # Table view for the selected case
                case_df = case_view.get_case_trace(
                    event_log,
                    case_id_col=CASE_ID_COL,
                    case_id_value=selected_case_id,
                    timestamp_col=TIMESTAMP_COL
                )
                
                st.subheader("Case details")
                num_events = len(case_df)
                with st.expander(f"{num_events} events: click to expand", expanded=False): # set expanded = False to have the expander closed by default
                    st.dataframe(case_df)

                st.subheader("DFG")
                # st.write("DFG saved in directory: " + str(DFG_DIR))

                # Generate DFG visualization using PM4Py
                dfg_image_path = case_view.compute_case_dfg(
                    case_df,
                    case_id_col=CASE_ID_COL,
                    activity_col=ACTIVITY_COL,
                    timestamp_col=TIMESTAMP_COL,
                    dfg_dir=DFG_DIR
                )
                
                if dfg_image_path:
                    st.image(dfg_image_path, caption=f"DFG for selected case {selected_case_id}", use_container_width=True)
                else:
                    st.warning("Unable to generate DFG for this case.")


# -------------------------------------------------------------------------
# TAB 4 – Narrative View (LLM-based)
# -------------------------------------------------------------------------
with tab4:
    if not TAB_FLAGS.get("narrative_view", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Narrative Generation")

        if st.session_state.event_log is None:
            st.warning("No event log available. Please upload a CSV in the first tab.")
        else:
            event_log = st.session_state.event_log

            st.markdown(
                '<p style="margin-bottom: 5px; margin-top: 0px;">Select a case identifier to view its narrative description.</p>',
                unsafe_allow_html=True
            )

            if CASE_ID_COL not in event_log.columns:
                st.error(
                    f"Column '{CASE_ID_COL}' not found in the event log. "
                    "Please adapt the configuration to match your schema."
                )
            else:
                # Ask the case_view module for all distinct case identifiers
                all_case_ids = case_view.get_all_case_ids(
                    event_log,
                    case_id_col=CASE_ID_COL
                )

                # Custom CSS to reduce spacing above selectbox
                st.markdown(
                    """
                    <style>
                    div[data-testid="stSelectbox"] {
                        margin-top: -20px !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                selected_narrative_case_id = st.selectbox(
                    " ",  # empty label to reduce clutter
                    options=all_case_ids,
                    index=0 if len(all_case_ids) > 0 else None,
                    key="narrative_case_selector"  # unique key to differentiate from Case View selectbox
                )

                # Load narrative file and find the narrative for selected case
                try:
                    narrative_df = pd.read_csv(NARRATIVE_PATH, sep=CSV_SEPARATOR)
                    
                    # Convert case IDs to string for consistent comparison
                    narrative_df[NARRATIVE_COL_CASE_ID] = narrative_df[NARRATIVE_COL_CASE_ID].astype(str)
                    selected_case_id_str = str(selected_narrative_case_id)
                    
                    # Filter by selected case ID
                    case_narrative = narrative_df[narrative_df[NARRATIVE_COL_CASE_ID] == selected_case_id_str]
                    
                    if not case_narrative.empty:
                        # Get narrative text and label
                        narrative_text = case_narrative[NARRATIVE_COL_TEXT].iloc[0]
                        narrative_label = case_narrative[NARRATIVE_COL_LABEL].iloc[0]
                        
                        # Display narrative in a text area with gray background and black text
                        st.markdown(
                            """
                            <style>
                            /* Stile per textarea narrative */
                            textarea {
                                background-color: #f0f0f0 !important;
                                color: #000000 !important;
                            }
                            /* Stile per text input label - include disabled state */
                            input[type="text"],
                            input[type="text"]:disabled {
                                background-color: #f0f0f0 !important;
                                color: #000000 !important;
                                -webkit-text-fill-color: #000000 !important;
                                opacity: 1 !important;
                            }
                            </style>
                            """,
                            unsafe_allow_html=True
                        )

                        
                        st.text_area(
                            f"Narrative ({selected_case_id_str})",
                            value=str(narrative_text),
                            height=300,
                            disabled=False,
                            key="narrative_text_display"
                        )

                        # Display label in disabled text input
                        st.text_input(
                            "Label",
                            value=str(narrative_label),
                            disabled=True,
                            key="narrative_label_display"
                        )

                    else:
                        st.warning(f"No narrative found for case ID: {selected_narrative_case_id}")
                        
                except FileNotFoundError:
                    st.error(f"Narrative file not found at: {NARRATIVE_PATH}")
                except Exception as e:
                    st.error(f"Error loading narrative: {e}")


# -------------------------------------------------------------------------
# TAB 5 – Outcome Prediction (traditional vs embedding-based)
# -------------------------------------------------------------------------
with tab5:
    if not TAB_FLAGS.get("outcome_prediction", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Outcome Prediction")
        st.write("<br>", unsafe_allow_html=True)  # Add a line break for spacing

        # Carica il file delle predizioni
        try:
            if PREDICTIONS_PATH.exists():
                predictions_df = pd.read_csv(PREDICTIONS_PATH, sep=CSV_SEPARATOR)
                
                # Verifica che la colonna caseid esista
                if "caseid" in predictions_df.columns:
                    # Ottieni la lista dei casi distinti
                    unique_cases = sorted(predictions_df["caseid"].unique())
                    
                    # Selectbox per scegliere il caso
                    selected_case = st.selectbox(
                        "Select a case:",
                        options=unique_cases,
                        index=0 if len(unique_cases) > 0 else None
                    )
                    
                    if selected_case:
                        # Filtra le predizioni per il caso selezionato
                        case_predictions = predictions_df[predictions_df["caseid"] == selected_case]
                        
                        # Mostra le informazioni richieste
                        st.subheader(f"Prediction details per case ({selected_case})")
                        
                        # Verifica se la predizione è corretta
                        true_outcome = case_predictions["true_outcome"].iloc[0]
                        predicted_outcome = case_predictions["predicted_outcome"].iloc[0]
                        is_correct = (true_outcome == predicted_outcome)
                        
                        # Crea colonne per visualizzare i dati
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("True Outcome", true_outcome)
                            st.metric("Model", case_predictions["model"].iloc[0])
                        
                        with col2:
                            st.metric("Predicted Outcome", predicted_outcome)
                            st.metric("Prediction Probability", f"{case_predictions['prediction_probability'].iloc[0]:.3f}")
                        
                        # Mostra indicatore di correttezza
                        if is_correct:
                            st.success("✅ Correct prediction: True Outcome matches Predicted Outcome")
                        else:
                            st.error("❌ Incorrect prediction: True Outcome differs from Predicted Outcome")

                        # Mostra tutte le predizioni per questo caso (se ce ne sono multiple)
                        if len(case_predictions) > 1:
                            st.subheader("All tentative predictions for this case:")
                            
                            # Prepara il dataframe nello stesso stile di tab2
                            df_predictions = case_predictions[[
                                "true_outcome", 
                                "predicted_outcome", 
                                "model", 
                                "prediction_probability",
                                "is_correct"
                            ]].copy()
                            
                            # Rinomina colonne per renderle più leggibili
                            df_predictions.columns = ["True Outcome", "Predicted Outcome", "Model", "Probability", "Correct (1 = yes, 0 = no)"]
                            
                            # Resetta l'indice e numeralo da 1
                            df_predictions.index = range(1, len(df_predictions) + 1)
                            df_predictions.index.name = "#"
                            
                            # Applica styling con sfondo grigio chiaro come in tab2
                            styled_df = df_predictions.style.set_properties(**{'text-align': 'left'})
                            st.table(styled_df)                            
                            # Legenda dei modelli
                            st.markdown(
                                '<p style="font-size: 0.8em; color: #666666; margin-top: 10px;">'
                                '<strong>Model legend:</strong> '
                                'LGBM = LightGBM, '
                                'LR = Logistic Regression, '
                                'RF = Random Forest, '
                                'XGB = XGBoost'
                                '</p>',
                                unsafe_allow_html=True
                            )                
                else:
                    st.error(f"The '{CASE_ID_COL}' column was not found in the prediction file. Please check the file format.")
            else:
                st.error(f"File not found: {PREDICTIONS_PATH}")
        except Exception as e:
            st.error(f"Error loading predictions: {e}")


# -------------------------------------------------------------------------
# TAB 6 – XAI Explanation (for traditional models)
# -------------------------------------------------------------------------
with tab6:
    if not TAB_FLAGS.get("xai_explanation", True):
        st.warning("This tab is disabled in the configuration file.")
    else:
        st.header("> Outcome Explanation")
        st.write("<br>", unsafe_allow_html=True)
        
        # Load and display SHAP feature importance
        try:
            if XAI_SHAP_PATH.exists():
                
                
                # Read SHAP values file
                shap_df = pd.read_csv(XAI_SHAP_PATH, sep=CSV_SEPARATOR)
                
                # Get top features
                top_features_df = shap_df.head(XAI_TOP_FEATURES)
                
                # Use configured column names
                feature_col = XAI_FEATURE_COL
                importance_col = XAI_IMPORTANCE_COL
                
                # Create horizontal bar chart for SHAP feature importance
                fig, ax = plt.subplots(figsize=(XAI_PLOT_WIDTH, XAI_PLOT_HEIGHT))
                
                # Get feature names and importance values - convert to proper types
                features = top_features_df[feature_col].astype(str).values
                importance = top_features_df[importance_col].astype(float).values
                
                # Create horizontal bars
                bars = ax.barh(range(len(features)), importance, color='steelblue', alpha=0.85)
                
                # Add value labels on bars
                for i, (bar, value) in enumerate(zip(bars, importance)):
                    ax.text(float(value) + 0.001, i, f'{float(value):.3f}', 
                            va='center', fontsize=10, fontweight='bold')
                
                # Customize plot
                ax.set_yticks(range(len(features)))
                ax.set_yticklabels(features, fontsize=11)
                ax.set_xlabel('Mean |SHAP value| (average impact on model output)', fontsize=12, fontweight='bold')
                ax.set_ylabel('Feature', fontsize=12, fontweight='bold')
                plt_title = f'Top {XAI_TOP_FEATURES} most important features (best model XGB)'
                ax.set_title(plt_title, fontsize=14, fontweight='bold', pad=20)
                ax.grid(axis='x', alpha=0.3, linestyle='--')
                ax.invert_yaxis()  # Highest importance at top
                
                # Remove top and right spines
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                
                plt.tight_layout()
                
                # Save plot with top features in filename
                shap_plot_filename = str(XAI_SHAP_FILE).replace('.csv', f'_top{XAI_TOP_FEATURES}_plot.png')
                shap_plot_path = Path(XAI_SHAP_DIR) / shap_plot_filename
                plt.savefig(shap_plot_path, dpi=300, bbox_inches='tight')
                
                # Display info message
                st.info(f"SHAP importance plot saved to '{shap_plot_path}'")
                
                # Display the plot in Streamlit - left aligned
                st.image(str(shap_plot_path), use_container_width=False)
                plt.close()
                
            else:
                st.error(f"SHAP values file not found: {XAI_SHAP_PATH}")
                
        except Exception as e:
            st.error(f"Error loading SHAP values: {e}")