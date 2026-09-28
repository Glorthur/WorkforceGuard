# CLAUDE DESIGN BRIEF: WORKFORCEGUARD DASHBOARD REDESIGN
**Executive HR Analytics & Statutory Algorithmic Governance Platform**

---

## 1. Executive Summary & Context

### Project Name:
**WorkforceGuard** — Relational HR Analytics & Algorithmic Governance Cockpit.

### The Objective:
Transform an existing, utilitarian Streamlit data app into a **high-impact, executive-grade, aesthetically sophisticated governance dashboard**. The platform serves Chief Risk Officers (CROs), Chief HR Officers (CHROs), labor economists, and AI compliance auditors who need to evaluate:
1. **Macroeconomic AI Task Exposure** across U.S. industries.
2. **Demographic Public Trust** in AI systems in employment (support by use case; AI vs. humans at treating applicants the same way).
3. **Statutory Classification & Obligations** under the **EU AI Act (Regulation (EU) 2024/1689, Annex III point 4 and Art. 5(1)(f))**, applied to U.S. data as a comparative lens. The dashboard is descriptive and reports no conformity status of its own.

---

## 2. Strict Project Boundaries & Technical Constraints

1. **EXACTLY TWO REAL DATASETS (No Synthetic Data)**:
   - **Dataset A: BLS Industry Employment + Industry AI Task-Exposure Score** (`data/raw/real_bls_industry_ai_exposure.csv`):
     - 355 rows: 18 sector-total rows + 337 industry rows at NAICS levels 3-6, with 2024 covered employment and a 0-10 `weighted_exposure` score.
     - The exposure score's construction method and source are not yet documented, to be cited by the project owner (do not attribute it to BLS or O*NET).
   - **Dataset B: Pew Research Center American Trends Panel Wave 119 microdata** (survey Dec 12-18, 2022):
     - $N = 11,004$ U.S. adults, weighted (`WEIGHT_W119`), converted by `python -m src.data_pipeline.build_pew_w119`.
     - 5 workplace AI use cases: AI Reviewing Job Applications, AI Making Final Hiring Decisions, AI Recording Workers' Computer Activity, AI Deciding Promotions, AI Analyzing Employees' Facial Expressions (favor / oppose / not sure).
     - One hiring item: would AI do better, worse or the same as humans at treating all applicants the same way.
     - 11 cohorts: all U.S. adults plus Gender, Race/Ethnicity and Age groups, each with unweighted n and 95% margin of error.
2. **100% ZERO MACHINE LEARNING**:
   - **NO** predictive models, **NO** scikit-learn training, **NO** synthetic candidate files.
   - All insights are **purely empirical, relational (SQL), and statutory**.
3. **Relational Database Stack**:
   - Optional: **MySQL 8.0**, used only when an environment variable is set (no credentials in code): `MYSQL_DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/workforce_ai_governance` (`WORKFORCEGUARD_DB_URL` is also accepted and checked first).
   - Default / automatic fallback: **SQLite** (`data/workforce_ai.db`), built automatically on first run.
   - Managed through `src/database/connection.py` with `execute_query(sql) -> pd.DataFrame`.
4. **Runtime & Framework**:
   - Streamlit (Python 3.10+ / 3.12).
   - Multi-tab or multi-page layout.

---

## 3. The Relational Data Schema (Third Normal Form - 3NF)

The database consists of 6 relational tables:

```
[dim_naics_sectors] 1 ────< ∞ [fact_industry_exposure]
   (20 sectors)                 (337 industries, NAICS 3-6)

[dim_ai_use_cases] 1 ────< ∞ [fact_pew_survey_responses]
   (5 use cases)                (55 cells = 5 use cases x 11 cohorts)
                                      ^
[dim_demographics] 1 ─────────────────┤
   (11 cohorts)                       │
                                      └── 1:1 [fact_pew_hiring_vs_humans]
                                               (11 cohort rows)
```

