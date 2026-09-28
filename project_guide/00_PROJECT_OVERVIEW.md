# Step 0: Project Overview & Learning Roadmap

Welcome to **WorkforceGuard**! This project is an educational, end-to-end analytics and governance pipeline built with **Python and SQL (MySQL 8.0, with an automatic SQLite fallback)**.

It combines:
1. **Real Data Engineering**: Understanding raw labour-market and survey data, profiling it, fixing flaws (including a double-counting trap), and designing a relational database.
2. **Relational Database Design (MySQL 8.0 / SQLite)**: Third Normal Form (3NF) across 6 tables, Primary Keys, Foreign Keys (`ON DELETE RESTRICT`), CHECK constraints, and analytical indexes.
3. **Advanced SQL Analytics**: `JOIN`s, group aggregations, employment-weighted averages, and SQL window functions (`RANK() OVER (PARTITION BY ...)`).
4. **AI Policy & Governance**: Mapping workplace AI use cases onto the **European Union Artificial Intelligence Act (EU AI Act - Regulation (EU) 2024/1689)**. The data is U.S. data, so the Act is used as a comparative lens, not because it applies to U.S. respondents. WorkforceGuard is a descriptive dashboard, not a high-risk AI system, and it reports no conformity status of its own.
5. **Interactive UI**: A single-page Streamlit dashboard (`streamlit run app.py`) that presents the data and findings.

---

## The Two Core Real Datasets

To keep things clear and avoid overwhelming you, this project uses **strictly two datasets**:

### Dataset 1: BLS Industry Employment + AI Exposure Score
* **File**: `data/raw/real_bls_industry_ai_exposure.csv`
* **Source**: Employment appears to follow the U.S. Bureau of Labor Statistics (BLS) National Employment Matrix structure ("Summary" / "Line Item" rows). The exposure column is **an industry AI task-exposure score (0-10); its construction method and source are not yet documented — to be cited by the project owner.** Do not attribute it to BLS or O*NET.
* **What it contains**: 355 rows — 18 sector-total rows (NAICS level 2) plus 337 industry rows at NAICS levels 3-6 — with covered employment counts and the 0-10 `weighted_exposure` score.
* **Core challenge**: The "Hierarchy Trap" — the 337 industry rows mix NAICS levels 3-6, so a level-3 total and its own sub-industries both appear. Summing every industry row gives 180.5M "covered workers"; counting each worker once gives **104.1M** (see Guide 01).

### Dataset 2: Pew Research Center American Trends Panel, Wave 119
* **Source file**: `data/W119_Dec22.zip` — Pew ATP Wave 119 microdata (survey Dec 12-18, 2022; N = 11,004 U.S. adults; weight `WEIGHT_W119`).
* **Derived files**: `python -m src.data_pipeline.build_pew_w119` converts the microdata into `data/raw/pew_w119_workplace_ai.csv` (55 rows = 5 use cases x 11 cohorts; favor / oppose / not sure) and `data/raw/pew_w119_hiring_ai_vs_humans.csv` (11 cohorts; would AI do better / worse / the same / not sure vs. humans at treating all applicants the same way). This build step needs `pyreadstat`; the app itself does not.
* **What it contains**: Weighted support for 5 workplace AI uses across 11 cohorts (Overall, Gender, Race/Ethnicity, Age), plus each cohort's unweighted n and 95% margin of error. The figures reproduce Pew's published toplines (e.g. 7% favor / 71% oppose AI making the final hiring decision).
* **Core challenge**: Normalizing flat survey output into relational tables and mapping each use case to its EU AI Act classification (Annex III, point 4(a)/(b), or the Art. 5(1)(f) emotion-recognition ban).
* **Note**: An older hand-typed Pew CSV did not match Pew's published figures and was archived to `archive/legacy_v1/data/UNVERIFIED_real_pew_ai_workplace_survey.csv`. Do not quote it. `data/W152_Aug24.zip` (Pew ATP Wave 152, Aug 2024) is also present but is not used by the pipeline.

---

## Learning Modules in this Folder

You can read through these guides at your own pace:

| File | What You Will Learn |
|---|---|
| [`01_DATA_CLEANING_AND_TRANSFORMATION_GUIDE.md`](./01_DATA_CLEANING_AND_TRANSFORMATION_GUIDE.md) | How the raw CSVs are cleaned, how the hierarchy trap is solved with the `counts_in_total` flag, and how 3NF normalization works. |
| [`02_MYSQL_SETUP_AND_INGESTION_GUIDE.md`](./02_MYSQL_SETUP_AND_INGESTION_GUIDE.md) | How the database connects (MySQL via environment variable, SQLite fallback), how the 6 tables are structured, and how data is loaded safely. |
| [`03_EDUCATIONAL_SQL_QUERIES_EXPLAINED.md`](./03_EDUCATIONAL_SQL_QUERIES_EXPLAINED.md) | Line-by-line explanation of every SQL query: weighted averages, joins, and window functions. |
| [`04_EU_AI_ACT_GOVERNANCE_AND_POLICY.md`](./04_EU_AI_ACT_GOVERNANCE_AND_POLICY.md) | The policy angle: High-Risk AI under Annex III, point 4(a)/(b), the Art. 5(1)(f) emotion-recognition ban, worker notice under Art. 26(7), and the obligations a provider or deployer must evidence. |
| [`05_STREAMLIT_DASHBOARD_AND_DEPLOYMENT.md`](./05_STREAMLIT_DASHBOARD_AND_DEPLOYMENT.md) | How the dashboard runs, and how to host it for free on GitHub / Streamlit Community Cloud. |
| [`QUICKSTART_CHEAT_SHEET.md`](./QUICKSTART_CHEAT_SHEET.md) | One-page reference with all terminal commands. |
