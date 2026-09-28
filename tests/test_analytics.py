"""
Phase 2 Educational SQL Analytics Test Suite (Two-Dataset Edition).
Validates live SQL query execution on normalized BLS and Pew survey tables.
"""
import unittest
from pathlib import Path
import pandas as pd
from src.database.connection import execute_query

RAW_BLS = Path(__file__).resolve().parents[1] / "data" / "raw" / "real_bls_industry_ai_exposure.csv"
from src.database.queries import (
    get_macro_exposure_summary,
    get_pew_hiring_vs_humans,
    get_use_cases_overall,
    get_statutory_risk_summary,
)

class TestAnalytics(unittest.TestCase):
    def test_macro_exposure_query(self):
        """Validates Query 1 execution and double-counting prevention."""
        df = get_macro_exposure_summary()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("sector_code", df.columns)
        self.assertIn("detailed_employment", df.columns)
        self.assertIn("employment_weighted_exposure", df.columns)

        # No double counting: each sector's total must not exceed the sector-level
        # employment BLS itself reports in the raw file (where it reports one).
        raw = pd.read_csv(RAW_BLS, dtype={"naics_code": str})
        raw_sector = {
            code[:2]: emp for code, emp, is_sec in
            zip(raw["naics_code"], raw["covered_employment_2024"], raw["is_sector"]) if is_sec
        }
        checked = 0
        for code, emp in zip(df["sector_code"], df["detailed_employment"]):
            if code in raw_sector:
                # 7% slack: BLS's own agriculture children sum 6% above its sector row;
                # a real double count roughly doubles a sector.
                self.assertLessEqual(emp, raw_sector[code] * 1.07, f"sector {code} double-counts employment")
                checked += 1
        self.assertGreater(checked, 10)

        # Summing every row (all NAICS levels) must be larger than the de-duplicated total
        all_rows_emp = execute_query("SELECT SUM(covered_employment) FROM fact_industry_exposure").iloc[0, 0]
        self.assertGreater(all_rows_emp, df["detailed_employment"].sum())

        # Verify no exposure score exceeds 10.0 or is below 0.0
        self.assertTrue((df["employment_weighted_exposure"] >= 0.0).all())
        self.assertTrue((df["employment_weighted_exposure"] <= 10.0).all())

    def test_pew_hiring_vs_humans_query(self):
        """Query 2: one row per cohort, net skepticism = worse - better, and Pew's published topline."""
        df = get_pew_hiring_vs_humans()
        self.assertEqual(len(df), 11)
        self.assertIn("skepticism_rank", df.columns)
        diff = (df["net_skepticism_pp"] - (df["ai_worse_pct"] - df["ai_better_pct"])).abs().max()
        self.assertLess(diff, 0.051)

        # Pew, "AI in Hiring and Evaluating Workers" (Apr 2023): 47% better, 15% worse
        overall = df[df["dimension_type"] == "Overall"].iloc[0]
        self.assertEqual(round(overall["ai_better_pct"]), 47)
        self.assertEqual(round(overall["ai_worse_pct"]), 15)

    def test_use_cases_match_published_pew_topline(self):
        """Weighted microdata estimates must reproduce Pew's published favor/oppose figures."""
        df = get_use_cases_overall().set_index("pew_item")
        published = {  # item: (favor, oppose), Pew Research Center, April 20, 2023
            "AIWRKH2_a": (28, 41),   # reviewing job applications
            "AIWRKH2_b": (7, 71),    # making a final hiring decision
            "FACERECWK2_b": (9, 70), # analyzing employees' facial expressions
            "AIWRKM4_a": (22, 47),   # deciding promotions
        }
        for item, (favor, oppose) in published.items():
            # stored to 0.1, Pew rounds the unrounded value to 1: allow half a point
            self.assertLessEqual(abs(df.at[item, "favor_pct"] - favor), 0.55, item)
            self.assertLessEqual(abs(df.at[item, "oppose_pct"] - oppose), 0.55, item)

    def test_statutory_risk_summary_query(self):
        """Validates Query 4 execution grouping by EU AI Act statutory risk tiers."""
        df = get_statutory_risk_summary()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("statutory_risk_tier", df.columns)
        self.assertIn("avg_net_opposition_pp", df.columns)
        self.assertIn("avg_favor_pct", df.columns)

if __name__ == "__main__":
    unittest.main()
