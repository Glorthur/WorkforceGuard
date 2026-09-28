"""
WorkforceGuard brand layer: design tokens, Altair theme, global CSS and small
presentation helpers shared by every tab module. No data access lives here.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

# --- Tokens (Midnight Slate & Electric Cobalt) --------------------------------
OBSIDIAN = "#020617"
SLATE_NAVY = "#0f172a"
SLATE_800 = "#1e293b"
BORDER = "#26334f"
COBALT = "#2563eb"
PERIWINKLE = "#7fa2ff"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
CRIMSON = "#ef4444"
AMBER = "#f59e0b"
EMERALD = "#10b981"

SERIF = '"Source Serif 4", Georgia, serif'
SANS = 'Inter, Archivo, system-ui, sans-serif'
MONO = '"IBM Plex Mono", ui-monospace, monospace'

TIER_ORDER = ["High", "Moderate", "Low"]
TIER_COLORS = {"High": CRIMSON, "Moderate": AMBER, "Low": EMERALD}
BADGE_COLORS = {"High": "red", "Moderate": "orange", "Low": "green"}

# Exposure bands implied by the BLS/O*NET tier labels in fact_industry_exposure.
HIGH_EXPOSURE_MIN = 7.5
MODERATE_EXPOSURE_MIN = 5.5


def short_tier(label: str) -> str:
    """Collapses verbose tier labels ('High Exposure (Accelerated ...)') to High / Moderate / Low."""
    s = str(label).strip().lower()
    if s.startswith("very high") or s.startswith("high"):
        return "High"
    if s.startswith("moderate"):
        return "Moderate"
    return "Low"


def band_for_score(score: float) -> str:
    if score >= HIGH_EXPOSURE_MIN:
        return "High"
    if score >= MODERATE_EXPOSURE_MIN:
        return "Moderate"
    return "Low"


def to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """MySQL DECIMAL columns arrive as Python Decimal; coerce for charting and arithmetic."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


# --- Altair theme -------------------------------------------------------------
def _altair_theme() -> dict:
    axis = {
        "labelColor": MUTED,
        "titleColor": MUTED,
        "labelFont": SANS,
        "titleFont": SANS,
        "labelFontSize": 11,
        "titleFontSize": 11,
        "titleFontWeight": 500,
        "titlePadding": 10,
        "gridColor": SLATE_800,
        "domainColor": BORDER,
        "tickColor": BORDER,
        "labelLimit": 260,
    }
    return {
        "config": {
            "background": "transparent",
            "font": SANS,
            "view": {"stroke": None},
            "axis": axis,
            "axisY": {"grid": False, "domain": False, "ticks": False, "labelPadding": 8},
            "legend": {
                "labelColor": TEXT,
                "titleColor": MUTED,
                "labelFont": SANS,
                "titleFont": SANS,
                "labelFontSize": 12,
                "titleFontSize": 11,
                "titleFontWeight": 500,
                "orient": "top",
                "symbolType": "square",
            },
            "title": {"color": TEXT, "font": SERIF, "fontSize": 16, "fontWeight": 600, "anchor": "start"},
            "range": {"category": [COBALT, PERIWINKLE, EMERALD, AMBER, CRIMSON, MUTED]},
            "bar": {"cornerRadiusEnd": 2},
            "text": {"font": MONO, "color": TEXT, "fontSize": 11},
        }
    }


def register_altair_theme() -> None:
    try:  # Altair >= 5.5
        alt.theme.register("workforceguard", enable=True)(_altair_theme)
    except AttributeError:  # Altair < 5.5
        alt.themes.register("workforceguard", _altair_theme)
        alt.themes.enable("workforceguard")


# --- Global CSS ---------------------------------------------------------------
def inject_css() -> None:
    st.html(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&family=Inter:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1400px; }}

/* Bordered cards: keyed containers (card_*) and bordered metrics get the surface colour */
[class*="st-key-card_"] {{ background: {SLATE_NAVY}; }}
div[data-testid="stMetric"] {{ background: {SLATE_NAVY}; }}
[data-testid="stMetricLabel"] p {{
  font-family: {MONO}; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: {MUTED};
}}
[data-testid="stMetricValue"] {{ font-family: {SERIF}; font-weight: 600; letter-spacing: -0.01em; }}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{ padding: 10px 14px; color: {MUTED}; }}
.stTabs [data-baseweb="tab"]:hover {{ color: {PERIWINKLE}; }}
.stTabs [aria-selected="true"] {{ color: {TEXT}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {COBALT}; height: 2px; }}

