# -*- coding: utf-8 -*-
"""
app.py — Sovereign Mind :: MENA Command
========================================
Streamlit cockpit. Reads data/data.json (refreshed hourly by processor.py)
and renders five fluid surfaces:

    PULSE              — live signal stream, persona-filtered
    BUTTERFLY MAP      — pydeck 3D globe with arcs
    HIDDEN LINKS       — streamlit-agraph network of clusters
    SOVEREIGN LENS     — per-event Scout interpretation
    DECISIONS          — gauges + swipeable recommendation cards

Aesthetic: dark "command center" with persona-tinted glows and a hairline
serif display face (Cormorant Garamond) paired with JetBrains Mono for data.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pydeck as pdk
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph

# Auto-refresh — soft import so the app still runs if package missing
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # pragma: no cover
    st_autorefresh = None  # type: ignore

from translations import (
    LANG_LABELS,
    PERSONAS,
    is_rtl,
    persona_doctrine,
    persona_name,
    t,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Sovereign Mind · MENA Command",
    page_icon="🜂",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Sovereign Mind · MENA Command — geopolitical intelligence console."},
)

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "data.json"


# ---------------------------------------------------------------------------
# Theme / CSS
# ---------------------------------------------------------------------------
def inject_css(persona_code: str, lang: str) -> None:
    p = PERSONAS[persona_code]
    primary = p["colors"]["primary"]
    accent = p["colors"]["accent"]
    glow = p["colors"]["glow"]
    rtl = is_rtl(lang)
    direction = "rtl" if rtl else "ltr"
    text_align = "right" if rtl else "left"

    # Arabic font stack switches when locale is RTL
    body_family = (
        "'Noto Naskh Arabic', 'Amiri', 'Cairo', serif"
        if rtl
        else "'Cormorant Garamond', 'EB Garamond', Georgia, serif"
    )
    display_family = (
        "'Reem Kufi', 'Cairo', sans-serif"
        if rtl
        else "'Cormorant Garamond', 'Playfair Display', serif"
    )
    mono_family = "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace"

    st.markdown(
        f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@300;400;500;700&family=Reem+Kufi:wght@400;500;600;700&family=Noto+Naskh+Arabic:wght@400;500;600;700&family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
:root {{
    --sm-primary: {primary};
    --sm-accent:  {accent};
    --sm-glow:    {glow};
    --sm-bg-0:    #05070D;
    --sm-bg-1:    #0A0E18;
    --sm-bg-2:    #111726;
    --sm-line:    rgba(255,255,255,0.06);
    --sm-line-2:  rgba(255,255,255,0.12);
    --sm-text:    #E6F1FF;
    --sm-muted:   #8A99B8;
    --sm-mono:    {mono_family};
    --sm-body:    {body_family};
    --sm-display: {display_family};
}}

html, body, [class*="css"], .stApp {{
    direction: {direction};
    text-align: {text_align};
    font-family: var(--sm-body);
    color: var(--sm-text);
    background: radial-gradient(1200px 700px at 15% -10%, rgba(0,212,255,0.06), transparent 60%),
                radial-gradient(900px 600px at 100% 110%, {primary}22, transparent 55%),
                #05070D;
}}

/* Subtle grain overlay */
.stApp::before {{
    content:"";
    position: fixed; inset: 0;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.025 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
    pointer-events: none;
    z-index: 0;
    opacity: .55;
}}
.main .block-container {{ position: relative; z-index: 1; padding-top: 1.2rem; }}

/* Hide Streamlit chrome we don't need */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header [data-testid="stHeader"] {{ background: transparent; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #07090F 0%, #0A0E18 100%);
    border-{ "left" if rtl else "right" }: 1px solid var(--sm-line);
}}
[data-testid="stSidebar"] * {{ direction: {direction}; text-align: {text_align}; }}

/* Display-grade headings */
h1, h2, h3 {{
    font-family: var(--sm-display);
    letter-spacing: 0.005em;
    color: var(--sm-text);
}}
h1 {{ font-weight: 500; font-size: clamp(2.1rem, 3vw, 3.2rem); line-height: 1.05; }}
h2 {{ font-weight: 500; font-size: 1.55rem; }}
h3 {{ font-weight: 600; font-size: 1.15rem; }}

/* Brand bar */
.sm-brandbar {{
    display: flex; align-items: baseline; gap: 1rem;
    padding: .25rem 0 .9rem;
    border-bottom: 1px solid var(--sm-line);
    margin-bottom: 1.2rem;
}}
.sm-brandbar .glyph {{
    font-family: var(--sm-display);
    font-weight: 300;
    font-size: 2.6rem;
    color: var(--sm-glow);
    text-shadow: 0 0 18px {glow}55, 0 0 2px {glow};
    line-height: 1;
}}
.sm-brandbar .title {{
    font-family: var(--sm-display);
    font-weight: 600;
    font-size: 1.6rem;
    letter-spacing: .12em;
    text-transform: uppercase;
}}
.sm-brandbar .sub {{
    font-family: var(--sm-mono);
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: .25em;
    color: var(--sm-muted);
    {('margin-right' if rtl else 'margin-left')}: auto;
}}
.sm-brandbar .pulse {{
    display: inline-block;
    width: 7px; height: 7px; border-radius: 50%;
    background: {glow};
    box-shadow: 0 0 12px {glow}, 0 0 2px {glow};
    animation: sm-pulse 1.6s ease-in-out infinite;
    {('margin-left' if rtl else 'margin-right')}: .5rem;
    transform: translateY(-2px);
}}
@keyframes sm-pulse {{
    0%, 100% {{ opacity: .35; transform: translateY(-2px) scale(.85); }}
    50%      {{ opacity: 1;   transform: translateY(-2px) scale(1.15); }}
}}

/* Persona doctrine card */
.sm-doctrine {{
    border: 1px solid var(--sm-line-2);
    border-{ "right" if rtl else "left" }: 3px solid var(--sm-glow);
    background: linear-gradient(135deg, rgba(255,255,255,.02), rgba(255,255,255,0));
    padding: 1rem 1.2rem;
    margin: 0 0 1.4rem;
    box-shadow: 0 0 32px {glow}10, inset 0 0 0 1px rgba(255,255,255,.02);
}}
.sm-doctrine .label {{
    font-family: var(--sm-mono);
    font-size: .68rem; letter-spacing: .28em; text-transform: uppercase;
    color: var(--sm-glow);
}}
.sm-doctrine .body {{
    font-family: var(--sm-display);
    font-style: italic;
    font-size: 1.15rem; line-height: 1.45;
    color: var(--sm-text);
    margin-top: .35rem;
}}

/* KPI tiles */
.sm-kpi {{
    border: 1px solid var(--sm-line-2);
    background: rgba(255,255,255,.015);
    padding: .9rem 1.1rem;
    position: relative; overflow: hidden;
}}
.sm-kpi::after {{
    content:""; position:absolute; inset: 0 auto 0 0; width: 2px;
    background: linear-gradient(180deg, transparent, var(--sm-glow), transparent);
    opacity: .5;
}}
.sm-kpi .lbl {{
    font-family: var(--sm-mono);
    font-size: .68rem; letter-spacing: .22em; text-transform: uppercase;
    color: var(--sm-muted);
}}
.sm-kpi .val {{
    font-family: var(--sm-display);
    font-size: 2rem; font-weight: 500;
    color: var(--sm-text);
    margin-top: .15rem;
}}
.sm-kpi .delta {{
    font-family: var(--sm-mono); font-size: .75rem; color: var(--sm-glow);
}}

/* Article / signal cards */
.sm-card {{
    border: 1px solid var(--sm-line);
    background: linear-gradient(180deg, rgba(255,255,255,.018), rgba(255,255,255,.005));
    padding: 1rem 1.15rem;
    margin-bottom: .85rem;
    transition: border-color .25s ease, transform .25s ease, box-shadow .25s ease;
    position: relative;
}}
.sm-card:hover {{
    border-color: {glow}55;
    box-shadow: 0 0 24px {glow}22;
    transform: translateY(-1px);
}}
.sm-card .meta {{
    font-family: var(--sm-mono);
    font-size: .68rem; letter-spacing: .14em; text-transform: uppercase;
    color: var(--sm-muted);
    display: flex; gap: .9rem; flex-wrap: wrap; align-items: center;
}}
.sm-card .meta .dot {{
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--sm-glow); box-shadow: 0 0 8px var(--sm-glow);
    display: inline-block;
}}
.sm-card .title {{
    font-family: var(--sm-display);
    font-size: 1.2rem; font-weight: 500; line-height: 1.3;
    margin: .35rem 0 .35rem;
}}
.sm-card .title a {{ color: var(--sm-text); text-decoration: none; }}
.sm-card .title a:hover {{ color: var(--sm-glow); }}
.sm-card .summary {{
    font-size: .92rem; line-height: 1.55; color: #B8C5DC;
}}
.sm-card .tagrow {{ margin-top: .55rem; display: flex; flex-wrap: wrap; gap: .35rem; }}
.sm-tag {{
    font-family: var(--sm-mono);
    font-size: .65rem; letter-spacing: .12em; text-transform: uppercase;
    padding: .2rem .55rem;
    border: 1px solid var(--sm-line-2);
    color: var(--sm-muted);
    border-radius: 2px;
}}
.sm-tag.hot   {{ color: #FF8A8A; border-color: #FF8A8A55; }}
.sm-tag.good  {{ color: #6EE7B7; border-color: #6EE7B755; }}
.sm-tag.cool  {{ color: var(--sm-glow); border-color: {glow}55; }}

/* Recommendation cards */
.sm-rec {{
    border: 1px solid var(--sm-line-2);
    padding: 1.1rem 1.25rem;
    background: linear-gradient(135deg, {primary}10, transparent 60%);
    margin-bottom: .9rem;
    position: relative;
}}
.sm-rec .badge {{
    font-family: var(--sm-mono);
    font-size: .65rem; letter-spacing: .2em; text-transform: uppercase;
    color: var(--sm-glow);
}}
.sm-rec .title {{
    font-family: var(--sm-display);
    font-weight: 600; font-size: 1.15rem; margin: .25rem 0 .45rem;
}}
.sm-rec .body  {{ font-size: .95rem; line-height: 1.6; color: #C8D4EA; }}
.sm-rec .foot  {{
    margin-top: .65rem;
    font-family: var(--sm-mono); font-size: .7rem; color: var(--sm-muted);
    display: flex; gap: 1rem;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 1.5rem;
    border-bottom: 1px solid var(--sm-line-2);
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    font-family: var(--sm-mono);
    font-size: .78rem;
    letter-spacing: .22em;
    text-transform: uppercase;
    color: var(--sm-muted);
    padding: .55rem 0;
}}
.stTabs [aria-selected="true"] {{
    color: var(--sm-text) !important;
    border-bottom: 2px solid var(--sm-glow) !important;
}}

/* Buttons */
.stButton > button {{
    font-family: var(--sm-mono);
    text-transform: uppercase;
    letter-spacing: .18em;
    font-size: .75rem;
    background: transparent;
    border: 1px solid var(--sm-line-2);
    color: var(--sm-text);
    border-radius: 0;
    padding: .5rem 1rem;
}}
.stButton > button:hover {{
    border-color: var(--sm-glow);
    color: var(--sm-glow);
    box-shadow: 0 0 14px {glow}33;
}}

/* Metric override */
[data-testid="stMetric"] {{
    background: rgba(255,255,255,.02);
    border: 1px solid var(--sm-line);
    padding: .7rem .9rem;
}}
[data-testid="stMetricLabel"] {{
    font-family: var(--sm-mono);
    font-size: .65rem !important; letter-spacing: .2em; text-transform: uppercase;
    color: var(--sm-muted) !important;
}}
[data-testid="stMetricValue"] {{
    font-family: var(--sm-display) !important;
    font-weight: 500 !important;
}}

/* Footer */
.sm-footer {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid var(--sm-line);
    font-family: var(--sm-mono);
    font-size: .68rem; letter-spacing: .18em; text-transform: uppercase;
    color: var(--sm-muted); text-align: center;
}}
</style>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def load_data() -> dict[str, Any]:
    if not DATA_PATH.exists():
        return _seed_data()
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        st.warning(f"data.json unreadable, using seed: {e}")
        return _seed_data()


def _seed_data() -> dict[str, Any]:
    """Demo data so the cockpit always renders, even before first cron run."""
    now = datetime.now(timezone.utc).isoformat()
    seed_articles = [
        {
            "id": "seed01",
            "title": "US tightens advanced-chip export controls toward Asia",
            "summary": "New rules expand restrictions on AI-grade semiconductors, prompting reroute of supply chains and renewed Gulf interest in domestic capacity.",
            "link": "https://example.com/a", "source": "Reuters World",
            "published": now, "region": "global", "lang": "en",
            "entities": ["US Commerce", "TSMC", "G42"],
            "geo_tags": ["US","TW","AE","SA"], "topics": ["semiconductors","export-controls","AI"],
            "sentiment": {"MA": 0.05, "SA": 0.20, "AE": 0.55},
            "risk":      {"MA": 0.20, "SA": 0.45, "AE": 0.40},
            "arc_to": ["AE","SA"], "arc_strength": {"MA":0.2,"SA":0.6,"AE":0.85},
            "hidden_links": ["C1"], "body": "",
        },
        {
            "id": "seed02",
            "title": "EU green hydrogen partnership with North Africa advances",
            "summary": "Brussels signals scale-up of cross-Mediterranean hydrogen corridor; Morocco positioned as anchor exporter.",
            "link": "https://example.com/b", "source": "FT World",
            "published": now, "region": "global", "lang": "en",
            "entities": ["EU Commission", "ONEE", "OCP"],
            "geo_tags": ["EU","MA","ES"], "topics": ["hydrogen","energy","trade"],
            "sentiment": {"MA": 0.75, "SA": 0.10, "AE": 0.05},
            "risk":      {"MA": 0.15, "SA": 0.10, "AE": 0.05},
            "arc_to": ["MA"], "arc_strength": {"MA":0.9,"SA":0.15,"AE":0.1},
            "hidden_links": ["C2"], "body": "",
        },
        {
            "id": "seed03",
            "title": "Red Sea shipping reroutes drive Gulf logistics demand",
            "summary": "Carriers extend Cape-of-Good-Hope detours; Jebel Ali and KAEC see throughput gains and rate spikes.",
            "link": "https://example.com/c", "source": "Bloomberg Markets",
            "published": now, "region": "global", "lang": "en",
            "entities": ["Maersk", "DP World", "Bahri"],
            "geo_tags": ["AE","SA","EG"], "topics": ["shipping","logistics","red-sea"],
            "sentiment": {"MA": -0.05, "SA": 0.35, "AE": 0.60},
            "risk":      {"MA": 0.10, "SA": 0.55, "AE": 0.50},
            "arc_to": ["AE","SA"], "arc_strength": {"MA":0.1,"SA":0.7,"AE":0.85},
            "hidden_links": ["C3"], "body": "",
        },
        {
            "id": "seed04",
            "title": "PIF announces fresh anchor commitment to AI compute fund",
            "summary": "Riyadh deepens stake in domestic AI infrastructure, with potential co-investments alongside MGX.",
            "link": "https://example.com/d", "source": "Arab News",
            "published": now, "region": "mena", "lang": "en",
            "entities": ["PIF", "MGX", "NVIDIA"],
            "geo_tags": ["SA","AE","US"], "topics": ["AI","sovereign-wealth","compute"],
            "sentiment": {"MA": 0.05, "SA": 0.70, "AE": 0.55},
            "risk":      {"MA": 0.05, "SA": 0.25, "AE": 0.20},
            "arc_to": ["SA","AE"], "arc_strength": {"MA":0.05,"SA":0.95,"AE":0.7},
            "hidden_links": ["C1"], "body": "",
        },
        {
            "id": "seed05",
            "title": "Atlantic gas discoveries off Mauritania-Senegal coast",
            "summary": "Field development progresses; downstream financing windows open for North African logistics partners.",
            "link": "https://example.com/e", "source": "Hespress EN",
            "published": now, "region": "mena", "lang": "en",
            "entities": ["BP", "Kosmos", "ONHYM"],
            "geo_tags": ["MR","SN","MA"], "topics": ["gas","atlantic","energy"],
            "sentiment": {"MA": 0.55, "SA": -0.10, "AE": 0.05},
            "risk":      {"MA": 0.20, "SA": 0.15, "AE": 0.10},
            "arc_to": ["MA"], "arc_strength": {"MA":0.85,"SA":0.1,"AE":0.1},
            "hidden_links": ["C2"], "body": "",
        },
    ]
    return {
        "generated_at": now,
        "model": "seed-fallback",
        "article_count": len(seed_articles),
        "articles": seed_articles,
        "clusters": [
            {"id": "C1", "label": "AI-Compute Sovereignty Bloc",
             "narrative": "US chip controls + PIF AI commitments compound: capital flows into Gulf-domiciled compute as Asia routes diversify.",
             "member_ids": ["seed01","seed04"], "personas": ["SA","AE"]},
            {"id": "C2", "label": "Atlantic-Med Energy Corridor",
             "narrative": "EU hydrogen pull + Atlantic gas finds reposition Morocco as the European energy gateway westward.",
             "member_ids": ["seed02","seed05"], "personas": ["MA"]},
            {"id": "C3", "label": "Red Sea Logistics Premium",
             "narrative": "Persistent Bab-el-Mandeb risk locks in elevated Gulf transshipment volumes through 2026.",
             "member_ids": ["seed03"], "personas": ["AE","SA"]},
        ],
        "recommendations": {
            "MA": [
                {"title":"Lock multi-year EU hydrogen offtake",
                 "body":"Use the Brussels signaling window to convert MOUs into binding offtakes with Spanish and German anchor buyers — Morocco's grid-link to Iberia is the moat. Pair with phosphate-DAP financing tied to the same instruments to compound African food-security narrative.",
                 "horizon":"30d","confidence":0.78},
                {"title":"Activate Atlantic Initiative downstream",
                 "body":"Position Tan-Tan / Dakhla as midstream nodes for Mauritania-Senegal gas; pre-build storage and regas optionality before majors finalize FIDs.",
                 "horizon":"7d","confidence":0.65},
            ],
            "SA": [
                {"title":"Move first on AI-compute domestication",
                 "body":"Translate PIF anchor into a sovereign GPU reserve. The chip-control window favors jurisdictions with capital + grid. Stand up KAUST + NEOM compute clusters as licensed partners before Asian capacity returns.",
                 "horizon":"30d","confidence":0.80},
                {"title":"Hedge Red Sea premium",
                 "body":"Bahri rate gains are real but fragile — lock 18-month charters now, redirect surplus margin to NEOM port build-out.",
                 "horizon":"7d","confidence":0.70},
            ],
            "AE": [
                {"title":"Capture chip-control arbitrage",
                 "body":"G42 + MGX should accelerate licensing dialogues with US Commerce. The ADGM-domiciled compute structure is the pitch — neutral, audited, rules-bound.",
                 "horizon":"24h","confidence":0.85},
                {"title":"Convert logistics windfall to permanent share",
                 "body":"Use Jebel Ali rate uplift to subsidize long-tenor shipper contracts; the goal is structural share, not cyclical profit.",
                 "horizon":"7d","confidence":0.72},
            ],
        },
        "advantage_index": {"MA": 0.42, "SA": 0.35, "AE": 0.55},
        "risk_index":      {"MA": 0.18, "SA": 0.32, "AE": 0.28},
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar(data: dict[str, Any]) -> tuple[str, str, int, bool, int]:
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: .25rem 0 1rem; border-bottom:1px solid var(--sm-line);">
                <div style="font-family: var(--sm-mono); font-size:.65rem; letter-spacing:.3em; color: var(--sm-muted); text-transform:uppercase;">
                    {t('sidebar_command', st.session_state.get('lang','en'))}
                </div>
                <div style="font-family: var(--sm-display); font-weight:600; font-size:1.2rem; margin-top:.2rem;">
                    🜂 Sovereign Mind
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Language first — so labels can re-render in chosen language
        lang = st.selectbox(
            t("sidebar_lang", st.session_state.get("lang", "en")),
            options=list(LANG_LABELS.keys()),
            format_func=lambda c: LANG_LABELS[c],
            index=list(LANG_LABELS.keys()).index(st.session_state.get("lang", "en")),
            key="lang_selector",
        )
        st.session_state["lang"] = lang

        # Persona toggle
        persona_codes = list(PERSONAS.keys())
        labels = {c: f"{PERSONAS[c]['flag']}  {persona_name(c, lang)}" for c in persona_codes}
        persona = st.radio(
            t("sidebar_persona", lang),
            options=persona_codes,
            format_func=lambda c: labels[c],
            index=persona_codes.index(st.session_state.get("persona", "MA")),
            key="persona_selector",
        )
        st.session_state["persona"] = persona

        horizon = st.slider(
            t("sidebar_horizon", lang),
            min_value=6, max_value=72, value=24, step=6,
        )

        st.markdown("---")
        if st.button(t("sidebar_refresh", lang), use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        # Auto-refresh control — defaults to ON at 180s (3 min)
        auto_on = st.toggle(
            t("sidebar_autorefresh", lang),
            value=st.session_state.get("autorefresh_on", True),
            key="autorefresh_on",
        )
        interval_s = st.select_slider(
            t("sidebar_autorefresh_interval", lang),
            options=[60, 120, 180, 300, 600, 900],
            value=st.session_state.get("autorefresh_interval", 180),
            format_func=lambda s: f"{s//60}m" if s >= 60 else f"{s}s",
            key="autorefresh_interval",
            disabled=not auto_on,
        )

        st.markdown("---")
        st.markdown(
            f"""
            <div style="font-family: var(--sm-mono); font-size:.7rem; color: var(--sm-muted); line-height:1.7;">
                <div style="letter-spacing:.2em; text-transform:uppercase; color:var(--sm-glow); margin-bottom:.4rem;">
                    {t('sidebar_status', lang)}
                </div>
                <div>{t('sidebar_last_sync', lang)}: <span style="color:var(--sm-text)">{_fmt_dt(data.get('generated_at'))}</span></div>
                <div>{t('sidebar_articles_loaded', lang)}: <span style="color:var(--sm-text)">{data.get('article_count', 0)}</span></div>
                <div>Model: <span style="color:var(--sm-text)">scout-17b-16e</span></div>
                <div>{t('sidebar_next_refresh', lang)}: <span style="color:var(--sm-text)">{interval_s}s</span> {'<span style="color:var(--sm-glow)">●</span>' if auto_on else '<span style="color:#555">○</span>'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return persona, lang, horizon, auto_on, interval_s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso[:19]


def _filter_articles(data: dict[str, Any], persona: str, horizon_h: int) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc).timestamp() - (horizon_h * 3600)
    rows: list[dict[str, Any]] = []
    for a in data.get("articles", []):
        try:
            ts = datetime.fromisoformat(a["published"].replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = datetime.now(timezone.utc).timestamp()
        if ts < cutoff:
            continue
        sent = float(a.get("sentiment", {}).get(persona, 0.0))
        risk = float(a.get("risk", {}).get(persona, 0.0))
        arc = float(a.get("arc_strength", {}).get(persona, 0.0))
        # Ranking score: combination of relevance + magnitude
        score = arc * 0.5 + abs(sent) * 0.3 + risk * 0.2
        rows.append({**a, "_score": score, "_ts": ts})
    rows.sort(key=lambda r: r["_score"], reverse=True)
    return rows


def _band_label(score: float, lang: str) -> tuple[str, str]:
    """Return (label, css class) for a magnitude band."""
    a = abs(score)
    if a >= 0.7:
        return t("score_critical", lang), "hot"
    if a >= 0.45:
        return t("score_high", lang), "hot" if score < 0 else "good"
    if a >= 0.2:
        return t("score_moderate", lang), "cool"
    return t("score_low", lang), "cool"


# ---------------------------------------------------------------------------
# Brand bar + doctrine
# ---------------------------------------------------------------------------
def render_brand(persona: str, lang: str) -> None:
    p = PERSONAS[persona]
    st.markdown(
        f"""
        <div class="sm-brandbar">
            <div class="glyph">🜂</div>
            <div>
                <div class="title">{t('app_title', lang)}</div>
                <div style="font-family: var(--sm-mono); font-size:.7rem; letter-spacing:.22em; color: var(--sm-muted); text-transform:uppercase;">
                    {t('app_subtitle', lang)}
                </div>
            </div>
            <div class="sub"><span class="pulse"></span>{p['flag']} {persona_name(persona, lang)}</div>
        </div>
        <div class="sm-doctrine">
            <div class="label">DOCTRINE · {p['flag']} {p['code']}</div>
            <div class="body">"{persona_doctrine(persona, lang)}"</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# KPI strip
# ---------------------------------------------------------------------------
def render_kpis(data: dict[str, Any], persona: str, articles: list[dict[str, Any]], lang: str) -> None:
    adv = float(data.get("advantage_index", {}).get(persona, 0.0))
    risk = float(data.get("risk_index", {}).get(persona, 0.0))
    n_signals = len(articles)
    n_clusters = sum(1 for c in data.get("clusters", []) if persona in c.get("personas", []))

    cols = st.columns(4, gap="small")
    tiles = [
        (t("advantage_meter", lang), f"{adv:+.2f}", "−1.00 ⟶ +1.00"),
        (t("risk_meter", lang),       f"{risk:.2f}", "0.00 ⟶ 1.00"),
        ("SIGNALS",                   f"{n_signals}", "in window"),
        ("HIDDEN LINKS",              f"{n_clusters}", "active clusters"),
    ]
    for col, (lbl, val, sub) in zip(cols, tiles):
        with col:
            st.markdown(
                f"""<div class="sm-kpi">
                    <div class="lbl">{lbl}</div>
                    <div class="val">{val}</div>
                    <div class="delta">{sub}</div>
                </div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
def render_pulse(articles: list[dict[str, Any]], persona: str, lang: str) -> None:
    st.markdown(f"### {t('pulse_header', lang)}")
    st.caption(t("pulse_caption", lang))
    if not articles:
        st.info(t("no_data", lang))
        return
    for a in articles[:30]:
        sent = float(a.get("sentiment", {}).get(persona, 0.0))
        risk = float(a.get("risk", {}).get(persona, 0.0))
        sent_label, sent_class = _band_label(sent, lang)
        topics = a.get("topics") or []
        ents = a.get("entities") or []
        tag_html = "".join(
            [f'<span class="sm-tag cool">#{tp}</span>' for tp in topics[:4]] +
            [f'<span class="sm-tag">{e}</span>' for e in ents[:3]]
        )
        st.markdown(
            f"""
            <div class="sm-card">
                <div class="meta">
                    <span class="dot"></span>
                    <span>{a['source']}</span>
                    <span>· {_fmt_dt(a['published'])}</span>
                    <span>· {a.get('region','—').upper()}</span>
                    <span style="margin-{ 'right' if is_rtl(lang) else 'left' }:auto;" class="sm-tag {sent_class}">
                        {sent_label} · ADV {sent:+.2f} · RISK {risk:.2f}
                    </span>
                </div>
                <div class="title"><a href="{a['link']}" target="_blank" rel="noopener">{a['title']}</a></div>
                <div class="summary">{a.get('summary','')}</div>
                <div class="tagrow">{tag_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_butterfly(data: dict[str, Any], articles: list[dict[str, Any]], persona: str, lang: str) -> None:
    st.markdown(f"### {t('butterfly_header', lang)}")
    st.caption(t("butterfly_caption", lang))

    capitals = {code: PERSONAS[code]["capital"] for code in PERSONAS}

    # Approximate centroid of geo_tags via a small lookup
    geo_lookup = _geo_centroids()

    arcs: list[dict[str, Any]] = []
    points: list[dict[str, Any]] = []
    for a in articles[:80]:
        # Pick a representative source coordinate
        src_lat, src_lon = None, None
        for tag in a.get("geo_tags", []):
            if tag in geo_lookup and tag not in ("MA","SA","AE"):
                src_lat, src_lon = geo_lookup[tag]
                break
        if src_lat is None:
            # fallback — randomish around equator based on hash
            h = int(a.get("id","0")[:6], 16) if a.get("id") else 0
            src_lat = ((h % 140) - 70)
            src_lon = (((h >> 4) % 340) - 170)

        points.append({
            "lat": src_lat, "lon": src_lon,
            "name": a["title"][:80],
            "score": float(a.get("arc_strength", {}).get(persona, 0.0)),
        })

        for code, cap in capitals.items():
            strength = float(a.get("arc_strength", {}).get(code, 0.0))
            if strength < 0.25:
                continue
            sent = float(a.get("sentiment", {}).get(code, 0.0))
            color = _arc_color(sent)
            # Highlight active persona
            alpha = 220 if code == persona else 70
            arcs.append({
                "from_lat": src_lat, "from_lon": src_lon,
                "to_lat": cap["lat"], "to_lon": cap["lon"],
                "width": 1 + strength * 5,
                "color": color + [alpha],
                "tooltip": f"{a['title'][:70]} → {cap['name']} · ADV {sent:+.2f}",
            })

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=arcs,
        get_source_position=["from_lon", "from_lat"],
        get_target_position=["to_lon", "to_lat"],
        get_source_color="color",
        get_target_color="color",
        get_width="width",
        get_height=0.4,
        pickable=True,
        auto_highlight=True,
    )

    src_layer = pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position=["lon", "lat"],
        get_radius=80000,
        get_fill_color=[230, 241, 255, 180],
        pickable=True,
    )

    cap_data = [{
        "lat": c["lat"], "lon": c["lon"], "name": f"{PERSONAS[code]['flag']} {c['name']}",
        "is_active": code == persona,
    } for code, c in capitals.items()]
    cap_layer = pdk.Layer(
        "ScatterplotLayer",
        data=cap_data,
        get_position=["lon", "lat"],
        get_radius=180000,
        get_fill_color=[255, 90, 90, 220],
        pickable=True,
    )

    cap_active = capitals[persona]
    view = pdk.ViewState(
        latitude=cap_active["lat"], longitude=cap_active["lon"],
        zoom=2.1, pitch=42, bearing=0,
    )
    deck = pdk.Deck(
        layers=[arc_layer, src_layer, cap_layer],
        initial_view_state=view,
        map_style=None,                  # transparent — let our dark theme show through
        tooltip={"text": "{tooltip}{name}"},
    )
    st.pydeck_chart(deck, use_container_width=True)


def _arc_color(sent: float) -> list[int]:
    """Green for positive advantage, amber for neutral, red for negative."""
    if sent >= 0.25:
        return [0, 230, 118]      # emerald
    if sent <= -0.25:
        return [255, 80, 80]      # crimson
    return [255, 200, 0]          # amber


def _geo_centroids() -> dict[str, tuple[float, float]]:
    return {
        "US": (39.8, -98.6), "CA": (56, -106), "MX": (23, -102),
        "BR": (-14, -52), "AR": (-34, -64),
        "GB": (54, -2), "EU": (50, 10), "FR": (46, 2), "DE": (51, 10), "ES": (40, -4), "IT": (42, 12),
        "RU": (61, 105), "UA": (49, 31), "TR": (39, 35),
        "CN": (35, 105), "JP": (36, 138), "KR": (37, 127), "TW": (23, 121),
        "IN": (21, 78), "PK": (30, 70), "ID": (-2, 117),
        "EG": (27, 30), "DZ": (28, 3), "TN": (34, 9), "LY": (27, 17),
        "MA": (32, -6), "SA": (24, 45), "AE": (24, 54), "QA": (25, 51), "KW": (29, 47), "OM": (21, 56), "BH": (26, 50),
        "IR": (32, 53), "IQ": (33, 44), "SY": (35, 38), "LB": (33.8, 35.8), "JO": (31, 36), "IL": (31, 35), "YE": (15, 48),
        "SD": (15, 30), "ET": (9, 40), "KE": (-1, 38), "NG": (10, 8), "ZA": (-30, 25),
        "MR": (20, -10), "SN": (14, -14),
        "AU": (-25, 133),
    }


def render_network(data: dict[str, Any], articles: list[dict[str, Any]], persona: str, lang: str) -> None:
    st.markdown(f"### {t('network_header', lang)}")
    st.caption(t("network_caption", lang))

    clusters = [c for c in data.get("clusters", []) if persona in c.get("personas", [])] or data.get("clusters", [])
    if not clusters and not articles:
        st.info(t("no_data", lang))
        return

    p = PERSONAS[persona]
    nodes: list[Node] = []
    edges: list[Edge] = []
    seen_nodes: set[str] = set()

    # Persona node — visual gravity center
    persona_id = f"persona::{persona}"
    nodes.append(Node(
        id=persona_id,
        label=f"{p['flag']} {persona}",
        size=42,
        color=p["colors"]["glow"],
        shape="diamond",
    ))
    seen_nodes.add(persona_id)

    # Cluster nodes
    for c in clusters:
        cid = f"cluster::{c['id']}"
        nodes.append(Node(
            id=cid,
            label=c.get("label", c["id"]),
            size=30,
            color=p["colors"]["primary"],
            shape="hexagon",
        ))
        seen_nodes.add(cid)
        edges.append(Edge(source=cid, target=persona_id, type="CURVE_SMOOTH", color="#888"))

        # Member articles + entities
        for art_id in c.get("member_ids", []):
            art = next((a for a in articles if a.get("id") == art_id), None)
            if not art:
                continue
            aid = f"event::{art_id}"
            if aid not in seen_nodes:
                nodes.append(Node(
                    id=aid,
                    label=art["title"][:55] + ("…" if len(art["title"]) > 55 else ""),
                    size=18,
                    color="#E6F1FF",
                ))
                seen_nodes.add(aid)
            edges.append(Edge(source=aid, target=cid))

            for ent in (art.get("entities") or [])[:3]:
                eid = f"entity::{ent}"
                if eid not in seen_nodes:
                    nodes.append(Node(
                        id=eid, label=ent, size=12, color="#8A99B8",
                    ))
                    seen_nodes.add(eid)
                edges.append(Edge(source=eid, target=aid))

    # If no clusters in window, fall back to top events for persona
    if not clusters:
        for art in articles[:8]:
            aid = f"event::{art['id']}"
            if aid not in seen_nodes:
                nodes.append(Node(id=aid, label=art["title"][:55], size=18, color="#E6F1FF"))
                seen_nodes.add(aid)
                edges.append(Edge(source=aid, target=persona_id))

    config = Config(
        width="100%", height=560,
        directed=True,
        physics=True, hierarchical=False,
        nodeHighlightBehavior=True, highlightColor=p["colors"]["glow"],
        collapsible=False,
        backgroundColor="rgba(0,0,0,0)",
        node={"labelProperty": "label", "renderLabel": True, "fontColor": "#E6F1FF"},
        link={"renderLabel": False, "highlightColor": p["colors"]["glow"]},
    )
    agraph(nodes=nodes, edges=edges, config=config)

    # Cluster narratives below the graph
    for c in clusters:
        st.markdown(
            f"""
            <div class="sm-card">
                <div class="meta">
                    <span class="dot"></span>
                    <span>CLUSTER · {c['id']}</span>
                    <span>· {len(c.get('member_ids', []))} signals</span>
                    <span>· {' '.join(PERSONAS[code]['flag'] for code in c.get('personas', []))}</span>
                </div>
                <div class="title">{c.get('label','')}</div>
                <div class="summary">{c.get('narrative','')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_lens(articles: list[dict[str, Any]], persona: str, lang: str) -> None:
    st.markdown(f"### {t('lens_header', lang)}")
    st.caption(t("lens_caption", lang))
    if not articles:
        st.info(t("no_data", lang))
        return

    p = PERSONAS[persona]
    pillars = p["pillars"]

    # Aggregate sentiment per topic
    rows = []
    for a in articles:
        for tp in a.get("topics", []) or []:
            rows.append({
                "topic": tp,
                "advantage": float(a.get("sentiment", {}).get(persona, 0.0)),
                "risk": float(a.get("risk", {}).get(persona, 0.0)),
            })
    if rows:
        df = pd.DataFrame(rows).groupby("topic", as_index=False).agg(
            advantage=("advantage", "mean"),
            risk=("risk", "mean"),
            count=("topic", "count"),
        ).sort_values("count", ascending=False).head(12)

        st.markdown("##### Topic Heat — your sovereign exposure")
        st.dataframe(
            df.style.format({"advantage": "{:+.2f}", "risk": "{:.2f}"}),
            use_container_width=True, hide_index=True,
        )

    st.markdown("##### Pillar Alignment")
    cols = st.columns(len(pillars))
    for col, pillar in zip(cols, pillars):
        # Naive alignment: how many articles' topics share keywords with pillar text
        kws = [w.lower() for w in pillar.replace("/", " ").replace("&", " ").split() if len(w) > 3]
        score = 0.0; n = 0
        for a in articles:
            text = " ".join([a.get("title",""), a.get("summary","")] + (a.get("topics") or [])).lower()
            if any(k in text for k in kws):
                score += float(a.get("sentiment", {}).get(persona, 0.0))
                n += 1
        avg = (score / n) if n else 0.0
        with col:
            st.markdown(
                f"""<div class="sm-kpi">
                    <div class="lbl">{pillar}</div>
                    <div class="val">{avg:+.2f}</div>
                    <div class="delta">{n} signals</div>
                </div>""",
                unsafe_allow_html=True,
            )


def render_decisions(data: dict[str, Any], persona: str, lang: str) -> None:
    st.markdown(f"### {t('decisions_header', lang)}")

    # Gauges
    adv = float(data.get("advantage_index", {}).get(persona, 0.0))
    risk = float(data.get("risk_index", {}).get(persona, 0.0))
    p = PERSONAS[persona]

    col1, col2 = st.columns(2)
    with col1:
        _gauge(t("advantage_meter", lang), adv, vmin=-1, vmax=1, color=p["colors"]["glow"])
    with col2:
        _gauge(t("risk_meter", lang), risk, vmin=0, vmax=1, color="#FF5050", invert_good=True)

    recs = data.get("recommendations", {}).get(persona, [])
    if not recs:
        st.info(t("no_data", lang))
        return

    for r in recs:
        st.markdown(
            f"""
            <div class="sm-rec">
                <div class="badge">{t('recommend_card', lang)} · {r.get('horizon','7d').upper()}</div>
                <div class="title">{r.get('title','')}</div>
                <div class="body">{r.get('body','')}</div>
                <div class="foot">
                    <span>CONFIDENCE · {float(r.get('confidence',0))*100:.0f}%</span>
                    <span>VOICE · {p['flag']} {persona_name(persona, lang).split('—')[-1].strip()}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _gauge(label: str, value: float, vmin: float, vmax: float, color: str, invert_good: bool = False) -> None:
    """Lightweight SVG arc gauge — no extra deps, RTL-safe."""
    v = max(vmin, min(vmax, value))
    pct = (v - vmin) / (vmax - vmin) if vmax != vmin else 0
    # arc from -135deg to +135deg (270 degrees of sweep)
    sweep = 270
    start = -225  # CSS rotation: arc bottom-left
    angle = start + sweep * pct
    # Big number formatting
    big = f"{value:+.2f}" if vmin < 0 else f"{value:.2f}"
    quality = "RISK" if invert_good else ("STRONG" if value > 0.3 else "WEAK" if value < -0.1 else "NEUTRAL")
    if invert_good:
        quality = "ELEVATED" if value > 0.5 else "MODERATE" if value > 0.25 else "CONTAINED"

    # Build the SVG
    radius = 70
    cx, cy = 90, 95
    def polar(a_deg, r):
        a = math.radians(a_deg)
        return cx + r * math.cos(a), cy + r * math.sin(a)
    x1, y1 = polar(start, radius)
    x2, y2 = polar(angle, radius)
    large_arc = 1 if (angle - start) > 180 else 0
    bg_x2, bg_y2 = polar(start + sweep, radius)

    svg = f"""
<svg viewBox="0 0 180 130" width="100%" style="max-width:280px; display:block; margin: .2rem auto .6rem;">
  <defs>
    <linearGradient id="grad-{label[:3]}" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0%"  stop-color="{color}" stop-opacity="0.1"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="1"/>
    </linearGradient>
    <filter id="glow-{label[:3]}"><feGaussianBlur stdDeviation="2.4"/></filter>
  </defs>
  <!-- track -->
  <path d="M {x1:.1f} {y1:.1f} A {radius} {radius} 0 1 1 {bg_x2:.1f} {bg_y2:.1f}"
        fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="10" stroke-linecap="round"/>
  <!-- value -->
  <path d="M {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large_arc} 1 {x2:.1f} {y2:.1f}"
        fill="none" stroke="url(#grad-{label[:3]})" stroke-width="10" stroke-linecap="round"
        filter="url(#glow-{label[:3]})"/>
  <text x="{cx}" y="{cy-2}" text-anchor="middle"
        font-family="'Cormorant Garamond', serif" font-weight="500" font-size="32" fill="#E6F1FF">{big}</text>
  <text x="{cx}" y="{cy+18}" text-anchor="middle"
        font-family="'JetBrains Mono', monospace" font-size="9"
        letter-spacing="3" fill="{color}">{quality}</text>
</svg>
"""
    st.markdown(
        f"""<div style="border:1px solid var(--sm-line-2); padding: .8rem; background: rgba(255,255,255,.015);">
                <div style="font-family: var(--sm-mono); font-size:.65rem; letter-spacing:.22em; text-transform:uppercase; color: var(--sm-muted); text-align:center;">{label}</div>
                {svg}
            </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.session_state.setdefault("lang", "en")
    st.session_state.setdefault("persona", "MA")

    data = load_data()
    persona, lang, horizon, auto_on, interval_s = render_sidebar(data)

    # Auto-refresh: re-runs the script every `interval_s` seconds. We clear the
    # data cache when the tick count changes so the JSON is re-read from disk
    # (otherwise the @st.cache_data ttl=60 would still gate it).
    if auto_on and st_autorefresh is not None:
        tick = st_autorefresh(interval=interval_s * 1000, key="sm_autorefresh")
        last_tick = st.session_state.get("_last_autorefresh_tick")
        if last_tick is not None and tick != last_tick:
            st.cache_data.clear()
            data = load_data()           # re-read with fresh cache
        st.session_state["_last_autorefresh_tick"] = tick

    inject_css(persona, lang)
    render_brand(persona, lang)

    articles = _filter_articles(data, persona, horizon)
    render_kpis(data, persona, articles, lang)
    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    tabs = st.tabs([
        t("tab_pulse",    lang),
        t("tab_butterfly", lang),
        t("tab_network", lang),
        t("tab_lens",    lang),
        t("tab_decisions", lang),
    ])
    with tabs[0]: render_pulse(articles, persona, lang)
    with tabs[1]: render_butterfly(data, articles, persona, lang)
    with tabs[2]: render_network(data, articles, persona, lang)
    with tabs[3]: render_lens(articles, persona, lang)
    with tabs[4]: render_decisions(data, persona, lang)

    st.markdown(f'<div class="sm-footer">{t("footer", lang)}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
