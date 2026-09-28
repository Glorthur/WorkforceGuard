"""
Educational SQL Analytics Suite for WorkforceGuard (Two-Dataset Edition).
Contains heavily commented, beginner-to-intermediate SQL queries analyzing:
1. Macro AI Exposure & Employment Aggregations by NAICS Sector (BLS employment).
2. AI vs humans in hiring by cohort, using window functions (Pew ATP W119 microdata).
3. Public support for each workplace AI use case, all U.S. adults (Pew ATP W119).
4. Statutory AI Risk Aggregations by EU AI Act classification (Annex III points 4(a)/4(b), Art. 5).
"""
import pandas as pd
from src.database.connection import execute_query

# -----------------------------------------------------------------------------
# Query 1: Macro AI Exposure & Covered Employment by 2-Digit Sector
# -----------------------------------------------------------------------------
# Educational Rationale:
# Demonstrates why an employment-weighted average [SUM(w * x) / SUM(w)] accurately
# measures true labor-market exposure across the economy, whereas a naive unweighted
# arithmetic mean [AVG(x)] distorts risk by treating tiny sub-industries identically
# to massive employment hubs. The fact table mixes NAICS levels 3-6, so only rows
# with counts_in_total = 1 (no ancestor present) are aggregated; otherwise a
# level-3 total and its own sub-industries would be summed together.
# -----------------------------------------------------------------------------
QUERY_MACRO_EXPOSURE_BY_SECTOR = """
SELECT
    s.sector_code,
    s.sector_title,
    COUNT(i.naics_code) AS detailed_industry_count,
    SUM(i.covered_employment) AS detailed_employment,
    ROUND(
        SUM(i.covered_employment * i.weighted_exposure) / NULLIF(SUM(i.covered_employment), 0),
        4
    ) AS employment_weighted_exposure,
    ROUND(AVG(i.weighted_exposure), 4) AS unweighted_mean_exposure
FROM dim_naics_sectors AS s
JOIN fact_industry_exposure AS i
    ON i.parent_sector_code = s.sector_code
WHERE i.counts_in_total = 1
GROUP BY s.sector_code, s.sector_title
ORDER BY employment_weighted_exposure DESC, s.sector_code;
"""

# Exposure tier cut-points on the 0-10 scale (single source for SQL and UI labels).
TIER_HIGH_MIN = 7.5
TIER_MODERATE_MIN = 5.5

QUERY_EMPLOYMENT_BY_TIER = f"""
SELECT
    CASE
        WHEN weighted_exposure >= {TIER_HIGH_MIN} THEN 'High'
        WHEN weighted_exposure >= {TIER_MODERATE_MIN} THEN 'Moderate'
        ELSE 'Low'
    END AS tier_group,
    SUM(covered_employment) AS total_emp
FROM fact_industry_exposure
WHERE counts_in_total = 1
GROUP BY tier_group;
"""

# -----------------------------------------------------------------------------
# Query 2: AI vs Humans in Hiring, by Cohort (Pew ATP W119, item AIWRKH3_b)
# -----------------------------------------------------------------------------
# Educational Rationale:
# "Would AI do better, worse or about the same as humans at treating all job applicants
# in the same way?" Net skepticism = % worse - % better (negative = more trust in AI).
# RANK() OVER (PARTITION BY ...) ranks cohorts within each demographic dimension.
# Cohort sample size and margin of error come from dim_demographics.
# -----------------------------------------------------------------------------
QUERY_PEW_HIRING_VS_HUMANS = """
SELECT
    d.dimension_type,
    d.demographic_name,
    d.unweighted_n,
    d.moe_pct,
    h.ai_better_pct,
    h.ai_worse_pct,
    h.ai_same_pct,
    h.ai_not_sure_pct,
    ROUND(h.ai_worse_pct - h.ai_better_pct, 1) AS net_skepticism_pp,
    RANK() OVER (
        PARTITION BY d.dimension_type
        ORDER BY (h.ai_worse_pct - h.ai_better_pct) DESC
    ) AS skepticism_rank
FROM fact_pew_hiring_vs_humans AS h
JOIN dim_demographics AS d
    ON h.demographic_id = d.demographic_id
ORDER BY d.dimension_type, skepticism_rank;
"""

