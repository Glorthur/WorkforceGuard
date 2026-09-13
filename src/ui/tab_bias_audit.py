"""
Streamlit Tab: Quantitative Algorithmic Bias Audit & EEOC 4/5ths Rule Station.
"""
import streamlit as st
import pandas as pd
from src.analytics.loader import load_candidate_data, load_eeoc_benchmarks
from src.governance.bias_audit import calculate_adverse_impact_ratio, benchmark_against_eeoc

def render_bias_audit_tab():
    st.markdown("## ⚖️ Quantitative Algorithmic Bias Audit & EEOC 4/5ths Station")
    st.markdown(
        "Evaluate Automated Employment Decision Tools (AEDT) for adverse impact under the "
        "**EEOC Uniform Guidelines on Employee Selection Procedures** (29 C.F.R. § 1607) and "
        "benchmark against real **federal EEOC EEO-1 private sector workforce data**."
    )
    
    df_candidates = load_candidate_data()
    df_eeoc = load_eeoc_benchmarks()
    
    # Threshold slider
    st.subheader("1. Interactive Decision Boundary Calibration")
    st.markdown("Adjust the algorithmic recommendation score cutoff threshold to observe live shifts in selection rates and adverse impact ratios.")
    
    cutoff = st.slider(
        "AI Selection Score Cutoff Threshold",
        min_value=0.40,
        max_value=0.85,
        value=0.65,
        step=0.01,
        help="Candidates with AlgorithmicScore >= Cutoff are selected."
    )
    
    df_sim = df_candidates.copy()
    df_sim["sim_selected"] = (df_sim["AlgorithmicScore"] >= cutoff).astype(int)
    
    # Audits
    gender_audit = calculate_adverse_impact_ratio(df_sim, "Gender", outcome_col="sim_selected")
    eth_audit = calculate_adverse_impact_ratio(df_sim, "Ethnicity", outcome_col="sim_selected")
    
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        badge = "🟢 Pass" if not gender_audit.overall_disparate_impact_found else "🔴 Adverse Impact Warning"
        st.metric("Gender Compliance (EEOC 4/5ths)", badge, f"Min AIR: {gender_audit.minimum_impact_ratio:.3f}")
    with col_status2:
        badge = "🟢 Pass" if not eth_audit.overall_disparate_impact_found else "🔴 Adverse Impact Warning"
        st.metric("Ethnicity Compliance (EEOC 4/5ths)", badge, f"Min AIR: {eth_audit.minimum_impact_ratio:.3f}")
        
    st.markdown("---")
    
    # Audit Breakdown Tables
    col_g, col_e = st.columns(2)
    with col_g:
        st.subheader("Gender Selection Rates & AIR")
        st.markdown(f"*Baseline Group*: **{gender_audit.baseline_group}** ({gender_audit.baseline_rate*100:.1f}%)")
        rows_g = []
        for g, m in gender_audit.group_metrics.items():
            rows_g.append({
                "Group": g,
                "Evaluated": m.total_count,
                "Selected": m.selected_count,
                "Selection Rate": f"{m.selection_rate*100:.1f}%",
                "Impact Ratio (AIR)": f"{m.impact_ratio:.3f}",
                "EEOC 4/5ths Rule": "✅ PASS" if m.passes_four_fifths_rule else "❌ FAIL (< 0.80)"
            })
        st.dataframe(pd.DataFrame(rows_g), use_container_width=True, hide_index=True)
        
    with col_e:
        st.subheader("Ethnicity Selection Rates & AIR")
        st.markdown(f"*Baseline Group*: **{eth_audit.baseline_group}** ({eth_audit.baseline_rate*100:.1f}%)")
        rows_e = []
        for eth, m in eth_audit.group_metrics.items():
            rows_e.append({
                "Group": eth,
                "Evaluated": m.total_count,
                "Selected": m.selected_count,
                "Selection Rate": f"{m.selection_rate*100:.1f}%",
                "Impact Ratio (AIR)": f"{m.impact_ratio:.3f}",
                "EEOC 4/5ths Rule": "✅ PASS" if m.passes_four_fifths_rule else "❌ FAIL (< 0.80)"
            })
        st.dataframe(pd.DataFrame(rows_e), use_container_width=True, hide_index=True)

    st.markdown("---")
    
    # Real Federal EEOC EEO-1 Comparison
    st.subheader("2. Federal EEOC EEO-1 National Workforce Benchmark Comparison")
    st.markdown(
        "Comparison of the candidate applicant pool against real national aggregate demographic shares "
        "from mandatory Title VII EEO-1 employer filings covering **56 million U.S. workers**."
    )
    
    role_choice = st.selectbox(
        "Select Federal EEO-1 Benchmark Job Classification:",
        list(df_eeoc["job_category"].unique()),
        index=2  # Default to Professionals
    )
    
    bench_data = benchmark_against_eeoc(df_candidates, df_eeoc, target_job_category=role_choice)
    if bench_data:
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(f"**Gender Share: Candidate Pool vs. Federal Benchmark ({role_choice})**")
            df_g_bench = pd.DataFrame([
                {"Group": "Female", "Candidate Pool (%)": bench_data["candidate_pool_representation"]["gender"].get("Female", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["female_pct"]},
                {"Group": "Male", "Candidate Pool (%)": bench_data["candidate_pool_representation"]["gender"].get("Male", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["male_pct"]},
            ])
            st.dataframe(df_g_bench, use_container_width=True, hide_index=True)
            
        with col_b2:
            st.markdown(f"**Ethnicity Share: Candidate Pool vs. Federal Benchmark ({role_choice})**")
            eth_cand = bench_data["candidate_pool_representation"]["ethnicity"]
            df_e_bench = pd.DataFrame([
                {"Ethnicity": "White", "Candidate Pool (%)": eth_cand.get("White", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["white_pct"]},
                {"Ethnicity": "Black or African American", "Candidate Pool (%)": eth_cand.get("Black", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["black_pct"]},
                {"Ethnicity": "Hispanic or Latino", "Candidate Pool (%)": eth_cand.get("Hispanic or Latino", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["hispanic_pct"]},
                {"Ethnicity": "Asian", "Candidate Pool (%)": eth_cand.get("Asian", 0), "Federal EEOC Benchmark (%)": bench_data["federal_eeoc_benchmark"]["asian_pct"]},
            ])
            st.dataframe(df_e_bench, use_container_width=True, hide_index=True)
