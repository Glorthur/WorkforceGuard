"""
Builds the Pew raw tables from the official ATP Wave 119 microdata (data/W119_Dec22.zip).

Survey: Pew Research Center American Trends Panel Wave 119, Dec 12-18, 2022, N = 11,004.
All percentages are weighted with WEIGHT_W119 over all respondents in the cohort (refusals stay
in the base, as in Pew's toplines). Margins of error are 95% for a 50% estimate, using the Kish
design effect of the weights within each cell.

Run once after replacing the zip:  python -m src.data_pipeline.build_pew_w119
Requires pyreadstat (only for this build step; the app reads the CSV outputs).
"""
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
ZIP_PATH = DATA_DIR / "W119_Dec22.zip"
OUT_USE_CASES = DATA_DIR / "raw" / "pew_w119_workplace_ai.csv"
OUT_HIRING_VS_HUMANS = DATA_DIR / "raw" / "pew_w119_hiring_ai_vs_humans.csv"

# Dashboard use case -> Pew item (favor / oppose / not sure). Names follow Pew's wording.
USE_CASE_ITEMS = {
    "AI Reviewing Job Applications": "AIWRKH2_a_W119",
    "AI Making Final Hiring Decisions": "AIWRKH2_b_W119",
    "AI Analyzing Employees' Facial Expressions": "FACERECWK2_b_W119",
    "AI Recording Workers' Computer Activity": "AIWRKM2_b_W119",
    "AI Deciding Promotions": "AIWRKM4_a_W119",
}
# "Would AI do better, worse or about the same as humans at treating all job applicants in the same way?"
HIRING_VS_HUMANS_ITEM = "AIWRKH3_b_W119"

COHORTS = [
    ("Total US Adults", None, None),
    ("Men", "F_GENDER", 1), ("Women", "F_GENDER", 2),
    ("White", "F_RACETHNMOD", 1), ("Black", "F_RACETHNMOD", 2),
    ("Hispanic", "F_RACETHNMOD", 3), ("Asian", "F_RACETHNMOD", 5),
    ("Ages 18-29", "F_AGECAT", 1), ("Ages 30-49", "F_AGECAT", 2),
    ("Ages 50-64", "F_AGECAT", 3), ("Ages 65+", "F_AGECAT", 4),
]


def weighted_shares(values: pd.Series, weights: pd.Series, codes: dict) -> dict:
    total = weights.sum()
    return {name: round(float(weights[values == code].sum() / total * 100), 1) for name, code in codes.items()}


def moe_pct(weights: pd.Series) -> float:
    n = len(weights)
    deff = n * float((weights ** 2).sum()) / float(weights.sum()) ** 2
    return round(float(1.96 * np.sqrt(deff * 0.25 / n) * 100), 1)


def build(zip_path: Path = ZIP_PATH):
    import pyreadstat

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as z:
            sav = next(n for n in z.namelist() if n.endswith(".sav"))
            z.extract(sav, tmp)
        df, meta = pyreadstat.read_sav(str(Path(tmp) / sav))
    labels = dict(zip(meta.column_names, meta.column_labels))

    use_rows, hvh_rows = [], []
    for cohort, var, code in COHORTS:
        d = df if var is None else df[df[var] == code]
        w = d["WEIGHT_W119"]
        base = {"source": "Pew Research Center ATP Wave 119 (Dec 12-18, 2022)",
                "demographic_group": cohort, "unweighted_n": len(d), "moe_pct": moe_pct(w)}
        for use_case, item in USE_CASE_ITEMS.items():
            shares = weighted_shares(d[item], w, {"favor_pct": 1, "oppose_pct": 2, "not_sure_pct": 9})
            question = labels[item].split(".", 1)[1].strip()
            use_rows.append({**base, "category": use_case, "pew_item": item.replace("_W119", ""),
                             "question": question, **shares})
        shares = weighted_shares(d[HIRING_VS_HUMANS_ITEM], w,
                                 {"ai_better_pct": 1, "ai_worse_pct": 2, "ai_same_pct": 3, "ai_not_sure_pct": 9})
        hvh_rows.append({**base, "pew_item": HIRING_VS_HUMANS_ITEM.replace("_W119", ""), **shares})

    pd.DataFrame(use_rows).to_csv(OUT_USE_CASES, index=False)
    pd.DataFrame(hvh_rows).to_csv(OUT_HIRING_VS_HUMANS, index=False)
    return len(use_rows), len(hvh_rows)


if __name__ == "__main__":
    n_use, n_hvh = build()
    print(f"Wrote {n_use} use-case rows to {OUT_USE_CASES.name} and {n_hvh} rows to {OUT_HIRING_VS_HUMANS.name}")
