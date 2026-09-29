"""
WorkforceGuard Editorial HTML Generator.
Generates an understated, human-crafted publication-grade executive interface with
full interactive Plotly charts, hover tooltips, PNG image export, and fullscreen expansion.
Palette: Strictly matte, muted, dignified slate grays and quiet deep blues.
Zero neon, zero glowing electric colors, zero rainbow tones.
Typography: Source Serif 4 (Editorial), IBM Plex Mono (Financial Tabular), Inter (UI).
"""
import json
from html import escape
import pandas as pd
from src.database.connection import execute_query, get_db_type
from src.database.queries import (
    QUERY_EMPLOYMENT_BY_TIER,
    TIER_HIGH_MIN,
    TIER_MODERATE_MIN,
    get_macro_exposure_summary,
    get_pew_hiring_vs_humans,
    get_use_cases_overall,
)

def fmt_emp(val):
    if val is None or pd.isna(val):
        return "0"
    val = float(val)
    if val >= 1e6:
        return f"{val / 1e6:.1f}M"
    elif val >= 1e3:
        return f"{int(round(val / 1e3))}K"
    return str(int(val))

def to_js(obj) -> str:
    """JSON for inline <script>; escapes '</' so data can never close the tag."""
    return json.dumps(obj).replace("</", "<\\/")

def marginalia_html(notes) -> str:
    items = "".join(
        f'<div class="marginalia-item"><span class="marginalia-num">{i}</span>'
        f'<p class="marginalia-p">{escape(n)}</p></div>'
        for i, n in enumerate(notes, 1)
    )
    return f'<div class="marginalia-box"><div class="marginalia-title">Marginalia</div>{items}</div>'

PEW_SOURCE_HTML = (
    '<div style="border-left:2px solid #3d5270;padding:4px 12px;margin:0 0 18px;font-size:12px;color:#8b9bb4;line-height:1.55;">'
    'Weighted estimates computed from Pew Research Center American Trends Panel Wave 119 microdata '
    '(Dec 12&ndash;18, 2022; N = 11,004), using WEIGHT_W119. &plusmn; values are 95% margins of error '
    'for each cohort; differences smaller than the combined margins are not statistically meaningful.</div>'
)

# (article, what must be evidenced, who owes it) - Regulation (EU) 2024/1689
OBLIGATIONS = [
    ("Art. 9 · Risk management system", "Continuous, documented identification and mitigation of risks", "Provider"),
    ("Art. 10 · Data &amp; data governance", "Training, validation and test data examined for possible biases", "Provider"),
    ("Art. 11–12 · Documentation &amp; logging", "Annex IV technical file; automatic event logs over the system&rsquo;s lifetime", "Provider"),
    ("Art. 13–14 · Transparency &amp; human oversight", "Instructions for use; designed so people can monitor, override or stop it", "Provider"),
    ("Art. 15 · Accuracy, robustness, cybersecurity", "Declared accuracy levels; resilience to errors and attacks", "Provider"),
    ("Art. 17 · Quality management system", "Documented policies, procedures and post-market monitoring", "Provider"),
    ("Art. 26 · Deployer duties", "Use per instructions, trained human overseers, keep logs ≥ 6 months, inform workers before use (26(7))", "Deployer"),
    ("Art. 86 · Right to explanation", "Affected persons may request an explanation of decisions based on the system&rsquo;s output", "Deployer"),
]

OBLIGATIONS_HTML = (
    '<h2 class="section-h2">Obligations to evidence</h2>'
    '<div style="font-size:11.5px;color:#64748b;line-height:1.5;">What providers and deployers of these high-risk systems '
    'must be able to show. WorkforceGuard is a descriptive dashboard, not a high-risk AI system, so it reports no '
    'conformity status of its own.</div>'
    '<div style="display:flex;flex-direction:column;border-top:1px solid #1c2638;">'
    + "".join(
        '<div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;gap:12px;">'
        f'<div><div style="font-size:13px;color:#b0bccd;font-weight:500;">{art}</div>'
        f'<div style="font-size:11.5px;color:#64748b;">{what}</div></div>'
        f'<span class="badge-status">{who.upper()}</span></div>'
        for art, what, who in OBLIGATIONS
    )
    + '</div>'
)

EU_NOTES = [
    "Annex III, point 4 covers AI for recruitment and selection (4(a)) and for decisions on promotion, termination, "
    "task allocation, and monitoring or evaluating workers' performance and behaviour (4(b)).",
    "Emotion recognition in the workplace, including recruitment, is prohibited under Art. 5(1)(f) except for medical "
    "or safety reasons. Employers must inform workers and their representatives before using high-risk AI (Art. 26(7)).",
    "Fines reach €35M or 7% of worldwide turnover for prohibited practices (Art. 99(3)) and €15M or 3% for breaching "
    "high-risk obligations (Art. 99(4)).",
    "Annex III obligations apply from 2 December 2027, as deferred by the 2026 Digital Omnibus; the Art. 5 bans have "
    "applied since 2 February 2025.",
]

