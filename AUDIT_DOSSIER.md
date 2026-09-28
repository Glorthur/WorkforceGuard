# WorkforceGuard: Architecture, Data & Governance Audit Dossier

> **Purpose**: Full technical, statistical, regulatory and design context for an independent audit of **WorkforceGuard**.
> **Revision**: v2, 28 Sep 2026. Supersedes v1 after the Sep 2026 audit. Section 8 lists what changed and why. Every figure below is a live output of the current pipeline (`python -m src.database.queries`, `python -m pytest`).

---

## 1. Project Overview & Core Philosophy

**WorkforceGuard** is an AI workforce analytics and statutory governance dashboard. It sets U.S. industry AI exposure and U.S. public opinion on workplace AI against the obligations of the **EU AI Act (Regulation (EU) 2024/1689)**. The EU law is a comparative lens: the Act does not govern the U.S. survey respondents.

### Scope & Constraints
1. **Exactly two datasets**
   - **Dataset 1 (labour)**: `data/raw/real_bls_industry_ai_exposure.csv`. It has 355 rows: 18 sector-total rows plus 337 industry rows at NAICS levels 3–6, with 2024 covered employment. The row structure ("Summary" / "Line Item") follows the BLS National Employment Matrix.
     - ⚠️ **The 0–10 `weighted_exposure` score has no documented source.** BLS and O\*NET do not publish an AI exposure score, and it is not Felten et al.'s AIOE (which is not on a 0–10 scale). Its construction must be cited before publication. The dashboard states this caveat on tab 01.
   - **Dataset 2 (public opinion)**: official **Pew Research Center American Trends Panel Wave 119 microdata** (`data/W119_Dec22.zip`). Fieldwork Dec 12–18, 2022, **N = 11,004** U.S. adults, weight `WEIGHT_W119`.
     - `python -m src.data_pipeline.build_pew_w119` converts it into `data/raw/pew_w119_workplace_ai.csv` and `data/raw/pew_w119_hiring_ai_vs_humans.csv`. This build step needs `pyreadstat`; the app does not.
     - `data/W152_Aug24.zip` (ATP Wave 152, Aug 2024, N = 5,410) is in the repo but **not used**.
2. **Zero-ML constraint**: descriptive SQL, window functions and survey-weighted percentages only. `tests/test_no_ml_guard.py` enforces this.
3. **Dual-mode database**
   - **MySQL 8.0**, used only when `MYSQL_DATABASE_URL` (or `WORKFORCEGUARD_DB_URL`) is set. No credentials live in code.
   - **SQLite** `data/workforce_ai.db` otherwise. It is built automatically on first run.
4. **Design**
   - Editorial dark theme aligned with *The Commonplace Book* (Quartz) and GitHub Dark Dimmed.
   - Palette: `#0d1322`, `#d8deee`, `#8b9bb4`, `#3b4f6e`, `#273244`.
   - Type: Source Serif 4 (editorial), IBM Plex Mono (metrics), Inter (UI).

### Setup
```bash
# Optional: use MySQL instead of the SQLite fallback (PowerShell: $env:MYSQL_DATABASE_URL = "...")
export MYSQL_DATABASE_URL="mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance"
python -m src.data_pipeline.build_pew_w119   # only when the Pew zip changes; needs pyreadstat
python -m src.database.ingest_data           # drops, recreates and reloads all 6 tables
python -m pytest                             # 15 tests
streamlit run app.py
```

---

## 2. Relational Database Architecture (3NF), 6 tables

Source: `src/database/schema_3nf.sql`. Ingest (`src/database/ingest_data.py`) rebuilds the processed CSVs from raw on every run, drops and recreates the tables, and loads them in one transaction.

