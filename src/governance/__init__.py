"""
Algorithmic Governance, Bias Auditing & Regulatory Policy Module for WorkforceGuard.
"""
from src.governance.bias_audit import (
    calculate_adverse_impact_ratio,
    audit_all_protected_attributes,
    benchmark_against_eeoc,
)
from src.governance.nyc_ll144 import (
    generate_nyc_ll144_report,
    format_nyc_ll144_markdown,
)
from src.governance.eu_ai_act import (
    evaluate_eu_ai_act_conformity,
)
from src.governance.policy_remediation import (
    optimize_selection_threshold,
)

__all__ = [
    "calculate_adverse_impact_ratio",
    "audit_all_protected_attributes",
    "benchmark_against_eeoc",
    "generate_nyc_ll144_report",
    "format_nyc_ll144_markdown",
    "evaluate_eu_ai_act_conformity",
    "optimize_selection_threshold",
]
