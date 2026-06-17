from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
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

SURVEY_PATH = DATA_DIR / "survey_clean.xlsx"
REVIEW_PATH = DATA_DIR / "ulasan_clean.xlsx"
QUESTIONNAIRE_PATH = DATA_DIR / "hasil_kuesioner.csv"


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
PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}

STOPWORDS_ID = {
    "yang", "dan", "dengan", "untuk", "dari", "ini", "itu", "saya", "kamu",
    "kita", "sudah", "bisa", "tidak", "sangat", "lebih", "pada", "dalam",
    "aplikasi", "app", "apk", "dana", "nya", "lah", "kok", "min", "gan",
    "aja", "banget", "juga", "kalau", "tapi", "karena", "jadi", "lagi",
    "udah", "di", "ke", "ada", "buat", "saat", "belum", "mau", "apa",
    "padahal", "sekali", "orang",
}

SENSITIVE_COLUMN_PATTERNS = {
    "nama", "nama anda", "nama responden", "siapa nama anda",
    "username", "user name", "nama pengguna", "pengguna",
    "email", "alamat email", "e mail",
    "no hp", "nomor hp", "nomor telepon", "telepon", "phone", "handphone",
}


st.set_page_config(
    page_title="DANA Insight Command Center",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# UI HELPERS
# =============================================================================
def inject_custom_css() -> None:
    st.html(
        f"""
        <style>
        :root {{
            --dana-primary: {C_PRIMARY};
            --dana-deep: {C_DEEP};
            --dana-sky: {C_SKY};
            --dana-bg: {C_BG};
            --dana-card: {C_CARD};
            --dana-text: {C_TEXT};
            --dana-muted: {C_MUTED};
            --dana-border: {C_BORDER};
        }}

        html, body, [class*="st-"], [data-testid="stAppViewContainer"] {{
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }}

        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 92% 4%, rgba(56,189,248,.12), transparent 24rem),
                linear-gradient(180deg, #F9FCFF 0%, {C_BG} 100%);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }}

        [data-testid="stSidebar"] {{
            background: rgba(255,255,255,.98);
            border-right: 1px solid {C_BORDER};
        }}

        [data-testid="stSidebar"] .block-container {{
            padding-top: 1.25rem;
        }}

        .st-key-top_header {{
            position: sticky;
            top: .4rem;
            z-index: 999;
            padding: .72rem .9rem;
            margin-bottom: 1rem;
            background: rgba(255,255,255,.92);
            backdrop-filter: blur(18px);
            border: 1px solid rgba(226,232,240,.88);
            border-radius: 18px;
            box-shadow: 0 10px 32px rgba(15,23,42,.07);
        }}

        .brand-lockup {{
            display: flex;
            align-items: center;
            gap: .72rem;
            min-height: 42px;
        }}

        .brand-mark {{
            width: 38px;
            height: 38px;
            display: grid;
            place-items: center;
            border-radius: 12px;
            color: white;
            font-weight: 900;
            font-size: 1.08rem;
            background: linear-gradient(145deg, {C_SKY}, {C_DEEP});
            box-shadow: 0 8px 18px rgba(16,142,233,.25);
            overflow: hidden;
        }}

        .brand-mark svg {{
            width: 26px;
            height: 26px;
        }}

        .brand-title {{
            color: {C_TEXT};
            font-weight: 800;
            font-size: 1rem;
            line-height: 1.15;
        }}

        .brand-subtitle {{
            color: {C_MUTED};
            font-size: .74rem;
            margin-top: .18rem;
        }}

        .header-status {{
            min-height: 42px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            flex-wrap: wrap;
            gap: .45rem;
        }}

        .status-pill, .time-pill {{
            display: inline-flex;
            align-items: center;
            gap: .38rem;
            min-height: 30px;
            padding: .3rem .65rem;
            border-radius: 999px;
            font-size: .7rem;
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
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: currentColor;
            box-shadow: 0 0 0 4px rgba(16,185,129,.12);
            animation: pulse-dot 1.8s ease-in-out infinite;
        }}

        .time-pill {{
            color: #475569;
            background: #F8FAFC;
            border: 1px solid {C_BORDER};
        }}

        .hero-section {{
            position: relative;
            overflow: hidden;
            min-height: 260px;
            margin-bottom: 1.15rem;
            padding: clamp(1.5rem, 4vw, 2.4rem);
            border-radius: 26px;
            color: white;
            background:
                radial-gradient(circle at 85% 20%, rgba(255,255,255,.19), transparent 22%),
                radial-gradient(circle at 72% 110%, rgba(56,189,248,.48), transparent 28%),
                linear-gradient(135deg, {C_PRIMARY} 0%, {C_DEEP} 58%, #0844A4 100%);
            box-shadow: 0 18px 42px rgba(11,94,215,.22);
        }}

        .hero-section::before {{
            content: "";
            position: absolute;
            inset: 0;
            opacity: .18;
            background-image:
                linear-gradient(rgba(255,255,255,.26) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.26) 1px, transparent 1px);
            background-size: 32px 32px;
            mask-image: linear-gradient(90deg, transparent 20%, black 100%);
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
        }}

        .eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            margin-bottom: .85rem;
            padding: .35rem .72rem;
            border: 1px solid rgba(255,255,255,.3);
            border-radius: 999px;
            background: rgba(255,255,255,.13);
            font-size: .7rem;
            font-weight: 750;
            letter-spacing: .06em;
            text-transform: uppercase;
        }}

        .hero-title {{
            max-width: 820px;
            margin: 0;
            font-size: clamp(1.72rem, 4vw, 2.65rem);
            font-weight: 850;
            letter-spacing: -.035em;
            line-height: 1.08;
        }}

        .hero-subtitle {{
            max-width: 760px;
            margin: .75rem 0 1.15rem;
            color: rgba(255,255,255,.88);
            font-size: clamp(.86rem, 1.5vw, 1rem);
            line-height: 1.6;
        }}

        .badge-row, .hero-stat-row, .chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: .52rem;
        }}

        .hero-badge {{
            padding: .34rem .68rem;
            border: 1px solid rgba(255,255,255,.25);
            border-radius: 999px;
            background: rgba(255,255,255,.12);
            font-size: .7rem;
            font-weight: 650;
        }}

        .hero-stat-row {{
            margin-top: 1.25rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(255,255,255,.2);
            gap: clamp(1rem, 3vw, 2.35rem);
        }}

        .hero-stat-value {{
            display: block;
            font-size: 1.18rem;
            font-weight: 820;
        }}

        .hero-stat-label {{
            display: block;
            margin-top: .12rem;
            color: rgba(255,255,255,.72);
            font-size: .64rem;
            font-weight: 650;
            letter-spacing: .06em;
            text-transform: uppercase;
        }}

        .section-heading {{
            margin: 1.1rem 0 .85rem;
        }}

        .section-kicker {{
            color: {C_PRIMARY};
            font-size: .68rem;
            font-weight: 800;
            letter-spacing: .09em;
            text-transform: uppercase;
        }}

        .section-title {{
            margin: .2rem 0 0;
            color: {C_TEXT};
            font-size: clamp(1.15rem, 2vw, 1.45rem);
            font-weight: 820;
            letter-spacing: -.02em;
        }}

        .section-description {{
            margin-top: .3rem;
            color: {C_MUTED};
            font-size: .82rem;
            line-height: 1.55;
        }}

        .kpi-card {{
            position: relative;
            overflow: hidden;
            min-height: 156px;
            padding: 1rem;
            border: 1px solid {C_BORDER};
            border-radius: 20px;
            background: {C_CARD};
            box-shadow: 0 6px 22px rgba(15,23,42,.045);
            transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
        }}

        .kpi-card::after {{
            content: "";
            position: absolute;
            width: 90px;
            height: 90px;
            top: -46px;
            right: -38px;
            border-radius: 50%;
            background: var(--kpi-soft, #EFF6FF);
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            border-color: #BFDBFE;
            box-shadow: 0 16px 34px rgba(16,142,233,.11);
        }}

        .kpi-top {{
            position: relative;
            z-index: 1;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .6rem;
        }}

        .icon-box {{
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 11px;
            color: var(--kpi-color, {C_PRIMARY});
            background: var(--kpi-soft, #EFF6FF);
        }}

        .icon-box svg {{
            width: 18px;
            height: 18px;
            stroke: currentColor;
        }}

        .kpi-label {{
            color: {C_MUTED};
            font-size: .63rem;
            font-weight: 800;
            letter-spacing: .075em;
            text-transform: uppercase;
            text-align: right;
        }}

        .kpi-value {{
            margin-top: .78rem;
            color: {C_TEXT};
            font-size: 1.82rem;
            font-weight: 850;
            letter-spacing: -.04em;
            line-height: 1;
        }}

        .kpi-caption {{
            min-height: 1.2rem;
            margin-top: .48rem;
            color: {C_MUTED};
            font-size: .69rem;
        }}

        .progress-track {{
            height: 6px;
            margin-top: .75rem;
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

        [class*="st-key-chart_"], [class*="st-key-panel_"] {{
            border: 1px solid {C_BORDER};
            border-radius: 20px;
            background: {C_CARD};
            box-shadow: 0 6px 22px rgba(15,23,42,.04);
            transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
        }}

        [class*="st-key-chart_"]:hover, [class*="st-key-panel_"]:hover {{
            transform: translateY(-2px);
            border-color: #CBDCF3;
            box-shadow: 0 13px 28px rgba(16,142,233,.08);
        }}

        .summary-card {{
            min-height: 122px;
            padding: 1rem;
            border: 1px solid {C_BORDER};
            border-radius: 18px;
            background: {C_CARD};
            box-shadow: 0 5px 18px rgba(15,23,42,.035);
        }}

        .summary-label {{
            color: {C_MUTED};
            font-size: .68rem;
            font-weight: 750;
            letter-spacing: .05em;
            text-transform: uppercase;
        }}

        .summary-value {{
            margin-top: .55rem;
            color: {C_TEXT};
            font-size: 1.15rem;
            font-weight: 820;
            line-height: 1.3;
        }}

        .summary-note {{
            margin-top: .3rem;
            color: {C_MUTED};
            font-size: .7rem;
        }}

        .health-card {{
            min-height: 138px;
            padding: 1rem;
            border: 1px solid var(--health-border);
            border-radius: 18px;
            background: var(--health-bg);
        }}

        .health-count {{
            margin: .52rem 0 .2rem;
            color: var(--health-color);
            font-size: 2rem;
            font-weight: 850;
            line-height: 1;
        }}

        .health-title {{
            color: var(--health-color);
            font-size: .78rem;
            font-weight: 800;
        }}

        .health-note {{
            color: #64748B;
            font-size: .69rem;
        }}

        .rank-card {{
            display: grid;
            grid-template-columns: 32px minmax(0,1fr) auto;
            gap: .7rem;
            align-items: center;
            margin-bottom: .55rem;
            padding: .75rem .82rem;
            border: 1px solid {C_BORDER};
            border-radius: 14px;
            background: white;
        }}

        .rank-number {{
            width: 30px;
            height: 30px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            color: var(--rank-color);
            background: var(--rank-soft);
            font-size: .72rem;
            font-weight: 850;
        }}

        .rank-question {{
            color: #334155;
            font-size: .77rem;
            line-height: 1.4;
        }}

        .rank-score {{
            color: var(--rank-color);
            font-size: .88rem;
            font-weight: 850;
        }}

        .filter-summary {{
            display: flex;
            align-items: flex-start;
            gap: .6rem;
            margin: .15rem 0 1rem;
            padding: .8rem .95rem;
            border: 1px solid #BFDBFE;
            border-radius: 14px;
            color: #1E40AF;
            background: #EFF6FF;
            font-size: .78rem;
            line-height: 1.55;
        }}

        .filter-summary.is-empty {{
            color: {C_MUTED};
            border-color: {C_BORDER};
            background: #F8FAFC;
        }}

        .filter-chip, .keyword-chip {{
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            padding: .32rem .62rem;
            border-radius: 999px;
            font-size: .68rem;
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
            min-width: 20px;
            height: 20px;
            padding: 0 .28rem;
            border-radius: 999px;
            color: white;
            background: {C_ELECTRIC};
            font-size: .61rem;
        }}

        .insight-card {{
            padding: 1.05rem 1.15rem;
            border: 1px solid #BFDBFE;
            border-left: 5px solid {C_PRIMARY};
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(239,246,255,.94), rgba(255,255,255,.98));
            box-shadow: 0 8px 24px rgba(16,142,233,.06);
        }}

        .insight-card h4 {{
            margin: 0 0 .5rem;
            color: {C_TEXT};
            font-size: .92rem;
        }}

        .insight-card p, .insight-card li {{
            color: #475569;
            font-size: .78rem;
            line-height: 1.65;
        }}

        .insight-card ul {{
            margin: 0;
            padding-left: 1.1rem;
        }}

        .privacy-note {{
            padding: .85rem 1rem;
            border: 1px solid #BAE6FD;
            border-radius: 14px;
            color: #075985;
            background: #F0F9FF;
            font-size: .76rem;
            line-height: 1.55;
        }}

        .sidebar-brand {{
            margin-bottom: .9rem;
            padding: 1rem;
            border: 1px solid {C_BORDER};
            border-radius: 18px;
            background: linear-gradient(145deg, #FFFFFF, #F3F8FF);
        }}

        .sidebar-title {{
            color: {C_TEXT};
            font-size: 1.05rem;
            font-weight: 830;
        }}

        .sidebar-subtitle {{
            margin-top: .22rem;
            color: {C_MUTED};
            font-size: .75rem;
        }}

        .sidebar-section {{
            margin: .85rem 0 .5rem;
            color: {C_PRIMARY};
            font-size: .66rem;
            font-weight: 820;
            letter-spacing: .08em;
            text-transform: uppercase;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            width: fit-content;
            max-width: 100%;
            gap: .28rem;
            margin-bottom: 1rem;
            padding: .32rem;
            overflow-x: auto;
            border: 1px solid {C_BORDER};
            border-radius: 999px;
            background: #EDF5FF;
        }}

        .stTabs [data-baseweb="tab"] {{
            min-height: 38px;
            padding: .4rem .85rem;
            border-radius: 999px;
            color: {C_MUTED};
            font-size: .76rem;
            font-weight: 750;
        }}

        .stTabs [aria-selected="true"] {{
            color: {C_DEEP} !important;
            background: white !important;
            box-shadow: 0 5px 14px rgba(16,142,233,.13);
        }}

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {{
            min-height: 40px;
            border-radius: 12px;
            font-weight: 730;
        }}

        .footer {{
            margin-top: 2.4rem;
            padding-top: 1.2rem;
            border-top: 1px solid {C_BORDER};
            color: #94A3B8;
            text-align: center;
            font-size: .71rem;
            line-height: 1.6;
        }}

        .fade-in {{ animation: fade-in .55s cubic-bezier(.16,1,.3,1) both; }}
        .fade-up {{ animation: fade-up .62s cubic-bezier(.16,1,.3,1) both; }}
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
            from {{ opacity: 0; transform: translateY(14px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes grow-bar {{
            from {{ transform: scaleX(0); }}
            to {{ transform: scaleX(1); }}
        }}

        @keyframes pulse-dot {{
            0%, 100% {{ opacity: .55; transform: scale(.92); }}
            50% {{ opacity: 1; transform: scale(1.12); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }}
        }}

        @media (max-width: 800px) {{
            .block-container {{
                padding-left: .8rem;
                padding-right: .8rem;
            }}
            .st-key-top_header {{
                top: .15rem;
                padding: .55rem;
            }}
            .brand-subtitle, .time-pill.refresh-time {{
                display: none;
            }}
            .hero-section {{
                min-height: auto;
                padding: 1.35rem;
                border-radius: 21px;
            }}
            .hero-stat-row {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}
            .kpi-card {{
                min-height: 145px;
            }}
        }}
        </style>
        """
    )


def icon_svg(name: str) -> str:
    paths = {
        "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        "reviews": '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/><path d="M8 8h8M8 12h5"/>',
        "score": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
        "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        "sentiment": '<circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><path d="M9 9h.01M15 9h.01"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
        "refresh": '<path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 4v5h5"/><path d="M4 13a8.1 8.1 0 0 0 15.5 2M20 20v-5h-5"/>',
    }
    body = paths.get(name, paths["score"])
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


def section_heading(kicker: str, title: str, description: str = "") -> None:
    st.html(
        f"""
        <div class="section-heading fade-up">
            <div class="section-kicker">{escape(kicker)}</div>
            <h2 class="section-title">{escape(title)}</h2>
            {f'<div class="section-description">{escape(description)}</div>' if description else ''}
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


def render_live_header(last_refresh: datetime, loaded: bool) -> None:
    status_class = "" if loaded else " is-error"
    status_text = "Data Loaded" if loaded else "Periksa Data"
    refresh_text = escape(format_wib(last_refresh))
    st.html(
        f"""
        <div class="header-status">
            <span class="status-pill{status_class}">
                <span class="status-dot"></span>{status_text}
            </span>
            <span class="time-pill" id="live-clock">--:--:-- WIB</span>
            <span class="time-pill refresh-time">Refresh: {refresh_text}</span>
        </div>
        <script>
        (() => {{
            const clock = document.getElementById("live-clock");
            if (!clock) return;
            const update = () => {{
                const time = new Intl.DateTimeFormat("id-ID", {{
                    timeZone: "Asia/Jakarta",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false
                }}).format(new Date());
                clock.textContent = time.replaceAll(".", ":") + " WIB";
            }};
            update();
            window.setInterval(update, 1000);
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
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


def normalized_column_name(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value).casefold())
    return re.sub(r"\s+", " ", text).strip()


def is_sensitive_column(column: Any) -> bool:
    normalized = normalized_column_name(column)
    if normalized in SENSITIVE_COLUMN_PATTERNS:
        return True
    return any(
        re.search(rf"(?:^|\s){re.escape(pattern)}(?:$|\s)", normalized)
        for pattern in (
            "nama responden", "siapa nama anda", "nama pengguna",
            "alamat email", "nomor telepon", "nomor hp",
        )
    )


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
        "insight": True,
        "animations": True,
        "presentation": False,
    }


def initialize_filter_state(defaults: dict[str, Any]) -> None:
    if "active_filters" not in st.session_state:
        st.session_state.active_filters = defaults.copy()
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
        "draft_insight": defaults["insight"],
        "draft_animations": defaults["animations"],
        "draft_presentation": defaults["presentation"],
    }
    for key, value in widget_map.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
        "draft_insight": "insight",
        "draft_animations": "animations",
        "draft_presentation": "presentation",
    }
    for widget_key, filter_key in mapping.items():
        st.session_state[widget_key] = defaults[filter_key]


def date_range_is_active(
    selected: tuple[date, date] | list[date] | None,
    full_range: tuple[date, date] | None,
) -> bool:
    if selected is None or full_range is None:
        return False
    return tuple(selected) != tuple(full_range)


def filter_scope(
    filters: dict[str, Any], defaults: dict[str, Any]
) -> tuple[bool, bool]:
    survey_active = bool(
        filters["gender"]
        or filters["age"]
        or filters["frequency"]
        or date_range_is_active(filters["survey_dates"], defaults["survey_dates"])
    )
    review_active = bool(
        filters["rating"]
        or filters["sentiment"]
        or filters["keyword"]
        or date_range_is_active(filters["review_dates"], defaults["review_dates"])
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
        column = columns.get(column_key)
        if selected and column and column in filtered.columns:
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
) -> pd.DataFrame | None:
    if reviews is None:
        return None
    filtered = reviews.copy()
    rating_column = columns.get("rating")
    if filters.get("rating") and rating_column in filtered.columns:
        filtered = filtered[filtered[rating_column].isin(filters["rating"])]
    if filters.get("sentiment") and "sentimen" in filtered.columns:
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


def base_layout(title: str, height: int = 330, **overrides: Any) -> dict[str, Any]:
    layout: dict[str, Any] = {
        "title": {
            "text": f"<b>{escape(title)}</b>",
            "x": 0.02,
            "y": 0.96,
            "font": {"size": 14, "color": C_TEXT},
        },
        "template": "plotly_white",
        "height": height,
        "margin": {"t": 55, "b": 32, "l": 28, "r": 24},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#475569"},
        "hoverlabel": {"bgcolor": "#0F172A", "font_color": "white"},
        "transition": {"duration": 500, "easing": "cubic-in-out"},
    }
    layout.update(overrides)
    return layout


def donut_chart(
    counts: pd.Series, title: str, color_map: dict[str, str]
) -> go.Figure:
    labels = counts.index.astype(str).tolist()
    values = counts.values.tolist()
    colors = [color_map.get(label, C_SKY) for label in labels]
    figure = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            sort=False,
            textinfo="label+percent",
            textfont={"size": 11},
            marker={"colors": colors, "line": {"color": "white", "width": 2}},
            hovertemplate="<b>%{label}</b><br>Jumlah: %{value}<br>Proporsi: %{percent}<extra></extra>",
        )
    )
    figure.update_layout(
        **base_layout(
            title,
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
    return figure


def bar_chart(
    labels: list[Any],
    values: list[Any],
    title: str,
    color: str | list[str] = C_PRIMARY,
    x_title: str = "",
    y_title: str = "Jumlah",
    height: int = 330,
) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker={"color": color, "line": {"width": 0}},
            text=values,
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{x}</b><br>Jumlah: %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        **base_layout(
            title,
            height,
            xaxis={"title": x_title, "showgrid": False},
            yaxis={"title": y_title, "gridcolor": "#EAF0F7", "rangemode": "tozero"},
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


def questionnaire_chart(questionnaire: pd.DataFrame) -> go.Figure:
    ordered = questionnaire.sort_values("rata_rata", ascending=True).copy()
    colors = [
        C_POSITIVE if value >= 4 else C_NEUTRAL if value >= 3 else C_NEGATIVE
        for value in ordered["rata_rata"]
    ]
    height = max(500, len(ordered) * 29 + 100)
    figure = go.Figure(
        go.Bar(
            x=ordered["rata_rata"],
            y=ordered["label"],
            orientation="h",
            marker={"color": colors},
            customdata=ordered["pertanyaan"],
            text=ordered["rata_rata"].map(lambda value: f"{value:.2f}"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>%{customdata}<br>"
                "Rata-rata: <b>%{x:.2f}</b><extra></extra>"
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
            },
            yaxis={"title": "", "showgrid": False},
            margin={"t": 55, "b": 38, "l": 55, "r": 48},
            showlegend=False,
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


def plot_chart(figure: go.Figure, key: str) -> None:
    st.plotly_chart(
        figure,
        width="stretch",
        theme=None,
        config=PLOTLY_CONFIG,
        key=key,
    )


# =============================================================================
# DASHBOARD COMPONENTS
# =============================================================================
def render_sidebar(
    options: dict[str, Any],
    defaults: dict[str, Any],
    load_errors: dict[str, str],
) -> dict[str, Any]:
    with st.sidebar:
        st.html(
            """
            <div class="sidebar-brand">
                <div class="sidebar-title">Control Panel</div>
                <div class="sidebar-subtitle">Atur filter dan preferensi dashboard.</div>
            </div>
            """
        )

        action_left, action_right = st.columns(2)
        with action_left:
            if st.button("Reset Semua", width="stretch", help="Kembalikan seluruh filter"):
                reset_filter_state(defaults)
                st.rerun()
        with action_right:
            if st.button("Refresh Data", width="stretch", help="Bersihkan cache data"):
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

            st.html('<div class="sidebar-section">Tampilan</div>')
            st.selectbox(
                "Jumlah baris tabel",
                options=["10", "25", "50", "100", "Semua"],
                key="draft_limit",
            )
            st.toggle("Insight otomatis", key="draft_insight")
            st.toggle("Animasi dashboard", key="draft_animations")
            st.toggle("Mode presentasi", key="draft_presentation")

            applied = st.form_submit_button(
                "Apply Filter",
                type="primary",
                width="stretch",
            )
            if applied:
                st.session_state.active_filters = collect_draft_filters()
                st.rerun()

        if load_errors:
            with st.expander("Status data"):
                for message in load_errors.values():
                    st.warning(message)
        else:
            st.caption("Semua sumber data berhasil dimuat.")

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
    """Return an <img> tag with the logo encoded as base64, or fallback to SVG."""
    import base64
    logo_path = BASE_DIR / "dana_logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/png;base64,{data}" width="38" height="38" style="border-radius:10px;display:block;"/>'
    return DANA_LOGO_SVG


def render_top_header(last_refresh: datetime, loaded: bool) -> None:
    with st.container(key="top_header"):
        brand_column, status_column, refresh_column = st.columns(
            [5.5, 4.3, 0.6], vertical_alignment="center"
        )
        with brand_column:
            logo_html = _logo_img_tag()
            st.html(
                f"""
                <div class="brand-lockup">
                    <div class="brand-mark" style="padding:0;background:none;box-shadow:none;">{logo_html}</div>
                    <div>
                        <div class="brand-title">DANA Insight Command Center</div>
                        <div class="brand-subtitle">Survey &amp; Review Analytics &mdash; Fintech Experience Dashboard</div>
                    </div>
                </div>
                """
            )
        with status_column:
            render_live_header(last_refresh, loaded)
        with refresh_column:
            if st.button(
                "↻",
                key="top_refresh_btn",
                help="Refresh Data dan bersihkan cache",
                width="stretch",
            ):
                st.cache_data.clear()
                st.session_state.last_refresh = datetime.now(WIB)
                st.rerun()



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
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;">
                    <div style="flex:1;min-width:0;">
                        <div class="eyebrow">
                            <span style="margin-right:.4rem;">&#9889;</span>
                            Fintech Experience Analytics
                        </div>
                        <h1 class="hero-title">DANA Insight<br/>Command Center</h1>
                        <p class="hero-subtitle">
                            Dashboard interaktif untuk memahami pola penggunaan,
                            skor pengalaman, rating, dan sentimen pengguna aplikasi DANA.
                        </p>
                        <div class="badge-row">
                            <span class="hero-badge">&#128100; {survey_total:,} Responden</span>
                            <span class="hero-badge">&#128172; {review_total:,} Ulasan</span>
                            <span class="hero-badge">&#129302; AI Sentiment</span>
                            <span class="hero-badge">&#127881; Interactive</span>
                        </div>
                    </div>
                    <div style="flex-shrink:0;opacity:.85;" aria-hidden="true">
                        {DANA_HERO_SVG}
                    </div>
                </div>
                <div class="hero-stat-row">
                    <div>
                        <span class="hero-stat-value">{survey_total:,}</span>
                        <span class="hero-stat-label">Responden Total</span>
                    </div>
                    <div>
                        <span class="hero-stat-value">{review_total:,}</span>
                        <span class="hero-stat-label">Ulasan Total</span>
                    </div>
                    <div>
                        <span class="hero-stat-value">{questionnaire_average:.2f}</span>
                        <span class="hero-stat-label">Skor Rata-rata</span>
                    </div>
                    <div>
                        <span class="hero-stat-value">{review_average:.2f} / 5</span>
                        <span class="hero-stat-label">Rating Rata-rata</span>
                    </div>
                    <div>
                        <span class="hero-stat-value">{positive_percentage:.1f}%</span>
                        <span class="hero-stat-label">Sentimen Positif</span>
                    </div>
                </div>
            </div>
        </section>
        """
    )


def active_filter_chips(
    filters: dict[str, Any], defaults: dict[str, Any]
) -> list[str]:
    chips: list[str] = []
    if filters["gender"]:
        chips.append(f"Gender: {', '.join(map(str, filters['gender']))}")
    if filters["age"]:
        chips.append(f"Usia: {', '.join(map(str, filters['age']))}")
    if filters["frequency"]:
        chips.append(f"Frekuensi: {', '.join(map(str, filters['frequency']))}")
    if date_range_is_active(filters["survey_dates"], defaults["survey_dates"]):
        chips.append(
            f"Survey: {filters['survey_dates'][0]} s.d. {filters['survey_dates'][1]}"
        )
    if filters["sentiment"]:
        chips.append(f"Sentimen: {', '.join(map(str, filters['sentiment']))}")
    if filters["rating"]:
        chips.append(f"Rating: {', '.join(map(str, filters['rating']))}")
    if date_range_is_active(filters["review_dates"], defaults["review_dates"]):
        chips.append(
            f"Ulasan: {filters['review_dates'][0]} s.d. {filters['review_dates'][1]}"
        )
    if filters["keyword"]:
        chips.append(f'Kata kunci: "{filters["keyword"]}"')
    return chips


def render_filter_summary(filters: dict[str, Any], defaults: dict[str, Any]) -> None:
    chips = active_filter_chips(filters, defaults)
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
            f'<div class="progress-fill" style="--progress:{bounded:.1f}%"></div>'
            "</div>"
        )
    value_html = escape(display_value)
    script = ""
    if animate:
        value_html = "0"
        script = f"""
        <script>
        (() => {{
            const element = document.getElementById("{identifier}");
            if (!element || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {{
                if (element) element.textContent = "{escape(display_value)}";
                return;
            }}
            const target = {float(value)};
            const duration = 950;
            const started = performance.now();
            const format = (number) => number.toLocaleString("id-ID", {{
                minimumFractionDigits: {decimals},
                maximumFractionDigits: {decimals}
            }}) + "{escape(suffix)}";
            const tick = (now) => {{
                const progress = Math.min((now - started) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                element.textContent = format(target * eased);
                if (progress < 1) requestAnimationFrame(tick);
            }};
            requestAnimationFrame(tick);
        }})();
        </script>
        """
    return f"""
    <div class="kpi-card" style="--kpi-color:{color};--kpi-soft:{soft_color}">
        <div class="kpi-top">
            <div class="icon-box">{icon_svg(icon)}</div>
            <div class="kpi-label">{escape(label)}</div>
        </div>
        <div class="kpi-value" id="{identifier}">{value_html}</div>
        <div class="kpi-caption">{escape(caption)}</div>
        {progress_html}
    </div>
    {script}
    """


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
    survey_caption = "berdasarkan filter aktif" if survey_filtered else "data total"
    review_caption = "berdasarkan filter aktif" if review_filtered else "data total"
    positive_label = "Positif Filter Aktif" if review_filtered else "Sentimen Positif"

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
    columns = st.columns(5)
    for column, card in zip(columns, cards):
        with column:
            st.html(
                kpi_card_html(*card, animate=animate),
                unsafe_allow_javascript=animate,
            )
    if review_filtered:
        st.caption("Angka ulasan berubah karena filter aktif.")


def summary_card(label: str, value: str, note: str = "") -> str:
    return f"""
    <div class="summary-card fade-up">
        <div class="summary-label">{escape(label)}</div>
        <div class="summary-value">{escape(value)}</div>
        {f'<div class="summary-note">{escape(note)}</div>' if note else ''}
    </div>
    """


def review_trend_chart(reviews: pd.DataFrame, date_column: str) -> go.Figure:
    """Create review trend chart — auto-selects hourly vs daily granularity."""
    source = reviews.dropna(subset=[date_column]).copy()
    dates = pd.to_datetime(source[date_column], errors="coerce").dropna()
    if dates.empty:
        return go.Figure()
    unique_days = dates.dt.date.nunique()
    if unique_days <= 3:
        # Use hourly granularity when data spans only a few days
        source["periode"] = dates.dt.floor("h")
        grouped = (
            source.groupby("periode")
            .size()
            .reset_index(name="jumlah")
            .sort_values("periode")
        )
        title = "Tren Ulasan per Jam"
        x_label = "Jam"
    else:
        source["periode"] = dates.dt.date
        grouped = (
            source.groupby("periode")
            .size()
            .reset_index(name="jumlah")
            .sort_values("periode")
        )
        title = "Tren Ulasan Harian"
        x_label = "Tanggal"
    figure = go.Figure(
        go.Scatter(
            x=grouped["periode"],
            y=grouped["jumlah"],
            mode="lines+markers",
            line={"color": C_PRIMARY, "width": 3, "shape": "spline"},
            marker={"size": 7, "color": C_ELECTRIC, "line": {"color": "white", "width": 1.5}},
            fill="tozeroy",
            fillcolor="rgba(16,142,233,.09)",
            hovertemplate="<b>%{x}</b><br>Jumlah ulasan: %{y}<extra></extra>",
        )
    )
    figure.update_layout(
        **base_layout(
            title,
            320,
            xaxis={"showgrid": False, "title": x_label},
            yaxis={"gridcolor": "#EAF0F7", "title": "Jumlah Ulasan", "rangemode": "tozero"},
            showlegend=False,
        )
    )
    return figure


def render_overview(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> None:
    section_heading(
        "Executive Dashboard",
        "Overview",
        "Ringkasan cepat karakteristik responden dan pengalaman pengguna.",
    )
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

    summary_columns = st.columns(4)
    values = [
        ("Mayoritas Responden", gender_text, "berdasarkan data yang tampil"),
        ("Frekuensi Terbanyak", frequency_text, "pola penggunaan dominan"),
        ("Rating Rata-rata", f"{metrics['avg_rating']:.2f} / 5", "hasil ulasan pengguna"),
        ("Sentimen Dominan", dominant_sentiment, "berdasarkan rating"),
    ]
    for column, item in zip(summary_columns, values):
        with column:
            st.html(summary_card(*item))

    left, right = st.columns(2)
    with left:
        with st.container(key="chart_overview_gender", border=True):
            gender_column = survey_columns.get("gender")
            if survey is not None and not survey.empty and gender_column in survey.columns:
                counts = survey[gender_column].value_counts()
                plot_chart(
                    donut_chart(
                        counts,
                        "Distribusi Gender Responden",
                        {"Perempuan": C_PRIMARY, "Laki-laki": C_SKY},
                    ),
                    "overview_gender",
                )
                st.caption("Proporsi gender responden pada data yang sedang ditampilkan.")
            else:
                st.info("Kolom gender tidak tersedia.")
    with right:
        with st.container(key="chart_overview_frequency", border=True):
            frequency_column = survey_columns.get("frequency")
            if (
                survey is not None
                and not survey.empty
                and frequency_column in survey.columns
            ):
                counts = survey[frequency_column].value_counts()
                plot_chart(
                    bar_chart(
                        counts.index.tolist(),
                        counts.values.tolist(),
                        "Frekuensi Penggunaan DANA",
                        C_PRIMARY,
                    ),
                    "overview_frequency",
                )
                st.caption("Jumlah responden menurut intensitas penggunaan DANA.")
            else:
                st.info("Kolom frekuensi penggunaan tidak tersedia.")

    left, right = st.columns(2)
    with left:
        with st.container(key="chart_overview_age", border=True):
            age_column = survey_columns.get("age")
            if survey is not None and not survey.empty and age_column in survey.columns:
                counts = survey[age_column].value_counts()
                ordered_labels = sorted(counts.index.tolist(), key=age_sort_key)
                ordered_values = [int(counts[label]) for label in ordered_labels]
                plot_chart(
                    bar_chart(
                        ordered_labels,
                        ordered_values,
                        "Distribusi Kelompok Usia",
                        C_ELECTRIC,
                    ),
                    "overview_age",
                )
                st.caption("Usia ditampilkan sebagai kelompok sesuai format dataset.")
            else:
                st.info("Kolom kelompok usia tidak tersedia.")
    with right:
        with st.container(key="chart_overview_trend", border=True):
            date_column = review_columns.get("date")
            if reviews is not None and not reviews.empty and date_column in reviews.columns:
                fig = review_trend_chart(reviews, date_column)
                if fig.data:
                    plot_chart(fig, "overview_trend")
                    unique_days = (
                        pd.to_datetime(reviews[date_column], errors="coerce")
                        .dropna().dt.date.nunique()
                    )
                    if unique_days <= 3:
                        st.caption(
                            f"Data ulasan mencakup {unique_days} hari — "
                            "tren ditampilkan per jam untuk resolusi lebih tinggi."
                        )
                    else:
                        st.caption("Pergerakan volume ulasan per hari pada rentang aktif.")
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


def render_survey_analysis(questionnaire: pd.DataFrame | None) -> None:
    section_heading(
        "Survey Experience Score",
        "Analisis Survei",
        "Evaluasi 20 indikator pengalaman pengguna pada skala 1 sampai 5.",
    )
    if questionnaire is None or questionnaire.empty:
        st.warning(
            "Data kuesioner tidak tersedia. Periksa hasil_kuesioner.csv atau kolom skor survey."
        )
        return

    strong = questionnaire[questionnaire["rata_rata"].ge(4)]
    moderate = questionnaire[
        questionnaire["rata_rata"].ge(3)
        & questionnaire["rata_rata"].lt(4)
    ]
    weak = questionnaire[questionnaire["rata_rata"].lt(3)]
    columns = st.columns(3)
    cards = [
        ("Indikator Kuat / Baik", len(strong), "Skor >= 4.00", C_POSITIVE, C_SOFT_GREEN, "#A7F3D0"),
        ("Indikator Cukup", len(moderate), "Skor 3.00-3.99", C_NEUTRAL, C_SOFT_AMBER, "#FDE68A"),
        ("Perlu Perhatian", len(weak), "Skor < 3.00", C_NEGATIVE, C_SOFT_RED, "#FECACA"),
    ]
    for column, card in zip(columns, cards):
        with column:
            st.html(health_card(*card))

    with st.container(key="chart_survey_scores", border=True):
        plot_chart(questionnaire_chart(questionnaire), "survey_scores")
        st.caption(
            "Semakin panjang bar, semakin baik penilaian. Garis putus-putus menandai batas cukup dan kuat."
        )

    left, right = st.columns(2)
    with left:
        with st.container(key="panel_survey_top", border=True):
            st.markdown("#### Top 5 indikator tertinggi")
            for rank, row in enumerate(
                questionnaire.nlargest(5, "rata_rata").itertuples(), start=1
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
                questionnaire.nsmallest(5, "rata_rata").itertuples(), start=1
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

    average = safe_mean(questionnaire["rata_rata"])
    best = questionnaire.loc[questionnaire["rata_rata"].idxmax()]
    worst = questionnaire.loc[questionnaire["rata_rata"].idxmin()]
    st.html(
        f"""
        <div class="insight-card">
            <h4>Insight otomatis survei</h4>
            <p>
                Rata-rata keseluruhan berada pada <strong>{average:.2f}/5</strong>.
                Indikator tertinggi adalah <strong>{escape(str(best['label']))}</strong>
                ({float(best['rata_rata']):.2f}), sedangkan indikator terendah adalah
                <strong>{escape(str(worst['label']))}</strong>
                ({float(worst['rata_rata']):.2f}). Area dengan skor terendah layak
                menjadi prioritas evaluasi pengalaman pengguna.
            </p>
        </div>
        """
    )

    with st.expander("Daftar lengkap Q1-Q20"):
        full = questionnaire[["label", "pertanyaan", "rata_rata"]].copy()
        full["rata_rata"] = full["rata_rata"].round(2)
        st.dataframe(
            full,
            width="stretch",
            hide_index=True,
            column_config={
                "label": st.column_config.TextColumn("Kode", width="small"),
                "pertanyaan": st.column_config.TextColumn("Pertanyaan", width="large"),
                "rata_rata": st.column_config.NumberColumn(
                    "Rata-rata", format="%.2f", width="small"
                ),
            },
        )


def render_keyword_chips(keywords: list[tuple[str, int]]) -> None:
    if not keywords:
        st.info("Belum ada keyword yang dapat ditampilkan.")
        return
    content = "".join(
        f'<span class="keyword-chip">{escape(word)}'
        f'<span class="chip-count">{count}</span></span>'
        for word, count in keywords
    )
    st.html(f'<div class="chip-row">{content}</div>')


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


def render_review_analysis(
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    review_total: int,
    filters: dict[str, Any],
    review_filter_active: bool,
) -> None:
    section_heading(
        "Review Intelligence",
        "Analisis Ulasan",
        "Sentimen, rating, tren waktu, keyword, dan contoh suara pengguna.",
    )
    if reviews is None or reviews.empty:
        st.info("Tidak ada ulasan yang cocok dengan filter aktif.")
        return

    metrics = review_metrics(reviews, review_columns)
    if review_filter_active:
        st.info(
            f"Menampilkan **{metrics['total']} dari {review_total} ulasan** "
            "berdasarkan filter yang dipilih. Angka berubah karena filter aktif."
        )
    else:
        st.info(f"Menampilkan seluruh **{review_total} ulasan**.")

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
            st.html(summary_card(*item))

    review_column = review_columns.get("review")
    st.markdown("#### Keyword yang sering muncul")
    if review_column and review_column in reviews.columns:
        render_keyword_chips(extract_keywords(reviews[review_column], 15))
    else:
        st.info("Kolom teks ulasan tidak tersedia.")

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
                        [f"{rating} / 5" for rating in counts.index],
                        counts.values.tolist(),
                        "Distribusi Rating",
                        colors,
                    ),
                    "review_rating",
                )
                st.caption("Sebaran rating lengkap pada data ulasan yang tampil.")
            else:
                st.info("Kolom rating tidak tersedia.")

    with st.container(key="chart_review_trend", border=True):
        date_column = review_columns.get("date")
        if date_column and date_column in reviews.columns:
            fig = review_trend_chart(reviews, date_column)
            if fig.data:
                plot_chart(fig, "review_trend")
                unique_days = (
                    pd.to_datetime(reviews[date_column], errors="coerce")
                    .dropna().dt.date.nunique()
                )
                if unique_days <= 3:
                    st.caption(
                        f"Data ulasan mencakup {unique_days} hari — "
                        "tren ditampilkan per jam untuk ketepatan lebih tinggi."
                    )
                else:
                    st.caption("Tren volume ulasan per hari pada rentang aktif.")
            else:
                st.info("Tidak ada tanggal valid untuk membuat tren.")
        else:
            st.info("Kolom tanggal ulasan tidak tersedia.")

    public_reviews = reviews_for_public(reviews, review_columns)
    numbered = add_number_column(public_reviews)
    limit = table_limit(filters)
    displayed = numbered if limit is None else numbered.head(limit)

    st.markdown("#### Tabel ulasan")
    st.dataframe(
        displayed,
        width="stretch",
        height=520,
        hide_index=True,
        column_config={
            "No": st.column_config.NumberColumn("No", width="small"),
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
        },
    )
    st.caption(
        f"Tabel menampilkan {len(displayed)} baris. Download memuat seluruh "
        f"{len(public_reviews)} ulasan hasil filter."
    )
    st.download_button(
        "Download seluruh ulasan hasil filter",
        data=convert_df_to_csv(public_reviews),
        file_name="ulasan_hasil_filter_publik.csv",
        mime="text/csv",
        width="content",
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


def render_data_explorer(
    survey: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    survey_total: int,
    review_total: int,
    review_columns: dict[str, Any],
    filters: dict[str, Any],
) -> None:
    section_heading(
        "Privacy-Safe Data",
        "Data Explorer",
        "Eksplorasi data hasil filter tanpa membuka identitas pengguna.",
    )
    st.html(
        """
        <div class="privacy-note">
            <strong>Privacy note.</strong> Nama responden, username, email, nomor
            telepon, dan kolom identitas serupa tidak ditampilkan. File download
            publik juga tidak memuat identitas pengguna.
        </div>
        """
    )

    st.markdown("#### Data Survey")
    public_survey = sanitize_public_df(survey)
    if public_survey.empty:
        st.info("Data survey tidak tersedia atau filter tidak menghasilkan data.")
    else:
        st.caption(
            f"Total asli: {survey_total} baris | Setelah filter: {len(public_survey)} baris "
            f"| {len(public_survey.columns)} kolom publik"
        )
        survey_table = add_number_column(public_survey)
        st.dataframe(
            survey_table,
            width="stretch",
            height=390,
            hide_index=True,
        )
        st.download_button(
            "Download survey hasil filter",
            data=convert_df_to_csv(public_survey),
            file_name="survey_hasil_filter_publik.csv",
            mime="text/csv",
            width="content",
        )

    st.divider()
    st.markdown("#### Data Ulasan")
    public_reviews = reviews_for_public(reviews, review_columns)
    if public_reviews.empty:
        st.info("Data ulasan tidak tersedia atau filter tidak menghasilkan data.")
    else:
        st.caption(
            f"Total asli: {review_total} ulasan | Setelah filter: "
            f"{len(public_reviews)} ulasan"
        )
        numbered = add_number_column(public_reviews)
        limit = table_limit(filters)
        displayed = numbered if limit is None else numbered.head(limit)
        st.dataframe(
            displayed,
            width="stretch",
            height=440,
            hide_index=True,
        )
        st.download_button(
            "Download ulasan hasil filter",
            data=convert_df_to_csv(public_reviews),
            file_name="ulasan_hasil_filter_publik.csv",
            mime="text/csv",
            width="content",
        )


def render_conclusion(
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> None:
    section_heading(
        "Decision Support",
        "Kesimpulan Utama",
        "Ringkasan otomatis berdasarkan data yang sedang ditampilkan.",
    )
    if questionnaire is None or questionnaire.empty:
        questionnaire_average = 0.0
        best_text = "indikator tertinggi belum tersedia"
        worst_text = "indikator terendah belum tersedia"
    else:
        questionnaire_average = safe_mean(questionnaire["rata_rata"])
        best = questionnaire.loc[questionnaire["rata_rata"].idxmax()]
        worst = questionnaire.loc[questionnaire["rata_rata"].idxmin()]
        best_text = (
            f"{best['label']} ({float(best['rata_rata']):.2f}) - "
            f"{best['pertanyaan']}"
        )
        worst_text = (
            f"{worst['label']} ({float(worst['rata_rata']):.2f}) - "
            f"{worst['pertanyaan']}"
        )

    metrics = review_metrics(reviews, review_columns)
    dominant = "belum tersedia"
    if reviews is not None and not reviews.empty and "sentimen" in reviews.columns:
        counts = reviews["sentimen"].value_counts()
        if not counts.empty:
            dominant = f"{counts.index[0]} ({counts.iloc[0] / len(reviews) * 100:.1f}%)"

    negative_keywords: list[tuple[str, int]] = []
    review_column = review_columns.get("review")
    if (
        reviews is not None
        and not reviews.empty
        and review_column in reviews.columns
        and "sentimen" in reviews.columns
    ):
        negative = reviews[reviews["sentimen"].eq("Negatif")]
        negative_keywords = extract_keywords(negative[review_column], 5)
    keyword_text = (
        ", ".join(f"{word} ({count}x)" for word, count in negative_keywords)
        if negative_keywords
        else "tidak ada keyword negatif dominan pada data aktif"
    )

    st.html(
        f"""
        <div class="insight-card">
            <h4>Ringkasan analitis</h4>
            <ul>
                <li>Pengalaman pengguna memperoleh rata-rata skor
                    <strong>{questionnaire_average:.2f}/5</strong>.</li>
                <li>Rating rata-rata ulasan adalah
                    <strong>{metrics['avg_rating']:.2f}/5</strong>, dengan sentimen
                    dominan <strong>{escape(dominant)}</strong>.</li>
                <li>Kekuatan utama: <strong>{escape(best_text)}</strong>.</li>
                <li>Prioritas perbaikan: <strong>{escape(worst_text)}</strong>.</li>
                <li>Keyword pada ulasan negatif: <strong>{escape(keyword_text)}</strong>.</li>
            </ul>
        </div>
        """
    )


def render_footer() -> None:
    st.html(
        """
        <footer class="footer">
            <strong>DANA Insight Command Center</strong><br>
            Dashboard Developer: Muhammad Arsyad Arroyan |
            Built with Streamlit, pandas, dan Plotly
        </footer>
        """
    )


# =============================================================================
# MAIN APP
# =============================================================================
def main() -> None:
    inject_custom_css()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now(WIB)

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

    options = available_options(survey, survey_columns, reviews, review_columns)
    defaults = default_filters(options)
    initialize_filter_state(defaults)

    render_top_header(
        st.session_state.last_refresh,
        loaded=not bool(data["errors"]),
    )

    filters = render_sidebar(options, defaults, data["errors"])
    survey_filter_active, review_filter_active = filter_scope(filters, defaults)

    if filters.get("presentation"):
        st.html(
            """
            <style>
            .block-container {
                max-width: 96vw !important;
                padding-left: 2vw !important;
                padding-right: 2vw !important;
            }
            </style>
            """
        )

    survey_filtered = apply_survey_filters(survey, survey_columns, filters)
    reviews_filtered = apply_review_filters(reviews, review_columns, filters)

    if survey_filter_active:
        questionnaire_filtered = compute_questionnaire_from_survey(
            survey_filtered,
            survey_columns.get("questions", []),
        )
    else:
        questionnaire_filtered = questionnaire_total

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
    render_filter_summary(filters, defaults)
    render_kpis(
        survey_filtered,
        reviews_filtered,
        questionnaire_filtered,
        review_columns,
        survey_filter_active,
        review_filter_active,
        bool(filters.get("animations")),
    )

    if survey is not None and survey_filtered is not None and survey_filtered.empty:
        st.info("Tidak ada data survey yang cocok dengan filter aktif.")
    if reviews is not None and reviews_filtered is not None and reviews_filtered.empty:
        st.info("Tidak ada data ulasan yang cocok dengan filter aktif.")

    tabs = st.tabs(
        ["Overview", "Analisis Survei", "Analisis Ulasan", "Data Explorer"]
    )
    with tabs[0]:
        render_overview(
            survey_filtered,
            survey_columns,
            reviews_filtered,
            review_columns,
        )
    with tabs[1]:
        render_survey_analysis(questionnaire_filtered)
    with tabs[2]:
        render_review_analysis(
            reviews_filtered,
            review_columns,
            review_total,
            filters,
            review_filter_active,
        )
    with tabs[3]:
        render_data_explorer(
            survey_filtered,
            reviews_filtered,
            survey_total,
            review_total,
            review_columns,
            filters,
        )

    if filters.get("insight"):
        render_conclusion(
            questionnaire_filtered,
            reviews_filtered,
            review_columns,
        )
    render_footer()


if __name__ == "__main__":
    main()