def build_editorial_html() -> str:
    db_type = get_db_type().upper()

    # 1. Macro Exposure Data
    df_sec = get_macro_exposure_summary()
    SECTOR_NAME_MAP = {
        "52": "Finance & insurance",
        "51": "Information",
        "55": "Management of companies",
        "54": "Professional & technical services",
        "42": "Wholesale trade",
        "44-45": "Retail trade",
        "61": "Educational services",
        "31-33": "Manufacturing",
        "90": "Government (excl. education & hospitals)",
        "53": "Real estate, rental & leasing",
        "22": "Utilities",
        "48-49": "Transportation & warehousing",
        "56": "Administrative & support services",
        "21": "Mining, quarrying, oil & gas",
        "81": "Other services",
        "71": "Arts, entertainment & recreation",
        "11": "Agriculture, forestry & fishing",
        "62": "Healthcare & social assistance",
        "23": "Construction",
        "72": "Accommodation & food services"
    }
    df_sec["sector_title"] = df_sec["sector_code"].map(SECTOR_NAME_MAP).fillna(df_sec["sector_title"])
    total_emp = float(df_sec["detailed_employment"].sum())
    wtd_avg = float((df_sec["detailed_employment"] * df_sec["employment_weighted_exposure"]).sum() / total_emp)
    unwtd_mean = float(df_sec["unweighted_mean_exposure"].mean())
    top_sec = df_sec.iloc[0]
    total_industries = int(df_sec["detailed_industry_count"].sum())

    sql_large = """
    SELECT industry_title, covered_employment, weighted_exposure
    FROM fact_industry_exposure
    WHERE covered_employment >= 250000
    ORDER BY weighted_exposure DESC
    LIMIT 6;
    """
    df_large = execute_query(sql_large)

    tier_emp = dict(execute_query(QUERY_EMPLOYMENT_BY_TIER).values.tolist())
    high_emp = float(tier_emp.get("High", 0))
    mod_emp = float(tier_emp.get("Moderate", 0))
    low_emp = float(tier_emp.get("Low", 0))
    high_pct = int(round(high_emp / total_emp * 100)) if total_emp > 0 else 0
    mod_pct = int(round(mod_emp / total_emp * 100)) if total_emp > 0 else 0
    low_pct = int(round(low_emp / total_emp * 100)) if total_emp > 0 else 0
    tier_high_label = f"Score >= {TIER_HIGH_MIN}"
    tier_mod_label = f"{TIER_MODERATE_MIN} <= Score < {TIER_HIGH_MIN}"
    tier_low_label = f"Score < {TIER_MODERATE_MIN}"

    # Double-counting illustration: every industry row summed vs each worker counted once
    naive_emp = float(execute_query("SELECT SUM(covered_employment) FROM fact_industry_exposure").iloc[0, 0])
    overlap_emp = naive_emp - total_emp

    # Exposure marginalia, computed from the data
    sec_diff = df_sec["employment_weighted_exposure"] - df_sec["unweighted_mean_exposure"]
    i_w = sec_diff.abs().idxmax()
    widest_name, widest_diff = df_sec.at[i_w, "sector_title"], float(sec_diff[i_w])
    largest = df_sec.loc[df_sec["detailed_employment"].idxmax()]
    single_industry = df_sec.loc[df_sec["detailed_industry_count"] == 1, "sector_title"].tolist()
    exposure_notes = [
        f"Weighting matters most in {widest_name}, where the employment-weighted score sits "
        f"{abs(widest_diff):.2f} {'below' if widest_diff < 0 else 'above'} the unweighted mean.",
        f"{largest['sector_title']} employs the most covered workers, {fmt_emp(largest['detailed_employment'])}, "
        f"and scores {largest['employment_weighted_exposure']:.2f}, "
        f"{'below' if largest['employment_weighted_exposure'] < wtd_avg else 'above'} the economy-wide {wtd_avg:.2f}.",
    ]
    if single_industry:
        names = single_industry[0] if len(single_industry) == 1 else ", ".join(single_industry[:-1]) + " and " + single_industry[-1]
        exposure_notes.append(f"{names} each map to one counted industry, so their weighted and unweighted scores match.")
    exposure_notes.append(
        "About the score: a language model rated each of 342 BLS occupations from 0 to 10 using a fixed rubric "
        "(Karpathy, 2026). Industry scores average those ratings by employment. They are best read as relative "
        "rankings, not precise measurements."
    )
    exposure_notes.append(
        f"Coverage: the {total_emp / 1e6:.1f}M workers are the jobs in those rated occupations, each counted once, "
        "so the total sits below overall U.S. employment."
    )

    # 2. Pew Data (ATP W119 microdata)
    df_cases_all = get_use_cases_overall()
    final_row = df_cases_all[df_cases_all["pew_item"] == "AIWRKH2_b"]
    df_pew = get_pew_hiring_vs_humans()
    overall = df_pew[df_pew["dimension_type"] == "Overall"]
    if final_row.empty or overall.empty:
        raise ValueError("Pew tables are missing the all-adult rows for hiring")
    overall = overall.iloc[0]
    h_fav = int(round(final_row.iloc[0]["favor_pct"]))
    h_opp = int(round(final_row.iloc[0]["oppose_pct"]))
    h_better = int(round(overall["ai_better_pct"]))
    h_worse = int(round(overall["ai_worse_pct"]))
    h_gap = int(round(overall["net_skepticism_pp"]))

    cohorts = df_pew[df_pew["dimension_type"] != "Overall"]
    row_by = {r["demographic_name"]: r for _, r in df_pew.iterrows()}
    gap_spread = int(round(cohorts["net_skepticism_pp"].max() - cohorts["net_skepticism_pp"].min())) if not cohorts.empty else 0
    scope = "every cohort" if (cohorts["net_skepticism_pp"] < 0).all() else "most cohorts"
    pew_hero = (f"Americans in {scope} expect AI to treat job applicants more consistently than humans, "
                f"<em>yet {h_opp}% oppose letting it make the final hiring decision</em>.")

    trust_notes = []
    if "Ages 18-29" in row_by and "Ages 65+" in row_by:
        young, old = row_by["Ages 18-29"], row_by["Ages 65+"]
        trust_notes.append(f"Adults 65+ are the least likely to say AI would do better ({old['ai_better_pct']:.0f}% vs. "
                           f"{young['ai_better_pct']:.0f}% of adults 18-29), mostly because more are unsure "
                           f"({old['ai_not_sure_pct']:.0f}% vs. {young['ai_not_sure_pct']:.0f}%).")
    if "Women" in row_by and "Men" in row_by:
        w, m = row_by["Women"], row_by["Men"]
        trust_notes.append(f"Net skepticism: women {w['net_skepticism_pp']:+.0f} pp, men {m['net_skepticism_pp']:+.0f} pp "
                           f"(margins ±{w['moe_pct']:.1f} and ±{m['moe_pct']:.1f} points).")
    if not cohorts.empty:
        top = cohorts.loc[cohorts["ai_better_pct"].idxmax()]
        trust_notes.append(f"{top['demographic_name']} adults are the most likely to say AI would do better "
                           f"({top['ai_better_pct']:.0f}%), but with n = {int(top['unweighted_n']):,} the margin of "
                           f"error is ±{top['moe_pct']:.1f} points.")
    trust_notes.append("AI used in hiring is high-risk under Annex III, point 4(a): providers must build in logging "
                       "(Art. 12) and human oversight (Art. 14); deployers must run it under trained human oversight (Art. 26).")

    grid = "grid-template-columns: minmax(96px, 150px) minmax(120px, 1fr) 38px 38px 46px 46px; gap: 0 10px;"
    mono = "font-family:'IBM Plex Mono',monospace;font-size:12px;text-align:right;"
    ref_left = 50 + h_gap / 1.2

    def cohort_row(r, cls, label, extra_style=""):
        gap = float(r["net_skepticism_pp"])
        return f"""
            <div class="row-item cohort-row {cls}" style="{grid}{extra_style}">
              <span style="font-size:13px;color:#b0bccd;">{escape(label)}</span>
              <div class="diverge-track">
                <div class="diverge-midline"></div>
                <div class="diverge-refline" style="left:{ref_left:.1f}%;"></div>
                <div class="diverge-left" style="width:{float(r['ai_better_pct']) / 1.2:.1f}%;"></div>
                <div class="diverge-right" style="width:{float(r['ai_worse_pct']) / 1.2:.1f}%;"></div>
              </div>
              <span style="{mono}color:#8b9bb4;">{float(r['ai_better_pct']):.0f}%</span>
              <span style="{mono}color:#8b9bb4;">{float(r['ai_worse_pct']):.0f}%</span>
              <span style="{mono}color:{'#d8deee' if gap >= 0 else '#8b9bb4'};">{gap:+.0f}</span>
              <span style="{mono}color:#64748b;">±{float(r['moe_pct']):.1f}</span>
            </div>"""

    cohort_rows_html = "".join(
        cohort_row(r, "cohort-all", "Total U.S. adults", " border-bottom: 1px solid #1c2638;")
        for _, r in df_pew[df_pew["dimension_type"] == "Overall"].iterrows()
    )
    for dim, key, title in [("Gender", "gender", "Gender"), ("Race_Ethnicity", "race", "Race / ethnicity"), ("Age", "age", "Age")]:
        group = df_pew[df_pew["dimension_type"] == dim].sort_values("skepticism_rank")
        if group.empty:
            continue
        cohort_rows_html += (f'<div class="cohort-header cohort-{key} cohort-all" style="padding:12px 0 4px;'
                             f"font-family:'Source Serif 4',serif;font-style:italic;font-size:13px;color:#64748b;\">{title}</div>")
        for _, r in group.iterrows():
            cohort_rows_html += cohort_row(r, f"cohort-{key} cohort-all", r["demographic_name"].replace("-", "–"))

    # 3. EU AI Act Data (support per use case, all adults)
    eu_avg_fav = float(df_cases_all["favor_pct"].mean())
    eu_avg_netopp = float(df_cases_all["net_opposition_pp"].mean())

    # 4. Provenance Data
    count_sec = execute_query("SELECT COUNT(*) FROM dim_naics_sectors").iloc[0, 0]
    count_ind = execute_query("SELECT COUNT(*) FROM fact_industry_exposure").iloc[0, 0]
    count_demo = execute_query("SELECT COUNT(*) FROM dim_demographics").iloc[0, 0]
    count_cases = execute_query("SELECT COUNT(*) FROM dim_ai_use_cases").iloc[0, 0]
    count_cells = execute_query("SELECT COUNT(*) FROM fact_pew_survey_responses").iloc[0, 0]

    # Prepare JSON payloads for client-side interactive Plotly charts
    sec_chart_data = []
    # Reverse order for horizontal bar so highest is at top
    for _, s in df_sec.iloc[::-1].iterrows():
        emp = float(s["detailed_employment"])
        sec_chart_data.append({
            "sector": s["sector_title"],
            "weighted": round(float(s["employment_weighted_exposure"]), 2),
            "unweighted": round(float(s["unweighted_mean_exposure"]), 2),
            "emp_str": fmt_emp(emp),
            "emp_num": emp,
            "industries": int(s["detailed_industry_count"]),
            "diff": round(float(s["employment_weighted_exposure"]) - float(s["unweighted_mean_exposure"]), 2)
        })
    sec_json = to_js(sec_chart_data)

    pew_chart_data = []
    # Order cohorts logically: Overall -> Gender -> Race -> Age
    dim_order = {"Overall": 0, "Gender": 1, "Race_Ethnicity": 2, "Age": 3}
    pew_sorted = df_pew.assign(dim_rank=df_pew["dimension_type"].map(lambda x: dim_order.get(x, 99)))
    pew_sorted = pew_sorted.sort_values(by=["dim_rank", "skepticism_rank"], ascending=[False, True])

    for _, r in pew_sorted.iterrows():
        dim = r["dimension_type"]
        pew_chart_data.append({
            "cohort": r["demographic_name"],
            "dim": "Race / ethnicity" if dim == "Race_Ethnicity" else dim,
            "dim_key": {"Overall": "all", "Gender": "gender", "Race_Ethnicity": "race"}.get(dim, "age"),
            "better": float(r["ai_better_pct"]),
            "worse": float(r["ai_worse_pct"]),
            "same": float(r["ai_same_pct"]),
            "notsure": float(r["ai_not_sure_pct"]),
            "gap": float(r["net_skepticism_pp"]),
            "moe": float(r["moe_pct"]),
            "n": int(r["unweighted_n"]),
        })
    pew_json = to_js(pew_chart_data)

    cases_chart_data = [
        {"name": c["use_case_name"], "tier": c["statutory_risk_tier"], "basis": c["risk_basis"],
         "favor": float(c["favor_pct"]), "netopp": float(c["net_opposition_pp"])}
        for _, c in df_cases_all.iterrows()
    ]
    cases_json = to_js(cases_chart_data)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400;1,8..60,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<script src="https://cdn.plot.ly/plotly-basic-2.35.2.min.js"></script>
<style>
* {{
  box-sizing: border-box;
}}
html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  background: #0d1322;
  color: #94a3b8;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  font-variant-numeric: tabular-nums;
  overflow-x: hidden;
}}

/* Responsive Container */
.container {{
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 32px;
}}
@media (max-width: 768px) {{
  .container {{ padding: 0 16px; }}
}}

