# Step 2: MySQL Setup & Database Ingestion Guide

This guide explains how the database connects to Python, how the database schema is defined, and how the tables are populated safely.

---

## 1. How Python Talks to MySQL

We use two standard Python libraries:
* **`SQLAlchemy`**: The industry-standard SQL toolkit and Object Relational Mapper for Python. It manages connections, pools, and SQL dialect translation.
* **`PyMySQL`**: A pure-Python MySQL client library that handles the low-level network communication with your MySQL server on port `3306`.

Our connection manager is located at:
👉 [`src/database/connection.py`](../src/database/connection.py)

### Your MySQL Connection String (via environment variable):
No credentials are hardcoded anywhere in the code. MySQL is used **only if you set an environment variable** holding the connection string:
```
mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance
```
* **`mysql+pymysql`**: The driver to use.
* **`<user>`**: Your MySQL username.
* **`<password>`**: Your MySQL password (never write your real password into docs or code).
* **`localhost:3306`**: Your local computer and default MySQL port.
* **`workforce_ai_governance`**: The database name.

Set it in the same terminal session before running any command:

**PowerShell (Windows):**
```powershell
$env:MYSQL_DATABASE_URL = "mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
```

**bash (macOS / Linux / Git Bash):**
```bash
export MYSQL_DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
```

`connection.py` also accepts `WORKFORCEGUARD_DB_URL`, which is checked first.

### Dual-Mode Fallback:
If neither variable is set, or MySQL cannot be reached (a notice is printed), `connection.py` automatically falls back to a local **SQLite** database (`data/workforce_ai.db`) with foreign keys switched on. If that file does not exist yet (or is empty), it is **built automatically on first run** by running the full ingestion. So you can run everything without installing MySQL at all.

---

## 2. The 3NF Relational Schema (`schema_3nf.sql`)

The database DDL (Data Definition Language) script is located at:
👉 [`src/database/schema_3nf.sql`](../src/database/schema_3nf.sql)

Ingestion is a full reload, so the script first drops all 6 tables (children before parents) and then recreates them. It defines 6 tables with explicit constraints:

### 1. `dim_naics_sectors`
```sql
-- Table 1: NAICS Sectors (Lookup Dimension). Range sectors use codes like '31-33'.
CREATE TABLE dim_naics_sectors (
  sector_code VARCHAR(5) PRIMARY KEY,
  sector_title VARCHAR(255) NOT NULL,
  CONSTRAINT uq_sector_title UNIQUE (sector_title)
);
```

### 2. `fact_industry_exposure`
```sql
-- Table 2: Detailed Industries, NAICS levels 3-6 (Fact Table).
-- counts_in_total = 1 marks rows with no ancestor in the table. Only those may be
-- summed, otherwise a level-3 total and its sub-industries are counted twice.
-- Exposure tiers are derived at query time (they depend on weighted_exposure, not the key).
CREATE TABLE fact_industry_exposure (
  naics_code CHAR(6) PRIMARY KEY,
  parent_sector_code VARCHAR(5) NOT NULL,
  industry_title VARCHAR(255) NOT NULL,
  naics_level SMALLINT NOT NULL,
  counts_in_total SMALLINT NOT NULL,
  covered_employment INT NOT NULL,
  weighted_exposure DECIMAL(6,4) NOT NULL,
  CONSTRAINT fk_industry_sector FOREIGN KEY (parent_sector_code)
    REFERENCES dim_naics_sectors(sector_code) ON DELETE RESTRICT,
  CONSTRAINT ck_industry_employment CHECK (covered_employment >= 0),
  CONSTRAINT ck_exposure_bounds CHECK (weighted_exposure BETWEEN 0 AND 10),
  CONSTRAINT ck_counts_in_total CHECK (counts_in_total IN (0, 1))
);
```
> **Key Feature**: `ON DELETE RESTRICT` guarantees that no one can accidentally delete a parent sector while detailed sub-industries still depend on it!

### 3. `dim_demographics`
```sql
-- Table 3: Demographic Cohorts (Lookup Dimension). Sample size and 95% margin of error
-- (design-effect adjusted) depend on the cohort alone, so they live here.
CREATE TABLE dim_demographics (
  demographic_id INT PRIMARY KEY,
  demographic_name VARCHAR(80) NOT NULL UNIQUE,
  dimension_type VARCHAR(32) NOT NULL,
  unweighted_n INT NOT NULL,
  moe_pct DECIMAL(4,1) NOT NULL,
  CONSTRAINT ck_demo_n CHECK (unweighted_n > 0)
);
```

