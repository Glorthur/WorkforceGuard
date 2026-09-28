"""
Streamlit Tab: Predictive AI Intelligence, Flight Risk Scorer & Proxy Explainability.
"""
import streamlit as st
import pandas as pd
from src.analytics.loader import load_attrition_data, load_candidate_data
from src.models.attrition_predictor import AttritionPredictor
from src.models.explainability import get_feature_importances, detect_proxy_variables

@st.cache_resource
def get_fitted_predictor():
    df = load_attrition_data()
    predictor = AttritionPredictor().fit(df)
    return predictor, df

def render_predictive_tab():
    st.markdown("## 🔮 Predictive Intelligence & Proxy-Variable Auditing")
    st.markdown(
        "Evaluate workforce flight risk using calibrated machine learning models while auditing feature attributes "
        "to prevent subtle proxy discrimination (indirect demographic bias)."
    )
    
    predictor, df_attrition = get_fitted_predictor()
    
    col_input, col_output = st.columns([1, 1])
    
    with col_input:
        st.subheader("Employee Profile Input")
        age = st.slider("Employee Age", min_value=18, max_value=65, value=35)
        monthly_income = st.slider("Monthly Income ($)", min_value=1500, max_value=25000, value=6500, step=250)
        overtime = st.selectbox("Overtime Work Required?", ["No", "Yes"], index=1)
        distance = st.slider("Distance From Home (Miles)", min_value=1, max_value=30, value=12)
        satisfaction = st.select_slider("Job Satisfaction (1-4)", options=[1, 2, 3, 4], value=2)
        wlb = st.select_slider("Work-Life Balance (1-4)", options=[1, 2, 3, 4], value=2)
        tenure = st.slider("Years at Company", min_value=0, max_value=25, value=4)
        promo_gap = st.slider("Years Since Last Promotion", min_value=0, max_value=15, value=3)
        department = st.selectbox("Department", ["Research & Development", "Sales", "Human Resources"])
        role = st.selectbox("Job Role", [
            "Sales Executive", "Research Scientist", "Laboratory Technician",
            "Manufacturing Director", "Healthcare Representative", "Manager"
        ])
        
        sample_record = {
            "Age": age,
            "MonthlyIncome": monthly_income,
            "OverTime": overtime,
            "DistanceFromHome": distance,
            "JobSatisfaction": satisfaction,
            "WorkLifeBalance": wlb,
            "YearsAtCompany": tenure,
            "YearsSinceLastPromotion": promo_gap,
            "Department": department,
            "JobRole": role,
            "EmployeeNumber": 9999,
        }
        
    with col_output:
        st.subheader("Model Assessment & Drivers")
        prediction = predictor.predict_flight_risk(sample_record)[0]
        
        # Risk Badge
        badge_color = "🔴" if prediction.risk_level == "High" else ("🟡" if prediction.risk_level == "Medium" else "🟢")
        st.markdown(f"### Flight Risk Tier: {badge_color} **{prediction.risk_level}** ({prediction.probability * 100:.1f}%)")
        
        # Progress indicator
        st.progress(min(1.0, prediction.probability))
        
        st.markdown("**Identified Retention Risk Drivers:**")
        for d in prediction.primary_drivers:
            st.markdown(f"- **{d['factor']}**: {d['value']} (*{d['impact']}*)")
            
        st.markdown("**Recommended Governance & Retention Actions:**")
        for r in prediction.retention_recommendations:
            st.info(f"💡 {r}")

    st.markdown("---")
    
    # Feature Importances & Proxy Variable Detection
    st.subheader("Algorithmic Transparency & Demographic Proxy Detection")
    st.markdown(
        "Under the EU AI Act (Art. 10 & 13) and EEOC Title VII, organizations must audit non-protected operational features "
        "to ensure they do not act as hidden proxies for protected characteristics (e.g., zip code or commute distance acting as a proxy for race/ethnicity)."
    )
    
    col_fi, col_proxy = st.columns([1, 1])
    
    with col_fi:
        st.markdown("**Global Feature Attribution**")
        importances = get_feature_importances(predictor)
        df_imp = pd.DataFrame(list(importances.items()), columns=["Feature", "Relative Importance"]).sort_values("Relative Importance", ascending=False)
        st.dataframe(df_imp, use_container_width=True, hide_index=True)
        
    with col_proxy:
        st.markdown("**Statistical Proxy-Variable Audit Scan**")
        with st.spinner("Scanning feature associations..."):
            df_cand = load_candidate_data()
            proxies = detect_proxy_variables(df_cand, correlation_threshold=0.15)
            
        if proxies:
            df_p = pd.DataFrame(proxies)[["protected_attribute", "candidate_feature", "association_score", "severity"]]
            df_p.columns = ["Protected Attribute", "Candidate Feature", "Association (0-1)", "Risk Level"]
            st.dataframe(df_p, use_container_width=True, hide_index=True)
        else:
            st.success("No high-association proxy variables detected above the 0.15 correlation threshold.")