```
 [dim_naics_sectors]  (20 NAICS sectors)
   sector_code VARCHAR(5) PK      -- range sectors '31-33', '44-45', '48-49'; BLS 999xxx government -> '90'
   sector_title
        │ 1:N  FK parent_sector_code, ON DELETE RESTRICT
        ▼
 [fact_industry_exposure]  (337 industry rows, NAICS levels 3–6)
   naics_code CHAR(6) PK, parent_sector_code FK, industry_title,
   naics_level, counts_in_total (0/1), covered_employment INT,
   weighted_exposure DECIMAL(6,4) CHECK 0–10
   -- no stored tier: tiers depend on weighted_exposure, so they are derived at query time

 [dim_demographics]  (11 cohorts)
   demographic_id PK, demographic_name, dimension_type,
   unweighted_n, moe_pct         -- depend on the cohort alone, so they live here
        │ 1:N                              │ 1:1
        ▼                                  ▼
 [fact_pew_survey_responses]  (55 = 5 × 11)    [fact_pew_hiring_vs_humans]  (11)
   response_id PK, use_case_id FK,               demographic_id PK/FK,
   demographic_id FK,                            ai_better_pct, ai_worse_pct,
   favor_pct, oppose_pct, not_sure_pct           ai_same_pct, ai_not_sure_pct
   UNIQUE (use_case_id, demographic_id)          -- Pew AIWRKH3_b, asked about hiring in general
        ▲ 1:N
 [dim_ai_use_cases]  (5)
   use_case_id PK, use_case_name, pew_item, pew_question,
   statutory_risk_tier, risk_basis
```

### The double-counting trap
- **The problem.** The raw file mixes NAICS levels: a level-3 total (e.g. *Ambulatory healthcare services*, 7.7M) sits next to its own level-4/5 sub-industries.
- **The v1 bug.** v1 removed only the 18 level-2 sector rows, so the fact table still summed totals together with their parts: **180.5M** workers, and **40.3M** in healthcare. v1's "true 135.5M" was a hardcoded HTML string that no query computed.
- **The v2 fix.** The cleaner flags `counts_in_total = 1` on rows with no ancestor in the file (92 rows), and every aggregate filters on it. Result: **104.1M** covered workers, and **20.7M** in healthcare, which matches BLS's own sector row. Summing every row double-counts **76.4M**.
- **Caveat.** 104.1M is what this file covers, not total U.S. employment, because the file omits some industries. Agriculture's level-3 rows sum 6% above BLS's own agriculture row. That is a source quirk, and the regression test tolerates it with 7% slack; a real double count roughly doubles a sector.

---

## 3. Core SQL Analytical Queries (`src/database/queries.py`)

### Query 1: Sector exposure (employment-weighted vs unweighted)
```sql
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
```
**Output**
- **Economy-wide.** Employment-weighted exposure is **5.20 / 10** across **104.1M** workers. The unweighted mean of sector means is 5.50.
- **Most exposed.** Information **7.75**, Finance & insurance **7.65**, Management of companies **7.39**, Professional, scientific & technical **7.38**.
- **Least exposed.** Accommodation & food **2.91**, Construction **3.78**.
- **Largest employer.** Healthcare & social assistance: **20.7M** workers, score **4.44**.

**Tiers** (`QUERY_EMPLOYMENT_BY_TIER`). The cut-points are defined once in `queries.py` (High ≥ 7.5, Moderate 5.5–7.5, Low < 5.5) and used for both the SQL and the UI labels.

| Tier | Workers | Share |
|---|---|---|
| High | 6.9M | **6.6%** |
| Moderate | 34.8M | **33.4%** |
| Low | 62.4M | **60.0%** |

v1's labels said 6.0 / 3.5, which never matched the stored tiers.

### Query 2: AI vs humans in hiring, by cohort (`QUERY_PEW_HIRING_VS_HUMANS`)
Pew item `AIWRKH3_b`: *"Do you think AI would do better, worse or about the same as humans at treating all job applicants in the same way?"*
```sql
SELECT
    d.dimension_type, d.demographic_name, d.unweighted_n, d.moe_pct,
    h.ai_better_pct, h.ai_worse_pct, h.ai_same_pct, h.ai_not_sure_pct,
    ROUND(h.ai_worse_pct - h.ai_better_pct, 1) AS net_skepticism_pp,
    RANK() OVER (
        PARTITION BY d.dimension_type
        ORDER BY (h.ai_worse_pct - h.ai_better_pct) DESC
    ) AS skepticism_rank
FROM fact_pew_hiring_vs_humans AS h
JOIN dim_demographics AS d ON h.demographic_id = d.demographic_id
ORDER BY d.dimension_type, skepticism_rank;
```
Net skepticism = % worse − % better. **Negative values mean more trust in AI.**

