"""
NYC Local Law 144 (Automated Employment Decision Tools - AEDT) bias audit generator.
Produces mandatory public audit summary tables, scoring rates, and impact ratios.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from src.core.schemas import NYCLocalLaw144Report, DemographicAuditResult
from src.governance.bias_audit import calculate_adverse_impact_ratio

def generate_nyc_ll144_report(
    df: pd.DataFrame,
    tool_name: str = "WorkforceGuard AEDT Selection Engine v2.1",
    job_categories: Optional[List[str]] = None,
    outcome_col: str = "Selected"
) -> NYCLocalLaw144Report:
    """
    Generates an annual NYC Local Law 144 compliant bias audit report.
    """
    if job_categories is None:
        if "Department" in df.columns:
            job_categories = list(df["Department"].unique())
        else:
            job_categories = ["Corporate Technical & Professional Roles"]
            
    gender_audit = calculate_adverse_impact_ratio(df, "Gender", outcome_col)
    ethnicity_audit = calculate_adverse_impact_ratio(df, "Ethnicity", outcome_col)
    
    # Intersectional audit (Gender x Ethnicity)
    intersectional_data = {}
    if "Gender" in df.columns and "Ethnicity" in df.columns:
        df_inter = df.copy()
        df_inter["intersectional"] = df_inter["Gender"] + " - " + df_inter["Ethnicity"]
        inter_audit = calculate_adverse_impact_ratio(df_inter, "intersectional", outcome_col)
        intersectional_data = {
            "baseline_group": inter_audit.baseline_group,
            "baseline_rate": inter_audit.baseline_rate,
            "groups": {
                k: {
                    "total": v.total_count,
                    "selected": v.selected_count,
                    "selection_rate": v.selection_rate,
                    "impact_ratio": v.impact_ratio,
                    "passes_4_5ths": v.passes_four_fifths_rule,
                }
                for k, v in inter_audit.group_metrics.items()
            }
        }
        
    audit_date = datetime.now().strftime("%Y-%m-%d")
    attestation = (
        "I hereby attest that this independent bias audit was conducted in compliance with "
        "New York City Administrative Code Section 20-871 (Local Law 144 of 2021) and "
        "NYC Rules Title 6, Chapter 5, Subchapter T."
    )
    
    return NYCLocalLaw144Report(
        tool_name=tool_name,
        audit_date=audit_date,
        job_categories=job_categories,
        gender_audit=gender_audit,
        ethnicity_audit=ethnicity_audit,
        intersectional_audit=intersectional_data,
        auditor_attestation=attestation
    )

def format_nyc_ll144_markdown(report: NYCLocalLaw144Report) -> str:
    """
    Formats the audit report into a public markdown summary for publication.
    """
    md = []
    md.append(f"# NYC Local Law 144: AEDT Annual Bias Audit Summary")
    md.append(f"**Automated Employment Decision Tool**: {report.tool_name}")
    md.append(f"**Audit Date**: {report.audit_date}")
    md.append(f"**Applicable Job Categories**: {', '.join(report.job_categories)}\n")
    
    md.append("## 1. Sex / Gender Disparate Impact Audit")
    md.append(f"*Baseline (Most Selected Group)*: **{report.gender_audit.baseline_group}** ({report.gender_audit.baseline_rate*100:.1f}%)")
    md.append("| Demographic Group | Total Evaluated | Total Selected | Selection Rate | Impact Ratio | Compliance Status |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for g, m in report.gender_audit.group_metrics.items():
        status = "Pass (≥ 80%)" if m.passes_four_fifths_rule else "**Adverse Impact (< 80%)**"
        md.append(f"| {g} | {m.total_count} | {m.selected_count} | {m.selection_rate*100:.1f}% | {m.impact_ratio:.3f} | {status} |")
        
    md.append("\n## 2. Race / Ethnicity Disparate Impact Audit")
    md.append(f"*Baseline (Most Selected Group)*: **{report.ethnicity_audit.baseline_group}** ({report.ethnicity_audit.baseline_rate*100:.1f}%)")
    md.append("| Race / Ethnicity | Total Evaluated | Total Selected | Selection Rate | Impact Ratio | Compliance Status |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for eth, m in report.ethnicity_audit.group_metrics.items():
        status = "Pass (≥ 80%)" if m.passes_four_fifths_rule else "**Adverse Impact (< 80%)**"
        md.append(f"| {eth} | {m.total_count} | {m.selected_count} | {m.selection_rate*100:.1f}% | {m.impact_ratio:.3f} | {status} |")

    md.append("\n## 3. Independent Auditor Attestation")
    md.append(f"> {report.auditor_attestation}\n")
    return "\n".join(md)
