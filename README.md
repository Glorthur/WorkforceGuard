# WorkforceGuard

**How exposed is the U.S. workforce to AI, how do Americans feel about AI making decisions at work, and what would the EU AI Act require of those systems?**

WorkforceGuard is a single-page Streamlit dashboard that answers those three questions from two datasets. It is descriptive by design: SQL, window functions and survey-weighted percentages. It has no machine-learning models, and a test enforces that.

## Key findings

- **Exposure is concentrated where employment isn't.** Information (7.75 / 10), finance (7.65) and professional services (7.38) score highest. The largest employer, healthcare and social assistance (20.7M workers), scores 4.44. Employment-weighted exposure across the 104.1M covered workers is **5.20 / 10**.
- **Americans trust AI's consistency but not its authority.** 47% say AI would treat all job applicants more alike than humans do, against 15% who say worse. Yet **71% oppose letting AI make the final hiring decision**, and only 7% favor it. The pattern holds in every gender, race and age cohort surveyed: more say AI would do better than worse, and 59–75% oppose it making the final decision.
- **All five surveyed workplace uses are regulated.**
  - Four are *high-risk* under Annex III, point 4 of the EU AI Act: reviewing applications, final hiring decisions, promotions and monitoring workers' computer activity.
  - The fifth, analysing employees' facial expressions, infers emotions and is **prohibited** under Art. 5(1)(f).

## The dashboard

| Tab | What it shows |
|---|---|
| **01 Exposure** | Sector ranking (employment-weighted vs unweighted), workforce by exposure tier, most exposed large industries |
| **02 Workforce trust** | AI vs humans at treating applicants the same way, by cohort, with ±95% margins of error; support for five workplace AI uses |
| **03 EU AI Act** | Each use case's legal classification alongside public support; the obligations providers and deployers must be able to evidence |
| **04 Provenance** | How the BLS double-counting trap is avoided, the 6-table schema with live row counts, data-quality checks |

The charts use Plotly.js and include hover detail, PNG export, a fullscreen view and a chart/table toggle.

## Quick start

Tested on Python 3.13.

```bash
pip install -r requirements.txt
streamlit run app.py
```

That's all. On first run the app builds a local SQLite database (`data/workforce_ai.db`) from `data/raw/`.

**Optional: use MySQL 8.0 instead.** Set a connection URL before starting. With no URL set, the app uses SQLite.

```bash
# bash
export MYSQL_DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
# PowerShell
$env:MYSQL_DATABASE_URL = "mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"

python -m src.database.ingest_data   # drops, recreates and reloads all tables
```

**Tests** (15):

```bash
python -m pytest
```

## Data

### 1. Industry employment and AI exposure: `data/raw/real_bls_industry_ai_exposure.csv`
- **Contents.** 355 rows: 18 sector totals and 337 industries at NAICS levels 3–6, with 2024 covered employment. The row structure follows the BLS National Employment Matrix.
- **Double counting.** The file mixes hierarchy levels, so a level-3 total sits next to its own sub-industries.
  - Summing every row gives 180.5M workers.
  - WorkforceGuard counts only rows with no parent in the file (`counts_in_total = 1`), which gives **104.1M**.
  - That is the workforce this file covers, not total U.S. employment.
- ⚠️ **The 0–10 exposure score's source is not yet documented.** BLS and O\*NET do not publish an AI exposure score, so treat industry scores as provisional until the method is cited.

### 2. Public opinion: Pew Research Center, American Trends Panel Wave 119
- **Survey.** Fieldwork Dec 12–18, 2022; N = 11,004 U.S. adults.
- **What's in the repo.** `data/raw/pew_w119_workplace_ai.csv` and `data/raw/pew_w119_hiring_ai_vs_humans.csv` are weighted estimates computed from the official microdata with `WEIGHT_W119`. Margins of error use the design effect of the weights.
- **Accuracy check.** The estimates reproduce Pew's published figures, and a test checks this.
- **Rebuilding.** Pew's terms restrict redistributing its microdata, so the `.sav` is not in this repo. To rebuild the CSVs, download the ATP W119 dataset from [pewresearch.org](https://www.pewresearch.org/datasets/), save it as `data/W119_Dec22.zip`, and run:

  ```bash
  pip install pyreadstat
  python -m src.data_pipeline.build_pew_w119
  ```

> Pew Research Center bears no responsibility for the analyses or interpretations of the data presented here.

Other files in `data/raw/` feed the data profiler and archived modules only. The dashboard uses the two datasets above.

## Architecture

```
data/raw/*.csv ──► src/data_pipeline/cleaner.py ──► src/database/ingest_data.py ──► MySQL 8.0 or SQLite
                   (3NF normalization)              (one transaction)                     │
                                                                                          ▼
             app.py ◄── src/ui/editorial_renderer.py ◄── src/database/queries.py (4 analytical queries)
```

**Schema** (`src/database/schema_3nf.sql`), 6 tables in third normal form:
- `dim_naics_sectors` (20 NAICS sectors) → `fact_industry_exposure` (337 industries)
- `dim_demographics` (11 cohorts, with sample size and margin of error)
- `dim_ai_use_cases` (5, with Pew item, question wording and EU AI Act classification)
- `fact_pew_survey_responses` (55 = 5 use cases × 11 cohorts)
- `fact_pew_hiring_vs_humans` (11)

**Queries** (`src/database/queries.py`):
- Employment-weighted vs unweighted sector exposure, and tiers derived at query time.
- Cohort ranking with `RANK() OVER (PARTITION BY …)`.
- Support by use case.
- Support grouped by legal classification.

## EU AI Act mapping

| Surveyed use | Classification under Regulation (EU) 2024/1689 |
|---|---|
| AI reviewing job applications | High-risk: Annex III, point 4(a) |
| AI making final hiring decisions | High-risk: Annex III, point 4(a) |
| AI deciding promotions | High-risk: Annex III, point 4(b) |
| AI recording workers' computer activity | High-risk: Annex III, point 4(b); workers must be informed before use (Art. 26(7)) |
| AI analysing employees' facial expressions | Prohibited where it infers emotions: Art. 5(1)(f), since 2 Feb 2025 |

Annex III obligations apply from **2 December 2027**, as deferred by the 2026 Digital Omnibus. The Act is used here as a comparative lens on U.S. data. WorkforceGuard itself is a descriptive dashboard, not a high-risk AI system, and it reports no conformity status. This is not legal advice.

## Repository layout

```
app.py                     Streamlit entry point
src/data_pipeline/         cleaning, 3NF normalization, Pew microdata build, profiling
src/database/              schema, connection (MySQL / SQLite), ingestion, queries
src/ui/editorial_renderer.py   the dashboard (HTML + Plotly.js)
tests/                     15 tests (pytest)
data/raw/                  source CSVs
archive/                   retired modules and data, kept for reference only
AUDIT_DOSSIER.md           full technical, statistical and regulatory write-up
```

For methodology detail, see [AUDIT_DOSSIER.md](AUDIT_DOSSIER.md). It also records the corrections made after the September 2026 audit.