| Cohort | Better | Worse | Net (pp) | ±MOE | n |
|---|---|---|---|---|---|
| **All U.S. adults** | **46.8** | **15.4** | **−31.4** | 1.4 | 11,004 |
| Men | 49.2 | 16.7 | −32.5 | 2.2 | 4,884 |
| Women | 44.7 | 14.2 | −30.5 | 1.8 | 5,993 |
| White | 48.5 | 14.8 | −33.7 | 1.7 | 7,220 |
| Black | 37.8 | 16.7 | −21.1 | 3.9 | 1,447 |
| Hispanic | 43.0 | 17.3 | −25.7 | 4.4 | 1,482 |
| Asian | 56.6 | 14.7 | −41.9 | 7.0 | 371 |
| Ages 18–29 | 49.5 | 16.4 | −33.1 | 4.3 | 930 |
| Ages 30–49 | 50.2 | 15.1 | −35.1 | 2.4 | 3,514 |
| Ages 50–64 | 44.2 | 17.0 | −27.2 | 2.5 | 3,157 |
| Ages 65+ | 42.4 | 13.5 | −28.9 | 2.5 | 3,367 |

**Reading**
- Every cohort expects AI to treat applicants more consistently than humans.
- Adults 65+ say "better" less often mainly because more of them are unsure (31.6% vs 17.9% of 18–29s).
- The men/women gap (2 pp) is within the combined margins.
- Asian adults are the most positive, but n = 371 (±7.0).

### Query 3: Support per use case, all adults (`QUERY_USE_CASES_OVERALL`)
Net opposition = % oppose − % favor. Refusals stay in the base, as in Pew's toplines, so rows sum to just under 100.

| Use case | Pew item | Favor | Oppose | Not sure | Net opp. |
|---|---|---|---|---|---|
| AI Reviewing Job Applications | AIWRKH2_a | 27.9 | 41.5 | 30.2 | +13.6 |
| AI Recording Workers' Computer Activity | AIWRKM2_b | 26.7 | 50.8 | 21.7 | +24.1 |
| AI Deciding Promotions | AIWRKM4_a | 22.1 | 47.4 | 29.6 | +25.3 |
| AI Analyzing Employees' Facial Expressions | FACERECWK2_b | 8.8 | 70.4 | 20.2 | +61.6 |
| AI Making Final Hiring Decisions | AIWRKH2_b | 7.1 | 70.9 | 21.6 | +63.8 |

**Headline**: 47% say AI would treat applicants more alike than humans, yet **71% oppose letting AI make the final hiring decision** (7% favor).

### Query 4: Statutory tier aggregation (`QUERY_STATUTORY_AI_RISK_SUMMARY`)
Averages all-adult support within each EU AI Act classification.

| Classification | Use cases | Avg favor | Avg oppose | Avg net opp. |
|---|---|---|---|---|
| Prohibited where it infers emotions (Art. 5(1)(f)) | 1 | 8.8 | 70.4 | +61.6 |
| High-Risk (Annex III, point 4(a)) | 2 | 17.5 | 56.2 | +38.7 |
| High-Risk (Annex III, point 4(b)) | 2 | 24.4 | 49.1 | +24.7 |

### Survey statistics
- Percentages are weighted with `WEIGHT_W119` over all respondents in the cohort.
- Margins of error are 95% for a 50% estimate, using the Kish design effect of the weights in each cohort. The overall ±1.4 is close to Pew's published ±1.5.
- Validation: `tests/test_analytics.py` checks that the microdata reproduces Pew's published toplines (*AI in Hiring and Evaluating Workers*, 20 Apr 2023) within 0.5 pt: 28/41, 7/71, 9/70, 22/47 and 47/15.

---

## 4. Statutory Mapping (Regulation (EU) 2024/1689)

| Use case | Classification | Basis & key obligations |
|---|---|---|
| **AI Reviewing Job Applications** | High-Risk, **Annex III, point 4(a)** | Analysing and filtering applications. Chapter III, Section 2 requirements (Arts. 9–15) for the provider; Art. 26 for the deployer. |
| **AI Making Final Hiring Decisions** | High-Risk, **Annex III, point 4(a)** | Recruitment and selection. Human oversight designed in (Art. 14); affected persons informed (Art. 26(11)); right to explanation (Art. 86). |
| **AI Deciding Promotions** | High-Risk, **Annex III, point 4(b)** | Decisions affecting promotion and other terms of work relationships. |
| **AI Recording Workers' Computer Activity** | High-Risk, **Annex III, point 4(b)** | Monitoring and evaluating performance and behaviour. Workers and their representatives must be informed before use (**Art. 26(7)**). *Not an Art. 50 case.* |
| **AI Analyzing Employees' Facial Expressions** | **Prohibited, Art. 5(1)(f)** | Emotion recognition in the workplace is banned since **2 Feb 2025**, except for medical or safety reasons. Commission guidelines extend "workplace" to recruitment. |

