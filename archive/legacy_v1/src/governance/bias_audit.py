"""
Quantitative algorithmic bias and disparate impact auditing engine for WorkforceGuard.
Implements EEOC 4/5ths Rule (Uniform Guidelines on Employee Selection Procedures)
and benchmarks against real federal EEO-1 aggregate statistics.
"""
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.core.schemas import DemographicAuditResult, GroupMetric


def _empty_audit_result(protected_col: str) -> DemographicAuditResult:
    return DemographicAuditResult(
        protected_attribute=protected_col,
        baseline_group="None",
        baseline_rate=0.0,
        group_metrics={},
        overall_disparate_impact_found=False,
        minimum_impact_ratio=1.0,
        compliance_status="COMPLIANT",
    )


def _normalize_outcome(series: pd.Series) -> pd.Series:
    if series.empty:
        return pd.Series([], dtype=int)

    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)

    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().all():
            return numeric.clip(0, 1).round().astype(int)

    cleaned = series.astype(str).str.strip().str.lower()
    mapping = {
        "1": 1,
        "true": 1,
        "yes": 1,
        "y": 1,
        "selected": 1,
        "accepted": 1,
        "hire": 1,
        "0": 0,
        "false": 0,
        "no": 0,
        "n": 0,
        "not selected": 0,
        "rejected": 0,
    }
    normalized = cleaned.map(mapping)
    return normalized.fillna(0).astype(int)


def calculate_adverse_impact_ratio(
    df: pd.DataFrame,
    protected_col: str,
    outcome_col: str = "selected_flag"
) -> DemographicAuditResult:
    """
    Computes Selection Rates, Adverse Impact Ratios (AIR), and EEOC 4/5ths rule pass/fail status
    for each subgroup of a protected attribute.
    """
    if df is None or len(df) == 0:
        return _empty_audit_result(protected_col)

    if protected_col not in df.columns:
        return _empty_audit_result(protected_col)

    if outcome_col not in df.columns:
        for candidate in ["selected_flag", "Selected", "selected"]:
            if candidate in df.columns:
                outcome_col = candidate
                break

    outcome_series = df[outcome_col] if outcome_col in df.columns else pd.Series(0, index=df.index)
    analysis_df = df[[protected_col]].copy()
    analysis_df["__outcome__"] = _normalize_outcome(outcome_series)
    analysis_df = analysis_df.dropna(subset=[protected_col, "__outcome__"])

    if analysis_df.empty:
        return _empty_audit_result(protected_col)

    grouped = analysis_df.groupby(protected_col, dropna=False).agg(
        total=("__outcome__", "count"),
        selected=("__outcome__", "sum")
    )
    grouped["selection_rate_exact"] = grouped["selected"] / grouped["total"].replace(0, np.nan)
    grouped["selection_rate"] = grouped["selection_rate_exact"].round(4)

    if len(grouped) == 0:
        baseline_group = "None"
        baseline_rate_exact = 0.0
        baseline_rate = 0.0
    else:
        baseline_group = str(grouped["selection_rate_exact"].idxmax())
        baseline_rate_exact = float(grouped.loc[baseline_group, "selection_rate_exact"])
        baseline_rate = float(grouped.loc[baseline_group, "selection_rate"])

    group_metrics: Dict[str, GroupMetric] = {}
    impact_ratios = []
    has_disparate_impact = False

    for grp_name, row in grouped.iterrows():
        rate = float(row["selection_rate"])
        rate_exact = float(row["selection_rate_exact"])
        if baseline_rate_exact > 0:
            air = round(rate_exact / baseline_rate_exact, 4)
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
            passes_four_fifths_rule=passes_rule,
        )

    min_air = float(min(impact_ratios)) if impact_ratios else 1.0

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
        compliance_status=compliance_status,
    )


def audit_all_protected_attributes(
    df: pd.DataFrame,
    protected_cols: Optional[List[str]] = None,
    outcome_col: str = "Selected"
) -> Dict[str, DemographicAuditResult]:
    """
    Runs adverse impact audits across all designated protected classes.
    """
    if df is None:
        return {}

    if protected_cols is None:
        protected_cols = [c for c in ["Gender", "Ethnicity", "AgeGroup"] if c in df.columns]

    results = {}
    for col in protected_cols:
        if col in df.columns:
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
    if df_eeoc_benchmarks is None or len(df_eeoc_benchmarks) == 0:
        eeoc_bench = {}
    else:
        eeoc_row = df_eeoc_benchmarks[df_eeoc_benchmarks["job_category"] == target_job_category]
        if len(eeoc_row) == 0:
            eeoc_row = df_eeoc_benchmarks.iloc[0:1]
        eeoc_bench = eeoc_row.iloc[0]

    total_candidates = len(df_candidates) if df_candidates is not None else 0
    if total_candidates == 0:
        return {
            "benchmark_category": target_job_category,
            "federal_eeoc_benchmark": {
                "female_pct": float(eeoc_bench.get("female_pct", 50.0)) if isinstance(eeoc_bench, dict) else 50.0,
                "male_pct": float(eeoc_bench.get("male_pct", 50.0)) if isinstance(eeoc_bench, dict) else 50.0,
                "white_pct": float(eeoc_bench.get("white_pct", 65.0)) if isinstance(eeoc_bench, dict) else 65.0,
                "black_pct": float(eeoc_bench.get("black_pct", 10.0)) if isinstance(eeoc_bench, dict) else 10.0,
                "hispanic_pct": float(eeoc_bench.get("hispanic_pct", 12.0)) if isinstance(eeoc_bench, dict) else 12.0,
                "asian_pct": float(eeoc_bench.get("asian_pct", 8.0)) if isinstance(eeoc_bench, dict) else 8.0,
            },
            "candidate_pool_representation": {"gender": {}, "ethnicity": {}},
            "selected_cohort_representation": {"gender": {}, "ethnicity": {}},
        }

    gender_dist = (df_candidates["Gender"].value_counts(normalize=True) * 100).round(1).to_dict() if "Gender" in df_candidates.columns else {}
    eth_dist = (df_candidates["Ethnicity"].value_counts(normalize=True) * 100).round(1).to_dict() if "Ethnicity" in df_candidates.columns else {}

    selected_df = df_candidates[df_candidates["Selected"] == 1] if "Selected" in df_candidates.columns else df_candidates.iloc[0:0]
    sel_gender = (selected_df["Gender"].value_counts(normalize=True) * 100).round(1).to_dict() if "Gender" in selected_df.columns and len(selected_df) > 0 else {}
    sel_eth = (selected_df["Ethnicity"].value_counts(normalize=True) * 100).round(1).to_dict() if "Ethnicity" in selected_df.columns and len(selected_df) > 0 else {}

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
        },
    }
