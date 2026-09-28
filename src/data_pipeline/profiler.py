"""
Data Profiling & Diagnostic Engine for WorkforceGuard.
Conducts statistical and structural audits on raw datasets before cleaning and ingestion.
"""
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

def profile_bls_industry_exposure(df: pd.DataFrame) -> Dict[str, Any]:
    """Profiles the BLS industry employment and AI exposure dataset."""
    total_rows = len(df)
    null_counts = df.isnull().sum().to_dict()
    
    # Hierarchy check
    is_sector_counts = df["is_sector"].value_counts().to_dict() if "is_sector" in df.columns else {}
    unique_naics = int(df["naics_code"].nunique())
    
    # Statistical bounds on exposure
    exposure_stats = {
        "min": float(df["weighted_exposure"].min()),
        "max": float(df["weighted_exposure"].max()),
        "mean": float(round(df["weighted_exposure"].mean(), 3)),
        "median": float(round(df["weighted_exposure"].median(), 3)),
        "std": float(round(df["weighted_exposure"].std(), 3)),
        "within_valid_bounds_0_to_10": bool(
            (df["weighted_exposure"] >= 0.0).all() and (df["weighted_exposure"] <= 10.0).all()
        ),
    }
    
    # Employment statistics
    emp_stats = {
        "total_workforce": int(df["covered_employment_2024"].sum()),
        "min_emp": int(df["covered_employment_2024"].min()),
        "max_emp": int(df["covered_employment_2024"].max()),
        "mean_emp": int(df["covered_employment_2024"].mean()),
        "zero_or_negative_emp_count": int((df["covered_employment_2024"] <= 0).sum()),
    }
    
    return {
        "dataset_name": "BLS Industry AI Occupational Exposure",
        "total_rows": total_rows,
        "unique_naics_codes": unique_naics,
        "is_primary_key_unique": bool(unique_naics == total_rows),
        "null_counts": null_counts,
        "hierarchy_distribution": is_sector_counts,
        "exposure_score_stats": exposure_stats,
        "covered_employment_stats": emp_stats,
    }

def profile_pew_survey(df: pd.DataFrame) -> Dict[str, Any]:
    """Profiles the real Pew Research Center ATP Wave 119 survey dataset."""
    total_rows = len(df)
    null_counts = df.isnull().sum().to_dict()
    unique_categories = list(df["category"].unique())
    unique_demographics = list(df["demographic_group"].unique())
    
    # Range checks: verify all percentages lie in [0, 100]
    pct_cols = [c for c in df.columns if c.endswith("_pct")]
    out_of_bounds = {}
    for c in pct_cols:
        invalid = int(((df[c] < 0.0) | (df[c] > 100.0)).sum())
        out_of_bounds[c] = invalid
        
    return {
        "dataset_name": "Pew Research Center ATP Wave 119 workplace AI items (weighted from microdata)",
        "total_rows": total_rows,
        "null_counts": null_counts,
        "distinct_use_cases_count": len(unique_categories),
        "distinct_use_cases": unique_categories,
        "distinct_demographic_groups_count": len(unique_demographics),
        "distinct_demographic_groups": unique_demographics,
        "percentage_columns_out_of_bounds_count": out_of_bounds,
    }

def profile_candidate_pool(df: pd.DataFrame) -> Dict[str, Any]:
    """Profiles the candidate selection audit dataset."""
    total_rows = len(df)
    null_counts = df.isnull().sum().to_dict()
    unique_candidates = int(df["CandidateID"].nunique())
    
    gender_counts = df["Gender"].value_counts().to_dict()
    ethnicity_counts = df["Ethnicity"].value_counts().to_dict()
    selection_rate = float(round(df["Selected"].mean(), 4))
    
    score_stats = {
        "min": float(df["AlgorithmicScore"].min()),
        "max": float(df["AlgorithmicScore"].max()),
        "mean": float(round(df["AlgorithmicScore"].mean(), 3)),
    }
    
    return {
        "dataset_name": "Candidate Selection Audit Dataset",
        "total_rows": total_rows,
        "unique_candidates": unique_candidates,
        "is_primary_key_unique": bool(unique_candidates == total_rows),
        "null_counts": null_counts,
        "overall_selection_rate": selection_rate,
        "gender_distribution": gender_counts,
        "ethnicity_distribution": ethnicity_counts,
        "score_distribution": score_stats,
    }

def profile_datasets() -> Dict[str, Any]:
    """Runs full profiling suite on all raw datasets and outputs report."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    df_bls = pd.read_csv(RAW_DIR / "real_bls_industry_ai_exposure.csv")
    df_pew = pd.read_csv(RAW_DIR / "pew_w119_workplace_ai.csv")
    df_cand = pd.read_csv(RAW_DIR / "hiring_promotion_candidates.csv")
    
    report = {
        "bls_industry_exposure": profile_bls_industry_exposure(df_bls),
        "pew_workplace_survey": profile_pew_survey(df_pew),
        "candidate_selection_pool": profile_candidate_pool(df_cand),
    }
    
    # Format markdown report
    md = [
        "# Data Profiling & Diagnostic Quality Report",
        "Generated as part of Phase 0 Data Understanding & Profiling.\n",
        "## 1. BLS Industry AI Occupational Exposure Dataset",
        f"- **Total Records**: {report['bls_industry_exposure']['total_rows']}",
        f"- **NAICS Code Uniqueness (Primary Key)**: {'✅ Unique' if report['bls_industry_exposure']['is_primary_key_unique'] else '❌ Duplicates Found'}",
        f"- **Null Counts**: {report['bls_industry_exposure']['null_counts']}",
        f"- **Exposure Score Range**: [{report['bls_industry_exposure']['exposure_score_stats']['min']}, {report['bls_industry_exposure']['exposure_score_stats']['max']}] (Valid Bounds: {report['bls_industry_exposure']['exposure_score_stats']['within_valid_bounds_0_to_10']})",
        f"- **Hierarchy**: {report['bls_industry_exposure']['hierarchy_distribution']} (Warning: Must separate parent sectors from detailed sub-industries to prevent double counting).\n",
        "## 2. Pew Research Center Workplace AI Survey",
        f"- **Total Records**: {report['pew_workplace_survey']['total_rows']}",
        f"- **Evaluated AI Use Cases**: {report['pew_workplace_survey']['distinct_use_cases_count']}",
        f"- **Evaluated Demographic Cohorts**: {report['pew_workplace_survey']['distinct_demographic_groups_count']}",
        f"- **Percentage Out-of-Bounds (0-100%)**: {report['pew_workplace_survey']['percentage_columns_out_of_bounds_count']}\n",
        "## 3. Candidate Selection Audit Dataset",
        f"- **Total Candidates**: {report['candidate_selection_pool']['total_rows']}",
        f"- **Overall Selection Rate**: {report['candidate_selection_pool']['overall_selection_rate'] * 100:.1f}%",
        f"- **Candidate ID Uniqueness**: {'✅ Unique' if report['candidate_selection_pool']['is_primary_key_unique'] else '❌ Duplicates'}",
    ]
    
    (PROCESSED_DIR / "data_profiling_report.md").write_text("\n".join(md), encoding="utf-8")
    return report

if __name__ == "__main__":
    rep = profile_datasets()
    print("Profiling complete. Report saved to data/processed/data_profiling_report.md")
