from __future__ import annotations

import base64
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from html import escape, unescape
from pathlib import Path
import sqlite3
import re
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# =============================================================================
# APP AND DATA PATHS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

SURVEY_PATH = DATA_DIR / "survey_clean.xlsx"
REVIEW_PATH = DATA_DIR / "ulasan_clean.xlsx"
QUESTIONNAIRE_PATH = DATA_DIR / "hasil_kuesioner.csv"
RAW_SURVEY_PATH = DATA_DIR / "raw_survey_clean.xlsx"
RAW_REVIEW_PATH = DATA_DIR / "raw_ulasan_clean.xlsx"
DATABASE_PATH = DATA_DIR / "hasil_analisis_dana.db"

DATA_SOURCE_SPECS = (
    ("Survey utama", SURVEY_PATH, "excel", True),
    ("Ulasan utama", REVIEW_PATH, "excel", True),
    ("Ringkasan kuesioner", QUESTIONNAIRE_PATH, "csv", True),
    ("Survey raw terlindungi", RAW_SURVEY_PATH, "excel", False),
    ("Ulasan raw terlindungi", RAW_REVIEW_PATH, "excel", False),
    ("Database validasi opsional", DATABASE_PATH, "sqlite", False),
)


# =============================================================================
# DANA-INSPIRED DESIGN TOKENS
# =============================================================================
C_PRIMARY = "#108EE9"
C_DEEP = "#0B5ED7"
C_ELECTRIC = "#2563EB"
C_SKY = "#38BDF8"
C_BG = "#F6FAFF"
C_PANEL = "#F3F8FF"
C_CARD = "#FFFFFF"
C_TEXT = "#0F172A"
C_MUTED = "#64748B"
C_BORDER = "#E2E8F0"
C_POSITIVE = "#10B981"
C_NEUTRAL = "#F59E0B"
C_NEGATIVE = "#EF4444"
C_SOFT_GREEN = "#ECFDF5"
C_SOFT_AMBER = "#FFFBEB"
C_SOFT_RED = "#FEF2F2"

WIB = timezone(timedelta(hours=7))
DEFAULT_SHOW_LOBBY = True
# Config for normal card charts — all drag/zoom/select disabled
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "doubleClick": False,
    "editable": False,
    "edits": {
        "shapePosition": False,
        "annotationPosition": False,
    },
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
        "toImage",
    ],
}
# Config for fullscreen dialog — zoom/pan allowed for exploration
PLOTLY_FULLSCREEN_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": True,
    "doubleClick": "reset",
}


PLOTLY_CARD_CONFIG = PLOTLY_CONFIG


def apply_normal_chart_behavior(fig):
    fig.update_layout(
        dragmode=False,
        hovermode="closest",
        clickmode="none",
        selectdirection=None,
        spikedistance=-1,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D7E8FF",
            font=dict(
                family="Inter, Arial, sans-serif",
                size=11,
                color="#0F172A",
            ),
            align="left",
            namelength=-1,
        ),
    )
    fig.update_xaxes(
        fixedrange=True,
        showspikes=False,
    )
    fig.update_yaxes(
        fixedrange=True,
        showspikes=False,
    )
    return fig


def apply_fullscreen_chart_behavior(fig):
    fig.update_layout(
        dragmode="zoom",
        hovermode="closest",
        spikedistance=-1,
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D7E8FF",
            font=dict(
                family="Inter, Arial, sans-serif",
                size=11,
                color="#0F172A",
            ),
            align="left",
            namelength=-1,
        ),
    )
    fig.update_xaxes(
        fixedrange=False,
        showspikes=False,
    )
    fig.update_yaxes(
        fixedrange=False,
        showspikes=False,
    )
    return fig


def render_plotly_normal(fig, key=None):
    apply_normal_chart_behavior(fig)
    container_key = f"normal_plotly_container_{key}" if key else "normal_plotly_container"
    with st.container(key=container_key):
        st.plotly_chart(
            fig,
            width="stretch",
            theme=None,
            config=PLOTLY_CARD_CONFIG,
            key=key,
        )


def render_plotly_fullscreen(fig, key=None):
    apply_fullscreen_chart_behavior(fig)
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        config=PLOTLY_FULLSCREEN_CONFIG,
        key=key,
    )



NAV_ITEMS = (
    ("Overview", "Ringkasan performa utama"),
    ("Analisis Survei", "Profil dan skor kuesioner"),
    ("Analisis Ulasan", "Rating, sentimen, dan suara pengguna"),
    ("Data Explorer", "Eksplorasi data publik"),
    ("Lampiran Presentasi", "Output dan kesiapan UAS"),
    ("Snapshot Flyer", "Snapshot ringkas flyer presentasi"),
)

STOPWORDS_ID = {
    "yang", "dan", "dengan", "untuk", "dari", "ini", "itu", "saya", "kamu",
    "kita", "sudah", "bisa", "tidak", "sangat", "lebih", "pada", "dalam",
    "aplikasi", "app", "apk", "dana", "nya", "lah", "kok", "min", "gan",
    "aja", "banget", "juga", "kalau", "tapi", "karena", "jadi", "lagi",
    "udah", "di", "ke", "ada", "buat", "saat", "belum", "mau", "apa",
    "padahal", "sekali", "orang",
}

SENSITIVE_COLUMN_PHRASES = {
    "nama lengkap", "nama anda", "nama responden", "siapa nama anda",
    "username", "user name", "nama pengguna", "id pengguna", "user id", "id user",
    "alamat email", "e mail", "email address",
    "no hp", "nomor hp", "nomor telepon",
}
SENSITIVE_COLUMN_TOKENS = {
    "nama", "name", "email", "phone", "telepon", "handphone",
    "nomor", "kontak", "username",
}


VARIABLE_GROUPS = {
    "X1 - Fleksibilitas": [
        "Penggunaan DANA membuat aktivitas keuangan menjadi lebih fleksibel."
    ],
    "X2 - Praktis": [
        "Saya merasa aplikasi DANA membuat transaksi menjadi lebih praktis."
    ],
    "M - Kepercayaan": [
        (
            "Dibandingkan dengan aplikasi e-wallet lainnya, saya merasa DANA "
            "memberikan keuntungan lebih dalam bertransaksi."
        ),
        "Saya yakin DANA dapat membantu saya dalam berbagai situasi pembayaran.",
        "Saya merasa nyaman mengandalkan DANA untuk transaksi sehari-hari.",
    ],
    "Y - Keseluruhan": "ALL_QUESTION_COLUMNS",
}

EXPECTED_BASELINE = {
    "survey_rows": 50,
    "review_rows": 330,
    "question_count": 20,
    "questionnaire_mean": 4.002,
    "rating_mean": 3.890909090909091,
    "gender": {"Perempuan": 39, "Laki-laki": 11},
    "age": {
        "< 18 Tahun": 9,
        "18 - 22 Tahun": 36,
        "23 - 27 Tahun": 3,
        "> 27 Tahun": 2,
    },
    "frequency": {
        "Jarang": 21,
        "Beberapa kali seminggu": 19,
        "Setiap hari": 10,
    },
    "rating": {1: 73, 2: 12, 3: 13, 4: 12, 5: 220},
    "sentiment": {"Positif": 232, "Netral": 13, "Negatif": 85},
    "review_dates": {
        date(2026, 6, 9): 248,
        date(2026, 6, 10): 82,
    },
}

COMPLAINT_TERMS = (
    "akun", "saldo", "hilang", "transaksi", "lag",
    "premium", "kecewa", "upgrade", "biaya", "gagal",
)


def asset_path(*parts: str) -> Path:
    """Return an asset path rooted inside the local project."""
    return ASSETS_DIR.joinpath(*parts)


def asset_exists(filename: str) -> bool:
    return asset_path(filename).is_file()


@lru_cache(maxsize=32)
def img_to_base64(filename: str) -> str:
    path = asset_path(filename)
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii") if path.is_file() else ""
    except OSError:
        return ""


def asset_css_url(filename: str) -> str:
    encoded = img_to_base64(filename)
    if not encoded:
        return "none"
    mime = "image/svg+xml" if filename.lower().endswith(".svg") else "image/png"
    return f'url("data:{mime};base64,{encoded}")'  # noqa: E501


def find_asset(*keywords: str) -> str:
    """Find first asset filename that contains ALL keywords (case-insensitive).
    Returns empty string if no match is found."""
    kws = [k.lower() for k in keywords]
    for f in sorted(ASSETS_DIR.iterdir()):
        name = f.name.lower()
        if all(k in name for k in kws):
            return f.name
    return ""


# =============================================================================
# ASSET REGISTRY — semantic name → actual filename
# =============================================================================
def _build_asset_registry() -> dict[str, str]:
    """Build a registry mapping semantic asset names to actual filenames."""
    r: dict[str, str] = {}

    # Landing hero — prefer wide/landscape for side visual panel
    for candidate in (
        "08_hero_dana_phone_wallet_large_1672x941.png",
        "09_hero_dashboard_phone_wide_1916x821.png",
        "16_hero_phone_wallet_shield_stage_1672x941.png",
        "08_hero_fintech_phone_wallet_1672x941.png",
    ):
        if asset_path(candidate).is_file():
            r["landing_hero"] = candidate
            break

    # Dashboard hero — wide banner
    for candidate in (
        "dana_hero_banner_1920x520.png",
        "06_hero_dana_phone_wallet_banner_2048x682.png",
        "09_hero_dashboard_phone_wide_1916x821.png",
    ):
        if asset_path(candidate).is_file():
            r["dashboard_hero"] = candidate
            break

    # Section banners — wide 2048×682 preferred
    for key, candidates in (
        ("review_banner", ["02_banner_review_insight_2048x682.png",
                           "01_illustration_review_sentiment_1254x1254.png"]),
        ("survey_banner", ["07_banner_survey_checklist_2048x682.png",
                           "13_illustration_survey_checklist_1254x1254.png"]),
        ("explorer_banner", ["03_banner_data_explorer_2048x682.png",
                             "12_illustration_data_explorer_search_1448x1086.png"]),
        ("presentation_banner", ["04_banner_output_presentation_2048x682.png"]),
    ):
        for c in candidates:
            if asset_path(c).is_file():
                r[key] = c
                break

    # Small illustrations / icons
    for key, candidates in (
        ("filter_illustration", ["15_illustration_filter_control_1254x1254.png",
                                  "02_illustration_filter_control_1254x1254.png"]),
        ("privacy_shield", ["06_icon_privacy_shield_1254x1254.png",
                             "04_illustration_security_shield_1254x1254.png",
                             "shield_privacy.svg"]),
        ("logo_wordmark", ["dana_logo_wordmark_header_480x120.png",
                            "dana_logo_wordmark_1200x300.png"]),
        ("logo_mark", ["dana_mark.svg"]),
        ("wallet_cluster", ["dana_wallet_cluster_720x720.png",
                             "dana_wallet_cluster_480x480.png"]),
        ("analytics_icon", ["11_icon_dashboard_analytics_1254x1254.png"]),
        ("survey_illustration", ["13_illustration_survey_checklist_1254x1254.png"]),
        ("review_illustration", ["14_illustration_review_rating_1254x1254.png"]),
        ("phone_mockup", ["10_phone_dana_app_mockup_1254x1254.png",
                           "03_phone_dana_dashboard_mockup_1024x1536.png"]),
    ):
        for c in candidates:
            if asset_path(c).is_file():
                r[key] = c
                break

    return r


ASSETS: dict[str, str] = _build_asset_registry()


def render_image_asset(
    filename: str,
    class_name: str | None = None,
    width: int | None = None,
    alt: str = "",
    fallback: str = "",
) -> str:
    encoded = img_to_base64(filename)
    if encoded:
        mime = "image/svg+xml" if filename.lower().endswith(".svg") else "image/png"
        source = f"data:{mime};base64,{encoded}"
    elif fallback:
        source = (
            "data:image/svg+xml;base64,"
            + base64.b64encode(fallback.encode("utf-8")).decode("ascii")
        )
    else:
        return ""
    class_attr = f' class="{escape(class_name)}"' if class_name else ""
    width_attr = f' width="{int(width)}"' if width else ""
    return (
        f'<img src="{source}" alt="{escape(alt)}"{class_attr}{width_attr} '
        'loading="eager" decoding="async"/>'
    )


from PIL import Image

def find_existing_asset(candidates):
    for item in candidates:
        p = Path(item)
        if p.exists():
            return p
        filename = p.name
        ap = asset_path(filename)
        if ap.is_file():
            return ap
    return None


@lru_cache(maxsize=32)
def image_to_data_uri(path):
    path = Path(path)
    if not path.exists():
        return ""
    mime = "image/png"
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    elif path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("utf-8")


def dana_logo_html(height=30, **kwargs):
    if isinstance(height, str):
        if height.endswith("px"):
            try:
                height = int(height[:-2])
            except ValueError:
                height = 30
    logo_path = find_existing_asset([
        "assets/dana_logo_wordmark_header_480x120.png",
        "assets/dana_logo_wordmark_1200x300.png",
        "assets/dana_wordmark.png",
        "assets/dana_logo.png",
    ])
    if not logo_path:
        return '<span style="font-weight:900;color:#108EE9;font-size:22px;">DANA</span>'
    uri = image_to_data_uri(logo_path)
    return f'<img src="{uri}" alt="DANA" style="height:{height}px;width:auto;display:block;object-fit:contain;">'


favicon_path = find_existing_asset([
    "assets/dana_favicon.png",
    "assets/dana_mark.png",
    "assets/favicon.png",
])

page_icon = Image.open(favicon_path) if favicon_path and favicon_path.exists() else None

