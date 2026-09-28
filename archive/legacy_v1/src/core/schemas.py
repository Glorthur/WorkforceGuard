"""
Core data contracts and schemas for WorkforceGuard.
Includes schemas for real BLS/O*NET AI exposure, Pew/Stanford AI adoption & governance surveys,
EEOC federal workforce benchmarks, and regulatory algorithmic bias audits (NYC LL144 & EU AI Act).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class IndustryAIExposureRecord:
    naics_code: str
    title: str
    industry_type: str
    covered_employment_2024: int
    weighted_exposure: float
    risk_tier: str

@dataclass
class OccupationAIExposureRecord:
    title: str
    category: str
    median_pay_annual: float
    num_jobs_2024: int
    projected_employment_2034: int
    outlook_pct: float
    exposure_tier: str

@dataclass
class PewAISurveyRecord:
    source: str
    category: str
    demographic_group: str
    acceptable_pct: float
    unacceptable_pct: float
    fairer_than_humans_pct: float
    less_fair_pct: float
    equal_fairness_pct: float

@dataclass
class EnterpriseAIGovernanceRecord:
    function: str
    adoption_rate_pct: float
    risk_recognized_pct: float
    risk_mitigated_pct: float
    governance_gap_pct: float

@dataclass
class EEOCBenchmarkRecord:
    job_category: str
    total_count: int
    female_pct: float
    male_pct: float
    white_pct: float
    black_pct: float
    hispanic_pct: float
    asian_pct: float
    other_pct: float

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
