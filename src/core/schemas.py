"""
Core data contracts and schemas for WorkforceGuard.
Shared across analytics, modeling, bias auditing, and the executive dashboard.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class EmployeeRecord:
    employee_id: int
    age: int
    gender: str
    ethnicity: str
    department: str
    job_role: str
    monthly_income: float
    overtime: str
    distance_from_home: int
    job_satisfaction: int
    work_life_balance: int
    years_at_company: int
    years_since_last_promotion: int
    attrition: str

@dataclass
class CandidateRecord:
    candidate_id: str
    department: str
    education: str
    years_experience: int
    age: int
    gender: str
    ethnicity: str
    interview_score: float
    technical_score: float
    algorithmic_score: float
    selected: int

@dataclass
class GroupMetric:
    group_name: str
    total_count: int
    selected_count: int
    selection_rate: float
    impact_ratio: float  # Compared to baseline/highest group
    passes_four_fifths_rule: bool

@dataclass
class DemographicAuditResult:
    protected_attribute: str
    baseline_group: str
    baseline_rate: float
    group_metrics: Dict[str, GroupMetric]
    overall_disparate_impact_found: bool
    minimum_impact_ratio: float
    compliance_status: str  # "COMPLIANT", "ADVERSE_IMPACT_WARNING", "NON_COMPLIANT"

@dataclass
class NYCLocalLaw144Report:
    tool_name: str
    audit_date: str
    job_categories: List[str]
    gender_audit: DemographicAuditResult
    ethnicity_audit: DemographicAuditResult
    intersectional_audit: Optional[Dict[str, Any]] = None
    auditor_attestation: str = ""

@dataclass
class EUAIActAssessment:
    system_name: str
    risk_classification: str  # "High-Risk (Annex III - Employment & Worker Management)"
    data_governance_score: float  # 0 to 100
    technical_documentation_complete: bool
    record_keeping_logging_active: bool
    transparency_explainability_rating: str  # "Satisfactory", "Needs Review"
    human_oversight_controls: List[str]
    cybersecurity_robustness: str
    overall_conformity_status: str  # "Pass", "Conditional", "Action Required"

@dataclass
class FlightRiskPrediction:
    employee_id: int
    probability: float
    risk_level: str  # "Low", "Medium", "High"
    primary_drivers: List[Dict[str, Any]]
    retention_recommendations: List[str]
