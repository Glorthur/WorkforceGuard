"""
Unit tests for WorkforceGuard analytics module with real datasets.
"""
import unittest
import pandas as pd

from src.analytics.loader import (
    load_industry_exposure_data,
    load_occupations_exposure_data,
    load_pew_survey_data,
    load_stanford_governance_data,
    load_eeoc_benchmarks,
    load_candidate_data,
)
from src.analytics.metrics import (
    analyze_ai_industry_exposure,
    analyze_pew_ai_sentiment,
    analyze_stanford_governance_gap,
)

class TestRealAnalytics(unittest.TestCase):
    def test_load_industry_exposure_data(self):
        df = load_industry_exposure_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 355)
        self.assertIn("weighted_exposure", df.columns)
        self.assertIn("exposure_tier", df.columns)
        
        # Test metric calculation
        metrics = analyze_ai_industry_exposure(df)
        self.assertEqual(metrics["total_industries_analyzed"], 355)
        self.assertGreater(metrics["average_exposure_score"], 0)
        self.assertIn("top_exposed_industries", metrics)
        self.assertEqual(len(metrics["top_exposed_industries"]), 10)

    def test_load_occupations_exposure_data(self):
        df = load_occupations_exposure_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 342)
        self.assertIn("median_pay_annual", df.columns)

    def test_load_pew_survey_data(self):
        df = load_pew_survey_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        sentiment = analyze_pew_ai_sentiment(df)
        self.assertIn("demographic_fairness_views", sentiment)
        self.assertIn("use_case_acceptability", sentiment)

    def test_load_stanford_governance_data(self):
        df = load_stanford_governance_data()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("governance_gap_pct", df.columns)
        gov = analyze_stanford_governance_gap(df)
        self.assertGreater(gov["average_governance_gap"], 0)

    def test_load_eeoc_benchmarks(self):
        df = load_eeoc_benchmarks()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 10)
        self.assertIn("female_pct", df.columns)

if __name__ == "__main__":
    unittest.main()
