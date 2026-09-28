# Step 1: Data Cleaning & 3NF Transformation Guide

This guide explains how we take messy, flat CSVs and transform them into clean, structured tables ready for a database.

---

## 1. Why Do We Clean Data First?

Raw datasets from government portals or surveys often have subtle problems:
* Numbers formatted as text strings (`"$50,000"`, `"12%"`).
* Leading zeros dropped from identification codes (the cleaner zero-pads every NAICS code to 6 characters).
* Repetitive text descriptions repeated thousands of times.
* Mixed levels of summary (e.g., industry totals mixed with their own sub-industries).

Our cleaner script is located at:
👉 [`src/data_pipeline/cleaner.py`](../src/data_pipeline/cleaner.py)

---

## 2. Cleaning Dataset 1: The BLS Hierarchy Trap

### The Problem:
Open `data/raw/real_bls_industry_ai_exposure.csv` and look at these rows:
* `540000, "Professional, scientific, and technical services", naics_level = 2, is_sector = True, covered_employment_2024 = 8,506,500`
* `541000, "Professional, scientific, and technical services", naics_level = 3, is_sector = False, covered_employment_2024 = 8,506,500`
* `541100, "Legal services", naics_level = 4, is_sector = False, covered_employment_2024 = 1,063,000`
* `541500, "Computer systems design and related services", naics_level = 4, is_sector = False, covered_employment_2024 = 1,882,900`

The file has 18 level-2 sector rows, and its 337 industry rows **mix NAICS levels 3-6**. Legal services (`541100`) and computer systems design (`541500`) are **already included** in the level-3 total `541000` — which is itself the same 8.5 million workers as sector `540000`.

The old cleaner removed only the 18 sector rows and summed everything else, so level-3 totals and their own sub-industries were counted together:
```
Sum of all 337 industry rows: 180,466,200 "covered workers" (healthcare alone: 40.3M)
```
(An older dossier also quoted a "135.5M" figure; that was a hardcoded string that no code ever computed.)

### The Solution:
In `cleaner.py`, we split the file into two tables and flag which rows may be summed:
1. **`dim_naics_sectors`**: Takes the rows where `is_sector == True` and stores the **20 NAICS sectors**. Three sectors span several 2-digit prefixes and get range codes: `31-33` Manufacturing, `44-45` Retail trade, `48-49` Transportation and warehousing. BLS codes government excluding education and hospitals as `999xxx`; those rows map to sector `90`. Row `910000` (Federal government) is dropped as a subset of `900000` (Government).
2. **`fact_industry_exposure`**: Takes the 337 rows where `is_sector == False`. Each row gets a Foreign Key `parent_sector_code` (the first two digits of `naics_code`, mapped through the range/government rules above), keeps its `naics_level`, and gets a **`counts_in_total`** flag:
   * `counts_in_total = 1` if no ancestor of the row (at levels 3 and up) is present in the file — 92 rows.
   * `counts_in_total = 0` otherwise, because its workers are already counted in an ancestor row.

The exposure tier (High / Moderate / Low) is **not** stored; it is derived at query time from `weighted_exposure` (High ≥ 7.5, Moderate 5.5–7.5, Low < 5.5, defined once in `src/database/queries.py`).

Now, when you calculate employment, you sum **only rows with `counts_in_total = 1`**, which counts each worker once: **104,054,400 covered workers (104.1M)**, with healthcare at **20.7M**. Summing every row instead would double count 76.4M.

> **Note**: 104.1M is what this file covers, **not** total U.S. employment — the file is incomplete. There are also small source quirks (e.g. agriculture's level-3 rows sum about 6% above BLS's own sector row), which the tests tolerate.

The `weighted_exposure` column is an industry AI task-exposure score (0-10); its construction method and source are not yet documented — to be cited by the project owner.

---

## 3. Cleaning Dataset 2: Pew Survey Normalization

### Where the Pew data comes from:
The Pew raw files are **built from the official ATP Wave 119 microdata** (`data/W119_Dec22.zip`) by:

```powershell
python -m src.data_pipeline.build_pew_w119
```