### Table Definitions & Key Columns:
(Authoritative definitions: `src/database/schema_3nf.sql`.)
- `dim_naics_sectors`:
  - `sector_code` (VARCHAR(5), PK) — e.g. `'54'`, `'52'`, `'62'`; range sectors `'31-33'`, `'44-45'`, `'48-49'`; government `'90'`.
  - `sector_title` (VARCHAR(255), UNIQUE) — e.g. `'Professional, scientific, and technical services'`.
- `fact_industry_exposure`:
  - `naics_code` (CHAR(6), PK) — 6-digit NAICS code.
  - `parent_sector_code` (VARCHAR(5), FK -> `dim_naics_sectors.sector_code`).
  - `industry_title` (VARCHAR(255)) — Industry name.
  - `naics_level` (SMALLINT) — 3 to 6.
  - `counts_in_total` (SMALLINT, 0/1) — 1 only for rows with no ancestor in the table (92 rows); only these are summed.
  - `covered_employment` (INT) — Workers covered by this row in the file.
  - `weighted_exposure` (DECIMAL(6,4)) — Scale 0.0 to 10.0. Exposure tiers are derived at query time (High >= 7.5, Moderate 5.5-7.5, Low < 5.5), not stored.
- `dim_demographics`:
  - `demographic_id` (INT, PK).
  - `demographic_name` (VARCHAR(80)) — e.g. `'Women'`, `'Black'`, `'Ages 18-29'`, `'Total US Adults'`.
  - `dimension_type` (VARCHAR(32)) — `'Gender'`, `'Race_Ethnicity'`, `'Age'`, `'Overall'`.
  - `unweighted_n` (INT), `moe_pct` (DECIMAL(4,1)) — 95% margin of error, design-effect adjusted.
- `dim_ai_use_cases`:
  - `use_case_id` (INT, PK).
  - `use_case_name` (VARCHAR(150)), `pew_item` (VARCHAR(32)), `pew_question` (VARCHAR(400)).
  - `statutory_risk_tier` (VARCHAR(160)) — `'High-Risk (Annex III, point 4(a))'`, `'High-Risk (Annex III, point 4(b))'` or `'Prohibited where it infers emotions (Art. 5(1)(f))'`.
  - `risk_basis` (VARCHAR(255)) — Statutory citation under the EU AI Act.
- `fact_pew_survey_responses`:
  - `response_id` (INT, PK); `use_case_id` (INT, FK); `demographic_id` (INT, FK); UNIQUE (`use_case_id`, `demographic_id`).
  - `favor_pct`, `oppose_pct`, `not_sure_pct` (DECIMAL(4,1)) — Weighted shares; refusals stay in the base.
- `fact_pew_hiring_vs_humans`:
  - `demographic_id` (INT, PK/FK).
  - `ai_better_pct`, `ai_worse_pct`, `ai_same_pct`, `ai_not_sure_pct` (DECIMAL(4,1)) — Would AI do better / worse / the same as humans at treating all applicants the same way (item `AIWRKH3_b`).

### The "BLS Hierarchy Trap" (Key Quality Guard):
The raw BLS CSV contains 18 sector-total rows and 337 industry rows that mix NAICS levels 3-6, so a level-3 total appears alongside its own sub-industries. Removing only the sector rows is not enough: summing every industry row gives 180.5M "covered workers". WorkforceGuard flags `counts_in_total = 1` on rows with no ancestor in the file and sums only those: **104.1M** covered workers (76.4M removed as double counting). 104.1M is what this file covers, not total U.S. employment.

---

## 4. Why the Current UI Needs a Redesign (Audit of Flaws)

1. **Amateur "Homework Project" Look**:
   - Relies purely on bare Streamlit default styling (raw gray backgrounds, standard red/blue primary accents, no unified design system).
   - No `.streamlit/config.toml` file configured for professional fonts and colors.
