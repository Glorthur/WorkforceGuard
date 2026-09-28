"""
Unit tests for WorkforceGuard statutory AI governance mapping.
Checks the EU AI Act (Regulation EU 2024/1689) classification of each surveyed workplace use case.
"""
import unittest
from src.database.connection import execute_query

class TestGovernance(unittest.TestCase):
    def test_eu_ai_act_statutory_classification(self):
        df = execute_query("SELECT use_case_name, statutory_risk_tier FROM dim_ai_use_cases")
        tier = dict(zip(df["use_case_name"], df["statutory_risk_tier"]))
        self.assertEqual(len(tier), 5)

        # Recruitment and selection: Annex III, point 4(a)
        self.assertIn("point 4(a)", tier["AI Making Final Hiring Decisions"])
        self.assertIn("point 4(a)", tier["AI Reviewing Job Applications"])
        # Promotion and monitoring/evaluating workers: Annex III, point 4(b) (not Art. 50)
        self.assertIn("point 4(b)", tier["AI Deciding Promotions"])
        self.assertIn("point 4(b)", tier["AI Recording Workers' Computer Activity"])
        # Emotion inference at work is prohibited outright
        self.assertIn("Art. 5(1)(f)", tier["AI Analyzing Employees' Facial Expressions"])

        for t in tier.values():
            self.assertNotIn("Art. 50", t)

if __name__ == "__main__":
    unittest.main()
