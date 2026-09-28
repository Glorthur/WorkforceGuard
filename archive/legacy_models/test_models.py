"""
Unit tests for WorkforceGuard predictive modeling and explainability.
"""
import unittest
import pandas as pd

from src.analytics.loader import load_attrition_data, load_candidate_data
from src.models.attrition_predictor import AttritionPredictor
from src.models.promotion_recommender import PromotionRecommender
from src.models.explainability import get_feature_importances, detect_proxy_variables
from src.core.schemas import FlightRiskPrediction

class TestModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.attrition_df = load_attrition_data()
        cls.candidate_df = load_candidate_data()
        cls.predictor = AttritionPredictor().fit(cls.attrition_df)

    def test_attrition_predictor_fit_and_predict(self):
        self.assertTrue(self.predictor.is_fitted)
        self.assertIn("roc_auc", self.predictor.evaluation_metrics)
        self.assertGreater(self.predictor.evaluation_metrics["roc_auc"], 0.60)
        
        sample = self.attrition_df.head(5)
        predictions = self.predictor.predict_flight_risk(sample)
        self.assertEqual(len(predictions), 5)
        self.assertIsInstance(predictions[0], FlightRiskPrediction)
        self.assertIn(predictions[0].risk_level, ["Low", "Medium", "High"])
        self.assertTrue(len(predictions[0].retention_recommendations) > 0)

    def test_promotion_recommender(self):
        recommender = PromotionRecommender()
        scored = recommender.score_candidates(self.candidate_df)
        self.assertIn("CompositeScore", scored.columns)
        self.assertIn("Rank", scored.columns)
        self.assertIn("ReadinessTier", scored.columns)
        self.assertEqual(int(scored["Rank"].min()), 1)
        
        top_10 = recommender.recommend_top_candidates(self.candidate_df, top_k=10)
        self.assertEqual(len(top_10), 10)
        self.assertTrue(top_10.iloc[0]["CompositeScore"] >= top_10.iloc[-1]["CompositeScore"])

    def test_explainability_feature_importances(self):
        importances = get_feature_importances(self.predictor)
        self.assertIsInstance(importances, dict)
        self.assertIn("MonthlyIncome", importances)
        # Sum of importances should be approximately 1.0
        self.assertAlmostEqual(sum(importances.values()), 1.0, places=1)

    def test_detect_proxy_variables(self):
        proxies = detect_proxy_variables(self.candidate_df, correlation_threshold=0.10)
        self.assertIsInstance(proxies, list)
        if proxies:
            self.assertIn("association_score", proxies[0])
            self.assertIn("severity", proxies[0])

if __name__ == "__main__":
    unittest.main()