### Cross-cutting points
- **Conformity route.** Annex III point 4 systems use **internal control** (Art. 43(2), Annex VI), with no notified body, and carry CE marking (Art. 48).
- **Logging.** Art. 12 requires automatic logging over the system's lifetime. Keeping logs for at least 6 months comes from Arts. 19 (provider) and 26(6) (deployer). "Tamper-evident" is not a statutory term.
- **Art. 14.** Oversight must be *designed in*, so people can monitor, override or stop the system. Mandatory human sign-off on adverse decisions is good practice, not a statutory rule.
- **Fines.** Up to **€35M or 7%** of worldwide turnover for prohibited practices (Art. 99(3)); **€15M or 3%** for breaching high-risk obligations (Art. 99(4)).
- **Timeline.** The 2026 Digital Omnibus deferred Annex III high-risk obligations from 2 Aug 2026 to **2 Dec 2027**. The Art. 5 bans have applied since 2 Feb 2025, and Art. 50 transparency applies from Aug 2026.

### "Obligations to evidence" panel (tab 03)
- The panel lists what providers and deployers of these systems must be able to show, each with an owner badge:

  | Obligation | Owner |
  |---|---|
  | Art. 9 risk management | Provider |
  | Art. 10 data governance | Provider |
  | Arts. 11–12 documentation & logging | Provider |
  | Arts. 13–14 transparency & oversight | Provider |
  | Art. 15 accuracy/robustness | Provider |
  | Art. 17 QMS | Provider |
  | Art. 26 deployer duties | Deployer |
  | Art. 86 right to explanation | Deployer |

- **WorkforceGuard reports no conformity status of its own.** It is a descriptive dashboard, not a high-risk AI system.
- v1's "PASS · 92/100 / COMPLETE / VERIFIED / 6 of 6 pillars / Compliant" badges were hardcoded strings and have been removed. The unused `eu_ai_act.py` scoring engine is archived.

---

## 5. UI Implementation

A single-page editorial interface: `src/ui/editorial_renderer.py`, rendered by `app.py` through Streamlit `components.html`. The iframe uses `scrolling=True`.

1. **Tabs**
   - `01 Exposure`: sector ranking (weighted bar plus unweighted tick, economy-average line), tier split, most exposed large industries, data-driven marginal notes.
   - `02 Workforce Trust`: a source line naming the Pew W119 microdata and ±MOE. It also shows KPIs, a diverging cohort chart (AI better vs worse than humans) with `All / Gender / Race / Age` filters, a cohort table with ±MOE, and a favor chart for the five use cases.
   - `03 EU AI Act`: support by use case (favor / net opposition) with legal citation and Pew item, and the *Obligations to evidence* panel.
   - `04 Provenance`: the double-counting explanation (104.1M vs 180.5M, computed live), the 6-table directory with live row counts, and the data-quality checks enforced by `tests/`.
2. **Plotly.js** (`plotly-basic-2.35.2`, from cdn.plot.ly)
   - Hover tooltips include n, ±MOE and not-sure shares.
   - PNG export (1400×900 @2x) and a fullscreen modal.
   - A Chart/Table toggle.
   - Window resizing is debounced and redraws only the visible tab.
3. **Hygiene**
   - Database strings are HTML-escaped.
   - The inline JSON escapes `</`.
   - Every headline number and marginal note is computed from the data; none are hardcoded.
   - v1's `postMessage('streamlit:setFrameHeight')` was removed, because Streamlit honours it only for registered custom components.

---

## 6. Automated Test Suite: 15 tests
```bash
python -m pytest        # pytest.ini: testpaths = tests
```
1. **`test_analytics.py`**
   - No sector total exceeds BLS's own sector row (7% slack).
   - The all-rows sum is larger than the counted total.
   - Pew toplines are reproduced within 0.5 pt.
   - Net-skepticism arithmetic is correct.
   - Query 4 has the expected columns.
2. **`test_database.py`**
   - Row counts are 20 / 337 / 11 / 5 / 55 / 11.
   - There are no orphaned foreign keys, and `ON DELETE RESTRICT` holds.
   - **The full dashboard renders on SQLite**, which guards against MySQL-only SQL. The rendered page contains no "Art. 50" and no "135.5M".
3. **`test_data_quality.py`**: PK uniqueness, referential integrity, numeric bounds, no NULLs, and the profiling report.
4. **`test_governance.py`**: each use case's classification (4(a), 4(b), Art. 5(1)(f)), and no Art. 50 mappings.
5. **`test_no_ml_guard.py`**: no ML imports or patterns in `src/` or `app.py`.

