"""
Streamlit Tab 4: Statutory Algorithmic Audit Station & Compliance Generator.
Executes live evaluations under the EEOC 4/5ths Rule (Title VII),
NYC Local Law 144 (AEDT public audit reporting), and the EU AI Act (Regulation 2024/1689 Annex III).
"""
import streamlit as st
import pandas as pd
from src.database.connection import execute_query
from src.governance.bias_audit import calculate_adverse_impact_ratio
from src.governance.nyc_ll144 import generate_nyc_ll144_report, format_nyc_ll144_markdown
from src.governance.eu_ai_act import evaluate_eu_ai_act_conformity
from src.governance.policy_remediation import optimize_selection_threshold

def render_statutory_audit_tab():
    st.markdown("## ⚖️ Statutory Algorithmic Audit & Regulatory Station")
    st.markdown(
        """
        Independent auditing station evaluating Automated Employment Decision Tools (AEDT) 
        against statutory civil rights and algorithmic compliance mandates.
        """
    )

    # 1. Load Candidate Audit Log from Database
    df_candidates = execute_query("SELECT * FROM candidate_bias_audit_log")

    # Audit Control Panel
    st.subheader("1. Interactive Decision Threshold & EEOC 4/5ths Audit")
    
    c1, c2 = st.columns([1, 2])
    with c1:
        protected_attr = st.selectbox(
            "Protected Demographic Attribute",
            options=["gender", "ethnicity", "age_group"],
            format_func=lambda x: x.replace("_", " ").title()
        )
    with c2:
        threshold = st.slider(
            "AEDT Algorithmic Score Cutoff (Simulated Decision Threshold)",
            min_value=0.50,
            max_value=0.90,
            value=0.65,
            step=0.01,
            help="Simulate selecting candidates where algorithmic_score >= threshold."
        )

    # Calculate simulated outcome vs observed outcome
    sim_df = df_candidates.copy()
    sim_df["simulated_selected"] = (sim_df["algorithmic_score"] >= threshold).astype(int)

    # Run audit on both
    audit_observed = calculate_adverse_impact_ratio(sim_df, protected_attr, "selected_flag")
    audit_simulated = calculate_adverse_impact_ratio(sim_df, protected_attr, "simulated_selected")

    # KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Candidates Audited", f"{len(df_candidates):,}", "Active Applicant Pool")
    with k2:
        st.metric("Benchmark Group", f"{audit_simulated.baseline_group}", f"Rate: {audit_simulated.baseline_rate:.1%}")
    with k3:
        min_air = audit_simulated.minimum_impact_ratio
        delta_val = f"{min_air - 0.80:+.2f} vs 0.80 Rule"
        st.metric("Minimum Impact Ratio (AIR)", f"{min_air:.4f}", delta_val)
    with k4:
        status = audit_simulated.compliance_status
        if status == "COMPLIANT":
            st.success("✅ COMPLIANT (>= 0.80)")
        elif status == "ADVERSE_IMPACT_WARNING":
            st.warning("⚠️ WARNING (0.65 - 0.80)")
        else:
            st.error("🚨 VIOLATION (< 0.65)")

    # Detailed Group Breakdown Table
    st.markdown(f"**Disparate Impact Audit Table: {protected_attr.title()}** (Threshold = {threshold:.2f})")
    rows = []
    for grp_name, m in audit_simulated.group_metrics.items():
        pass_badge = "✅ PASS" if m.passes_four_fifths_rule else "❌ ADVERSE IMPACT"
        rows.append({
            "Demographic Group": grp_name,
            "Total Evaluated": m.total_count,
            "Selected Count": m.selected_count,
            "Selection Rate": f"{m.selection_rate:.1%}",
            "Impact Ratio (AIR)": f"{m.impact_ratio:.4f}",
            "EEOC 4/5ths Rule Status": pass_badge
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. NYC Local Law 144 AEDT Public Audit Package
    st.subheader("2. NYC Local Law 144: Mandatory Annual Public Audit Summary")
    st.markdown(
        """
        Under **NYC Administrative Code § 20-870**, employers utilizing AEDTs must publish an independent 
        bias audit summary calculating selection rates and impact ratios for Sex/Gender and Race/Ethnicity.
        """
    )
    
    ll144_report = generate_nyc_ll144_report(
        sim_df, 
        tool_name="WorkforceGuard Algorithmic Evaluation Engine v2.4",
        outcome_col="simulated_selected"
    )
    ll144_md = format_nyc_ll144_markdown(ll144_report)

    with st.expander("📄 Preview NYC Local Law 144 Public Audit Document"):
        st.markdown(ll144_md)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            label="📥 Download NYC LL144 Public Report (Markdown)",
            data=ll144_md,
            file_name="nyc_ll144_bias_audit_summary.md",
            mime="text/markdown"
        )
    with dl_col2:
        csv_rows = []
        for grp, m in ll144_report.gender_audit.group_metrics.items():
            csv_rows.append({"Category": "Gender", "Group": grp, "Total": m.total_count, "Selected": m.selected_count, "Rate": m.selection_rate, "AIR": m.impact_ratio})
        for grp, m in ll144_report.ethnicity_audit.group_metrics.items():
            csv_rows.append({"Category": "Ethnicity", "Group": grp, "Total": m.total_count, "Selected": m.selected_count, "Rate": m.selection_rate, "AIR": m.impact_ratio})
        csv_data = pd.DataFrame(csv_rows).to_csv(index=False)
        st.download_button(
            label="📥 Download NYC LL144 Statutory Table (CSV)",
            data=csv_data,
            file_name="nyc_ll144_audit_table.csv",
            mime="text/csv"
        )

    st.markdown("---")

    # 3. EU AI Act Annex III High-Risk Assessment
    st.subheader("3. EU AI Act (Regulation 2024/1689) Annex III High-Risk Conformity")
    st.markdown(
        "Mandatory 5-point conformity assessment for Employment & Worker Management AI systems:"
    )

    eu_assessment = evaluate_eu_ai_act_conformity(
        system_name="WorkforceGuard AEDT Selection Engine",
        audit_results={protected_attr: audit_simulated},
        technical_docs_present=True,
        logging_active=True,
        human_in_the_loop_active=True,
    )

    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("Statutory Risk Tier", "Annex III, Item 4", "High-Risk Employment AI")
    with e2:
        st.metric("Data Governance & Bias Score", f"{eu_assessment.data_governance_score:.1f} / 100")
    with e3:
        st.info(f"**Conformity Status**: {eu_assessment.overall_conformity_status}")

    with st.expander("🔍 View Annex III 5-Point Governance Evidence Checklist"):
        st.markdown("- **1. Risk Management (Art. 9)**: Lifecycle hazard identification and continuous risk register.")
        st.markdown("- **2. Data Governance (Art. 10)**: Training/validation dataset bias auditing and protected attribute testing.")
        st.markdown("- **3. Technical Documentation (Art. 11)**: System purpose, model cards, and operational logging (Art. 12).")
        st.markdown("- **4. Human Oversight (Art. 14)**: Override capabilities, stop mechanisms, and candidate appeal pathways.")
        st.markdown("- **5. Cybersecurity & Accuracy (Art. 15)**: ISO/IEC 27001 standard with cryptographic log integrity.")

    st.markdown("---")

    # 4. Deterministic Threshold Remediation Simulator
    st.subheader("4. Deterministic Policy Remediation Engine")
    st.markdown(
        "Simulates alternative score thresholds to identify decision cutoffs that maximize positive selections "
        "while guaranteeing all demographic groups maintain Adverse Impact Ratios $\\ge 0.80$:"
    )

    remediation = optimize_selection_threshold(sim_df, score_col="algorithmic_score")
    rec_thresh = remediation.get("recommended_threshold")
    curve_df = pd.DataFrame(remediation.get("simulation_curve", []))

    if rec_thresh is not None:
        st.success(f"🎯 **Recommended Statutorily Compliant Threshold**: `{rec_thresh:.3f}`")
        if not curve_df.empty:
            st.line_chart(curve_df.set_index("threshold")[["min_air", "selection_rate"]])
    else:
        st.warning(
            "⚠️ No single global score cutoff achieves full 4/5ths rule compliance across all demographic groups. "
            "Policy remediation recommendation: implement dual-band review or holistic human-in-the-loop assessments."
        )
