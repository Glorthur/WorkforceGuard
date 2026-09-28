"""
Data Cleaning & 3NF Relational Normalization Pipeline for WorkforceGuard.
Decomposes exactly TWO real empirical datasets into 6 normalized relational tables:
1. BLS industry employment & AI exposure -> dim_naics_sectors, fact_industry_exposure
2. Pew ATP Wave 119 microdata (via build_pew_w119.py) -> dim_demographics, dim_ai_use_cases,
   fact_pew_survey_responses, fact_pew_hiring_vs_humans
"""
from pathlib import Path
from typing import Dict, Tuple
import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

SECTOR_OF_PREFIX = {
    "31": "31-33", "32": "31-33", "33": "31-33",
    "44": "44-45", "45": "44-45",
    "48": "48-49", "49": "48-49",
    "99": "90",  # BLS 999100-999300: government excluding education and hospitals
}
RANGE_SECTOR_TITLES = {
    "31-33": "Manufacturing",
    "44-45": "Retail trade",
    "48-49": "Transportation and warehousing",
}

def clean_and_normalize_bls_exposure(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Decomposes raw BLS industry employment and exposure data into:
    1. dim_naics_sectors (Lookup Table of 2-digit parent sectors)
    2. fact_industry_exposure (Fact Table of 6-digit detailed industries)
    """
    df_clean = df.copy()
    df_clean["naics_code"] = df_clean["naics_code"].astype(str).str.strip().str.zfill(6)
    df_clean["title"] = df_clean["title"].astype(str).str.strip()
    df_clean["covered_employment_2024"] = df_clean["covered_employment_2024"].fillna(0).astype(int)
    df_clean["weighted_exposure"] = df_clean["weighted_exposure"].astype(float).round(4)
    
    # 1. Parent sectors (dim_naics_sectors). NAICS has 20 sectors; three span
    # several 2-digit prefixes, and BLS codes state/local government as 999xxx.
    sectors = df_clean[df_clean["is_sector"] == True].copy()
    # 910000 Federal government is a subset of 900000 Government; keep one parent.
    sectors = sectors[sectors["naics_code"] != "910000"]
    sectors["sector_code"] = sectors["naics_code"].str[:2].map(lambda p: SECTOR_OF_PREFIX.get(p, p))
    dim_sectors = sectors[["sector_code", "title"]].drop_duplicates(subset=["sector_code"]).copy()
    dim_sectors.columns = ["sector_code", "sector_title"]
    missing_titles = [
        {"sector_code": code, "sector_title": title}
        for code, title in RANGE_SECTOR_TITLES.items()
        if code not in set(dim_sectors["sector_code"])
    ]
    dim_sectors = pd.concat([dim_sectors, pd.DataFrame(missing_titles)], ignore_index=True)

    detailed = df_clean[df_clean["is_sector"] == False].copy()
    detailed["sector_code"] = detailed["naics_code"].str[:2].map(lambda p: SECTOR_OF_PREFIX.get(p, p))
    missing_codes = set(detailed["sector_code"]) - set(dim_sectors["sector_code"])
    if missing_codes:
        raise ValueError(f"Industries reference unknown NAICS sectors: {sorted(missing_codes)}")
    dim_sectors = dim_sectors.sort_values("sector_code").reset_index(drop=True)

    # 2. Fact table. The raw file mixes NAICS levels 3-6, so a level-3 total and its
    # own sub-industries both appear. Flag the rows with no ancestor in the file:
    # summing only those counts each worker once.
    detailed["naics_level"] = detailed["naics_level"].astype(int)
    prefixes = {(lvl, code[:lvl]) for code, lvl in zip(detailed["naics_code"], detailed["naics_level"])}
    detailed["counts_in_total"] = [
        int(not any((k, code[:k]) in prefixes for k in range(3, lvl)))
        for code, lvl in zip(detailed["naics_code"], detailed["naics_level"])
    ]

    fact_industries = detailed[[
        "naics_code", "sector_code", "title", "naics_level", "counts_in_total",
        "covered_employment_2024", "weighted_exposure",
    ]].copy()
    fact_industries.columns = [
        "naics_code", "parent_sector_code", "industry_title", "naics_level", "counts_in_total",
        "covered_employment", "weighted_exposure",
    ]
    fact_industries = fact_industries.sort_values("naics_code").reset_index(drop=True)
    
    return dim_sectors, fact_industries

def clean_and_normalize_pew_survey(df: pd.DataFrame, df_hvh: pd.DataFrame):
    """
    Decomposes the Pew ATP Wave 119 tables (built from microdata by build_pew_w119.py) into:
    1. dim_demographics (cohort lookup; unweighted n and margin of error depend on the cohort only)
    2. dim_ai_use_cases (use case, Pew item and wording, EU AI Act classification)
    3. fact_pew_survey_responses (weighted favor / oppose / not sure per use case x cohort)
    4. fact_pew_hiring_vs_humans (AI better / worse / same as humans at treating applicants the same, per cohort)
    """
    df_clean = df.copy()
    df_clean["category"] = df_clean["category"].astype(str).str.strip()
    df_clean["demographic_group"] = df_clean["demographic_group"].astype(str).str.strip()

    def classify_demo(d: str) -> str:
        if d == "Total US Adults":
            return "Overall"
        elif d in ["Men", "Women"]:
            return "Gender"
        elif d in ["White", "Black", "Hispanic", "Asian"]:
            return "Race_Ethnicity"
        elif d.startswith("Ages"):
            return "Age"
        raise ValueError(f"Unknown demographic group: {d}")

    demos = df_clean.drop_duplicates("demographic_group").sort_values("demographic_group")
    dim_demographics = pd.DataFrame({
        "demographic_id": range(1, len(demos) + 1),
        "demographic_name": demos["demographic_group"].values,
        "dimension_type": [classify_demo(d) for d in demos["demographic_group"]],
        "unweighted_n": demos["unweighted_n"].astype(int).values,
        "moe_pct": demos["moe_pct"].astype(float).values,
    })
    demo_to_id = dict(zip(dim_demographics["demographic_name"], dim_demographics["demographic_id"]))

    def get_risk_metadata(case_name: str) -> Tuple[str, str]:
        if "Reviewing Job Applications" in case_name:
            return ("High-Risk (Annex III, point 4(a))",
                    "Analysing and filtering job applications.")
        if "Final Hiring" in case_name:
            return ("High-Risk (Annex III, point 4(a))",
                    "Recruitment and selection, including evaluating candidates.")
        if "Facial Expressions" in case_name:
            return ("Prohibited where it infers emotions (Art. 5(1)(f))",
                    "Emotion recognition in the workplace is banned since 2 Feb 2025, except for medical or safety reasons.")
        if "Promotions" in case_name:
            return ("High-Risk (Annex III, point 4(b))",
                    "Decisions affecting promotion and other terms of work relationships.")
        if "Computer Activity" in case_name:
            return ("High-Risk (Annex III, point 4(b))",
                    "Monitoring and evaluating worker behaviour; employers must inform workers and their representatives before use (Art. 26(7)).")
        raise ValueError(f"No EU AI Act classification defined for use case: {case_name}")

    cases = df_clean.drop_duplicates("category").sort_values("category")
    dim_use_cases = pd.DataFrame([
        {"use_case_id": i, "use_case_name": c, "pew_item": item, "pew_question": q,
         "statutory_risk_tier": get_risk_metadata(c)[0], "risk_basis": get_risk_metadata(c)[1]}
        for i, (c, item, q) in enumerate(zip(cases["category"], cases["pew_item"], cases["question"]), start=1)
    ])
    case_to_id = dict(zip(dim_use_cases["use_case_name"], dim_use_cases["use_case_id"]))

    fact_responses = pd.DataFrame({
        "response_id": range(1, len(df_clean) + 1),
        "use_case_id": df_clean["category"].map(case_to_id).values,
        "demographic_id": df_clean["demographic_group"].map(demo_to_id).values,
        "favor_pct": df_clean["favor_pct"].astype(float).values,
        "oppose_pct": df_clean["oppose_pct"].astype(float).values,
        "not_sure_pct": df_clean["not_sure_pct"].astype(float).values,
    })

    fact_hvh = pd.DataFrame({
        "demographic_id": df_hvh["demographic_group"].str.strip().map(demo_to_id).values,
        "ai_better_pct": df_hvh["ai_better_pct"].astype(float).values,
        "ai_worse_pct": df_hvh["ai_worse_pct"].astype(float).values,
        "ai_same_pct": df_hvh["ai_same_pct"].astype(float).values,
        "ai_not_sure_pct": df_hvh["ai_not_sure_pct"].astype(float).values,
    })
    if fact_hvh["demographic_id"].isna().any() or fact_responses.isna().any().any():
        raise ValueError("Pew tables reference cohorts or use cases that are not in the dimensions")
    return dim_demographics, dim_use_cases, fact_responses, fact_hvh

PEW_TABLES = ("dim_demographics", "dim_ai_use_cases", "fact_pew_survey_responses", "fact_pew_hiring_vs_humans")

def clean_and_normalize_datasets() -> Dict[str, pd.DataFrame]:
    """Runs end-to-end cleaning for the TWO datasets and saves clean 3NF relational tables."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df_bls = pd.read_csv(RAW_DIR / "real_bls_industry_ai_exposure.csv")
    df_pew = pd.read_csv(RAW_DIR / "pew_w119_workplace_ai.csv")
    df_hvh = pd.read_csv(RAW_DIR / "pew_w119_hiring_ai_vs_humans.csv")

    dim_sectors, fact_industries = clean_and_normalize_bls_exposure(df_bls)
    tables = {"dim_naics_sectors": dim_sectors, "fact_industry_exposure": fact_industries}
    tables.update(zip(PEW_TABLES, clean_and_normalize_pew_survey(df_pew, df_hvh)))

    for name, table in tables.items():
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    return tables

if __name__ == "__main__":
    tables = clean_and_normalize_datasets()
    print("Cleaned & 3NF normalized tables generated from TWO real datasets:")
    for name, df in tables.items():
        print(f"- {name}: {df.shape[0]} rows, {df.shape[1]} columns")
