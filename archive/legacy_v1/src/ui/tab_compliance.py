"""
Streamlit Tab: Regulatory Compliance Center (NYC Local Law 144 & EU AI Act Annex III).
"""
import streamlit as st
import pandas as pd
from src.analytics.loader import load_candidate_data
from src.governance.bias_audit import audit_all_protected_attributes
from src.governance.nyc_ll144 import generate_nyc_ll144_report, format_nyc_ll144_markdown
from src.governance.eu_ai_act import evaluate_eu_ai_act_conformity
from src.governance.policy_remediation import optimize_selection_threshold

def render_compliance_tab():
    st.markdown("## 📜 Regulatory AI Compliance & Legal Audit Center")
    st.markdown(
        "Direct statutory compliance engines for **NYC Local Law 144 (AEDT)** and the **EU AI Act (Regulation EU 2024/1689)**."
    )
    
    df_candidates = load_candidate_data()
    audits = audit_all_protected_attributes(df_candidates)
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs([
        "NYC Local Law 144 AEDT Audit",
        "EU AI Act High-Risk Conformity",
        "Algorithmic Policy Remediation"
    ])
    
    # 1. NYC LL144 Tab
    with sub_tab1:
        st.subheader("New York City Local Law 144: AEDT Annual Public Audit")
        st.markdown(
            "Employers in New York City using Automated Employment Decision Tools (AEDT) to screen candidates or promote workers "
            "must publish an independent annual bias audit summary table on their public careers website."
        )
        report = generate_nyc_ll144_report(df_candidates, tool_name="WorkforceGuard Talent AI v2.4")
        md_content = format_nyc_ll144_markdown(report)
        
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            st.markdown(md_content)
        with col_r2:
            st.markdown("### Export & Publication")
            st.download_button(
                label="📥 Download Public Audit Notice (.md)",
                data=md_content,
                file_name=f"nyc_ll144_audit_{report.audit_date}.md",
                mime="text/markdown",
            )
            st.info(
                "💡 **Statutory Notice**: Mandated under NYC Admin Code § 20-871. "
                "Notice must remain publicly posted for at least 6 months following deployment."
            )
            
    # 2. EU AI Act Tab
    with sub_tab2:
        st.subheader("EU AI Act: Annex III High-Risk Employment Conformity Assessment")
        st.markdown(
            "Under **Regulation (EU) 2024/1689 (Annex III, Point 4)**, AI systems used for recruitment, applicant filtering, "
            "task allocation, and promotion monitoring are legally classified as **High-Risk AI Systems**."
        )
        
        tech_docs = st.checkbox("Technical Documentation & Architecture Specs Complete (Art. 11)", value=True)
        logging_active = st.checkbox("Automatic Continuous Event & Decision Logging Active (Art. 12)", value=True)
        human_oversight = st.checkbox("Mandatory Human-in-the-Loop Override Mechanisms Active (Art. 14)", value=True)
        
        assessment = evaluate_eu_ai_act_conformity(
            system_name="WorkforceGuard Algorithmic Evaluation Engine",
            audit_results=audits,
            technical_docs_present=tech_docs,
            logging_active=logging_active,
            human_in_the_loop_active=human_oversight,
        )
        
        col_e1, col_e2, col_e3 = st.columns(3)
        with col_e1:
            st.metric("Conformity Status", assessment.overall_conformity_status.split(" ")[0], assessment.overall_conformity_status)
        with col_e2:
            st.metric("Data Governance Score", f"{assessment.data_governance_score:.1f} / 100", "Art. 10 Compliance")
        with col_e3:
            st.metric("Risk Category", "Annex III (High-Risk)", "Item 4: Employment")
            
        st.markdown("---")
        st.markdown("### Mandatory Statutory Controls & Safeguards")
        st.markdown(f"- **Transparency Rating (Art. 13)**: {assessment.transparency_explainability_rating}")
        st.markdown(f"- **Cybersecurity & Robustness (Art. 15)**: {assessment.cybersecurity_robustness}")
        st.markdown("- **Human Oversight Controls (Art. 14)**:")
        for ctrl in assessment.human_oversight_controls:
            st.markdown(f"  - ✔️ {ctrl}")

    # 3. Policy Remediation Tab
    with sub_tab3:
        st.subheader("Algorithmic Policy Remediation: Threshold Calibration Engine")
        st.markdown(
            "Simulates alternative decision boundaries across the candidate distribution to find the optimal cutoff threshold "
            "that eliminates disparate impact and guarantees legal compliance (AIR ≥ 0.80)."
        )
        
        remediation = optimize_selection_threshold(df_candidates, score_col="AlgorithmicScore")
        
        st.success(f"🎯 **Recommended Operational Cutoff: {remediation['recommended_threshold']:.2f}**")
        st.markdown(f"**Regulatory Outcome**: {remediation['status']}")
        
        col_sim1, col_sim2 = st.columns([1, 1])
        with col_sim1:
            st.markdown("**Simulated Boundary Curve (Sample Cutoffs)**")
            df_sim_curve = pd.DataFrame(remediation["simulation_curve"])
            # Format impact ratios
            df_sim_curve["Gender AIR"] = df_sim_curve["impact_ratios"].apply(lambda x: x.get("Gender", 0))
            df_sim_curve["Ethnicity AIR"] = df_sim_curve["impact_ratios"].apply(lambda x: x.get("Ethnicity", 0))
            df_sim_display = df_sim_curve[["threshold", "total_selected", "overall_selection_rate", "Gender AIR", "Ethnicity AIR", "all_protected_groups_compliant"]]
            df_sim_display.columns = ["Cutoff", "Selected Count", "Selection Rate", "Gender AIR", "Ethnicity AIR", "All Groups ≥ 80%"]
            st.dataframe(df_sim_display, use_container_width=True, hide_index=True)
            
        with col_sim2:
            st.markdown("**Governance & Policy Directives**")
            for pol in remediation["policy_recommendations"]:
                st.warning(f"📌 {pol}")
