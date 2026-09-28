"""
Tab 4 · Data Provenance & 3NF Relational Architecture.
Dataset lineage, the BLS hierarchy double-counting guard, the five-table schema
and live integrity checks executed against the active engine.
"""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.database.connection import execute_query, get_db_type
from src.ui.theme import (
    BORDER, COBALT, CRIMSON, MUTED, PERIWINKLE, SLATE_800, SLATE_NAVY, TEXT,
    card, card_heading, section,
)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

TABLES = {
    "dim_naics_sectors": ("Dimension", "2-digit parent NAICS sectors", "BLS / O*NET"),
    "fact_industry_exposure": ("Fact", "Detailed industries with covered employment and exposure", "BLS / O*NET"),
    "dim_demographics": ("Dimension", "Demographic cohorts: gender, race / ethnicity, age, overall", "Pew ATP W119"),
    "dim_ai_use_cases": ("Dimension", "Workplace AI use cases with EU AI Act classification", "Pew ATP W119"),
    "fact_pew_survey_responses": ("Fact", "Survey response percentages per use case × cohort", "Pew ATP W119"),
}

INTEGRITY_CHECKS = [
    ("Referential integrity", "fact_industry_exposure → dim_naics_sectors",
     """SELECT COUNT(*) FROM fact_industry_exposure i
        LEFT JOIN dim_naics_sectors s ON s.sector_code = i.parent_sector_code
        WHERE s.sector_code IS NULL"""),
    ("Referential integrity", "fact_pew_survey_responses → dim_ai_use_cases",
     """SELECT COUNT(*) FROM fact_pew_survey_responses r
        LEFT JOIN dim_ai_use_cases u ON u.use_case_id = r.use_case_id
        WHERE u.use_case_id IS NULL"""),
    ("Referential integrity", "fact_pew_survey_responses → dim_demographics",
     """SELECT COUNT(*) FROM fact_pew_survey_responses r
        LEFT JOIN dim_demographics d ON d.demographic_id = r.demographic_id
        WHERE d.demographic_id IS NULL"""),
    ("Primary key uniqueness", "fact_industry_exposure.naics_code",
     "SELECT COUNT(*) - COUNT(DISTINCT naics_code) FROM fact_industry_exposure"),
    ("Grain uniqueness", "fact_pew_survey_responses (use_case_id, demographic_id)",
     """SELECT COUNT(*) FROM (SELECT use_case_id, demographic_id FROM fact_pew_survey_responses
        GROUP BY use_case_id, demographic_id HAVING COUNT(*) > 1) AS dup"""),
    ("Numerical bounds", "weighted_exposure within [0, 10]",
     "SELECT COUNT(*) FROM fact_industry_exposure WHERE weighted_exposure < 0 OR weighted_exposure > 10"),
    ("Numerical bounds", "survey percentages within [0, 100]",
     """SELECT COUNT(*) FROM fact_pew_survey_responses
        WHERE acceptable_pct NOT BETWEEN 0 AND 100 OR unacceptable_pct NOT BETWEEN 0 AND 100
           OR fairer_than_humans_pct NOT BETWEEN 0 AND 100 OR less_fair_pct NOT BETWEEN 0 AND 100
           OR equal_fairness_pct NOT BETWEEN 0 AND 100"""),
    ("Null integrity", "required analytical columns",
     """SELECT
          (SELECT COUNT(*) FROM fact_industry_exposure
             WHERE covered_employment IS NULL OR weighted_exposure IS NULL OR exposure_tier IS NULL)
        + (SELECT COUNT(*) FROM fact_pew_survey_responses
             WHERE acceptable_pct IS NULL OR less_fair_pct IS NULL OR fairer_than_humans_pct IS NULL)"""),
]


def _scalar(sql: str) -> int:
    value = execute_query(sql).iloc[0, 0]
    return 0 if value is None or pd.isna(value) else int(value)


@st.cache_data(ttl=600, show_spinner=False)
def _table_counts() -> dict[str, int]:
    return {t: _scalar(f"SELECT COUNT(*) FROM {t}") for t in TABLES}  # table names are a fixed whitelist


@st.cache_data(ttl=600, show_spinner=False)
def _run_integrity_checks() -> pd.DataFrame:
    rows = []
    for gate, target, sql in INTEGRITY_CHECKS:
        violations = _scalar(sql)
        rows.append({"gate": gate, "target": target, "violations": violations,
                     "status": "Pass" if violations == 0 else "Fail"})
    return pd.DataFrame(rows)


