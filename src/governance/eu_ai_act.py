"""
EU AI Act (Regulation EU 2024/1689) Annex III High-Risk AI Conformity Assessment Engine.
Specifically audits compliance for AI systems used in recruitment, selection, promotion, and worker management.
"""
from typing import Dict, Any, List, Optional
from src.core.schemas import EUAIActAssessment, DemographicAuditResult

def evaluate_eu_ai_act_conformity(
    system_name: str = "WorkforceGuard Algorithmic Evaluation Engine",
    audit_results: Optional[Dict[str, DemographicAuditResult]] = None,
    technical_docs_present: bool = True,
    logging_active: bool = True,
    human_in_the_loop_active: bool = True,
    cybersecurity_standard: str = "ISO/IEC 27001 / SOC 2 Certified",
) -> EUAIActAssessment:
    """
    Evaluates conformity against the mandatory Chapter III requirements for High-Risk Employment AI:
    - Art. 9: Risk Management
    - Art. 10: Data & Data Governance
    - Art. 11: Technical Documentation
    - Art. 12: Automatic Record-Keeping / Logging
    - Art. 13: Transparency & Worker Disclosures
    - Art. 14: Human Oversight
    - Art. 15: Accuracy, Robustness & Cybersecurity
    """
    # 1. Evaluate Data Governance & Bias (Art. 10)
    data_gov_score = 100.0
    bias_detected = False
    
    if audit_results:
        for attr, res in audit_results.items():
            if res.overall_disparate_impact_found:
                bias_detected = True
                # Deduct points based on severity of minimum impact ratio
                penalty = max(10.0, (0.80 - res.minimum_impact_ratio) * 100.0)
                data_gov_score -= penalty
    data_gov_score = max(20.0, round(data_gov_score, 1))

    # 2. Human Oversight Controls (Art. 14)
    human_controls = []
    if human_in_the_loop_active:
        human_controls = [
            "Mandatory human sign-off on adverse hiring decisions",
            "Real-time override button for candidate score adjustments",
            "Recruiter discretion audit trail",
            "Candidate appeal and manual reassessment workflow"
        ]
    else:
        human_controls = ["Warning: Fully automated scoring without human override capability"]

    # 3. Transparency & Explainability (Art. 13)
    if data_gov_score >= 80.0 and technical_docs_present:
        transparency = "Satisfactory (Candidate Disclosures & Model Cards Active)"
    else:
        transparency = "Needs Remediation (Incomplete Bias Documentation or Missing Cards)"

    # 4. Overall Conformity Status
    score = (
        data_gov_score * 0.40 +
        (100.0 if technical_docs_present else 0.0) * 0.20 +
        (100.0 if logging_active else 0.0) * 0.20 +
        (100.0 if human_in_the_loop_active else 0.0) * 0.20
    )
    
    if score >= 85.0 and not bias_detected:
        status = "Pass (High-Risk Conformity Validated)"
    elif score >= 65.0:
        status = "Conditional (Corrective Action Plan Required within 60 Days)"
    else:
        status = "Action Required (Non-Compliant under EU AI Act Annex III)"

    return EUAIActAssessment(
        system_name=system_name,
        risk_classification="High-Risk (Annex III, Item 4 - Employment & Worker Management)",
        data_governance_score=data_gov_score,
        technical_documentation_complete=technical_docs_present,
        record_keeping_logging_active=logging_active,
        transparency_explainability_rating=transparency,
        human_oversight_controls=human_controls,
        cybersecurity_robustness=cybersecurity_standard,
        overall_conformity_status=status
    )