/* Header */
header {{
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px 24px;
  padding: 24px 0 18px;
  border-bottom: 1px solid #1c2638;
}}
.brand {{
  display: flex;
  align-items: baseline;
  gap: 14px;
  flex-wrap: wrap;
}}
.wordmark {{
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 24px;
  font-weight: 600;
  color: #d8deee;
  letter-spacing: -0.01em;
}}
.wordmark em {{
  font-weight: 400;
  font-style: italic;
  color: #a2b0c3;
}}
.subwordmark {{
  font-family: 'Source Serif 4', Georgia, serif;
  font-style: italic;
  font-size: 14px;
  color: #64748b;
}}
nav {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
}}
.nav-tab {{
  cursor: pointer;
  display: flex;
  align-items: baseline;
  gap: 7px;
  font-size: 13.5px;
  color: #8b9bb4;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  padding-bottom: 6px;
  transition: all 0.15s ease;
}}
.nav-tab:hover {{
  color: #d8deee;
}}
.nav-tab.active {{
  color: #d8deee;
  border-bottom-color: #64748b;
}}
.nav-num {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  color: #64748b;
}}
.nav-tab.active .nav-num {{
  color: #8b9bb4;
}}

/* Hero Section */
.hero-sec {{
  display: flex;
  flex-wrap: wrap;
  gap: 18px 40px;
  padding: 34px 0 24px;
  align-items: flex-end;
}}
.hero-left {{
  flex: 999 1 540px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}}
.eyebrow {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: #64748b;
}}
.hero-title {{
  margin: 0;
  font-family: 'Source Serif 4', Georgia, serif;
  font-weight: 400;
  font-size: clamp(22px, 2.4vw, 32px);
  line-height: 1.25;
  letter-spacing: -0.012em;
  color: #d8deee;
  text-wrap: balance;
}}
.hero-title em {{
  font-style: italic;
  color: #a2b0c3;
}}
.hero-desc {{
  flex: 1 1 300px;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #8b9bb4;
  text-wrap: pretty;
}}
.hero-desc em {{
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 14.5px;
  color: #b0bccd;
}}

/* Hairline Responsive KPI Strip */
.kpi-strip {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1px;
  background: #1c2638;
  border-top: 1px solid #1c2638;
  border-bottom: 1px solid #1c2638;
  margin-bottom: 28px;
}}
.kpi-cell {{
  padding: 14px 16px;
  background: #0d1322;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}}
.kpi-val {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: clamp(18px, 1.8vw, 22px);
  color: #d8deee;
  letter-spacing: -0.01em;
  font-weight: 500;
  white-space: nowrap;
}}
.kpi-unit {{
  font-size: 12px;
  color: #64748b;
  margin-left: 3px;
}}
.kpi-label {{
  font-size: 12px;
  line-height: 1.35;
  color: #8b9bb4;
}}

/* Main Responsive Flex Layout */
.main-grid {{
  display: flex;
  flex-wrap: wrap;
  gap: 36px;
  padding-bottom: 28px;
}}
.main-left {{
  flex: 999 1 620px;
  min-width: 0;
  display: flex;
  flex-direction: column;
}}
.main-right {{
  flex: 1 1 340px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 28px;
}}

/* Section Headings & Interactive Toolbars */
.section-h2-wrap {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 12px;
  padding-bottom: 12px;
}}
.section-h2 {{
  white-space: nowrap;
  margin: 0;
  font-family: 'Source Serif 4', Georgia, serif;
  font-weight: 600;
  font-size: 17px;
  color: #d8deee;
}}
.section-sub {{
  font-family: 'Source Serif 4', Georgia, serif;
  font-style: italic;
  font-size: 13.5px;
  color: #64748b;
}}

.chart-header-actions {{
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}}
.btn-action {{
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #1c2638;
  color: #8b9bb4;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}}
.btn-action:hover {{
  background: rgba(255, 255, 255, 0.08);
  color: #d8deee;
  border-color: #334155;
}}
.view-toggle {{
  display: inline-flex;
  border: 1px solid #1c2638;
  border-radius: 3px;
  overflow: hidden;
}}
.view-toggle-btn {{
  background: transparent;
  border: none;
  color: #64748b;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  padding: 3px 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}}
.view-toggle-btn.active {{
  background: #1c2638;
  color: #d8deee;
}}

/* Responsive Table Grid Classes */
.table-header {{
  display: grid;
  align-items: center;
  padding: 8px 0;
  border-top: 1px solid #1c2638;
  border-bottom: 1px solid #1c2638;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: #64748b;
}}
.row-item {{
  display: grid;
  align-items: center;
  padding: 7px 0;
  border-bottom: 1px solid #141d2d;
  transition: background 0.1s ease;
}}
.row-item:hover {{
  background: rgba(255, 255, 255, 0.015);
}}

/* Fluid Bar Chart Track */
.bar-track {{
  position: relative;
  height: 10px;
  width: 100%;
  min-width: 60px;
}}
.bar-fill {{
  position: absolute;
  left: 0;
  top: 0;
  height: 10px;
  background: #3b4f6e;
  border-radius: 1px;
}}
.bar-tick {{
  position: absolute;
  top: -3px;
  height: 16px;
  width: 2px;
  background: #8b9bb4;
  z-index: 2;
}}
.bar-baseline {{
  position: absolute;
  top: -6px;
  bottom: -6px;
  border-left: 1px dotted #334155;
  z-index: 1;
}}

/* Diverging Chart Elements */
.diverge-track {{
  position: relative;
  height: 10px;
  width: 100%;
  min-width: 70px;
}}
.diverge-midline {{
  position: absolute;
  left: 50%;
  top: -6px;
  bottom: -6px;
  width: 1px;
  background: #233044;
}}
.diverge-refline {{
  position: absolute;
  top: -6px;
  bottom: -6px;
  border-left: 1px dotted #334155;
}}
.diverge-left {{
  position: absolute;
  right: 50%;
  top: 0;
  height: 10px;
  background: #3d5270;
  border-radius: 1px 0 0 1px;
}}
.diverge-right {{
  position: absolute;
  left: 50%;
  top: 0;
  height: 10px;
  background: #273244;
  border-radius: 0 1px 1px 0;
}}

/* Marginalia Box */
.marginalia-box {{
  display: flex;
  flex-direction: column;
  gap: 14px;
  border-top: 1px solid #1c2638;
  padding-top: 16px;
}}
.marginalia-title {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10px;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: #64748b;
}}
.marginalia-item {{
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  gap: 8px;
}}
.marginalia-num {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: #8b9bb4;
  padding-top: 2px;
}}
.marginalia-p {{
  margin: 0;
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 13.5px;
  line-height: 1.55;
  color: #94a3b8;
}}

/* Filter Pills */
.pill-wrap {{
  display: flex;
  gap: 14px;
  font-size: 12px;
}}
.pill-btn {{
  cursor: pointer;
  color: #64748b;
  border-bottom: 1px solid transparent;
  padding-bottom: 2px;
  white-space: nowrap;
  transition: all 0.15s ease;
}}
.pill-btn:hover {{
  color: #a2b0c3;
}}
.pill-btn.active {{
  color: #d8deee;
  border-bottom-color: #64748b;
}}

/* Badges */
.badge-status {{
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: #8b9bb4;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid #233044;
  padding: 2px 7px;
  border-radius: 2px;
  letter-spacing: 0.04em;
  white-space: nowrap;
}}

/* Expand Fullscreen Modal */
.expand-modal {{
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(13, 19, 34, 0.94);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  z-index: 999999;
  justify-content: center;
  align-items: center;
  padding: 24px;
}}
.expand-modal.active {{
  display: flex;
}}
.modal-card {{
  width: 92vw;
  max-width: 1200px;
  height: 85vh;
  background: #0d1322;
  border: 1px solid #233044;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
}}
.modal-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #1c2638;
  padding-bottom: 14px;
  margin-bottom: 16px;
}}
.modal-title {{
  margin: 0;
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 18px;
  color: #d8deee;
  font-weight: 600;
}}
.btn-modal-close {{
  background: transparent;
  border: 1px solid #1c2638;
  color: #8b9bb4;
  font-size: 14px;
  width: 28px;
  height: 28px;
  border-radius: 3px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}}
.btn-modal-close:hover {{
  color: #d8deee;
  border-color: #334155;
  background: rgba(255, 255, 255, 0.05);
}}

footer {{
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px 24px;
  margin-top: 32px;
  padding: 14px 0 28px;
  border-top: 1px solid #1c2638;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: #56657a;
}}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

/* Responsive Breakpoints */
@media (max-width: 900px) {{
  .main-grid {{
    flex-direction: column;
  }}
  .main-right {{
    width: 100%;
  }}
}}
@media (max-width: 640px) {{
  .kpi-strip {{
    grid-template-columns: repeat(2, 1fr);
  }}
  .hero-sec {{
    padding: 20px 0 14px;
  }}
  .table-header, .row-item {{
    font-size: 11.5px;
  }}
}}
</style>
</head>
<body>

