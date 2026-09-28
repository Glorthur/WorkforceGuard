"""
Tab 1 · Macroeconomic AI Exposure Intelligence.
Employment-weighted AI exposure by 2-digit NAICS sector (BLS / O*NET), with
detailed-industry drill-down. Pure SQL aggregation + descriptive statistics.
"""
import altair as alt
import pandas as pd
import streamlit as st

from src.database.connection import execute_query
from src.database.queries import QUERY_MACRO_EXPOSURE_BY_SECTOR, get_macro_exposure_summary
from src.ui.theme import (
    BADGE_COLORS, COBALT, MUTED, PERIWINKLE, TIER_COLORS, TIER_ORDER,
    band_for_score, card, card_heading, insight, section, short_tier, to_numeric,
)

SQL_DETAILED_INDUSTRIES = """
SELECT
    i.naics_code,
    i.parent_sector_code,
    s.sector_title,
    i.industry_title,
    i.covered_employment,
    i.weighted_exposure,
    i.exposure_tier
FROM fact_industry_exposure AS i
JOIN dim_naics_sectors AS s
    ON s.sector_code = i.parent_sector_code
ORDER BY i.weighted_exposure DESC;
"""


@st.cache_data(ttl=600, show_spinner=False)
def _load_sectors() -> pd.DataFrame:
    df = to_numeric(
        get_macro_exposure_summary(),
        ["detailed_industry_count", "detailed_employment", "employment_weighted_exposure", "unweighted_mean_exposure"],
    )
    df["band"] = df["employment_weighted_exposure"].map(band_for_score)
    df["weighting_effect"] = df["employment_weighted_exposure"] - df["unweighted_mean_exposure"]
    return df


@st.cache_data(ttl=600, show_spinner=False)
def _load_industries() -> pd.DataFrame:
    df = to_numeric(execute_query(SQL_DETAILED_INDUSTRIES), ["covered_employment", "weighted_exposure"])
    df["tier"] = df["exposure_tier"].map(short_tier)
    return df


def _sector_chart(df: pd.DataFrame, economy_avg: float) -> alt.Chart:
    order = df.sort_values("employment_weighted_exposure", ascending=False)["sector_title"].tolist()
    base = alt.Chart(df).encode(
        y=alt.Y("sector_title:N", sort=order, title=None, axis=alt.Axis(labelLimit=280)),
    )
    tooltip = [
        alt.Tooltip("sector_title:N", title="Sector"),
        alt.Tooltip("sector_code:N", title="NAICS"),
        alt.Tooltip("employment_weighted_exposure:Q", title="Employment-weighted", format=".2f"),
        alt.Tooltip("unweighted_mean_exposure:Q", title="Unweighted mean", format=".2f"),
        alt.Tooltip("detailed_employment:Q", title="Covered employment", format=",.0f"),
        alt.Tooltip("detailed_industry_count:Q", title="Detailed industries"),
    ]
    bars = base.mark_bar(height=14).encode(
        x=alt.X(
            "employment_weighted_exposure:Q",
            title="Employment-weighted AI exposure (0–10)",
            scale=alt.Scale(domain=[0, 10]),
        ),
        color=alt.Color(
            "band:N",
            title="Exposure band",
            scale=alt.Scale(domain=TIER_ORDER, range=[TIER_COLORS[t] for t in TIER_ORDER]),
        ),
        tooltip=tooltip,
    )
    ticks = base.mark_tick(color=PERIWINKLE, thickness=2, size=18).encode(
        x="unweighted_mean_exposure:Q", tooltip=tooltip
    )
    avg_rule = (
        alt.Chart(pd.DataFrame({"x": [economy_avg]}))
        .mark_rule(color=MUTED, strokeDash=[4, 4])
        .encode(x="x:Q", tooltip=[alt.Tooltip("x:Q", title="Economy-wide weighted", format=".2f")])
    )
    return (bars + ticks + avg_rule).properties(height=max(320, 26 * len(df)))


