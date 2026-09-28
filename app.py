"""
WorkforceGuard: AI, HR Analytics & Algorithmic Governance Cockpit.
Two-Dataset Edition: U.S. BLS Industry Employment & AI Exposure + Pew Research Center Workplace AI Survey.
Completely free of machine learning training or predictive regressions.
"""
import streamlit as st
import streamlit.components.v1 as components
from src.ui.editorial_renderer import build_editorial_html

st.set_page_config(
    page_title="WorkforceGuard · AI Workforce Governance",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Eliminate Streamlit chrome & padding for responsive full-bleed bespoke interface
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {visibility: hidden; height: 0px;}
    [data-testid="stSidebar"] {display: none;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
        width: 100% !important;
    }
    .stApp {
        background-color: #0d1322 !important;
    }
    iframe {
        border: none !important;
        width: 100% !important;
        min-height: 98vh !important;
        background-color: #0d1322 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def main():
    html_content = build_editorial_html()
    components.html(html_content, height=1350, scrolling=True)

if __name__ == "__main__":
    main()