<div class="container">
  <!-- Minimalist Master Header -->
  <header>
    <div class="brand">
      <div class="wordmark">Workforce<em>Guard</em></div>
      <div class="subwordmark">Governance brief, in four parts</div>
    </div>
    <nav>
      <div class="nav-tab active" id="btn-tab-0" onclick="showTab(0)"><span class="nav-num">01</span>Exposure</div>
      <div class="nav-tab" id="btn-tab-1" onclick="showTab(1)"><span class="nav-num">02</span>Workforce trust</div>
      <div class="nav-tab" id="btn-tab-2" onclick="showTab(2)"><span class="nav-num">03</span>EU AI Act</div>
      <div class="nav-tab" id="btn-tab-3" onclick="showTab(3)"><span class="nav-num">04</span>Provenance</div>
    </nav>
  </header>

  <!-- ==================== TAB 01: EXPOSURE ==================== -->
  <div class="tab-content active" id="tab-0">
    <section class="hero-sec">
      <div class="hero-left">
        <div class="eyebrow">01 · Macroeconomic AI exposure intelligence</div>
        <h1 class="hero-title">Finance, information and professional services carry the most AI exposure; <em>the largest employers carry the least</em>.</h1>
      </div>
      <p class="hero-desc"><em>Exposure</em> (0–10) estimates how much of an industry&rsquo;s work today&rsquo;s AI could perform or speed up, based on AI ratings of 342 occupations weighted by 2024 employment.</p>
    </section>

    <section class="kpi-strip">
      <div class="kpi-cell">
        <div class="kpi-val">{total_emp / 1e6:.1f}<span class="kpi-unit">M</span></div>
        <div class="kpi-label">covered workers</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{wtd_avg:.2f}<span class="kpi-unit">/10</span></div>
        <div class="kpi-label">economy-wide, weighted</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{unwtd_mean:.2f}<span class="kpi-unit">/10</span></div>
        <div class="kpi-label">unweighted mean</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{high_pct}%</div>
        <div class="kpi-label">in high-exposure industries</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{top_sec['employment_weighted_exposure']:.2f}</div>
        <div class="kpi-label">highest sector score ({top_sec['sector_title'][:14]}...)</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{total_industries}</div>
        <div class="kpi-label">industries counted</div>
      </div>
    </section>

    <div class="main-grid">
      <!-- Left Column: Sectors Interactive Chart / Table -->
      <div class="main-left">
        <div class="section-h2-wrap">
          <div style="display:flex;align-items:baseline;gap:6px 12px;flex-wrap:wrap;">
            <h2 class="section-h2">Sector exposure ranking</h2>
            <span class="section-sub">{len(df_sec)} NAICS sectors, employment-weighted</span>
          </div>
          <div class="chart-header-actions">
            <div class="view-toggle">
              <button class="view-toggle-btn active" id="btn-toggle-sec-chart" onclick="toggleSecView('chart')">Chart</button>
              <button class="view-toggle-btn" id="btn-toggle-sec-table" onclick="toggleSecView('table')">Table</button>
            </div>
            <button class="btn-action" onclick="downloadChartPNG('chart-sector-exposure', 'workforce_sector_exposure')" title="Download publication-grade PNG">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              PNG
            </button>
            <button class="btn-action" onclick="expandChart('chart-sector-exposure', 'Sector Exposure Ranking (0–10)')" title="Expand to fullscreen">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path></svg>
              Expand
            </button>
          </div>
        </div>

        <!-- Interactive Plotly Chart View -->
        <div id="sec-chart-view" style="width:100%;height:740px;margin-bottom:12px;">
          <div id="chart-sector-exposure" style="width:100%;height:100%;"></div>
        </div>

        <!-- Tabular Fallback View -->
        <div id="sec-table-view" style="display:none;width:100%;">
          <div class="table-header" style="grid-template-columns: minmax(130px, 240px) minmax(100px, 1fr) 42px 42px 52px; gap: 0 10px;">
            <span>Sector</span><span>Exposure, 0–10</span><span style="text-align:right;">Wtd</span><span style="text-align:right;">Mean</span><span style="text-align:right;">Jobs</span>
          </div>
"""

    for _, s in df_sec.iterrows():
        name = s["sector_title"]
        w = float(s["employment_weighted_exposure"])
        u = float(s["unweighted_mean_exposure"])
        emp_str = fmt_emp(s["detailed_employment"])
        bar_w = min(100.0, w * 10.0)
        tick_pos = min(100.0, u * 10.0)
        
        html += f"""
          <div class="row-item" style="grid-template-columns: minmax(130px, 240px) minmax(100px, 1fr) 42px 42px 52px; gap: 0 10px;">
            <span style="font-size:13px;color:#b0bccd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{escape(name)}</span>
            <div class="bar-track">
              <div class="bar-baseline" style="left:51%;"></div>
              <div class="bar-fill" style="width:{bar_w:.1f}%;"></div>
              <div class="bar-tick" style="left:{tick_pos:.1f}%;"></div>
            </div>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{w:.2f}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#64748b;text-align:right;">{u:.2f}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{emp_str}</span>
          </div>
        """

    html += f"""
        </div>
        <div style="margin-top:8px;font-size:11.5px;color:#64748b;line-height:1.5;">Bar: employment-weighted score. Tick: unweighted mean of sector industries. Dotted line: economy-wide weighted average ({wtd_avg:.2f}). Hover any bar for detailed metrics.</div>
      </div>

      <!-- Right Column: Tier & Large Industries & Marginalia -->
      <aside class="main-right">
        <!-- Tier Distribution -->
        <div style="display:flex;flex-direction:column;gap:12px;">
          <div class="section-h2-wrap">
            <h2 class="section-h2">Workforce by exposure tier</h2>
            <button class="btn-action" onclick="downloadChartPNG('chart-tier-distribution', 'workforce_tier_distribution')" title="Download PNG">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              PNG
            </button>
          </div>
          <div id="chart-tier-distribution" style="width:100%;height:44px;"></div>
          <div style="display:flex;flex-direction:column;border-top:1px solid #1c2638;">
            <div style="display:grid;grid-template-columns:10px minmax(0,1fr) 56px 44px;gap:0 10px;align-items:center;padding:7px 0;border-bottom:1px solid #141d2d;">
              <i style="width:6px;height:6px;background:#3d5270;display:inline-block;border-radius:1px;"></i>
              <span style="font-size:13px;color:#b0bccd;">High exposure</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{fmt_emp(high_emp)}</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{high_pct}%</span>
            </div>
            <div style="display:grid;grid-template-columns:10px minmax(0,1fr) 56px 44px;gap:0 10px;align-items:center;padding:7px 0;border-bottom:1px solid #141d2d;">
              <i style="width:6px;height:6px;background:#4b5a70;display:inline-block;border-radius:1px;"></i>
              <span style="font-size:13px;color:#b0bccd;">Moderate exposure</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{fmt_emp(mod_emp)}</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{mod_pct}%</span>
            </div>
            <div style="display:grid;grid-template-columns:10px minmax(0,1fr) 56px 44px;gap:0 10px;align-items:center;padding:7px 0;border-bottom:1px solid #141d2d;">
              <i style="width:6px;height:6px;background:#273244;display:inline-block;border-radius:1px;"></i>
              <span style="font-size:13px;color:#b0bccd;">Low exposure</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{fmt_emp(low_emp)}</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{low_pct}%</span>
            </div>
          </div>
        </div>

        <!-- Most Exposed Large Industries -->
        <div style="display:flex;flex-direction:column;">
          <div class="section-h2-wrap">
            <h2 class="section-h2">Most exposed large industries</h2>
            <span class="section-sub">250,000+ workers</span>
          </div>
          <div class="table-header" style="grid-template-columns: minmax(0, 1fr) 52px 40px; gap: 0 10px;">
            <span>Industry</span><span style="text-align:right;">Jobs</span><span style="text-align:right;">Exp.</span>
          </div>
    """

    for _, l in df_large.iterrows():
        html += f"""
          <div class="row-item" style="grid-template-columns: minmax(0, 1fr) 52px 40px; gap: 0 10px;">
            <span style="font-size:13px;color:#b0bccd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{escape(l['industry_title'])}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{fmt_emp(l['covered_employment'])}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{float(l['weighted_exposure']):.2f}</span>
          </div>
        """

    html += f"""
        </div>

        <!-- Marginalia -->
        {marginalia_html(exposure_notes)}
      </aside>
    </div>
  </div>

  <!-- ==================== TAB 02: WORKFORCE TRUST ==================== -->
  <div class="tab-content" id="tab-1">
    <section class="hero-sec">
      <div class="hero-left">
        <div class="eyebrow">02 · Workforce trust &amp; demographic disparities</div>
        <h1 class="hero-title">{pew_hero}</h1>
      </div>
      <p class="hero-desc"><em>Net skepticism</em> is the share who say AI would do worse than humans at treating all job applicants the same way, minus the share who say it would do better. Negative values mean more trust in AI; the rest said about the same or were not sure.</p>
    </section>
    {PEW_SOURCE_HTML}

    <section class="kpi-strip">
      <div class="kpi-cell">
        <div class="kpi-val">{h_fav}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">favor AI making final hiring decisions</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{h_opp}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">oppose it</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{h_better}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">say AI would treat applicants more alike</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{h_worse}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">say AI would do worse</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{h_gap:+d}<span class="kpi-unit">pp</span></div>
        <div class="kpi-label">net skepticism</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{gap_spread}<span class="kpi-unit">pp</span></div>
        <div class="kpi-label">spread across cohorts</div>
      </div>
    </section>

    <div class="main-grid">
      <!-- Left Column: Diverging Interactive Chart / Table -->
      <div class="main-left">
        <div class="section-h2-wrap">
          <div style="display:flex;align-items:baseline;gap:6px 12px;flex-wrap:wrap;">
            <h2 class="section-h2">AI vs. humans in hiring, by cohort</h2>
            <span class="section-sub">Treating applicants the same way</span>
          </div>
          <div class="chart-header-actions">
            <div class="pill-wrap">
              <span class="pill-btn active" id="pill-all" onclick="filterCohort('all')">All</span>
              <span class="pill-btn" id="pill-gender" onclick="filterCohort('gender')">Gender</span>
              <span class="pill-btn" id="pill-race" onclick="filterCohort('race')">Race</span>
              <span class="pill-btn" id="pill-age" onclick="filterCohort('age')">Age</span>
            </div>
            <div class="view-toggle">
              <button class="view-toggle-btn active" id="btn-toggle-cohort-chart" onclick="toggleCohortView('chart')">Chart</button>
              <button class="view-toggle-btn" id="btn-toggle-cohort-table" onclick="toggleCohortView('table')">Table</button>
            </div>
            <button class="btn-action" onclick="downloadChartPNG('chart-cohort-diverging', 'workforce_pew_fairness_by_cohort')" title="Download publication-grade PNG">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              PNG
            </button>
            <button class="btn-action" onclick="expandChart('chart-cohort-diverging', 'AI vs Humans at Treating Applicants the Same (Pew ATP W119)')" title="Expand to fullscreen">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path></svg>
              Expand
            </button>
          </div>
        </div>

        <!-- Interactive Diverging Plotly Chart -->
        <div id="cohort-chart-view" style="width:100%;height:490px;margin-bottom:12px;">
          <div id="chart-cohort-diverging" style="width:100%;height:100%;"></div>
        </div>

        <!-- Tabular Fallback View -->
        <div id="cohort-table-view" style="display:none;width:100%;">
          <div class="table-header" style="grid-template-columns: minmax(96px, 150px) minmax(120px, 1fr) 38px 38px 46px 46px; gap: 0 10px;">
            <span>Cohort</span>
            <span style="display:flex;justify-content:space-between;"><span>← AI better</span><span>AI worse →</span></span>
            <span style="text-align:right;">Better</span><span style="text-align:right;">Worse</span><span style="text-align:right;">Net</span><span style="text-align:right;">±MoE</span>
          </div>

          <div id="cohort-rows">{cohort_rows_html}
          </div>
        </div>

        <div style="margin-top:8px;font-size:11.5px;color:#64748b;line-height:1.5;">Left bar: % say AI would do better than humans. Right bar: % say AI would do worse. Dotted line: total U.S. adults baseline ({h_gap:+d} pp). Hover for cohort detail.</div>
      </div>

      <!-- Right Column: Five Use Cases & Marginalia -->
      <aside class="main-right">
        <div style="display:flex;flex-direction:column;">
          <div class="section-h2-wrap">
            <h2 class="section-h2">Five use cases</h2>
            <button class="btn-action" onclick="downloadChartPNG('chart-use-cases', 'workforce_five_use_cases')" title="Download PNG">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              PNG
            </button>
          </div>
          <div id="chart-use-cases" style="width:100%;height:220px;margin-bottom:8px;"></div>
        </div>

        <!-- Marginalia -->
        {marginalia_html(trust_notes)}
      </aside>
    </div>
  </div>

  <!-- ==================== TAB 03: EU AI ACT ==================== -->
  <div class="tab-content" id="tab-2">
    <section class="hero-sec">
      <div class="hero-left">
        <div class="eyebrow">03 · Statutory AI governance &amp; EU AI Act cockpit</div>
        <h1 class="hero-title">Four of the five surveyed workplace uses are Annex III high-risk; <em>the fifth, reading employees&rsquo; facial expressions, is banned outright</em>.</h1>
      </div>
      <p class="hero-desc">Regulation (EU) 2024/1689 classifies AI used in recruitment, promotion and worker monitoring as high-risk (Annex III, point 4). Those obligations apply from 2 December 2027, as deferred by the 2026 Digital Omnibus; the Art. 5 bans have applied since 2 February 2025.</p>
    </section>

    <section class="kpi-strip">
      <div class="kpi-cell">
        <div class="kpi-val">Annex III<span class="kpi-unit">pt. 4</span></div>
        <div class="kpi-label">statutory classification</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{count_cases}</div>
        <div class="kpi-label">surveyed use cases mapped</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{eu_avg_fav:.1f}<span class="kpi-unit">%</span></div>
        <div class="kpi-label">avg share in favor</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{eu_avg_netopp:+.1f}<span class="kpi-unit">pp</span></div>
        <div class="kpi-label">avg net opposition</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">2 Dec<span class="kpi-unit">2027</span></div>
        <div class="kpi-label">Annex III obligations apply</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">Art. 5</div>
        <div class="kpi-label">bans emotion inference at work</div>
      </div>
    </section>

    <div class="main-grid">
      <!-- Left Column: Use Case Classification Table & Download -->
      <div class="main-left">
        <div class="section-h2-wrap">
          <div style="display:flex;align-items:baseline;gap:6px 12px;flex-wrap:wrap;">
            <h2 class="section-h2">Statutory classification of surveyed AI systems</h2>
            <span class="section-sub">Regulation (EU) 2024/1689, Annex III point 4 &amp; Art. 5(1)(f)</span>
          </div>
          <div class="chart-header-actions">
            <button class="btn-action" onclick="downloadChartPNG('chart-statutory-risk', 'eu_ai_act_risk_matrix')" title="Download PNG">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
              PNG
            </button>
            <button class="btn-action" onclick="expandChart('chart-statutory-risk', 'Statutory Risk vs Public Support')" title="Expand to fullscreen">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path></svg>
              Expand
            </button>
          </div>
        </div>

        <!-- Interactive Statutory Chart -->
        <div id="chart-statutory-risk" style="width:100%;height:220px;margin-bottom:14px;"></div>

        <div class="table-header" style="grid-template-columns: minmax(140px, 260px) minmax(120px, 1fr) 46px 46px; gap: 0 10px;">
          <span>Workplace Application</span><span>Legal Citation &amp; Scope</span><span style="text-align:right;">Favor</span><span style="text-align:right;">Net opp.</span>
        </div>