### 4. `dim_ai_use_cases`
```sql
-- Table 4: Workplace AI Use Cases (Lookup Dimension with EU AI Act Tiers)
CREATE TABLE dim_ai_use_cases (
  use_case_id INT PRIMARY KEY,
  use_case_name VARCHAR(150) NOT NULL UNIQUE,
  pew_item VARCHAR(32) NOT NULL,
  pew_question VARCHAR(400) NOT NULL,
  statutory_risk_tier VARCHAR(160) NOT NULL,
  risk_basis VARCHAR(255) NOT NULL
);
```

### 5. `fact_pew_survey_responses`
```sql
-- Table 5: Pew ATP W119 weighted responses per use case x cohort (Fact Table).
-- Refusals stay in the base, so the three shares sum to slightly under 100.
CREATE TABLE fact_pew_survey_responses (
  response_id INT PRIMARY KEY,
  use_case_id INT NOT NULL,
  demographic_id INT NOT NULL,
  favor_pct DECIMAL(4,1) NOT NULL,
  oppose_pct DECIMAL(4,1) NOT NULL,
  not_sure_pct DECIMAL(4,1) NOT NULL,
  CONSTRAINT uq_pew_cell UNIQUE (use_case_id, demographic_id),
  CONSTRAINT fk_pew_case FOREIGN KEY (use_case_id)
    REFERENCES dim_ai_use_cases(use_case_id) ON DELETE RESTRICT,
  CONSTRAINT fk_pew_demo FOREIGN KEY (demographic_id)
    REFERENCES dim_demographics(demographic_id) ON DELETE RESTRICT,
  CONSTRAINT ck_pew_percentages CHECK (
    favor_pct BETWEEN 0 AND 100 AND oppose_pct BETWEEN 0 AND 100 AND not_sure_pct BETWEEN 0 AND 100
    AND favor_pct + oppose_pct + not_sure_pct <= 100.5
  )
);
```

### 6. `fact_pew_hiring_vs_humans`
```sql
-- Table 6: Would AI do better, worse or the same as humans at treating all job applicants
-- the same way? (Pew item AIWRKH3_b, asked about hiring in general, not per use case.)
CREATE TABLE fact_pew_hiring_vs_humans (
  demographic_id INT PRIMARY KEY,
  ai_better_pct DECIMAL(4,1) NOT NULL,
  ai_worse_pct DECIMAL(4,1) NOT NULL,
  ai_same_pct DECIMAL(4,1) NOT NULL,
  ai_not_sure_pct DECIMAL(4,1) NOT NULL,
  CONSTRAINT fk_hvh_demo FOREIGN KEY (demographic_id)
    REFERENCES dim_demographics(demographic_id) ON DELETE RESTRICT,
  CONSTRAINT ck_hvh_percentages CHECK (
    ai_better_pct + ai_worse_pct + ai_same_pct + ai_not_sure_pct <= 100.5
  )
);
```

### Indexes
```sql
-- Indexes for Analytical Query Acceleration
-- (fact_pew_survey_responses is already indexed by uq_pew_cell.)
CREATE INDEX idx_industry_sector ON fact_industry_exposure (parent_sector_code);
CREATE INDEX idx_industry_exposure ON fact_industry_exposure (weighted_exposure);
CREATE INDEX idx_demographic_type ON dim_demographics (dimension_type);
```

---

## 3. The Ingestion Pipeline (`ingest_data.py`)

Our ingestion script is located at:
👉 [`src/database/ingest_data.py`](../src/database/ingest_data.py)

Every run it:
1. Drops and recreates all 6 tables from `schema_3nf.sql`.
2. Rebuilds the processed tables from the raw CSVs (`clean_and_normalize_datasets()` in `cleaner.py`, which also rewrites `data/processed/`), so they never go stale.
3. Loads all tables **in one transaction**, so a failure never leaves a half-loaded database.
4. Verifies row counts and checks for zero orphaned foreign keys.

### The Dependency Rule:
In relational databases, you **cannot insert a child row before its parent exists**.
* Therefore, each dimension is loaded before the facts that reference it, in this order:
  1. `dim_naics_sectors`
  2. `fact_industry_exposure` (references `dim_naics_sectors`)
  3. `dim_demographics`
  4. `dim_ai_use_cases`
  5. `fact_pew_survey_responses` (references `dim_ai_use_cases` and `dim_demographics`)
  6. `fact_pew_hiring_vs_humans` (references `dim_demographics`)

### How to Run Ingestion:
```powershell
python -m src.database.ingest_data
```

**Expected Output** (the first line says `SQLITE` unless a MySQL URL is set and reachable):
```
Ingesting into MYSQL...
Ingestion complete! Verified row counts for the TWO real datasets:
  - dim_naics_sectors: 20 rows
  - fact_industry_exposure: 337 rows
  - dim_demographics: 11 rows
  - dim_ai_use_cases: 5 rows
  - fact_pew_survey_responses: 55 rows
  - fact_pew_hiring_vs_humans: 11 rows
```