@st.cache_data(ttl=600, show_spinner=False)
def _hierarchy_totals() -> dict[str, float] | None:
    path = RAW_DIR / "real_bls_industry_ai_exposure.csv"
    if not path.exists():
        return None
    raw = pd.read_csv(path)
    is_sector = raw["is_sector"].astype(str).str.lower().eq("true")
    return {
        "raw_rows": len(raw),
        "sector_rows": int(is_sector.sum()),
        "raw_sum": float(raw["covered_employment_2024"].sum()),
        "sector_sum": float(raw.loc[is_sector, "covered_employment_2024"].sum()),
        "fact_sum": float(_scalar("SELECT SUM(covered_employment) FROM fact_industry_exposure")),
    }


@st.cache_data(ttl=600, show_spinner=False)
def _preview(table: str) -> pd.DataFrame:
    return execute_query(f"SELECT * FROM {table} LIMIT 25")  # whitelist-only


def _schema_dot(counts: dict[str, int]) -> str:
    def node(name: str, cols: list[tuple[str, str]]) -> str:
        kind = TABLES[name][0]
        head = COBALT if kind == "Fact" else SLATE_800
        rows = "".join(
            f'<TR><TD ALIGN="LEFT" BGCOLOR="{SLATE_NAVY}"><FONT COLOR="{PERIWINKLE if k else MUTED}" POINT-SIZE="9">{k}</FONT></TD>'
            f'<TD ALIGN="LEFT" BGCOLOR="{SLATE_NAVY}"><FONT COLOR="{TEXT}" POINT-SIZE="10">{c}</FONT></TD></TR>'
            for k, c in cols
        )
        return (
            f'{name} [label=<<TABLE BORDER="1" COLOR="{BORDER}" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6">'
            f'<TR><TD COLSPAN="2" ALIGN="LEFT" BGCOLOR="{head}"><FONT COLOR="{TEXT}" POINT-SIZE="11"><B>{name}</B></FONT>'
            f'<FONT COLOR="{TEXT}" POINT-SIZE="9">   {counts.get(name, 0):,} rows</FONT></TD></TR>{rows}</TABLE>>];'
        )

    return f"""
digraph schema {{
  graph [bgcolor="transparent", rankdir=LR, pad=0.3, nodesep=0.5, ranksep=1.1, fontname="Inter"];
  node  [shape=plaintext, fontname="Inter"];
  edge  [color="{PERIWINKLE}", arrowhead=crow, arrowtail=tee, dir=both, penwidth=1.2];
  {node("dim_naics_sectors", [("PK", "sector_code"), ("", "sector_title")])}
  {node("fact_industry_exposure", [("PK", "naics_code"), ("FK", "parent_sector_code"), ("", "industry_title"),
                                   ("", "covered_employment"), ("", "weighted_exposure"), ("", "exposure_tier")])}
  {node("dim_ai_use_cases", [("PK", "use_case_id"), ("", "use_case_name"), ("", "statutory_risk_tier"), ("", "risk_basis")])}
  {node("dim_demographics", [("PK", "demographic_id"), ("", "demographic_name"), ("", "dimension_type")])}
  {node("fact_pew_survey_responses", [("PK", "response_id"), ("FK", "use_case_id"), ("FK", "demographic_id"),
                                      ("", "acceptable_pct · unacceptable_pct"), ("", "fairer_than_humans_pct · less_fair_pct"),
                                      ("", "equal_fairness_pct")])}
  dim_naics_sectors -> fact_industry_exposure;
  dim_ai_use_cases -> fact_pew_survey_responses;
  dim_demographics -> fact_pew_survey_responses;
}}"""


def _hierarchy_chart(h: dict[str, float]) -> alt.Chart:
    df = pd.DataFrame(
        [
            {"label": "Naive sum of all raw rows", "value": h["raw_sum"], "kind": "Double-counted"},
            {"label": "3NF fact table (detailed industries)", "value": h["fact_sum"], "kind": "Normalised"},
        ]
    )
    return (
        alt.Chart(df)
        .mark_bar(height=22)
        .encode(
            y=alt.Y("label:N", title=None, sort=None, axis=alt.Axis(labelLimit=280)),
            x=alt.X("value:Q", title="Covered employment", axis=alt.Axis(format="~s")),
            color=alt.Color("kind:N", legend=None,
                            scale=alt.Scale(domain=["Double-counted", "Normalised"], range=[CRIMSON, COBALT])),
            tooltip=[alt.Tooltip("label:N", title="Method"), alt.Tooltip("value:Q", title="Workers", format=",.0f")],
        )
        .properties(height=110)
    )