"""

    for _, c in df_cases_all.iterrows():
        tier_label = c['statutory_risk_tier']
        html += f"""
        <div class="row-item" style="grid-template-columns: minmax(140px, 260px) minmax(120px, 1fr) 46px 46px; gap: 0 10px; padding: 10px 0;">
          <div style="display:flex;flex-direction:column;gap:3px;min-width:0;">
            <span style="font-size:13px;color:#b0bccd;font-weight:500;">{escape(c['use_case_name'])}</span>
            <span style="font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#64748b;">{escape(tier_label)} · Pew {escape(c['pew_item'])}</span>
          </div>
          <span style="font-size:12px;color:#7e8f9f;line-height:1.4;">{escape(c['risk_basis'])}</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b9bb4;text-align:right;">{int(round(c['favor_pct']))}%</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{int(round(c['net_opposition_pp'])):+d}</span>
        </div>
        """

    html += f"""
        <div style="margin-top:12px;font-size:11.5px;color:#64748b;line-height:1.5;">Net opp.: % oppose minus % favor among all U.S. adults (Pew ATP W119). Annex III point 4 systems follow the internal-control conformity route (Art. 43(2), Annex VI; no notified body) and carry CE marking (Art. 48).</div>
      </div>

      <!-- Right Column: Mandatory 6 Pillars & Marginalia -->
      <aside class="main-right">
        <div style="display:flex;flex-direction:column;gap:12px;">
          {OBLIGATIONS_HTML}
        </div>

        <!-- Marginalia -->
        {marginalia_html(EU_NOTES)}
      </aside>
    </div>
  </div>

  <!-- ==================== TAB 04: PROVENANCE ==================== -->
  <div class="tab-content" id="tab-3">
    <section class="hero-sec">
      <div class="hero-left">
        <div class="eyebrow">04 · Data provenance &amp; 3NF relational architecture</div>
        <h1 class="hero-title">Counting each worker once <em>removes {fmt_emp(overlap_emp)} of double-counted employment</em>.</h1>
      </div>
      <p class="hero-desc">WorkforceGuard normalizes BLS industry employment and exposure data and Pew ATP Wave 119 microdata into a strict Third Normal Form (3NF) relational architecture, verified by automated integrity gates.</p>
    </section>

    <section class="kpi-strip">
      <div class="kpi-cell">
        <div class="kpi-val">6</div>
        <div class="kpi-label">3NF relational tables</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{count_ind}</div>
        <div class="kpi-label">industry rows (NAICS 3–6)</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{count_sec}</div>
        <div class="kpi-label">parent NAICS sectors</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{count_demo}</div>
        <div class="kpi-label">demographic cohorts</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">{total_industries}</div>
        <div class="kpi-label">rows counted in totals</div>
      </div>
      <div class="kpi-cell">
        <div class="kpi-val">0</div>
        <div class="kpi-label">predictive models</div>
      </div>
    </section>

    <div class="main-grid">
      <!-- Left Column: Hierarchy Trap & Schema -->
      <div class="main-left">
        <div class="section-h2-wrap">
          <div style="display:flex;align-items:baseline;gap:6px 12px;flex-wrap:wrap;">
            <h2 class="section-h2">The BLS hierarchy double-counting trap</h2>
            <span class="section-sub">Summary rows vs. their own sub-industries</span>
          </div>
        </div>
        <div style="background:rgba(255,255,255,0.015);border:1px solid #1c2638;padding:16px 20px;margin-bottom:24px;border-radius:2px;">
          <div style="font-size:13.5px;color:#b0bccd;font-weight:500;margin-bottom:6px;">Why normalization is mathematically mandatory:</div>
          <div style="font-size:12.5px;color:#8c9bb0;line-height:1.6;">
            The raw BLS file mixes NAICS levels: sector totals plus {count_ind} industry rows at levels 3–6, where a level-3 total such as Ambulatory healthcare services appears alongside its own sub-industries. Summing every industry row gives <strong>{fmt_emp(naive_emp)}</strong>; counting only rows with no parent in the file gives <strong>{fmt_emp(total_emp)}</strong>. The file does not cover every industry, so this is below total U.S. employment.
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:28px;margin-top:14px;padding-top:12px;border-top:1px solid #1c2638;">
            <div>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:18px;color:#8b9bb4;font-weight:500;">{fmt_emp(naive_emp)}</span>
              <div style=\"font-size:11px;color:#64748b;\">Every row summed (double-counts)</div>
            </div>
            <div>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:18px;color:#d8deee;font-weight:500;">{fmt_emp(total_emp)}</span>
              <div style=\"font-size:11px;color:#64748b;\">Each worker counted once</div>
            </div>
            <div>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:18px;color:#64748b;font-weight:500;">{fmt_emp(overlap_emp)}</span>
              <div style=\"font-size:11px;color:#64748b;\">Double-counted</div>
            </div>
          </div>
        </div>

        <div class="section-h2-wrap">
          <h2 class="section-h2">Relational 3NF table directory</h2>
          <span class="section-sub">Engine: {db_type}</span>
        </div>
        <div class="table-header" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span>Table Name</span><span>Type</span><span>Analytical Purpose</span><span style="text-align:right;">Rows</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">dim_naics_sectors</span>
          <span style="font-size:12px;color:#64748b;">Dimension</span>
          <span style="font-size:12px;color:#8c9bb0;">NAICS sectors (Primary Key: sector_code)</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{count_sec}</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">fact_industry_exposure</span>
          <span style="font-size:12px;color:#64748b;">Fact</span>
          <span style="font-size:12px;color:#8c9bb0;">Industries at NAICS levels 3–6, flagged counts_in_total (FK -&gt; dim_naics_sectors)</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{count_ind}</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">dim_demographics</span>
          <span style="font-size:12px;color:#64748b;">Dimension</span>
          <span style="font-size:12px;color:#8c9bb0;">Cohorts with unweighted n and 95% margin of error</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{count_demo}</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">dim_ai_use_cases</span>
          <span style="font-size:12px;color:#64748b;">Dimension</span>
          <span style="font-size:12px;color:#8c9bb0;">Workplace AI applications with EU AI Act classification</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{count_cases}</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">fact_pew_survey_responses</span>
          <span style="font-size:12px;color:#64748b;">Fact</span>
          <span style="font-size:12px;color:#8c9bb0;">Weighted favor / oppose / not sure, use case × cohort (Pew ATP W119)</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{count_cells}</span>
        </div>
        <div class="row-item" style="grid-template-columns: minmax(130px, 200px) 70px minmax(0, 1fr) 52px; gap: 0 10px;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#b0bccd;">fact_pew_hiring_vs_humans</span>
          <span style="font-size:12px;color:#64748b;">Fact</span>
          <span style="font-size:12px;color:#8c9bb0;">AI vs humans at treating applicants the same, per cohort</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#d8deee;text-align:right;">{len(df_pew)}</span>
        </div>
      </div>

      <!-- Right Column: Automated Quality Gates -->
      <aside class="main-right">
        <div style="display:flex;flex-direction:column;gap:12px;">
          <h2 class="section-h2">Automated data quality gates</h2>
          <div style="display:flex;flex-direction:column;border-top:1px solid #1c2638;">
            <div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;color:#b0bccd;font-weight:500;">Primary Key Uniqueness</div>
                <div style="font-size:11.5px;color:#64748b;">0 duplicate keys across all 6 tables</div>
              </div>
              <span class="badge-status">TESTED</span>
            </div>
            <div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;color:#b0bccd;font-weight:500;">Referential Integrity</div>
                <div style="font-size:11.5px;color:#64748b;">0 orphaned foreign keys (ON DELETE RESTRICT)</div>
              </div>
              <span class="badge-status">TESTED</span>
            </div>
            <div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;color:#b0bccd;font-weight:500;">Numerical Bounds</div>
                <div style="font-size:11.5px;color:#64748b;">Exposure in [0, 10]; percentages in [0, 100]</div>
              </div>
              <span class="badge-status">TESTED</span>
            </div>
            <div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;color:#b0bccd;font-weight:500;">Null Integrity</div>
                <div style="font-size:11.5px;color:#64748b;">0 unhandled NULLs in required analytical columns</div>
              </div>
              <span class="badge-status">TESTED</span>
            </div>
            <div style="padding:9px 0;border-bottom:1px solid #141d2d;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;color:#b0bccd;font-weight:500;">Zero-ML Guard</div>
                <div style="font-size:11.5px;color:#64748b;">100% absence of predictive models or ML training</div>
              </div>
              <span class="badge-status">TESTED</span>
            </div>
          </div>
        </div>

        <!-- Marginalia -->
        <div class="marginalia-box">
          <div class="marginalia-title">Marginalia</div>
          <div class="marginalia-item">
            <span class="marginalia-num">1</span>
            <p class="marginalia-p">Uneven age brackets (18–29, 30–49, 50–64, 65+) reflect Pew and Census career stages rather than statistical binning errors.</p>
          </div>
          <div class="marginalia-item">
            <span class="marginalia-num">2</span>
            <p class="marginalia-p">Legacy predictive models (archive/legacy_models/) and retired modules and data (archive/legacy_v1/) are kept out of the runtime.</p>
          </div>
        </div>
      </aside>
    </div>
  </div>

  <!-- Footnote -->
  <footer>
    <span id="foot-source">Employment: BLS National Employment Matrix, 2024 · Exposure ratings: Karpathy (2026), github.com/karpathy/jobs</span>
    <span>MySQL 8.0 · descriptive SQL, no models · 23 Sep 2026</span>
  </footer>
