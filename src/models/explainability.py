"""
Model explainability and proxy-variable detection engine.
Audits features for indirect discrimination and demographic proxy risks.
"""
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.models.attrition_predictor import AttritionPredictor, NUMERIC_FEATURES, CATEGORICAL_FEATURES

def get_feature_importances(predictor: AttritionPredictor) -> Dict[str, float]:
    """
    Extracts global feature importances from the trained RandomForestClassifier,
    aggregating one-hot encoded categories back into their root feature names.
    """
    if not predictor.is_fitted:
        raise ValueError("Predictor must be fitted before extracting importances.")
        
    model = predictor.pipeline.named_steps["classifier"]
    preprocessor = predictor.pipeline.named_steps["preprocessor"]
    
    # Get feature names from preprocessor
    cat_encoder = preprocessor.named_transformers_["cat"]
    cat_names = list(cat_encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    all_feature_names = NUMERIC_FEATURES + cat_names
    
    raw_importances = model.feature_importances_
    
    # Aggregate one-hot encoded columns back to parent feature
    aggregated: Dict[str, float] = {}
    for name, imp in zip(all_feature_names, raw_importances):
        # Determine parent feature
        parent = name
        for cat in CATEGORICAL_FEATURES:
            if name.startswith(f"{cat}_"):
                parent = cat
                break
        aggregated[parent] = aggregated.get(parent, 0.0) + float(imp)
        
    # Sort descending
    sorted_imp = {k: round(v, 4) for k, v in sorted(aggregated.items(), key=lambda x: x[1], reverse=True)}
    return sorted_imp

def detect_proxy_variables(
    df: pd.DataFrame,
    protected_cols: Optional[List[str]] = None,
    candidate_features: Optional[List[str]] = None,
    correlation_threshold: float = 0.20
) -> List[Dict[str, Any]]:
    """
    Audits feature correlations against protected demographic attributes
    to detect subtle proxy variables (e.g. DistanceFromHome acting as a proxy for Ethnicity/Neighborhood).
    Uses ANOVA Eta-Squared for categorical-numeric relationships and Cramér's V for categorical-categorical.
    """
    if protected_cols is None:
        protected_cols = [c for c in ["Gender", "Ethnicity", "AgeGroup"] if c in df.columns]
    
    if candidate_features is None:
        candidate_features = [
            c for c in [
                "MonthlyIncome", "DistanceFromHome", "YearsAtCompany",
                "YearsSinceLastPromotion", "OverTime", "JobSatisfaction",
                "WorkLifeBalance", "Education", "YearsExperience", "Department"
            ] if c in df.columns
        ]
        
    proxy_flags = []
    
    for prot in protected_cols:
        for feat in candidate_features:
            if prot == feat:
                continue
                
            association_score = 0.0
            test_type = ""
            
            # Numeric feature vs Categorical protected
            if pd.api.types.is_numeric_dtype(df[feat]):
                # One-way ANOVA
                groups = [group.dropna().values for _, group in df.groupby(prot)[feat]]
                groups = [g for g in groups if len(g) > 1]
                if len(groups) > 1:
                    f_val, p_val = stats.f_oneway(*groups)
                    # Compute Eta-Squared (n^2 = SS_between / SS_total)
                    all_vals = df[feat].dropna()
                    grand_mean = all_vals.mean()
                    ss_between = sum(len(g) * (g.mean() - grand_mean)**2 for g in groups)
                    ss_total = sum((all_vals - grand_mean)**2)
                    eta_sq = float(ss_between / ss_total) if ss_total > 0 else 0.0
                    association_score = round(np.sqrt(max(0.0, eta_sq)), 4)  # Correlation equivalent
                    test_type = "ANOVA Eta-Association"
            else:
                # Categorical vs Categorical: Cramér's V
                contingency = pd.crosstab(df[prot], df[feat])
                if contingency.size > 0:
                    chi2, p_val, _, _ = stats.chi2_contingency(contingency)
                    n = contingency.sum().sum()
                    r, k = contingency.shape
                    cramers_v = np.sqrt(chi2 / (n * (min(r, k) - 1))) if (n * (min(r, k) - 1)) > 0 else 0.0
                    association_score = round(float(cramers_v), 4)
                    test_type = "Cramér's V"
                    
            if association_score >= correlation_threshold:
                severity = "High Proxy Risk" if association_score >= 0.40 else "Moderate Proxy Concern"
                proxy_flags.append({
                    "protected_attribute": prot,
                    "candidate_feature": feat,
                    "association_score": association_score,
                    "method": test_type,
                    "severity": severity,
                    "recommendation": (
                        f"Variable '{feat}' demonstrates notable association ({association_score}) with protected class '{prot}'. "
                        "Evaluate model weights or omit feature to prevent indirect algorithmic disparity."
                    ),
                })
                
    # Sort highest association first
    proxy_flags.sort(key=lambda x: x["association_score"], reverse=True)
    return proxy_flags
