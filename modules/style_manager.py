# modules/style_manager.py
from pathlib import Path
import streamlit as st

def load_css(css_path: str = "style.css") -> None:
    """
    Load a CSS file into Streamlit and inject it into the page.
    """
    css_file = Path(css_path)
    if css_file.exists():
        with css_file.open() as f:
            css = f"<style>{f.read()}</style>"
            st.markdown(css, unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found at: {css_path}")