</div>

<!-- Expand Fullscreen Modal Overlay -->
<div id="expand-modal" class="expand-modal" onclick="closeExpandModal(event)">
  <div class="modal-card" onclick="event.stopPropagation()">
    <div class="modal-header">
      <h3 id="modal-chart-title" class="modal-title">Chart Fullscreen Inspection</h3>
      <div style="display:flex;gap:10px;align-items:center;">
        <button class="btn-action" onclick="downloadModalPNG()">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
          Download PNG
        </button>
        <button class="btn-modal-close" onclick="closeExpandModal()" title="Close (Esc)">✕</button>
      </div>
    </div>
    <div id="modal-chart-container" style="width:100%;height:calc(85vh - 70px);"></div>
  </div>
</div>

<script>
// Data payloads injected from relational database queries
const secData = {sec_json};
const pewData = {pew_json};
const casesData = {cases_json};
const economyAvg = {wtd_avg:.2f};

// Common Plotly Dark Dimmed / Matte Slate Configuration
const plotlyConfig = {{
  responsive: true,
  displayModeBar: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toggleSpikelines'],
  toImageButtonOptions: {{
    format: 'png',
    height: 900,
    width: 1400,
    scale: 2
  }}
}};

const commonPlotlyLayout = {{
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: {{ family: 'Inter, sans-serif', color: '#8b9bb4', size: 11 }},
  hoverlabel: {{
    bgcolor: '#131b2e',
    bordercolor: '#233044',
    font: {{ family: 'Inter, sans-serif', size: 12, color: '#d8deee' }}
  }}
}};

// 1. Render Sector Exposure Ranking Chart
function renderSectorExposureChart() {{
  const el = document.getElementById('chart-sector-exposure');
  if (!el || typeof Plotly === 'undefined') return;

  const ySectors = secData.map(d => d.sector);
  const xWeighted = secData.map(d => d.weighted);
  const xUnweighted = secData.map(d => d.unweighted);
  const customData = secData.map(d => [d.unweighted, d.emp_str, d.industries, d.diff]);

  const barTrace = {{
    type: 'bar',
    orientation: 'h',
    name: 'Employment-weighted',
    x: xWeighted,
    y: ySectors,
    customdata: customData,
    text: xWeighted.map(v => v.toFixed(2)),
    textposition: 'inside',
    insidetextanchor: 'end',
    textfont: {{ family: 'IBM Plex Mono, monospace', size: 10.5, color: '#d8deee' }},
    marker: {{ color: '#3b4f6e', opacity: 0.95, line: {{ width: 0 }} }},
    hovertemplate: '<b>%{{y}}</b><br>' +
      '• Employment-Weighted Exposure: <b>%{{x:.2f}} / 10</b><br>' +
      '• Unweighted Mean Exposure: <b>%{{customdata[0]:.2f}} / 10</b><br>' +
      '• Covered Workers: <b>%{{customdata[1]}}</b><br>' +
      '• Detailed Industries: <b>%{{customdata[2]}}</b><br>' +
      '• Weighting Effect: <b>%{{customdata[3]:+.2f}}</b>' +
      '<extra></extra>'
  }};

  const tickTrace = {{
    type: 'scatter',
    mode: 'markers',
    name: 'Unweighted mean',
    x: xUnweighted,
    y: ySectors,
    customdata: customData,
    marker: {{
      symbol: 'diamond',
      size: 7,
      color: '#8b9bb4',
      line: {{ width: 1, color: '#0d1322' }}
    }},
    hovertemplate: '<b>%{{y}} (Unweighted Mean)</b><br>' +
      '• Unweighted Mean: <b>%{{x:.2f}} / 10</b><br>' +
      '• Weighted Exposure: <b>%{{customdata[0]:.2f}} / 10</b>' +
      '<extra></extra>'
  }};

  const layout = {{
    ...commonPlotlyLayout,
    height: 720,
    bargap: 0.32,
    margin: {{ l: 240, r: 40, t: 15, b: 40 }},
    showlegend: false,
    xaxis: {{
      range: [0, 10],
      title: {{ text: 'AI Exposure Score (0–10)', font: {{ size: 11, color: '#64748b' }} }},
      gridcolor: '#1c2638',
      zerolinecolor: '#233044',
      tickfont: {{ color: '#8b9bb4', family: 'IBM Plex Mono' }}
    }},
    yaxis: {{
      automargin: true,
      tickfont: {{ color: '#b0bccd', size: 11 }},
      gridcolor: 'transparent'
    }},
    shapes: [{{
      type: 'line',
      x0: economyAvg,
      x1: economyAvg,
      y0: 0,
      y1: 1,
      xref: 'x',
      yref: 'paper',
      line: {{ dash: 'dot', color: '#64748b', width: 1.5 }}
    }}],
    annotations: [{{
      x: economyAvg,
      y: 0.01,
      xref: 'x',
      yref: 'paper',
      text: 'Avg ' + economyAvg,
      showarrow: false,
      font: {{ size: 10, family: 'IBM Plex Mono', color: '#8b9bb4' }},
      xanchor: 'left',
      yanchor: 'bottom'
    }}]
  }};

  Plotly.newPlot('chart-sector-exposure', [barTrace, tickTrace], layout, {{ ...plotlyConfig, displayModeBar: 'hover' }});
}}