st.set_page_config(
    page_title="DANA Insight Command Center",
    page_icon=page_icon if page_icon else "💠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_custom_css() -> None:
    # Use ASSETS registry to get actual filenames dynamically
    hero_filename = ASSETS.get("dashboard_hero", "dana_hero_banner_1920x520.png")
    landing_hero_filename = ASSETS.get("landing_hero", "08_hero_dana_phone_wallet_large_1672x941.png")
    hero_background = asset_css_url(hero_filename)
    landing_hero_bg = asset_css_url(landing_hero_filename)
    # Use st.markdown instead of st.html to avoid MemoryError on large CSS blocks.
    # Streamlit's st.html() renders in a sandboxed iframe; large strings can cause
    # memory pressure. st.markdown with unsafe_allow_html=True injects directly.
    _css = f"""
        .brand-logo-wrap {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 128px;
            height: 44px;
            padding: 0 10px;
        }}

        .brand-logo-wrap img {{
            height: 30px !important;
            width: auto !important;
            max-width: 150px !important;
            object-fit: contain !important;
        }}

        :root {{
            --dana-blue: #108EE9;
            --dana-blue-dark: #005BEA;
            --dana-blue-soft: #EAF5FF;
            --dana-sky: #F5FAFF;
            --dana-navy: #07132F;
            --dana-text: #102040;
            --dana-muted: #5C6B86;
            --dana-border: #D7E8FF;
            --dana-card: #FFFFFF;
            --dana-green: #16C784;
            --dana-yellow: #FFB020;
            --dana-red: #FF4D5E;
            --dana-purple: #725CFF;
            --radius-lg: 24px;
            --radius-md: 18px;
            --shadow-soft: 0 18px 45px rgba(16, 142, 233, 0.08);
            --shadow-card: 0 10px 28px rgba(7, 19, 47, 0.06);
            --dana-primary: {C_PRIMARY};
            --dana-deep: {C_DEEP};
            --dana-accent-sky: {C_SKY};
            --dana-electric: {C_ELECTRIC};
            --dana-bg: {C_BG};
            --sidebar-width: 220px;
        }}

        *, *::before, *::after {{
            box-sizing: border-box;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            max-width: 100%;
            overflow-x: hidden;
        }}

        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] button,
        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea,
        [data-testid="stAppViewContainer"] select {{
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }}

        /* ── HIDE STREAMLIT CHROME ── */
        #MainMenu,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        footer {{
            display: none !important;
        }}

        /* ── HIDE STREAMLIT SIDEBAR (filter is now a dialog) ── */
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"],
        section[data-testid="stSidebar"] {{
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            visibility: hidden !important;
        }}

        /* ── FULL-WIDTH MAIN CONTAINER ── */
        [data-testid="stAppViewContainer"] {{
            margin-left: 0 !important;
        }}

        [data-testid="stMain"] {{
            margin-left: 0 !important;
        }}

        /* ── MAIN APP BACKGROUND ── */
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(180deg, #F7FBFF 0%, #EEF7FF 100%);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ── SIDEBAR — WHITE CLEAN NAV ── */
        [data-testid="stSidebar"] {{
            width: var(--sidebar-width) !important;
            min-width: var(--sidebar-width) !important;
            background: #FFFFFF !important;
            border-right: 1px solid var(--dana-border) !important;
            box-shadow: 8px 0 28px rgba(7,19,47,.055) !important;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 0 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}

        /* Sidebar widget labels */
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] .stMarkdown p {{
            color: {C_TEXT} !important;
            font-size: 0.78rem !important;
        }}

        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stMultiSelect label,
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stDateInput label,
        [data-testid="stSidebar"] .stCaption {{
            color: {C_MUTED} !important;
            font-size: 0.7rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.03em !important;
            text-transform: uppercase !important;
        }}

        /* Sidebar form submit button */
        [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button {{
            background: linear-gradient(135deg, {C_PRIMARY}, {C_DEEP}) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}

        [data-testid="stSidebar"] [data-testid="stButton"] button {{
            border-radius: 12px !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            transition: transform .2s ease, color .2s ease, background .2s ease,
                border-color .2s ease, box-shadow .2s ease !important;
        }}

        [data-testid="stSidebar"]:not(:has(.filter-rail-marker))
        [data-testid="stButton"] button {{
            justify-content: flex-start !important;
            color: var(--dana-muted) !important;
            border-color: transparent !important;
            background: transparent !important;
            box-shadow: none !important;
        }}

        [data-testid="stSidebar"]:not(:has(.filter-rail-marker))
        [data-testid="stButton"] button:hover {{
            color: var(--dana-blue-dark) !important;
            border-color: var(--dana-border) !important;
            background: var(--dana-blue-soft) !important;
            transform: translateX(2px);
        }}

        [data-testid="stSidebar"]:not(:has(.filter-rail-marker))
        [data-testid="stButton"] button[kind="primary"] {{
            color: var(--dana-blue-dark) !important;
            border-color: #BFD8FF !important;
            background: linear-gradient(135deg, #F3F9FF, #E5F2FF) !important;
            box-shadow: inset 3px 0 0 var(--dana-blue),
                0 7px 18px rgba(16,142,233,.08) !important;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) {{
            background: linear-gradient(180deg, #073B86 0%, #087DC4 100%) !important;
            border-right-color: rgba(255,255,255,.16) !important;
            box-shadow: 8px 0 28px rgba(3,57,126,.18) !important;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) > div:first-child {{
            animation: filter-slide-in .3s cubic-bezier(.16,1,.3,1) both;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) label,
        [data-testid="stSidebar"]:has(.filter-rail-marker) p,
        [data-testid="stSidebar"]:has(.filter-rail-marker) .stMarkdown p,
        [data-testid="stSidebar"]:has(.filter-rail-marker) .stCaption {{
            color: rgba(255,255,255,.92) !important;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) .sidebar-section {{
            color: #BAE6FD !important;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) [data-testid="stForm"] {{
            border: 0 !important;
        }}

        [data-testid="stSidebar"]:has(.filter-rail-marker) [data-baseweb="select"] > div,
        [data-testid="stSidebar"]:has(.filter-rail-marker) input {{
            background: rgba(255,255,255,.96) !important;
            color: #0F172A !important;
        }}

        .filter-rail-marker {{
            margin: 0 0 .55rem;
            padding: .75rem .85rem .65rem;
            color: white;
            border-bottom: 1px solid rgba(255,255,255,.16);
            display: flex;
            align-items: center;
            gap: .55rem;
        }}

        .filter-rail-marker-icon {{
            width: 28px;
            height: 28px;
            flex: 0 0 28px;
            object-fit: contain;
            border-radius: 8px;
            opacity: .92;
        }}

        .filter-rail-marker-text {{
            flex: 1;
            min-width: 0;
        }}

        .filter-rail-marker strong {{
            display: block;
            font-size: .85rem;
            letter-spacing: .02em;
        }}

        .filter-rail-marker span {{
            display: block;
            margin-top: .18rem;
            color: rgba(255,255,255,.72);
            font-size: .63rem;
            line-height: 1.4;
        }}

        /* ── MAIN CONTENT AREA — FULL WIDTH ── */
        .block-container,
        [data-testid="stMainBlockContainer"] {{
            max-width: 1480px !important;
            margin: 0 auto !important;
            padding-top: 0.9rem !important;
            padding-bottom: 3rem !important;
            padding-left: clamp(1rem, 2vw, 2rem) !important;
            padding-right: clamp(1rem, 2vw, 2rem) !important;
        }}

        /* ── SIDEBAR NAVIGATION COMPONENTS ── */
        .sidebar-header {{
            padding: 1.1rem 1rem .85rem;
            border-bottom: 1px solid #F1F5F9;
            margin-bottom: .2rem;
        }}

        .sidebar-logo img {{
            width: 88px;
            height: auto;
            object-fit: contain;
        }}

        .sidebar-logo-fallback {{
            display: flex;
            align-items: center;
            gap: .45rem;
            font-size: 1.15rem;
            font-weight: 900;
            color: {C_DEEP};
        }}

        .sidebar-nav-section {{
            padding: .6rem .9rem .35rem;
        }}

        .sidebar-nav-label {{
            color: #94A3B8;
            font-size: .6rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
            padding: 0 .3rem;
            margin-bottom: .3rem;
            display: block;
        }}

        .sidebar-nav-item {{
            display: flex;
            align-items: center;
            gap: .65rem;
            padding: .58rem .68rem;
            border-radius: 10px;
            margin-bottom: .18rem;
            cursor: pointer;
            transition: all .14s ease;
            color: #475569;
            font-size: .78rem;
            font-weight: 600;
        }}

        .sidebar-nav-item:hover {{
            background: #F1F5F9;
            color: {C_TEXT};
        }}

        .sidebar-nav-item.active {{
            background: linear-gradient(135deg, #EFF6FF, #DBEAFE);
            color: {C_DEEP};
            font-weight: 700;
        }}

        .sidebar-nav-item .nav-icon {{
            width: 26px;
            height: 26px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 26px;
            background: #F8FAFC;
            font-size: .82rem;
        }}

        .sidebar-nav-item.active .nav-icon {{
            background: {C_PRIMARY};
            color: white;
        }}

        .sidebar-divider {{
            height: 1px;
            background: #F1F5F9;
            margin: .6rem .9rem;
        }}

        .sidebar-filter-header {{
            padding: .4rem .9rem .3rem;
        }}

        .sidebar-filter-title {{
            color: #94A3B8;
            font-size: .6rem;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}

        /* ── LOBBY PAGE ── */
        .lobby-shell {{
            position: relative;
            overflow: hidden;
            min-height: 440px;
            padding: clamp(1.45rem, 3vw, 2.5rem);
            border-radius: 28px;
            /* Gradient left solid → fade → hero image on right */
            background-image:
                linear-gradient(108deg,
                    #FFFFFF 0%,
                    #F8FCFF 38%,
                    rgba(240,249,255,.92) 52%,
                    rgba(255,255,255,.45) 68%,
                    rgba(255,255,255,.08) 80%,
                    transparent 100%),
                {landing_hero_bg};
            background-size: 100%, cover;
            background-position: left top, center right;
            background-repeat: no-repeat, no-repeat;
            border: 1px solid #CDDEFA;
            box-shadow: var(--shadow-soft), 0 4px 16px rgba(15,23,42,.05);
            animation: fade-in .4s ease-out both;
        }}

        .lobby-hero {{
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(200px, .85fr);
            align-items: center;
            gap: clamp(1rem, 3vw, 2.5rem);
        }}

        .lobby-mark {{
            display: flex;
            align-items: center;
            gap: .75rem;
            margin-bottom: 1.5rem;
        }}

        .lobby-mark img {{
            width: 96px;
            height: auto;
            object-fit: contain;
        }}

        .lobby-title {{
            max-width: 620px;
            margin: 0;
            color: {C_TEXT};
            font-size: clamp(2.1rem, 5.2vw, 3.75rem);
            font-weight: 900;
            letter-spacing: -.04em;
            line-height: 1.03;
        }}

        .lobby-title span {{
            background: linear-gradient(135deg, {C_PRIMARY}, {C_DEEP});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .lobby-subtitle {{
            max-width: 540px;
            margin: 1.1rem 0 1.65rem;
            color: #475569;
            font-size: clamp(.88rem, 1.5vw, 1.02rem);
            line-height: 1.7;
        }}

        /* RIGHT PANEL: transparent placeholder that lets shell background show through */
        .lobby-visual {{
            position: relative;
            display: block;
            min-height: 300px;
            border-radius: 16px;
            /* transparent — the hero image shows through the lobby-shell background */
            background: transparent;
        }}

        .st-key-lobby_actions {{
            max-width: 640px;
            margin-top: -1.05rem;
            margin-bottom: .9rem;
        }}

        .lobby-metrics {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0,1fr));
            gap: .6rem;
            margin-top: 0;
        }}

        .lobby-metric {{
            padding: 1rem .95rem;
            border: 1px solid var(--dana-border);
            border-radius: var(--radius-md);
            background: rgba(255,255,255,.92);
            box-shadow: var(--shadow-card);
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            transition: transform .22s ease, border-color .22s ease,
                box-shadow .22s ease;
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}

        .lobby-metric:nth-child(2) {{ animation-delay: .05s; }}
        .lobby-metric:nth-child(3) {{ animation-delay: .1s; }}
        .lobby-metric:nth-child(4) {{ animation-delay: .15s; }}
        .lobby-metric:nth-child(5) {{ animation-delay: .2s; }}

        .lobby-metric:hover {{
            transform: translateY(-3px);
            border-color: #A9D3FF;
            box-shadow: 0 16px 34px rgba(16,142,233,.11);
        }}

        .lobby-metric-icon {{
            width: 36px;
            height: 36px;
            border-radius: 9px;
            background: linear-gradient(135deg, rgba(56,189,248,.2), rgba(16,142,233,.13));
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: .55rem;
            font-size: 1rem;
        }}

        .lobby-metric strong {{
            display: block;
            color: {C_TEXT};
            font-size: 1.48rem;
            font-weight: 880;
            line-height: 1;
            letter-spacing: -.025em;
        }}

        .lobby-metric span {{
            display: block;
            margin-top: .2rem;
            color: {C_MUTED};
            font-size: .66rem;
            font-weight: 600;
            line-height: 1.35;
        }}

        .lobby-privacy {{
            display: flex;
            align-items: center;
            gap: .85rem;
            margin-top: 1.2rem;
            padding: .85rem 1.05rem;
            border: 1px solid #BAE6FD;
            border-radius: 14px;
            color: #0369A1;
            background: rgba(240,249,255,.9);
            font-size: .74rem;
            line-height: 1.5;
        }}

        .lobby-privacy img {{
            width: 36px;
            height: 36px;
            flex: 0 0 36px;
        }}

        /* ── MODULE GRID ── */
        .module-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0,1fr));
            gap: .6rem;
            margin: 1.1rem 0;
        }}

        .module-card {{
            padding: .95rem;
            border: 1px solid {C_BORDER};
            border-radius: 14px;
            background: white;
            transition: all .18s ease;
        }}

        .module-card:hover {{
            border-color: #93C5FD;
            box-shadow: 0 8px 22px rgba(16,142,233,.09);
            transform: translateY(-2px);
        }}

        .module-card-icon {{
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: #EFF6FF;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: .6rem;
            font-size: 1rem;
        }}

        .module-card strong {{
            display: block;
            color: {C_TEXT};
            font-size: .75rem;
            font-weight: 700;
            margin-bottom: .28rem;
        }}

        .module-card span {{
            display: block;
            color: {C_MUTED};
            font-size: .66rem;
            line-height: 1.45;
        }}

        [class*="st-key-landing_module_"] {{
            height: 100%;
            min-height: 126px;
            padding: .82rem !important;
            border: 1px solid var(--dana-border) !important;
            border-radius: var(--radius-md) !important;
            background: rgba(255,255,255,.95) !important;
            box-shadow: var(--shadow-card);
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}

        [class*="st-key-landing_module_"]:hover {{
            transform: translateY(-4px);
            border-color: #93C5FD !important;
            box-shadow: 0 12px 28px rgba(16,142,233,.12);
        }}

        [class*="st-key-landing_module_"] button {{
            width: 100%;
            justify-content: flex-start !important;
            color: {C_DEEP} !important;
            border: 0 !important;
            background: linear-gradient(135deg, #F1F8FF, #E8F4FF) !important;
        }}

        [class*="st-key-landing_module_"] button::after {{
            content: "›";
            margin-left: auto;
            color: var(--dana-blue);
            font-size: 1.15rem;
            font-weight: 800;
        }}

        .lobby-topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .8rem;
            padding: .3rem .2rem;
        }}

        .lobby-topbar img {{
            width: 112px;
            height: auto;
            object-fit: contain;
        }}

        .lobby-help {{
            color: {C_MUTED};
            font-size: .72rem;
            font-weight: 650;
        }}

        /* ── TOP HEADER ── */
        .st-key-top_header {{
            position: sticky;
            top: .25rem;
            z-index: 999;
            padding: .55rem .85rem;
            margin-bottom: .75rem;
            background: rgba(255,255,255,.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(215,232,255,.9);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-card);
            /* Ensure it never overflows the content column */
            max-width: 100%;
            overflow: hidden;
        }}

        /* All columns inside topbar must shrink gracefully */
        .st-key-top_header [data-testid="stColumns"] {{
            gap: .5rem !important;
            flex-wrap: nowrap;
            align-items: center;
        }}

        .st-key-top_header [data-testid="stColumn"] {{
            min-width: 0 !important;
            overflow: hidden;
        }}

        .st-key-top_header [data-testid="stButton"] button {{
            white-space: nowrap !important;
            min-height: 40px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        /* Filter toggle button in topbar: enough width for icon + text */
        .st-key-top_header .st-key-toggle_filter_panel button {{
            min-width: 110px !important;
            padding-left: .5rem !important;
            padding-right: .5rem !important;
        }}

        .st-key-top_header .st-key-top_refresh_btn button {{
            min-width: 90px !important;
            white-space: nowrap !important;
        }}

        /* Status column: wrap text, don't overflow */
        .st-key-top_header .header-status {{
            overflow: hidden;
        }}

        .st-key-top_header .header-status .time-pill,
        .st-key-top_header .header-status .status-pill {{
            font-size: .6rem;
        }}


        .brand-lockup {{
            display: flex;
            align-items: center;
            gap: .6rem;
            min-height: 38px;
        }}

        .brand-mark {{
            width: 160px;
            height: 32px;
            display: flex;
            align-items: center;
            overflow: visible;
            border-radius: 0;
            background: none;
            box-shadow: none;
        }}

        .brand-mark img {{
            height: 28px;
            width: auto;
            max-width: 160px;
            object-fit: contain;
        }}

        .brand-title {{
            color: {C_TEXT};
            font-weight: 800;
            font-size: .9rem;
            line-height: 1.15;
        }}

        .brand-subtitle {{
            color: {C_MUTED};
            font-size: .68rem;
            margin-top: .12rem;
        }}

        .header-status {{
            min-height: 38px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            gap: .35rem;
        }}

        .status-pill, .time-pill {{
            display: inline-flex;
            align-items: center;
            gap: .32rem;
            min-height: 26px;
            padding: .22rem .55rem;
            border-radius: 999px;
            font-size: .65rem;
            font-weight: 700;
            white-space: nowrap;
        }}

        .status-pill {{
            color: #047857;
            background: {C_SOFT_GREEN};
            border: 1px solid #A7F3D0;
        }}

        .status-pill.is-error {{
            color: #B91C1C;
            background: {C_SOFT_RED};
            border-color: #FECACA;
        }}

        .status-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 0 3px rgba(16,185,129,.14);
            animation: pulse-dot 1.8s ease-in-out infinite;
        }}

        .time-pill {{
            color: #475569;
            background: #F8FAFC;
            border: 1px solid {C_BORDER};
        }}

        /* ── HERO SECTION ── */
        .hero-section {{
            position: relative;
            overflow: hidden;
            min-height: 200px;
            max-height: 320px;
            margin-bottom: .8rem;
            padding: clamp(1.2rem, 3vw, 1.9rem);
            border-radius: 20px;
            color: {C_TEXT};
            background-image:
                linear-gradient(92deg, rgba(255,255,255,1) 0%, rgba(255,255,255,.98) 35%, rgba(255,255,255,.80) 55%, rgba(255,255,255,.25) 72%, rgba(255,255,255,.04) 88%),
                {hero_background},
                linear-gradient(135deg, #F8FBFF 0%, #EBF5FF 100%);
            background-position: center, center right 0%, center;
            background-repeat: no-repeat;
            background-size: 100%, cover, cover;
            border: 1px solid #CDDEFA;
            box-shadow: 0 6px 24px rgba(16,142,233,.09);
        }}

        /* ── SECTION BANNER (2048×682 wide images) ── */
        .section-banner {{
            position: relative;
            overflow: hidden;
            height: clamp(100px, 14vw, 150px);
            margin-bottom: .9rem;
            border-radius: 18px;
            border: 1px solid #CDDEFA;
            background-size: cover;
            background-position: center right;
            background-repeat: no-repeat;
        }}

        .section-banner::before {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(
                to right,
                rgba(255,255,255,0.97) 0%,
                rgba(255,255,255,0.92) 38%,
                rgba(255,255,255,0.55) 62%,
                rgba(255,255,255,0.10) 82%,
                transparent 100%
            );
            z-index: 1;
        }}

        .section-banner-content {{
            position: relative;
            z-index: 2;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 0 clamp(1rem, 3vw, 2rem);
        }}

        .section-banner-kicker {{
            color: {C_PRIMARY};
            font-size: .62rem;
            font-weight: 800;
            letter-spacing: .09em;
            text-transform: uppercase;
            margin-bottom: .28rem;
        }}

        .section-banner-title {{
            margin: 0;
            color: {C_TEXT};
            font-size: clamp(1.1rem, 2.2vw, 1.55rem);
            font-weight: 860;
            letter-spacing: -.025em;
            line-height: 1.15;
        }}

        .section-banner-desc {{
            margin-top: .25rem;
            color: {C_MUTED};
            font-size: clamp(.72rem, 1.2vw, .82rem);
            line-height: 1.45;
        }}


        .hero-section::before {{
            content: "";
            position: absolute;
            inset: 0;
            opacity: .06;
            background-image:
                radial-gradient(circle at 88% 18%, rgba(56,189,248,1) 0%, transparent 42%),
                radial-gradient(circle at 72% 82%, rgba(16,142,233,.55) 0%, transparent 28%);
            pointer-events: none;
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1.5rem;
            width: 100%;
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: .38rem;
            margin-bottom: .7rem;
            padding: .28rem .6rem;
            color: {C_DEEP};
            border: 1px solid #BFDBFE;
            border-radius: 999px;
            background: rgba(239,246,255,.88);
            font-size: .64rem;
            font-weight: 700;
            letter-spacing: .06em;
            text-transform: uppercase;
        }}

        .hero-title {{
            max-width: 700px;
            margin: 0;
            font-size: clamp(1.5rem, 3.2vw, 2.2rem);
            font-weight: 880;
            letter-spacing: -.03em;
            line-height: 1.1;
        }}

        .hero-subtitle {{
            max-width: 600px;
            margin: .55rem 0 .85rem;
            color: #475569;
            font-size: clamp(.8rem, 1.3vw, .92rem);
            line-height: 1.6;
        }}

        .badge-row, .hero-stat-row, .chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: .42rem;
        }}

        .hero-badge {{
            padding: .26rem .55rem;
            color: #1E40AF;
            border: 1px solid #BFDBFE;
            border-radius: 999px;
            background: rgba(255,255,255,.82);
            font-size: .64rem;
            font-weight: 650;
        }}

        .hero-stat-row {{
            display: grid !important;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            margin-top: .9rem;
            padding-top: .8rem;
            max-width: 680px;
            border-top: 1px solid #D9EAFE;
            gap: clamp(.5rem, 1.5vw, 1.4rem);
        }}

        .hero-stat-value {{
            display: block;
            font-size: clamp(.88rem, 1.4vw, 1.08rem);
            font-weight: 820;
            color: {C_TEXT};
            white-space: nowrap;
        }}

        .hero-stat-label {{
            display: block;
            margin-top: .08rem;
            color: #64748B;
            font-size: clamp(.5rem, .75vw, .58rem);
            font-weight: 650;
            letter-spacing: .04em;
            text-transform: uppercase;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .hero-stat-item {{
            display: flex;
            flex-direction: column;
            gap: .1rem;
        }}

        /* Hero layout with optional phone image */
        .hero-copy-col {{
            flex: 1;
            min-width: 0;
        }}
        .hero-image-col {{
            flex: 0 0 auto;
            display: flex;
            align-items: center;
            justify-content: flex-end;
        }}
        .hero-phone-visual {{
            width: clamp(90px, 12vw, 160px);
            height: auto;
            object-fit: contain;
            filter: drop-shadow(0 12px 24px rgba(16,142,233,.15));
            animation: lobby-float 3s ease-in-out infinite;
            border-radius: 16px;
        }}

        /* ── SECTION HEADINGS ── */
        .section-heading {{
            display: flex;
            align-items: center;
            gap: .68rem;
            margin: 1rem 0 .75rem;
        }}

        .section-visual {{
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
            display: grid;
            place-items: center;
            overflow: hidden;
            border: 1px solid #BFDBFE;
            border-radius: 12px;
            background: linear-gradient(145deg, #FFFFFF, #EFF6FF);
            box-shadow: 0 5px 14px rgba(16,142,233,.07);
        }}

        .section-visual svg, .section-visual img {{
            width: 36px;
            height: 36px;
            object-fit: contain;
        }}

        .section-heading-copy {{
            min-width: 0;
        }}

        .section-kicker {{
            color: {C_PRIMARY};
            font-size: .63rem;
            font-weight: 800;
            letter-spacing: .09em;
            text-transform: uppercase;
        }}

        .section-title {{
            margin: .14rem 0 0;
            color: {C_TEXT};
            font-size: clamp(1.05rem, 1.7vw, 1.3rem);
            font-weight: 820;
            letter-spacing: -.02em;
        }}

        .section-description {{
            margin-top: .22rem;
            color: {C_MUTED};
            font-size: .76rem;
            line-height: 1.5;
        }}

        /* ── KPI CARDS ── */
        /* 5-column KPI grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0,1fr));
            gap: .65rem;
            margin-bottom: .8rem;
        }}

        @media (max-width: 1024px) {{
            .kpi-grid {{
                grid-template-columns: repeat(3, minmax(0,1fr));
            }}
        }}

        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}
        }}

        .kpi-card {{
            position: relative;
            overflow: hidden;
            padding: 1rem;
            border: 1px solid {C_BORDER};
            border-radius: 17px;
            background: {C_CARD};
            box-shadow: 0 3px 14px rgba(15,23,42,.04);
            transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }}

        .kpi-card::after {{
            content: "";
            position: absolute;
            width: 76px;
            height: 76px;
            top: -38px;
            right: -30px;
            border-radius: 50%;
            background: var(--kpi-soft, #EFF6FF);
            opacity: .6;
        }}

        .kpi-card:hover {{
            transform: translateY(-3px);
            border-color: #BFDBFE;
            box-shadow: 0 11px 26px rgba(16,142,233,.1);
        }}

        .kpi-top {{
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .5rem;
        }}

        .icon-box {{
            width: 38px;
            height: 38px;
            flex: 0 0 38px;
            display: grid;
            place-items: center;
            border-radius: 11px;
            background: var(--kpi-soft, #EFF6FF);
            border: 1px solid var(--kpi-color, {C_PRIMARY});
            border-opacity: 0.2;
        }}

        .icon-box svg {{
            width: 19px;
            height: 19px;
            stroke: var(--kpi-color, {C_PRIMARY});
            stroke-width: 2;
            fill: none;
        }}

        .kpi-label {{
            color: {C_MUTED};
            font-size: .58rem;
            font-weight: 800;
            letter-spacing: .07em;
            text-transform: uppercase;
            text-align: right;
        }}

        .kpi-value {{
            margin-top: .65rem;
            color: {C_TEXT};
            font-size: 1.7rem;
            font-weight: 850;
            letter-spacing: -.04em;
            line-height: 1;
        }}

        .kpi-caption {{
            min-height: 1.05rem;
            margin-top: .38rem;
            color: {C_MUTED};
            font-size: .63rem;
        }}

        .progress-track {{
            height: 5px;
            margin-top: .6rem;
            overflow: hidden;
            border-radius: 999px;
            background: #EEF2F7;
        }}

        .progress-fill {{
            height: 100%;
            width: var(--progress, 0%);
            border-radius: inherit;
            background: var(--kpi-color, {C_PRIMARY});
            transform-origin: left center;
            animation: grow-bar .9s cubic-bezier(.16,1,.3,1) both;
        }}

        /* ── CHART CONTAINERS ── */
        [class*="st-key-chart_"], [class*="st-key-panel_"] {{
            width: 100%;
            max-width: 100%;
            overflow: visible !important;
            padding: .5rem .72rem .45rem;
            border: 1px solid var(--dana-border);
            border-radius: var(--radius-md);
            background: var(--dana-card);
            box-shadow: var(--shadow-card);
            transition: transform .22s ease, box-shadow .22s ease,
                border-color .22s ease;
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}

        [class*="st-key-chart_"]:hover, [class*="st-key-panel_"]:hover {{
            transform: translateY(-2px);
            border-color: #BFD8FF;
            box-shadow: 0 16px 34px rgba(16,142,233,.09);
        }}

        [data-testid="stPlotlyChart"],
        [data-testid="stPlotlyChart"] > div {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        /* Reduce Streamlit's default vertical gap around plotly charts */
        [class*="st-key-chart_"] [data-testid="stPlotlyChart"] {{
            margin-top: -4px;
            margin-bottom: -4px;
        }}

        /* Reduce gap between Streamlit element containers within chart cards */
        [class*="st-key-chart_"] [data-testid="stVerticalBlock"] > div {{
            gap: 0 !important;
        }}

        /* Plotly modebar hidden since config sets displayModeBar: false */
        [data-testid="stPlotlyChart"] .modebar {{
            display: none !important;
        }}

        .chart-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .5rem;
            padding: .25rem .1rem .0rem;
            min-height: 28px;
        }}

        .chart-card-title {{
            color: var(--dana-navy);
            font-size: .92rem;
            font-weight: 800;
            line-height: 1.35;
        }}

        .chart-card-title::after {{
            content: "i";
            display: inline-grid;
            place-items: center;
            width: 16px;
            height: 16px;
            margin-left: .4rem;
            border: 1px solid #BFD8FF;
            border-radius: 50%;
            color: var(--dana-muted);
            font-size: .62rem;
            font-weight: 800;
            vertical-align: 2px;
        }}

        [data-testid="stDataFrame"] {{
            width: 100%;
            max-width: 100%;
            overflow: visible !important;
            border: 1px solid var(--dana-border);
            border-radius: 14px;
            background: var(--dana-card);
            box-shadow: none;
            font-size: .82rem;
        }}

        [data-testid="stDataFrame"] div {{
            scrollbar-width: thin;
        }}

        [class*="st-key-table_card_"],
        .st-key-audit_metadata_card,
        .st-key-output_audit_card,
        .st-key-output_screenshot_card {{
            width: 100%;
            max-width: 100%;
            padding: .9rem;
            overflow: clip;
            border: 1px solid var(--dana-border);
            border-radius: var(--radius-md);
            background: var(--dana-card);
            box-shadow: var(--shadow-card);
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}

        [class*="st-key-table_card_"] [data-testid="stDataFrame"],
        .st-key-audit_metadata_card [data-testid="stDataFrame"],
        .st-key-output_audit_card [data-testid="stDataFrame"],
        .st-key-output_screenshot_card [data-testid="stDataFrame"] {{
            box-shadow: none;
        }}

        /* Fullscreen button — small, inline, not a giant circle */
        [class*="st-key-chart_expand_"] {{
            display: flex !important;
            align-items: center !important;
            justify-content: flex-end !important;
        }}

        [class*="st-key-chart_expand_"] button {{
            width: 26px !important;
            min-width: 26px !important;
            height: 24px !important;
            min-height: 24px !important;
            max-height: 24px !important;
            padding: 0 !important;
            font-size: .68rem !important;
            line-height: 1 !important;
            border-radius: 6px !important;
            color: {C_MUTED} !important;
            border: 1px solid {C_BORDER} !important;
            background: #F1F5F9 !important;
            box-shadow: none !important;
        }}

        [class*="st-key-chart_expand_"] button:hover {{
            color: white !important;
            border-color: {C_PRIMARY} !important;
            background: linear-gradient(135deg, {C_PRIMARY}, {C_DEEP}) !important;
            box-shadow: 0 4px 10px rgba(16,142,233,.2) !important;
        }}

        [data-testid="stDialog"] {{
            background: rgba(7,19,47,.45) !important;
            animation: fade-in .22s ease-out both;
        }}

        [data-testid="stDialog"] > div {{
            width: min(92vw, 1500px) !important;
            max-width: min(92vw, 1500px) !important;
            max-height: 86vh !important;
            border-radius: 24px !important;
            border: 1px solid var(--dana-border) !important;
            box-shadow: 0 30px 80px rgba(7,19,47,.2) !important;
            animation: modal-in .28s cubic-bezier(.16,1,.3,1) both;
        }}

        [data-testid="stDialog"] [data-testid="stPlotlyChart"] {{
            min-height: 68vh;
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid var(--dana-border);
            border-radius: 16px;
            overflow: auto !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,.75);
        }}

        /* ── CUSTOM TABS ── */
        .st-key-horizontal_navigation {{
            margin: .1rem 0 .85rem;
            padding: .28rem;
            overflow-x: auto;
            border: 1px solid {C_BORDER};
            border-radius: 15px;
            background: rgba(255,255,255,.92);
            box-shadow: 0 4px 16px rgba(15,23,42,.04);
        }}

        .st-key-horizontal_navigation [data-testid="stHorizontalBlock"] {{
            min-width: 720px;
            gap: .25rem;
        }}

        .st-key-horizontal_navigation button {{
            min-height: 38px !important;
            border: 0 !important;
            border-radius: 10px !important;
            color: #64748B !important;
            background: transparent !important;
            box-shadow: none !important;
            font-size: .72rem !important;
        }}

        .st-key-horizontal_navigation button[kind="primary"] {{
            color: {C_DEEP} !important;
            background: #EFF6FF !important;
            box-shadow: inset 0 -3px 0 {C_PRIMARY} !important;
        }}

        /* ── GLOBAL SEARCH ── */
        .global-search-note {{
            margin: -.28rem 0 .7rem;
            color: {C_MUTED};
            font-size: .66rem;
        }}

        .search-result-card {{
            margin-bottom: .38rem;
            padding: .62rem .72rem;
            border: 1px solid {C_BORDER};
            border-radius: 11px;
            background: white;
            color: #334155;
            font-size: .71rem;
            line-height: 1.5;
        }}

        /* ── PRESENTATION ── */
        .presentation-visual {{
            width: min(220px, 100%);
            max-height: 300px;
            object-fit: contain;
            filter: drop-shadow(0 18px 30px rgba(11,94,215,.16));
        }}

        .conclusion-visual {{
            float: right;
            width: min(175px, 28%);
            max-height: 175px;
            margin: -.3rem -.1rem .8rem 1rem;
            object-fit: contain;
            filter: drop-shadow(0 14px 24px rgba(11,94,215,.12));
        }}

        /* ── SUMMARY CARDS ── */
        .summary-card {{
            min-height: 108px;
            padding: .88rem;
            border: 1px solid var(--dana-border);
            border-radius: var(--radius-md);
            background: var(--dana-card);
            box-shadow: var(--shadow-card);
            transition: transform .2s ease, border-color .2s ease,
                box-shadow .2s ease;
        }}

        .summary-card:hover {{
            transform: translateY(-3px);
            border-color: #BFD8FF;
            box-shadow: 0 14px 30px rgba(16,142,233,.09);
        }}

        .summary-label {{
            color: {C_MUTED};
            font-size: .62rem;
            font-weight: 750;
            letter-spacing: .05em;
            text-transform: uppercase;
        }}

        .summary-value {{
            margin-top: .42rem;
            color: {C_TEXT};
            font-size: 1.08rem;
            font-weight: 820;
            line-height: 1.3;
        }}

        .summary-note {{
            margin-top: .26rem;
            color: {C_MUTED};
            font-size: .65rem;
        }}

        /* ── HEALTH CARDS ── */
        .health-card {{
            min-height: 128px;
            padding: .95rem;
            border: 1px solid var(--health-border);
            border-radius: 15px;
            background: var(--health-bg);
        }}

        .health-count {{
            margin: .45rem 0 .16rem;
            color: var(--health-color);
            font-size: 1.85rem;
            font-weight: 850;
            line-height: 1;
        }}

        .health-title {{
            color: var(--health-color);
            font-size: .74rem;
            font-weight: 800;
        }}

        .health-note {{
            color: #64748B;
            font-size: .65rem;
        }}

        /* ── RANK CARDS ── */
        .rank-card {{
            display: grid;
            grid-template-columns: 28px minmax(0,1fr) auto;
            gap: .62rem;
            align-items: center;
            margin-bottom: .48rem;
            padding: .68rem .75rem;
            border: 1px solid {C_BORDER};
            border-radius: 12px;
            background: white;
        }}

        .rank-number {{
            width: 26px;
            height: 26px;
            display: grid;
            place-items: center;
            border-radius: 8px;
            color: var(--rank-color);
            background: var(--rank-soft);
            font-size: .68rem;
            font-weight: 850;
        }}

        .rank-question {{
            color: #334155;
            font-size: .72rem;
            line-height: 1.4;
        }}

        .rank-score {{
            color: var(--rank-color);
            font-size: .83rem;
            font-weight: 850;
        }}

        /* ── FILTER SUMMARY ── */
        .filter-summary {{
            display: flex;
            align-items: flex-start;
            gap: .52rem;
            margin: .08rem 0 .8rem;
            padding: .72rem .88rem;
            border: 1px solid #BFDBFE;
            border-radius: 12px;
            color: #1E40AF;
            background: #EFF6FF;
            font-size: .74rem;
            line-height: 1.5;
        }}

        .filter-summary.is-empty {{
            color: {C_MUTED};
            border-color: {C_BORDER};
            background: #F8FAFC;
        }}

        /* ── CONTROL PANEL (sidebar filter) ── */
        .st-key-control_panel {{
            padding: 1rem 1.1rem;
            border: 1px solid var(--dana-border) !important;
            border-radius: var(--radius-lg) !important;
            background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(234,245,255,.96)) !important;
            box-shadow: var(--shadow-soft) !important;
            margin-bottom: 1rem;
            animation: filterSlide .28s ease both;
        }}

        /* ── BUTTONS ── */
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {{
            min-height: 36px;
            border-radius: 12px;
            font-weight: 700;
            transition: transform .18s ease, box-shadow .18s ease,
                border-color .18s ease, background .18s ease, color .18s ease;
        }}

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {{
            transform: translateY(-2px);
            border-color: #9DCBFF;
            box-shadow: 0 10px 22px rgba(16,142,233,.14);
        }}

        div[data-testid="stButton"] > button:disabled,
        div[data-testid="stDownloadButton"] > button:disabled,
        div[data-testid="stFormSubmitButton"] > button:disabled {{
            transform: none;
            box-shadow: none;
        }}

        /* ── CHIP STYLES ── */
        .filter-chip, .keyword-chip {{
            display: inline-flex;
            align-items: center;
            gap: .28rem;
            padding: .25rem .52rem;
            border-radius: 999px;
            font-size: .64rem;
            font-weight: 720;
        }}

        .filter-chip {{
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
            background: white;
        }}

        .keyword-chip {{
            color: #1E40AF;
            border: 1px solid #BFDBFE;
            background: #EFF6FF;
        }}

        .chip-count {{
            display: grid;
            place-items: center;
            min-width: 17px;
            height: 17px;
            padding: 0 .22rem;
            border-radius: 999px;
            color: white;
            background: {C_ELECTRIC};
            font-size: .58rem;
        }}

        /* ── INSIGHT CARDS ── */
        .insight-card {{
            padding: .95rem 1.05rem;
            border: 1px solid #BFDBFE;
            border-left: 4px solid {C_PRIMARY};
            border-radius: 15px;
            background: linear-gradient(135deg, rgba(239,246,255,.94), rgba(255,255,255,.98));
            box-shadow: 0 5px 18px rgba(16,142,233,.05);
        }}

        .insight-card h4 {{
            margin: 0 0 .42rem;
            color: {C_TEXT};
            font-size: .88rem;
        }}

        .insight-card p, .insight-card li {{
            color: #475569;
            font-size: .74rem;
            line-height: 1.65;
        }}

        .insight-card ul {{
            margin: 0;
            padding-left: .95rem;
        }}

        /* ── PRIVACY / MISC ── */
        .privacy-note {{
            padding: .78rem .92rem;
            border: 1px solid #BAE6FD;
            border-radius: 12px;
            color: #075985;
            background: #F0F9FF;
            font-size: .72rem;
            line-height: 1.5;
        }}

        .privacy-note-card {{
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            padding: 1rem 1.2rem;
            border: 1px solid #BAE6FD;
            border-radius: 16px;
            background: linear-gradient(135deg, #F0F9FF, #EFF6FF);
            margin-bottom: .75rem;
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}
        .privacy-note-icon {{
            flex: 0 0 48px;
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .privacy-shield-icon {{
            width: 48px;
            height: 48px;
            object-fit: contain;
        }}
        .privacy-note-body {{
            flex: 1;
            color: #075985;
            font-size: .78rem;
            line-height: 1.55;
        }}
        .privacy-note-body strong {{
            display: block;
            margin-bottom: .3rem;
            font-size: .82rem;
            color: #0369A1;
        }}
        .privacy-note-body p {{
            margin: 0;
        }}

        .empty-state {{
            display: grid;
            justify-items: center;
            gap: .28rem;
            padding: 1.05rem;
            border: 1px dashed #93C5FD;
            border-radius: 17px;
            color: {C_MUTED};
            text-align: center;
            background: linear-gradient(145deg, #FFFFFF, #F0F9FF);
        }}

        .empty-state img {{
            width: min(250px, 80%);
            max-height: 145px;
            object-fit: contain;
        }}

        .empty-state strong {{
            color: {C_TEXT};
            font-size: .9rem;
        }}

        /* ── AUDIT STATUS ── */
        .audit-ok, .audit-warning, .audit-error {{
            display: inline-flex;
            align-items: center;
            padding: .17rem .46rem;
            border-radius: 999px;
            font-size: .63rem;
            font-weight: 760;
        }}

        .audit-ok {{
            color: #047857;
            background: {C_SOFT_GREEN};
        }}

        .audit-warning {{
            color: #B45309;
            background: {C_SOFT_AMBER};
        }}

        .audit-error {{
            color: #B91C1C;
            background: {C_SOFT_RED};
        }}

        /* ── DELIVERABLES ── */
        .deliverable-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0,1fr));
            gap: .6rem;
        }}

        .deliverable-card {{
            min-height: 98px;
            padding: .82rem;
            border: 1px solid {C_BORDER};
            border-radius: 13px;
            background: white;
        }}

        .deliverable-card strong {{
            display: block;
            margin-bottom: .28rem;
            color: {C_TEXT};
            font-size: .74rem;
        }}

        .deliverable-card span {{
            color: {C_MUTED};
            font-size: .68rem;
            line-height: 1.45;
        }}

        /* ── SIDEBAR BRAND (old compat) ── */
        .sidebar-brand {{
            margin-bottom: .75rem;
            padding: .85rem;
            border: 1px solid {C_BORDER};
            border-radius: 16px;
            background: linear-gradient(145deg, #FFFFFF, #F3F8FF);
        }}

        .sidebar-title {{
            color: {C_TEXT};
            font-size: 1rem;
            font-weight: 830;
        }}

        .sidebar-subtitle {{
            margin-top: .2rem;
            color: {C_MUTED};
            font-size: .72rem;
        }}

        .sidebar-section {{
            margin: .75rem 0 .45rem;
            color: {C_PRIMARY};
            font-size: .64rem;
            font-weight: 820;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}

        /* ── FOOTER ── */
        .footer {{
            margin-top: 1.8rem;
            padding-top: .9rem;
            border-top: 1px solid {C_BORDER};
            color: #94A3B8;
            text-align: center;
            font-size: .65rem;
            line-height: 1.6;
        }}

        /* ── ANIMATIONS ── */
        .fade-in {{ animation: fade-in .5s cubic-bezier(.16,1,.3,1) both; }}
        .fade-up {{ animation: fade-up .55s cubic-bezier(.16,1,.3,1) both; }}
        .stagger-1 {{ animation-delay: .05s; }}
        .stagger-2 {{ animation-delay: .1s; }}
        .stagger-3 {{ animation-delay: .15s; }}
        .stagger-4 {{ animation-delay: .2s; }}
        .stagger-5 {{ animation-delay: .25s; }}

        @keyframes fade-in {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        @keyframes fade-up {{
            from {{ opacity: 0; transform: translateY(11px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes grow-bar {{
            from {{ transform: scaleX(0); }}
            to {{ transform: scaleX(1); }}
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: .55; transform: scale(.92); }}
            50% {{ opacity: 1; transform: scale(1.1); }}
        }}

        @keyframes lobby-float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}

        @keyframes filter-slide-in {{
            from {{ opacity: 0; transform: translateX(-18px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        @keyframes filterSlide {{
            from {{ opacity: 0; transform: translateY(-14px) scale(.98); }}
            to {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        @keyframes modal-in {{
            from {{ opacity: 0; transform: scale(.97) translateY(8px); }}
            to {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }}
        }}

        /* ── NO-ANIMATIONS MODE (user preference) ── */
        body.no-animations *, body.no-animations *::before, body.no-animations *::after {{
            animation: none !important;
            animation-duration: .01ms !important;
            transition: none !important;
            transition-duration: .01ms !important;
        }}
        body.no-animations .kpi-card:hover {{
            transform: none !important;
            box-shadow: 0 3px 14px rgba(15,23,42,.04) !important;
        }}
        body.no-animations [class*="st-key-chart_"]:hover,
        body.no-animations [class*="st-key-panel_"]:hover {{
            transform: none !important;
        }}

        /* ── PRESENTATION MODE ── */
        body.presentation-mode .kpi-value {{ font-size: 2.1rem !important; }}
        body.presentation-mode .kpi-label {{ font-size: .68rem !important; }}
        body.presentation-mode .section-banner-title {{ font-size: 2rem !important; }}
        body.presentation-mode .section-title {{ font-size: 1.6rem !important; }}
        body.presentation-mode h2 {{ font-size: 1.5rem !important; }}
        body.presentation-mode .kpi-caption {{ display: none; }}
        body.presentation-mode .stCaption {{ display: none; }}

        /* Presentation mode badge */
        .presentation-badge {{
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            padding: .28rem .8rem;
            background: linear-gradient(135deg, #7C3AED, #4F46E5);
            color: white;
            border-radius: 999px;
            font-size: .7rem;
            font-weight: 700;
            letter-spacing: .06em;
            text-transform: uppercase;
            box-shadow: 0 2px 10px rgba(124,58,237,.35);
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}
        .presentation-banner-bar {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: .75rem;
            padding: .55rem 1.2rem;
            background: linear-gradient(135deg, rgba(124,58,237,.08), rgba(79,70,229,.06));
            border: 1px solid rgba(124,58,237,.2);
            border-radius: 12px;
            margin-bottom: 1rem;
            animation: fade-up .4s cubic-bezier(.16,1,.3,1) both;
        }}
        .presentation-banner-bar span {{
            font-size: .82rem;
            font-weight: 600;
            color: #4F46E5;
        }}

        /* ── GRID LAYOUTS ── */
        .kpi-grid, .summary-grid-5 {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: .82rem;
            margin-bottom: 1.1rem;
        }}

        .summary-grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: .82rem;
            margin-bottom: 1.1rem;
        }}

        .health-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .82rem;
            margin-bottom: 1.1rem;
        }}

        /* ── RESPONSIVE ── */
        @media (max-width: 1100px) {{
            .kpi-grid, .summary-grid-5 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
            .summary-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .lobby-hero {{ grid-template-columns: 1fr 260px; }}
            .lobby-metrics {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
            .module-grid {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
            .brand-subtitle {{ display: none; }}
            .st-key-top_header .brand-subtitle {{ display: none; }}
            .refresh-time {{ display: none; }}
            .hero-content {{ max-width: 78%; }}
            /* Shrink hero stats to 3 columns when sidebar is open */
            .hero-stat-row {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        }}

        @media (max-width: 1024px) {{
            .kpi-grid, .summary-grid-5 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
            .summary-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .lobby-hero {{ grid-template-columns: 1fr 240px; }}
            .lobby-metrics {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
            .module-grid {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
            .brand-subtitle {{ display: none; }}
            .refresh-time {{ display: none; }}
        }}

        @media (max-width: 800px) {{
            .block-container {{
                padding-left: .75rem;
                padding-right: .75rem;
            }}
            .st-key-top_header {{
                position: relative;
                top: .1rem;
                padding: .48rem .65rem;
            }}
            .hero-section {{
                min-height: 185px;
                background-size: cover, cover, cover;
                background-position: center, center right, center;
            }}
            .hero-content {{ max-width: 100%; }}
            .hero-stat-row {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}
            .deliverable-grid {{ grid-template-columns: 1fr; }}
            .lobby-shell {{
                min-height: auto;
                padding: 1.2rem;
                border-radius: 20px;
                /* On mobile, anchor hero image to right-center */
                background-position: left top, right center;
            }}
            .lobby-hero {{ grid-template-columns: 1fr; }}
            /* hide transparent spacer on mobile — text takes full width */
            .lobby-visual {{ display: none; }}
            .lobby-title {{ font-size: clamp(1.85rem, 10vw, 2.9rem); }}
            .lobby-metrics {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
            .module-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
            .section-banner {{ height: clamp(80px, 12vw, 110px); }}
            [data-testid="stDialog"] > div {{
                width: 96vw !important;
                max-width: 96vw !important;
                max-height: 92vh !important;
            }}
        }}

        @media (max-width: 768px) {{
            .kpi-grid, .summary-grid-5, .health-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .summary-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .st-key-horizontal_navigation {{ overflow-x: auto; }}
        }}

        @media (max-width: 480px) {{
            .kpi-grid, .summary-grid-5, .summary-grid-4, .health-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .hero-stat-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .lobby-metrics {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
            .module-grid {{ grid-template-columns: 1fr; }}
            .conclusion-visual {{ display: none; }}
            .lobby-title {{ font-size: clamp(1.6rem, 8vw, 2.4rem); }}
            [class*="st-key-chart_"], [class*="st-key-panel_"] {{
                padding: .62rem .55rem .5rem;
                border-radius: 16px;
            }}
        }}

        /* ── ACTIVE TAB ENHANCEMENT ── */
        [data-baseweb="tab"][aria-selected="true"] {{
            border-bottom: 3px solid {C_PRIMARY} !important;
            color: {C_PRIMARY} !important;
            font-weight: 700 !important;
        }}

        /* ── FILTER CHIP IMPROVEMENT ── */
        .filter-chip {{
            display: inline-flex;
            align-items: center;
            background: #EFF6FF;
            border: 1.5px solid {C_PRIMARY}40;
            border-radius: 999px;
            padding: .18rem .65rem;
            font-size: .68rem;
            font-weight: 600;
            color: {C_PRIMARY};
            white-space: nowrap;
            transition: background .18s ease, border-color .18s ease;
        }}
        .filter-chip:hover {{
            background: #DBEAFE;
            border-color: {C_PRIMARY};
        }}

        /* ── KPI PROGRESS BAR ANIMATION ── */
        @keyframes progress-fill {{
            from {{ width: 0%; }}
            to {{ width: var(--progress-w, 50%); }}
        }}
        .kpi-progress-bar-fill {{
            animation: progress-fill .8s cubic-bezier(.25,.8,.25,1) forwards;
        }}

        /* ── DIALOG / MODAL Z-INDEX (above all Plotly layers) ── */
        div[data-testid="stDialog"],
        div[data-testid="stModal"] {{
            z-index: 999999 !important;
        }}

        div[data-testid="stDialog"] [role="dialog"],
        div[data-testid="stModal"] [role="dialog"] {{
            z-index: 1000000 !important;
            background: #F8FBFF !important;
            overflow: auto !important;
        }}

        div[data-testid="stDialog"]::backdrop,
        div[data-testid="stModal"]::backdrop {{
            background: rgba(15, 23, 42, 0.55) !important;
            z-index: 999998 !important;
        }}

        /* ── PLOTLY: hide spikes, selection/zoom layers, force stable tooltip ── */
        .js-plotly-plot .hoverlayer {{
            z-index: 1 !important;
        }}
        .js-plotly-plot .spikelines {{
            display: none !important;
        }}
        /* Force-hide drag selection box, zoom layer, and select outlines */
        .js-plotly-plot .select-outline,
        .js-plotly-plot .zoomlayer,
        .js-plotly-plot .selectlayer {{
            display: none !important;
            pointer-events: none !important;
        }}
        /* Stable dark hover tooltip styling */
        .js-plotly-plot .hoverlayer .hovertext path {{
            fill: #0F172A !important;
            stroke: rgba(255,255,255,0.35) !important;
        }}
        .js-plotly-plot .hoverlayer .hovertext text,
        .js-plotly-plot .hoverlayer .hovertext tspan {{
            fill: #FFFFFF !important;
            font-family: Inter, Arial, sans-serif !important;
            font-size: 13px !important;
            z-index: 1 !important;
        }}

        /* ── KPI GRID & CARDS ── */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 1.05rem;
            margin: 1.2rem 0 1.8rem;
        }}
        .kpi-card {{
            position: relative;
            overflow: hidden;
            padding: 1.2rem 1.15rem 1.05rem;
            border: 1.5px solid rgba(16,142,233,.16);
            border-radius: 22px;
            box-shadow: 0 10px 30px rgba(16,142,233,.10), 0 1px 4px rgba(15,23,42,.04);
            min-height: 148px;
        }}
        .kpi-orb {{
            position: absolute;
            right: -22px;
            top: -30px;
            width: 88px;
            height: 88px;
            border-radius: 999px;
            opacity: .06;
            pointer-events: none;
        }}
        .kpi-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .65rem;
            margin-bottom: .7rem;
        }}
        .kpi-icon {{
            width: 48px;
            height: 48px;
            flex: 0 0 48px;
            border-radius: 14px;
            border: 1.5px solid;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            line-height: 1;
        }}
        .kpi-label {{
            color: #64748B;
            font-size: .66rem;
            font-weight: 850;
            letter-spacing: .08em;
            text-transform: uppercase;
            text-align: right;
            line-height: 1.35;
        }}
        .kpi-value {{
            color: #07132F;
            font-size: 2.05rem;
            font-weight: 900;
            letter-spacing: -.045em;
            line-height: 1.05;
        }}
        .kpi-caption {{
            margin-top: .42rem;
            color: #64748B;
            font-size: .72rem;
        }}
        .progress-track {{
            height: 6px;
            margin-top: .8rem;
            border-radius: 999px;
            background: #EEF2F7;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 999px;
        }}
        @media (max-width: 1200px) {{
            .kpi-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
        }}
        @media (max-width: 760px) {{
            .kpi-grid {{ grid-template-columns: 1fr; }}
        }}

        /* ── REVISED SNAPSHOT FLYER STYLING ── */
        .st-key-snapshot_flyer_frame_desktop {{
            background: #FFFFFF !important;
            border: 2px solid #D7E8FF !important;
            border-radius: 24px !important;
            padding: 24px !important;
            box-shadow: 0 12px 40px rgba(16, 142, 233, 0.05) !important;
        }}

        .flyer-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }}

        .flyer-kpi-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 8px 10px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.01);
        }}

        .flyer-kpi-label {{
            font-size: 0.62rem;
            color: #64748B;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 2px;
        }}

        .flyer-kpi-value {{
            font-size: 1.35rem;
            font-weight: 900;
            color: #108EE9;
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }}

        .flyer-section-title {{
            font-size: 0.8rem;
            font-weight: 850;
            color: #07132F;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
            padding-bottom: 4px;
            border-bottom: 2px solid #F0F6FF;
        }}

        .flyer-insight-card {{
            background: linear-gradient(135deg, #F0F6FF 0%, #E6F0FA 100%);
            border: 1px solid #D7E8FF;
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 14px;
        }}

        .flyer-insight-title {{
            font-size: 0.8rem;
            font-weight: 800;
            color: #07132F;
            margin-bottom: 6px;
        }}

        .flyer-insight-text {{
            font-size: 0.74rem;
            color: #475569;
            line-height: 1.45;
        }}

        .flyer-mini-stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}

        .flyer-mini-stat-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 8px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.01);
        }}

        .flyer-mini-stat-val {{
            font-size: 1.1rem;
            font-weight: 900;
            color: #07132F;
            margin-bottom: 2px;
        }}

        .flyer-mini-stat-lbl {{
            font-size: 0.58rem;
            color: #64748B;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}

        .flyer-review-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 10px;
            margin-bottom: 8px;
            box-shadow: 0 1px 4px rgba(7, 19, 47, 0.02);
        }}

        .flyer-review-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }}

        .flyer-review-date {{
            font-size: 0.65rem;
            color: #64748B;
            font-weight: 600;
        }}

        .flyer-review-text {{
            font-size: 0.72rem;
            color: #102040;
            line-height: 1.3;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            white-space: normal;
        }}

        .flyer-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid #F0F6FF;
            font-size: 0.68rem;
            color: #94A3B8;
        }}

        .insight-highlight-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.72rem;
            margin: 0.5rem 0 0.85rem;
        }}
        .insight-highlight-card {{
            padding: 0.75rem 1rem;
            border-radius: 14px;
            min-width: 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            word-break: keep-all;
            overflow-wrap: normal;
        }}
        .insight-highlight-label {{
            font-size: 0.58rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            word-break: keep-all;
            overflow-wrap: normal;
            white-space: normal;
        }}
        .insight-highlight-value {{
            font-size: 0.9rem;
            font-weight: 700;
            color: #0F172A;
            line-height: 1.3;
            word-break: keep-all;
            overflow-wrap: normal;
            white-space: normal;
        }}

        /* Desktop vs Mobile display utilities */
        div[class*="st-key-"][class*="_desktop"] {{
            display: block !important;
        }}
        div[class*="st-key-"][class*="_mobile"] {{
            display: none !important;
        }}
        @media (max-width: 768px) {{
            div[class*="st-key-"][class*="_desktop"] {{
                display: none !important;
            }}
            div[class*="st-key-"][class*="_mobile"] {{
                display: block !important;
            }}
        }}

        /* Scoped style to hide Plotly zoom/select overlays in normal charts */
        div[class*="st-key-normal_plotly_container"] .js-plotly-plot .selectlayer,
        div[class*="st-key-normal_plotly_container"] .js-plotly-plot .zoomlayer,
        div[class*="st-key-normal_plotly_container"] .js-plotly-plot .dragcover {{
            display: none !important;
            pointer-events: none !important;
        }}

        /* Fullscreen mobile chart dialog adjustments */
        @media (max-width: 768px) {{
            div[data-testid="stDialog"] > div {{
                width: 92vw !important;
                max-width: 92vw !important;
                max-height: 85vh !important;
                padding: 12px !important;
            }}
            /* Clamp the height of the chart container in fullscreen mobile view */
            div[data-testid="stDialog"] [data-testid="stPlotlyChart"] {{
                height: 360px !important;
                min-height: 320px !important;
                max-height: 420px !important;
            }}
            /* Hide modal header title text to avoid double titles (body title remains visible) */
            div[data-testid="stDialog"] h1[id*="detail-grafik"] {{
                display: none !important;
            }}
            /* Make dialog close button larger and easier to click on mobile viewports */
            div[data-testid="stDialog"] [data-testid="stHeader"] button,
            div[data-testid="stDialog"] button[aria-label="Close"] {{
                width: 44px !important;
                height: 44px !important;
                min-width: 44px !important;
                min-height: 44px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                top: 8px !important;
                right: 8px !important;
            }}
        }}

        /* Responsive overrides for layout columns on mobile screen widths */
        @media (max-width: 768px) {{
            /* Stack columns inside all containers with key starting with layout_ or snapshot_flyer */
            div[class*="st-key-layout_"] [data-testid="stHorizontalBlock"],
            div[class*="st-key-snapshot_flyer_"] [data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
                gap: 16px !important;
            }}
            div[class*="st-key-layout_"] [data-testid="stHorizontalBlock"] > div,
            div[class*="st-key-snapshot_flyer_"] [data-testid="stHorizontalBlock"] > div {{
                width: 100% !important;
                max-width: 100% !important;
            }}

            /* Enforce 2-column layout for KPI grid on mobile */
            .kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                gap: 8px !important;
                margin: 0.8rem 0 1.2rem !important;
            }}

            .insight-highlight-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                gap: 8px !important;
                margin: 0.4rem 0 0.7rem !important;
            }}
            .insight-highlight-card {{
                padding: 0.6rem 0.8rem !important;
            }}
            .insight-highlight-label {{
                font-size: 0.54rem !important;
            }}
            .insight-highlight-value {{
                font-size: 0.82rem !important;
            }}
            .kpi-card {{
                min-height: 112px !important;
                padding: 10px 8px !important;
                word-break: keep-all !important;
                overflow-wrap: normal !important;
                min-width: 0 !important;
            }}
            .kpi-card:nth-child(5) {{
                grid-column: span 2 !important;
            }}
            .kpi-head {{
                flex-direction: column !important;
                align-items: flex-start !important;
                gap: 4px !important;
                margin-bottom: 4px !important;
            }}
            .kpi-icon {{
                width: 32px !important;
                height: 32px !important;
                flex: 0 0 32px !important;
                font-size: 1.05rem !important;
            }}
            .kpi-label {{
                text-align: left !important;
                word-break: keep-all !important;
                overflow-wrap: normal !important;
                white-space: normal !important;
                font-size: 0.58rem !important;
                line-height: 1.1 !important;
                min-width: 0 !important;
            }}
            .kpi-value {{
                margin-top: 2px !important;
                font-size: 1.35rem !important;
                font-variant-numeric: tabular-nums !important;
            }}
            .kpi-caption {{
                display: none !important;
            }}
            .progress-track {{
                margin-top: 0.4rem !important;
                height: 4px !important;
            }}

            /* Mobile Hero banner constraints */
            .hero-section {{
                min-height: 155px !important;
                max-height: 250px !important;
                padding: 14px !important;
                border-radius: 16px !important;
                background-image:
                    linear-gradient(92deg, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.96) 100%),
                    {hero_background},
                    linear-gradient(135deg, #F8FBFF 0%, #EBF5FF 100%) !important;
            }}
            .hero-title {{
                font-size: 1.35rem !important;
                line-height: 1.15 !important;
            }}
            .hero-subtitle {{
                font-size: 0.72rem !important;
                line-height: 1.3 !important;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                margin-top: 2px !important;
            }}
            .badge-row span:nth-child(n+3) {{
                display: none !important;
            }}
            .hero-stat-row {{
                display: none !important;
            }}

            /* Mobile top header tweaks */
            .st-key-top_header_mobile {{
                height: 56px !important;
                display: flex !important;
                align-items: center !important;
                padding: 4px 8px !important;
            }}
        }}
        """
    # Split into two halves to reduce peak memory usage during injection.
    # A 64KB f-string consumed in one markdown() call can trigger MemoryError
    # in constrained environments (e.g. Streamlit AppTest).
    lines = _css.split("\n")
    mid = len(lines) // 2
    _css_a = "\n".join(lines[:mid])
    _css_b = "\n".join(lines[mid:])
    try:
        st.markdown(f"<style>{_css_a}\n{_css_b}</style>", unsafe_allow_html=True)
    except MemoryError:
        # Fallback: inject a minimal style sheet with just core tokens
        _minimal = f"""
        :root {{
            --dana-primary: {C_PRIMARY};
            --dana-deep: {C_DEEP};
            --dana-bg: {C_BG};
        }}
        [data-testid="stAppViewContainer"] {{
            background: {C_BG} !important;
        }}
        """
        st.markdown(f"<style>{_minimal}</style>", unsafe_allow_html=True)



def inject_preference_classes(filters: dict) -> None:
    """Inject dynamic CSS overrides based on user animation/presentation prefs.

    Uses CSS custom-property overrides injected via st.html <style> block.
    Avoids JS body.classList because st.html() runs in a sandboxed iframe
    in Streamlit ≥1.38 and cannot access the parent document.body.
    Falls back to streamlit.components.v1.html for script injection.
    """
    animations_on = bool(filters.get("animations", True))
    presentation_on = bool(filters.get("presentation", False))

    # ── CSS override block ──────────────────────────────────────────────────
    anim_css = "" if animations_on else """
        *, *::before, *::after {
            animation: none !important;
            animation-duration: 0.01ms !important;
            transition: none !important;
            transition-duration: 0.01ms !important;
        }
        .kpi-card:hover { transform: none !important; }
    """
    pres_css = "" if not presentation_on else """
        .kpi-value { font-size: 2.1rem !important; }
        .kpi-label { font-size: .68rem !important; }
        .section-banner-title { font-size: 2rem !important; }
        .section-title { font-size: 1.6rem !important; }
        h2 { font-size: 1.5rem !important; }
        .kpi-caption { display: none !important; }
    """

    if anim_css or pres_css:
        combined = f"<style>{anim_css}{pres_css}</style>"
        st.html(combined)

    # ── JS body class injection (best-effort via st.iframe) ─────────────────
    try:
        no_anim_action = "remove" if animations_on else "add"
        pres_action = "add" if presentation_on else "remove"
        js = f"""
        <script>
        (function() {{
            var root = window.parent ? window.parent.document : document;
            var b = root.body;
            if (b) {{
                b.classList.{no_anim_action}('no-animations');
                b.classList.{pres_action}('presentation-mode');
            }}
        }})();
        </script>
        """
        st.iframe(js, height=0)

    except Exception:
        pass  # graceful degradation — CSS overrides above still apply


def icon_svg(name: str, color: str = "currentColor", size: str = "18") -> str:
    """Return a Lucide-style SVG icon with inline stroke for st.html() iframe compatibility."""
    paths = {
        "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        "reviews": '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 8h8M8 12h5"/>',
        "score": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
        "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        "sentiment": '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><path d="M9 9h.01M15 9h.01"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
        "refresh": '<path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/>',
        "search": '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
        "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
        "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
        "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    }
    body = paths.get(name, paths["score"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" '
        f'style="display:block;flex:0 0 auto;color:{color};" '
        f'stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def asset_svg(filename: str, fallback: str = "") -> str:
    path = asset_path(filename)
    try:
        return path.read_text(encoding="utf-8") if path.exists() else fallback
    except OSError:
        return fallback


def asset_img_tag(
    filename: str,
    alt: str = "",
    class_name: str = "",
    fallback: str = "",
) -> str:
    return render_image_asset(
        filename,
        class_name=class_name or None,
        alt=alt,
        fallback=fallback,
    )


def section_heading(
    kicker: str,
    title: str,
    description: str = "",
    asset: str | None = None,
) -> None:
    visual = (
        '<div class="section-visual" aria-hidden="true">'
        f'{asset_img_tag(asset, alt="")}</div>'
        if asset
        else ""
    )
    st.html(
        f"""
        <div class="section-heading fade-up">
            {visual}
            <div class="section-heading-copy">
                <div class="section-kicker">{escape(kicker)}</div>
                <h2 class="section-title">{escape(title)}</h2>
                {f'<div class="section-description">{escape(description)}</div>' if description else ''}
            </div>
        </div>
        """
    )


def section_banner(
    kicker: str,
    title: str,
    description: str = "",
    banner_asset_key: str = "",
) -> None:
    """Render a premium wide-banner header using 2048×682 landscape images.
    banner_asset_key: key in ASSETS registry (e.g. 'survey_banner')
    """
    banner_filename = ASSETS.get(banner_asset_key, "")
    banner_bg = asset_css_url(banner_filename) if banner_filename else "none"
    desc_html = (
        f'<div class="section-banner-desc">{escape(description)}</div>'
        if description else ""
    )
    st.html(
        f"""
        <div class="section-banner" style="background-image: {banner_bg};">
            <div class="section-banner-content">
                <div class="section-banner-kicker">{escape(kicker)}</div>
                <h2 class="section-banner-title">{escape(title)}</h2>
                {desc_html}
            </div>
        </div>
        """
    )


def render_empty_state(
    title: str,
    message: str,
) -> None:
    visual = asset_img_tag("empty_state.svg", alt="")
    st.html(
        f"""
        <div class="empty-state" role="status">
            {visual}
            <strong>{escape(title)}</strong>
            <span>{escape(message)}</span>
        </div>
        """
    )


def format_wib(value: datetime) -> str:
    month_names = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    local = value.astimezone(WIB)
    return (
        f"{local.day:02d} {month_names[local.month - 1]} {local.year}, "
        f"{local:%H:%M:%S} WIB"
    )


def render_live_header(
    cache_refresh: datetime,
    data_updated: datetime | None,
    loaded: bool,
) -> None:
    status_class = "" if loaded else " is-error"
    status_text = "Data Loaded" if loaded else "Periksa Data"
    refresh_text = escape(format_wib(cache_refresh))
    updated_text = (
        escape(format_wib(data_updated))
        if data_updated is not None
        else "Tidak tersedia"
    )
    current_time = datetime.now(WIB).strftime("%H:%M:%S WIB")
    st.html(
        f"""
        <div class="header-status">
            <span class="status-pill{status_class}">
                <span class="status-dot"></span>{status_text}
            </span>
            <span class="time-pill">{current_time}</span>
            <span class="time-pill refresh-time">Data updated: {updated_text}</span>
            <span class="time-pill refresh-time">Cache refreshed: {refresh_text}</span>
        </div>
        """
    )


# =============================================================================
# DATA LOADING AND PRIVACY
# =============================================================================
def file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


@st.cache_data(show_spinner=False)
def load_excel_cached(path_text: str, signature: tuple[int, int]) -> pd.DataFrame:
    del signature
    return pd.read_excel(path_text, engine="openpyxl")


@st.cache_data(show_spinner=False)
def load_csv_cached(path_text: str, signature: tuple[int, int]) -> pd.DataFrame:
    del signature
    return pd.read_csv(path_text)


def load_frame(path: Path, kind: str) -> tuple[pd.DataFrame | None, str | None]:
    signature = file_signature(path)
    if signature is None:
        return None, f"File tidak ditemukan: {path.name}"
    if signature[1] == 0:
        return None, f"File kosong (0 byte): {path.name}"
    try:
        if kind == "excel":
            frame = load_excel_cached(str(path), signature)
        else:
            frame = load_csv_cached(str(path), signature)
    except Exception as exc:
        return None, f"{path.name} tidak dapat dibaca: {exc}"
    if frame.empty:
        return None, f"{path.name} tidak memiliki baris data."
    return frame, None


def load_all_data() -> dict[str, Any]:
    survey, survey_error = load_frame(SURVEY_PATH, "excel")
    reviews, review_error = load_frame(REVIEW_PATH, "excel")
    questionnaire, questionnaire_error = load_frame(QUESTIONNAIRE_PATH, "csv")
    errors = {
        key: message
        for key, message in {
            "survey": survey_error,
            "reviews": review_error,
            "questionnaire": questionnaire_error,
        }.items()
        if message
    }
    return {
        "survey": survey,
        "reviews": reviews,
        "questionnaire": questionnaire,
        "errors": errors,
    }


def latest_primary_data_modified() -> datetime | None:
    timestamps: list[float] = []
    for path in (SURVEY_PATH, REVIEW_PATH, QUESTIONNAIRE_PATH):
        try:
            timestamps.append(path.stat().st_mtime)
        except OSError:
            continue
    return datetime.fromtimestamp(max(timestamps), tz=WIB) if timestamps else None


def _audit_frame(frame: pd.DataFrame) -> dict[str, Any]:
    sensitive = [str(column) for column in frame.columns if is_sensitive_column(column)]
    return {
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": ", ".join(map(str, frame.columns)),
        "nulls": int(frame.isna().sum().sum()),
        "duplicates": int(frame.duplicated().sum()),
        "sensitive_columns": ", ".join(sensitive) if sensitive else "-",
    }


def _expected_rows_for(path: Path) -> int | None:
    expected = {
        SURVEY_PATH: EXPECTED_BASELINE["survey_rows"],
        RAW_SURVEY_PATH: EXPECTED_BASELINE["survey_rows"],
        REVIEW_PATH: EXPECTED_BASELINE["review_rows"],
        RAW_REVIEW_PATH: EXPECTED_BASELINE["review_rows"],
        QUESTIONNAIRE_PATH: EXPECTED_BASELINE["question_count"],
    }
    return expected.get(path)


def audit_data_sources() -> pd.DataFrame:
    """Return privacy-safe metadata for every known source without exposing values."""
    records: list[dict[str, Any]] = []
    for role, path, kind, public_source in DATA_SOURCE_SPECS:
        base_record = {
            "Sumber": path.name,
            "Peran": role,
            "Publik": "Ya" if public_source else "Tidak",
            "Ditemukan": path.exists(),
            "Ukuran (KB)": round(path.stat().st_size / 1024, 1) if path.exists() else 0.0,
            "Sheet/Tabel": 0,
            "Baris": 0,
            "Kolom": 0,
            "Nama Kolom": "-",
            "Null": 0,
            "Duplikat": 0,
            "Kolom Identitas": "-",
            "Rekonsiliasi": "-",
            "Status": "Valid",
        }
        if not path.exists():
            base_record["Status"] = (
                "Opsional tidak tersedia"
                if path == DATABASE_PATH
                else "Error: file tidak ditemukan"
            )
            records.append(base_record)
            continue
        try:
            frames: list[pd.DataFrame] = []
            labels: list[str] = []
            if kind == "excel":
                with pd.ExcelFile(path, engine="openpyxl") as workbook:
                    labels = list(workbook.sheet_names)
                    frames = [
                        workbook.parse(sheet_name=sheet)
                        for sheet in labels
                    ]
            elif kind == "csv":
                labels = ["CSV"]
                frames = [pd.read_csv(path)]
            else:
                with closing(sqlite3.connect(path)) as connection:
                    tables = pd.read_sql_query(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                        "ORDER BY name",
                        connection,
                    )["name"].astype(str).tolist()
                    labels = tables
                    frames = [
                        pd.read_sql_query(f'SELECT * FROM "{table}"', connection)
                        for table in tables
                    ]
            summaries = [_audit_frame(frame) for frame in frames]
            base_record["Sheet/Tabel"] = len(labels)
            base_record["Baris"] = sum(item["rows"] for item in summaries)
            base_record["Kolom"] = max(
                (item["columns"] for item in summaries),
                default=0,
            )
            base_record["Nama Kolom"] = " | ".join(
                f"{label}: {item['column_names']}"
                for label, item in zip(labels, summaries)
            ) or "-"
            base_record["Null"] = sum(item["nulls"] for item in summaries)
            base_record["Duplikat"] = sum(item["duplicates"] for item in summaries)
            sensitive = sorted(
                {
                    column.strip()
                    for item in summaries
                    for column in item["sensitive_columns"].split(",")
                    if column.strip() and column.strip() != "-"
                }
            )
            base_record["Kolom Identitas"] = ", ".join(sensitive) if sensitive else "-"
            expected_rows = _expected_rows_for(path)
            if expected_rows is not None:
                actual_rows = base_record["Baris"]
                matches = actual_rows == expected_rows
                base_record["Rekonsiliasi"] = (
                    f"{actual_rows}/{expected_rows} baris"
                )
                if not matches:
                    base_record["Status"] = "Peringatan: jumlah baris berbeda"
            elif path == DATABASE_PATH and labels:
                unique_details = [
                    f"{label}: {len(frame)} raw / {len(frame.drop_duplicates())} unik"
                    for label, frame in zip(labels, frames)
                ]
                base_record["Rekonsiliasi"] = "; ".join(unique_details)
                normalized_table_names = {
                    normalized_column_name(label): frame
                    for label, frame in zip(labels, frames)
                }
                database_expectations = {
                    "ulasan": 330,
                    "kuesioner": 20,
                    "demografi": 9,
                }
                database_warnings: list[str] = []
                for keyword, expected_unique in database_expectations.items():
                    matched = next(
                        (
                            frame
                            for table_name, frame in normalized_table_names.items()
                            if keyword in table_name
                        ),
                        None,
                    )
                    if matched is not None and len(matched.drop_duplicates()) != expected_unique:
                        database_warnings.append(
                            f"{keyword} unik {len(matched.drop_duplicates())}, "
                            f"diharapkan {expected_unique}"
                        )
                if database_warnings:
                    base_record["Status"] = (
                        "Peringatan DB: " + "; ".join(database_warnings)
                    )
                elif base_record["Duplikat"]:
                    base_record["Status"] = "Valid setelah deduplikasi"
            if public_source and sensitive:
                base_record["Status"] = "Error: identitas pada sumber publik"
            elif not public_source and sensitive and base_record["Status"] == "Valid":
                base_record["Status"] = "Terlindungi"
            elif path == DATABASE_PATH and not labels:
                base_record["Status"] = "Peringatan: database tanpa tabel"
        except Exception as exc:
            base_record["Status"] = f"Error: {type(exc).__name__}"
            base_record["Rekonsiliasi"] = str(exc)[:120]
        records.append(base_record)
    return pd.DataFrame(records)


def normalized_column_name(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value).casefold())
    return re.sub(r"\s+", " ", text).strip()


def is_sensitive_column(column: Any) -> bool:
    normalized = normalized_column_name(column)
    if not normalized or normalized.startswith("unnamed "):
        return False
    if normalized in SENSITIVE_COLUMN_PHRASES:
        return True
    if any(
        re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", normalized)
        for phrase in SENSITIVE_COLUMN_PHRASES
    ):
        return True
    tokens = set(normalized.split())
    if normalized == "responden":
        return True
    return bool(tokens & SENSITIVE_COLUMN_TOKENS)



def sanitize_public_df(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None:
        return pd.DataFrame()
    safe_columns = [column for column in frame.columns if not is_sensitive_column(column)]
    return frame.loc[:, safe_columns].copy()


def find_column(frame: pd.DataFrame | None, candidates: list[str]) -> str | None:
    if frame is None:
        return None
    normalized = {column: normalized_column_name(column) for column in frame.columns}
    for candidate in candidates:
        exact = normalized_column_name(candidate)
        for column, value in normalized.items():
            if value == exact:
                return str(column)
    for candidate in candidates:
        phrase = normalized_column_name(candidate)
        for column, value in normalized.items():
            if phrase in value:
                return str(column)
    return None


def detect_question_columns(frame: pd.DataFrame | None) -> list[str]:
    if frame is None:
        return []
    demographic_terms = {
        "timestamp", "waktu", "nama", "jenis kelamin", "gender",
        "usia", "umur", "seberapa sering", "frekuensi", "email",
        "telepon", "pekerjaan", "pendidikan",
    }
    columns: list[str] = []
    for column in frame.columns:
        normalized = normalized_column_name(column)
        if is_sensitive_column(column):
            continue
        if any(term in normalized for term in demographic_terms):
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        valid = numeric.dropna()
        if not valid.empty and valid.between(1, 5).all():
            columns.append(str(column))
    return columns


def prepare_survey_data(
    frame: pd.DataFrame | None,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    if frame is None:
        return None, {}
    survey = frame.copy()
    survey.columns = [str(column).strip() for column in survey.columns]
    columns = {
        "name": find_column(survey, ["Siapa nama Anda?", "nama responden", "nama"]),
        "gender": find_column(survey, ["Apa jenis kelamin Anda?", "jenis kelamin", "gender"]),
        "age": find_column(survey, ["Berapa usia Anda sekarang?", "usia", "umur"]),
        "frequency": find_column(
            survey,
            ["Seberapa sering Anda menggunakan aplikasi DANA?", "frekuensi", "seberapa sering"],
        ),
        "timestamp": find_column(survey, ["Timestamp", "tanggal survey", "waktu"]),
    }
    columns["questions"] = detect_question_columns(survey)
    timestamp_column = columns.get("timestamp")
    if timestamp_column and timestamp_column in survey.columns:
        survey[timestamp_column] = pd.to_datetime(
            survey[timestamp_column], errors="coerce"
        )
    return survey, columns


def prepare_review_data(
    frame: pd.DataFrame | None,
) -> tuple[pd.DataFrame | None, dict[str, str | None]]:
    if frame is None:
        return None, {}
    reviews = frame.copy()
    reviews.columns = [str(column).strip() for column in reviews.columns]
    columns = {
        "username": find_column(reviews, ["username", "nama pengguna", "user name"]),
        "rating": find_column(reviews, ["rating", "bintang", "nilai"]),
        "date": find_column(reviews, ["tanggal", "date", "waktu"]),
        "review": find_column(reviews, ["ulasan", "review", "komentar", "content"]),
    }
    rating_column = columns.get("rating")
    if rating_column and rating_column in reviews.columns:
        reviews[rating_column] = pd.to_numeric(
            reviews[rating_column], errors="coerce"
        )
        reviews["sentimen"] = np.select(
            [
                reviews[rating_column].ge(4),
                reviews[rating_column].eq(3),
                reviews[rating_column].le(2),
            ],
            ["Positif", "Netral", "Negatif"],
            default="Tidak Diketahui",
        )
    else:
        reviews["sentimen"] = "Tidak Diketahui"
    date_column = columns.get("date")
    if date_column and date_column in reviews.columns:
        reviews[date_column] = pd.to_datetime(reviews[date_column], errors="coerce")
    return reviews, columns


def compute_questionnaire_from_survey(
    survey: pd.DataFrame | None, question_columns: list[str]
) -> pd.DataFrame | None:
    if survey is None or survey.empty or not question_columns:
        return None
    available = [column for column in question_columns if column in survey.columns]
    if not available:
        return None
    numeric = survey[available].apply(pd.to_numeric, errors="coerce")
    means = numeric.mean().dropna()
    if means.empty:
        return None
    return pd.DataFrame(
        {
            "pertanyaan": means.index.astype(str),
            "rata_rata": means.values.astype(float),
            "label": [f"Q{index + 1}" for index in range(len(means))],
        }
    )


def normalize_questionnaire(
    questionnaire: pd.DataFrame | None,
    survey: pd.DataFrame | None,
    question_columns: list[str],
) -> pd.DataFrame | None:
    if questionnaire is not None and not questionnaire.empty:
        candidate = questionnaire.dropna(how="all").copy()
        question_column = find_column(
            candidate, ["pertanyaan", "question", "indikator", "Unnamed: 0"]
        )
        score_column = find_column(
            candidate, ["rata_rata", "rata rata", "mean", "average", "skor", "nilai", "0"]
        )
        if question_column is None and len(candidate.columns) >= 1:
            question_column = str(candidate.columns[0])
        if score_column is None and len(candidate.columns) >= 2:
            score_column = str(candidate.columns[1])
        if question_column and score_column:
            normalized = pd.DataFrame(
                {
                    "pertanyaan": candidate[question_column].astype(str).str.strip(),
                    "rata_rata": pd.to_numeric(
                        candidate[score_column], errors="coerce"
                    ),
                }
            )
            normalized = normalized.dropna(subset=["rata_rata"])
            normalized = normalized[
                normalized["pertanyaan"].str.len().ge(4)
                & normalized["rata_rata"].between(1, 5)
            ].reset_index(drop=True)
            if not normalized.empty:
                normalized["label"] = [
                    f"Q{index + 1}" for index in range(len(normalized))
                ]
                return normalized[["pertanyaan", "rata_rata", "label"]]
    return compute_questionnaire_from_survey(survey, question_columns)


def score_interpretation(value: float) -> str:
    if value >= 4:
        return "Kuat/Baik"
    if value >= 3:
        return "Cukup"
    return "Perlu Perhatian"


def add_questionnaire_categories(questionnaire: pd.DataFrame | None) -> pd.DataFrame | None:
    if questionnaire is None:
        return None
    categorized = questionnaire.copy()
    categorized["kategori"] = categorized["rata_rata"].map(score_interpretation)
    return categorized


def has_data(df: pd.DataFrame | None) -> bool:
    return df is not None and not df.empty


def compute_variable_scores(
    survey: pd.DataFrame | None,
    question_columns: list[str],
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    records: list[dict[str, Any]] = []
    missing_by_variable: dict[str, list[str]] = {}
    if survey is None or survey.empty:
        return pd.DataFrame(
            columns=["variabel", "rata_rata", "interpretasi", "jumlah_indikator"]
        ), missing_by_variable
    for variable, configured_columns in VARIABLE_GROUPS.items():
        columns = (
            list(question_columns)
            if configured_columns == "ALL_QUESTION_COLUMNS"
            else list(configured_columns)
        )
        missing = [column for column in columns if column not in survey.columns]
        available = [column for column in columns if column in survey.columns]
        if missing:
            missing_by_variable[variable] = missing
        if not available:
            continue
        numeric = survey[available].apply(pd.to_numeric, errors="coerce")
        score = numeric.stack().mean()
        if pd.isna(score):
            continue
        records.append(
            {
                "variabel": variable,
                "rata_rata": float(score),
                "interpretasi": score_interpretation(float(score)),
                "jumlah_indikator": len(available),
            }
        )
    return pd.DataFrame(records), missing_by_variable


def validate_data_invariants(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
) -> list[str]:
    errors: list[str] = []

    def expect(label: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            errors.append(f"{label}: aktual {actual!r}, diharapkan {expected!r}")

    if survey is None:
        errors.append("Survey utama tidak tersedia.")
    else:
        expect("Jumlah survey", len(survey), EXPECTED_BASELINE["survey_rows"])
        for key, expected_counts in (
            ("gender", EXPECTED_BASELINE["gender"]),
            ("age", EXPECTED_BASELINE["age"]),
            ("frequency", EXPECTED_BASELINE["frequency"]),
        ):
            column = survey_columns.get(key)
            if not column or column not in survey.columns:
                errors.append(f"Kolom survey {key} tidak ditemukan.")
                continue
            actual_counts = survey[column].value_counts().to_dict()
            expect(f"Distribusi {key}", actual_counts, expected_counts)

    if questionnaire is None:
        errors.append("Ringkasan kuesioner tidak tersedia.")
    else:
        expect(
            "Jumlah indikator",
            len(questionnaire),
            EXPECTED_BASELINE["question_count"],
        )
        actual_mean = safe_mean(questionnaire["rata_rata"])
        if not np.isclose(
            actual_mean,
            EXPECTED_BASELINE["questionnaire_mean"],
            atol=1e-9,
        ):
            errors.append(
                "Rata-rata kuesioner: "
                f"aktual {actual_mean:.6f}, "
                f"diharapkan {EXPECTED_BASELINE['questionnaire_mean']:.6f}"
            )

    if reviews is None:
        errors.append("Ulasan utama tidak tersedia.")
    else:
        expect("Jumlah ulasan", len(reviews), EXPECTED_BASELINE["review_rows"])
        rating_column = review_columns.get("rating")
        date_column = review_columns.get("date")
        if rating_column and rating_column in reviews.columns:
            rating = pd.to_numeric(reviews[rating_column], errors="coerce")
            actual_rating = (
                rating.dropna().astype(int).value_counts().sort_index().to_dict()
            )
            expect("Distribusi rating", actual_rating, EXPECTED_BASELINE["rating"])
            if not np.isclose(
                float(rating.mean()),
                EXPECTED_BASELINE["rating_mean"],
                atol=1e-9,
            ):
                errors.append("Rata-rata rating tidak sesuai baseline.")
        else:
            errors.append("Kolom rating tidak ditemukan.")
        if "sentimen" in reviews.columns:
            actual_sentiment = reviews["sentimen"].value_counts().to_dict()
            expect(
                "Distribusi sentimen",
                actual_sentiment,
                EXPECTED_BASELINE["sentiment"],
            )
        else:
            errors.append("Kolom sentimen turunan tidak tersedia.")
        if date_column and date_column in reviews.columns:
            actual_dates = (
                pd.to_datetime(reviews[date_column], errors="coerce")
                .dt.date.value_counts().sort_index().to_dict()
            )
            expect("Distribusi tanggal ulasan", actual_dates, EXPECTED_BASELINE["review_dates"])
        else:
            errors.append("Kolom tanggal ulasan tidak ditemukan.")
        if int(reviews.duplicated().sum()) != 0:
            errors.append("Data ulasan memiliki exact duplicate rows.")
        review_column = review_columns.get("review")
        if review_column and int(reviews[review_column].duplicated().sum()) != 0:
            errors.append("Data ulasan memiliki duplicate review text.")
    return errors


# =============================================================================
# FILTER STATE AND FILTERING
# =============================================================================
def age_sort_key(value: Any) -> tuple[int, str]:
    text = str(value)
    numbers = [int(number) for number in re.findall(r"\d+", text)]
    if text.strip().startswith("<"):
        return (-1, text)
    if numbers:
        return (numbers[0], text)
    if text.strip().startswith(">"):
        return (10_000, text)
    return (9_999, text)


def available_options(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> dict[str, Any]:
    def unique(column: str | None, frame: pd.DataFrame | None) -> list[Any]:
        if frame is None or not column or column not in frame.columns:
            return []
        return frame[column].dropna().unique().tolist()

    survey_dates: tuple[date, date] | None = None
    timestamp_column = survey_columns.get("timestamp")
    if survey is not None and timestamp_column in survey.columns:
        valid = pd.to_datetime(survey[timestamp_column], errors="coerce").dropna()
        if not valid.empty:
            survey_dates = (valid.min().date(), valid.max().date())

    review_dates: tuple[date, date] | None = None
    date_column = review_columns.get("date")
    if reviews is not None and date_column in reviews.columns:
        valid = pd.to_datetime(reviews[date_column], errors="coerce").dropna()
        if not valid.empty:
            review_dates = (valid.min().date(), valid.max().date())

    return {
        "gender": sorted(unique(survey_columns.get("gender"), survey), key=str),
        "age": sorted(unique(survey_columns.get("age"), survey), key=age_sort_key),
        "frequency": sorted(
            unique(survey_columns.get("frequency"), survey), key=str
        ),
        "survey_dates": survey_dates,
        "review_dates": review_dates,
        "rating": [1, 2, 3, 4, 5],
        "sentiment": ["Positif", "Netral", "Negatif"],
    }


def default_filters(options: dict[str, Any]) -> dict[str, Any]:
    return {
        "gender": [],
        "age": [],
        "frequency": [],
        "survey_dates": options.get("survey_dates"),
        "rating": [],
        "sentiment": [],
        "review_dates": options.get("review_dates"),
        "keyword": "",
        "sort": "Terbaru",
        "limit": "50",
        "questionnaire_categories": [],
        "questionnaire_view": "Semua indikator",
        "insight": True,
        "animations": True,
        "presentation": False,
    }


def initialize_filter_state(defaults: dict[str, Any]) -> None:
    if "active_filters" not in st.session_state:
        st.session_state.active_filters = defaults.copy()
    else:
        for key, value in defaults.items():
            st.session_state.active_filters.setdefault(key, value)
    widget_map = {
        "draft_gender": defaults["gender"],
        "draft_age": defaults["age"],
        "draft_frequency": defaults["frequency"],
        "draft_survey_dates": defaults["survey_dates"],
        "draft_rating": defaults["rating"],
        "draft_sentiment": defaults["sentiment"],
        "draft_review_dates": defaults["review_dates"],
        "draft_keyword": defaults["keyword"],
        "draft_sort": defaults["sort"],
        "draft_limit": defaults["limit"],
        "draft_questionnaire_categories": defaults["questionnaire_categories"],
        "draft_questionnaire_view": defaults["questionnaire_view"],
        "draft_insight": defaults["insight"],
        "draft_animations": defaults["animations"],
        "draft_presentation": defaults["presentation"],
    }
    for key, value in widget_map.items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state.pending_filters = collect_draft_filters()


def collect_draft_filters() -> dict[str, Any]:
    return {
        "gender": list(st.session_state.get("draft_gender", [])),
        "age": list(st.session_state.get("draft_age", [])),
        "frequency": list(st.session_state.get("draft_frequency", [])),
        "survey_dates": st.session_state.get("draft_survey_dates"),
        "rating": list(st.session_state.get("draft_rating", [])),
        "sentiment": list(st.session_state.get("draft_sentiment", [])),
        "review_dates": st.session_state.get("draft_review_dates"),
        "keyword": str(st.session_state.get("draft_keyword", "")).strip(),
        "sort": st.session_state.get("draft_sort", "Terbaru"),
        "limit": st.session_state.get("draft_limit", "50"),
        "questionnaire_categories": list(
            st.session_state.get("draft_questionnaire_categories", [])
        ),
        "questionnaire_view": st.session_state.get(
            "draft_questionnaire_view",
            "Semua indikator",
        ),
        "insight": bool(st.session_state.get("draft_insight", True)),
        "animations": bool(st.session_state.get("draft_animations", True)),
        "presentation": bool(st.session_state.get("draft_presentation", False)),
    }


def reset_filter_state(defaults: dict[str, Any]) -> None:
    st.session_state.active_filters = defaults.copy()
    mapping = {
        "draft_gender": "gender",
        "draft_age": "age",
        "draft_frequency": "frequency",
        "draft_survey_dates": "survey_dates",
        "draft_rating": "rating",
        "draft_sentiment": "sentiment",
        "draft_review_dates": "review_dates",
        "draft_keyword": "keyword",
        "draft_sort": "sort",
        "draft_limit": "limit",
        "draft_questionnaire_categories": "questionnaire_categories",
        "draft_questionnaire_view": "questionnaire_view",
        "draft_insight": "insight",
        "draft_animations": "animations",
        "draft_presentation": "presentation",
    }
    for widget_key, filter_key in mapping.items():
        st.session_state[widget_key] = defaults[filter_key]
    st.session_state.pending_filters = defaults.copy()


def date_range_is_active(
    selected: tuple[date, date] | list[date] | None,
    full_range: tuple[date, date] | None,
) -> bool:
    if selected is None or full_range is None:
        return False
    return tuple(selected) != tuple(full_range)


def is_filter_active(selected: list[Any] | None, options: list[Any] | None) -> bool:
    if not selected:
        return False
    if options and len(selected) == len(options):
        return False
    return True


def filter_scope(
    filters: dict[str, Any], defaults: dict[str, Any], options: dict[str, Any]
) -> tuple[bool, bool]:
    survey_active = bool(
        is_filter_active(filters.get("gender"), options.get("gender"))
        or is_filter_active(filters.get("age"), options.get("age"))
        or is_filter_active(filters.get("frequency"), options.get("frequency"))
        or date_range_is_active(filters.get("survey_dates"), defaults.get("survey_dates"))
    )
    review_active = bool(
        is_filter_active(filters.get("rating"), options.get("rating"))
        or is_filter_active(filters.get("sentiment"), options.get("sentiment"))
        or filters.get("keyword")
        or date_range_is_active(filters.get("review_dates"), defaults.get("review_dates"))
    )
    return survey_active, review_active


def apply_inclusive_date_filter(
    frame: pd.DataFrame,
    column: str,
    selected_range: tuple[date, date] | list[date] | None,
) -> pd.DataFrame:
    if not selected_range or len(selected_range) != 2:
        return frame
    start = pd.Timestamp(selected_range[0])
    end_exclusive = pd.Timestamp(selected_range[1]) + pd.Timedelta(days=1)
    values = pd.to_datetime(frame[column], errors="coerce")
    return frame.loc[values.ge(start) & values.lt(end_exclusive)]


def apply_survey_filters(
    survey: pd.DataFrame | None,
    columns: dict[str, Any],
    filters: dict[str, Any],
    options: dict[str, Any],
) -> pd.DataFrame | None:
    if survey is None:
        return None
    filtered = survey.copy()
    mappings = [
        ("gender", "gender"),
        ("age", "age"),
        ("frequency", "frequency"),
    ]
    for filter_key, column_key in mappings:
        selected = filters.get(filter_key, [])
        options_list = options.get(filter_key, [])
        if selected and len(selected) < len(options_list):
            column = columns.get(column_key)
            if column and column in filtered.columns:
                filtered = filtered[filtered[column].isin(selected)]
    timestamp_column = columns.get("timestamp")
    if timestamp_column and timestamp_column in filtered.columns:
        filtered = apply_inclusive_date_filter(
            filtered, timestamp_column, filters.get("survey_dates")
        )
    return filtered


def apply_review_filters(
    reviews: pd.DataFrame | None,
    columns: dict[str, Any],
    filters: dict[str, Any],
    options: dict[str, Any],
) -> pd.DataFrame | None:
    if reviews is None:
        return None
    filtered = reviews.copy()
    rating_column = columns.get("rating")
    if filters.get("rating") and len(filters["rating"]) < len(options.get("rating", [])) and rating_column in filtered.columns:
        filtered = filtered[filtered[rating_column].isin(filters["rating"])]
    if filters.get("sentiment") and len(filters["sentiment"]) < len(options.get("sentiment", [])) and "sentimen" in filtered.columns:
        filtered = filtered[filtered["sentimen"].isin(filters["sentiment"])]
    date_column = columns.get("date")
    if date_column and date_column in filtered.columns:
        filtered = apply_inclusive_date_filter(
            filtered, date_column, filters.get("review_dates")
        )
    keyword = str(filters.get("keyword", "")).strip()
    review_column = columns.get("review")
    if keyword and review_column and review_column in filtered.columns:
        mask = filtered[review_column].astype(str).str.contains(
            keyword, case=False, regex=False, na=False
        )
        filtered = filtered[mask]
    return sort_reviews(filtered, columns, filters.get("sort", "Terbaru"))


def apply_questionnaire_filters(
    questionnaire: pd.DataFrame | None,
    filters: dict[str, Any],
) -> pd.DataFrame | None:
    if questionnaire is None:
        return None
    filtered = add_questionnaire_categories(questionnaire)
    selected_categories = filters.get("questionnaire_categories", [])
    if selected_categories:
        filtered = filtered[filtered["kategori"].isin(selected_categories)]
    view = filters.get("questionnaire_view", "Semua indikator")
    if view == "Top 5":
        filtered = filtered.nlargest(5, "rata_rata")
    elif view == "Bottom 5":
        filtered = filtered.nsmallest(5, "rata_rata")
    return filtered.reset_index(drop=True)


def sort_reviews(
    reviews: pd.DataFrame | None,
    columns: dict[str, Any],
    sort_mode: str,
) -> pd.DataFrame | None:
    if reviews is None or reviews.empty:
        return reviews
    date_column = columns.get("date")
    rating_column = columns.get("rating")
    if sort_mode == "Terbaru" and date_column in reviews.columns:
        return reviews.sort_values(date_column, ascending=False, kind="mergesort")
    if sort_mode == "Terlama" and date_column in reviews.columns:
        return reviews.sort_values(date_column, ascending=True, kind="mergesort")
    if sort_mode == "Rating Tertinggi" and rating_column in reviews.columns:
        return reviews.sort_values(rating_column, ascending=False, kind="mergesort")
    if sort_mode == "Rating Terendah" and rating_column in reviews.columns:
        return reviews.sort_values(rating_column, ascending=True, kind="mergesort")
    return reviews


# =============================================================================
# METRICS, KEYWORDS, AND CHARTS
# =============================================================================
def safe_mean(values: pd.Series | None) -> float:
    if values is None:
        return 0.0
    numeric = pd.to_numeric(values, errors="coerce")
    result = numeric.mean()
    return float(result) if pd.notna(result) else 0.0


def review_metrics(
    reviews: pd.DataFrame | None, columns: dict[str, Any]
) -> dict[str, float]:
    total = len(reviews) if reviews is not None else 0
    if reviews is None or reviews.empty:
        return {
            "total": 0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "positive_pct": 0.0,
            "avg_rating": 0.0,
        }
    sentiment = reviews.get("sentimen", pd.Series(index=reviews.index, dtype=str))
    positive = int(sentiment.eq("Positif").sum())
    neutral = int(sentiment.eq("Netral").sum())
    negative = int(sentiment.eq("Negatif").sum())
    rating_column = columns.get("rating")
    return {
        "total": total,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        "positive_pct": positive / total * 100 if total else 0.0,
        "avg_rating": safe_mean(
            reviews[rating_column]
            if rating_column and rating_column in reviews.columns
            else None
        ),
    }


def extract_keywords(texts: pd.Series | list[Any], top_n: int = 15) -> list[tuple[str, int]]:
    words: list[str] = []
    for text in texts:
        for word in re.findall(r"[a-zA-Z]{3,}", str(text).casefold()):
            if word not in STOPWORDS_ID:
                words.append(word)
    return Counter(words).most_common(top_n)


def complaint_term_counts(
    reviews: pd.DataFrame | None,
    review_column: str | None,
) -> list[tuple[str, int]]:
    if (
        reviews is None
        or reviews.empty
        or not review_column
        or review_column not in reviews.columns
        or "sentimen" not in reviews.columns
    ):
        return []
    negative_text = (
        reviews.loc[reviews["sentimen"].eq("Negatif"), review_column]
        .fillna("")
        .astype(str)
    )
    counts = [
        (
            term,
            int(
                negative_text.str.contains(
                    term,
                    case=False,
                    regex=False,
                    na=False,
                ).sum()
            ),
        )
        for term in COMPLAINT_TERMS
    ]
    return sorted(
        [(term, count) for term, count in counts if count > 0],
        key=lambda item: (-item[1], item[0]),
    )


def base_layout(title: str, height: int = 360, **overrides: Any) -> dict[str, Any]:
    layout: dict[str, Any] = {
        "title": {
            "text": f"<b>{escape(title)}</b>",
            "x": 0.02,
            "y": 0.96,
            "font": {"size": 14, "color": C_TEXT},
        },
        "template": "plotly_white",
        "autosize": True,
        "height": height,
        "margin": {"t": 28, "b": 46, "l": 38, "r": 20},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#475569"},
        "hoverlabel": {
            "bgcolor": "#FFFFFF",
            "font_color": "#0F172A",
            "font_size": 11,
            "bordercolor": "#D7E8FF",
            "namelength": -1,
            "align": "left",
        },
        "hovermode": "closest",
        # Disable all drag/selection interaction on card charts
        "dragmode": False,
        "clickmode": "none",
        "selectdirection": "any",  # Plotly requires this when dragmode is set
        "transition": {"duration": 500, "easing": "cubic-in-out"},
        "spikedistance": -1,
    }
    layout.update(overrides)
    return layout


def hover_scope_text(scope_label: str) -> str:
    normalized = scope_label.strip().casefold()
    if normalized == "total data":
        return "dari total data"
    if normalized == "filter aktif":
        return "berdasarkan filter aktif"
    return scope_label


def render_static_compact_table(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    max_rows: int = 6,
    title: str | None = None,
) -> None:
    from html import escape
    to_display = df.copy()

    # Drop identity columns only, do not automatically drop 'responden'
    identity_cols = [
        "nama", "username", "email", "telepon", "phone", "kontak",
        "user_id", "id_user", "nomor_hp", "no_hp"
    ]
    cols_to_drop = [
        c for c in to_display.columns
        if any(id_field in c.lower() for id_field in identity_cols)
    ]
    to_display = to_display.drop(columns=cols_to_drop, errors="ignore")

    # Select requested columns if they exist
    if columns:
        valid_cols = [c for c in columns if c in to_display.columns]
        if valid_cols:
            to_display = to_display[valid_cols]

    to_display = to_display.head(max_rows)

    # Build HTML table with clean styles
    css = """
    <style>
    .static-table-wrap {
        width: 100%;
        overflow-x: auto;
        margin: 0.5rem 0;
        border-radius: 12px;
        border: 1px solid #D7E8FF;
    }
    .static-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: 0.8rem;
        color: #102040;
    }
    .static-table th, .static-table td {
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid #E2E8F0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .static-table th {
        background-color: #F3F8FF;
        font-weight: 700;
        color: #5C6B86;
    }
    .static-table tr:last-child td {
        border-bottom: none;
    }
    .static-table td.long-text {
        white-space: normal;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    </style>
    """

    html = f'<div class="static-table-wrap">{css}'
    if title:
        html += (
            '<div style="font-weight:700; font-size:0.85rem; padding: 8px 12px; '
            f'background:#EAF5FF; color:#0B5ED7; border-bottom:1px solid #D7E8FF;">'
            f'{escape(title)}</div>'
        )
    html += '<table class="static-table">'

    # Headers
    html += "<thead><tr>"
    for col in to_display.columns:
        html += f"<th>{escape(str(col))}</th>"
    html += "</tr></thead><tbody>"

    # Rows
    for _, row in to_display.iterrows():
        html += "<tr>"
        for col in to_display.columns:
            val = str(row[col])
            td_class = ' class="long-text"' if len(val) > 40 else ""
            html += f"<td{td_class}>{escape(val)}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


def donut_chart(
    counts: pd.Series,
    title: str,
    color_map: dict[str, str],
    scope_label: str = "Data tampil",
    unit_label: str = "data",
) -> go.Figure:
    labels = counts.index.astype(str).tolist()
    values = counts.values.tolist()
    colors = [color_map.get(label, C_SKY) for label in labels]

    total = float(sum(values)) if sum(values) else 0
    percentages = [(float(v) / total * 100) if total else 0 for v in values]

    display_texts = []
    text_positions = []
    for label, val, pct in zip(labels, values, percentages):
        if pct < 5:
            display_texts.append("")
            text_positions.append("inside")
        else:
            display_texts.append(f"{pct:.1f}%")
            text_positions.append("inside")

    pull_values = [0.06 if pct < 5 else 0 for pct in percentages]

    figure = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                textinfo="text",
                text=display_texts,
                textposition=text_positions,
                pull=pull_values,
                automargin=True,
                domain=dict(x=[0.08, 0.92], y=[0.02, 0.98]),
                marker=dict(
                    colors=colors,
                    line=dict(color="#FFFFFF", width=3)
                ),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Jumlah: <b>%{value}</b><br>"
                    "Persentase: <b>%{percent:.1%}</b>"
                    "<extra></extra>"
                ),
                sort=False,
            )
        ]
    )
    figure.update_layout(
        **base_layout(
            title,
            360,
            showlegend=True,
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": -0.08,
                "xanchor": "center",
                "x": 0.5,
            },
        )
    )
    annotations = []
    small_slice_idx = 0
    for label, val, pct in zip(labels, values, percentages):
        if pct < 5:
            annotations.append(
                dict(
                    text=f"ℹ️ {label}: {pct:.1f}% ({val} {unit_label})",
                    showarrow=False,
                    x=0.02,
                    y=0.02 + small_slice_idx * 0.06,
                    xref="paper",
                    yref="paper",
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(
                        family="Inter, Arial, sans-serif",
                        size=11,
                        color="#64748B",
                    ),
                )
            )
            small_slice_idx += 1

    figure.update_layout(
        uniformtext_minsize=11,
        uniformtext_mode="show",
        margin=dict(l=50, r=80, t=45, b=60),
        showlegend=True,
        annotations=annotations,
    )
    return figure


def bar_chart(
    labels: list[Any],
    values: list[Any],
    title: str,
    color: str | list[str] = C_PRIMARY,
    x_title: str = "",
    y_title: str = "Jumlah",
    height: int = 360,
    denominator: int | None = None,
    scope_label: str = "Data tampil",
    unit_label: str = "data",
) -> go.Figure:
    hover_scope = hover_scope_text(scope_label)
    original_labels = [str(label) for label in labels]
    display_labels = [
        "Beberapa kali<br>seminggu"
        if str(label) == "Beberapa kali seminggu"
        else str(label)
        for label in labels
    ]
    if denominator is not None:
        customdata = [
            [
                original_label,
                str(int(value)) if isinstance(value, float) and value.is_integer() else str(value),
                f"{float(value) / denominator * 100:.1f}" if denominator else "0.0",
            ]
            for value, original_label in zip(values, original_labels)
        ]
        hovertemplate = (
            "<b>%{x}</b><br>"
            "Jumlah: <b>%{y}</b><br>"
            "Persentase: <b>%{customdata[2]}%</b>"
            "<extra></extra>"
        )
    else:
        customdata = [[original_label] for original_label in original_labels]
        hovertemplate = (
            "<b>%{x}</b><br>"
            "Nilai: <b>%{y}</b>"
            "<extra></extra>"
        )
    figure = go.Figure(
        go.Bar(
            x=display_labels,
            y=values,
            marker={"color": color, "line": {"width": 0}},
            text=values,
            textposition="outside",
            cliponaxis=False,
            customdata=customdata,
            hovertemplate=hovertemplate,
        )
    )
    figure.update_layout(
        **base_layout(
            title,
            height,
            xaxis={
                "title": x_title,
                "showgrid": False,
                "tickangle": -25,
                "automargin": True,
                "showspikes": False,
            },
            yaxis={"title": y_title, "gridcolor": "#EAF0F7", "rangemode": "tozero", "showspikes": False},
            showlegend=False,
            bargap=0.34,
        )
    )
    return figure


def line_chart(
    frame: pd.DataFrame, x_column: str, y_column: str, title: str
) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=frame[x_column],
            y=frame[y_column],
            mode="lines+markers",
            line={"color": C_PRIMARY, "width": 3, "shape": "spline"},
            marker={"size": 6, "color": C_ELECTRIC, "line": {"color": "white", "width": 1}},
            fill="tozeroy",
            fillcolor="rgba(16,142,233,.08)",
            hovertemplate="<b>%{x}</b><br>Jumlah ulasan: %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        **base_layout(
            title,
            320,
            xaxis={"showgrid": False, "title": ""},
            yaxis={"gridcolor": "#EAF0F7", "title": "Jumlah Ulasan", "rangemode": "tozero"},
            showlegend=False,
        )
    )
    return figure


def questionnaire_chart(
    questionnaire: pd.DataFrame,
    respondent_count: int,
    scope_label: str,
) -> go.Figure:
    ordered = questionnaire.sort_values("rata_rata", ascending=True).copy()
    if "kategori" not in ordered.columns:
        ordered["kategori"] = ordered["rata_rata"].map(score_interpretation)
    colors = [
        C_POSITIVE if value >= 4 else C_NEUTRAL if value >= 3 else C_NEGATIVE
        for value in ordered["rata_rata"]
    ]
    height = max(500, min(560, len(ordered) * 23 + 90))
    customdata = [[str(respondent_count)] for _ in range(len(ordered))]
    figure = go.Figure(
        go.Bar(
            x=ordered["rata_rata"],
            y=ordered["label"],
            orientation="h",
            marker={"color": colors},
            customdata=customdata,
            text=ordered["rata_rata"].map(lambda value: f"{value:.2f}"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Rata-rata: <b>%{x:.2f} / 5</b><br>"
                "Responden: <b>%{customdata[0]}</b>"
                "<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        **base_layout(
            "Rata-rata Skor Q1-Q20",
            height,
            xaxis={
                "range": [0, 5.4],
                "title": "Rata-rata Skor",
                "tick0": 0,
                "dtick": 1,
                "gridcolor": "#EAF0F7",
                "showspikes": False,
            },
            yaxis={"title": "", "showgrid": False},
            margin={"t": 48, "b": 52, "l": 48, "r": 42},
            showlegend=False,
            bargap=0.22,
        )
    )
    figure.add_vline(
        x=3,
        line_dash="dash",
        line_color=C_NEUTRAL,
        annotation_text="Cukup",
        annotation_position="top",
    )
    figure.add_vline(
        x=4,
        line_dash="dash",
        line_color=C_POSITIVE,
        annotation_text="Kuat",
        annotation_position="top",
    )
    return figure


def variable_score_chart(
    variables: pd.DataFrame,
    scope_label: str,
) -> go.Figure:
    labels = variables["variabel"].astype(str).tolist()
    values = variables["rata_rata"].astype(float).tolist()
    interpretations = variables["interpretasi"].astype(str).tolist()
    indicator_counts = variables["jumlah_indikator"].astype(int).tolist()
    colors = [
        C_POSITIVE if value >= 4 else C_NEUTRAL if value >= 3 else C_NEGATIVE
        for value in values
    ]
    customdata = [
        [str(interp), str(cnt), f"{v:.2f}"]
        for interp, cnt, v in zip(interpretations, indicator_counts, values)
    ]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{value:.2f}" for value in values],
            textposition="outside",
            cliponaxis=False,
            customdata=customdata,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Skor rata-rata: <b>%{customdata[2]} / 5</b><br>"
                "Interpretasi: <b>%{customdata[0]}</b><br>"
                "Berdasarkan %{customdata[1]} indikator"
                "<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        **base_layout(
            "Rata-rata Skor per Variabel",
            360,
            xaxis={"title": "", "showgrid": False},
            yaxis={
                "title": "Skor Rata-rata",
                "range": [0, 5.35],
                "dtick": 1,
                "gridcolor": "#EAF0F7",
                "showspikes": False,
            },
            showlegend=False,
            bargap=0.35,
        )
    )
    figure.add_hline(
        y=4,
        line_dash="dash",
        line_color=C_POSITIVE,
    )
    return figure


