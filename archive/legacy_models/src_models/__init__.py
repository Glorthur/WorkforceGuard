"""
Predictive AI and Explainability Module for WorkforceGuard.
"""
from src.models.attrition_predictor import AttritionPredictor
from src.models.promotion_recommender import PromotionRecommender
from src.models.explainability import get_feature_importances, detect_proxy_variables

__all__ = [
    "AttritionPredictor",
    "PromotionRecommender",
    "get_feature_importances",
    "detect_proxy_variables",
]