// 2. Render Workforce Exposure Tier Chart
function renderTierChart() {{
  const el = document.getElementById('chart-tier-distribution');
  if (!el || typeof Plotly === 'undefined') return;

  const highPct = {high_pct};
  const modPct = {mod_pct};
  const lowPct = {low_pct};

  const traceHigh = {{
    type: 'bar',
    orientation: 'h',
    name: 'High',
    x: [highPct],
    y: ['Tier'],
    customdata: [['High Exposure', '{fmt_emp(high_emp)}', '{tier_high_label}']],
    marker: {{ color: '#3d5270' }},
    hovertemplate: '<b>%{{customdata[0]}}</b><br>• Workers: <b>%{{customdata[1]}}</b><br>• Share: <b>%{{x}}%</b><br>• Criteria: %{{customdata[2]}}<extra></extra>'
  }};

  const traceMod = {{
    type: 'bar',
    orientation: 'h',
    name: 'Moderate',
    x: [modPct],
    y: ['Tier'],
    customdata: [['Moderate Exposure', '{fmt_emp(mod_emp)}', '{tier_mod_label}']],
    marker: {{ color: '#4b5a70' }},
    hovertemplate: '<b>%{{customdata[0]}}</b><br>• Workers: <b>%{{customdata[1]}}</b><br>• Share: <b>%{{x}}%</b><br>• Criteria: %{{customdata[2]}}<extra></extra>'
  }};

  const traceLow = {{
    type: 'bar',
    orientation: 'h',
    name: 'Low',
    x: [lowPct],
    y: ['Tier'],
    customdata: [['Low Exposure', '{fmt_emp(low_emp)}', '{tier_low_label}']],
    marker: {{ color: '#273244' }},
    hovertemplate: '<b>%{{customdata[0]}}</b><br>• Workers: <b>%{{customdata[1]}}</b><br>• Share: <b>%{{x}}%</b><br>• Criteria: %{{customdata[2]}}<extra></extra>'
  }};

  const layout = {{
    ...commonPlotlyLayout,
    barmode: 'stack',
    margin: {{ l: 0, r: 0, t: 0, b: 0 }},
    showlegend: false,
    xaxis: {{ showgrid: false, showticklabels: false, range: [0, 100] }},
    yaxis: {{ showgrid: false, showticklabels: false }}
  }};

  Plotly.newPlot('chart-tier-distribution', [traceHigh, traceMod, traceLow], layout, {{ ...plotlyConfig, displayModeBar: false }});
}}

// 3. Render Perceived Fairness Diverging Bar Chart
let currentCohortFilter = 'all';
function renderCohortChart(filterKey = 'all') {{
  const el = document.getElementById('chart-cohort-diverging');
  if (!el || typeof Plotly === 'undefined') return;

  currentCohortFilter = filterKey;
  let filtered = pewData;
  if (filterKey !== 'all') {{
    filtered = pewData.filter(d => d.dim_key === filterKey || d.dim_key === 'all');
  }}

  // Sort reversed so Total US Adults is at top
  const cohortsRev = [...filtered].reverse();
  const yLabels = cohortsRev.map(d => d.cohort);
  const xBetter = cohortsRev.map(d => -d.better);
  const xWorse = cohortsRev.map(d => d.worse);
  const customData = cohortsRev.map(d => [d.better, d.worse, d.gap, d.moe, d.cohort, d.dim, d.same, d.notsure, d.n]);

  const traceBetter = {{
    type: 'bar',
    orientation: 'h',
    name: 'AI better than humans',
    x: xBetter,
    y: yLabels,
    customdata: customData,
    marker: {{ color: '#3d5270' }},
    hovertemplate: '<b>%{{customdata[4]}}</b> (%{{customdata[5]}})<br>' +
      '• AI would do better: <b>%{{customdata[0]}}%</b><br>' +
      '• AI would do worse: <b>%{{customdata[1]}}%</b><br>' +
      '• About the same: <b>%{{customdata[6]}}%</b> · Not sure: <b>%{{customdata[7]}}%</b><br>' +
      '• Net Skepticism: <b>%{{customdata[2]:+d}} pp</b><br>' +
      '• Margin of error: <b>±%{{customdata[3]}} pts</b> (n = %{{customdata[8]:,}})' +
      '<extra></extra>'
  }};

  const traceWorse = {{
    type: 'bar',
    orientation: 'h',
    name: 'AI worse than humans',
    x: xWorse,
    y: yLabels,
    customdata: customData,
    marker: {{ color: '#273244' }},
    hovertemplate: '<b>%{{customdata[4]}}</b> (%{{customdata[5]}})<br>' +
      '• AI would do worse: <b>%{{customdata[1]}}%</b><br>' +
      '• AI would do better: <b>%{{customdata[0]}}%</b><br>' +
      '• About the same: <b>%{{customdata[6]}}%</b> · Not sure: <b>%{{customdata[7]}}%</b><br>' +
      '• Net Skepticism: <b>%{{customdata[2]:+d}} pp</b><br>' +
      '• Margin of error: <b>±%{{customdata[3]}} pts</b> (n = %{{customdata[8]:,}})' +
      '<extra></extra>'
  }};

  // Annotations for net gap at right of bars
  const annotations = cohortsRev.map(d => ({{
    x: d.worse + 3,
    y: d.cohort,
    text: (d.gap > 0 ? '+' : '') + Math.round(d.gap),
    showarrow: false,
    font: {{ size: 11, family: 'IBM Plex Mono', color: '#d8deee' }},
    xanchor: 'left'
  }}));

  // Baseline dotted line at the total U.S. adults gap
  const layout = {{
    ...commonPlotlyLayout,
    barmode: 'relative',
    margin: {{ l: 140, r: 40, t: 15, b: 40 }},
    showlegend: false,
    xaxis: {{
      range: [-65, 65],
      tickvals: [-60, -30, 0, 30, 60],
      ticktext: ['60%', '30%', '0', '30%', '60%'],
      title: {{ text: '← % say AI would do better   ·   % say AI would do worse →', font: {{ size: 11, color: '#64748b' }} }},
      gridcolor: '#1c2638',
      zerolinecolor: '#233044',
      tickfont: {{ color: '#8b9bb4', family: 'IBM Plex Mono' }}
    }},
    yaxis: {{
      automargin: true,
      tickfont: {{ color: '#b0bccd', size: 11.5 }},
      gridcolor: 'transparent'
    }},
    shapes: [{{
      type: 'line',
      x0: {h_gap},
      x1: {h_gap},
      y0: 0,
      y1: 1,
      xref: 'x',
      yref: 'paper',
      line: {{ dash: 'dot', color: '#64748b', width: 1.5 }}
    }}],
    annotations: annotations
  }};

  Plotly.react('chart-cohort-diverging', [traceBetter, traceWorse], layout, plotlyConfig);
}}

// 4. Render Five Use Cases Chart
function renderUseCasesChart() {{
  const el = document.getElementById('chart-use-cases');
  if (!el || typeof Plotly === 'undefined') return;

  const revCases = [...casesData].reverse();
  const yNames = revCases.map(d => d.name);
  const xFav = revCases.map(d => d.favor);
  const colors = revCases.map(d => d.name === 'AI Making Final Hiring Decisions' ? '#4a638d' : '#3b4f6e');
  const customData = revCases.map(d => [d.netopp, d.tier, d.basis]);

  const trace = {{
    type: 'bar',
    orientation: 'h',
    x: xFav,
    y: yNames,
    customdata: customData,
    marker: {{ color: colors }},
    hovertemplate: '<b>%{{y}}</b><br>' +
      '• Favor: <b>%{{x}}%</b><br>' +
      '• Net opposition: <b>%{{customdata[0]:+d}} pp</b><br>' +
      '• EU AI Act Tier: <b>%{{customdata[1]}}</b><br>' +
      '• Scope: %{{customdata[2]}}' +
      '<extra></extra>'
  }};

  const layout = {{
    ...commonPlotlyLayout,
    margin: {{ l: 200, r: 25, t: 10, b: 35 }},
    xaxis: {{
      range: [0, 45],
      ticksuffix: '%',
      gridcolor: '#1c2638',
      tickfont: {{ color: '#8b9bb4', family: 'IBM Plex Mono' }}
    }},
    yaxis: {{
      tickfont: {{ color: '#b0bccd', size: 11 }},
      gridcolor: 'transparent'
    }}
  }};

  Plotly.newPlot('chart-use-cases', [trace], layout, {{ ...plotlyConfig, displayModeBar: false }});
}}