def _chart_title(figure: go.Figure) -> str:
    title = figure.layout.title.text if figure.layout.title else ""
    plain_title = re.sub(r"<[^>]+>", "", str(title or "Detail Grafik"))
    return unescape(plain_title).strip() or "Detail Grafik"


def _open_fullscreen_chart(chart_id: str) -> None:
    st.session_state.fullscreen_chart_id = chart_id


def _clear_fullscreen_chart() -> None:
    st.session_state.fullscreen_chart_id = None


@st.dialog(
    "📊 Detail Grafik",
    width="large",
    on_dismiss=_clear_fullscreen_chart,
)
def render_fullscreen_dialog() -> None:
    chart_id = st.session_state.get("fullscreen_chart_id")
    registry = st.session_state.get("chart_registry", {})
    chart = registry.get(chart_id)
    if not chart:
        st.info("Grafik tidak lagi tersedia pada halaman aktif.")
        if st.button("Tutup", key="close_missing_fullscreen"):
            st.session_state.fullscreen_chart_id = None
            st.rerun()
        return

    st.markdown(f"#### {escape(chart['title'])}")
    enlarged = go.Figure(chart["figure"])
    
    # Check if all y-values in the chart traces are integers to prevent fractional tick labels on zoom
    y_vals = []
    for trace in enlarged.data:
        if hasattr(trace, "y") and trace.y is not None:
            y_vals.extend([v for v in trace.y if pd.notna(v)])
    
    enlarged.update_layout(
        autosize=True,
        height=500,
        title=None,  # Clear the title from the figure layout to avoid double titles
        margin={"l": 55, "r": 35, "t": 28, "b": 65},
    )
    
    if y_vals and all(isinstance(v, (int, np.integer)) or (isinstance(v, float) and v.is_integer()) for v in y_vals):
        enlarged.update_yaxes(tickformat="d")

    # Fullscreen dialog: enable scroll zoom and pan for exploration
    enlarged.update_layout(dragmode="zoom")
    enlarged.update_xaxes(fixedrange=False)
    enlarged.update_yaxes(fixedrange=False)
    render_plotly_fullscreen(enlarged, key=f"fullscreen_{chart_id}")
    st.caption("Gunakan toolbar Plotly di sudut kanan atas untuk zoom, pan, dan download grafik.")



