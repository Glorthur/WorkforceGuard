"""
WorkforceGuard: AI, HR Analytics & Algorithmic Governance Cockpit.
Entry point for the Streamlit multi-tab executive application.
"""
import streamlit as st

st.set_page_config(
    page_title="WorkforceGuard | AI & Algorithmic Governance Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.ui.tab_overview import render_overview_tab
from src.ui.tab_predictive import render_predictive_tab
from src.ui.tab_bias_audit import render_bias_audit_tab
from src.ui.tab_compliance import render_compliance_tab

def main():
    # Sidebar
    with st.sidebar:
        st.title("🛡️ WorkforceGuard")
        st.markdown("**AI & Algorithmic Governance Engine**")
        st.caption("Version 2.4 | Enterprise Compliance Edition")
        st.markdown("---")
        
        st.markdown("### 🏛️ Regulatory Standards")
        st.markdown("- **EEOC 4/5ths Rule** (29 C.F.R. § 1607)")
        st.markdown("- **NYC Local Law 144** (AEDT Audit)")
        st.markdown("- **EU AI Act** (Annex III High-Risk AI)")
        st.markdown("- **Title VII EEO-1** (Federal Benchmarks)")
        st.markdown("---")
        
        st.markdown("### 📊 Empirical Data Sources")
        st.markdown("- **U.S. Bureau of Labor Statistics** (355 Industries)")
        st.markdown("- **O*NET** (342 Detailed Occupations)")
        st.markdown("- **Pew Research Center** (ATP Wave 119)")
        st.markdown("- **Stanford HAI AI Index** (Enterprise Survey)")
        st.markdown("- **EEOC EEO-1 National Aggregate** (56M Workers)")
        st.markdown("---")
        st.info("System Status: **Operational & Audited**")

    # Main Header
    st.title("WorkforceGuard: AI Workforce Analytics & Algorithmic Governance")
    st.markdown(
        "A unified compliance and intelligence engine auditing **AI workplace adoption**, "
        "**occupational exposure**, and **employment algorithmic decision systems** against U.S. and European legal standards."
    )
    
    # Navigation Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌐 Real AI Exposure & Adoption",
        "🔮 Predictive AI & Proxy Detection",
        "⚖️ EEOC Bias Audit & 4/5ths Rule",
        "📜 NYC LL144 & EU AI Act Compliance"
    ])
    
    with tab1:
        render_overview_tab()
    with tab2:
        render_predictive_tab()
    with tab3:
        render_bias_audit_tab()
    with tab4:
        render_compliance_tab()

if __name__ == "__main__":
    main()
