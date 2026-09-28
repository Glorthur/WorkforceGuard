"""
Phase 0 Data Quality & Relational Integrity Test Suite.
Validates 3NF schema constraints, primary/foreign key integrity, and numeric bounds.
"""
import unittest
import pandas as pd
from pathlib import Path

from src.data_pipeline.cleaner import clean_and_normalize_datasets
from src.data_pipeline.profiler import profile_datasets

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"

class TestDataQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = clean_and_normalize_datasets()
        cls.dim_sectors = cls.tables["dim_naics_sectors"]
        cls.fact_industries = cls.tables["fact_industry_exposure"]
        cls.dim_demos = cls.tables["dim_demographics"]
        cls.dim_cases = cls.tables["dim_ai_use_cases"]
        cls.fact_responses = cls.tables["fact_pew_survey_responses"]

    def test_primary_key_uniqueness(self):
        # 1. dim_naics_sectors: sector_code unique
        self.assertEqual(len(self.dim_sectors), self.dim_sectors["sector_code"].nunique(), "Duplicate sector_code found in dim_naics_sectors")
        # 2. fact_industry_exposure: naics_code unique
        self.assertEqual(len(self.fact_industries), self.fact_industries["naics_code"].nunique(), "Duplicate naics_code found in fact_industry_exposure")
        # 3. dim_demographics: demographic_id unique
        self.assertEqual(len(self.dim_demos), self.dim_demos["demographic_id"].nunique(), "Duplicate demographic_id found in dim_demographics")
        # 4. dim_ai_use_cases: use_case_id unique
        self.assertEqual(len(self.dim_cases), self.dim_cases["use_case_id"].nunique(), "Duplicate use_case_id found in dim_ai_use_cases")
        # 5. fact_pew_survey_responses: response_id unique
        self.assertEqual(len(self.fact_responses), self.fact_responses["response_id"].nunique(), "Duplicate response_id found in fact_pew_survey_responses")

    def test_referential_integrity(self):
        # Every industry's parent_sector_code must exist in dim_naics_sectors
        valid_sectors = set(self.dim_sectors["sector_code"])
        industry_sectors = set(self.fact_industries["parent_sector_code"])
        orphaned_sectors = industry_sectors - valid_sectors
        self.assertEqual(len(orphaned_sectors), 0, f"Orphaned sector codes in fact_industry_exposure: {orphaned_sectors}")

        # Every survey response's use_case_id must exist in dim_ai_use_cases
        valid_cases = set(self.dim_cases["use_case_id"])
        response_cases = set(self.fact_responses["use_case_id"])
        orphaned_cases = response_cases - valid_cases
        self.assertEqual(len(orphaned_cases), 0, f"Orphaned use_case_id in fact_pew_survey_responses: {orphaned_cases}")

        # Every survey response's demographic_id must exist in dim_demographics
        valid_demos = set(self.dim_demos["demographic_id"])
        response_demos = set(self.fact_responses["demographic_id"])
        orphaned_demos = response_demos - valid_demos
        self.assertEqual(len(orphaned_demos), 0, f"Orphaned demographic_id in fact_pew_survey_responses: {orphaned_demos}")

    def test_numeric_bounds(self):
        # Exposure score between 0.0 and 10.0
        min_exp = self.fact_industries["weighted_exposure"].min()
        max_exp = self.fact_industries["weighted_exposure"].max()
        self.assertTrue(0.0 <= min_exp <= 10.0, f"Invalid minimum exposure score: {min_exp}")
        self.assertTrue(0.0 <= max_exp <= 10.0, f"Invalid maximum exposure score: {max_exp}")

        # All survey percentages between 0.0 and 100.0
        for col in ["favor_pct", "oppose_pct", "not_sure_pct"]:
            col_min = self.fact_responses[col].min()
            col_max = self.fact_responses[col].max()
            self.assertTrue(0.0 <= col_min <= 100.0, f"Percentage underflow in {col}: {col_min}")
            self.assertTrue(0.0 <= col_max <= 100.0, f"Percentage overflow in {col}: {col_max}")

    def test_no_unhandled_nulls(self):
        self.assertEqual(self.dim_sectors.isnull().sum().sum(), 0)
        self.assertEqual(self.fact_industries.isnull().sum().sum(), 0)
        self.assertEqual(self.dim_demos.isnull().sum().sum(), 0)
        self.assertEqual(self.dim_cases.isnull().sum().sum(), 0)
        self.assertEqual(self.fact_responses.isnull().sum().sum(), 0)

    def test_profiling_report_generated(self):
        report = profile_datasets()
        self.assertIn("bls_industry_exposure", report)
        self.assertIn("pew_workplace_survey", report)
        self.assertTrue((PROCESSED_DIR / "data_profiling_report.md").exists())

if __name__ == "__main__":
    unittest.main()