2. **Academic & Mechanical Navigation**:
   - Tab titles are named like engineering phases: `"Phase 0: Data Profiling"`, `"Phase 1/2: Macro AI Exposure"`, `"Phase 2: Pew Survey"`, `"Phase 3: Statutory AI Governance"`.
   - Users want executive-oriented, story-driven modules:
     - **Macro Exposure Intelligence**
     - **Workforce Trust & Demographic Disparities**
     - **EU AI Act & Statutory Compliance Cockpit**
     - **Data Provenance & 3NF Integrity Hub**
3. **Clunky Data Tables & Basic Visualizations**:
   - Relies on default `st.dataframe` dumps with unformatted raw numbers instead of `st.column_config` (progress bars, badges, formatted integers).
   - Uses basic `st.bar_chart` horizontal bars with truncated text labels instead of interactive Plotly or Altair charts with informative tooltips and color-coded risk tiers.
   - Demographic fairness perception lacks a **diverging bar chart** (visualizing net skepticism = `% AI would do worse` minus `% AI would do better` than humans at treating applicants the same way; negative = more trust in AI).
4. **Lack of Executive Visual Hierarchy**:
   - KPI metrics use standard `st.metric` without borders, background cards, or sparkline trends.
   - Missing modern Streamlit UI elements: `border=True` containers, `st.segmented_control` / `st.pills` for filtering, Material Symbols icons (`:material/security:`, `:material/trending_up:`, `:material/policy:`).

---

## 5. Exact Brand Identity & Design System (Gloria Arthur / Glorthur)