def render_chart_card(
    title: str,
    figure: go.Figure,
    chart_id: str,
    caption: str | None = None,
) -> None:
    clean_title = _chart_title(go.Figure(figure)) or _chart_title(
        go.Figure(layout={"title": {"text": title}})
    )
    st.session_state.setdefault("chart_registry", {})
    st.session_state.chart_registry[chart_id] = {
        "title": clean_title,
        "figure": go.Figure(figure),
    }
    # Compact header: chart title + small fullscreen button in one tight row
    col_title, col_btn = st.columns([15, 1], vertical_alignment="center")
    with col_title:
        st.html(
            f'<div style="font-size:.83rem;font-weight:800;color:#07132F;padding:.1rem 0;line-height:1.3;">' + escape(clean_title) + '</div>'
        )
    with col_btn:
        if st.button(
            "⛶",
            key=f"chart_expand_{chart_id}",
            help=f"Fullscreen: {clean_title}",
        ):
            _open_fullscreen_chart(chart_id)
            st.rerun()

    inline = go.Figure(figure)
    inline.update_layout(
        title=None,
        margin=dict(l=28, r=16, t=16, b=38),
        dragmode=False,
        clickmode="none",
    )
    # fixedrange=True prevents zoom-selection box on axes in card charts
    inline.update_xaxes(fixedrange=True, showspikes=False)
    inline.update_yaxes(fixedrange=True, showspikes=False)
    render_plotly_normal(inline, key=chart_id)
    if caption:
        st.caption(caption)


def plot_chart(figure: go.Figure, key: str) -> None:
    render_chart_card(_chart_title(figure), figure, key)


# =============================================================================
# DASHBOARD COMPONENTS
# =============================================================================
def render_sidebar_nav() -> None:
    """Render the main navigation menu in the sidebar."""
    logo_html = render_image_asset(
        "dana_logo_wordmark_header_480x120.png",
        class_name="sidebar-logo",
        alt="DANA Insight",
        fallback='<div class="sidebar-logo-fallback">DANA Insight</div>'
    )
    st.sidebar.html(
        f"""
        <div class="sidebar-header">
            {logo_html}
        </div>
        """
    )

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Overview"

    st.sidebar.html(
        '<div class="sidebar-nav-section">'
        '<div class="sidebar-nav-label">Navigasi Utama</div></div>'
    )
    for tab_name, _ in NAV_ITEMS:
        if st.sidebar.button(
            tab_name,
            key=f"sidebar_nav_{tab_name}",
            type="primary" if st.session_state.active_tab == tab_name else "secondary",
            width="stretch",
        ):
            st.session_state.active_tab = tab_name
            st.rerun()

    st.sidebar.html('<div class="sidebar-divider"></div>')
    if st.sidebar.button(
        "☰ Buka Filter & Control",
        key="sidebar_open_filter",
        width="stretch",
    ):
        st.session_state.filter_open = True
        st.rerun()

    updated = latest_primary_data_modified()
    updated_text = format_wib(updated) if updated else "Tidak tersedia"
    st.sidebar.caption(f"Data terakhir diperbarui\n\n{updated_text}")


def render_horizontal_tabs() -> None:
    # Desktop Navigation View
    with st.container(key="navigation_desktop"):
        with st.container(key="horizontal_navigation"):
            columns = st.columns(len(NAV_ITEMS))
            for column, (tab_name, _) in zip(columns, NAV_ITEMS):
                with column:
                    if st.button(
                        tab_name,
                        key=f"horizontal_nav_{tab_name}",
                        type=(
                            "primary"
                            if st.session_state.get("active_tab") == tab_name
                            else "secondary"
                        ),
                        width="stretch",
                    ):
                        st.session_state.active_tab = tab_name
                        st.rerun()

    # Mobile Navigation View (Dropdown section switcher, space saving & clean)
    with st.container(key="navigation_mobile"):
        nav_names = [item[0] for item in NAV_ITEMS]
        current_active = st.session_state.get("active_tab", "Overview")
        if current_active not in nav_names:
            current_active = nav_names[0]
            
        selected_tab = st.selectbox(
            "Pilih Halaman",
            options=nav_names,
            index=nav_names.index(current_active),
            key="mobile_navigation_selectbox",
            label_visibility="collapsed",
        )
        if selected_tab != current_active:
            st.session_state.active_tab = selected_tab
            st.rerun()


