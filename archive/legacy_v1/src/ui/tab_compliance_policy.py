"""
Tab 3 · EU AI Act & Statutory Compliance Cockpit.
Maps the surveyed workplace AI use cases to Regulation (EU) 2024/1689 (Annex III § 4
high-risk vs Art. 50 transparency) and runs the Chapter III conformity evaluator.
"""
import altair as alt
import pandas as pd
import streamlit as st

from src.database.connection import execute_query
from src.database.queries import QUERY_STATUTORY_AI_RISK_SUMMARY, get_statutory_risk_summary
from src.governance.eu_ai_act import evaluate_eu_ai_act_conformity
from src.ui.theme import (
    AMBER, CRIMSON, MUTED, TEXT, card, card_heading, section, to_numeric,
)

SQL_USE_CASE_CLASSIFICATION = """
SELECT
    u.use_case_name,
    u.statutory_risk_tier,
    u.risk_basis,
    r.acceptable_pct,
    r.unacceptable_pct,
    ROUND(r.less_fair_pct - r.fairer_than_humans_pct, 1) AS skepticism_gap_pct
FROM dim_ai_use_cases AS u
JOIN fact_pew_survey_responses AS r ON r.use_case_id = u.use_case_id
JOIN dim_demographics AS d ON d.demographic_id = r.demographic_id
WHERE d.dimension_type = 'Overall'
ORDER BY u.statutory_risk_tier, u.use_case_name;
"""

FAMILY_COLORS = {"Annex III high-risk": CRIMSON, "Art. 50 transparency": AMBER}


def _family(tier: str) -> str:
    return "Annex III high-risk" if "Annex III" in str(tier) else "Art. 50 transparency"


@st.cache_data(ttl=600, show_spinner=False)
def _load_risk_summary() -> pd.DataFrame:
    df = to_numeric(
        get_statutory_risk_summary(),
        ["use_case_count", "avg_acceptability_pct", "avg_unacceptability_pct",
         "avg_fairer_pct", "avg_less_fair_pct", "avg_skepticism_gap"],
    )
    df["family"] = df["statutory_risk_tier"].map(_family)
    return df


@st.cache_data(ttl=600, show_spinner=False)
def _load_use_cases() -> pd.DataFrame:
    df = to_numeric(
        execute_query(SQL_USE_CASE_CLASSIFICATION),
        ["acceptable_pct", "unacceptable_pct", "skepticism_gap_pct"],
    )
    df["family"] = df["statutory_risk_tier"].map(_family)
    return df


def _position_chart(df: pd.DataFrame) -> alt.Chart:
    tooltip = [
        alt.Tooltip("use_case_name:N", title="Use case"),
        alt.Tooltip("statutory_risk_tier:N", title="Classification"),
        alt.Tooltip("acceptable_pct:Q", title="Acceptable (%)", format=".0f"),
        alt.Tooltip("skepticism_gap_pct:Q", title="Net skepticism (pp)", format="+.0f"),
    ]
    base = alt.Chart(df).encode(
        x=alt.X("acceptable_pct:Q", title="Find it acceptable (% of U.S. adults)", scale=alt.Scale(domain=[10, 40])),
        y=alt.Y("skepticism_gap_pct:Q", title="Net skepticism (pp)", scale=alt.Scale(domain=[0, 50]),
                axis=alt.Axis(grid=True)),
        tooltip=tooltip,
    )
    pts = base.mark_circle(size=220, opacity=0.95, stroke="#020617", strokeWidth=2).encode(
        color=alt.Color(
            "family:N", title=None,
            scale=alt.Scale(domain=list(FAMILY_COLORS), range=list(FAMILY_COLORS.values())),
        )
    )
    labels = base.mark_text(align="left", dx=12, dy=-2, font="Inter", fontSize=11, color=TEXT).encode(
        text="use_case_name:N"
    )
    return (pts + labels).properties(height=320)


def _pillars(a) -> list[dict]:
    oversight_ok = not any(c.lower().startswith("warning") for c in a.human_oversight_controls)
    return [
        {"art": "Art. 10", "title": "Data and data governance", "ok": a.data_governance_score >= 80,
         "detail": f"Governance score {a.data_governance_score:.0f} / 100. Bias testing across demographic cohorts."},
        {"art": "Art. 11", "title": "Technical documentation", "ok": a.technical_documentation_complete,
         "detail": "System architecture, model cards and intended-purpose statement."},
        {"art": "Art. 12", "title": "Record-keeping", "ok": a.record_keeping_logging_active,
         "detail": "Automatic, tamper-evident event logs retained for at least six months."},
        {"art": "Art. 13", "title": "Transparency to deployers", "ok": a.transparency_explainability_rating.startswith("Satisfactory"),
         "detail": a.transparency_explainability_rating},
        {"art": "Art. 14", "title": "Human oversight", "ok": oversight_ok,
         "detail": "Human sign-off, override and appeal routes on adverse decisions." if oversight_ok
         else a.human_oversight_controls[0]},
        {"art": "Art. 15", "title": "Accuracy, robustness, cybersecurity", "ok": True,
         "detail": a.cybersecurity_robustness},
    ]


def _status_color(status: str) -> str:
    s = status.lower()
    if s.startswith("pass"):
        return "green"
    if s.startswith("conditional"):
        return "orange"
    return "red"


