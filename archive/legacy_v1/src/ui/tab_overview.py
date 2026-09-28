"""
Streamlit Tab: Real Macro AI Adoption, Occupational Exposure & Governance Surveys.
"""
import streamlit as st
import pandas as pd
from src.analytics.loader import (
    load_industry_exposure_data,
    load_occupations_exposure_data,
    load_pew_survey_data,
    load_stanford_governance_data,
)
from src.analytics.metrics import (
    analyze_ai_industry_exposure,
    analyze_pew_ai_sentiment,
    analyze_stanford_governance_gap,
)

def render_overview_tab():
    st.markdown("## 🌐 Real AI Workforce Exposure & Governance Analytics")
    st.markdown(
        """
        Empirical macroeconomic datasets from the **U.S. Bureau of Labor Statistics (BLS)**, 
        **O*NET**, **Pew Research Center**, and the **Stanford HAI AI Index**.
        """
    )
    
    # Load Real Datasets
    with st.spinner("Loading real macroeconomic datasets..."):
        df_ind = load_industry_exposure_data()
        df_occ = load_occupations_exposure_data()
        df_pew = load_pew_survey_data()
        df_stanford = load_stanford_governance_data()
        
    ind_metrics = analyze_ai_industry_exposure(df_ind)
    pew_metrics = analyze_pew_ai_sentiment(df_pew)
    gov_metrics = analyze_stanford_governance_gap(df_stanford)
    
    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Industries Analyzed", f"{ind_metrics['total_industries_analyzed']}", "Real NAICS Sectors")
    with col2:
        st.metric("Total Covered Workforce", f"{ind_metrics['total_covered_workforce'] / 1e6:.1f}M", "BLS 2024 Employment")
    with col3:
        st.metric("Avg AI Exposure Score", f"{ind_metrics['average_exposure_score']} / 10", "AIOE Scale")
    with col4:
        st.metric("Avg Enterprise Governance Gap", f"{gov_metrics['average_governance_gap']}%", "Unmitigated AI Risk")

    st.markdown("---")
    
    # Section 1: BLS Industry AI Exposure
    st.subheader("1. U.S. Industry AI Automation & Exposure Index (BLS / O*NET)")
    st.markdown(
        "Weighted occupational exposure across 355 NAICS private and public industry categories. "
        "High scores indicate routine cognitive tasks susceptible to rapid AI workflow automation."
    )
    
    tab_ind1, tab_ind2 = st.tabs(["Top 10 Most Exposed Industries", "Least Exposed Industries"])
    with tab_ind1:
        top_df = pd.DataFrame(ind_metrics["top_exposed_industries"])[
            ["naics_code", "title", "covered_employment_2024", "weighted_exposure", "exposure_tier"]
        ]
        top_df.columns = ["NAICS", "Industry Title", "Covered Employment (2024)", "Exposure Score (0-10)", "Risk Tier"]
        st.dataframe(top_df, use_container_width=True, hide_index=True)
    with tab_ind2:
        bot_df = pd.DataFrame(ind_metrics["least_exposed_industries"])[
            ["naics_code", "title", "covered_employment_2024", "weighted_exposure", "exposure_tier"]
        ]
        bot_df.columns = ["NAICS", "Industry Title", "Covered Employment (2024)", "Exposure Score (0-10)", "Risk Tier"]
        st.dataframe(bot_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Section 2: Pew Research Center Survey Insights
    st.subheader("2. Pew Research Center: Public Perception of AI in Hiring (ATP Wave 119)")
    st.markdown(
        "National representative survey data (*N = 11,004 U.S. adults*) tracking public trust in AI hiring tools "
        "and perceived fairness across demographic groups."
    )
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Perceived Fairness in AI Hiring Decisions by Demographic Group**")
        df_fairness = pd.DataFrame(pew_metrics["demographic_fairness_views"])
        df_fairness.columns = ["Demographic Cohort", "Acceptable (%)", "Unacceptable (%)", "More Fair Than Humans (%)", "Less Fair (%)"]
        st.dataframe(df_fairness, use_container_width=True, hide_index=True)
        
    with col_p2:
        st.markdown("**Acceptability Across AI Workplace Use Cases (Total U.S. Adults)**")
        df_cases = pd.DataFrame(pew_metrics["use_case_acceptability"])
        df_cases.columns = ["AI Workplace Use Case", "Acceptable (%)", "Unacceptable (%)", "More Fair Than Humans (%)", "Less Fair (%)"]
        st.dataframe(df_cases, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Section 3: Stanford HAI AI Index Governance Deficit
    st.subheader("3. Stanford HAI AI Index: Enterprise Governance & Risk Deficit")
    st.markdown(
        "Global survey of enterprise AI deployment comparing organizational **adoption rate** against the **governance deficit** "
        "(gap between recognizing AI compliance/bias risk and actually executing governance mitigations)."
    )
    df_gov = pd.DataFrame(gov_metrics["functions_ranked_by_deficit"])[
        ["function", "adoption_rate_pct", "risk_recognized_pct", "risk_mitigated_pct", "governance_gap_pct"]
    ]
    df_gov.columns = ["Business Function", "AI Adoption (%)", "Risk Recognized (%)", "Risk Mitigated (%)", "Governance Deficit (%)"]
    st.dataframe(df_gov, use_container_width=True, hide_index=True)
