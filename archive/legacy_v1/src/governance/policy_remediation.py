"""
Algorithmic bias policy remediation and decision-threshold optimization engine.
Simulates alternative decision boundaries to satisfy EEOC 4/5ths and AEDT parity rules.
"""
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.governance.bias_audit import calculate_adverse_impact_ratio


def optimize_selection_threshold(
    df: pd.DataFrame,
    score_col: str = "AlgorithmicScore",
    protected_cols: Optional[List[str]] = None,
    min_air_target: float = 0.80
) -> Dict[str, Any]:
    """
    Simulates decision cutoffs between 0.40 and 0.85 to find the optimal threshold
    that maximizes selection quality while strictly maintaining legal AIR >= 0.80.
    """
    if df is None or len(df) == 0:
        return {
            "status": "No candidate data available for threshold optimization.",
            "recommended_threshold": None,
            "recommended_metrics": {"threshold": None, "total_selected": 0, "overall_selection_rate": 0.0, "impact_ratios": {}, "all_protected_groups_compliant": True},
            "simulation_curve": [],
            "policy_recommendations": [
                "Add candidate score data before running threshold optimization.",
                "Validate that protected-group attributes and outcome data are present.",
            ],
        }

    if score_col not in df.columns:
        raise ValueError(f"Score column '{score_col}' not found in DataFrame.")

    if protected_cols is None:
        protected_cols = [p for p in ["Gender", "Ethnicity"] if p in df.columns]
    valid_protected_cols = [p for p in protected_cols if p in df.columns]

    thresholds = np.linspace(0.40, 0.85, 25).round(3)
    simulation_results = []
    viable_thresholds = []

    for th in thresholds:
        df_sim = df.copy()
        df_sim["sim_selected"] = (df_sim[score_col] >= th).astype(int)

        col_airs = {}
        all_passed = True

        for p in valid_protected_cols:
            res = calculate_adverse_impact_ratio(df_sim, p, outcome_col="sim_selected")
            col_airs[p] = res.minimum_impact_ratio
            if res.minimum_impact_ratio < min_air_target:
                all_passed = False

        total_selected = int(df_sim["sim_selected"].sum())
        selection_rate = round(total_selected / len(df_sim), 4) if len(df_sim) > 0 else 0.0

        record = {
            "threshold": float(th),
            "total_selected": total_selected,
            "overall_selection_rate": selection_rate,
            "impact_ratios": col_airs,
            "all_protected_groups_compliant": all_passed,
        }
        simulation_results.append(record)

        if all_passed and total_selected > 0:
            viable_thresholds.append(record)

    if viable_thresholds:
        best_threshold = viable_thresholds[-1]
        rec_status = "Optimal Compliant Threshold Identified"
    elif simulation_results:
        best_threshold = max(simulation_results, key=lambda x: min(x["impact_ratios"].values()) if x["impact_ratios"] else 0.0)
        rec_status = "No Cutoff Achieves 100% Compliance; Feature Re-weighting Required"
    else:
        return {
            "status": "No viable thresholds evaluated.",
            "recommended_threshold": None,
            "recommended_metrics": {"threshold": None, "total_selected": 0, "overall_selection_rate": 0.0, "impact_ratios": {}, "all_protected_groups_compliant": True},
            "simulation_curve": [],
            "policy_recommendations": [
                "Ensure the score column and protected-group columns are present and populated.",
                "Review candidate data quality before running the optimization routine.",
            ],
        }

    recommendations = [
        f"Calibrate AI decision boundary to {best_threshold['threshold']:.2f} to maximize regulatory compliance.",
        "Implement human oversight interview stages for borderline candidates scoring within ±0.05 of the cutoff.",
        "Audit training data feature weights for historical demographic proxies.",
    ]

    return {
        "status": rec_status,
        "recommended_threshold": best_threshold["threshold"],
        "recommended_metrics": best_threshold,
        "simulation_curve": simulation_results,
        "policy_recommendations": recommendations,
    }
