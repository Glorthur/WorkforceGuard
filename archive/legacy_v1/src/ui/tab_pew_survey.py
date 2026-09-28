"""
Tab 2 · Workforce Trust & Demographic Disparities.
Pew Research Center ATP Wave 119 (N = 11,004 U.S. adults): acceptability of five
workplace AI use cases and perceived fairness versus human decision-makers.
"""
import altair as alt
import pandas as pd
import streamlit as st

from src.database.queries import QUERY_PEW_DEMOGRAPHIC_FAIRNESS_GAP, get_pew_fairness_gap_analysis
from src.ui.theme import (
    COBALT, CRIMSON, MUTED, TEXT, card, card_heading, insight, section, to_numeric,
)

PCT_COLS = [
    "acceptable_pct", "unacceptable_pct", "fairer_than_humans_pct",
    "less_fair_pct", "equal_fairness_pct", "fairness_gap_pct", "skepticism_rank",
]
DIMENSION_LABELS = {
    "Overall": "Overall",
    "Gender": "Gender",
    "Race_Ethnicity": "Race / ethnicity",
    "Age": "Age",
}
DIMENSION_ORDER = ["Overall", "Gender", "Race_Ethnicity", "Age"]
SEG_FAIRER = "Fairer than humans"
SEG_LESS = "Less fair than humans"


@st.cache_data(ttl=600, show_spinner=False)
def _load_pew() -> pd.DataFrame:
    df = to_numeric(get_pew_fairness_gap_analysis(), PCT_COLS)
    df["dimension_label"] = df["dimension_type"].map(DIMENSION_LABELS).fillna(df["dimension_type"])
    df["risk_family"] = df["statutory_risk_tier"].str.contains("Annex III", na=False).map(
        {True: "Annex III high-risk", False: "Art. 50 transparency"}
    )
    return df


def _diverging_chart(df: pd.DataFrame, label_col: str, order: list[str], group_col: str | None = None) -> alt.Chart:
    """Fairer-than-humans extends left of zero, less-fair extends right. Net gap is labelled at the bar end."""
    long = pd.concat(
        [
            df.assign(segment=SEG_FAIRER, value=-df["fairer_than_humans_pct"], pct=df["fairer_than_humans_pct"]),
            df.assign(segment=SEG_LESS, value=df["less_fair_pct"], pct=df["less_fair_pct"]),
        ],
        ignore_index=True,
    )
    tooltip = [
        alt.Tooltip(f"{label_col}:N", title="Group"),
        alt.Tooltip("segment:N", title="Response"),
        alt.Tooltip("pct:Q", title="Share (%)", format=".0f"),
        alt.Tooltip("fairness_gap_pct:Q", title="Net gap (pp)", format="+.0f"),
        alt.Tooltip("equal_fairness_pct:Q", title="No difference (%)", format=".0f"),
    ]
    if group_col:
        tooltip.insert(1, alt.Tooltip(f"{group_col}:N", title="Dimension"))

    y = alt.Y(f"{label_col}:N", sort=order, title=None, axis=alt.Axis(labelLimit=260))
    lim = max(60, float(long["pct"].max()) + 12)
    bars = (
        alt.Chart(long)
        .mark_bar(height=16, cornerRadius=2)
        .encode(
            y=y,
            x=alt.X(
                "value:Q",
                title="← % say AI is fairer than humans   ·   % say AI is less fair →",
                scale=alt.Scale(domain=[-lim, lim]),
                axis=alt.Axis(labelExpr="abs(datum.value) + '%'", tickCount=7),
            ),
            color=alt.Color(
                "segment:N",
                title=None,
                scale=alt.Scale(domain=[SEG_FAIRER, SEG_LESS], range=[COBALT, CRIMSON]),
            ),
            tooltip=tooltip,
        )
    )
    labels = (
        alt.Chart(df)
        .mark_text(align="left", dx=6, font="IBM Plex Mono", fontSize=11, color=TEXT)
        .encode(
            y=y,
            x=alt.X("less_fair_pct:Q"),
            text=alt.Text("fairness_gap_pct:Q", format="+.0f"),
            tooltip=tooltip,
        )
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color=MUTED, strokeWidth=1).encode(x="x:Q")
    return (bars + zero + labels).properties(height=max(200, 30 * len(df)))


