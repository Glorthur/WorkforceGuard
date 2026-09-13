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
    if protected_cols is None:
        protected_cols = ["Gender", "Ethnicity"]
        
    thresholds = np.linspace(0.40, 0.85, 25).round(3)
    simulation_results = []
    viable_thresholds = []
    
    for th in thresholds:
        df_sim = df.copy()
        df_sim["sim_selected"] = (df_sim[score_col] >= th).astype(int)
        
        # Check impact ratios across all protected cols
        col_airs = {}
        all_passed = True
        
        for p in protected_cols:
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
            
    # Find recommended threshold
    if viable_thresholds:
        # Pick the highest threshold that is compliant (selects highest quality while compliant)
        best_threshold = viable_thresholds[-1]
        rec_status = "Optimal Compliant Threshold Identified"
    else:
        # Fallback to the one with the highest minimum AIR
        best_threshold = max(simulation_results, key=lambda x: min(x["impact_ratios"].values()) if x["impact_ratios"] else 0.0)
        rec_status = "No Cutoff Achieves 100% Compliance; Feature Re-weighting Required"

    recommendations = [
        f"Calibrate AI decision boundary to {best_threshold['threshold']:.2f} to maximize regulatory compliance.",
        "Implement human oversight interview stages for borderline candidates scoring within ±0.05 of the cutoff.",
        "Audit training data feature weights for historical demographic proxies."
    ]

    return {
        "status": rec_status,
        "recommended_threshold": best_threshold["threshold"],
        "recommended_metrics": best_threshold,
        "simulation_curve": simulation_results,
        "policy_recommendations": recommendations,
    }
