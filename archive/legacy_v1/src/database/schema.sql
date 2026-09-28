-- =====================================================================
-- WorkforceGuard: MySQL Database Schema
-- Real Macro AI Exposure, Public Survey & Algorithmic Bias Audit Tables
-- =====================================================================

CREATE DATABASE IF NOT EXISTS workforce_ai_governance;
USE workforce_ai_governance;

-- ---------------------------------------------------------------------
-- Table 1: industry_ai_exposure (Macroeconomic BLS/O*NET Data)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS industry_ai_exposure;
CREATE TABLE industry_ai_exposure (
    naics_code VARCHAR(10) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    industry_type VARCHAR(100),
    covered_employment_2024 INT DEFAULT 0,
    weighted_exposure DECIMAL(5, 4) NOT NULL,
    exposure_tier VARCHAR(80) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table 2: pew_workplace_ai_survey (Pew Research Center ATP Wave 119)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS pew_workplace_ai_survey;
CREATE TABLE pew_workplace_ai_survey (
    survey_id INT AUTO_INCREMENT PRIMARY KEY,
    source VARCHAR(80) NOT NULL,
    category VARCHAR(150) NOT NULL,
    demographic_group VARCHAR(80) NOT NULL,
    acceptable_pct DECIMAL(5, 2) NOT NULL,
    unacceptable_pct DECIMAL(5, 2) NOT NULL,
    fairer_than_humans_pct DECIMAL(5, 2) NOT NULL,
    less_fair_pct DECIMAL(5, 2) NOT NULL,
    equal_fairness_pct DECIMAL(5, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- Table 3: candidate_bias_audit_log (Candidate Selection Audit Pool)
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS candidate_bias_audit_log;
CREATE TABLE candidate_bias_audit_log (
    candidate_id VARCHAR(50) PRIMARY KEY,
    department VARCHAR(100) NOT NULL,
    education VARCHAR(50),
    years_experience INT,
    age INT,
    gender VARCHAR(30) NOT NULL,
    ethnicity VARCHAR(80) NOT NULL,
    interview_score DECIMAL(5, 2),
    technical_score DECIMAL(5, 2),
    algorithmic_score DECIMAL(5, 4) NOT NULL,
    selected TINYINT(1) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_gender (gender),
    INDEX idx_ethnicity (ethnicity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