This step needs `pyreadstat` (`pip install pyreadstat`) and only has to be re-run if the zip is replaced. It writes:
* `data/raw/pew_w119_workplace_ai.csv` — 55 rows (5 use cases x 11 cohorts) with `favor_pct`, `oppose_pct`, `not_sure_pct`.
* `data/raw/pew_w119_hiring_ai_vs_humans.csv` — 11 rows (one per cohort) for item `AIWRKH3_b` with `ai_better_pct`, `ai_worse_pct`, `ai_same_pct`, `ai_not_sure_pct`.

Percentages are weighted with `WEIGHT_W119` over all respondents in the cohort (refusals stay in the base, as in Pew's toplines, so shares sum to slightly under 100). Each cohort also gets its unweighted n and a 95% margin of error for a 50% estimate, using the Kish design effect of the weights.

> The old hand-typed Pew CSV did not match Pew's published figures and was archived to `archive/legacy_v1/data/UNVERIFIED_real_pew_ai_workplace_survey.csv`. It is not used and should not be quoted.

### The Problem:
In `data/raw/pew_w119_workplace_ai.csv`, every row repeats the use-case name, its Pew item and question wording, and the cohort name, sample size and margin of error (`"AI Making Final Hiring Decisions"`, `"Total US Adults"`, etc.).

If you want to query by demographic type (e.g., *"Compare all racial groups"*), you can't, because gender, race, and age are all mixed together in one column.

### The Solution:
We decompose the survey into four clean relational tables:
1. **`dim_demographics`**:
   Assigns a unique ID to each of the 11 cohorts, tags it with a `dimension_type`, and stores the cohort-level `unweighted_n` and `moe_pct` (they depend on the cohort alone):
   * `"Men"`, `"Women"` → `dimension_type = "Gender"`
   * `"White"`, `"Black"`, `"Hispanic"`, `"Asian"` → `dimension_type = "Race_Ethnicity"`
   * `"Ages 18-29"`, `"Ages 30-49"`, etc. → `dimension_type = "Age"`
   * `"Total US Adults"` → `dimension_type = "Overall"`
2. **`dim_ai_use_cases`**:
   Assigns a unique ID to each of the 5 use cases, stores its `pew_item` and `pew_question`, and enriches it with its **EU AI Act** classification (`statutory_risk_tier`, `risk_basis`):
   * *AI Reviewing Job Applications* (`AIWRKH2_a`) and *AI Making Final Hiring Decisions* (`AIWRKH2_b`) → High-Risk (Annex III, point 4(a))
   * *AI Recording Workers' Computer Activity* (`AIWRKM2_b`) and *AI Deciding Promotions* (`AIWRKM4_a`) → High-Risk (Annex III, point 4(b))
   * *AI Analyzing Employees' Facial Expressions* (`FACERECWK2_b`) → Prohibited where it infers emotions (Art. 5(1)(f))
3. **`fact_pew_survey_responses`**:
   Contains only numbers and IDs! It connects `use_case_id` and `demographic_id` to the 3 percentage columns (`favor_pct`, `oppose_pct`, `not_sure_pct`) — 55 rows.
4. **`fact_pew_hiring_vs_humans`**:
   One row per cohort (`demographic_id`) with `ai_better_pct`, `ai_worse_pct`, `ai_same_pct`, `ai_not_sure_pct` — 11 rows. This question was asked about hiring in general, not per use case, so it gets its own table.

---

## 4. How to Run the Cleaner Yourself

From PowerShell in the project directory, run:

```powershell
python -m src.data_pipeline.cleaner
```

**Expected Output:**
```
Cleaned & 3NF normalized tables generated from TWO real datasets:
- dim_naics_sectors: 20 rows, 2 columns
- fact_industry_exposure: 337 rows, 7 columns
- dim_demographics: 11 rows, 5 columns
- dim_ai_use_cases: 5 rows, 6 columns
- fact_pew_survey_responses: 55 rows, 6 columns
- fact_pew_hiring_vs_humans: 11 rows, 5 columns
```

The cleaned tables are saved as clean CSVs inside `data/processed/`. You rarely need to run this by hand: ingestion (`python -m src.database.ingest_data`) rebuilds these tables from the raw files every time.