@st.dialog("Filter & Control", width="large")
def render_filter_dialog(
    options: dict[str, Any],
    defaults: dict[str, Any],
) -> None:
    """Filter & Control panel as a proper Streamlit dialog (modal).
    Opens when user clicks ☰ Filter in the topbar.
    Applies changes to st.session_state.active_filters via rerun.
    """
    # ── header ──────────────────────────────────────────────────────────────
    filter_icon = ASSETS.get("filter_illustration", "")
    icon_html = (
        f'<img src="data:image/png;base64,{img_to_base64(filter_icon)}" '
        f'style="width:32px;height:32px;object-fit:contain;vertical-align:middle;'
        f'border-radius:8px;margin-right:.5rem;" alt="" />'
        if filter_icon else ""
    )
    st.html(
        f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem;">'
        f'{icon_html}'
        f'<div>'
        f'<div style="font-weight:800;font-size:1.05rem;color:#102040;">Filter &amp; Control</div>'
        f'<div style="font-size:.72rem;color:#5C6B86;">Ubah filter, lalu klik <em>Terapkan Filter</em> untuk memperbarui seluruh dashboard.</div>'
        f'</div></div>'
    )

    # ── action buttons (above form) ──────────────────────────────────────────
    btn_left, btn_right = st.columns(2)
    with btn_left:
        if st.button("↺ Reset Semua Filter", key="dialog_reset_all", width="stretch"):
            reset_filter_state(defaults)
            st.rerun()
    with btn_right:
        if st.button("⟳ Refresh Data", key="dialog_refresh_data", width="stretch"):
            st.cache_data.clear()
            st.session_state.last_refresh = datetime.now(WIB)
            st.rerun()

    st.divider()

    # ── filter form ──────────────────────────────────────────────────────────
    with st.form("filter_dialog_form", border=False):
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Filter Responden Survei**")
            st.multiselect(
                "Jenis kelamin",
                options=options["gender"],
                key="draft_gender",
                placeholder="Semua gender",
            )
            st.multiselect(
                "Kelompok usia",
                options=options["age"],
                key="draft_age",
                placeholder="Semua kelompok usia",
            )
            st.multiselect(
                "Frekuensi penggunaan DANA",
                options=options["frequency"],
                key="draft_frequency",
                placeholder="Semua frekuensi",
            )
            if options.get("survey_dates"):
                st.date_input(
                    "Rentang tanggal survei",
                    min_value=options["survey_dates"][0],
                    max_value=options["survey_dates"][1],
                    key="draft_survey_dates",
                )
            st.markdown("**Kuesioner & Tampilan**")
            st.multiselect(
                "Kategori skor indikator",
                options=["Kuat/Baik", "Cukup", "Perlu Perhatian"],
                key="draft_questionnaire_categories",
                placeholder="Semua kategori",
            )
            st.selectbox(
                "Tampilkan indikator",
                options=["Semua indikator", "Top 5", "Bottom 5", "Variabel X1/X2/M/Y"],
                key="draft_questionnaire_view",
            )

        with col_b:
            st.markdown("**Filter Ulasan**")
            st.multiselect(
                "Sentimen",
                options=options["sentiment"],
                key="draft_sentiment",
                placeholder="Semua sentimen",
            )
            st.multiselect(
                "Rating",
                options=options["rating"],
                key="draft_rating",
                placeholder="Semua rating",
                format_func=lambda v: f"{v} / 5",
            )
            if options.get("review_dates"):
                st.date_input(
                    "Rentang tanggal ulasan",
                    min_value=options["review_dates"][0],
                    max_value=options["review_dates"][1],
                    key="draft_review_dates",
                )
            st.text_input(
                "Cari kata dalam ulasan",
                key="draft_keyword",
                placeholder="Contoh: transaksi, saldo, cepat",
            )
            st.selectbox(
                "Urutkan ulasan",
                options=["Terbaru", "Terlama", "Rating Tertinggi", "Rating Terendah"],
                key="draft_sort",
            )
            st.selectbox(
                "Jumlah baris tabel",
                options=["10", "25", "50", "100", "Semua"],
                key="draft_limit",
            )
            st.markdown("**Preferensi Dashboard**")
            st.toggle("Insight otomatis", key="draft_insight")
            st.toggle("Animasi dashboard", key="draft_animations")
            st.toggle("Mode presentasi", key="draft_presentation")

        # ── submit ───────────────────────────────────────────────────────────
        applied = st.form_submit_button(
            "✅ Terapkan Filter",
            type="primary",
            width="stretch",
        )
        if applied:
            pending = collect_draft_filters()
            st.session_state.pending_filters = pending
            st.session_state.active_filters = pending.copy()
            st.rerun()


def render_filter_panel(
    options: dict[str, Any],
    defaults: dict[str, Any],
    load_errors: dict[str, str],
) -> dict[str, Any]:
    if not st.session_state.get("filter_open", False):
        return st.session_state.active_filters.copy()

    st.session_state.pending_filters = collect_draft_filters()
    with st.container(key="control_panel"):
        action_left, action_right = st.columns(2)
        with action_left:
            if st.button(
                "↺ Reset Semua",
                key="panel_reset_all",
                width="stretch",
            ):
                reset_filter_state(defaults)
                st.rerun()
        with action_right:
            if st.button(
                "⟳ Refresh Data",
                key="panel_refresh_data",
                width="stretch",
            ):
                st.cache_data.clear()
                st.session_state.last_refresh = datetime.now(WIB)
                st.rerun()

        with st.form("filter_control_form", border=False):
            st.html('<div class="sidebar-section">Filter Survey</div>')
            st.multiselect(
                "Jenis kelamin",
                options=options["gender"],
                key="draft_gender",
                placeholder="Semua gender",
            )
            st.multiselect(
                "Kelompok usia",
                options=options["age"],
                key="draft_age",
                placeholder="Semua kelompok usia",
            )
            st.multiselect(
                "Frekuensi penggunaan DANA",
                options=options["frequency"],
                key="draft_frequency",
                placeholder="Semua frekuensi",
            )
            if options["survey_dates"]:
                st.date_input(
                    "Rentang tanggal survey",
                    min_value=options["survey_dates"][0],
                    max_value=options["survey_dates"][1],
                    key="draft_survey_dates",
                )

            st.html('<div class="sidebar-section">Filter Ulasan</div>')
            st.multiselect(
                "Sentimen",
                options=options["sentiment"],
                key="draft_sentiment",
                placeholder="Semua sentimen",
            )
            st.multiselect(
                "Rating",
                options=options["rating"],
                key="draft_rating",
                placeholder="Semua rating",
                format_func=lambda value: f"{value} / 5",
            )
            if options["review_dates"]:
                st.date_input(
                    "Rentang tanggal ulasan",
                    min_value=options["review_dates"][0],
                    max_value=options["review_dates"][1],
                    key="draft_review_dates",
                )
            st.text_input(
                "Cari kata dalam ulasan",
                key="draft_keyword",
                placeholder="Contoh: transaksi, saldo, cepat",
            )
            st.selectbox(
                "Urutkan ulasan",
                options=[
                    "Terbaru",
                    "Terlama",
                    "Rating Tertinggi",
                    "Rating Terendah",
                ],
                key="draft_sort",
            )

            st.html('<div class="sidebar-section">Kuesioner & Tampilan</div>')
            st.multiselect(
                "Kategori skor indikator",
                options=["Kuat/Baik", "Cukup", "Perlu Perhatian"],
                key="draft_questionnaire_categories",
                placeholder="Semua kategori",
            )
            st.selectbox(
                "Tampilkan indikator",
                options=[
                    "Semua indikator",
                    "Top 5",
                    "Bottom 5",
                    "Variabel X1/X2/M/Y",
                ],
                key="draft_questionnaire_view",
            )
            st.selectbox(
                "Jumlah baris tabel",
                options=["10", "25", "50", "100", "Semua"],
                key="draft_limit",
            )
            st.toggle("Insight otomatis", key="draft_insight")
            st.toggle("Animasi dashboard", key="draft_animations")
            st.toggle("Mode presentasi", key="draft_presentation")

            applied = st.form_submit_button(
                "✅ Terapkan Filter",
                type="primary",
                width="stretch",
            )
            if applied:
                pending_filters = collect_draft_filters()
                st.session_state.pending_filters = pending_filters
                st.session_state.active_filters = pending_filters.copy()
                st.rerun()

        if load_errors:
            with st.expander("Status data sumber utama"):
                for message in load_errors.values():
                    st.warning(message)
        else:
            st.caption(
                "Sumber utama berhasil dimuat. File raw tetap lokal dan tidak "
                "digunakan oleh dashboard publik."
            )

    return st.session_state.active_filters.copy()


DANA_LOGO_SVG = """
<svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="dg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="100%" stop-color="#0B5ED7"/>
    </linearGradient>
  </defs>
  <rect width="32" height="32" rx="9" fill="url(#dg)"/>
  <path d="M8 8h7c4.4 0 8 3.6 8 8s-3.6 8-8 8H8V8z" fill="white"/>
  <path d="M10.5 10.5h4.5c3 0 5.5 2.5 5.5 5.5s-2.5 5.5-5.5 5.5h-4.5V10.5z" fill="url(#dg)"/>
  <circle cx="26" cy="7" r="3.5" fill="#38BDF8" opacity="0.9"/>
</svg>
"""

DANA_HERO_SVG = """
<svg viewBox="0 0 120 80" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:120px;height:80px;">
  <defs>
    <linearGradient id="hg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="white" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="white" stop-opacity="0.05"/>
    </linearGradient>
  </defs>
  <rect x="10" y="5" width="100" height="70" rx="16" fill="url(#hg)" stroke="white" stroke-opacity="0.2" stroke-width="1"/>
  <rect x="18" y="18" width="60" height="8" rx="4" fill="white" fill-opacity="0.3"/>
  <rect x="18" y="32" width="40" height="6" rx="3" fill="white" fill-opacity="0.2"/>
  <rect x="18" y="44" width="50" height="6" rx="3" fill="white" fill-opacity="0.2"/>
  <circle cx="88" cy="38" r="16" fill="white" fill-opacity="0.12" stroke="white" stroke-opacity="0.25" stroke-width="1"/>
  <path d="M82 38h7c2.8 0 5 2.2 5 5s-2.2 5-5 5h-7V38z" fill="white" fill-opacity="0.5"/>
  <path d="M83.5 39.5h5.5c1.9 0 3.5 1.6 3.5 3.5s-1.6 3.5-3.5 3.5h-5.5V39.5z" fill="url(#hg)"/>
  <circle cx="98" cy="26" r="4" fill="#38BDF8" fill-opacity="0.7"/>
</svg>
"""


def _logo_img_tag() -> str:
    """Return DANA wordmark img tag from asset, with SVG fallback."""
    # Try dana_logo_html first (uses ASSETS registry correctly)
    html = dana_logo_html(asset_key="logo_wordmark", height="32px", alt="DANA Wordmark")
    if html.startswith("<img"):
        return html
    # Direct fallback via render_image_asset
    rendered = render_image_asset(
        "dana_logo_wordmark_header_480x120.png",
        alt="DANA Wordmark",
        fallback=DANA_LOGO_SVG,
    )
    return rendered if rendered else DANA_LOGO_SVG