def _tier_chart(df_ind: pd.DataFrame) -> alt.Chart:
    tiers = (
        df_ind.groupby("tier", as_index=False)
        .agg(employment=("covered_employment", "sum"), industries=("naics_code", "count"))
    )
    tiers["share"] = tiers["employment"] / tiers["employment"].sum()
    return (
        alt.Chart(tiers)
        .mark_bar(height=34, cornerRadiusEnd=0)
        .encode(
            x=alt.X("share:Q", stack="normalize", axis=alt.Axis(format="%", title=None, grid=False)),
            color=alt.Color(
                "tier:N",
                title=None,
                sort=TIER_ORDER,
                scale=alt.Scale(domain=TIER_ORDER, range=[TIER_COLORS[t] for t in TIER_ORDER]),
            ),
            order=alt.Order("tier_rank:Q"),
            tooltip=[
                alt.Tooltip("tier:N", title="Tier"),
                alt.Tooltip("employment:Q", title="Covered employment", format=",.0f"),
                alt.Tooltip("share:Q", title="Share of workforce", format=".1%"),
                alt.Tooltip("industries:Q", title="Industries"),
            ],
        )
        .transform_calculate(tier_rank="indexof(['High','Moderate','Low'], datum.tier)")
        .properties(height=70)
    )


def _industry_table(df: pd.DataFrame, height: int | str = "auto") -> None:
    st.dataframe(
        df[["naics_code", "industry_title", "sector_title", "covered_employment", "weighted_exposure", "tier"]],
        width="stretch",
        height=height,
        hide_index=True,
        column_config={
            "naics_code": st.column_config.TextColumn("NAICS", width="small"),
            "industry_title": st.column_config.TextColumn("Industry", width="large"),
            "sector_title": st.column_config.TextColumn("Parent sector", width="medium"),
            "covered_employment": st.column_config.NumberColumn("Covered employment", format="localized"),
            "weighted_exposure": st.column_config.ProgressColumn(
                "AI exposure (0–10)", min_value=0, max_value=10, format="%.2f"
            ),
            "tier": st.column_config.TextColumn("Tier", width="small"),
        },
    )


