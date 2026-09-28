-- =====================================================================
-- WorkforceGuard: Relational 3NF Database Schema (Two-Dataset Edition)
-- Standardized for MySQL 8.0 & SQLite Dual-Mode
-- Ingestion is a full reload from data/processed/, so tables are rebuilt.
-- =====================================================================

DROP TABLE IF EXISTS fact_pew_hiring_vs_humans;
DROP TABLE IF EXISTS fact_pew_survey_responses;
DROP TABLE IF EXISTS fact_industry_exposure;
DROP TABLE IF EXISTS dim_ai_use_cases;
DROP TABLE IF EXISTS dim_demographics;
DROP TABLE IF EXISTS dim_naics_sectors;

-- Table 1: NAICS Sectors (Lookup Dimension). Range sectors use codes like '31-33'.
CREATE TABLE dim_naics_sectors (
  sector_code VARCHAR(5) PRIMARY KEY,
  sector_title VARCHAR(255) NOT NULL,
  CONSTRAINT uq_sector_title UNIQUE (sector_title)
);

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

-- Table 4: Workplace AI Use Cases (Lookup Dimension with EU AI Act Tiers)
CREATE TABLE dim_ai_use_cases (
  use_case_id INT PRIMARY KEY,
  use_case_name VARCHAR(150) NOT NULL UNIQUE,
  pew_item VARCHAR(32) NOT NULL,
  pew_question VARCHAR(400) NOT NULL,
  statutory_risk_tier VARCHAR(160) NOT NULL,
  risk_basis VARCHAR(255) NOT NULL
);

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

-- Indexes for Analytical Query Acceleration
-- (fact_pew_survey_responses is already indexed by uq_pew_cell.)
CREATE INDEX idx_industry_sector ON fact_industry_exposure (parent_sector_code);
CREATE INDEX idx_industry_exposure ON fact_industry_exposure (weighted_exposure);
CREATE INDEX idx_demographic_type ON dim_demographics (dimension_type);
