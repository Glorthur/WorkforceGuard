"""
Candidate selection and promotion recommendation scoring engine.
Produces composite readiness ranks and categorized recommendations.
"""
from typing import Optional
import numpy as np
import pandas as pd

class PromotionRecommender:
    def __init__(self, weights: Optional[dict] = None):
        # Default balanced scoring weights
        self.weights = weights or {
            "interview": 0.40,
            "technical": 0.40,
            "experience": 0.20,
        }

    def score_candidates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes normalized composite scores and ranks candidates.
        """
        df_scored = df.copy()
        
        # Normalize experience to 0-100 scale (max cap at 15 years)
        norm_exp = (df_scored["YearsExperience"].clip(0, 15) / 15.0) * 100.0
        
        composite = (
            df_scored["InterviewScore"] * self.weights["interview"] +
            df_scored["TechnicalAssessmentScore"] * self.weights["technical"] +
            norm_exp * self.weights["experience"]
        )
        
        # Scale to 0.0 - 1.0
        df_scored["CompositeScore"] = (composite / 100.0).round(4)
        
        # Ranking (1 is highest score)
        df_scored["Rank"] = df_scored["CompositeScore"].rank(ascending=False, method="min").astype(int)
        
        # Percentile
        df_scored["Percentile"] = (df_scored["CompositeScore"].rank(pct=True) * 100.0).round(1)
        
        # Readiness Tier
        def assign_tier(score: float) -> str:
            if score >= 0.75:
                return "Ready Now"
            elif score >= 0.60:
                return "High Potential"
            else:
                return "Developing Pathway"
                
        df_scored["ReadinessTier"] = df_scored["CompositeScore"].apply(assign_tier)
        return df_scored

    def recommend_top_candidates(
        self, df: pd.DataFrame, top_k: Optional[int] = None, threshold: float = 0.65
    ) -> pd.DataFrame:
        """
        Filters and returns the top candidates meeting the promotion threshold.
        """
        scored = self.score_candidates(df)
        qualified = scored[scored["CompositeScore"] >= threshold].sort_values("CompositeScore", ascending=False)
        if top_k is not None:
            return qualified.head(top_k)
        return qualified