def _acceptability_chart(df: pd.DataFrame, order: list[str]) -> alt.Chart:
    long = pd.concat(
        [
            df.assign(segment="Acceptable", pct=df["acceptable_pct"]),
            df.assign(segment="Unacceptable", pct=df["unacceptable_pct"]),
        ],
        ignore_index=True,
    )
    return (
        alt.Chart(long)
        .mark_bar(height=16)
        .encode(
            y=alt.Y("use_case_name:N", sort=order, title=None, axis=alt.Axis(labelLimit=260)),
            x=alt.X("pct:Q", stack="zero", title="Share of U.S. adults (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color(
                "segment:N", title=None,
                scale=alt.Scale(domain=["Acceptable", "Unacceptable"], range=["#7fa2ff", "#1e293b"]),
            ),
            order=alt.Order("segment:N"),
            tooltip=[
                alt.Tooltip("use_case_name:N", title="Use case"),
                alt.Tooltip("segment:N", title="Response"),
                alt.Tooltip("pct:Q", title="Share (%)", format=".0f"),
                alt.Tooltip("risk_family:N", title="EU AI Act"),
            ],
        )
        .properties(height=max(180, 34 * len(df)))
    )


def render_pew_survey_tab() -> None:
    df = _load_pew()

    section(
        "Module 02 · Pew Research Center, ATP Wave 119",
        "How workers judge AI in hiring, promotion and monitoring",
        "Net skepticism is the share of adults who say AI would be less fair than a human decision-maker, minus "
        "the share who say it would be fairer. Positive values mean distrust outweighs trust.",
    )

    cohort_counts = df.groupby("use_case_name")["demographic_name"].nunique().sort_values(ascending=False)
    use_cases = cohort_counts.index.tolist()

    with card("pew_filters"):
        f1, f2 = st.columns([3, 2], gap="medium")
        with f1:
            use_case = st.pills(
                "Workplace AI use case",
                use_cases,
                selection_mode="single",
                default=use_cases[0],
                key="pew_use_case",
            ) or use_cases[0]
        available_dims = [d for d in DIMENSION_ORDER if d in df.loc[df["use_case_name"] == use_case, "dimension_type"].unique()]
        dim_options = ["All"] + [d for d in available_dims if d != "Overall"]
        with f2:
            dim = st.segmented_control(
                "Demographic dimension",
                dim_options,
                default="All",
                format_func=lambda d: "All cohorts" if d == "All" else DIMENSION_LABELS.get(d, d),
                disabled=len(dim_options) == 1,
            ) or "All"

    case_df = df[df["use_case_name"] == use_case]
    overall = case_df[case_df["dimension_type"] == "Overall"]
    cohorts = case_df[case_df["dimension_type"] != "Overall"]
    ov = overall.iloc[0] if len(overall) else case_df.iloc[0]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Find it acceptable", f"{ov['acceptable_pct']:.0f}%", help="Total U.S. adults.", border=True)
    k2.metric("Say AI is fairer", f"{ov['fairer_than_humans_pct']:.0f}%", help="Total U.S. adults.", border=True)
    k3.metric(
        "Net skepticism", f"{ov['fairness_gap_pct']:+.0f} pp",
        help="% less fair minus % fairer than humans, total U.S. adults.", border=True,
    )
    if len(cohorts):
        spread = cohorts["fairness_gap_pct"].max() - cohorts["fairness_gap_pct"].min()
        k4.metric(
            "Cohort spread", f"{spread:.0f} pp",
            help="Difference between the most and least skeptical demographic cohorts.", border=True,
        )
    else:
        k4.metric("Cohort spread", "n/a", help="Pew reports this use case for total adults only.", border=True)

    left, right = st.columns([3, 2], gap="medium")
    with left:
        with card("pew_diverging"):
            card_heading(
                "Perceived fairness by demographic cohort",
                f"{use_case}. Numbers at the bar ends are the net gap in percentage points.",
            )
            if len(cohorts):
                view = case_df if dim == "All" else case_df[case_df["dimension_type"].isin(["Overall", dim])]
                view = view.assign(
                    _dim_rank=view["dimension_type"].map({d: i for i, d in enumerate(DIMENSION_ORDER)})
                ).sort_values(["_dim_rank", "fairness_gap_pct"], ascending=[True, False])
                st.altair_chart(
                    _diverging_chart(view, "demographic_name", view["demographic_name"].tolist(), "dimension_label"),
                    theme=None, width="stretch",
                )
            else:
                st.altair_chart(
                    _diverging_chart(overall, "demographic_name", overall["demographic_name"].tolist()),
                    theme=None, width="stretch",
                )
                st.caption(
                    ":material/info: Pew publishes demographic breakdowns for this item on hiring decisions only. "
                    "Select *AI in Hiring Decisions* to compare cohorts."
                )

    with right:
        with card("pew_insight"):
            card_heading("Reading the gap")
            if len(cohorts):
                most = cohorts.loc[cohorts["fairness_gap_pct"].idxmax()]
                least = cohorts.loc[cohorts["fairness_gap_pct"].idxmin()]
                insight(
                    f"<b>{most['demographic_name']}</b> are the most skeptical cohort "
                    f"(<span>{most['fairness_gap_pct']:+.0f} pp</span>). "
                    f"<b>{least['demographic_name']}</b> are the least "
                    f"(<span>{least['fairness_gap_pct']:+.0f} pp</span>)."
                )
            else:
                insight(
                    f"<span>{ov['less_fair_pct']:.0f}%</span> of U.S. adults say AI would be less fair than a human "
                    f"here, against <span>{ov['fairer_than_humans_pct']:.0f}%</span> who say it would be fairer."
                )
            st.badge(ov["risk_family"], icon=":material/gavel:", color="red" if "Annex" in ov["risk_family"] else "orange")
            st.caption(ov["statutory_risk_tier"])

        with card("pew_accept"):
            card_heading("Acceptability across all five use cases", "Total U.S. adults.")
            all_overall = df[df["dimension_type"] == "Overall"].sort_values("acceptable_pct", ascending=False)
            st.altair_chart(
                _acceptability_chart(all_overall, all_overall["use_case_name"].tolist()),
                theme=None, width="stretch",
            )

    section("Comparison", "Net skepticism across use cases", "Total U.S. adults, ranked by net gap.")
    with card("pew_cases"):
        ov_all = df[df["dimension_type"] == "Overall"].sort_values("fairness_gap_pct", ascending=False)
        st.altair_chart(
            _diverging_chart(ov_all, "use_case_name", ov_all["use_case_name"].tolist()),
            theme=None, width="stretch",
        )

    section("Survey cells", "Full response table", "Every use case × cohort cell returned by the window-function query.")
    table = df if dim == "All" else df[df["dimension_type"].isin(["Overall", dim])]
    st.dataframe(
        table[[
            "use_case_name", "risk_family", "demographic_name", "dimension_label",
            "acceptable_pct", "unacceptable_pct", "fairer_than_humans_pct", "less_fair_pct",
            "fairness_gap_pct", "skepticism_rank",
        ]],
        width="stretch",
        hide_index=True,
        column_config={
            "use_case_name": st.column_config.TextColumn("Use case", width="medium"),
            "risk_family": st.column_config.TextColumn("EU AI Act"),
            "demographic_name": st.column_config.TextColumn("Cohort"),
            "dimension_label": st.column_config.TextColumn("Dimension", width="small"),
            "acceptable_pct": st.column_config.ProgressColumn("Acceptable", min_value=0, max_value=100, format="%.0f%%"),
            "unacceptable_pct": st.column_config.ProgressColumn("Unacceptable", min_value=0, max_value=100, format="%.0f%%"),
            "fairer_than_humans_pct": st.column_config.NumberColumn("Fairer %", format="%.0f"),
            "less_fair_pct": st.column_config.NumberColumn("Less fair %", format="%.0f"),
            "fairness_gap_pct": st.column_config.NumberColumn("Net gap (pp)", format="%+.0f"),
            "skepticism_rank": st.column_config.NumberColumn("Rank in dimension", format="%d", width="small"),
        },
    )

    with st.expander("SQL and methodology", icon=":material/code:"):
        st.code(QUERY_PEW_DEMOGRAPHIC_FAIRNESS_GAP.strip(), language="sql")
        st.markdown(
            "- `r.less_fair_pct - r.fairer_than_humans_pct` computes the signed net perception gap.\n"
            "- `RANK() OVER (PARTITION BY use_case, dimension_type ORDER BY gap DESC)` ranks cohorts within their "
            "own dimension, so gender is not compared against age.\n"
            "- The remainder of each row (\"no difference\") is shown in tooltips and excluded from the net gap."
        )
        st.caption("Survey percentages describe public perception. They do not measure the behaviour of any deployed system.")