# -----------------------------------------------------------------------------
# Query 3: Public Support by Use Case, All U.S. Adults (Pew ATP W119)
# -----------------------------------------------------------------------------
# Net opposition = % oppose - % favor for each surveyed workplace use, alongside its
# EU AI Act classification.
# -----------------------------------------------------------------------------
QUERY_USE_CASES_OVERALL = """
SELECT
    u.use_case_name,
    u.pew_item,
    u.pew_question,
    u.statutory_risk_tier,
    u.risk_basis,
    r.favor_pct,
    r.oppose_pct,
    r.not_sure_pct,
    ROUND(r.oppose_pct - r.favor_pct, 1) AS net_opposition_pp
FROM fact_pew_survey_responses AS r
JOIN dim_ai_use_cases AS u ON r.use_case_id = u.use_case_id
JOIN dim_demographics AS d ON r.demographic_id = d.demographic_id
WHERE d.dimension_type = 'Overall'
ORDER BY r.favor_pct DESC;
"""

# -----------------------------------------------------------------------------
# Query 4: Statutory AI Risk Tier Aggregation (EU AI Act classifications)
# -----------------------------------------------------------------------------
# Averages all-adult support across the use cases in each classification in
# Regulation (EU) 2024/1689: Annex III point 4(a) (recruitment), point 4(b)
# (work relationships) and Art. 5(1)(f) (emotion inference, prohibited).
# -----------------------------------------------------------------------------
QUERY_STATUTORY_AI_RISK_SUMMARY = """
SELECT
    u.statutory_risk_tier,
    COUNT(DISTINCT u.use_case_id) AS use_case_count,
    ROUND(AVG(r.favor_pct), 1) AS avg_favor_pct,
    ROUND(AVG(r.oppose_pct), 1) AS avg_oppose_pct,
    ROUND(AVG(r.oppose_pct - r.favor_pct), 1) AS avg_net_opposition_pp
FROM fact_pew_survey_responses AS r
JOIN dim_ai_use_cases AS u ON r.use_case_id = u.use_case_id
JOIN dim_demographics AS d ON r.demographic_id = d.demographic_id
WHERE d.dimension_type = 'Overall'
GROUP BY u.statutory_risk_tier
ORDER BY avg_net_opposition_pp DESC;
"""

def get_macro_exposure_summary() -> pd.DataFrame:
    """Runs Query 1 and returns macro sector exposure summary."""
    return execute_query(QUERY_MACRO_EXPOSURE_BY_SECTOR)

def get_pew_hiring_vs_humans() -> pd.DataFrame:
    """Runs Query 2: AI vs humans at treating applicants the same, by cohort."""
    return execute_query(QUERY_PEW_HIRING_VS_HUMANS)

def get_use_cases_overall() -> pd.DataFrame:
    """Runs Query 3: support for each workplace AI use among all U.S. adults."""
    return execute_query(QUERY_USE_CASES_OVERALL)

def get_statutory_risk_summary() -> pd.DataFrame:
    """Runs Query 4 and returns public sentiment grouped by EU AI Act statutory risk tier."""
    return execute_query(QUERY_STATUTORY_AI_RISK_SUMMARY)

if __name__ == "__main__":
    print("Testing Query 1: Macro Exposure by Sector...")
    df1 = get_macro_exposure_summary()
    print(df1.head())
    
    print("\nTesting Query 2: Pew AI vs Humans in Hiring...")
    df2 = get_pew_hiring_vs_humans()
    print(df2.head())

    print("\nTesting Query 4: Statutory AI Risk Summary...")
    df3 = get_statutory_risk_summary()
    print(df3)