def render_macro_exposure_tab() -> None:
    df_sec = _load_sectors()
    df_ind = _load_industries()

    total_emp = df_ind["covered_employment"].sum()
    economy_w = (df_ind["covered_employment"] * df_ind["weighted_exposure"]).sum() / total_emp
    economy_u = df_ind["weighted_exposure"].mean()
    high_share = df_ind.loc[df_ind["tier"] == "High", "covered_employment"].sum() / total_emp
    top = df_sec.iloc[0]

    section(
        "Module 01 · BLS / O*NET",
        "Where AI exposure concentrates in the U.S. labour market",
        "Exposure scores measure the share of occupational tasks that routine-cognitive and generative AI can "
        "perform. Sector figures are weighted by 2024 covered employment, so large employers count in proportion "
        "to the workers they hold.",
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Covered workforce", f"{total_emp / 1e6:.1f}M",
        help="Sum of covered employment across detailed industries in fact_industry_exposure.", border=True,
    )
    k2.metric(
        "Economy-wide exposure", f"{economy_w:.2f} / 10",
        delta=f"{economy_w - economy_u:+.2f} vs unweighted mean", delta_color="off",
        help="SUM(employment × exposure) / SUM(employment).", border=True,
    )
    k3.metric(
        "Workforce in high-exposure industries", f"{high_share:.0%}",
        help="Share of covered employment in industries tagged 'High Exposure (Accelerated Automation)'.",
        border=True,
    )
    k4.metric(
        "Most exposed sector", f"{top['employment_weighted_exposure']:.2f}",
        delta=top["sector_title"], delta_color="off", delta_arrow="off", border=True,
    )

    left, right = st.columns([3, 2], gap="medium")
    with left:
        with card("macro_sectors"):
            card_heading(
                "Sector exposure ranking",
                "Bars show the employment-weighted score. The periwinkle tick marks the unweighted mean of the "
                "sector's industries; the dashed line is the economy-wide average.",
            )
            st.altair_chart(_sector_chart(df_sec, economy_w), theme=None, width="stretch")

    with right:
        with card("macro_tiers"):
            card_heading("Workforce by exposure tier", "Share of covered employment in each BLS / O*NET tier.")
            st.altair_chart(_tier_chart(df_ind), theme=None, width="stretch")
            biggest_gap = df_sec.loc[df_sec["weighting_effect"].abs().idxmax()]
            insight(
                f"In <b>{biggest_gap['sector_title']}</b>, weighting by employment moves the score by "
                f"<span>{biggest_gap['weighting_effect']:+.2f}</span> against the unweighted mean."
            )

        with card("macro_large"):
            card_heading(
                "Most exposed large industries",
                "Detailed industries with at least 250,000 covered workers, ranked by exposure.",
            )
            large = df_ind[df_ind["covered_employment"] >= 250_000].head(6)
            st.dataframe(
                large[["industry_title", "covered_employment", "weighted_exposure"]],
                width="stretch",
                hide_index=True,
                column_config={
                    "industry_title": st.column_config.TextColumn("Industry", width="large"),
                    "covered_employment": st.column_config.NumberColumn("Employment", format="compact"),
                    "weighted_exposure": st.column_config.ProgressColumn(
                        "Exposure", min_value=0, max_value=10, format="%.2f"
                    ),
                },
            )

    section(
        "Drill-down",
        "Detailed industries within a sector",
        "Filter the 6-digit NAICS fact table by parent sector and exposure tier.",
    )
    with card("macro_drill"):
        c1, c2 = st.columns([2, 3], gap="medium")
        sector_titles = dict(zip(df_sec["sector_code"], df_sec["sector_title"]))
        with c1:
            sector = st.selectbox(
                "Parent sector",
                options=[None] + list(sector_titles.keys()),
                format_func=lambda c: "All sectors" if c is None else f"{c} · {sector_titles[c]}",
            )
        with c2:
            tiers = st.pills(
                "Exposure tier", TIER_ORDER, selection_mode="multi", default=TIER_ORDER, key="macro_tier_pills"
            )

        view = df_ind if sector is None else df_ind[df_ind["parent_sector_code"] == sector]
        view = view[view["tier"].isin(tiers or TIER_ORDER)]

        m1, m2, m3 = st.columns(3)
        m1.metric("Industries", f"{len(view):,}")
        m2.metric("Covered employment", f"{view['covered_employment'].sum() / 1e6:.2f}M")
        w = (
            (view["covered_employment"] * view["weighted_exposure"]).sum() / view["covered_employment"].sum()
            if len(view) else 0.0
        )
        m3.metric("Weighted exposure", f"{w:.2f}")
        if len(view):
            st.badge(f"{band_for_score(w)} exposure band", color=BADGE_COLORS[band_for_score(w)])

        _industry_table(view, height=420)

    with st.expander("SQL and methodology", icon=":material/code:"):
        st.code(QUERY_MACRO_EXPOSURE_BY_SECTOR.strip(), language="sql")
        st.markdown(
            "- `JOIN dim_naics_sectors` links each detailed industry to its parent via `parent_sector_code`.\n"
            "- `SUM(covered_employment * weighted_exposure) / SUM(covered_employment)` gives the employment-weighted mean.\n"
            "- `NULLIF(…, 0)` guards against division by zero in suppressed sectors.\n"
            "- Parent-sector summary rows are held in `dim_naics_sectors`, so workers are not counted twice."
        )
        st.caption("Exposure scores describe task-level potential. They do not forecast job loss or employment change.")