The design must strictly conform to the user's personal brand identity from:
- **Portfolio**: [glorthur.github.io](https://glorthur.github.io/)
- **Digital Garden**: [The Commonplace Book](https://glorthur.github.io/Digital-Garden/)

### A. Typography Hierarchy
- **Header Font**: `"Source Serif 4"`, serif (Editorial, intellectual, authoritative, established in The Commonplace Book)
- **Body & UI Font**: `"Inter"` / `"Archivo"`, sans-serif (Clean, modern, highly legible)
- **Code & Metric Monospace**: `"IBM Plex Mono"`, monospace

### B. Exact Color Tokens
#### 1. Institutional Dark Theme (Primary - Matching `glorthur.github.io` & Digital Garden Dark):
- **Page Background (`--bg-dark`)**: `#020617` (Deep Obsidian / Midnight Slate)
- **Card / Surface Background (`--bg-card`)**: `#0f172a` (Slate 900 / Deep Navy)
- **Card Hover / Accent Surface (`--bg-card-hover`)**: `#1e293b` (Slate 800)
- **Primary Brand Accent (`--accent`)**: `#2563eb` (Electric Royal Cobalt)
- **Secondary Luminous Accent**: `#7fa2ff` (Soft Periwinkle / Digital Garden Secondary)
- **Text Primary (`--text-primary`)**: `#f8fafc` (Crisp Slate 50)
- **Text Secondary / Muted (`--text-secondary`)**: `#94a3b8` (Slate 400)
- **Borders & Dividers**: `rgba(255, 255, 255, 0.1)` / `#26334f`

#### 2. Editorial Light Theme (Alternative - Matching The Commonplace Book Warm Paper):
- **Page Background**: `#f6f3ec` (Warm Parchment / Alabaster Cream)
- **Card / Border Surface**: `#dedbd3` (Stone Gray)
- **Primary Accent / Ink**: `#020617` (Midnight Ink)
- **Text Dark**: `#1f1b16` (Deep Espresso)
- **Muted Text**: `#423f3a` (Warm Charcoal)

---

## 6. Prompt to Give to Claude

> **Status note:** This brief has been implemented. The current UI is a single editorial HTML page built by `src/ui/editorial_renderer.py` and rendered from `app.py` with `components.html(..., scrolling=True)`; the `src/ui/tab_*.py` modules requested below are retired to `archive/legacy_v1/`.

Copy and paste the following prompt directly into Claude:

```markdown
You are an expert UI/UX designer and principal Streamlit engineer specializing in executive analytics dashboards for C-suite leaders, labor economists, and AI compliance officers.

I have an existing Streamlit project called **WorkforceGuard** that analyzes macroeconomic AI occupational exposure and demographic workplace trust under the EU AI Act. The backend and MySQL database are completely operational, but the current UI looks basic and uninspired.

I want you to redesign the front-end architecture and visual design of the application to look modern, institutional, polished, and executive-ready, **strictly conforming to my personal brand identity from glorthur.github.io and The Commonplace Book (glorthur.github.io/Digital-Garden)**.

### Brand Identity & Design Tokens to Enforce:
1. **Typography**:
   - Header Font: `"Source Serif 4"`, serif
   - Body Font: `"Inter"` or `"Archivo"`, sans-serif
   - Monospace: `"IBM Plex Mono"`
2. **Color Palette (Midnight Slate & Electric Cobalt)**:
   - Background: `#020617` (Deep Obsidian)
   - Secondary / Surface: `#0f172a` (Slate Navy Card)
   - Primary Accent: `#2563eb` (Royal Cobalt)
   - Text Color: `#f8fafc` (Crisp Slate)
   - Muted Text: `#94a3b8` (Muted Slate)
   - Accent Tint / Hover: `#7fa2ff` (Periwinkle Blue)
   - Risk Badges: Crimson (`#ef4444` for High Risk), Amber (`#f59e0b` for Moderate), Emerald (`#10b981` for Low).

### Project & Technical Constraints:
1. **Framework**: Streamlit 1.63. Use modern Streamlit features:
   - `with st.container(border=True):` for visual cards
   - `st.metric(..., border=True)`
   - `st.pills` or `st.segmented_control` for clean filtering
   - Material Symbols icons (`:material/shield:`, `:material/analytics:`, etc.)
   - `st.dataframe(..., column_config=...)` with ProgressColumn and NumberColumn
   - `width="stretch"` (never use deprecated `use_container_width=True`)
2. **Visualizations**: Use clean Altair or Plotly charts with the exact brand palette (`#2563eb`, `#7fa2ff`, `#0f172a`, `#ef4444`, `#10b981`), hover tooltips, and responsive layouts (especially a diverging bar chart for demographic fairness gaps).
3. **Strict Scope**:
   - Exactly two real datasets: BLS industry employment with an industry AI task-exposure score (355 rows; score source not yet documented) and Pew ATP Wave 119 microdata (N=11,004).
   - Zero Machine Learning (no scikit-learn, no training, no predictions). Everything is relational SQL and descriptive analytics.
4. **Database Connection**:
   - Keep existing database connector: `from src.database.connection import execute_query, get_db_type`
   - Keep existing query helpers: `from src.database.queries import get_macro_exposure_summary, get_pew_hiring_vs_humans, get_use_cases_overall, get_statutory_risk_summary`
   - Do not add a conformity score or pass/compliant badge: the dashboard reports no conformity status of its own (the old conformity engine is retired to `archive/legacy_v1/`). Show EU AI Act obligations to evidence instead.

### What I need from you:
1. **`.streamlit/config.toml`**: Brand theme configuration applying the `#020617` / `#0f172a` / `#2563eb` palette and typography.
2. **`app.py`**: A clean entry point with a sleek sidebar, executive hero header, and 4 refined modules:
   - **Tab 1: Macroeconomic AI Exposure Intelligence**
   - **Tab 2: Workforce Trust & Demographic Disparities**
   - **Tab 3: EU AI Act & Statutory Compliance Cockpit**
   - **Tab 4: Data Provenance & 3NF Relational Architecture**
3. **Refactored Tab Modules in `src/ui/`**:
   - `src/ui/tab_macro_exposure.py`
   - `src/ui/tab_pew_survey.py`
   - `src/ui/tab_compliance_policy.py`
   - `src/ui/tab_profiling.py`

Please provide the complete, clean, production-ready Python code and configuration, ensuring each view tells a clear story with hero KPI cards, interactive charts, and rich data tables.
```
