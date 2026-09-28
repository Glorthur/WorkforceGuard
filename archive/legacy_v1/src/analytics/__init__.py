"""
Analytics module for WorkforceGuard.
"""
from src.analytics.loader import (
    load_attrition_data,
    load_candidate_data,
    to_employee_records,
    to_candidate_records,
)
from src.analytics.metrics import (
    calculate_attrition_kpis,
    calculate_pay_equity,
    calculate_promotion_latency,
)

__all__ = [
    "load_attrition_data",
    "load_candidate_data",
    "to_employee_records",
    "to_candidate_records",
    "calculate_attrition_kpis",
    "calculate_pay_equity",
    "calculate_promotion_latency",
]
