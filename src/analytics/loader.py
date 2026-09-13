"""
Dataset loader and validation module for WorkforceGuard.
Ingests real BLS/O*NET AI exposure, Pew Research survey, Stanford HAI governance,
and EEOC federal workforce benchmark datasets.
"""
from pathlib import Path
from typing import List, Optional
import pandas as pd

from src.core.schemas import (
    IndustryAIExposureRecord,
    OccupationAIExposureRecord,
    PewAISurveyRecord,
    EnterpriseAIGovernanceRecord,
    EEOCBenchmarkRecord,
    CandidateRecord,
    EmployeeRecord,
    GroupMetric,
)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

REAL_INDUSTRY_PATH = RAW_DIR / "real_bls_industry_ai_exposure.csv"
REAL_OCCUPATIONS_PATH = RAW_DIR / "real_bls_occupations_ai_exposure.csv"
REAL_PEW_PATH = RAW_DIR / "real_pew_ai_workplace_survey.csv"
REAL_STANFORD_PATH = RAW_DIR / "real_stanford_hai_enterprise_governance.csv"
REAL_EEOC_PATH = RAW_DIR / "real_eeoc_workforce_benchmarks.csv"
CANDIDATE_PATH = RAW_DIR / "hiring_promotion_candidates.csv"
ATTRITION_PATH = RAW_DIR / "ibm_hr_attrition.csv"

def load_industry_exposure_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else REAL_INDUSTRY_PATH
    if not path.exists():
        raise FileNotFoundError(f"Industry exposure dataset not found at {path}")
    df = pd.read_csv(path)
    df["weighted_exposure"] = df["weighted_exposure"].astype(float)
    df["covered_employment_2024"] = df["covered_employment_2024"].fillna(0).astype(int)
    
    def assign_tier(val: float) -> str:
        if val >= 7.5:
            return "High Exposure (Accelerated Automation)"
        elif val >= 5.5:
            return "Moderate Exposure (Augmentation / Workflow AI)"
        else:
            return "Low Exposure (Manual / Physical Intensive)"
            
    df["exposure_tier"] = df["weighted_exposure"].apply(assign_tier)
    return df

def load_occupations_exposure_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else REAL_OCCUPATIONS_PATH
    if not path.exists():
        raise FileNotFoundError(f"Occupations exposure dataset not found at {path}")
    df = pd.read_csv(path)
    df["median_pay_annual"] = df["median_pay_annual"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False)
    df["median_pay_annual"] = pd.to_numeric(df["median_pay_annual"], errors="coerce").fillna(0.0)
    df["num_jobs_2024"] = df["num_jobs_2024"].fillna(0).astype(int)
    df["projected_employment_2034"] = df["projected_employment_2034"].fillna(0).astype(int)
    df["outlook_pct"] = df["outlook_pct"].fillna(0.0).astype(float)
    return df

def load_pew_survey_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else REAL_PEW_PATH
    if not path.exists():
        raise FileNotFoundError(f"Pew survey dataset not found at {path}")
    return pd.read_csv(path)

def load_stanford_governance_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else REAL_STANFORD_PATH
    if not path.exists():
        raise FileNotFoundError(f"Stanford governance dataset not found at {path}")
    df = pd.read_csv(path)
    df["governance_gap_pct"] = (df["risk_recognized_pct"] - df["risk_mitigated_pct"]).round(1)
    return df

def load_eeoc_benchmarks(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else REAL_EEOC_PATH
    if not path.exists():
        raise FileNotFoundError(f"EEOC benchmark dataset not found at {path}")
    return pd.read_csv(path)

def load_candidate_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else CANDIDATE_PATH
    if not path.exists():
        raise FileNotFoundError(f"Candidate dataset not found at {path}")
    df = pd.read_csv(path)
    df["Selected"] = df["Selected"].astype(int)
    df["AlgorithmicScore"] = df["AlgorithmicScore"].astype(float)
    return df

def load_attrition_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    path = Path(csv_path) if csv_path else ATTRITION_PATH
    if not path.exists():
        raise FileNotFoundError(f"Attrition dataset not found at {path}")
    df = pd.read_csv(path)
    df["EmployeeNumber"] = df["EmployeeNumber"].astype(int)
    df["MonthlyIncome"] = df["MonthlyIncome"].astype(float)
    df["YearsAtCompany"] = df["YearsAtCompany"].astype(int)
    df["YearsSinceLastPromotion"] = df["YearsSinceLastPromotion"].astype(int)
    df["Attrition_Binary"] = (df["Attrition"].str.strip().str.lower() == "yes").astype(int)
    return df

def to_employee_records(df: pd.DataFrame) -> List[EmployeeRecord]:
    records = []
    for _, row in df.iterrows():
        records.append(
            EmployeeRecord(
                employee_id=int(row["EmployeeNumber"]),
                age=int(row["Age"]),
                gender=str(row["Gender"]),
                ethnicity=str(row["Ethnicity"]),
                department=str(row["Department"]),
                job_role=str(row["JobRole"]),
                monthly_income=float(row["MonthlyIncome"]),
                overtime=str(row["OverTime"]),
                distance_from_home=int(row["DistanceFromHome"]),
                job_satisfaction=int(row["JobSatisfaction"]),
                work_life_balance=int(row["WorkLifeBalance"]),
                years_at_company=int(row["YearsAtCompany"]),
                years_since_last_promotion=int(row["YearsSinceLastPromotion"]),
                attrition=str(row["Attrition"]),
            )
        )
    return records

def to_candidate_records(df: pd.DataFrame) -> List[CandidateRecord]:
    records = []
    for _, row in df.iterrows():
        records.append(
            CandidateRecord(
                candidate_id=str(row["CandidateID"]),
                department=str(row["Department"]),
                education=str(row["Education"]),
                years_experience=int(row["YearsExperience"]),
                age=int(row["Age"]),
                gender=str(row["Gender"]),
                ethnicity=str(row["Ethnicity"]),
                interview_score=float(row["InterviewScore"]),
                technical_score=float(row["TechnicalAssessmentScore"]),
                algorithmic_score=float(row["AlgorithmicScore"]),
                selected=int(row["Selected"]),
            )
        )
    return records
