"""
Quantitative algorithmic bias and disparate impact auditing engine for WorkforceGuard.
Implements EEOC 4/5ths Rule (Uniform Guidelines on Employee Selection Procedures)
and benchmarks against real federal EEO-1 aggregate statistics.
"""
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.core.schemas import DemographicAuditResult, GroupMetric

def calculate_adverse_impact_ratio(
    df: pd.DataFrame,
    protected_col: str,
    outcome_col: str = "Selected"
) -> DemographicAuditResult:
    """
    Computes Selection Rates, Adverse Impact Ratios (AIR), and EEOC 4/5ths rule pass/fail status
    for each subgroup of a protected attribute.
    """
    if len(df) == 0:
        return DemographicAuditResult(
            protected_attribute=protected_col,
            baseline_group="None",
            baseline_rate=0.0,
            group_metrics={},
            overall_disparate_impact_found=False,
            minimum_impact_ratio=1.0,
            compliance_status="COMPLIANT"
        )
        
    grouped = df.groupby(protected_col).agg(
        total=(outcome_col, "count"),
        selected=(outcome_col, lambda x: (x == 1).sum())
    )
    grouped["selection_rate"] = (grouped["selected"] / grouped["total"]).round(4)
    
    # Baseline group is the highest selection rate
    if len(grouped) == 0:
        baseline_group = "None"
        baseline_rate = 0.0
    else:
        baseline_group = str(grouped["selection_rate"].idxmax())
        baseline_rate = float(grouped.loc[baseline_group, "selection_rate"])
        
    group_metrics: Dict[str, GroupMetric] = {}
    impact_ratios = []
    has_disparate_impact = False
    
    for grp_name, row in grouped.iterrows():
        rate = float(row["selection_rate"])
        if baseline_rate > 0:
            air = round(rate / baseline_rate, 4)
        else:
            air = 1.0
            
        passes_rule = bool(air >= 0.80)
        if not passes_rule:
            has_disparate_impact = True
            
        impact_ratios.append(air)
        group_metrics[str(grp_name)] = GroupMetric(
            group_name=str(grp_name),
            total_count=int(row["total"]),
            selected_count=int(row["selected"]),
            selection_rate=rate,
            impact_ratio=air,
            passes_four_fifths_rule=passes_rule
        )
        
    min_air = float(min(impact_ratios)) if impact_ratios else 1.0
    
    # Compliance tier
    if min_air >= 0.80:
        compliance_status = "COMPLIANT"
    elif min_air >= 0.65:
        compliance_status = "ADVERSE_IMPACT_WARNING"
    else:
        compliance_status = "NON_COMPLIANT"
        
    return DemographicAuditResult(
        protected_attribute=protected_col,
        baseline_group=baseline_group,
        baseline_rate=baseline_rate,
        group_metrics=group_metrics,
        overall_disparate_impact_found=has_disparate_impact,
        minimum_impact_ratio=min_air,
        compliance_status=compliance_status
    )

def audit_all_protected_attributes(
    df: pd.DataFrame,
    protected_cols: Optional[List[str]] = None,
    outcome_col: str = "Selected"
) -> Dict[str, DemographicAuditResult]:
    """
    Runs adverse impact audits across all designated protected classes.
    """
    if protected_cols is None:
        protected_cols = [c for c in ["Gender", "Ethnicity", "AgeGroup"] if c in df.columns]
        
    results = {}
    for col in protected_cols:
        results[col] = calculate_adverse_impact_ratio(df, col, outcome_col)
    return results

def benchmark_against_eeoc(
    df_candidates: pd.DataFrame,
    df_eeoc_benchmarks: pd.DataFrame,
    target_job_category: str = "Professionals"
) -> Dict[str, Any]:
    """
    Compares the applicant/selection demographic distribution against real EEOC EEO-1
    national aggregate private sector workforce distributions.
    """
    eeoc_row = df_eeoc_benchmarks[df_eeoc_benchmarks["job_category"] == target_job_category]
    if len(eeoc_row) == 0:
        eeoc_row = df_eeoc_benchmarks.iloc[0:1]
    eeoc_bench = eeoc_row.iloc[0]
    
    total_candidates = len(df_candidates)
    if total_candidates == 0:
        return {}
        
    # Candidate distributions
    gender_dist = (df_candidates["Gender"].value_counts(normalize=True) * 100).round(1).to_dict()
    eth_dist = (df_candidates["Ethnicity"].value_counts(normalize=True) * 100).round(1).to_dict()
    
    # Selected candidate distributions
    selected_df = df_candidates[df_candidates["Selected"] == 1]
    sel_gender = (selected_df["Gender"].value_counts(normalize=True) * 100).round(1).to_dict() if len(selected_df) > 0 else {}
    sel_eth = (selected_df["Ethnicity"].value_counts(normalize=True) * 100).round(1).to_dict() if len(selected_df) > 0 else {}

    return {
        "benchmark_category": target_job_category,
        "federal_eeoc_benchmark": {
            "female_pct": float(eeoc_bench.get("female_pct", 50.0)),
            "male_pct": float(eeoc_bench.get("male_pct", 50.0)),
            "white_pct": float(eeoc_bench.get("white_pct", 65.0)),
            "black_pct": float(eeoc_bench.get("black_pct", 10.0)),
            "hispanic_pct": float(eeoc_bench.get("hispanic_pct", 12.0)),
            "asian_pct": float(eeoc_bench.get("asian_pct", 8.0)),
        },
        "candidate_pool_representation": {
            "gender": gender_dist,
            "ethnicity": eth_dist,
        },
        "selected_cohort_representation": {
            "gender": sel_gender,
            "ethnicity": sel_eth,
        }
    }
