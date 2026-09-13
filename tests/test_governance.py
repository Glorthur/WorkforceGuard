"""
Unit tests for WorkforceGuard governance and algorithmic auditing module.
"""
import unittest
import pandas as pd

from src.analytics.loader import load_candidate_data, load_eeoc_benchmarks
from src.governance.bias_audit import (
    calculate_adverse_impact_ratio,
    audit_all_protected_attributes,
    benchmark_against_eeoc,
)
from src.governance.nyc_ll144 import (
    generate_nyc_ll144_report,
    format_nyc_ll144_markdown,
)
from src.governance.eu_ai_act import evaluate_eu_ai_act_conformity
from src.governance.policy_remediation import optimize_selection_threshold

class TestGovernance(unittest.TestCase):
    def test_exact_adverse_impact_math(self):
        # Deterministic validation dataset
        data = {
            "Group": ["A"] * 100 + ["B"] * 100 + ["C"] * 100,
            "Selected": [1] * 50 + [0] * 50 + [1] * 30 + [0] * 70 + [1] * 45 + [0] * 55,
        }
        df = pd.DataFrame(data)
        result = calculate_adverse_impact_ratio(df, "Group", "Selected")
        
        # Baseline group should be A with 0.50 selection rate
        self.assertEqual(result.baseline_group, "A")
        self.assertEqual(result.baseline_rate, 0.50)
        
        # Group B: rate=0.30, AIR = 0.30 / 0.50 = 0.60 (Fails 4/5ths)
        self.assertAlmostEqual(result.group_metrics["B"].impact_ratio, 0.60, places=2)
        self.assertFalse(result.group_metrics["B"].passes_four_fifths_rule)
        
        # Group C: rate=0.45, AIR = 0.45 / 0.50 = 0.90 (Passes 4/5ths)
        self.assertAlmostEqual(result.group_metrics["C"].impact_ratio, 0.90, places=2)
        self.assertTrue(result.group_metrics["C"].passes_four_fifths_rule)
        
        # Overall status should flag adverse impact (0.60 < 0.65 -> NON_COMPLIANT)
        self.assertTrue(result.overall_disparate_impact_found)
        self.assertEqual(result.compliance_status, "NON_COMPLIANT")

    def test_audit_candidate_data(self):
        df = load_candidate_data()
        audits = audit_all_protected_attributes(df)
        self.assertIn("Gender", audits)
        self.assertIn("Ethnicity", audits)
        self.assertTrue(0.0 <= audits["Gender"].minimum_impact_ratio <= 1.0)

    def test_benchmark_against_eeoc(self):
        df_candidates = load_candidate_data()
        df_eeoc = load_eeoc_benchmarks()
        comparison = benchmark_against_eeoc(df_candidates, df_eeoc, "Professionals")
        self.assertIn("federal_eeoc_benchmark", comparison)
        self.assertIn("female_pct", comparison["federal_eeoc_benchmark"])
        self.assertIn("candidate_pool_representation", comparison)

    def test_nyc_ll144_report(self):
        df = load_candidate_data()
        report = generate_nyc_ll144_report(df, tool_name="WorkforceGuard AEDT Test")
        self.assertEqual(report.tool_name, "WorkforceGuard AEDT Test")
        self.assertIn("Local Law 144", report.auditor_attestation)
        
        md = format_nyc_ll144_markdown(report)
        self.assertIn("# NYC Local Law 144", md)
        self.assertIn("Impact Ratio", md)

    def test_eu_ai_act_conformity(self):
        df = load_candidate_data()
        audits = audit_all_protected_attributes(df)
        assessment = evaluate_eu_ai_act_conformity(
            system_name="WorkforceGuard Test System",
            audit_results=audits,
            technical_docs_present=True,
            logging_active=True,
            human_in_the_loop_active=True,
        )
        self.assertEqual(assessment.risk_classification, "High-Risk (Annex III, Item 4 - Employment & Worker Management)")
        self.assertGreater(assessment.data_governance_score, 0)
        self.assertIn("human sign-off", assessment.human_oversight_controls[0].lower())

    def test_optimize_selection_threshold(self):
        df = load_candidate_data()
        opt = optimize_selection_threshold(df, score_col="AlgorithmicScore")
        self.assertIn("recommended_threshold", opt)
        self.assertIn("simulation_curve", opt)
        self.assertTrue(len(opt["simulation_curve"]) > 0)

if __name__ == "__main__":
    unittest.main()
