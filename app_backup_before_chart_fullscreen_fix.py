from __future__ import annotations

import base64
from collections import Counter
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from html import escape
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
PLOTLY_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "displayModeBar": "hover",
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

SENSITIVE_COLUMN_PHRASES = {
    "nama lengkap", "nama anda", "nama responden", "siapa nama anda",
    "username", "user name", "nama pengguna", "id pengguna", "user id",
    "alamat email", "e mail", "email address",
    "no hp", "nomor hp", "nomor telepon",
}
SENSITIVE_COLUMN_TOKENS = {
    "nama", "name", "email", "phone", "telepon", "handphone",
    "nomor", "kontak", "responden", "username",
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


st.set_page_config(
    page_title="DANA Insight Command Center",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="collapsed",
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

        html, body, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] button,
        [data-testid="stAppViewContainer"] input,
        [data-testid="stAppViewContainer"] textarea,
        [data-testid="stAppViewContainer"] select {{
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
                "Segoe UI", sans-serif;
        }}

        #MainMenu,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        footer {{
            display: none !important;
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

        .lobby-shell {{
            position: relative;
            overflow: hidden;
            min-height: 620px;
            padding: clamp(1.4rem, 4vw, 3.2rem);
            border: 1px solid #BFDBFE;
            border-radius: 32px;
            background:
                radial-gradient(circle at 83% 12%, rgba(56,189,248,.22), transparent 26rem),
                radial-gradient(circle at 8% 92%, rgba(37,99,235,.10), transparent 22rem),
                linear-gradient(145deg, #FFFFFF 0%, #F3F8FF 68%, #EAF5FF 100%);
            box-shadow: 0 24px 70px rgba(15,54,96,.13);
        }}

        .lobby-hero {{
            display: grid;
            grid-template-columns: minmax(0,1.1fr) minmax(320px,.9fr);
            align-items: center;
            gap: clamp(1.5rem, 5vw, 4rem);
        }}

        .lobby-mark {{
            display: flex;
            align-items: center;
            gap: .75rem;
            margin-bottom: 1.4rem;
            color: {C_DEEP};
            font-size: 1.05rem;
            font-weight: 850;
            letter-spacing: .12em;
        }}

        .lobby-mark img {{
            width: 54px;
            height: 54px;
        }}

        .lobby-title {{
            max-width: 760px;
            margin: 0;
            color: {C_TEXT};
            font-size: clamp(2.35rem, 6vw, 4.8rem);
            font-weight: 900;
            letter-spacing: -.055em;
            line-height: .98;
        }}

        .lobby-subtitle {{
            max-width: 700px;
            margin: 1.25rem 0 1.5rem;
            color: #475569;
            font-size: clamp(.95rem, 1.8vw, 1.14rem);
            line-height: 1.7;
        }}

        .lobby-visual img {{
            width: 100%;
            max-height: 380px;
            object-fit: contain;
            filter: drop-shadow(0 24px 34px rgba(11,94,215,.18));
            animation: lobby-float 5.5s ease-in-out infinite;
        }}

        .lobby-metrics {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0,1fr));
            gap: .75rem;
            margin-top: 2rem;
        }}

        .lobby-metric {{
            padding: 1rem;
            border: 1px solid rgba(191,219,254,.92);
            border-radius: 18px;
            background: rgba(255,255,255,.86);
            box-shadow: 0 10px 26px rgba(15,23,42,.05);
        }}

        .lobby-metric strong {{
            display: block;
            color: {C_TEXT};
            font-size: 1.42rem;
            font-weight: 880;
        }}

        .lobby-metric span {{
            display: block;
            margin-top: .18rem;
            color: {C_MUTED};
            font-size: .68rem;
            line-height: 1.35;
        }}

        .lobby-privacy {{
            display: flex;
            align-items: center;
            gap: .85rem;
            margin-top: 1rem;
            padding: .9rem 1rem;
            border: 1px solid #BAE6FD;
            border-radius: 16px;
            color: #075985;
            background: rgba(240,249,255,.88);
            font-size: .76rem;
            line-height: 1.5;
        }}

        .lobby-privacy img {{
            width: 42px;
            height: 42px;
            flex: 0 0 42px;
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
            width: 94px;
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
            width: 94px;
            height: 38px;
        }}

        .brand-mark img {{
            width: 94px;
            height: 38px;
            object-fit: contain;
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
            display: flex;
            align-items: center;
            gap: .75rem;
            margin: 1.1rem 0 .85rem;
        }}

        .section-visual {{
            width: 46px;
            height: 46px;
            flex: 0 0 46px;
            display: grid;
            place-items: center;
            overflow: hidden;
            border: 1px solid #BFDBFE;
            border-radius: 14px;
            background: linear-gradient(145deg, #FFFFFF, #EFF6FF);
            box-shadow: 0 8px 20px rgba(16,142,233,.09);
        }}

        .section-visual svg, .section-visual img {{
            width: 42px;
            height: 42px;
            object-fit: contain;
        }}

        .section-heading-copy {{
            min-width: 0;
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

        .st-key-control_panel {{
            position: sticky;
            top: 6.2rem;
            max-height: calc(100vh - 7rem);
            overflow-y: auto;
            margin-bottom: 1rem;
            padding: 1rem;
            border: 1px solid rgba(255,255,255,.2);
            border-radius: 24px;
            background:
                radial-gradient(circle at 92% 3%, rgba(56,189,248,.35), transparent 15rem),
                linear-gradient(180deg, #0B5ED7 0%, #0749A8 100%);
            box-shadow: 0 18px 38px rgba(11,94,215,.2);
        }}

        .st-key-control_panel label,
        .st-key-control_panel p,
        .st-key-control_panel .control-panel-title,
        .st-key-control_panel .control-panel-note,
        .st-key-control_panel .sidebar-section,
        .st-key-control_panel [data-testid="stCaptionContainer"] {{
            color: white !important;
        }}

        .st-key-control_panel [data-baseweb="select"] > div,
        .st-key-control_panel input,
        .st-key-control_panel textarea {{
            background: rgba(255,255,255,.97) !important;
        }}

        .st-key-control_panel div[data-testid="stButton"] button,
        .st-key-control_panel div[data-testid="stButton"] button p {{
            color: {C_DEEP} !important;
            background: white !important;
        }}

        .st-key-control_panel div[data-testid="stFormSubmitButton"] button,
        .st-key-control_panel div[data-testid="stFormSubmitButton"] button p {{
            color: white !important;
            background: {C_SKY} !important;
        }}

        .control-panel-header {{
            display: flex;
            align-items: center;
            gap: .75rem;
            margin-bottom: .75rem;
        }}

        .control-panel-visual {{
            width: 54px;
            height: 54px;
            flex: 0 0 54px;
        }}

        .control-panel-visual svg, .control-panel-visual img {{
            width: 54px;
            height: 54px;
            object-fit: contain;
        }}

        .hero-wallet-visual {{
            width: 220px;
            max-width: 24vw;
            height: auto;
            filter: drop-shadow(0 14px 26px rgba(3,31,84,.18));
        }}

        .control-panel-title {{
            color: {C_TEXT};
            font-size: 1rem;
            font-weight: 830;
        }}

        .control-panel-note {{
            margin-top: .2rem;
            color: {C_MUTED};
            font-size: .74rem;
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

        .empty-state {{
            display: grid;
            justify-items: center;
            gap: .35rem;
            padding: 1.2rem;
            border: 1px dashed #93C5FD;
            border-radius: 20px;
            color: {C_MUTED};
            text-align: center;
            background: linear-gradient(145deg, #FFFFFF, #F0F9FF);
        }}

        .empty-state img {{
            width: min(280px, 80%);
            max-height: 160px;
            object-fit: contain;
        }}

        .empty-state strong {{
            color: {C_TEXT};
            font-size: .95rem;
        }}

        .audit-ok, .audit-warning, .audit-error {{
            display: inline-flex;
            align-items: center;
            padding: .2rem .5rem;
            border-radius: 999px;
            font-size: .67rem;
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

        .deliverable-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0,1fr));
            gap: .7rem;
        }}

        .deliverable-card {{
            min-height: 108px;
            padding: .9rem;
            border: 1px solid {C_BORDER};
            border-radius: 16px;
            background: white;
        }}

        .deliverable-card strong {{
            display: block;
            margin-bottom: .35rem;
            color: {C_TEXT};
            font-size: .78rem;
        }}

        .deliverable-card span {{
            color: {C_MUTED};
            font-size: .72rem;
            line-height: 1.45;
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

        @keyframes lobby-float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: .01ms !important;
            }}
        }}

        .kpi-grid, .summary-grid-5 {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        .summary-grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        .health-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}

        @media (max-width: 1024px) {{
            .kpi-grid, .summary-grid-5 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
            .summary-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .lobby-hero {{ grid-template-columns: 1fr 320px; }}
            .lobby-metrics {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
            .st-key-top_header .brand-subtitle,
            .st-key-top_header .time-pill.refresh-time {{
                display: none;
            }}
            .st-key-top_header .brand-title {{
                font-size: .88rem;
            }}
            .st-key-top_header .brand-mark img {{
                width: 70px;
            }}
            .st-key-top_header button {{
                padding-left: .38rem !important;
                padding-right: .38rem !important;
            }}
            .st-key-top_header button p {{
                white-space: nowrap;
                font-size: .68rem;
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
            .st-key-control_panel {{
                position: static;
                max-height: none;
                overflow: visible;
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
            .deliverable-grid {{
                grid-template-columns: 1fr;
            }}
            .section-heading {{
                align-items: flex-start;
            }}
            .kpi-card {{
                min-height: 145px;
            }}
            .lobby-shell {{
                min-height: auto;
                padding: 1.3rem;
                border-radius: 24px;
            }}
            .lobby-hero {{
                grid-template-columns: 1fr;
            }}
            .lobby-visual {{
                order: -1;
                max-width: 330px;
                margin: 0 auto;
            }}
            .lobby-title {{
                font-size: clamp(2.1rem, 11vw, 3.6rem);
            }}
            .lobby-metrics {{
                grid-template-columns: repeat(2, minmax(0,1fr));
            }}
        }}

        @media (max-width: 768px) {{
            .kpi-grid, .summary-grid-5, .health-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}

        @media (max-width: 480px) {{
            .kpi-grid, .summary-grid-5, .summary-grid-4, .health-grid {{ grid-template-columns: 1fr; }}
            .hero-stat-row {{ grid-template-columns: 1fr; }}
            .lobby-metrics {{ grid-template-columns: 1fr; }}
        }}
        </style>
        <script>
        (() => {{
            if (window.__danaTabResizeInstalled) return;
            window.__danaTabResizeInstalled = true;
            document.addEventListener("click", (event) => {{
                const tab = event.target.closest('[role="tab"]');
                if (!tab) return;
                [80, 260, 650].forEach((delay) => {{
                    window.setTimeout(
                        () => window.dispatchEvent(new Event("resize")),
                        delay
                    );
                }});
            }});
        }})();
        </script>
        """
        ,
        unsafe_allow_javascript=True,
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


def asset_svg(filename: str, fallback: str = "") -> str:
    path = ASSETS_DIR / filename
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
    svg = asset_svg(filename, fallback)
    if not svg:
        return ""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    class_attr = f' class="{escape(class_name)}"' if class_name else ""
    return (
        f'<img src="data:image/svg+xml;base64,{encoded}" '
        f'alt="{escape(alt)}"{class_attr}/>'
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
    st.html(
        f"""
        <div class="header-status">
            <span class="status-pill{status_class}">
                <span class="status-dot"></span>{status_text}
            </span>
            <span class="time-pill" id="live-clock">--:--:-- WIB</span>
            <span class="time-pill refresh-time">Data updated: {updated_text}</span>
            <span class="time-pill refresh-time">Cache refreshed: {refresh_text}</span>
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
    counts: pd.Series,
    title: str,
    color_map: dict[str, str],
    scope_label: str = "Data tampil",
) -> go.Figure:
    labels = counts.index.astype(str).tolist()
    values = counts.values.tolist()
    total = int(sum(values))
    percentages = [value / total * 100 if total else 0.0 for value in values]
    customdata = [
        [total, f"{percentage:.1f}", scope_label]
        for percentage in percentages
    ]
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
            customdata=customdata,
            hovertemplate=(
                "<b>%{label}</b><br>"
                "%{value} dari %{customdata[0]} %{customdata[2]}<br>"
                "%{customdata[1]}% dari %{customdata[2]}<extra></extra>"
            ),
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
    denominator: int | None = None,
    scope_label: str = "Data tampil",
) -> go.Figure:
    if denominator is not None:
        customdata = [
            [denominator, f"{float(value) / denominator * 100:.1f}" if denominator else "0.0", scope_label]
            for value in values
        ]
        hovertemplate = (
            "<b>%{x}</b><br>%{y} dari %{customdata[0]} %{customdata[2]}<br>"
            "%{customdata[1]}% dari %{customdata[2]}<extra></extra>"
        )
    else:
        customdata = [[scope_label] for _ in values]
        hovertemplate = (
            "<b>%{x}</b><br>Nilai: %{y}<br>"
            "Berdasarkan %{customdata[0]}<extra></extra>"
        )
    figure = go.Figure(
        go.Bar(
            x=labels,
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
    height = max(500, len(ordered) * 29 + 100)
    figure = go.Figure(
        go.Bar(
            x=ordered["rata_rata"],
            y=ordered["label"],
            orientation="h",
            marker={"color": colors},
            customdata=np.column_stack(
                [
                    ordered["pertanyaan"],
                    ordered["kategori"],
                    np.repeat(respondent_count, len(ordered)),
                    np.repeat(scope_label, len(ordered)),
                ]
            ),
            text=ordered["rata_rata"].map(lambda value: f"{value:.2f}"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Pertanyaan: %{customdata[0]}<br>"
                "Rata-rata: <b>%{text}</b><br>"
                "Interpretasi: %{customdata[1]}<br>"
                "Berdasarkan %{customdata[2]} responden (%{customdata[3]})<extra></extra>"
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
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{value:.2f}" for value in values],
            textposition="outside",
            cliponaxis=False,
            customdata=[
                [interpretation, indicator_count, scope_label]
                for interpretation, indicator_count in zip(
                    interpretations,
                    indicator_counts,
                )
            ],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Skor rata-rata: <b>%{text}</b><br>"
                "Interpretasi: %{customdata[0]}<br>"
                "Berdasarkan %{customdata[1]} indikator<br>"
                "Dari %{customdata[2]}<extra></extra>"
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
def render_filter_panel(
    options: dict[str, Any],
    defaults: dict[str, Any],
    load_errors: dict[str, str],
) -> dict[str, Any]:
    if not st.session_state.get("show_filter_panel", True):
        return st.session_state.active_filters.copy()

    with st.container(key="control_panel"):
        st.html(
            f"""
            <div class="control-panel-header">
                <div class="control-panel-visual" aria-hidden="true">
                    {asset_img_tag("filter_illustration.svg", alt="")}
                </div>
                <div>
                    <div class="control-panel-title">Control Panel</div>
                    <div class="control-panel-note">
                        Atur filter penelitian, tampilan tabel, insight, dan mode presentasi.
                        Perubahan statistik diterapkan setelah menekan Apply Filter.
                    </div>
                </div>
            </div>
            """
        )

        action_left, action_right = st.columns(2)
        with action_left:
            if st.button(
                "Reset Semua",
                key="panel_reset_all",
                width="stretch",
                help="Kembalikan seluruh filter",
            ):
                reset_filter_state(defaults)
                st.rerun()
        with action_right:
            if st.button(
                "Refresh Data",
                key="panel_refresh_data",
                width="stretch",
                help="Bersihkan cache data",
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
                "Apply Filter",
                type="primary",
                width="stretch",
            )
            if applied:
                st.session_state.active_filters = collect_draft_filters()
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
    """Return the custom local SVG mark; never use the checkerboard JPEG asset."""
    return asset_img_tag(
        "dana_mark.svg",
        alt="DANA inspired custom mark",
        fallback=DANA_LOGO_SVG,
    )


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


def render_lobby_page(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    questionnaire: pd.DataFrame | None,
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
) -> bool:
    """Render the optional presentation lobby and return True after entry."""
    if st.session_state.get("entered_dashboard", not DEFAULT_SHOW_LOBBY):
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
    visual = asset_img_tag(
        "phone_dashboard_illustration.svg",
        alt="Ilustrasi dashboard dompet digital DANA-inspired",
    )
    shield = asset_img_tag("shield_privacy.svg", alt="")
    metric_items = (
        (f"{survey_total:,}", "Responden anonim"),
        (f"{review_total:,}", "Ulasan pengguna"),
        (f"{indicator_total:,}", "Indikator kuesioner"),
        (f"{questionnaire_average:.2f}", "Skor kuesioner"),
        (f"{metrics['positive_pct']:.1f}%", "Sentimen positif"),
    )
    metric_html = "".join(
        f'<div class="lobby-metric"><strong>{value}</strong><span>{label}</span></div>'
        for value, label in metric_items
    )
    st.html(
        f"""
        <section class="lobby-shell fade-in">
            <div class="lobby-hero">
                <div>
                    <div class="lobby-mark">{logo}<span>DANA INSIGHT</span></div>
                    <h1 class="lobby-title">DANA Insight<br>Command Center</h1>
                    <p class="lobby-subtitle">
                        Dashboard interaktif untuk memahami pengalaman pengguna
                        DANA berdasarkan data survei dan ulasan pengguna.
                    </p>
                    <div class="badge-row">
                        <span class="hero-badge">Profil Responden</span>
                        <span class="hero-badge">20 Indikator</span>
                        <span class="hero-badge">Review Intelligence</span>
                        <span class="hero-badge">Data Explorer Aman</span>
                    </div>
                </div>
                <div class="lobby-visual">{visual}</div>
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

    enter_column, summary_column, spacer = st.columns([1.4, 1.2, 3])
    with enter_column:
        if st.button(
            "Masuk ke Dashboard",
            key="enter_dashboard",
            type="primary",
            width="stretch",
        ):
            st.session_state.entered_dashboard = True
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
    render_footer()
    return False


def render_top_header(
    cache_refresh: datetime,
    data_updated: datetime | None,
    loaded: bool,
) -> None:
    with st.container(key="top_header"):
        filter_column, brand_column, status_column, refresh_column = st.columns(
            [1.1, 4.5, 4.2, 0.9],
            vertical_alignment="center",
        )
        with filter_column:
            panel_open = bool(st.session_state.get("show_filter_panel", True))
            filter_label = "Tutup Filter" if panel_open else "Buka Filter"
            if st.button(
                filter_label,
                key="toggle_filter_panel",
                type="primary" if panel_open else "secondary",
                help="Buka/Tutup Filter",
                width="stretch",
            ):
                st.session_state.show_filter_panel = not panel_open
                st.rerun()
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
            render_live_header(cache_refresh, data_updated, loaded)
        with refresh_column:
            if st.button(
                "Refresh",
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
    wallet_visual = asset_img_tag(
        "wallet_illustration.svg",
        alt="",
        class_name="hero-wallet-visual",
        fallback=DANA_HERO_SVG,
    )
    st.html(
        f"""
        <section class="hero-section fade-in">
            <div class="hero-content">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;">
                    <div style="flex:1;min-width:0;">
                        <div class="eyebrow">
                            Total Data &middot; Fintech Experience Analytics
                        </div>
                        <h1 class="hero-title">DANA Insight<br/>Command Center</h1>
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
                    <div style="flex-shrink:0;opacity:.85;" aria-hidden="true">
                        {wallet_visual}
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
    kpi_html = "".join(kpi_card_html(*card, animate=animate) for card in cards)
    st.html(f'<div class="kpi-grid">{kpi_html}</div>', unsafe_allow_javascript=animate)
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
    grouped["persentase"] = (
        grouped["jumlah"] / denominator * 100 if denominator else 0.0
    ).map(lambda x: f"{x:.1f}")
    grouped["scope"] = scope_label
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
            customdata=np.column_stack(
                [
                    np.repeat(denominator, len(grouped)),
                    grouped["persentase"],
                    grouped["scope"],
                ]
            ),
            hovertemplate=(
                "<b>%{x}</b><br>%{y} dari %{customdata[0]} ulasan<br>"
                "%{customdata[1]}% dari %{customdata[2]}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        **base_layout(
            "Volume Ulasan per Tanggal",
            320,
            xaxis={"showgrid": False, "title": "Tanggal", "type": "category"},
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
    )


def render_overview(
    survey: pd.DataFrame | None,
    survey_columns: dict[str, Any],
    reviews: pd.DataFrame | None,
    review_columns: dict[str, Any],
    survey_total: int,
    review_total: int,
) -> None:
    section_heading(
        "Executive Dashboard",
        "Overview",
        "Ringkasan cepat karakteristik responden dan pengalaman pengguna.",
        "dana_mark.svg",
    )
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
                        survey_scope,
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
                        denominator=len(survey),
                        scope_label=survey_scope,
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
                        denominator=len(survey),
                        scope_label=survey_scope,
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
    section_heading(
        "Survey Experience Score",
        "Analisis Survei",
        "Evaluasi 20 indikator pengalaman pengguna pada skala 1 sampai 5.",
        "survey_illustration.svg",
    )
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
    columns = st.columns(3)
    cards = [
        ("Indikator Kuat / Baik", len(strong), "Skor >= 4.00", C_POSITIVE, C_SOFT_GREEN, "#A7F3D0"),
        ("Indikator Cukup", len(moderate), "Skor 3.00-3.99", C_NEUTRAL, C_SOFT_AMBER, "#FDE68A"),
        ("Perlu Perhatian", len(weak), "Skor < 3.00", C_NEGATIVE, C_SOFT_RED, "#FECACA"),
    ]
    for column, card in zip(columns, cards):
        with column:
            st.html(health_card(*card))

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
    st.info(
        "Catatan akademik: mapping variabel ini masih sementara mengikuti arahan "
        "project. Y - Keseluruhan memakai seluruh Q1-Q20 sehingga overlap dengan "
        "X1, X2, dan M. Sesuaikan mapping dengan operasionalisasi variabel resmi "
        "jika kelompok atau dosen memiliki pembagian indikator yang berbeda."
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
                <h4>Insight otomatis survei &middot; {escape(scope_label)}</h4>
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
                "kategori": st.column_config.TextColumn("Interpretasi", width="medium"),
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
        "review_illustration.svg",
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
                    scope_label,
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
                        denominator=len(reviews),
                        scope_label=scope_label,
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
    section_heading(
        "Privacy-Safe Data",
        "Data Explorer",
        "Eksplorasi data hasil filter tanpa membuka identitas pengguna.",
        "survey_illustration.svg",
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
    st.dataframe(
        audit_frame[
            [column for column in safe_audit_columns if column in audit_frame.columns]
        ],
        width="stretch",
        hide_index=True,
        height=260,
    )
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
        survey_table = add_number_column(survey_view)
        if survey_view.empty:
            render_empty_state(
                "Pencarian survey tidak menemukan hasil",
                "Gunakan kata yang lebih umum atau kosongkan pencarian tabel.",
            )
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
        numbered = add_number_column(review_view)
        limit = table_limit(filters)
        displayed = numbered if limit is None else numbered.head(limit)
        if review_view.empty:
            render_empty_state(
                "Pencarian ulasan tidak menemukan hasil",
                "Gunakan kata yang lebih umum atau kosongkan pencarian tabel.",
            )
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
        public_questionnaire = add_number_column(questionnaire_view)
        if questionnaire_view.empty:
            render_empty_state(
                "Pencarian indikator tidak menemukan hasil",
                "Gunakan kode Q1-Q20 atau potongan teks pertanyaan.",
            )
        st.dataframe(
            public_questionnaire,
            width="stretch",
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "label": st.column_config.TextColumn("Kode", width="small"),
                "pertanyaan": st.column_config.TextColumn("Pertanyaan", width="large"),
                "rata_rata": st.column_config.NumberColumn(
                    "Rata-rata",
                    format="%.2f",
                    width="small",
                ),
            },
        )
        st.download_button(
            "Download hasil kuesioner publik",
            data=convert_df_to_csv(public_questionnaire.drop(columns=["No"])),
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
    section_heading(
        "Submission Readiness",
        "Lampiran Presentasi",
        "Audit sumber data, checklist penyerahan, tautan, dan panduan screenshot UAS.",
        "filter_illustration.svg",
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

    st.markdown("#### Audit sumber data")
    st.dataframe(
        audit_frame,
        width="stretch",
        hide_index=True,
        height=320,
        column_config={
            "Nama Kolom": st.column_config.TextColumn("Nama Kolom", width="large"),
            "Kolom Identitas": st.column_config.TextColumn(
                "Kolom Identitas",
                width="medium",
            ),
            "Status": st.column_config.TextColumn("Status", width="medium"),
        },
    )
    st.caption(
        "Audit hanya menampilkan metadata. Nilai nama responden dan username "
        "dari file raw tidak pernah ditampilkan."
    )

    deliverables = [
        ("Dashboard Streamlit", "Tersedia melalui app.py dan siap dijalankan lokal."),
        ("Source Code", "Entry point: app.py. builder.py adalah legacy dan jangan dijalankan."),
        ("Repository GitHub", "Belum dibuat. Pastikan data/raw_* tetap di-ignore."),
        ("Streamlit Cloud", "Belum dideploy. Isi URL setelah deployment berhasil."),
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
    st.html(f'<div class="deliverable-grid">{cards}</div>')

    st.markdown("#### Tautan publik")
    link_left, link_right = st.columns(2)
    with link_left:
        st.text_input(
            "GitHub URL",
            key="presentation_github_url",
            placeholder="Belum tersedia - isi setelah repository dibuat",
        )
    with link_right:
        st.text_input(
            "Streamlit Cloud URL",
            key="presentation_streamlit_url",
            placeholder="Belum tersedia - isi setelah deployment berhasil",
        )
    st.caption(
        "Kolom ini bersifat catatan sesi dan tidak berarti repository atau "
        "deployment sudah dibuat."
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
    st.dataframe(screenshot_frame, width="stretch", hide_index=True)

    st.markdown("#### Ringkasan fitur")
    st.write(
        "Dashboard memuat profil responden, 20 indikator kuesioner, analisis "
        "variabel X1/X2/M/Y, hasil web scraping ulasan, filter interaktif, "
        "Plotly hover dengan denominator, data explorer aman, insight otomatis, "
        "audit data, dan kesimpulan penelitian tanpa klaim kausal."
    )


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
            <h4 style="margin-bottom:0.5rem;font-size:1.05rem;">Ringkasan Analitis &middot; {escape(scope_label)}</h4>
            
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

    tabs = st.tabs(
        [
            "Overview",
            "Analisis Survei",
            "Analisis Ulasan",
            "Data Explorer",
            "Lampiran Presentasi",
        ]
    )
    with tabs[0]:
        render_overview(
            survey_filtered,
            survey_columns,
            reviews_filtered,
            review_columns,
            survey_total,
            review_total,
        )
    with tabs[1]:
        render_survey_analysis(
            questionnaire_filtered,
            survey_filtered,
            survey_columns.get("questions", []),
            filters,
            survey_total,
        )
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
            questionnaire_filtered,
            audit_frame,
            survey_total,
            review_total,
            review_columns,
            filters,
        )
    with tabs[4]:
        render_output_and_presentation(audit_frame, invariant_errors)

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
    st.session_state.setdefault("show_filter_panel", True)
    st.session_state.setdefault("entered_dashboard", not DEFAULT_SHOW_LOBBY)
    st.session_state.setdefault("show_lobby_summary", False)

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
    render_top_header(
        st.session_state.last_refresh,
        latest_primary_data_modified(),
        loaded=not bool(data["errors"]) and not invariant_errors,
    )

    if st.session_state.get("show_filter_panel", True):
        filter_area, dashboard_area = st.columns(
            [0.24, 0.76],
            gap="large",
            vertical_alignment="top",
        )
        with filter_area:
            filters = render_filter_panel(options, defaults, data["errors"])
    else:
        filters = st.session_state.active_filters.copy()
        dashboard_area = st.container()

    with dashboard_area:
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


if __name__ == "__main__":
    main()
