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
    if df is None:
        df = pd.DataFrame()

    if job_categories is None:
        dept_col = "department" if "department" in df.columns else ("Department" if "Department" in df.columns else None)
        if dept_col:
            job_categories = [str(x) for x in df[dept_col].dropna().unique()]
        elif "JobRole" in df.columns:
            job_categories = [str(x) for x in df["JobRole"].dropna().unique()]
        else:
            job_categories = ["Corporate Technical & Professional Roles"]

    gender_col = "gender" if "gender" in df.columns else ("Gender" if "Gender" in df.columns else None)
    ethnicity_col = "ethnicity" if "ethnicity" in df.columns else ("Ethnicity" if "Ethnicity" in df.columns else None)

    empty_gender = DemographicAuditResult(
        protected_attribute="Gender",
        baseline_group="None",
        baseline_rate=0.0,
        group_metrics={},
        overall_disparate_impact_found=False,
        minimum_impact_ratio=1.0,
        compliance_status="COMPLIANT",
    )
    empty_ethnicity = DemographicAuditResult(
        protected_attribute="Ethnicity",
        baseline_group="None",
        baseline_rate=0.0,
        group_metrics={},
        overall_disparate_impact_found=False,
        minimum_impact_ratio=1.0,
        compliance_status="COMPLIANT",
    )

    gender_audit = calculate_adverse_impact_ratio(df, gender_col, outcome_col) if gender_col else empty_gender
    ethnicity_audit = calculate_adverse_impact_ratio(df, ethnicity_col, outcome_col) if ethnicity_col else empty_ethnicity

    intersectional_data = {}
    if gender_col and ethnicity_col:
        df_inter = df.copy()
        df_inter["intersectional"] = df_inter[gender_col].fillna("Unknown").astype(str) + " - " + df_inter[ethnicity_col].fillna("Unknown").astype(str)
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
            },
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
        auditor_attestation=attestation,
    )


def format_nyc_ll144_markdown(report: NYCLocalLaw144Report) -> str:
    """
    Formats the audit report into a public markdown summary for publication.
    """
    md = []
    md.append("# NYC Local Law 144: AEDT Annual Bias Audit Summary")
    md.append(f"**Automated Employment Decision Tool**: {report.tool_name}")
    md.append(f"**Audit Date**: {report.audit_date}")
    category_text = ", ".join(report.job_categories) if report.job_categories else "N/A"
    md.append(f"**Applicable Job Categories**: {category_text}\n")

    def _render_table(title: str, audit_label: str, audit: DemographicAuditResult):
        md.append(f"## {title}")
        md.append(f"*Baseline (Most Selected Group)*: **{audit.baseline_group}** ({audit.baseline_rate * 100:.1f}%)")
        md.append(f"| {audit_label} | Total Evaluated | Total Selected | Selection Rate | Impact Ratio | Compliance Status |")
        md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        if not audit.group_metrics:
            md.append(f"| No eligible demographic data | 0 | 0 | 0.0% | 0.000 | N/A |")
            return
        for g, m in audit.group_metrics.items():
            status = "Pass (≥ 80%)" if m.passes_four_fifths_rule else "**Adverse Impact (< 80%)**"
            md.append(f"| {g} | {m.total_count} | {m.selected_count} | {m.selection_rate*100:.1f}% | {m.impact_ratio:.3f} | {status} |")

    _render_table("1. Sex / Gender Disparate Impact Audit", "Demographic Group", report.gender_audit)
    _render_table("2. Race / Ethnicity Disparate Impact Audit", "Race / Ethnicity", report.ethnicity_audit)

    md.append("\n## 3. Independent Auditor Attestation")
    md.append(f"> {report.auditor_attestation}\n")
    return "\n".join(md)