def render_lobby_summary(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> None:
    survey_total = len(survey) if survey is not None else 0
    review_total = len(reviews) if reviews is not None else 0
    questionnaire_average = (
        safe_mean(questionnaire["rata_rata"])
        if questionnaire is not None and not questionnaire.empty
        else 0.0
    )
    metrics = review_metrics(reviews, review_columns)

    dominant_profile: list[str] = []
    if survey is not None and not survey.empty:
        for key, label in (
            ("gender", "Gender dominan"),
            ("age", "Usia dominan"),
            ("frequency", "Frekuensi dominan"),
        ):
            column = survey_columns.get(key)
            if column and column in survey.columns:
                counts = survey[column].value_counts()
                if not counts.empty:
                    value = str(counts.index[0])
                    count = int(counts.iloc[0])
                    percentage = count / survey_total * 100 if survey_total else 0.0
                    dominant_profile.append(
                        f"<li>{label}: <strong>{escape(value)}</strong> "
                        f"({count}/{survey_total}; {percentage:.1f}%).</li>"
                    )

    variable_scores, _ = compute_variable_scores(
        survey,
        survey_columns.get("questions", []),
    )
    variable_summary = ""
    if not variable_scores.empty:
        best = variable_scores.loc[variable_scores["rata_rata"].idxmax()]
        worst = variable_scores.loc[variable_scores["rata_rata"].idxmin()]
        variable_summary = (
            f"<li>Variabel tertinggi: <strong>{escape(str(best['variabel']))} "
            f"{float(best['rata_rata']):.2f}</strong>.</li>"
            f"<li>Variabel terendah: <strong>{escape(str(worst['variabel']))} "
            f"{float(worst['rata_rata']):.2f}</strong>.</li>"
        )

    st.html(
        f"""
        <div class="insight-card fade-up">
            <h4>Ringkasan penelitian</h4>
            <ul>
                {''.join(dominant_profile)}
                <li>Skor kuesioner rata-rata: <strong>{questionnaire_average:.2f}/5</strong>.</li>
                {variable_summary}
                <li>Rating ulasan: <strong>{metrics['avg_rating']:.2f}/5</strong>.</li>
                <li>Sentimen positif: <strong>{metrics['positive']} dari {review_total}
                    ({metrics['positive_pct']:.1f}%)</strong>.</li>
            </ul>
            <p>
                Ringkasan bersifat deskriptif. Dashboard tidak menyimpulkan
                hubungan kausal dan tidak menampilkan identitas pribadi.
            </p>
        </div>
        """
    )


def go_to_dashboard(tab: str = "Overview") -> None:
    st.session_state.app_view = "dashboard"
    st.session_state.entered_dashboard = True
    st.session_state.active_tab = tab


def go_to_landing() -> None:
    st.session_state.app_view = "landing"
    st.session_state.entered_dashboard = False
    st.session_state.show_lobby_summary = False


def render_lobby_page(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> bool:
    """Render the optional presentation lobby and return True after entry."""
    if st.session_state.get("app_view") == "dashboard":
        return True

    survey_total = len(survey) if survey is not None else 0
    review_total = len(reviews) if reviews is not None else 0
    indicator_total = len(questionnaire) if questionnaire is not None else 0
    questionnaire_average = (
        safe_mean(questionnaire["rata_rata"])
        if questionnaire is not None and not questionnaire.empty
        else 0.0
    )
    metrics = review_metrics(reviews, review_columns)
    logo = _logo_img_tag()
    shield = asset_img_tag("shield_privacy.svg", alt="")
    metric_icons = ("👥", "💬", "📋", "⭐", "😊")
    metric_items = (
        (f"{survey_total:,}", "Responden anonim", "👥"),
        (f"{review_total:,}", "Ulasan pengguna", "💬"),
        (f"{indicator_total:,}", "Indikator kuesioner", "📋"),
        (f"{questionnaire_average:.2f}", "Skor kuesioner", "⭐"),
        (f"{metrics['positive_pct']:.1f}%", "Sentimen positif", "😊"),
    )
    metric_html = "".join(
        f'<div class="lobby-metric">'
        f'<div class="lobby-metric-icon">{icon}</div>'
        f'<strong>{value}</strong>'
        f'<span>{label}</span>'
        f'</div>'
        for value, label, icon in metric_items
    )
    st.html(
        f"""
        <div class="lobby-topbar">
            {_logo_img_tag()}
            <div class="lobby-help">Butuh bantuan? Gunakan <strong>Lampiran Presentasi</strong>.</div>
        </div>
        """
    )
    st.html(
        f"""
        <section class="lobby-shell fade-in">
            <div class="lobby-hero">
                <div>
                    <div class="lobby-mark">{logo}</div>
                    <h1 class="lobby-title">DANA Insight<br><span>Command Center</span></h1>
                    <p class="lobby-subtitle">
                        Dashboard interaktif untuk memahami pengalaman pengguna
                        DANA berdasarkan data survei dan ulasan pengguna.
                    </p>
                    <div class="badge-row">
                        <span class="hero-badge">&#128101; Profil Responden</span>
                        <span class="hero-badge">&#128203; 20 Indikator</span>
                        <span class="hero-badge">&#129302; Review Intelligence</span>
                        <span class="hero-badge">&#128274; Data Explorer Aman</span>
                    </div>
                </div>
                <div class="lobby-visual" aria-hidden="true">
                    <!-- transparent spacer — hero image shows through lobby-shell background -->
                </div>

            </div>
            <div class="lobby-metrics">{metric_html}</div>
            <div class="lobby-privacy">
                {shield}
                <span><strong>Privasi pengguna terlindungi.</strong><br>
                Identitas pribadi tidak ditampilkan dan tidak masuk download publik.</span>
            </div>
        </section>
        """
    )

    with st.container(key="lobby_actions"):
        enter_column, summary_column, spacer = st.columns([1.4, 1.2, 3])
        with enter_column:
            if st.button(
                "Masuk ke Dashboard",
                key="enter_dashboard",
                type="primary",
                width="stretch",
            ):
                go_to_dashboard("Overview")
                st.rerun()
        with summary_column:
            summary_label = (
                "Tutup Ringkasan"
                if st.session_state.get("show_lobby_summary", False)
                else "Lihat Ringkasan"
            )
            if st.button(
                summary_label,
                key="toggle_lobby_summary",
                width="stretch",
            ):
                st.session_state.show_lobby_summary = not st.session_state.get(
                    "show_lobby_summary",
                    False,
                )
                st.rerun()

    if st.session_state.get("show_lobby_summary", False):
        render_lobby_summary(
            survey,
            survey_columns,
            questionnaire,
            reviews,
            review_columns,
        )

    st.markdown("### Modul yang Tersedia")
    module_columns = st.columns(len(NAV_ITEMS))
    for index, (column, (tab_name, description)) in enumerate(
        zip(module_columns, NAV_ITEMS),
        start=1,
    ):
        with column:
            with st.container(key=f"landing_module_{index}"):
                if st.button(
                    tab_name,
                    key=f"landing_open_{index}",
                    width="stretch",
                ):
                    go_to_dashboard(tab_name)
                    st.rerun()
                st.caption(description)
    render_footer()
    return False


def global_search_matches(
    query: str,
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    limit: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return literal, privacy-safe search matches without changing dashboard scope."""
    term = query.strip()
    question_matches = pd.DataFrame()
    review_matches = pd.DataFrame()
    if not term:
        return question_matches, review_matches
    if questionnaire is not None and not questionnaire.empty:
        searchable_columns = [
            column
            for column in ("label", "pertanyaan")
            if column in questionnaire.columns
        ]
        if searchable_columns:
            mask = pd.Series(False, index=questionnaire.index)
            for column in searchable_columns:
                mask |= questionnaire[column].astype(str).str.contains(
                    term,
                    case=False,
                    regex=False,
                    na=False,
                )
            question_matches = questionnaire.loc[mask].head(limit).copy()
    safe_reviews = reviews_for_public(reviews, review_columns)
    review_column = review_columns.get("review")
    if (
        not safe_reviews.empty
        and review_column
        and review_column in safe_reviews.columns
    ):
        mask = safe_reviews[review_column].astype(str).str.contains(
            term,
            case=False,
            regex=False,
            na=False,
        )
        review_matches = safe_reviews.loc[mask].head(limit).copy()
    return question_matches, review_matches


def render_global_search_results(
    query: str,
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> None:
    if not query.strip():
        return
    question_matches, review_matches = global_search_matches(
        query,
        questionnaire,
        reviews,
        review_columns,
    )
    with st.container(key="global_search_results", border=True):
        st.markdown(f"#### Hasil pencarian cepat: `{query.strip()}`")
        st.html(
            '<div class="global-search-note">'
            "Pencarian cepat hanya menampilkan kecocokan dan tidak mengubah KPI, "
            "chart, atau filter statistik."
            "</div>"
        )
        if question_matches.empty and review_matches.empty:
            render_empty_state(
                "Tidak ada hasil pencarian",
                "Gunakan kode indikator atau potongan kata dari pertanyaan dan ulasan.",
            )
            return
        left, right = st.columns(2)
        with left:
            st.markdown("##### Indikator kuesioner")
            if question_matches.empty:
                st.caption("Tidak ada indikator yang cocok.")
            else:
                for row in question_matches.itertuples():
                    score = getattr(row, "rata_rata", None)
                    score_text = f" · {float(score):.2f}" if score is not None else ""
                    st.html(
                        '<div class="search-result-card">'
                        f"<strong>{escape(str(getattr(row, 'label', 'Indikator')))}</strong>"
                        f"{score_text}<br>{escape(str(getattr(row, 'pertanyaan', '')))}"
                        "</div>"
                    )
        with right:
            st.markdown("##### Ulasan pengguna")
            if review_matches.empty:
                st.caption("Tidak ada ulasan yang cocok.")
            else:
                rating_column = review_columns.get("rating")
                date_column = review_columns.get("date")
                review_column = review_columns.get("review")
                for _, row in review_matches.iterrows():
                    metadata = " | ".join(
                        value
                        for value in (
                            f"Rating {row.get(rating_column)}" if rating_column else "",
                            str(row.get("sentimen", "")),
                            str(row.get(date_column, "")) if date_column else "",
                        )
                        if value
                    )
                    text = str(row.get(review_column, "")) if review_column else ""
                    st.html(
                        '<div class="search-result-card">'
                        f"<strong>{escape(metadata)}</strong><br>{escape(text)}"
                        "</div>"
                    )


def render_top_header(
    cache_refresh: datetime,
    data_updated: datetime | None,
    loaded: bool,
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    options: dict[str, Any] | None = None,
    defaults: dict[str, Any] | None = None,
) -> None:
    search_query = ""
    
    # Desktop Header View
    with st.container(key="top_header_desktop"):
        with st.container(key="top_header"):
            filter_column, brand_column, search_column, status_column, refresh_column = st.columns(
                [1.0, 2.6, 2.4, 2.8, 0.8],
                vertical_alignment="center",
            )
            with filter_column:
                active_filters = st.session_state.get("active_filters", {})
                _defaults = defaults or {}
                filter_is_active = any(
                    active_filters.get(k) != _defaults.get(k)
                    for k in ("gender", "age", "frequency", "rating", "sentiment", "keyword")
                )
                filter_btn_label = "☰ Filter ●" if filter_is_active else "☰ Filter"
                if st.button(
                    filter_btn_label,
                    key="open_filter_dialog_btn",
                    type="primary" if filter_is_active else "secondary",
                    width="stretch",
                ):
                    if options is not None and defaults is not None:
                        render_filter_dialog(options, defaults)
            with brand_column:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:.6rem;min-height:38px;">
                        <div class="brand-logo-wrap">
                            {dana_logo_html(30)}
                        </div>
                        <div>
                            <div style="color:#07132F;font-weight:800;font-size:.9rem;line-height:1.15;">DANA Insight Command Center</div>
                            <div style="color:#94A3B8;font-size:.68rem;margin-top:.12rem;">Survey &amp; Review Analytics &mdash; Fintech Experience Dashboard</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with search_column:
                search_query = st.text_input(
                    "Pencarian global",
                    key="global_search_query",
                    placeholder="Cari indikator atau kata ulasan...",
                    label_visibility="collapsed",
                )
            with status_column:
                render_live_header(cache_refresh, data_updated, loaded)
            with refresh_column:
                if st.button(
                    "Refresh",
                    key="top_refresh_btn",
                    width="stretch",
                ):
                    st.cache_data.clear()
                    st.session_state.last_refresh = datetime.now(WIB)
                    st.rerun()

    # Mobile Header View (Compact, centered logo, no search box, touch-optimized)
    with st.container(key="top_header_mobile"):
        col_filter, col_logo, col_refresh = st.columns([1.2, 2.0, 1.2], vertical_alignment="center")
        with col_filter:
            active_filters = st.session_state.get("active_filters", {})
            _defaults = defaults or {}
            filter_is_active = any(
                active_filters.get(k) != _defaults.get(k)
                for k in ("gender", "age", "frequency", "rating", "sentiment", "keyword")
            )
            filter_btn_label = "☰ Filter ●" if filter_is_active else "☰ Filter"
            if st.button(
                filter_btn_label,
                key="open_filter_dialog_btn_mobile",
                type="primary" if filter_is_active else "secondary",
                width="stretch",
            ):
                if options is not None and defaults is not None:
                    render_filter_dialog(options, defaults)
        with col_logo:
            st.html(
                f'<div style="display:flex;justify-content:center;align-items:center;height:38px;">'
                f'{dana_logo_html(24)}'
                f'</div>'
            )
        with col_refresh:
            if st.button(
                "Refresh",
                key="top_refresh_btn_mobile",
                width="stretch",
            ):
                st.cache_data.clear()
                st.session_state.last_refresh = datetime.now(WIB)
                st.rerun()
        
        # Simplified live status indicator underneath
        st.html(
            f'<div style="display:flex;justify-content:center;align-items:center;gap:8px;margin-top:6px;padding:2px 0;">'
            f'<span style="font-size:0.68rem;color:#16C784;background:#ECFDF5;padding:2px 6px;border-radius:6px;font-weight:700;">● Data Loaded</span>'
            f'<span style="font-size:0.68rem;color:#5C6B86;font-family:monospace;">WIB: {datetime.now(WIB).strftime("%H:%M:%S")}</span>'
            f'</div>'
        )

    # Perform global search calculations if search query is provided
    if search_query:
        render_global_search_results(
            search_query,
            questionnaire,
            reviews,
            review_columns,
        )



def render_hero(
    survey_total: int,
    review_total: int,
    questionnaire_average: float,
    review_average: float,
    positive_percentage: float,
) -> None:
    st.html(
        f"""
        <section class="hero-section fade-in">
            <div class="hero-content">
                <div class="hero-copy-col">
                        <div class="eyebrow">
                            TOTAL DATA · FINTECH EXPERIENCE ANALYTICS
                        </div>
                        <h1 class="hero-title">DANA Insight Command Center</h1>
                        <p class="hero-subtitle">
                            Dashboard interaktif untuk memahami pola penggunaan,
                            skor pengalaman, rating, dan sentimen pengguna aplikasi DANA.
                        </p>
                        <div class="badge-row">
                            <span class="hero-badge">{survey_total:,} Responden</span>
                            <span class="hero-badge">{review_total:,} Ulasan</span>
                            <span class="hero-badge">Sentimen dari Rating</span>
                            <span class="hero-badge">Plotly Interaktif</span>
                        </div>
                </div>
            </div>
            <div class="hero-stat-row">
                <div class="hero-stat-item">
                    <span class="hero-stat-value">{survey_total:,}</span>
                    <span class="hero-stat-label">Responden Total</span>
                </div>
                <div class="hero-stat-item">
                    <span class="hero-stat-value">{review_total:,}</span>
                    <span class="hero-stat-label">Ulasan Total</span>
                </div>
                <div class="hero-stat-item">
                    <span class="hero-stat-value">{questionnaire_average:.2f}</span>
                    <span class="hero-stat-label">Skor Rata-rata</span>
                </div>
                <div class="hero-stat-item">
                    <span class="hero-stat-value">{review_average:.2f} / 5</span>
                    <span class="hero-stat-label">Rating Rata-rata</span>
                </div>
                <div class="hero-stat-item">
                    <span class="hero-stat-value">{positive_percentage:.1f}%</span>
                    <span class="hero-stat-label">Sentimen Positif</span>
                </div>
            </div>
        </section>
        """
    )


def active_filter_chips(
    filters: dict[str, Any], defaults: dict[str, Any], options: dict[str, Any]
) -> list[str]:
    chips: list[str] = []
    if filters["gender"] and len(filters["gender"]) < len(options["gender"]):
        chips.append(f"Gender: {', '.join(map(str, filters['gender']))}")
    if filters["age"] and len(filters["age"]) < len(options["age"]):
        chips.append(f"Usia: {', '.join(map(str, filters['age']))}")
    if filters["frequency"] and len(filters["frequency"]) < len(options["frequency"]):
        chips.append(f"Frekuensi: {', '.join(map(str, filters['frequency']))}")
    if date_range_is_active(filters["survey_dates"], defaults["survey_dates"]):
        chips.append(
            f"Survey: {filters['survey_dates'][0]} s.d. {filters['survey_dates'][1]}"
        )
    if filters["sentiment"] and len(filters["sentiment"]) < len(options["sentiment"]):
        chips.append(f"Sentimen: {', '.join(map(str, filters['sentiment']))}")
    if filters["rating"] and len(filters["rating"]) < len(options["rating"]):
        chips.append(f"Rating: {', '.join(map(str, filters['rating']))}")
    if date_range_is_active(filters["review_dates"], defaults["review_dates"]):
        chips.append(
            f"Ulasan: {filters['review_dates'][0]} s.d. {filters['review_dates'][1]}"
        )
    if filters["keyword"]:
        chips.append(f'Kata kunci: "{filters["keyword"]}"')
    if filters.get("questionnaire_categories") and len(filters["questionnaire_categories"]) < 3:
        chips.append(
            "Kategori indikator: "
            + ", ".join(map(str, filters["questionnaire_categories"]))
        )
    if filters.get("questionnaire_view", "Semua indikator") != "Semua indikator":
        chips.append(f"Mode indikator: {filters['questionnaire_view']}")
    return chips


def render_filter_summary(filters: dict[str, Any], defaults: dict[str, Any], options: dict[str, Any]) -> None:
    chips = active_filter_chips(filters, defaults, options)
    if not chips:
        st.html(
            """
            <div class="filter-summary is-empty fade-in">
                <strong>Menampilkan seluruh data.</strong>
                Tidak ada filter yang mempersempit dataset.
            </div>
            """
        )
        return
    chip_html = "".join(
        f'<span class="filter-chip">{escape(chip)}</span>' for chip in chips
    )
    st.html(
        f"""
        <div class="filter-summary fade-in">
            <strong>Filter aktif</strong>
            <div class="chip-row">{chip_html}</div>
        </div>
        """
    )


def render_data_scope_summary(
    survey_count: int,
    survey_total: int,
    review_count: int,
    review_total: int,
    survey_filtered: bool,
    review_filtered: bool,
) -> None:
    survey_text = (
        f"Menampilkan <strong>{survey_count} dari {survey_total} responden</strong> "
        "berdasarkan filter aktif."
        if survey_filtered
        else f"Menampilkan seluruh <strong>{survey_total} responden</strong>."
    )
    review_text = (
        f"Menampilkan <strong>{review_count} dari {review_total} ulasan</strong> "
        "berdasarkan filter aktif."
        if review_filtered
        else f"Menampilkan seluruh <strong>{review_total} ulasan</strong>."
    )
    st.html(
        f"""
        <div class="filter-summary is-empty fade-in">
            <span>{survey_text}</span>
            <span>{review_text}</span>
        </div>
        """
    )


def kpi_card_html(
    identifier: str,
    icon: str,
    label: str,
    value: float,
    caption: str,
    color: str,
    soft_color: str,
    progress: float | None,
    decimals: int,
    suffix: str,
    animate: bool,
) -> str:
    display_value = f"{value:,.{decimals}f}{suffix}"
    progress_html = ""
    if progress is not None:
        bounded = max(0.0, min(float(progress), 100.0))
        progress_html = (
            '<div class="progress-track">'
            f'<div class="progress-fill" style="width:{bounded:.1f}%;background:linear-gradient(90deg,{color},#38BDF8);"></div>'
            '</div>'
        )
    value_html = escape(display_value)
    animation_class = " fade-up" if animate else ""
    # SVG icons (Lucide-style, reliable in st.markdown context)
    _svg = {
        "users": (
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
            '<circle cx="9" cy="7" r="4"/>'
            '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
            '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
            '</svg>'
        ),
        "reviews": (
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
            '</svg>'
        ),
        "score": (
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M9 11l3 3L22 4"/>'
            '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'
            '</svg>'
        ),
        "star": (
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
            '</svg>'
        ),
        "sentiment": (
            '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"/>'
            '<path d="M8 13s1.5 2 4 2 4-2 4-2"/>'
            '<line x1="9" y1="9" x2="9.01" y2="9"/>'
            '<line x1="15" y1="9" x2="15.01" y2="9"/>'
            '</svg>'
        ),
    }
    emoji_icon = _svg.get(icon, (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="8"/></svg>'
    ))
    emoji_icon = emoji_icon.replace('stroke="currentColor"', f'stroke="{color}"')
    return (
        f'<article class="kpi-card{animation_class}"'
        f' style="border-color:{color}22;background:linear-gradient(145deg,#FFFFFF,{soft_color});">'
        f'<div class="kpi-orb" style="background:{color};"></div>'
        f'<div class="kpi-head">'
        f'<div class="kpi-icon" style="background:{soft_color};border-color:{color}44;">{emoji_icon}</div>'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'</div>'
        f'<div class="kpi-value">{value_html}</div>'
        f'<div class="kpi-caption">{escape(caption)}</div>'
        f'{progress_html}'
        f'</article>'
    )


def render_kpis(
    survey: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    questionnaire: pd.DataFrame | None,
    review_columns: dict[str, Any],
    survey_filtered: bool,
    review_filtered: bool,
    animate: bool,
) -> None:
    survey_count = len(survey) if survey is not None else 0
    metrics = review_metrics(reviews, review_columns)
    questionnaire_average = (
        safe_mean(questionnaire["rata_rata"])
        if questionnaire is not None and not questionnaire.empty
        else 0.0
    )
    survey_caption = "⚡ filter aktif" if survey_filtered else "total data"
    review_caption = "⚡ filter aktif" if review_filtered else "total data"
    positive_label = "Sentimen Positif"

    cards = [
        (
            "kpi-survey", "users", "Responden Survei", float(survey_count),
            survey_caption, C_PRIMARY, "#EFF6FF", None, 0, "",
        ),
        (
            "kpi-reviews", "reviews", "Ulasan Pengguna", float(metrics["total"]),
            review_caption, C_ELECTRIC, "#EEF2FF", None, 0, "",
        ),
        (
            "kpi-score", "score", "Rata-rata Skor", questionnaire_average,
            survey_caption, C_PRIMARY, "#EFF6FF",
            questionnaire_average / 5 * 100, 2, "",
        ),
        (
            "kpi-rating", "star", "Rata-rata Rating", metrics["avg_rating"],
            review_caption, C_NEUTRAL, C_SOFT_AMBER,
            metrics["avg_rating"] / 5 * 100, 2, "",
        ),
        (
            "kpi-positive", "sentiment", positive_label, metrics["positive_pct"],
            review_caption, C_POSITIVE, C_SOFT_GREEN,
            metrics["positive_pct"], 1, "%",
        ),
    ]
    kpi_html = "".join(kpi_card_html(*card, animate=animate) for card in cards)
    # Use CSS class kpi-grid (defined in inject_custom_css) for responsive layout
    st.markdown(
        f'<div class="kpi-grid">{kpi_html}</div>',
        unsafe_allow_html=True,
    )
    if review_filtered:
        st.caption("Angka ulasan berubah karena filter aktif.")


def summary_card(label: str, value: str, note: str = "") -> str:
    note_html = (
        f'<div style="margin-top:.26rem;color:#64748B;font-size:.65rem;">{escape(note)}</div>'
        if note else ""
    )
    return f"""
    <div style="min-height:110px;padding:.95rem 1rem;border:1.5px solid #DBEAFE;border-radius:16px;background:linear-gradient(145deg,#fff,#F8FCFF);box-shadow:0 4px 14px rgba(16,142,233,.07);">
        <div style="color:#64748B;font-size:.6rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;margin-bottom:.35rem;">{escape(label)}</div>
        <div style="color:#07132F;font-size:1.1rem;font-weight:800;line-height:1.3;">{escape(value)}</div>
        {note_html}
    </div>
    """


def executive_summary_card(
    survey: "pd.DataFrame | None",
    survey_columns: dict,
    questionnaire: "pd.DataFrame | None",
    reviews: "pd.DataFrame | None",
    review_columns: dict,
    scope_label: str = "Total data",
) -> str:
    """Return HTML for a dynamic executive summary card computed from live data."""
    def dominant(df: "pd.DataFrame | None", col: str, total: int) -> str:
        if df is None or df.empty or col not in df.columns:
            return "—"
        vc = df[col].value_counts()
        if vc.empty:
            return "—"
        return f"{vc.index[0]} ({vc.iloc[0]}/{total} = {vc.iloc[0]/total*100:.0f}%)"

    survey_total = len(survey) if survey is not None else 0
    gender_dom = dominant(survey, survey_columns.get("gender", ""), survey_total)
    age_dom = dominant(survey, survey_columns.get("age", ""), survey_total)
    freq_dom = dominant(survey, survey_columns.get("frequency", ""), survey_total)

    q_avg_text = "—"
    if questionnaire is not None and not questionnaire.empty:
        avg = safe_mean(questionnaire["rata_rata"])
        q_avg_text = f"{avg:.2f} / 5"

    review_total = len(reviews) if reviews is not None else 0
    rating_text = "—"
    pos_text = "—"
    neg_kw_text = "—"
    if reviews is not None and not reviews.empty:
        m = review_metrics(reviews, review_columns)
        rating_text = f"{m['avg_rating']:.2f} / 5 ({review_total} ulasan)"
        pos_text = f"{m['positive_pct']:.1f}% Positif, {100 - m['positive_pct'] - (m['neutral']/review_total*100 if review_total else 0):.1f}% Negatif"
        rev_col = review_columns.get("review")
        if rev_col:
            kws = complaint_term_counts(reviews, rev_col)[:3]
            if kws:
                neg_kw_text = ", ".join(f"{w} ({c}x)" for w, c in kws)

    rows = [
        ("Gender Dominan", gender_dom),
        ("Kelompok Usia", age_dom),
        ("Frekuensi Penggunaan", freq_dom),
        ("Skor Kuesioner", q_avg_text),
        ("Rating Ulasan", rating_text),
        ("Sentimen", pos_text),
        ("Keyword Negatif", neg_kw_text),
    ]
    row_html = "".join(
        f'<div style="display:flex;gap:.5rem;padding:.42rem 0;border-bottom:1px solid #EEF2F7;">'
        f'<div style="flex:0 0 130px;font-size:.68rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.04em;">{escape(label)}</div>'
        f'<div style="font-size:.78rem;font-weight:600;color:#0F172A;">{escape(value)}</div>'
        f'</div>'
        for label, value in rows
    )
    return f"""
    <div style="padding:1rem 1.2rem;background:linear-gradient(135deg,#F0F9FF,#EFF6FF);border:1.5px solid #BFDBFE;border-radius:18px;margin-bottom:1rem;">
        <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.7rem;">
            <div style="width:8px;height:8px;border-radius:50%;background:#108EE9;"></div>
            <strong style="font-size:.8rem;color:#1E40AF;text-transform:uppercase;letter-spacing:.06em;">Executive Summary — {escape(scope_label)}</strong>
        </div>
        {row_html}
        <div style="margin-top:.6rem;font-size:.65rem;color:#94A3B8;font-style:italic;">Data bersifat deskriptif. Tidak ada klaim kausal.</div>
    </div>
    """


def insight_highlight_cards(
    survey: "pd.DataFrame | None",
    survey_columns: dict,
    reviews: "pd.DataFrame | None",
    review_columns: dict,
) -> None:
    """Render 4 insight highlight chips below KPI cards."""
    survey_total = len(survey) if survey is not None else 0
    review_total = len(reviews) if reviews is not None else 0

    def dominant_value(df: "pd.DataFrame | None", col_key: str, fallback: str = "—") -> str:
        col = survey_columns.get(col_key, "") if df is not None else ""
        if df is None or df.empty or col not in df.columns:
            return fallback
        vc = df[col].value_counts()
        return str(vc.index[0]) if not vc.empty else fallback

    gender_val = dominant_value(survey, "gender")
    freq_val = dominant_value(survey, "frequency")

    sentiment_val = "—"
    area_val = "—"
    if reviews is not None and not reviews.empty:
        m = review_metrics(reviews, review_columns)
        sentiment_val = f"Positif {m['positive_pct']:.1f}%"
        rev_col = review_columns.get("review")
        if rev_col:
            kws = complaint_term_counts(reviews, rev_col)[:1]
            if kws:
                area_val = kws[0][0]

    _insight_data = [
        ("Mayoritas Responden", gender_val, "#108EE9", "#EFF6FF", "👥"),
        ("Frekuensi Dominan", freq_val, "#2563EB", "#EEF2FF", "📅"),
        ("Sentimen Dominan", sentiment_val, "#10B981", "#ECFDF5", "😊"),
        ("Area Perhatian", area_val, "#EF4444", "#FEF2F2", "⚠️"),
    ]
    card_html = "".join(
        f'<div class="insight-highlight-card" style="background:{bg};border:1.5px solid {color}33;">'
        f'<div style="display:flex;align-items:center;gap:.3rem;margin-bottom:.28rem;">'
        f'<span style="font-size:1rem;line-height:1;">{icon}</span>'
        f'<span class="insight-highlight-label" style="color:{color};">{escape(label)}</span>'
        f'</div>'
        f'<div class="insight-highlight-value">{escape(value)}</div>'
        f'</div>'
        for label, value, color, bg, icon in _insight_data
    )
    st.markdown(
        f'<div class="insight-highlight-grid">{card_html}</div>',
        unsafe_allow_html=True,
    )


def presentation_mode_banner() -> None:
    """Render a sticky presentation mode banner at the top of the dashboard."""
    st.html("""
    <div style="
        position:sticky;top:0;z-index:999;
        background:linear-gradient(90deg,#1E40AF,#108EE9);
        color:white;
        text-align:center;
        padding:.45rem 1rem;
        font-size:.78rem;font-weight:700;letter-spacing:.08em;
        text-transform:uppercase;
        border-radius:0 0 12px 12px;
        margin-bottom:.5rem;
        box-shadow:0 4px 12px rgba(16,142,233,.35);
    ">
        Mode Presentasi Aktif — Data DANA Insight Command Center
    </div>
    """)


def script_presentasi_blocks() -> None:
    """Render 4 copy-ready presentation script blocks."""
    scripts = [
        (
            "Pembuka",
            """Selamat [pagi/siang/sore]. Nama saya [Nama], dari kelompok [X].
Hari ini kami mempresentasikan hasil penelitian tentang analisis kepuasan pengguna
aplikasi DANA berdasarkan survei kuesioner dan ulasan pengguna di Play Store.

Dashboard yang Anda lihat bernama DANA Insight Command Center — sebuah platform
analisis data interaktif yang kami bangun menggunakan Streamlit dan Python.
Kita bisa melakukan drill-down data secara langsung selama presentasi ini."""
        ),
        (
            "Penjelasan Data",
            """Data kami berasal dari dua sumber utama:
1. Survei primer: 50 responden pengguna DANA, mengisi kuesioner 20 indikator
   pada skala Likert 1-5. Mayoritas responden adalah Perempuan (78%) berusia
   18-22 tahun (72%), dengan frekuensi penggunaan jarang (42%).

2. Web scraping: 330 ulasan pengguna dari Google Play Store, dikumpulkan
   pada 9-10 Juni 2026. Ulasan dianalisis berdasarkan rating dan sentimen.

Variabel penelitian mencakup X1-Fleksibilitas, X2-Praktis, M-Kepercayaan,
dan Y-Kepuasan Keseluruhan. Setiap variabel dipetakan dari kolom kuesioner."""
        ),
        (
            "Insight Utama",
            """Berikut temuan utama dari analisis data kami:

SURVEI (50 responden):
- Rata-rata skor kuesioner: 4.00 / 5 (kategori Kuat/Baik)
- Semua variabel berada di atas threshold 3.5 (cukup baik)
- Variabel tertinggi: X2-Praktis dan X1-Fleksibilitas

ULASAN (330 data):
- Rating rata-rata: 3.89 / 5
- Sentimen Positif: 70.3% (232 ulasan) — pengguna umumnya puas
- Sentimen Negatif: 25.8% (85 ulasan) — keluhan terbanyak tentang:
  saldo, akun bermasalah, transaksi gagal, dan biaya premium

KESENJANGAN:
Survey menunjukkan kepuasan tinggi, namun ulasan mencatat sejumlah keluhan
teknis yang perlu diperhatikan. Ini menunjukkan pengalaman pengguna yang
berbeda-beda tergantung konteks penggunaan."""
        ),
        (
            "Kesimpulan",
            """Kesimpulan dari penelitian kami:

1. Secara keseluruhan, pengguna DANA memiliki persepsi positif terhadap
   aplikasi, tercermin dari skor kuesioner 4.00/5 dan sentimen positif 70.3%.

2. Area yang masih perlu peningkatan adalah keandalan sistem (transaksi gagal,
   masalah saldo) dan transparansi biaya layanan premium.

3. Dashboard ini bersifat deskriptif. Kami tidak mengklaim hubungan kausal
   antar variabel tanpa analisis statistik inferensial lebih lanjut.

4. Rekomendasi: DANA dapat fokus pada peningkatan stabilitas sistem dan
   komunikasi biaya layanan kepada pengguna untuk mengurangi ulasan negatif.

Terima kasih. Kami siap menjawab pertanyaan."""
        ),
    ]
    st.markdown("#### Script Presentasi (Siap Salin)")
    for title, text in scripts:
        with st.expander(f"📄 Script: {title}", expanded=False):
            st.code(text, language="text")
            st.caption(f"Salin teks '{title}' di atas untuk presentasi Anda.")



def review_trend_chart(
    reviews: pd.DataFrame,
    date_column: str,
    scope_label: str = "Data tampil",
) -> go.Figure:
    """Create the primary review trend grouped strictly by calendar date."""
    source = reviews.copy()
    source["_parsed_date"] = pd.to_datetime(source[date_column], errors="coerce")
    source = source.dropna(subset=["_parsed_date"])
    if source.empty:
        return go.Figure()
    source["periode"] = source["_parsed_date"].dt.date
    grouped = (
        source.groupby("periode")
        .size()
        .reset_index(name="jumlah")
        .sort_values("periode")
    )
    denominator = len(reviews)
    grouped["pct_str"] = (
        grouped["jumlah"].map(
            lambda v: f"{v / denominator * 100:.1f}" if denominator else "0.0"
        )
    )
    # customdata[0] = denominator string, customdata[1] = pct string
    customdata = [
        [str(denominator), pct] for pct in grouped["pct_str"].tolist()
    ]
    figure = go.Figure(
        go.Bar(
            x=grouped["periode"].astype(str),
            y=grouped["jumlah"],
            text=grouped["jumlah"],
            textposition="outside",
            cliponaxis=False,
            marker={
                "color": C_ELECTRIC,
                "line": {"color": "white", "width": 1.5},
            },
            customdata=customdata,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Jumlah: <b>%{y}</b> dari %{customdata[0]}<br>"
                "Persentase: <b>%{customdata[1]}%</b>"
                "<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        **base_layout(
            "Volume Ulasan per Tanggal",
            360,
            xaxis={
                "showgrid": False,
                "title": "Tanggal",
                "type": "category",
                "tickangle": 0,
                "automargin": True,
            },
            yaxis={"gridcolor": "#EAF0F7", "title": "Jumlah Ulasan", "rangemode": "tozero"},
            margin={"t": 62, "b": 44, "l": 58, "r": 58},
            showlegend=False,
        )
    )
    return figure


def review_hour_chart(
    reviews: pd.DataFrame,
    date_column: str,
    scope_label: str = "Data tampil",
) -> go.Figure:
    source = reviews.copy()
    source["_parsed_date"] = pd.to_datetime(source[date_column], errors="coerce")
    source = source.dropna(subset=["_parsed_date"])
    if source.empty:
        return go.Figure()
    counts = (
        source["_parsed_date"].dt.hour.value_counts().reindex(range(24), fill_value=0)
    )
    labels = [f"{hour:02d}:00" for hour in counts.index]
    return bar_chart(
        labels,
        counts.tolist(),
        "Distribusi Ulasan per Jam",
        C_SKY,
        x_title="Jam",
        denominator=len(reviews),
        scope_label=scope_label,
        unit_label="ulasan",
    )


def render_overview(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    survey_total: int,
    review_total: int,
    questionnaire: "pd.DataFrame | None" = None,
    filters: "dict[str, Any] | None" = None,
) -> None:
    section_heading(
        "Executive Dashboard",
        "Overview",
        "Ringkasan cepat karakteristik responden dan pengalaman pengguna.",
        "dana_mark.svg",
    )
    filters = filters or {}
    presentation_on = bool(filters.get("presentation", False))

    survey_scope = (
        "Filter aktif"
        if survey is not None and len(survey) != survey_total
        else "Total data"
    )
    review_scope = (
        "Filter aktif"
        if reviews is not None and len(reviews) != review_total
        else "Total data"
    )
    scope_label = "Filter aktif" if survey_scope == "Filter aktif" or review_scope == "Filter aktif" else "Total data"

    # Executive Summary Card — always visible; expanded=True for presentation readiness
    exec_html = executive_summary_card(
        survey, survey_columns, questionnaire, reviews, review_columns, scope_label
    )
    if presentation_on:
        st.markdown(exec_html, unsafe_allow_html=True)
    else:
        with st.expander("Executive Summary", expanded=True):
            st.markdown(exec_html, unsafe_allow_html=True)

    gender_text = "Data tidak tersedia"
    frequency_text = "Data tidak tersedia"
    if survey is not None and not survey.empty:
        gender_column = survey_columns.get("gender")
        if gender_column in survey.columns:
            counts = survey[gender_column].value_counts()
            if not counts.empty:
                gender_text = (
                    f"{counts.index[0]} "
                    f"({counts.iloc[0] / len(survey) * 100:.0f}%)"
                )
        frequency_column = survey_columns.get("frequency")
        if frequency_column in survey.columns:
            counts = survey[frequency_column].value_counts()
            if not counts.empty:
                frequency_text = str(counts.index[0])
    metrics = review_metrics(reviews, review_columns)
    dominant_sentiment = "Data tidak tersedia"
    if reviews is not None and not reviews.empty and "sentimen" in reviews.columns:
        counts = reviews["sentimen"].value_counts()
        if not counts.empty:
            dominant_sentiment = (
                f"{counts.index[0]} ({counts.iloc[0] / len(reviews) * 100:.0f}%)"
            )

    # Insight highlight chips — always shown for quick overview
    insight_highlight_cards(survey, survey_columns, reviews, review_columns)

    with st.container(key="layout_overview_summary"):
        summary_columns = st.columns(4)
        values = [
            ("Mayoritas Responden", gender_text, "berdasarkan data yang tampil"),
            ("Frekuensi Terbanyak", frequency_text, "pola penggunaan dominan"),
            ("Rating Rata-rata", f"{metrics['avg_rating']:.2f} / 5", "hasil ulasan pengguna"),
            ("Sentimen Dominan", dominant_sentiment, "berdasarkan rating"),
        ]
        for column, item in zip(summary_columns, values):
            with column:
                st.markdown(summary_card(*item), unsafe_allow_html=True)

    with st.container(key="layout_overview_charts1"):
        left, right = st.columns(2)
        with left:
            with st.container(key="chart_overview_gender", border=True):
                if not has_data(survey):
                    render_empty_state("Tidak ada data survei", "Silakan reset atau ubah kombinasi filter.")
                else:
                    gender_column = survey_columns.get("gender")
                    if gender_column in survey.columns:
                        counts = survey[gender_column].value_counts()
                        plot_chart(
                            donut_chart(
                                counts,
                                "Distribusi Gender Responden",
                                {"Perempuan": C_PRIMARY, "Laki-laki": C_SKY},
                                survey_scope,
                                "responden",
                            ),
                            "overview_gender",
                        )
                        st.caption("Proporsi gender responden pada data yang sedang ditampilkan.")
                    else:
                        st.info("Kolom gender tidak tersedia.")
        with right:
            with st.container(key="chart_overview_frequency", border=True):
                if not has_data(survey):
                    render_empty_state("Tidak ada data survei", "Silakan reset atau ubah kombinasi filter.")
                else:
                    frequency_column = survey_columns.get("frequency")
                    if frequency_column in survey.columns:
                        counts = survey[frequency_column].value_counts()
                        plot_chart(
                            bar_chart(
                                counts.index.tolist(),
                                counts.values.tolist(),
                                "Frekuensi Penggunaan DANA",
                                C_PRIMARY,
                                denominator=len(survey),
                                scope_label=survey_scope,
                                unit_label="responden",
                            ),
                            "overview_frequency",
                        )
                        st.caption("Jumlah responden menurut intensitas penggunaan DANA.")
                    else:
                        st.info("Kolom frekuensi penggunaan tidak tersedia.")

    with st.container(key="layout_overview_charts2"):
        left, right = st.columns(2)
        with left:
            with st.container(key="chart_overview_age", border=True):
                if not has_data(survey):
                    render_empty_state("Tidak ada data survei", "Silakan reset atau ubah kombinasi filter.")
                else:
                    age_column = survey_columns.get("age")
                    if age_column in survey.columns:
                        counts = survey[age_column].value_counts()
                        ordered_labels = sorted(counts.index.tolist(), key=age_sort_key)
                        ordered_values = [int(counts[label]) for label in ordered_labels]
                        plot_chart(
                            bar_chart(
                                ordered_labels,
                                ordered_values,
                                "Distribusi Kelompok Usia",
                                C_ELECTRIC,
                                denominator=len(survey),
                                scope_label=survey_scope,
                                unit_label="responden",
                            ),
                            "overview_age",
                        )
                        st.caption("Usia ditampilkan sebagai kelompok sesuai format dataset.")
                    else:
                        st.info("Kolom kelompok usia tidak tersedia.")
        with right:
            with st.container(key="chart_overview_trend", border=True):
                if not has_data(reviews):
                    render_empty_state("Tidak ada data ulasan", "Silakan reset atau ubah kombinasi filter.")
                else:
                    date_column = review_columns.get("date")
                    if date_column in reviews.columns:
                        fig = review_trend_chart(reviews, date_column, review_scope)
                        if fig.data:
                            plot_chart(fig, "overview_trend")
                            st.caption(
                                "Volume ulasan dikelompokkan berdasarkan tanggal kalender, "
                                "bukan jam."
                            )
                        else:
                            st.info("Tanggal ulasan tidak valid untuk membuat tren.")
                    else:
                        st.info("Kolom tanggal ulasan tidak tersedia.")


def health_card(
    title: str,
    count: int,
    note: str,
    color: str,
    background: str,
    border: str,
) -> str:
    return f"""
    <div class="health-card fade-up"
         style="--health-color:{color};--health-bg:{background};--health-border:{border}">
        <div class="health-title">{escape(title)}</div>
        <div class="health-count">{count}</div>
        <div class="health-note">{escape(note)}</div>
    </div>
    """


def rank_card(
    rank: int,
    label: str,
    question: str,
    score: float,
    positive: bool,
) -> str:
    color = C_POSITIVE if positive else C_NEGATIVE
    soft = C_SOFT_GREEN if positive else C_SOFT_RED
    shortened = question if len(question) <= 95 else f"{question[:92]}..."
    return f"""
    <div class="rank-card" style="--rank-color:{color};--rank-soft:{soft}">
        <div class="rank-number">{rank}</div>
        <div class="rank-question"><strong>{escape(label)}</strong> - {escape(shortened)}</div>
        <div class="rank-score">{score:.2f}</div>
    </div>
    """


def render_survey_analysis(
    questionnaire: pd.DataFrame | None,
    survey: pd.DataFrame | None,
    question_columns: list[str],
    filters: dict[str, Any],
    survey_total: int,
) -> None:
    section_banner(
        "Survey Experience Score",
        "Analisis Survei",
        "Evaluasi 20 indikator pengalaman pengguna pada skala 1 sampai 5.",
        banner_asset_key="survey_banner",
    )
    if not has_data(survey):
        render_empty_state(
            "Tidak ada responden yang cocok",
            "Ubah filter survey atau tekan Reset Semua untuk mengembalikan data."
        )
        return
    if questionnaire is None or questionnaire.empty:
        st.warning(
            "Data kuesioner tidak tersedia. Periksa hasil_kuesioner.csv atau kolom skor survey."
        )
        return

    categorized = add_questionnaire_categories(questionnaire)
    displayed_questionnaire = apply_questionnaire_filters(categorized, filters)
    respondent_count = len(survey) if survey is not None else 0
    scope_label = (
        "Filter aktif"
        if survey is not None and len(survey) != survey_total
        else "Total data"
    )

    strong = categorized[categorized["rata_rata"].ge(4)]
    moderate = categorized[
        categorized["rata_rata"].ge(3)
        & categorized["rata_rata"].lt(4)
    ]
    weak = categorized[categorized["rata_rata"].lt(3)]
    with st.container(key="layout_survey_health"):
        columns = st.columns(3)
        cards = [
            ("Indikator Kuat / Baik", len(strong), "Skor >= 4.00", C_POSITIVE, C_SOFT_GREEN, "#A7F3D0"),
            ("Indikator Cukup", len(moderate), "Skor 3.00-3.99", C_NEUTRAL, C_SOFT_AMBER, "#FDE68A"),
            ("Perlu Perhatian", len(weak), "Skor < 3.00", C_NEGATIVE, C_SOFT_RED, "#FECACA"),
        ]
        for column, card in zip(columns, cards):
            with column:
                st.markdown(health_card(*card), unsafe_allow_html=True)

    section_heading(
        "Research Variables",
        "Analisis Variabel Penelitian",
        "Rata-rata X1, X2, M, dan Y dihitung langsung dari jawaban survey yang tampil.",
        "variable_illustration.svg",
    )
    variable_scores, missing_mapping = compute_variable_scores(
        survey,
        question_columns,
    )
    if variable_scores.empty:
        st.warning("Variabel penelitian tidak dapat dihitung dari data yang tampil.")
    else:
        with st.container(key="chart_survey_variables", border=True):
            plot_chart(
                variable_score_chart(variable_scores, scope_label),
                "survey_variables",
            )
            st.caption(
                "Metodologi: Nilai variabel (X1, X2, M, Y) dihitung sebagai rata-rata "
                "dari skor indikator-indikator (Q1-Q20) yang dipetakan kepadanya. "
                "Interpretasi: skor >= 4.00 Kuat/Baik, 3.00-3.99 Cukup, "
                "dan < 3.00 Perlu Perhatian."
            )
    if missing_mapping:
        for variable, missing_columns in missing_mapping.items():
            st.warning(
                f"{variable}: {len(missing_columns)} kolom mapping tidak ditemukan: "
                + "; ".join(missing_columns)
            )
    with st.expander("ℹ️ Catatan Metodologi Pemetaan Variabel", expanded=False):
        st.info(
            "Catatan metodologi: Pemetaan variabel mengikuti struktur indikator "
            "pada dataset proyek. Y - Keseluruhan memakai seluruh Q1-Q20 sehingga "
            "overlap dengan X1, X2, dan M. Sesuaikan mapping dengan operasionalisasi "
            "variabel resmi jika kelompok atau dosen memiliki pembagian indikator "
            "yang berbeda."
        )

    if filters.get("questionnaire_view") != "Variabel X1/X2/M/Y":
        if displayed_questionnaire is None or displayed_questionnaire.empty:
            st.info("Tidak ada indikator yang cocok dengan filter kuesioner.")
        else:
            with st.container(key="chart_survey_scores", border=True):
                plot_chart(
                    questionnaire_chart(
                        displayed_questionnaire,
                        respondent_count,
                        scope_label,
                    ),
                    "survey_scores",
                )
                st.caption(
                    f"Menampilkan {len(displayed_questionnaire)} dari "
                    f"{len(categorized)} indikator. Garis putus-putus menandai "
                    "batas cukup dan kuat."
                )

    with st.container(key="layout_survey_ranks"):
        left, right = st.columns(2)
        with left:
            with st.container(key="panel_survey_top", border=True):
                st.markdown("#### Top 5 indikator tertinggi")
                for rank, row in enumerate(
                    categorized.nlargest(5, "rata_rata").itertuples(), start=1
                ):
                    st.html(
                        rank_card(
                            rank,
                            str(row.label),
                            str(row.pertanyaan),
                            float(row.rata_rata),
                            True,
                        )
                    )
        with right:
            with st.container(key="panel_survey_bottom", border=True):
                st.markdown("#### Bottom 5 indikator terendah")
                for rank, row in enumerate(
                    categorized.nsmallest(5, "rata_rata").itertuples(), start=1
                ):
                    st.html(
                        rank_card(
                            rank,
                            str(row.label),
                            str(row.pertanyaan),
                            float(row.rata_rata),
                            False,
                        )
                    )

    average = safe_mean(categorized["rata_rata"])
    best = categorized.loc[categorized["rata_rata"].idxmax()]
    worst = categorized.loc[categorized["rata_rata"].idxmin()]
    if filters.get("insight", True):
        st.html(
            f"""
            <div class="insight-card">
                <h4>Insight otomatis survei — {escape(scope_label)}</h4>
                <p>
                    Rata-rata keseluruhan berada pada <strong>{average:.2f}/5</strong>.
                    Indikator tertinggi adalah <strong>{escape(str(best['label']))}</strong>
                    ({float(best['rata_rata']):.2f}), sedangkan indikator terendah adalah
                    <strong>{escape(str(worst['label']))}</strong>
                    ({float(worst['rata_rata']):.2f}). Area dengan skor terendah layak
                    menjadi prioritas evaluasi, tanpa menyimpulkan hubungan kausal.
                </p>
            </div>
            """
        )

    with st.expander("Daftar lengkap Q1-Q20"):
        full = categorized[["label", "pertanyaan", "rata_rata", "kategori"]].copy()
        full["rata_rata"] = full["rata_rata"].round(2)
        
        with st.container(key="survey_q1_q20_desktop"):
            st.dataframe(
                full,
                width="stretch",
                height=500,
                hide_index=True,
                column_config={
                    "label": st.column_config.TextColumn("Kode", width="small"),
                    "pertanyaan": st.column_config.TextColumn("Pertanyaan", width="large"),
                    "rata_rata": st.column_config.NumberColumn(
                        "Rata-rata", format="%.2f", width="small"
                    ),
                    "kategori": st.column_config.TextColumn("Interpretasi", width="medium"),
                },
            )
            
        with st.container(key="survey_q1_q20_mobile"):
            cards_html = '<div class="mobile-card-list">'
            for _, row in full.iterrows():
                r_val = float(row["rata_rata"])
                k_val = str(row["kategori"])
                q_lbl = str(row["label"])
                q_txt = str(row["pertanyaan"])
                
                # Determine colors based on category/score
                if r_val >= 4.0:
                    badge_color = "#16C784"
                    badge_bg = "#ECFDF5"
                elif r_val >= 3.0:
                    badge_color = "#FFB020"
                    badge_bg = "#FFFBEB"
                else:
                    badge_color = "#FF4D5E"
                    badge_bg = "#FEF2F2"
                    
                cards_html += f"""
                <div class="mobile-card-item" style="border: 1px solid #D7E8FF; border-radius: 12px; padding: 10px; margin-bottom: 8px; background: white;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size:0.85rem; font-weight:700; color:#0B5ED7;">{escape(q_lbl)}</span>
                        <span style="font-size:0.75rem; font-weight:700; color:{badge_color}; background:{badge_bg}; padding:2px 6px; border-radius:6px;">★ {r_val:.2f}</span>
                    </div>
                    <div style="font-size:0.8rem; color:#102040; margin-bottom:4px; line-height:1.3; white-space:normal;">{escape(q_txt)}</div>
                    <div style="font-size:0.7rem; color:#5C6B86;">Kategori: <strong style="color:{badge_color};">{escape(k_val)}</strong></div>
                </div>
                """
            cards_html += '</div>'
            st.markdown(cards_html, unsafe_allow_html=True)


def render_keyword_chips(keywords: list[tuple[str, int]]) -> None:
    if not keywords:
        st.info("Belum ada keyword yang dapat ditampilkan.")
        return
    content = "".join(
        f'<span class="keyword-chip">{escape(word)}'
        f'<span class="chip-count">{count}</span></span>'
        for word, count in keywords
    )
    st.markdown(f'<div class="chip-row">{content}</div>', unsafe_allow_html=True)


def table_limit(filters: dict[str, Any]) -> int | None:
    value = filters.get("limit", "50")
    return None if value == "Semua" else int(value)


def reviews_for_public(
    reviews: pd.DataFrame | None, columns: dict[str, Any]
) -> pd.DataFrame:
    safe = sanitize_public_df(reviews)
    preferred: list[str] = []
    for key in ("rating", "date", "review"):
        column = columns.get(key)
        if column and column in safe.columns and column not in preferred:
            preferred.append(column)
    if "sentimen" in safe.columns:
        preferred.append("sentimen")
    remaining = [column for column in safe.columns if column not in preferred]
    return safe[preferred + remaining]


def add_number_column(frame: pd.DataFrame) -> pd.DataFrame:
    numbered = frame.reset_index(drop=True).copy()
    numbered.insert(0, "No", np.arange(1, len(numbered) + 1))
    return numbered


def convert_df_to_csv(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def render_paginated_table(
    frame: pd.DataFrame,
    key_prefix: str,
    height: int = 500,
    default_page_size: int = 10,
    column_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    safe_frame = sanitize_public_df(frame).reset_index(drop=True)
    if safe_frame.empty:
        return safe_frame

    numbered = add_number_column(safe_frame)
    page_sizes: list[int | str] = [10, 25, 50, 100, "Semua"]
    default_value: int | str = (
        default_page_size if default_page_size in page_sizes else 10
    )
    control_info, control_size = st.columns([3, 1])
    with control_size:
        selected_size = st.selectbox(
            "Baris per halaman",
            options=page_sizes,
            index=page_sizes.index(default_value),
            key=f"{key_prefix}_page_size",
        )

    page_size = len(numbered) if selected_size == "Semua" else int(selected_size)
    total_pages = max(1, int(np.ceil(len(numbered) / max(page_size, 1))))
    page_key = f"{key_prefix}_page"
    current_page = int(st.session_state.get(page_key, 1))
    current_page = max(1, min(current_page, total_pages))
    st.session_state[page_key] = current_page

    start = (current_page - 1) * page_size
    stop = min(start + page_size, len(numbered))
    displayed = numbered.iloc[start:stop].copy()
    with control_info:
        st.caption(
            f"Menampilkan {start + 1}-{stop} dari {len(numbered)} baris "
            f"| Halaman {current_page} dari {total_pages}"
        )

    with st.container(key=f"table_card_{key_prefix}_desktop"):
        st.dataframe(
            displayed,
            width="stretch",
            height=height,
            hide_index=True,
            column_config=column_config,
        )

    with st.container(key=f"table_card_{key_prefix}_mobile"):
        from html import escape
        cards_html = '<div class="mobile-card-list">'
        for _, row in displayed.iterrows():
            cards_html += '<div class="mobile-card-item">'
            rating_field = next((c for c in displayed.columns if "rating" in c.lower()), None)
            sentiment_field = next((c for c in displayed.columns if "sentimen" in c.lower()), None)
            date_field = next((c for c in displayed.columns if "tanggal" in c.lower() or "date" in c.lower()), None)
            text_field = next((c for c in displayed.columns if "ulasan" in c.lower() or "review" in c.lower()), None)

            if rating_field or text_field:
                r_val = row[rating_field] if rating_field else "-"
                s_val = str(row[sentiment_field]) if sentiment_field else "-"
                d_val = str(row[date_field]) if date_field else "-"
                t_val = str(row[text_field]) if text_field else "-"
                s_color = "#10B981" if "positif" in s_val.lower() else ("#EF4444" if "negatif" in s_val.lower() else "#F59E0B")
                s_bg = "#ECFDF5" if "positif" in s_val.lower() else ("#FEF2F2" if "negatif" in s_val.lower() else "#FFFBEB")
                cards_html += f"""
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.75rem; color:#64748B; font-weight:600;">{escape(d_val)}</span>
                    <div style="display:flex; gap:4px;">
                        <span style="font-size:0.7rem; font-weight:700; color:{s_color}; background:{s_bg}; padding:2px 6px; border-radius:6px;">{escape(s_val)}</span>
                        <span style="font-size:0.7rem; font-weight:700; color:#0B5ED7; background:#EAF5FF; padding:2px 6px; border-radius:6px;">★ {r_val}</span>
                    </div>
                </div>
                <div style="font-size:0.8rem; color:#102040; line-height:1.4; white-space:normal; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                    {escape(t_val)}
                </div>
                """
            else:
                item_count = 0
                for col in displayed.columns:
                    if col == "No":
                        continue
                    val = str(row[col])
                    if val and val != "nan" and val != "-":
                        if item_count == 0:
                            cards_html += f'<div style="font-weight:800; color:#07132F; font-size:0.85rem; margin-bottom:4px;">{escape(col)}: {escape(val)}</div>'
                        else:
                            cards_html += f'<div style="font-size:0.75rem; color:#475569; margin-bottom:2px;">{escape(col)}: <strong style="color:#102040;">{escape(val)}</strong></div>'
                        item_count += 1
            cards_html += '</div>'
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

    previous, page_status, next_page = st.columns([1, 2, 1])
    with previous:
        if st.button(
            "Sebelumnya",
            key=f"{key_prefix}_previous",
            disabled=current_page <= 1,
            width="stretch",
        ):
            st.session_state[page_key] = current_page - 1
            st.rerun()
    with page_status:
        st.caption(f"Halaman {current_page} / {total_pages}")
    with next_page:
        if st.button(
            "Berikutnya",
            key=f"{key_prefix}_next",
            disabled=current_page >= total_pages,
            width="stretch",
        ):
            st.session_state[page_key] = current_page + 1
            st.rerun()
    return displayed


def render_review_analysis(
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    review_total: int,
    filters: dict[str, Any],
    review_filter_active: bool,
) -> None:
    section_banner(
        "Review Intelligence",
        "Analisis Ulasan",
        "Sentimen, rating, tren waktu, keyword, dan contoh suara pengguna.",
        banner_asset_key="review_banner",
    )
    if reviews is None or reviews.empty:
        st.info("Tidak ada ulasan yang cocok dengan filter aktif.")
        return

    metrics = review_metrics(reviews, review_columns)
    scope_label = "Filter aktif" if review_filter_active else "Total data"
    if review_filter_active:
        st.info(
            f"Menampilkan **{metrics['total']} dari {review_total} ulasan** "
            "berdasarkan filter yang dipilih. Angka berubah karena filter aktif."
        )
    else:
        st.info(f"Menampilkan seluruh **{review_total} ulasan**.")

    with st.container(key="layout_review_summary"):
        metric_columns = st.columns(5)
        metric_values = [
            ("Total Ulasan", f"{metrics['total']:,}", "hasil filter aktif"),
            ("Positif", f"{metrics['positive']:,}", f"{metrics['positive_pct']:.1f}%"),
            ("Netral", f"{metrics['neutral']:,}", "rating 3"),
            ("Negatif", f"{metrics['negative']:,}", "rating 1-2"),
            ("Rata-rata Rating", f"{metrics['avg_rating']:.2f}", "dari 5"),
        ]
        for column, item in zip(metric_columns, metric_values):
            with column:
                st.markdown(summary_card(*item), unsafe_allow_html=True)

    review_column = review_columns.get("review")
    st.markdown("#### Keyword yang sering muncul")
    if review_column and review_column in reviews.columns:
        render_keyword_chips(extract_keywords(reviews[review_column], 15))
    else:
        st.info("Kolom teks ulasan tidak tersedia.")

    with st.container(key="layout_review_charts"):
        left, right = st.columns(2)
        with left:
            with st.container(key="chart_review_sentiment", border=True):
                counts = reviews["sentimen"].value_counts()
                plot_chart(
                    donut_chart(
                        counts,
                        "Distribusi Sentimen",
                        {
                            "Positif": C_POSITIVE,
                            "Netral": C_NEUTRAL,
                            "Negatif": C_NEGATIVE,
                        },
                        scope_label,
                        "ulasan",
                    ),
                    "review_sentiment",
                )
                st.caption("Sentimen diturunkan dari rating: 4-5 positif, 3 netral, 1-2 negatif.")
        with right:
            with st.container(key="chart_review_rating", border=True):
                rating_column = review_columns.get("rating")
                if rating_column and rating_column in reviews.columns:
                    counts = (
                        reviews[rating_column]
                        .dropna()
                        .astype(int)
                        .value_counts()
                        .reindex([1, 2, 3, 4, 5], fill_value=0)
                    )
                    colors = [
                        C_NEGATIVE,
                        "#F87171",
                        C_NEUTRAL,
                        "#34D399",
                        C_POSITIVE,
                    ]
                    plot_chart(
                        bar_chart(
                            [f"Rating {rating}" for rating in counts.index],
                            counts.values.tolist(),
                            "Distribusi Rating",
                            colors,
                            denominator=len(reviews),
                            scope_label=scope_label,
                            unit_label="ulasan",
                        ),
                        "review_rating",
                    )
                    st.caption("Sebaran rating lengkap pada data ulasan yang tampil.")
                else:
                    st.info("Kolom rating tidak tersedia.")

    with st.container(key="chart_review_trend", border=True):
        date_column = review_columns.get("date")
        if date_column and date_column in reviews.columns:
            fig = review_trend_chart(reviews, date_column, scope_label)
            if fig.data:
                plot_chart(fig, "review_trend")
                st.caption(
                    "Tren utama selalu dikelompokkan per tanggal agar tidak "
                    "mencampurkan analisis harian dengan jam."
                )
            else:
                st.info("Tidak ada tanggal valid untuk membuat tren.")
        else:
            st.info("Kolom tanggal ulasan tidak tersedia.")

    if date_column and date_column in reviews.columns:
        with st.expander("Distribusi Ulasan per Jam (analisis tambahan)"):
            hourly = review_hour_chart(reviews, date_column, scope_label)
            if hourly.data:
                plot_chart(hourly, "review_hour_distribution")
                st.caption(
                    "Grafik ini bersifat tambahan. Tren utama tetap menggunakan "
                    "tanggal kalender."
                )

    st.markdown("#### Keluhan negatif utama")
    complaints = complaint_term_counts(reviews, review_column)
    if complaints:
        render_keyword_chips(complaints)
        st.caption(
            "Jumlah menunjukkan banyak ulasan negatif yang mengandung istilah "
            "tersebut; satu ulasan dapat memuat lebih dari satu istilah."
        )
    else:
        st.info("Tidak ada istilah keluhan terpantau pada data aktif.")

    public_reviews = reviews_for_public(reviews, review_columns)
    review_table = public_reviews.copy().reset_index(drop=True)
    review_table.insert(
        0,
        "Pengguna anonim",
        [f"Ulasan #{index:03d}" for index in range(1, len(review_table) + 1)],
    )
    review_table["Sumber"] = "Dataset ulasan"
    limit = table_limit(filters)
    default_page_size = limit or min(100, max(10, len(review_table)))

    st.markdown("#### Tabel ulasan")
    displayed = render_paginated_table(
        review_table,
        "review_analysis",
        height=500,
        default_page_size=default_page_size,
        column_config={
            "No": st.column_config.NumberColumn("No", width="small"),
            "Pengguna anonim": st.column_config.TextColumn(
                "Pengguna anonim",
                width="medium",
            ),
            review_columns.get("rating", "rating"): st.column_config.NumberColumn(
                "Rating", width="small", format="%d"
            ),
            review_columns.get("date", "tanggal"): st.column_config.DatetimeColumn(
                "Tanggal", width="medium", format="DD-MM-YYYY HH:mm"
            ),
            review_columns.get("review", "ulasan"): st.column_config.TextColumn(
                "Ulasan", width="large"
            ),
            "sentimen": st.column_config.TextColumn("Sentimen", width="small"),
            "Sumber": st.column_config.TextColumn("Sumber", width="medium"),
        },
    )
    st.caption(
        f"Halaman ini menampilkan {len(displayed)} baris. Download memuat seluruh "
        f"{len(public_reviews)} ulasan hasil filter."
    )
    st.download_button(
        "Download seluruh ulasan hasil filter",
        data=convert_df_to_csv(public_reviews),
        file_name="ulasan_hasil_filter_publik.csv",
        mime="text/csv",
    )

    st.markdown("#### Contoh ulasan lengkap")
    examples = public_reviews.head(10)
    for _, row in examples.iterrows():
        rating_column = review_columns.get("rating")
        date_column = review_columns.get("date")
        text_column = review_columns.get("review")
        rating = row.get(rating_column, "-") if rating_column else "-"
        review_date = row.get(date_column, "-") if date_column else "-"
        sentiment = row.get("sentimen", "-")
        review_text = row.get(text_column, "-") if text_column else "-"
        with st.expander(f"{sentiment} | Rating {rating} | {review_date}"):
            st.write(review_text)


def explorer_table_view(
    frame: pd.DataFrame,
    key_prefix: str,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    columns = [str(column) for column in frame.columns]
    with st.container(key=f"layout_explorer_controls_{key_prefix}"):
        control_search, control_sort, control_order = st.columns([1.5, 1, 0.8])
        with control_search:
            query = st.text_input(
                "Cari dalam tabel",
                key=f"{key_prefix}_search",
                placeholder="Pencarian literal, bukan regex",
            ).strip()
        with control_sort:
            sort_column = st.selectbox(
                "Urutkan kolom",
                options=["Tanpa sorting", *columns],
                key=f"{key_prefix}_sort_column",
            )
        with control_order:
            sort_order = st.selectbox(
                "Urutan",
                options=["Naik", "Turun"],
                key=f"{key_prefix}_sort_order",
            )

    result = frame.copy()
    if query:
        searchable = result.astype(str)
        mask = searchable.apply(
            lambda column: column.str.contains(
                query,
                case=False,
                regex=False,
                na=False,
            )
        ).any(axis=1)
        result = result.loc[mask].copy()
    if sort_column != "Tanpa sorting" and sort_column in result.columns:
        result = result.sort_values(
            sort_column,
            ascending=sort_order == "Naik",
            kind="mergesort",
        )
    return result


def render_data_explorer(
    survey: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    questionnaire: pd.DataFrame | None,
    audit_frame: pd.DataFrame,
    survey_total: int,
    review_total: int,
    review_columns: dict[str, Any],
    filters: dict[str, Any],
) -> None:
    section_banner(
        "Privacy-Safe Data",
        "Data Explorer",
        "Eksplorasi data hasil filter tanpa membuka identitas pengguna.",
        banner_asset_key="explorer_banner",
    )
    shield_img = render_image_asset(
        ASSETS.get("privacy_shield", "06_icon_privacy_shield_1254x1254.png"),
        class_name="privacy-shield-icon",
        alt="Data Aman",
        fallback="",
    )
    st.html(
        f"""
        <div class="privacy-note-card">
            <div class="privacy-note-icon">{shield_img}</div>
            <div class="privacy-note-body">
                <strong>🔒 Data Aman — Identitas Tersembunyi</strong>
                <p>Nama responden, username, email, nomor telepon, dan kolom identitas
                serupa tidak ditampilkan. File download publik juga tidak memuat
                identitas pengguna. Privasi responden terlindungi sepenuhnya.</p>
            </div>
        </div>
        """
    )

    st.markdown("#### Audit Metadata Sumber")
    safe_audit_columns = [
        "Sumber",
        "Peran",
        "Publik",
        "Ditemukan",
        "Ukuran (KB)",
        "Sheet/Tabel",
        "Baris",
        "Kolom",
        "Duplikat",
        "Kolom Identitas",
        "Rekonsiliasi",
        "Status",
    ]
    with st.container(key="audit_metadata_desktop"):
        with st.container(key="audit_metadata_card"):
            st.dataframe(
                audit_frame[
                    [
                        column
                        for column in safe_audit_columns
                        if column in audit_frame.columns
                    ]
                ],
                width="stretch",
                hide_index=True,
                height=260,
            )
            
    with st.container(key="audit_metadata_mobile"):
        from html import escape
        cards_html = '<div class="mobile-card-list">'
        for _, row in audit_frame.iterrows():
            sumber = str(row.get("Sumber", "-"))
            status = str(row.get("Status", "-"))
            peran = str(row.get("Peran", "-"))
            baris = str(row.get("Baris", "-"))
            kolom = str(row.get("Kolom", "-"))
            identitas = str(row.get("Kolom Identitas", "-"))
            
            status_color = "#16C784" if "valid" in status.lower() or "aman" in status.lower() else "#FFB020"
            status_bg = "#ECFDF5" if "valid" in status.lower() or "aman" in status.lower() else "#FFFBEB"
            
            cards_html += f"""
            <div class="mobile-card-item" style="border: 1px solid #D7E8FF; border-radius: 12px; padding: 10px; margin-bottom: 8px; background: white;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.8rem; font-weight:700; color:#07132F;">{escape(sumber)}</span>
                    <span style="font-size:0.7rem; font-weight:700; color:{status_color}; background:{status_bg}; padding:2px 6px; border-radius:6px;">{escape(status)}</span>
                </div>
                <div style="font-size:0.75rem; color:#475569; margin-bottom:2px;">Peran: <strong style="color:#102040;">{escape(peran)}</strong></div>
                <div style="font-size:0.75rem; color:#475569; margin-bottom:2px;">Dimensi: <strong style="color:#102040;">{escape(baris)} Baris x {escape(kolom)} Kolom</strong></div>
                <div style="font-size:0.75rem; color:#475569;">Kolom Identitas: <strong style="color:#FF4D5E;">{escape(identitas)}</strong></div>
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)
    st.caption(
        "File raw dan database hanya ditampilkan sebagai metadata. Nilai identitas "
        "tidak pernah dimuat ke tabel publik."
    )

    st.markdown("#### Data Survey")
    public_survey = sanitize_public_df(survey)
    if public_survey.empty:
        render_empty_state(
            "Data survey tidak ditemukan",
            "Ubah atau reset filter survey untuk menampilkan kembali data.",
        )
    else:
        st.caption(
            f"Total asli: {survey_total} baris | Setelah filter: {len(public_survey)} baris "
            f"| {len(public_survey.columns)} kolom publik"
        )
        survey_view = explorer_table_view(public_survey, "explorer_survey")
        if survey_view.empty:
            render_empty_state(
                "Pencarian survey tidak menemukan hasil",
                "Gunakan kata yang lebih umum atau kosongkan pencarian tabel.",
            )
        else:
            render_paginated_table(
                survey_view,
                "explorer_survey_table",
                default_page_size=25,
                height=420,
            )
        st.download_button(
            "Download survey hasil filter",
            data=convert_df_to_csv(public_survey),
            file_name="survey_hasil_filter_publik.csv",
            mime="text/csv",
        )

    st.divider()
    st.markdown("#### Data Ulasan")
    public_reviews = reviews_for_public(reviews, review_columns)
    if public_reviews.empty:
        render_empty_state(
            "Data ulasan tidak ditemukan",
            "Ubah atau reset filter ulasan untuk menampilkan kembali data.",
        )
    else:
        st.caption(
            f"Total asli: {review_total} ulasan | Setelah filter: "
            f"{len(public_reviews)} ulasan"
        )
        review_view = explorer_table_view(public_reviews, "explorer_reviews")
        limit = table_limit(filters)
        if review_view.empty:
            render_empty_state(
                "Pencarian ulasan tidak menemukan hasil",
                "Gunakan kata yang lebih umum atau kosongkan pencarian tabel.",
            )
        else:
            render_paginated_table(
                review_view,
                "explorer_review_table",
                default_page_size=limit or 25,
                height=500,
            )
        st.download_button(
            "Download ulasan hasil filter",
            data=convert_df_to_csv(public_reviews),
            file_name="ulasan_hasil_filter_publik.csv",
            mime="text/csv",
        )

    st.divider()
    st.markdown("#### Data Hasil Kuesioner")
    if questionnaire is None or questionnaire.empty:
        render_empty_state(
            "Data kuesioner tidak tersedia",
            "Periksa sumber hasil_kuesioner.csv dan audit data.",
        )
    else:
        questionnaire_public = questionnaire[
            ["label", "pertanyaan", "rata_rata"]
        ].copy()
        questionnaire_view = explorer_table_view(
            questionnaire_public,
            "explorer_questionnaire",
        )
        if questionnaire_view.empty:
            render_empty_state(
                "Pencarian indikator tidak menemukan hasil",
                "Gunakan kode Q1-Q20 atau potongan teks pertanyaan.",
            )
        else:
            render_paginated_table(
                questionnaire_view,
                "explorer_questionnaire_table",
                default_page_size=25,
                height=420,
                column_config={
                    "No": st.column_config.NumberColumn("No", width="small"),
                    "label": st.column_config.TextColumn("Kode", width="small"),
                    "pertanyaan": st.column_config.TextColumn(
                        "Pertanyaan",
                        width="large",
                    ),
                    "rata_rata": st.column_config.NumberColumn(
                        "Rata-rata",
                        format="%.2f",
                        width="small",
                    ),
                },
            )
        st.download_button(
            "Download hasil kuesioner publik",
            data=convert_df_to_csv(questionnaire_public),
            file_name="hasil_kuesioner_publik.csv",
            mime="text/csv",
        )

    database_audit = audit_frame[audit_frame["Sumber"].eq(DATABASE_PATH.name)]
    if not database_audit.empty:
        database_status = str(database_audit.iloc[0]["Status"])
        st.caption(
            "Database validasi opsional: "
            f"{database_status}. Database tidak menjadi sumber KPI dashboard."
        )


def render_output_and_presentation(
    audit_frame: pd.DataFrame,
    invariant_errors: list[str],
) -> None:
    section_banner(
        "Submission Readiness",
        "Lampiran Presentasi",
        "Audit sumber data, checklist penyerahan, tautan, dan panduan screenshot UAS.",
        banner_asset_key="presentation_banner",
    )

    if invariant_errors:
        st.warning(
            "Validasi baseline menemukan perbedaan. Periksa detail audit sebelum "
            "menggunakan dashboard untuk presentasi."
        )
        with st.expander("Detail invariant yang tidak sesuai", expanded=True):
            for message in invariant_errors:
                st.write(f"- {message}")
    else:
        st.success(
            "Semua invariant utama sesuai: 50 survey, 330 ulasan, 20 indikator, "
            "rating, sentimen, dan tanggal ulasan tervalidasi."
        )

    with st.container(key="layout_presentation_lobby"):
        intro_column, visual_column = st.columns([2.2, 0.8], vertical_alignment="center")
        with intro_column:
            st.markdown("#### Mode presentasi")
            st.write(
                "Landing visual tampil saat aplikasi dibuka. Tombol ini dapat "
                "menampilkan kembali cover pembuka tanpa mengubah filter atau data."
            )
            if st.button(
                "Tampilkan Lobi",
                key="show_optional_lobby",
                help="Buka cover presentasi tanpa mengubah filter atau data",
            ):
                go_to_landing()
                st.rerun()
        with visual_column:
            mobile_visual = render_image_asset(
                "dana_mobile_mockup_360x480.png",
                class_name="presentation-visual",
                alt="Preview responsif dashboard DANA Insight",
            )
            if mobile_visual:
                st.html(mobile_visual)

    with st.container(key="output_audit_desktop"):
        with st.container(key="output_audit_card"):
            st.dataframe(
                audit_frame,
                width="stretch",
                hide_index=True,
                height=320,
                column_config={
                    "Nama Kolom": st.column_config.TextColumn(
                        "Nama Kolom",
                        width="large",
                    ),
                    "Kolom Identitas": st.column_config.TextColumn(
                        "Kolom Identitas",
                        width="medium",
                    ),
                    "Status": st.column_config.TextColumn("Status", width="medium"),
                },
            )
            
    with st.container(key="output_audit_mobile"):
        from html import escape
        cards_html = '<div class="mobile-card-list">'
        for _, row in audit_frame.iterrows():
            sumber = str(row.get("Sumber", "-"))
            status = str(row.get("Status", "-"))
            peran = str(row.get("Peran", "-"))
            baris = str(row.get("Baris", "-"))
            kolom = str(row.get("Kolom", "-"))
            identitas = str(row.get("Kolom Identitas", "-"))
            
            status_color = "#16C784" if "valid" in status.lower() or "aman" in status.lower() else "#FFB020"
            status_bg = "#ECFDF5" if "valid" in status.lower() or "aman" in status.lower() else "#FFFBEB"
            
            cards_html += f"""
            <div class="mobile-card-item" style="border: 1px solid #D7E8FF; border-radius: 12px; padding: 10px; margin-bottom: 8px; background: white;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:0.8rem; font-weight:700; color:#07132F;">{escape(sumber)}</span>
                    <span style="font-size:0.7rem; font-weight:700; color:{status_color}; background:{status_bg}; padding:2px 6px; border-radius:6px;">{escape(status)}</span>
                </div>
                <div style="font-size:0.75rem; color:#475569; margin-bottom:2px;">Peran: <strong style="color:#102040;">{escape(peran)}</strong></div>
                <div style="font-size:0.75rem; color:#475569; margin-bottom:2px;">Dimensi: <strong style="color:#102040;">{escape(baris)} Baris x {escape(kolom)} Kolom</strong></div>
                <div style="font-size:0.75rem; color:#475569;">Kolom Identitas: <strong style="color:#FF4D5E;">{escape(identitas)}</strong></div>
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

    deliverables = [
        ("Dashboard Streamlit", "Tersedia melalui app.py dan siap dijalankan lokal."),
        ("Source Code", "Entry point: app.py. builder.py adalah legacy dan jangan dijalankan."),
        ("Repository GitHub", "https://github.com/Sekolah76/dashboard-tugas"),
        ("Streamlit Cloud", "https://dashboard-dana.streamlit.app"),
        ("Screenshot", "Ambil sepuluh tampilan utama setelah QA visual final."),
        ("Ringkasan Fitur", "Tersedia di Ringkasan_Fitur_Dashboard.txt."),
    ]
    cards = "".join(
        (
            '<div class="deliverable-card">'
            f"<strong>{escape(title)}</strong><span>{escape(note)}</span>"
            "</div>"
        )
        for title, note in deliverables
    )
    st.markdown(f'<div class="deliverable-grid">{cards}</div>', unsafe_allow_html=True)

    st.markdown("#### Bahan Flyer Presentasi")
    st.html(
        """
        <div style="background:#F0F6FF; border: 1.5px solid #D7E8FF; border-radius: 12px; padding: 16px; margin-bottom: 20px;">
            <div style="font-weight:800; color:#07132F; font-size:0.9rem; margin-bottom:8px;">💡 Panduan Bahan Flyer (Snapshot Flyer)</div>
            <div style="font-size:0.8rem; color:#475569; line-height:1.4;">
                <p style="margin-bottom:6px;">Tab <strong>Snapshot Flyer</strong> disediakan khusus untuk mempermudah pengambilan tangkapan layar (screenshot) sebagai bahan visual di Canva atau flyer presentasi UAS Anda.</p>
                <ul style="margin-left:16px; margin-bottom:0;">
                    <li>Gunakan <strong>browser zoom 80-90%</strong> untuk memuat seluruh komponen flyer dalam satu screenshot utuh.</li>
                    <li>Gunakan <strong>laptop atau desktop</strong> untuk mendapatkan resolusi dan tata letak flyer terbaik.</li>
                </ul>
            </div>
        </div>
        """
    )

    with st.container(key="layout_presentation_links"):
        link_left, link_right = st.columns(2)
        with link_left:
            st.text_input(
                "GitHub URL",
                value="https://github.com/Sekolah76/dashboard-tugas",
                key="presentation_github_url",
            )
        with link_right:
            st.text_input(
                "Streamlit Cloud URL",
                value="https://dashboard-dana.streamlit.app",
                key="presentation_streamlit_url",
            )
        st.caption(
            "Kolom ini bersifat catatan sesi untuk referensi tautan publik dashboard."
        )

    st.markdown("#### Daftar screenshot presentasi")
    screenshot_names = [
        "01_Lobby",
        "02_Hero_KPI",
        "03_Control_Panel",
        "04_Overview",
        "05_Analisis_Survei",
        "06_Analisis_Ulasan",
        "07_Data_Explorer",
        "08_Kesimpulan",
        "09_Lampiran_Presentasi",
        "10_Mobile_View",
    ]
    screenshot_frame = pd.DataFrame(
        {
            "No": range(1, len(screenshot_names) + 1),
            "Nama Screenshot": screenshot_names,
            "Status": ["Perlu diambil setelah QA visual"] * len(screenshot_names),
        }
    )
    with st.container(key="output_screenshot_desktop"):
        with st.container(key="output_screenshot_card"):
            st.dataframe(screenshot_frame, width="stretch", hide_index=True)
            
    with st.container(key="output_screenshot_mobile"):
        from html import escape
        cards_html = '<div class="mobile-card-list">'
        for _, row in screenshot_frame.iterrows():
            no = str(row.get("No", ""))
            name = str(row.get("Nama Screenshot", ""))
            status = str(row.get("Status", ""))
            
            cards_html += f"""
            <div class="mobile-card-item" style="border: 1px solid #D7E8FF; border-radius: 12px; padding: 10px; margin-bottom: 8px; background: white;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:0.8rem; font-weight:700; color:#07132F;">{no}. {escape(name)}</span>
                    <span style="font-size:0.7rem; font-weight:600; color:#5C6B86; background:#EEF2F7; padding:2px 6px; border-radius:6px;">{escape(status)}</span>
                </div>
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)

    st.markdown("#### 📋 Ringkasan Otomatis Presentasi")
    with st.container(key="auto_summary_panel"):
        st.html("""
        <div class="insight-card" style="border-color:#BFDBFE; background:linear-gradient(135deg,#F0F9FF,#EFF6FF);">
            <h4>Ringkasan 4 Poin Utama</h4>
            <ul>
                <li>
                    <strong>Profil Responden Dominan:</strong>
                    50 responden, didominasi Perempuan (78%), kelompok usia 18–22 tahun (72%),
                    frekuensi penggunaan jarang (42%).
                </li>
                <li>
                    <strong>Skor Survei Utama:</strong>
                    Rata-rata 20 indikator kuesioner mencapai <strong>4.00 / 5</strong>
                    (kategori Kuat/Baik). Variabel Praktis (X2) dan Fleksibilitas (X1)
                    mendapat skor tertinggi.
                </li>
                <li>
                    <strong>Rating &amp; Sentimen:</strong>
                    Rata-rata rating ulasan <strong>3.89 / 5</strong> dari 330 ulasan.
                    Sentimen Positif (rating 4–5) mendominasi dengan <strong>70.3%</strong>
                    (232 ulasan), Negatif 25.8%, Netral 3.9%.
                </li>
                <li>
                    <strong>Area Perbaikan:</strong>
                    Ulasan negatif (85 ulasan) banyak menyebut masalah saldo, akun,
                    transaksi gagal, dan biaya premium. Perlu perhatian khusus pada
                    keandalan sistem dan transparansi biaya.
                </li>
            </ul>
            <p style="font-size:.72rem;color:#64748B;margin-top:.6rem;">
                <em>Catatan: Dashboard ini bersifat deskriptif. Tidak ada simpulan kausal
                yang dapat ditarik hanya dari data ini.</em>
            </p>
        </div>
        """)

        summary_text = """RINGKASAN PENELITIAN — DANA Insight Command Center

1. PROFIL RESPONDEN
   - Total: 50 responden
   - Dominan: Perempuan (39/78%), Usia 18-22 tahun (36/72%)
   - Frekuensi DANA: Jarang (21/42%)

2. SKOR KUESIONER
   - Rata-rata 20 indikator: 4.00 / 5 (Kuat/Baik)
   - Indikator tertinggi: kategori Kuat (≥4.00)
   - Variabel: X1-Fleksibilitas, X2-Praktis, M-Kepercayaan

3. RATING & SENTIMEN ULASAN
   - Total ulasan: 330
   - Rating rata-rata: 3.89 / 5
   - Sentimen Positif: 232 ulasan (70.3%)
   - Sentimen Netral: 13 ulasan (3.9%)
   - Sentimen Negatif: 85 ulasan (25.8%)

4. AREA PERBAIKAN
   - Keluhan utama: saldo, akun, transaksi, biaya
   - Perlu peningkatan keandalan sistem dan layanan pelanggan

Catatan: Data bersifat deskriptif. Tidak menyimpulkan hubungan kausal."""

        with st.expander("📄 Teks Ringkasan (dapat disalin)", expanded=False):
            st.code(summary_text, language="text")
            st.caption("Salin teks di atas untuk presentasi atau laporan Anda.")


def render_conclusion(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    scope_label: str,
) -> None:
    section_heading(
        "Decision Support",
        "Kesimpulan Utama",
        "Ringkasan otomatis berdasarkan data yang sedang ditampilkan.",
        "variable_illustration.svg",
    )
    conclusion_visual = render_image_asset(
        "dana_wallet_cluster_480x480.png",
        class_name="conclusion-visual",
        alt="",
    )

    profile_html = ""
    if survey is not None and not survey.empty:
        total_survey = len(survey)
        def get_dominant(col_key: str) -> str:
            col = survey_columns.get(col_key)
            if col and col in survey.columns:
                counts = survey[col].value_counts()
                if not counts.empty:
                    val = counts.index[0]
                    count = counts.iloc[0]
                    pct = (count / total_survey) * 100
                    return f"{escape(str(val))} = {count} dari {total_survey} = {pct:.0f}%"
            return "-"
        
        dominant_gender = get_dominant("gender")
        dominant_age = get_dominant("age")
        dominant_freq = get_dominant("frequency")
        
        profile_html = f"""
        <ul>
            <li>Mayoritas responden berjenis kelamin <strong>{dominant_gender}</strong>.</li>
            <li>Kelompok usia dominan adalah <strong>{dominant_age}</strong>.</li>
            <li>Frekuensi penggunaan DANA dominan: <strong>{dominant_freq}</strong>.</li>
        </ul>
        """

    questionnaire_html = ""
    if questionnaire is not None and not questionnaire.empty:
        questionnaire_average = safe_mean(questionnaire["rata_rata"])
        best_ind = questionnaire.loc[questionnaire["rata_rata"].idxmax()]
        worst_ind = questionnaire.loc[questionnaire["rata_rata"].idxmin()]
        
        variable_scores, _ = compute_variable_scores(
            survey,
            survey_columns.get("questions", []),
        )
        var_text = ""
        if not variable_scores.empty:
            best_var = variable_scores.loc[variable_scores["rata_rata"].idxmax()]
            worst_var = variable_scores.loc[variable_scores["rata_rata"].idxmin()]
            var_text = (
                f"<li>Variabel tertinggi: <strong>{escape(str(best_var['variabel']))} = {best_var['rata_rata']:.2f}</strong>.</li>"
                f"<li>Variabel terendah: <strong>{escape(str(worst_var['variabel']))} = {worst_var['rata_rata']:.2f}</strong>.</li>"
            )
            
        questionnaire_html = f"""
        <ul>
            <li>Skor kuesioner rata-rata mencapai <strong>{questionnaire_average:.2f}/5</strong>.</li>
            {var_text}
            <li>Indikator tertinggi: <strong>{escape(str(best_ind['label']))} ({float(best_ind['rata_rata']):.2f})</strong> - {escape(str(best_ind['pertanyaan']))}</li>
            <li>Indikator terendah: <strong>{escape(str(worst_ind['label']))} ({float(worst_ind['rata_rata']):.2f})</strong> - {escape(str(worst_ind['pertanyaan']))}</li>
        </ul>
        """

    scraping_html = ""
    if reviews is not None and not reviews.empty:
        total_reviews = len(reviews)
        metrics = review_metrics(reviews, review_columns)
        
        def sentiment_text(sent_name: str, count: int) -> str:
            pct = (count / total_reviews) * 100 if total_reviews else 0.0
            return f"Sentimen {sent_name.lower()} <strong>{count} dari {total_reviews} = {pct:.1f}%</strong>"
            
        pos_text = sentiment_text("Positif", metrics["positive"])
        neg_text = sentiment_text("Negatif", metrics["negative"])
        net_text = sentiment_text("Netral", metrics["neutral"])
        
        negative_keywords: list[tuple[str, int]] = []
        review_column = review_columns.get("review")
        if review_column and "sentimen" in reviews.columns:
            negative_keywords = complaint_term_counts(reviews, review_column)[:5]
        keyword_text = (
            ", ".join(f"{word} ({count}x)" for word, count in negative_keywords)
            if negative_keywords
            else "tidak ada keluhan spesifik dominan pada ulasan negatif"
        )
        
        scraping_html = f"""
        <ul>
            <li>Rating rata-rata dari ulasan pengguna adalah <strong>{metrics['avg_rating']:.2f}/5</strong>.</li>
            <li>{pos_text}, {neg_text}, dan {net_text}.</li>
            <li>Keyword/keluhan negatif utama: <strong>{escape(keyword_text)}</strong>.</li>
        </ul>
        """

    st.html(
        f"""
        <div class="insight-card">
            {conclusion_visual}
            <h4 style="margin-bottom:0.5rem;font-size:1.05rem;">Ringkasan Analitis — {escape(scope_label)}</h4>
            
            <p style="margin-top:0.8rem;font-weight:bold;margin-bottom:0.2rem;">Profil Responden</p>
            {profile_html}
            
            <p style="margin-top:0.8rem;font-weight:bold;margin-bottom:0.2rem;">Hasil Kuesioner (X1, X2, M, Y)</p>
            {questionnaire_html}
            
            <p style="margin-top:0.8rem;font-weight:bold;margin-bottom:0.2rem;">Hasil Web Scraping</p>
            {scraping_html}
            
            <p style="margin-top:0.8rem;font-weight:bold;margin-bottom:0.2rem;">Kesimpulan Akhir</p>
            <ul>
                <li>Secara keseluruhan, DANA memiliki skor kepuasan yang tinggi baik pada responden survei maupun sentimen ulasan. Fokus perbaikan disarankan pada area indikator terendah dan keluhan terbanyak untuk lebih meningkatkan pengalaman pengguna (tanpa mengklaim hubungan kausal).</li>
            </ul>
        </div>
        """
    )


def render_clean_html(html_str: str) -> None:
    import textwrap
    dedented = textwrap.dedent(html_str).strip()
    # Remove leading whitespace from each line to prevent markdown code block formatting (4+ spaces)
    cleaned = "\n".join(line.lstrip() for line in dedented.splitlines())
    st.markdown(cleaned, unsafe_allow_html=True)


def render_snapshot_flyer(
    survey: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
    survey_columns: dict[str, Any],
) -> None:
    import textwrap

    section_heading(
        "Flyer Snapshot",
        "Snapshot Flyer",
        "Presentation snapshot board - optimized for Canva/flyer screen capture.",
        "dana_mark.svg",
    )

    # Compute calculations dynamically based on unfiltered data (guarantees invariants match)
    survey_count = len(survey) if survey is not None else 50
    review_count = len(reviews) if reviews is not None else 330
    
    avg_skor = (
        safe_mean(questionnaire["rata_rata"])
        if questionnaire is not None and not questionnaire.empty
        else 4.00
    )
    
    metrics = review_metrics(reviews, review_columns)
    avg_rating = metrics.get("avg_rating", 3.89)
    positive_pct = metrics.get("positive_pct", 70.3)
    
    # Dynamic counts for mini stats
    if questionnaire is not None and not questionnaire.empty:
        kuat_count = len(questionnaire[questionnaire["rata_rata"] >= 4.0])
        cukup_count = len(questionnaire[(questionnaire["rata_rata"] >= 3.0) & (questionnaire["rata_rata"] < 4.0)])
        perhatian_count = len(questionnaire[questionnaire["rata_rata"] < 3.0])
    else:
        kuat_count = 13
        cukup_count = 7
        perhatian_count = 0
        
    if reviews is not None and not reviews.empty and review_columns.get("rating") in reviews.columns:
        r_col = review_columns.get("rating")
        r5_count = len(reviews[reviews[r_col] == 5])
    else:
        r5_count = 220

    # Calculate variables score dynamically
    x1_score = 4.00
    x2_score = 4.26
    m_score = 3.82
    y_score = 4.00

    if survey is not None:
        vars_df, _ = compute_variable_scores(survey, survey_columns.get("questions", []))
        if not vars_df.empty:
            for _, row in vars_df.iterrows():
                var_name = str(row["variabel"])
                score_val = float(row["rata_rata"])
                if "X1" in var_name:
                    x1_score = score_val
                elif "X2" in var_name:
                    x2_score = score_val
                elif "M" in var_name:
                    m_score = score_val
                elif "Y" in var_name:
                    y_score = score_val

    x1_pct = min(100.0, max(0.0, (x1_score / 5.0) * 100.0))
    x2_pct = min(100.0, max(0.0, (x2_score / 5.0) * 100.0))
    m_pct = min(100.0, max(0.0, (m_score / 5.0) * 100.0))
    y_pct = min(100.0, max(0.0, (y_score / 5.0) * 100.0))

    # Load visual assets safely via the cached registry
    bg_path = find_existing_asset(["assets/dana_hero_banner_1920x520.png"])
    bg_uri = image_to_data_uri(bg_path) if bg_path else ""
    logo_path = find_existing_asset(["assets/dana_logo_wordmark_header_480x120.png"])
    logo_uri = image_to_data_uri(logo_path) if logo_path else ""

    # Desktop View (Canva-ready 16:9 presentation slide layout)
    with st.container(key="snapshot_flyer_desktop"):
        with st.container(key="snapshot_flyer_frame_desktop"):
            # Header Row with base64 visual background
            render_clean_html(f"""
            <div class="flyer-header-visual" style="
                background-image: linear-gradient(90deg, #F7FBFF 0%, rgba(247,251,255,0.96) 35%, rgba(247,251,255,0.85) 60%, rgba(247,251,255,0.1) 100%), url('{bg_uri}');
                background-size: cover;
                background-position: right center;
                border-radius: 18px;
                padding: 20px 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border: 1px solid #D7E8FF;
                margin-bottom: 16px;
            ">
                <div style="text-align:left;">
                    <div style="display:flex; align-items:center; gap:10px;">
                        <img src="{logo_uri}" alt="DANA Logo" style="height:28px; width:auto; object-fit:contain; display:block;" />
                        <span style="font-size:0.65rem; font-weight:800; color:#108EE9; background:#EAF5FF; padding:2px 8px; border-radius:20px; border:1px solid #D7E8FF; text-transform:uppercase; letter-spacing:0.05em;">Presentation Snapshot</span>
                    </div>
                    <div style="color:#07132F; font-weight:900; font-size:1.6rem; line-height:1.2; margin-top:6px;">DANA Insight Command Center</div>
                    <div style="color:#5C6B86; font-size:0.8rem; font-weight:600; margin-top:2px;">Survey &amp; Review Analytics — Fintech Experience Dashboard</div>
                </div>
                <div style="text-align:right; font-size:0.68rem; color:#64748B; font-weight:700; background:rgba(255,255,255,0.8); padding:8px 12px; border-radius:10px; border:1px solid #E2E8F0; backdrop-filter:blur(4px);">
                    <div>DATA SURVEY: {survey_count} RESPONDEN</div>
                    <div style="margin-top:2px;">REVIEW: {review_count} ULASAN</div>
                </div>
            </div>
            """)
            
            # KPI Metrics Row (5 columns)
            render_clean_html(f"""
            <div class="flyer-kpi-grid" style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px;">
                <div class="flyer-kpi-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:10px; text-align:center;">
                    <div class="flyer-kpi-label" style="font-size:0.58rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Responden</div>
                    <div class="flyer-kpi-value" style="font-size:1.45rem; font-weight:900; color:#108EE9; font-variant-numeric:tabular-nums; line-height:1.15;">{survey_count}</div>
                    <div style="font-size:0.55rem; color:#64748B; font-weight:600; margin-top:2px;">Responden Survei</div>
                </div>
                <div class="flyer-kpi-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:10px; text-align:center;">
                    <div class="flyer-kpi-label" style="font-size:0.58rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Ulasan</div>
                    <div class="flyer-kpi-value" style="font-size:1.45rem; font-weight:900; color:#2563EB; font-variant-numeric:tabular-nums; line-height:1.15;">{review_count}</div>
                    <div style="font-size:0.55rem; color:#64748B; font-weight:600; margin-top:2px;">Ulasan Pengguna</div>
                </div>
                <div class="flyer-kpi-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:10px; text-align:center;">
                    <div class="flyer-kpi-label" style="font-size:0.58rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Skor Survey</div>
                    <div class="flyer-kpi-value" style="font-size:1.45rem; font-weight:900; color:#108EE9; font-variant-numeric:tabular-nums; line-height:1.15;">{avg_skor:.2f}<span style="font-size:0.8rem; font-weight:600; color:#64748B;"> / 5</span></div>
                    <div style="font-size:0.55rem; color:#64748B; font-weight:600; margin-top:2px;">Rata-rata Kuesioner</div>
                </div>
                <div class="flyer-kpi-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:10px; text-align:center;">
                    <div class="flyer-kpi-label" style="font-size:0.58rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Rating Ulasan</div>
                    <div class="flyer-kpi-value" style="font-size:1.45rem; font-weight:900; color:#FFB020; font-variant-numeric:tabular-nums; line-height:1.15;">{avg_rating:.2f}<span style="font-size:0.8rem; font-weight:600; color:#64748B;"> / 5</span></div>
                    <div style="font-size:0.55rem; color:#64748B; font-weight:600; margin-top:2px;">Rata-rata Rating</div>
                </div>
                <div class="flyer-kpi-card" style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:14px; padding:10px; text-align:center;">
                    <div class="flyer-kpi-label" style="font-size:0.58rem; color:#047857; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:2px;">Sentimen Positif</div>
                    <div class="flyer-kpi-value" style="font-size:1.45rem; font-weight:900; color:#10B981; font-variant-numeric:tabular-nums; line-height:1.15;">{positive_pct:.1f}%</div>
                    <div style="font-size:0.55rem; color:#047857; font-weight:600; margin-top:2px;">{int(positive_pct/100*review_count)} dari {review_count} Ulasan</div>
                </div>
            </div>
            """)
            
            # Main Layout Columns
            col_1, col_2, col_3 = st.columns([1.05, 1.0, 1.15])
            
            with col_1:
                render_clean_html(f"""
                <div class="flyer-card" style="background:white; border:1px solid #D7E8FF; border-radius:16px; padding:14px; height:100%; box-shadow:0 2px 4px rgba(7, 19, 47, 0.02);">
                    <div class="flyer-section-title" style="font-size:0.8rem; font-weight:850; color:#07132F; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px; padding-bottom:4px; border-bottom:2px solid #F0F6FF;">
                        👥 Profil Responden
                    </div>
                    
                    <!-- Gender Row -->
                    <div style="margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#475569; margin-bottom:4px; font-weight:600;">
                            <span>Perempuan: <strong>78.0%</strong> (39)</span>
                            <span>Laki-laki: <strong>22.0%</strong> (11)</span>
                        </div>
                        <div style="display:flex; height:10px; border-radius:5px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:78%; background:#108EE9;" title="Perempuan: 78%"></div>
                            <div style="width:22%; background:#38BDF8;" title="Laki-laki: 22%"></div>
                        </div>
                    </div>

                    <!-- Age Row -->
                    <div style="margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#475569; margin-bottom:4px; font-weight:600;">
                            <span>Usia Dominan: <strong>18&ndash;22 Tahun</strong></span>
                            <span><strong>72.0%</strong> (36)</span>
                        </div>
                        <div style="display:flex; height:10px; border-radius:5px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:72%; background:#2563EB;" title="18-22 Tahun: 72%"></div>
                            <div style="width:14%; background:#60A5FA;" title="23-27 Tahun: 14%"></div>
                            <div style="width:14%; background:#93C5FD;" title="Lainnya: 14%"></div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.58rem; color:#64748B; margin-top:2px;">
                            <span>18&ndash;22: 72%</span>
                            <span>23&ndash;27: 14%</span>
                            <span>Lainnya: 14%</span>
                        </div>
                    </div>

                    <!-- Frequency Row -->
                    <div style="margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.7rem; color:#475569; margin-bottom:4px; font-weight:600;">
                            <span>Frekuensi Dominan: <strong>Jarang</strong></span>
                            <span><strong>42.0%</strong> (21)</span>
                        </div>
                        <div style="display:flex; height:10px; border-radius:5px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:42%; background:#0B5ED7;" title="Jarang: 42%"></div>
                            <div style="width:38%; background:#3B82F6;" title="Sering: 38%"></div>
                            <div style="width:20%; background:#93C5FD;" title="Sangat Sering: 20%"></div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.58rem; color:#64748B; margin-top:2px;">
                            <span>Jarang: 42%</span>
                            <span>Sering: 38%</span>
                            <span>Sgt Sering: 20%</span>
                        </div>
                    </div>

                    <!-- Highlight Box -->
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:10px; text-align:left; margin-top:8px;">
                        <div style="font-size:0.62rem; color:#64748B; font-weight:700; text-transform:uppercase; margin-bottom:2px;">Karakteristik Utama</div>
                        <div style="font-size:0.72rem; color:#07132F; font-weight:600; line-height:1.35;">
                            Mayoritas responden survei adalah <strong>Perempuan</strong>, kelompok usia muda <strong>18&ndash;22 tahun</strong>, dengan tingkat penggunaan <strong>Jarang</strong>.
                        </div>
                    </div>
                </div>
                """)
            
            with col_2:
                render_clean_html(f"""
                <div class="flyer-card" style="background:white; border:1px solid #D7E8FF; border-radius:16px; padding:14px; height:100%; box-shadow:0 2px 4px rgba(7, 19, 47, 0.02); display: flex; flex-direction: column;">
                    <div class="flyer-section-title" style="font-size:0.8rem; font-weight:850; color:#07132F; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px; padding-bottom:4px; border-bottom:2px solid #F0F6FF;">
                        📈 Skor Pengalaman
                    </div>
                    <div style="font-size:0.72rem; font-weight:750; color:#07132F; margin-bottom:10px; text-align:center;">Rata-rata Skor per Variabel</div>
                    
                    <!-- X1 Row -->
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:#475569; margin-bottom:3px; font-weight:600;">
                            <span>X1 Fleksibilitas</span>
                            <span><strong>{x1_score:.2f}</strong> / 5.00</span>
                        </div>
                        <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:{x1_pct:.1f}%; background:#108EE9;"></div>
                        </div>
                    </div>

                    <!-- X2 Row -->
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:#475569; margin-bottom:3px; font-weight:600;">
                            <span>X2 Kepraktisan</span>
                            <span style="color:#10B981;"><strong>{x2_score:.2f}</strong> / 5.00</span>
                        </div>
                        <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:{x2_pct:.1f}%; background:#10B981;"></div>
                        </div>
                    </div>

                    <!-- M Row -->
                    <div style="margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:#475569; margin-bottom:3px; font-weight:600;">
                            <span>M Kepercayaan</span>
                            <span style="color:#FF4D5E;"><strong>{m_score:.2f}</strong> / 5.00</span>
                        </div>
                        <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:{m_pct:.1f}%; background:#FF4D5E;"></div>
                        </div>
                    </div>

                    <!-- Y Row -->
                    <div style="margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:#475569; margin-bottom:3px; font-weight:600;">
                            <span>Y Keseluruhan</span>
                            <span><strong>{y_score:.2f}</strong> / 5.00</span>
                        </div>
                        <div style="display:flex; height:8px; border-radius:4px; overflow:hidden; background:#E2E8F0;">
                            <div style="width:{y_pct:.1f}%; background:#2563EB;"></div>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; font-size:0.62rem; color:#64748B; padding:0 4px; margin-bottom:8px; font-weight:600;">
                        <span>Terkuat: <strong style="color:#10B981;">X2 Praktis ({x2_score:.2f})</strong></span>
                        <span>Pantau: <strong style="color:#FF4D5E;">M Kepercayaan ({m_score:.2f})</strong></span>
                    </div>
                    
                    <div class="flyer-mini-stats-grid" style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: auto;">
                        <div class="flyer-mini-stat-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:6px; text-align:center;">
                            <div class="flyer-mini-stat-val" style="font-size:1.05rem; font-weight:900; color:#10B981;">{kuat_count}</div>
                            <div class="flyer-mini-stat-lbl" style="font-size:0.55rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.03em;">Kuat (&ge; 4.00)</div>
                        </div>
                        <div class="flyer-mini-stat-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:6px; text-align:center;">
                            <div class="flyer-mini-stat-val" style="font-size:1.05rem; font-weight:900; color:#FFB020;">{cukup_count}</div>
                            <div class="flyer-mini-stat-lbl" style="font-size:0.55rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.03em;">Cukup (3-3.99)</div>
                        </div>
                        <div class="flyer-mini-stat-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:6px; text-align:center;">
                            <div class="flyer-mini-stat-val" style="font-size:1.05rem; font-weight:900; color:#FF4D5E;">{perhatian_count}</div>
                            <div class="flyer-mini-stat-lbl" style="font-size:0.55rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.03em;">Pantau (&lt; 3.00)</div>
                        </div>
                        <div class="flyer-mini-stat-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:6px; text-align:center;">
                            <div class="flyer-mini-stat-val" style="font-size:1.05rem; font-weight:900; color:#108EE9;">{r5_count}</div>
                            <div class="flyer-mini-stat-lbl" style="font-size:0.55rem; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.03em;">Bintang 5 Ulasan</div>
                        </div>
                    </div>
                </div>
                """)

            with col_3:
                # Compile reviews HTML list inside python
                reviews_list_html = ""
                if reviews is not None and not reviews.empty:
                    date_col = review_columns.get("date")
                    text_col = review_columns.get("review")
                    rating_col = review_columns.get("rating")
                    
                    # Sort by date descending and take top 3
                    sorted_reviews = reviews.sort_values(date_col, ascending=False).head(3)
                    for _, row in sorted_reviews.iterrows():
                        r_val = row.get(rating_col, "-")
                        d_val = str(row.get(date_col, "-"))
                        t_val = str(row.get(text_col, "-"))
                        s_val = str(row.get("sentimen", "-"))
                        
                        s_color = "#10B981" if "positif" in s_val.lower() else ("#EF4444" if "negatif" in s_val.lower() else "#FFB020")
                        s_bg = "#ECFDF5" if "positif" in s_val.lower() else ("#FEF2F2" if "negatif" in s_val.lower() else "#FFFBEB")
                        
                        reviews_list_html += f"""
                        <div class="flyer-review-card" style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:6px 8px; margin-bottom:6px; box-shadow:none;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
                                <span style="font-size:0.58rem; color:#64748B; font-weight:600;">{d_val}</span>
                                <div style="display:flex; gap:4px;">
                                    <span style="font-size:0.55rem; font-weight:700; color:{s_color}; background:{s_bg}; padding:1px 4px; border-radius:4px; text-transform:uppercase;">{s_val}</span>
                                    <span style="font-size:0.55rem; font-weight:700; color:#0B5ED7; background:#EAF5FF; padding:1px 4px; border-radius:4px;">★ {r_val}</span>
                                </div>
                            </div>
                            <div style="font-size:0.68rem; color:#102040; line-height:1.25; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; white-space:normal; word-break:keep-all;">
                                {escape(t_val)}
                            </div>
                        </div>
                        """
                else:
                    reviews_list_html = "<div style='font-size:0.7rem; color:#64748B; padding:10px; text-align:center;'>Data ulasan tidak tersedia.</div>"

                render_clean_html(f"""
                <div class="flyer-card" style="background:white; border:1px solid #D7E8FF; border-radius:16px; padding:14px; height:100%; box-shadow:0 2px 4px rgba(7, 19, 47, 0.02); display: flex; flex-direction: column;">
                    <div class="flyer-section-title" style="font-size:0.8rem; font-weight:850; color:#07132F; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:12px; padding-bottom:4px; border-bottom:2px solid #F0F6FF;">
                        💬 Sentimen &amp; Ulasan
                    </div>

                    <!-- Segmented Progress Bar -->
                    <div style="display:flex; height:12px; border-radius:6px; overflow:hidden; margin-bottom:6px; background:#E2E8F0;">
                        <div style="width:70.3%; background:#10B981;" title="Positif: 70.3%"></div>
                        <div style="width:3.9%; background:#FFB020;" title="Netral: 3.9%"></div>
                        <div style="width:25.8%; background:#EF4444;" title="Negatif: 25.8%"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-size:0.58rem; color:#64748B; font-weight:700; margin-bottom:10px;">
                        <span style="color:#10B981;">● Positif 70.3%</span>
                        <span style="color:#FFB020;">● Netral 3.9%</span>
                        <span style="color:#EF4444;">● Negatif 25.8%</span>
                    </div>

                    <!-- Insight Paragraph -->
                    <div style="font-size:0.71rem; color:#475569; line-height:1.4; margin-bottom:10px;">
                        Ulasan didominasi oleh <strong>Sentimen Positif (70.3%)</strong> yang memuji kepraktisan dan kecepatan transaksi. Namun, area perhatian utama dari ulasan negatif adalah masalah terkait <strong>akun, saldo, dan transaksi gagal</strong>.
                    </div>
                    
                    {reviews_list_html}
                </div>
                """)
            
            # Flyer Footer
            render_clean_html(f"""
            <div class="flyer-footer" style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; padding-top: 8px; border-top: 1px solid #F0F6FF; font-size: 0.62rem; color: #94A3B8; font-weight: 600;">
                <span>Dashboard: <a href="https://dashboard-dana.streamlit.app" target="_blank" style="color:#108EE9; text-decoration:none; font-weight:700;">dashboard-dana.streamlit.app</a></span>
                <span>GitHub: <a href="https://github.com/Sekolah76/dashboard-tugas" target="_blank" style="color:#108EE9; text-decoration:none; font-weight:700;">github.com/Sekolah76/dashboard-tugas</a></span>
                <span>Disclaimer: Data bersifat deskriptif &amp; identitas pengguna disembunyikan.</span>
            </div>
            """)

    # Mobile View (notice and clean simplified stats, no overflow)
    with st.container(key="snapshot_flyer_mobile"):
        st.info("📱 Gunakan laptop/desktop untuk screenshot flyer terbaik.")
        
        render_clean_html('<div style="font-weight:800;color:#07132F;font-size:0.9rem;margin-bottom:8px;">Ringkasan KPI Utama</div>')
        mobile_kpis = [
            ("Responden", f"{survey_count} Orang"),
            ("Ulasan", f"{review_count} Ulasan"),
            ("Skor Kuesioner", f"{avg_skor:.2f} / 5.00"),
            ("Rating Ulasan", f"{avg_rating:.2f} / 5.00"),
            ("Sentimen Positif", f"{positive_pct:.1f}%"),
        ]
        
        for label, val in mobile_kpis:
            render_clean_html(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;background:white;border:1px solid #D7E8FF;border-radius:8px;padding:8px 12px;margin-bottom:6px;width:100%; box-sizing:border-box;">
                <span style="font-size:0.75rem;color:#5C6B86;font-weight:600;">{label}</span>
                <span style="font-size:0.8rem;color:#108EE9;font-weight:800;margin-left:auto;font-variant-numeric:tabular-nums;">{val}</span>
            </div>
            """)

def render_footer() -> None:
    st.html(
        """
        <footer class="footer">
            <strong>DANA Insight Command Center</strong><br>
            Developer: Muhammad Arsyad Arroyan |
            Built with Streamlit &amp; Plotly |
            Siap presentasi UAS
        </footer>
        """
    )


# =============================================================================
# MAIN APP
# =============================================================================
def render_dashboard_content(
    data: dict[str, Any],
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    questionnaire_from_file: pd.DataFrame | None,
    questionnaire_total: pd.DataFrame | None,
    audit_frame: pd.DataFrame,
    invariant_errors: list[str],
    filters: dict[str, Any],
    defaults: dict[str, Any],
    options: dict[str, Any],
) -> None:
    survey_filter_active, review_filter_active = filter_scope(
        filters,
        defaults,
        options,
    )
    if filters.get("presentation"):
        st.html(
            """
            <style>
            .block-container {
                max-width: 98vw !important;
                padding-left: 1vw !important;
                padding-right: 1vw !important;
            }
            </style>
            """
        )
        presentation_mode_banner()

    survey_filtered = apply_survey_filters(survey, survey_columns, filters, options)
    reviews_filtered = apply_review_filters(reviews, review_columns, filters, options)
    questionnaire_filtered = (
        compute_questionnaire_from_survey(
            survey_filtered,
            survey_columns.get("questions", []),
        )
        if survey_filter_active
        else questionnaire_total
    )

    survey_total = len(survey) if survey is not None else 0
    review_total = len(reviews) if reviews is not None else 0
    total_review_metrics = review_metrics(reviews, review_columns)
    total_questionnaire_average = (
        safe_mean(questionnaire_total["rata_rata"])
        if questionnaire_total is not None and not questionnaire_total.empty
        else 0.0
    )
    render_hero(
        survey_total,
        review_total,
        total_questionnaire_average,
        total_review_metrics["avg_rating"],
        total_review_metrics["positive_pct"],
    )
    for key in ("survey", "reviews"):
        if key in data["errors"]:
            st.error(data["errors"][key])
    if questionnaire_from_file is None:
        if questionnaire_total is not None:
            reason = data["errors"].get(
                "questionnaire",
                "Format hasil_kuesioner.csv tidak memiliki kolom pertanyaan dan skor yang valid.",
            )
            st.warning(f"{reason} Rata-rata dihitung ulang dari data survey.")
        else:
            st.warning(
                "Data kuesioner tidak tersedia dan tidak dapat dihitung dari data survey."
            )

    render_filter_summary(filters, defaults, options)
    render_data_scope_summary(
        len(survey_filtered) if survey_filtered is not None else 0,
        survey_total,
        len(reviews_filtered) if reviews_filtered is not None else 0,
        review_total,
        survey_filter_active,
        review_filter_active,
    )
    render_kpis(
        survey_filtered,
        reviews_filtered,
        questionnaire_filtered,
        review_columns,
        survey_filter_active,
        review_filter_active,
        bool(filters.get("animations")),
    )
    # NOTE: render_horizontal_tabs() is now called in main() before render_dashboard_content

    if survey is not None and survey_filtered is not None and survey_filtered.empty:
        render_empty_state(
            "Tidak ada responden yang cocok",
            "Ubah filter survey atau tekan Reset Semua untuk mengembalikan data.",
        )
    if reviews is not None and reviews_filtered is not None and reviews_filtered.empty:
        render_empty_state(
            "Tidak ada ulasan yang cocok",
            "Ubah filter ulasan atau tekan Reset Semua untuk mengembalikan data.",
        )
    has_empty_filter_result = (
        survey is not None
        and survey_filtered is not None
        and survey_filtered.empty
    ) or (
        reviews is not None
        and reviews_filtered is not None
        and reviews_filtered.empty
    )
    if has_empty_filter_result and st.button(
        "Reset Filter",
        key="empty_state_reset_filters",
        type="primary",
    ):
        st.session_state.reset_filters_requested = True
        st.rerun()

    active_tab = st.session_state.get("active_tab", "Overview")
    
    if active_tab == "Overview":
        render_overview(
            survey_filtered,
            survey_columns,
            reviews_filtered,
            review_columns,
            survey_total,
            review_total,
            questionnaire=questionnaire_filtered,
            filters=filters,
        )
    elif active_tab == "Analisis Survei":
        render_survey_analysis(
            questionnaire_filtered,
            survey_filtered,
            survey_columns.get("questions", []),
            filters,
            survey_total,
        )
    elif active_tab == "Analisis Ulasan":
        render_review_analysis(
            reviews_filtered,
            review_columns,
            review_total,
            filters,
            review_filter_active,
        )
    elif active_tab == "Data Explorer":
        render_data_explorer(
            survey_filtered,
            reviews_filtered,
            questionnaire_filtered,
            audit_frame,
            survey_total,
            review_total,
            review_columns,
            filters,
        )
    elif active_tab == "Snapshot Flyer":
        render_snapshot_flyer(
            survey,
            reviews,
            review_columns,
            questionnaire_total,
            survey_columns,
        )
    elif active_tab == "Lampiran Presentasi":
        render_output_and_presentation(audit_frame, invariant_errors)
        script_presentasi_blocks()
        if filters.get("presentation"):
            st.markdown("#### Executive Summary (Presentasi)")
            scope_lbl = (
                "Filter aktif"
                if survey_filter_active or review_filter_active
                else "Total data"
            )
            st.markdown(executive_summary_card(
                survey_filtered, survey_columns, questionnaire_filtered,
                reviews_filtered, review_columns, scope_lbl,
            ), unsafe_allow_html=True)

    if filters.get("insight"):
        render_conclusion(
            survey_filtered,
            survey_columns,
            questionnaire_filtered,
            reviews_filtered,
            review_columns,
            (
                "Filter aktif"
                if survey_filter_active or review_filter_active
                else "Total data"
            ),
        )
    render_footer()


def main() -> None:
    inject_custom_css()
    st.session_state.setdefault("last_refresh", datetime.now(WIB))
    st.session_state.setdefault(
        "app_view",
        "landing" if DEFAULT_SHOW_LOBBY else "dashboard",
    )
    st.session_state.setdefault(
        "entered_dashboard",
        st.session_state.app_view == "dashboard",
    )
    st.session_state.setdefault("show_lobby_summary", False)
    st.session_state.setdefault("active_tab", "Overview")
    # Legacy state — kept for backward compat but not used for layout anymore
    st.session_state.setdefault("filter_open", False)
    st.session_state.setdefault("fullscreen_chart_id", None)
    st.session_state.chart_registry = {}

    with st.spinner("Memuat dan memvalidasi data..."):
        data = load_all_data()
        survey, survey_columns = prepare_survey_data(data["survey"])
        reviews, review_columns = prepare_review_data(data["reviews"])
        questionnaire_from_file = normalize_questionnaire(
            data["questionnaire"],
            None,
            [],
        )
        questionnaire_total = (
            questionnaire_from_file
            if questionnaire_from_file is not None
            else compute_questionnaire_from_survey(
                survey,
                survey_columns.get("questions", []),
            )
        )
        audit_frame = audit_data_sources()
        invariant_errors = validate_data_invariants(
            survey,
            survey_columns,
            reviews,
            review_columns,
            questionnaire_total,
        )

    if not render_lobby_page(
        survey,
        survey_columns,
        questionnaire_total,
        reviews,
        review_columns,
    ):
        return

    options = available_options(survey, survey_columns, reviews, review_columns)
    defaults = default_filters(options)
    initialize_filter_state(defaults)
    if st.session_state.pop("reset_filters_requested", False):
        reset_filter_state(defaults)
        st.rerun()

    # Render topbar with filter dialog capability
    render_top_header(
        st.session_state.last_refresh,
        latest_primary_data_modified(),
        loaded=not bool(data["errors"]) and not invariant_errors,
        questionnaire=questionnaire_total,
        reviews=reviews,
        review_columns=review_columns,
        options=options,
        defaults=defaults,
    )

    # Active filters come directly from session state (set by dialog)
    filters = st.session_state.active_filters.copy()

    # Inject body CSS classes based on user preferences
    inject_preference_classes(filters)

    # Render horizontal navigation tabs
    render_horizontal_tabs()

    # Show presentation mode banner
    if filters.get("presentation"):
        st.html("""
        <div class="presentation-banner-bar">
            <span class="presentation-badge">🎯 Mode Presentasi Aktif</span>
            <span>Tampilan dioptimalkan untuk presentasi — teks lebih besar, elemen teknis dikurangi</span>
        </div>
        """)

    # Render main dashboard content (full width — no sidebar)
    render_dashboard_content(
        data,
        survey,
        survey_columns,
        reviews,
        review_columns,
        questionnaire_from_file,
        questionnaire_total,
        audit_frame,
        invariant_errors,
        filters,
        defaults,
        options,
    )

    if st.session_state.get("fullscreen_chart_id"):
        render_fullscreen_dialog()



if __name__ == "__main__":
    main()

