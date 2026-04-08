"""Revenue Intelligence Agent - Streamlit Dashboard Entry Point."""

import streamlit as st

st.set_page_config(
    page_title="Revenue Intelligence Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from streamlit_app.components.styles import apply_global_styles
apply_global_styles()

from streamlit_app.pages.executive_overview import render
render()