def render_profiling_tab() -> None:
    counts = _table_counts()
    checks = _run_integrity_checks()
    db_type = get_db_type().upper()

    section(
        "Module 04 · Provenance",
        "Two real datasets, five normalised tables",
        "Every figure in this dashboard is computed by SQL against these tables. Nothing is synthetic, imputed or "
        "predicted.",
    )

    d1, d2 = st.columns(2, gap="medium")
    with d1:
        with card("prov_bls"):
            st.badge("Dataset A", icon=":material/factory:", color="blue")
            card_heading(
                "U.S. Bureau of Labor Statistics and O*NET",
                "Industry-level AI exposure: 2024 covered employment joined to O*NET task profiles. 355 raw NAICS "
                "rows, split into parent sectors and detailed industries.",
            )
            a, b = st.columns(2)
            a.metric("dim_naics_sectors", f"{counts['dim_naics_sectors']:,}")
            b.metric("fact_industry_exposure", f"{counts['fact_industry_exposure']:,}")
    with d2:
        with card("prov_pew"):
            st.badge("Dataset B", icon=":material/how_to_reg:", color="blue")
            card_heading(
                "Pew Research Center, American Trends Panel Wave 119",
                "Nationally representative survey of 11,004 U.S. adults on five workplace AI use cases, reported "
                "for total adults and by gender, race / ethnicity and age.",
            )
            a, b, c = st.columns(3)
            a.metric("dim_ai_use_cases", f"{counts['dim_ai_use_cases']:,}")
            b.metric("dim_demographics", f"{counts['dim_demographics']:,}")
            c.metric("fact_pew_…", f"{counts['fact_pew_survey_responses']:,}")

    section(
        "Quality guard",
        "The BLS hierarchy trap",
        "The raw BLS file mixes 2-digit sector summary rows with their own detailed sub-industries. Summing every "
        "row counts the same workers twice. Sector rows are moved to dim_naics_sectors; only detailed industries "
        "enter the fact table.",
    )
    h = _hierarchy_totals()
    with card("prov_trap"):
        if h is None:
            st.warning("Raw file data/raw/real_bls_industry_ai_exposure.csv not found; hierarchy comparison skipped.",
                       icon=":material/warning:")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Naive raw CSV sum", f"{h['raw_sum'] / 1e6:.1f}M",
                      delta=f"{h['raw_rows']} rows incl. {h['sector_rows']} sector totals",
                      delta_color="inverse", border=True)
            m2.metric("3NF fact table sum", f"{h['fact_sum'] / 1e6:.1f}M", delta="Detailed industries only",
                      delta_color="off", border=True)
            m3.metric("Sector summary rows", f"{h['sector_sum'] / 1e6:.1f}M", delta="Held in dimension table",
                      delta_color="off", border=True)
            st.altair_chart(_hierarchy_chart(h), theme=None, width="stretch")

    section("Architecture", "Third normal form schema", "Two independent star fragments, one per dataset. Foreign keys use ON DELETE RESTRICT.")
    left, right = st.columns([3, 2], gap="medium")
    with left:
        with card("prov_schema"):
            st.graphviz_chart(_schema_dot(counts))
    with right:
        with card("prov_explorer"):
            card_heading("Table explorer", "First 25 rows of the selected table.")
            table = st.selectbox("Table", list(TABLES), format_func=lambda t: f"{t}  ·  {TABLES[t][0]}")
            kind, desc, src = TABLES[table]
            st.caption(f"{desc}. Source: {src}. {counts[table]:,} rows.")
            st.dataframe(_preview(table), width="stretch", hide_index=True, height=300)

    section("Integrity", "Live quality gates", f"Executed on every cache refresh against the active {db_type} engine.")
    passed = int((checks["status"] == "Pass").sum())
    with card("prov_gates"):
        g1, g2 = st.columns([1, 3], gap="medium")
        with g1:
            st.metric("Gates passing", f"{passed} / {len(checks)}")
            st.badge(
                "All checks pass" if passed == len(checks) else f"{len(checks) - passed} failing",
                icon=":material/check_circle:" if passed == len(checks) else ":material/error:",
                color="green" if passed == len(checks) else "red",
            )
            st.badge("Scope: 2 datasets · zero ML", icon=":material/verified:", color="blue")
        with g2:
            st.dataframe(
                checks,
                width="stretch",
                hide_index=True,
                column_config={
                    "gate": st.column_config.TextColumn("Gate"),
                    "target": st.column_config.TextColumn("Target", width="large"),
                    "violations": st.column_config.NumberColumn("Violations", format="%d", width="small"),
                    "status": st.column_config.TextColumn("Status", width="small"),
                },
            )

    with st.expander("Data limitations", icon=":material/info:"):
        st.markdown(
            "1. **BLS and O\\*NET.** Exposure scores measure occupational task potential. They do not predict job "
            "loss or net employment change.\n"
            "2. **Pew ATP Wave 119.** Grouped survey percentages describe public perception across cohorts. They do "
            "not represent individual employee outcomes or causal workplace effects.\n"
            "3. **Statutory mapping.** EU AI Act classifications are regulatory mappings derived from Regulation (EU) "
            "2024/1689 Annex III § 4 and Article 50."
        )