// 5. Render Statutory Risk Matrix Chart
function renderStatutoryRiskChart() {{
  const el = document.getElementById('chart-statutory-risk');
  if (!el || typeof Plotly === 'undefined') return;

  const yNames = casesData.map(d => d.name);
  const xFav = casesData.map(d => d.favor);
  const xNetOpp = casesData.map(d => d.netopp);
  const customData = casesData.map(d => [d.tier, d.basis]);

  const traceAcc = {{
    type: 'bar',
    name: 'Favor %',
    x: yNames,
    y: xFav,
    customdata: customData,
    marker: {{ color: '#3b4f6e' }},
    hovertemplate: '<b>%{{x}}</b><br>• Favor: <b>%{{y}}%</b><br>• Tier: %{{customdata[0]}}<extra></extra>'
  }};

  const traceGap = {{
    type: 'bar',
    name: 'Net opposition (pp)',
    x: yNames,
    y: xNetOpp,
    customdata: customData,
    marker: {{ color: '#273244' }},
    hovertemplate: '<b>%{{x}}</b><br>• Net opposition: <b>%{{y:+d}} pp</b><br>• Scope: %{{customdata[1]}}<extra></extra>'
  }};

  const layout = {{
    ...commonPlotlyLayout,
    barmode: 'group',
    margin: {{ l: 30, r: 15, t: 10, b: 40 }},
    showlegend: true,
    legend: {{ orientation: 'h', y: 1.15, x: 0, font: {{ size: 10.5, color: '#8b9bb4' }} }},
    xaxis: {{
      tickfont: {{ color: '#b0bccd', size: 10 }},
      tickangle: -10,
      gridcolor: 'transparent'
    }},
    yaxis: {{
      gridcolor: '#1c2638',
      tickfont: {{ color: '#8b9bb4', family: 'IBM Plex Mono' }}
    }}
  }};

  Plotly.newPlot('chart-statutory-risk', [traceAcc, traceGap], layout, plotlyConfig);
}}

// 6. View Toggles (Chart vs Table)
function toggleSecView(mode) {{
  const chartView = document.getElementById('sec-chart-view');
  const tableView = document.getElementById('sec-table-view');
  const btnChart = document.getElementById('btn-toggle-sec-chart');
  const btnTable = document.getElementById('btn-toggle-sec-table');

  if (mode === 'chart') {{
    chartView.style.display = 'block';
    tableView.style.display = 'none';
    btnChart.classList.add('active');
    btnTable.classList.remove('active');
    setTimeout(() => {{ Plotly.Plots.resize('chart-sector-exposure'); }}, 50);
  }} else {{
    chartView.style.display = 'none';
    tableView.style.display = 'block';
    btnChart.classList.remove('active');
    btnTable.classList.add('active');
  }}
}}

function toggleCohortView(mode) {{
  const chartView = document.getElementById('cohort-chart-view');
  const tableView = document.getElementById('cohort-table-view');
  const btnChart = document.getElementById('btn-toggle-cohort-chart');
  const btnTable = document.getElementById('btn-toggle-cohort-table');

  if (mode === 'chart') {{
    chartView.style.display = 'block';
    tableView.style.display = 'none';
    btnChart.classList.add('active');
    btnTable.classList.remove('active');
    setTimeout(() => {{ Plotly.Plots.resize('chart-cohort-diverging'); }}, 50);
  }} else {{
    chartView.style.display = 'none';
    tableView.style.display = 'block';
    btnChart.classList.remove('active');
    btnTable.classList.add('active');
  }}
}}

// 7. Download PNG Functionality
function downloadChartPNG(divId, filename) {{
  const gd = document.getElementById(divId);
  if (!gd || typeof Plotly === 'undefined') return;
  Plotly.downloadImage(gd, {{
    format: 'png',
    width: 1400,
    height: 900,
    filename: filename || 'workforceguard_chart'
  }});
}}

// 8. Fullscreen / Expand Modal Management
let activeExpandedDivId = null;
function expandChart(sourceDivId, title) {{
  const modal = document.getElementById('expand-modal');
  const titleEl = document.getElementById('modal-chart-title');
  const container = document.getElementById('modal-chart-container');
  const sourceGd = document.getElementById(sourceDivId);

  if (!modal || !sourceGd || typeof Plotly === 'undefined') return;

  activeExpandedDivId = sourceDivId;
  titleEl.textContent = title || 'WorkforceGuard Chart Inspection';
  modal.classList.add('active');

  // Clone source data and layout with expanded styling
  const clonedData = JSON.parse(JSON.stringify(sourceGd.data || []));
  const clonedLayout = JSON.parse(JSON.stringify(sourceGd.layout || {{}}));
  clonedLayout.autosize = true;
  delete clonedLayout.width;
  delete clonedLayout.height;

  Plotly.newPlot(container, clonedData, clonedLayout, plotlyConfig).then(() => {{
    Plotly.Plots.resize(container);
  }});
}}

function closeExpandModal(event) {{
  const modal = document.getElementById('expand-modal');
  if (modal) modal.classList.remove('active');
  const container = document.getElementById('modal-chart-container');
  if (container && typeof Plotly !== 'undefined') Plotly.purge(container);
  activeExpandedDivId = null;
}}

function downloadModalPNG() {{
  const container = document.getElementById('modal-chart-container');
  if (container) {{
    Plotly.downloadImage(container, {{
      format: 'png',
      width: 1800,
      height: 1100,
      filename: (activeExpandedDivId || 'workforceguard') + '_expanded'
    }});
  }}
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeExpandModal();
}});


// 10. Tab Switching
function showTab(idx) {{
  for (let i = 0; i < 4; i++) {{
    const el = document.getElementById('tab-' + i);
    const btn = document.getElementById('btn-tab-' + i);
    if (el) el.classList.remove('active');
    if (btn) btn.classList.remove('active');
  }}
  const target = document.getElementById('tab-' + idx);
  const targetBtn = document.getElementById('btn-tab-' + idx);
  if (target) target.classList.add('active');
  if (targetBtn) targetBtn.classList.add('active');

  const foot = document.getElementById('foot-source');
  if (foot) {{
    if (idx === 0) {{
      foot.textContent = 'Employment: BLS National Employment Matrix, 2024 · Exposure ratings: Karpathy (2026), github.com/karpathy/jobs';
    }} else if (idx === 1) {{
      foot.textContent = 'Pew Research Center, American Trends Panel Wave 119 · N = 11,004 U.S. adults · weighted estimates from microdata';
    }} else if (idx === 2) {{
      foot.textContent = 'Regulation (EU) 2024/1689, Annex III point 4 & Art. 5 · Annex III dates as amended by the 2026 Digital Omnibus';
    }} else {{
      foot.textContent = 'WorkforceGuard Third Normal Form (3NF) Relational Architecture · {db_type}';
    }}
  }}

  // Resize visible charts when unhidden
  setTimeout(() => {{
    if (idx === 0) {{
      Plotly.Plots.resize('chart-sector-exposure');
      Plotly.Plots.resize('chart-tier-distribution');
    }} else if (idx === 1) {{
      Plotly.Plots.resize('chart-cohort-diverging');
      Plotly.Plots.resize('chart-use-cases');
    }} else if (idx === 2) {{
      Plotly.Plots.resize('chart-statutory-risk');
    }}
  }}, 60);

  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

// 11. Demographic Cohort Filtering
function filterCohort(dim) {{
  const pills = ['all', 'gender', 'race', 'age'];
  pills.forEach(p => {{
    const el = document.getElementById('pill-' + p);
    if (el) el.classList.remove('active');
  }});
  const activePill = document.getElementById('pill-' + dim);
  if (activePill) activePill.classList.add('active');

  // Filter both Plotly chart and table
  renderCohortChart(dim);

  const rows = document.querySelectorAll('.cohort-row, .cohort-header');
  rows.forEach(r => {{
    if (dim === 'all') {{
      r.style.display = 'grid';
      if (r.classList.contains('cohort-header')) r.style.display = 'block';
    }} else {{
      if (r.classList.contains('cohort-' + dim)) {{
        r.style.display = 'grid';
        if (r.classList.contains('cohort-header')) r.style.display = 'block';
      }} else {{
        r.style.display = 'none';
      }}
    }}
  }});
}}

// Initializer
window.addEventListener('load', () => {{
  renderSectorExposureChart();
  renderTierChart();
  renderCohortChart('all');
  renderUseCasesChart();
  renderStatutoryRiskChart();
}});

// Resize only the charts on the visible tab, debounced
let resizeTimer;
window.addEventListener('resize', () => {{
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {{
    document.querySelectorAll('.tab-content.active .js-plotly-plot').forEach(gd => Plotly.Plots.resize(gd));
  }}, 120);
}});
</script>
</body>
</html>
"""
    return html