---

## 7. Open Items

1. **Exposure score provenance.** Document how `weighted_exposure` was built (source, method, scale) and cite it.
2. **Credentials.** No password is in code or git history; `src/database/` has never been committed. The local MySQL root password was, however, written in plaintext in earlier docs. It is now removed from them; rotate it if those docs were ever shared.
3. **Concurrent agents.** A Codex agent edited `editorial_renderer.py` (the `SECTOR_NAME_MAP` short names) during the audit. Confirm no agent is still writing to the repo, then commit.
4. **Unused data.** Either use `W152_Aug24.zip` (it adds 2024 items such as AI vs humans at "making a hiring decision") or remove it.
5. **Dependencies.** There is no `requirements.txt`. The runtime needs `streamlit`, `pandas`, `sqlalchemy` and `pymysql` (for MySQL); the Pew build step also needs `pyreadstat`.

---

## 8. Changes Since v1 (Sep 2026 Audit)

| Area | v1 | v2 |
|---|---|---|
| Covered workforce | "135.5M" (hardcoded); SQL actually summed 180.5M | **104.1M**, each worker counted once (`counts_in_total`) |
| Healthcare employment | 40.3M (double-counted) | **20.7M** |
| Economy-wide exposure | 5.10 | **5.20** |
| Sectors | "24" (26 in the table), including placeholders such as "Sector 33 Industry Group" | **20 NAICS sectors** (31-33, 44-45, 48-49; 999xxx → 90) |
| Tiers | Labels said 6.0 / 3.5; data used 7.5 / 5.5; share of a double-counted total | Single 7.5 / 5.5 definition; 6.6 / 33.4 / 60.0% |
| Pew data | Hand-typed 15-cell CSV that did not match Pew (e.g. "28% acceptable / 71% unacceptable" combined two different questions; "27% fairer / 47% less fair" reversed Pew's 47% better / 15% worse) | Weighted from **ATP W119 microdata**, 55 + 11 cells, with n and ±MOE. Old file kept at `archive/legacy_v1/data/UNVERIFIED_real_pew_ai_workplace_survey.csv` |
| Trust headline | "Distrust outweighs trust in every group except Asian adults" | Every cohort expects AI to treat applicants more consistently, yet 71% oppose AI making the final hiring decision |
| Surveillance | Art. 50 transparency | **Annex III point 4(b)** high-risk; worker notice under Art. 26(7) |
| Facial/emotion analysis | Annex III 4(a) high-risk | **Prohibited, Art. 5(1)(f)** |
| Fines | €35M / 7% for high-risk breaches | €35M / 7% prohibited (99(3)); **€15M / 3%** high-risk (99(4)) |
| Conformity route | "Third-party audit" | Internal control (Art. 43(2), Annex VI); no notified body |
| Conformity badges | Hardcoded PASS · 92/100, 6/6 pillars | Removed; *Obligations to evidence* panel |
| Timeline | Not stated | Annex III obligations from 2 Dec 2027 (Digital Omnibus) |
| SQLite fallback | Crashed (MySQL-only `ORDER BY FIELD`) | Portable SQL; auto-built database; render test |
| Credentials | Hardcoded root password as the default in `connection.py` | Environment variable only |
| Ingest | DELETE and INSERT in separate transactions | Drop, recreate and load in one transaction |
| Schema | 5 tables; stored `exposure_tier` (not 3NF); `DECIMAL(5,4)` couldn't hold 10.0 | 6 tables; derived tiers; `DECIMAL(6,4)`; n and MOE in the cohort dimension |
| Dead code | About 10 unused tab modules, analytics, governance and core packages | Moved to `archive/legacy_v1/` |
| Tests | 14 tests, including a tautological sum check and one that locked in the Art. 50 error | 15 tests checking against independent references (BLS sector rows, Pew toplines) |

---

## 9. Questions for the Next Audit
1. Is the `counts_in_total` rule (the broadest row present in each NAICS branch) the right unit of aggregation, or should exposure be computed at leaf level and re-weighted?
2. Once its provenance is documented, is the exposure score appropriate for industry-level comparison?
3. Are Kish-deff margins of error sufficient, or should the dashboard use Pew's published design effect or replicate weights?
4. Should the Art. 5(1)(f) classification carry a caveat for facial analysis that does *not* infer emotions (for example, identity verification)?
5. Is the diverging chart's sign convention (negative = trust in AI) intuitive for executive readers?
