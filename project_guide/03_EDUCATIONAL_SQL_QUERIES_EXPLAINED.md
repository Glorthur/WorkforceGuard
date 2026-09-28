# Step 3: Educational SQL Queries Explained

All of our analytical queries reside in:
👉 [`src/database/queries.py`](../src/database/queries.py)

Here is a line-by-line explanation of every SQL clause and why it was chosen. The SQL below is copied verbatim from `queries.py`; figures quoted are the current outputs on the rebuilt database.

---

## Query 1: Macro AI Exposure & Employment by Sector

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

### Line-by-Line Breakdown:
1. **`JOIN fact_industry_exposure i ON i.parent_sector_code = s.sector_code`**:
   Connects each industry row to its parent NAICS sector (20 sectors, including the range sectors `31-33`, `44-45`, `48-49` and `90` for government).
2. **`WHERE i.counts_in_total = 1`**:
   **The double-counting guard.** The raw BLS file mixes NAICS levels 3-6, so a level-3 total sits in the same table as its own level-4/5/6 sub-industries. The cleaner sets `counts_in_total = 1` only on rows that have **no ancestor present in the file** (92 of 337 rows); a row whose parent is also in the file is already included in that parent's total. Summing only the flagged rows counts every worker once: **104.1M covered workers** (healthcare 20.7M). Summing every row would give 180.5M — 76.4M workers double counted. Note that 104.1M is what this file covers, not total U.S. employment.
3. **`SUM(covered_employment * weighted_exposure) / NULLIF(SUM(covered_employment), 0)`**:
   **The Employment-Weighted Exposure Formula**:
   * If Industry A has 2,000,000 workers with an exposure of 8.0, and Industry B has 10,000 workers with an exposure of 2.0, a simple `AVG()` would say `(8.0 + 2.0) / 2 = 5.0` (which is misleading).
   * The weighted average multiplies each score by its worker count, giving an accurate representation of labor exposure. Economy-wide this gives **5.20 / 10**, versus 5.50 for the unweighted mean of sector means.
   * `weighted_exposure` is an industry AI task-exposure score (0-10); its construction method and source are not yet documented — to be cited by the project owner.
4. **`NULLIF(..., 0)`**:
   A defensive SQL guard. If a sector has 0 workers, `NULLIF` turns `0` into `NULL`, preventing a `Division by Zero` error.
5. **`GROUP BY s.sector_code, s.sector_title`**:
   Rolls up the 92 counted industry rows into the 20 sectors. Top: Information 7.75, Finance & insurance 7.65; bottom: Accommodation & food services 2.91.

### Companion query: Employment by Exposure Tier (`QUERY_EMPLOYMENT_BY_TIER`)

```sql
SELECT
    CASE
        WHEN weighted_exposure >= {TIER_HIGH_MIN} THEN 'High'
        WHEN weighted_exposure >= {TIER_MODERATE_MIN} THEN 'Moderate'
        ELSE 'Low'
    END AS tier_group,
    SUM(covered_employment) AS total_emp
FROM fact_industry_exposure
WHERE counts_in_total = 1
GROUP BY tier_group;
```

* **Tiers are derived at query time**, not stored — the schema has no tier column. The query is a Python f-string that fills in `TIER_HIGH_MIN = 7.5` and `TIER_MODERATE_MIN = 5.5`, the single source for both the SQL and the UI labels: High ≥ 7.5, Moderate 5.5-7.5, Low < 5.5.
* The same `counts_in_total = 1` filter applies. Result: High 6.9M (6.6%), Moderate 34.8M (33.4%), Low 62.4M (60.0%).

---

## Query 2: AI vs Humans in Hiring, by Cohort (SQL Window Functions)

```sql
SELECT
    d.dimension_type,
    d.demographic_name,
    d.unweighted_n,
    d.moe_pct,
    h.ai_better_pct,
    h.ai_worse_pct,
    h.ai_same_pct,
    h.ai_not_sure_pct,
    ROUND(h.ai_worse_pct - h.ai_better_pct, 1) AS net_skepticism_pp,
    RANK() OVER (
        PARTITION BY d.dimension_type
        ORDER BY (h.ai_worse_pct - h.ai_better_pct) DESC
    ) AS skepticism_rank
FROM fact_pew_hiring_vs_humans AS h
JOIN dim_demographics AS d
    ON h.demographic_id = d.demographic_id
ORDER BY d.dimension_type, skepticism_rank;
```

