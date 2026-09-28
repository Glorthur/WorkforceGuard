"""
Analytics and metrics engine for WorkforceGuard.
Computes real macro AI industry exposure, occupation outlooks,
Pew public sentiment perception gaps, Stanford enterprise governance deficits,
and workforce descriptive statistics.
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd

def analyze_ai_industry_exposure(df_industry: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes real BLS/NAICS industry AI exposure distributions.
    """
    total_industries = len(df_industry)
    if total_industries == 0:
        return {}
        
    avg_exposure = float(round(df_industry["weighted_exposure"].mean(), 2))
    total_covered_employment = int(df_industry["covered_employment_2024"].sum())
    
    # Tier breakdown
    tier_counts = df_industry["exposure_tier"].value_counts().to_dict()
    tier_employment = df_industry.groupby("exposure_tier")["covered_employment_2024"].sum().to_dict()
    
    # Top 10 highest exposed industries
    top_10 = df_industry.sort_values("weighted_exposure", ascending=False).head(10)[
        ["naics_code", "title", "covered_employment_2024", "weighted_exposure", "exposure_tier"]
    ].to_dict(orient="records")
    
    # 10 lowest exposed industries
    bottom_10 = df_industry.sort_values("weighted_exposure", ascending=True).head(10)[
        ["naics_code", "title", "covered_employment_2024", "weighted_exposure", "exposure_tier"]
    ].to_dict(orient="records")
    
    return {
        "total_industries_analyzed": total_industries,
        "average_exposure_score": avg_exposure,
        "total_covered_workforce": total_covered_employment,
        "tier_distribution": tier_counts,
        "tier_workforce_impact": tier_employment,
        "top_exposed_industries": top_10,
        "least_exposed_industries": bottom_10,
    }

def analyze_pew_ai_sentiment(df_pew: pd.DataFrame) -> Dict[str, Any]:
    """
    Extracts real survey insights from Pew Research ATP 119 on AI in Hiring and Workforce Evaluation.
    """
    if len(df_pew) == 0:
        return {}
        
    hiring_df = df_pew[df_pew["category"] == "AI in Hiring Decisions"]
    
    # Demographic comparison on fairness
    demographic_fairness = hiring_df[
        hiring_df["demographic_group"].isin(["Men", "Women", "White", "Black", "Hispanic", "Asian", "Ages 18-29", "Ages 65+"])
    ][["demographic_group", "acceptable_pct", "unacceptable_pct", "fairer_than_humans_pct", "less_fair_pct"]].to_dict(orient="records")
    
    # Use cases breakdown
    use_cases = df_pew[df_pew["demographic_group"] == "Total US Adults"][
        ["category", "acceptable_pct", "unacceptable_pct", "fairer_than_humans_pct", "less_fair_pct"]
    ].to_dict(orient="records")
    
    return {
        "demographic_fairness_views": demographic_fairness,
        "use_case_acceptability": use_cases,
    }

def analyze_stanford_governance_gap(df_stanford: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes the Stanford HAI enterprise AI governance gap:
    disparity between recognizing AI risks and actually implementing mitigations.
    """
    if len(df_stanford) == 0:
        return {}
        
    avg_adoption = float(round(df_stanford["adoption_rate_pct"].mean(), 2))
    avg_gap = float(round(df_stanford["governance_gap_pct"].mean(), 2))
    
    ranked_by_gap = df_stanford.sort_values("governance_gap_pct", ascending=False).to_dict(orient="records")
    
    return {
        "average_adoption_rate": avg_adoption,
        "average_governance_gap": avg_gap,
        "functions_ranked_by_deficit": ranked_by_gap,
    }

def calculate_attrition_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    total_employees = len(df)
    if total_employees == 0:
        return {"total_employees": 0, "total_attrition": 0, "overall_attrition_rate": 0.0}
    attrition_binary = df["Attrition_Binary"] if "Attrition_Binary" in df.columns else (df["Attrition"].str.strip().str.lower() == "yes").astype(int)
    total_attrition = int(attrition_binary.sum())
    overall_rate = float(round(total_attrition / total_employees, 4))
    return {
        "total_employees": total_employees,
        "total_attrition": total_attrition,
        "overall_attrition_rate": overall_rate,
    }

def calculate_pay_equity(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) == 0:
        return {}
    gender_stats = df.groupby("Gender")["MonthlyIncome"].agg(["median", "mean", "count"]).round(2)
    gender_dict = {
        str(g): {
            "median_income": float(row["median"]),
            "mean_income": float(row["mean"]),
            "headcount": int(row["count"]),
        }
        for g, row in gender_stats.iterrows()
    }
    return {"gender_equity": gender_dict}

def calculate_promotion_latency(df: pd.DataFrame) -> Dict[str, Any]:
    if len(df) == 0:
        return {}
    return {
        "avg_tenure": float(round(df["YearsAtCompany"].mean(), 2)),
        "avg_years_since_promo": float(round(df["YearsSinceLastPromotion"].mean(), 2)),
    }