def render_compliance_policy_tab() -> None:
    risk = _load_risk_summary()
    cases = _load_use_cases()

    section(
        "Module 03 · Regulation (EU) 2024/1689",
        "Statutory classification of the surveyed workplace AI systems",
        "Four of the five use cases fall under Annex III § 4 (employment, worker management and access to "
        "self-employment) and carry the full Chapter III obligations. Productivity surveillance is mapped to "
        "Art. 50 transparency and notice duties.",
    )

    cols = st.columns(len(risk), gap="medium")
    for col, (_, row) in zip(cols, risk.iterrows()):
        with col:
            with card(f"tier_{row.name}"):
                st.badge(
                    row["family"], icon=":material/gavel:",
                    color="red" if row["family"].startswith("Annex") else "orange",
                )
                card_heading(row["statutory_risk_tier"], f"{int(row['use_case_count'])} use case(s) · total U.S. adults")
                m1, m2 = st.columns(2)
                m1.metric("Acceptable", f"{row['avg_acceptability_pct']:.0f}%")
                m2.metric("Net skepticism", f"{row['avg_skepticism_gap']:+.0f} pp")

    left, right = st.columns([3, 2], gap="medium")
    with left:
        with card("comp_position"):
            card_heading(
                "Public position of each system",
                "Further right is more accepted. Higher means distrust outweighs trust by more.",
            )
            st.altair_chart(_position_chart(cases), theme=None, width="stretch")
    with right:
        with card("comp_table"):
            card_heading("Legal basis", "Classification and citation stored in dim_ai_use_cases.")
            st.dataframe(
                cases[["use_case_name", "family", "risk_basis", "acceptable_pct"]],
                width="stretch",
                hide_index=True,
                height=320,
                column_config={
                    "use_case_name": st.column_config.TextColumn("Use case", width="medium"),
                    "family": st.column_config.TextColumn("Tier", width="small"),
                    "risk_basis": st.column_config.TextColumn("Basis", width="large"),
                    "acceptable_pct": st.column_config.ProgressColumn(
                        "Acceptable", min_value=0, max_value=100, format="%.0f%%"
                    ),
                },
            )

    section(
        "Conformity cockpit",
        "Annex III Chapter III conformity assessment",
        "Set the deployer's control posture to see how the evaluator scores the system. Data governance reflects "
        "any disparate-impact audit supplied; no candidate-level data is held in this project, so none is passed.",
    )

    with card("comp_cockpit"):
        controls, result = st.columns([2, 3], gap="large")
        with controls:
            st.html('<div class="wg-eyebrow">Control posture</div>')
            system_name = st.text_input("System under assessment", "WorkforceGuard Workplace AI Governance Suite")
            docs = st.toggle("Technical documentation complete (Art. 11)", value=True)
            logging = st.toggle("Automatic logging active (Art. 12)", value=True)
            hitl = st.toggle("Human-in-the-loop oversight (Art. 14)", value=True)

        a = evaluate_eu_ai_act_conformity(
            system_name=system_name,
            technical_docs_present=docs,
            logging_active=logging,
            human_in_the_loop_active=hitl,
        )

        with result:
            st.html('<div class="wg-eyebrow">Evaluator output</div>')
            st.badge(a.overall_conformity_status, icon=":material/verified_user:", color=_status_color(a.overall_conformity_status))
            st.caption(a.risk_classification)
            r1, r2 = st.columns(2)
            r1.metric("Data governance score", f"{a.data_governance_score:.0f} / 100", border=True)
            met = sum(p["ok"] for p in _pillars(a))
            r2.metric("Obligations met", f"{met} / 6", border=True)
            st.progress(met / 6)

    pillars = _pillars(a)
    for row_start in (0, 3):
        cols = st.columns(3, gap="medium")
        for col, p in zip(cols, pillars[row_start:row_start + 3]):
            with col:
                with card(f"pillar_{p['art'].replace('. ', '')}"):
                    st.badge(
                        "Met" if p["ok"] else "Gap",
                        icon=":material/check_circle:" if p["ok"] else ":material/error:",
                        color="green" if p["ok"] else "red",
                    )
                    card_heading(f"{p['art']} · {p['title']}", p["detail"])

    with card("comp_oversight"):
        card_heading("Human oversight controls (Art. 14)")
        for c in a.human_oversight_controls:
            icon = ":material/warning:" if c.lower().startswith("warning") else ":material/check:"
            st.markdown(f"{icon} {c}")

    section("Policy", "Recommendations for HR organisations")
    with card("comp_policy"):
        st.markdown(
            "1. **Advance worker notice.** Before deploying surveillance or productivity-tracking AI, give "
            "transparent disclosure under Article 50.\n"
            "2. **Multi-perspective fairness testing.** Given the skepticism across racial and age cohorts in the "
            "Pew data, run independent statistical audits before activating any algorithmic screening tool.\n"
            "3. **No solely automated decisions.** Under GDPR Art. 22 and EU AI Act Art. 14, automated "
            "recommendations must not be the sole basis for a hiring rejection or termination without substantive "
            "human review."
        )

    with st.expander("SQL and methodology", icon=":material/code:"):
        st.code(QUERY_STATUTORY_AI_RISK_SUMMARY.strip(), language="sql")
        st.markdown(
            "- Aggregates the `Overall` cohort only, so tiers are compared on the same population.\n"
            "- Tier labels and legal basis come from `dim_ai_use_cases`; they are regulatory mappings, not court findings.\n"
            "- Art. 9 (risk management system) is a deployer attestation and is not scored by the evaluator."
        )