### Line-by-Line Breakdown:
1. **Data source**: Pew ATP Wave 119 item `AIWRKH3_b` — would AI do better, worse, or about the same as humans at treating all job applicants in the same way? Weighted percentages per cohort, built from Pew's microdata.
2. **`h.ai_worse_pct - h.ai_better_pct AS net_skepticism_pp`**:
   Calculates **Net Skepticism** = % worse − % better. A **negative** number means the cohort has **more trust in AI** than in humans on this question. All U.S. adults: 46.8% better, 15.4% worse → **−31.4 pp**. Every cohort is negative.
3. **`d.unweighted_n, d.moe_pct`**:
   Sample size and 95% margin of error (including the design effect of the weights) from `dim_demographics`, so small cohorts are read with caution — e.g. Asian adults (n = 371, ±7.0).
4. **`RANK() OVER (PARTITION BY ... ORDER BY ...)`**:
   **A Window Function**:
   * `PARTITION BY d.dimension_type`: Ranks cohorts against others in the same dimension (all age groups against each other, then all racial/ethnic groups, and so on).
   * `ORDER BY (worse - better) DESC`: Assigns Rank `1` to the least-trusting cohort in each dimension (e.g. Black adults, −21.1, among race/ethnicity).
   * Unlike `GROUP BY`, window functions **do not collapse rows**—every individual demographic group remains visible!

---

## Query 3: Public Support by Use Case (All U.S. Adults)

```sql
SELECT
    u.use_case_name,
    u.pew_item,
    u.pew_question,
    u.statutory_risk_tier,
    u.risk_basis,
    r.favor_pct,
    r.oppose_pct,
    r.not_sure_pct,
    ROUND(r.oppose_pct - r.favor_pct, 1) AS net_opposition_pp
FROM fact_pew_survey_responses AS r
JOIN dim_ai_use_cases AS u ON r.use_case_id = u.use_case_id
JOIN dim_demographics AS d ON r.demographic_id = d.demographic_id
WHERE d.dimension_type = 'Overall'
ORDER BY r.favor_pct DESC;
```

### Line-by-Line Breakdown:
1. **`WHERE d.dimension_type = 'Overall'`**: Keeps only the "Total US Adults" row for each of the 5 use cases.
2. **`r.oppose_pct - r.favor_pct AS net_opposition_pp`**: **Net Opposition** = % oppose − % favor. Positive means more Americans oppose than favor. It ranges from +13.6 (AI Reviewing Job Applications, 27.9 favor / 41.5 oppose) to +63.8 (AI Making Final Hiring Decisions, 7.1 favor / 70.9 oppose).
3. **`u.statutory_risk_tier, u.risk_basis`**: Carries each use case's EU AI Act classification next to the public opinion figures.

---

## Query 4: Statutory AI Risk Summary (EU AI Act)

```sql
SELECT
    u.statutory_risk_tier,
    COUNT(DISTINCT u.use_case_id) AS use_case_count,
    ROUND(AVG(r.favor_pct), 1) AS avg_favor_pct,
    ROUND(AVG(r.oppose_pct), 1) AS avg_oppose_pct,
    ROUND(AVG(r.oppose_pct - r.favor_pct), 1) AS avg_net_opposition_pp
FROM fact_pew_survey_responses AS r
JOIN dim_ai_use_cases AS u ON r.use_case_id = u.use_case_id
JOIN dim_demographics AS d ON r.demographic_id = d.demographic_id
WHERE d.dimension_type = 'Overall'
GROUP BY u.statutory_risk_tier
ORDER BY avg_net_opposition_pp DESC;
```

### What This Tells Us:
It compares how the American public feels about workplace AI grouped by its EU AI Act classification (a comparative lens — the Act does not apply to U.S. respondents):
* **Prohibited where it infers emotions (Art. 5(1)(f))** — 1 use case (facial expressions): average net opposition **+61.6 pp** (8.8 favor / 70.4 oppose).
* **High-Risk (Annex III, point 4(a))** — recruitment, 2 use cases: **+38.7 pp** (17.5 favor / 56.2 oppose).
* **High-Risk (Annex III, point 4(b))** — work relationships (monitoring, promotions), 2 use cases: **+24.7 pp** (24.4 favor / 49.1 oppose).

---

## How to Test Queries in Python
```powershell
python -m src.database.queries
```
This prints Queries 1, 2 and 4 against whichever database is active (SQLite by default, MySQL if `MYSQL_DATABASE_URL` is set).