/* Vega tooltip */
#vg-tooltip-element {{
  background: {SLATE_800}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 6px;
  font-family: {SANS}; font-size: 12px; box-shadow: 0 8px 24px rgba(2,6,23,.6);
}}
#vg-tooltip-element td.key {{ color: {MUTED}; }}

/* Brand primitives */
.wg-eyebrow {{ font-family: {MONO}; font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase; color: {PERIWINKLE}; }}
.wg-hero {{
  border: 1px solid {BORDER}; border-radius: 10px; padding: 36px 40px 30px;
  background:
    radial-gradient(900px 260px at 0% 0%, rgba(37,99,235,.16), transparent 60%),
    {SLATE_NAVY};
}}
.wg-hero h1 {{ font-family: {SERIF}; font-weight: 600; font-size: 2.5rem; line-height: 1.12; letter-spacing: -0.015em; color: {TEXT}; margin: 10px 0 12px; padding: 0; }}
.wg-hero p {{ font-family: {SANS}; color: {MUTED}; font-size: 1.02rem; line-height: 1.6; max-width: 760px; margin: 0; }}
.wg-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }}
.wg-chip {{
  font-family: {MONO}; font-size: 0.72rem; color: {TEXT}; background: {OBSIDIAN};
  border: 1px solid {BORDER}; border-radius: 4px; padding: 5px 9px;
}}
.wg-chip b {{ color: {PERIWINKLE}; font-weight: 500; }}
.wg-section {{ margin: 8px 0 4px; }}
.wg-section h3 {{ font-family: {SERIF}; font-weight: 600; font-size: 1.45rem; color: {TEXT}; margin: 6px 0 6px; padding: 0; letter-spacing: -0.01em; }}
.wg-section p {{ font-family: {SANS}; color: {MUTED}; font-size: 0.95rem; line-height: 1.6; max-width: 820px; margin: 0; }}
.wg-card-title {{ font-family: {SERIF}; font-weight: 600; font-size: 1.1rem; color: {TEXT}; margin: 0 0 2px; }}
.wg-card-sub {{ font-family: {SANS}; color: {MUTED}; font-size: 0.85rem; line-height: 1.5; margin: 0; }}
.wg-insight {{
  border-left: 2px solid {COBALT}; padding: 4px 0 4px 14px; color: {TEXT};
  font-family: {SERIF}; font-size: 1.05rem; line-height: 1.55;
}}
.wg-insight span {{ color: {PERIWINKLE}; font-family: {MONO}; font-size: 0.95rem; }}
.wg-wordmark {{ font-family: {SERIF}; font-weight: 700; font-size: 1.5rem; color: {TEXT}; letter-spacing: -0.01em; }}
.wg-wordmark span {{ color: {PERIWINKLE}; }}
</style>
"""
    )


# --- Presentation helpers -----------------------------------------------------
def hero(eyebrow: str, title: str, subtitle: str, chips: list[tuple[str, str]]) -> None:
    chip_html = "".join(f'<span class="wg-chip"><b>{k}</b> {v}</span>' for k, v in chips)
    st.html(
        f"""<div class="wg-hero">
  <div class="wg-eyebrow">{eyebrow}</div>
  <h1>{title}</h1>
  <p>{subtitle}</p>
  <div class="wg-meta">{chip_html}</div>
</div>"""
    )


def section(eyebrow: str, title: str, blurb: str | None = None) -> None:
    body = f"<p>{blurb}</p>" if blurb else ""
    st.html(f'<div class="wg-section"><div class="wg-eyebrow">{eyebrow}</div><h3>{title}</h3>{body}</div>')


def card_heading(title: str, sub: str | None = None) -> None:
    sub_html = f'<p class="wg-card-sub">{sub}</p>' if sub else ""
    st.html(f'<div><p class="wg-card-title">{title}</p>{sub_html}</div>')


def insight(html_text: str) -> None:
    st.html(f'<div class="wg-insight">{html_text}</div>')


def card(key: str, **kwargs):
    """Bordered surface container. The key yields the CSS class `st-key-card_<key>`."""
    return st.container(border=True, key=f"card_{key}", **kwargs)
