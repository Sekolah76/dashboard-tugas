# =============================================================================
# Dashboard Analisis Penggunaan Aplikasi DANA
# Developer: Muhammad Arsyad Arroyan
# Built with Streamlit + Plotly
# =============================================================================

from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date
import re
from collections import Counter

# =============================================================================
# PATH SETUP — Selalu relatif terhadap lokasi file app.py
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR  = BASE_DIR / "data"

SURVEY_PATH        = DATA_DIR / "survey_clean.xlsx"
REVIEW_PATH        = DATA_DIR / "ulasan_clean.xlsx"
QUESTIONNAIRE_PATH = DATA_DIR / "hasil_kuesioner.csv"

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="DANA Insight Command Center",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS
# =============================================================================
def inject_custom_css():
    st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background: #F3F8FF; }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(15px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .fade-in { animation: fadeUp 0.5s ease forwards; }

    /* ---- Hero ---- */
    .hero-section {
        background: linear-gradient(135deg, #108EE9 0%, #0B5ED7 100%);
        border-radius: 20px;
        padding: 30px 40px;
        margin-bottom: 25px;
        color: white;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 25px rgba(16, 142, 233, 0.15);
    }
    .hero-section::before {
        content: ''; position: absolute; top: -50px; right: -50px;
        width: 200px; height: 200px; border-radius: 50%;
        background: rgba(255,255,255,0.08);
    }
    .hero-section::after {
        content: ''; position: absolute; bottom: -80px; left: -20px;
        width: 250px; height: 250px; border-radius: 50%;
        background: rgba(255,255,255,0.05);
    }
    .hero-title {
        font-size: 2rem; font-weight: 800; margin: 0 0 8px 0; line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 0.95rem; font-weight: 400; opacity: 0.9; margin: 0 0 20px 0; max-width: 700px;
    }
    .badge-container { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
    .hero-badge {
        background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4);
        color: white; padding: 4px 12px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 600;
    }
    .hero-stats {
        display: flex; gap: 20px; flex-wrap: wrap; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px;
    }
    .h-stat { display: flex; flex-direction: column; }
    .h-stat-val { font-size: 1.2rem; font-weight: 800; }
    .h-stat-lbl { font-size: 0.7rem; text-transform: uppercase; opacity: 0.8; letter-spacing: 0.5px; }

    /* ---- KPI Card ---- */
    .kpi-card {
        background: #FFFFFF; border-radius: 18px; padding: 20px;
        box-shadow: 0 4px 12px rgba(16, 142, 233, 0.05);
        border: 1px solid #E2E8F0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: left; position: relative; margin-bottom: 15px;
    }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(16, 142, 233, 0.12); }
    .kpi-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
    .kpi-icon { font-size: 1.5rem; }
    .kpi-label { font-size: 0.75rem; color: #64748B; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 1.8rem; font-weight: 800; color: #0F172A; margin: 0; line-height: 1.1; }
    .kpi-caption { font-size: 0.7rem; color: #64748B; margin-top: 6px; }
    .kpi-progress-bg { background: #E2E8F0; height: 4px; border-radius: 2px; margin-top: 8px; overflow: hidden; }
    .kpi-progress-bar { height: 100%; border-radius: 2px; transition: width 1s ease-in-out; }

    /* ---- Chart Card ---- */
    .chart-card {
        background: #FFFFFF; border-radius: 16px; padding: 15px; margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
        border: 1px solid #E2E8F0; transition: box-shadow 0.2s ease;
    }
    .chart-card:hover { box-shadow: 0 6px 16px rgba(16, 142, 233, 0.08); }

    /* ---- Insight Card ---- */
    .insight-card {
        background: #FFFFFF; border-radius: 16px; padding: 18px;
        border-left: 4px solid #108EE9; margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .insight-title { font-size: 0.9rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }
    .insight-item  { font-size: 0.85rem; color: #475569; margin: 6px 0; line-height: 1.5; }

    /* ---- Rank Card ---- */
    .rank-card {
        background: #FFFFFF; border-radius: 12px; padding: 12px 16px; margin: 6px 0;
        display: flex; align-items: center; gap: 12px;
        border: 1px solid #E2E8F0; transition: transform 0.2s;
    }
    .rank-card:hover { transform: translateX(4px); border-color: #108EE9; }
    .rank-badge {
        width: 28px; height: 28px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
    }
    .rank-top    { background: #D1FAE5; color: #065F46; }
    .rank-bottom { background: #FEE2E2; color: #991B1B; }
    .rank-label  { font-size: 0.8rem; color: #334155; flex: 1; font-weight: 500; }
    .rank-score  { font-size: 0.9rem; font-weight: 800; color: #108EE9; }

    /* ---- Keyword Chips ---- */
    .chip-container { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
    .chip {
        background: #EFF6FF; border: 1px solid #BFDBFE; color: #1D4ED8;
        padding: 4px 10px; border-radius: 16px; font-size: 0.75rem; font-weight: 600;
        display: flex; align-items: center; gap: 6px;
    }
    .chip-count { background: #3B82F6; color: white; border-radius: 10px; padding: 1px 6px; font-size: 0.65rem; }

    /* ---- Interp Box ---- */
    .interp-box { border-radius: 12px; padding: 16px; border-left: 4px solid; margin-bottom: 10px; }
    .interp-title { font-weight: 700; font-size: 0.88rem; margin-bottom: 6px; }
    .interp-count { font-size: 1.8rem; font-weight: 800; margin: 4px 0; }
    .interp-desc { font-size: 0.78rem; }

    /* ---- Tabs Pill Style ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px; background: transparent; padding: 0; border-bottom: none; margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 20px; font-weight: 600; font-size: 0.85rem;
        color: #64748B; padding: 8px 16px; background: #E2E8F0; border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important; color: #108EE9 !important;
        box-shadow: 0 2px 8px rgba(16,142,233,0.15) !important; border-bottom: none !important;
    }

    /* ---- Sidebar & Misc ---- */
    [data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E2E8F0; }
    .custom-divider { border: none; border-top: 1px solid #E2E8F0; margin: 24px 0; }
    .footer {
        text-align: center; padding: 20px; color: #94A3B8; font-size: 0.8rem;
        border-top: 1px solid #E2E8F0; margin-top: 30px;
    }
    .footer span { color: #108EE9; font-weight: 600; }
    .upload-zone {
        background: #F8FAFF; border: 2px dashed #BFDBFE;
        border-radius: 14px; padding: 22px; text-align: center; margin: 10px 0;
    }
    </style>
    ''', unsafe_allow_html=True)

# FILE HELPER
# =============================================================================
def get_file_mtime(path: Path):
    """Return file modification time or None if file doesn't exist."""
    try:
        return path.stat().st_mtime if path.exists() else None
    except Exception:
        return None


def file_status(path: Path) -> dict:
    """Return dict with exists, size, readable status."""
    info = {"exists": False, "size": 0, "readable": False, "error": ""}
    if not path.exists():
        info["error"] = "File tidak ditemukan"
        return info
    info["exists"] = True
    info["size"] = path.stat().st_size
    if info["size"] == 0:
        info["error"] = "File kosong (0 byte)"
        return info
    info["readable"] = True
    return info


# =============================================================================
# DATA LOADING — cached with mtime so cache refreshes when file changes
# =============================================================================
@st.cache_data(show_spinner=True)
def load_excel_cached(path_str: str, mtime):
    """Load Excel file — mtime param busts cache when file changes."""
    return pd.read_excel(path_str, engine="openpyxl")


@st.cache_data(show_spinner=True)
def load_csv_cached(path_str: str, mtime):
    """Load CSV file — mtime param busts cache when file changes."""
    return pd.read_csv(path_str)


def load_data():
    """
    Load all three data files using absolute pathlib paths.
    Returns dict: survey, ulasan, kuesioner, errors (list of dicts).
    """
    result = {
        "survey":    None,
        "ulasan":    None,
        "kuesioner": None,
        "errors":    {},   # key -> error message
    }

    # ---- Survey ----
    fs = file_status(SURVEY_PATH)
    if not fs["exists"]:
        result["errors"]["survey"] = f"File tidak ditemukan: {SURVEY_PATH}"
    elif fs["size"] == 0:
        result["errors"]["survey"] = f"File kosong (0 byte): {SURVEY_PATH}"
    else:
        try:
            result["survey"] = load_excel_cached(
                str(SURVEY_PATH), get_file_mtime(SURVEY_PATH)
            )
        except Exception as e:
            result["errors"]["survey"] = f"File tidak bisa dibaca: {e}"

    # ---- Ulasan ----
    fu = file_status(REVIEW_PATH)
    if not fu["exists"]:
        result["errors"]["ulasan"] = f"File tidak ditemukan: {REVIEW_PATH}"
    elif fu["size"] == 0:
        result["errors"]["ulasan"] = f"File kosong (0 byte): {REVIEW_PATH}"
    else:
        try:
            result["ulasan"] = load_excel_cached(
                str(REVIEW_PATH), get_file_mtime(REVIEW_PATH)
            )
        except Exception as e:
            result["errors"]["ulasan"] = f"File tidak bisa dibaca: {e}"

    # ---- Kuesioner CSV ----
    fk = file_status(QUESTIONNAIRE_PATH)
    if not fk["exists"]:
        result["errors"]["kuesioner"] = f"File tidak ditemukan: {QUESTIONNAIRE_PATH}"
    elif fk["size"] == 0:
        result["errors"]["kuesioner"] = "File kosong (0 byte). Rata-rata akan dihitung dari survey."
    else:
        try:
            df_k = load_csv_cached(
                str(QUESTIONNAIRE_PATH), get_file_mtime(QUESTIONNAIRE_PATH)
            )
            if df_k.empty:
                result["errors"]["kuesioner"] = "File CSV kosong. Rata-rata akan dihitung dari survey."
            else:
                result["kuesioner"] = df_k
        except Exception as e:
            result["errors"]["kuesioner"] = f"File tidak bisa dibaca: {e}"

    return result


# =============================================================================
# COLUMN DETECTION
# =============================================================================
def detect_column(df, keywords):
    """Return first column name matching any keyword (case-insensitive)."""
    if df is None:
        return None
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in str(col).lower():
                return col
    return None


def detect_questionnaire_columns(df):
    """
    Detect score columns: numeric columns with values in 1-5, excluding demographics.
    """
    if df is None:
        return []
    demo_kws = ["timestamp", "siapa nama", "jenis kelamin", "usia", "seberapa sering",
                "email", "no hp", "pekerjaan", "pendidikan"]
    q_cols = []
    for col in df.columns:
        col_l = col.lower()
        if any(kw in col_l for kw in demo_kws):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            vals = df[col].dropna().unique()
            if len(vals) > 0 and all(v in [1, 2, 3, 4, 5] for v in vals if not np.isnan(float(v))):
                q_cols.append(col)
    # Fallback: any non-demo numeric column
    if not q_cols:
        for col in df.columns:
            if any(kw in col.lower() for kw in demo_kws):
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                q_cols.append(col)
    return q_cols


# =============================================================================
# DATA PREPARATION
# =============================================================================
def prepare_survey_data(df):
    """Return cleaned survey df + detected column dict."""
    if df is None:
        return None, {}
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        "nama":   detect_column(df, ["siapa nama", "nama anda", "nama"]),
        "gender": detect_column(df, ["jenis kelamin", "gender", "kelamin"]),
        "usia":   detect_column(df, ["usia", "umur", "age"]),
        "freq":   detect_column(df, ["seberapa sering", "frekuensi", "frequency"]),
        "timestamp": detect_column(df, ["timestamp", "waktu", "time"]),
    }
    cols["q_cols"] = detect_questionnaire_columns(df)

    # Hide nama column from display (privacy)
    if cols["nama"] and cols["nama"] in df.columns:
        df = df.drop(columns=[cols["nama"]])

    return df, cols


def prepare_review_data(df):
    """Return cleaned review df + detected column dict, with sentimen column."""
    if df is None:
        return None, {}
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        "username": detect_column(df, ["username", "user", "pengguna"]),
        "rating":   detect_column(df, ["rating", "bintang", "nilai"]),
        "tanggal":  detect_column(df, ["tanggal", "date", "waktu", "time"]),
        "ulasan":   detect_column(df, ["ulasan", "review", "komentar", "isi", "content"]),
    }

    # Sentimen from rating
    if cols["rating"] and cols["rating"] in df.columns:
        df[cols["rating"]] = pd.to_numeric(df[cols["rating"]], errors="coerce")
        def _sent(r):
            if pd.isna(r):  return "Netral"
            r = float(r)
            if r >= 4:      return "Positif"
            elif r == 3:    return "Netral"
            else:           return "Negatif"
        df["sentimen"] = df[cols["rating"]].apply(_sent)
    else:
        df["sentimen"] = "Tidak Diketahui"

    # Parse tanggal
    if cols["tanggal"] and cols["tanggal"] in df.columns:
        try:
            df[cols["tanggal"]] = pd.to_datetime(df[cols["tanggal"]], errors="coerce")
        except Exception:
            pass

    return df, cols


def prepare_questionnaire_data(survey_df, survey_cols, kuesioner_df):
    """
    Build DataFrame[pertanyaan, rata_rata, label].
    Priority: hasil_kuesioner.csv → compute from survey.
    Handles the actual CSV format: unnamed first col = pertanyaan, second col = nilai.
    """
    # ---- From CSV (actual format: Unnamed:0 = pertanyaan, '0' = nilai) ----
    if kuesioner_df is not None:
        df = kuesioner_df.copy()
        # Drop trailing empty rows
        df = df.dropna(how="all")

        # Detect columns flexibly
        cols = list(df.columns)
        # Check if it's the raw export format: first col = pertanyaan text, second = score
        # Column names might be 'Unnamed: 0' and '0'
        str_cols  = [c for c in cols if df[c].dtype == object or str(c).startswith("Unnamed")]
        num_cols  = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

        # Also try renamed approach
        rename_map = {}
        for c in cols:
            cs = str(c).lower().strip()
            if any(k in cs for k in ["pertanyaan", "question", "indikator", "unnamed"]):
                rename_map[c] = "pertanyaan"
            elif any(k in cs for k in ["rata", "mean", "avg", "skor", "score", "nilai"]):
                rename_map[c] = "rata_rata"
            # Handle numeric column name like '0'
            elif cs.isdigit():
                rename_map[c] = "rata_rata"
        df = df.rename(columns=rename_map)

        # If first column was Unnamed, it likely holds question text
        if "pertanyaan" not in df.columns and len(df.columns) >= 2:
            df.columns = ["pertanyaan", "rata_rata"] + list(df.columns[2:])

        if "pertanyaan" in df.columns and "rata_rata" in df.columns:
            df["rata_rata"] = pd.to_numeric(df["rata_rata"], errors="coerce")
            df = df.dropna(subset=["rata_rata"])
            df["pertanyaan"] = df["pertanyaan"].astype(str).str.strip()
            df = df[df["pertanyaan"].str.len() > 3]  # Remove empty/junk rows
            df = df.reset_index(drop=True)
            df["label"] = [f"Q{i+1}" for i in range(len(df))]
            return df[["pertanyaan", "rata_rata", "label"]]

    # ---- Compute from survey ----
    if survey_df is not None and survey_cols.get("q_cols"):
        q_cols = survey_cols["q_cols"]
        means  = survey_df[q_cols].mean()
        df = pd.DataFrame({
            "pertanyaan": q_cols,
            "rata_rata":  means.values,
            "label":      [f"Q{i+1}" for i in range(len(q_cols))]
        })
        return df

    return None


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================
def apply_survey_filters(df, cols, f_gender, f_usia, f_freq):
    if df is None or df.empty:
        return df
    fdf = df.copy()
    if cols.get("gender") and f_gender and "Semua" not in f_gender and cols["gender"] in fdf.columns:
        fdf = fdf[fdf[cols["gender"]].isin(f_gender)]
    if cols.get("usia") and f_usia and cols["usia"] in fdf.columns:
        lo, hi = f_usia
        fdf = fdf[pd.to_numeric(fdf[cols["usia"]], errors="coerce").between(lo, hi)]
    if cols.get("freq") and f_freq and "Semua" not in f_freq and cols["freq"] in fdf.columns:
        fdf = fdf[fdf[cols["freq"]].isin(f_freq)]
    return fdf


def apply_review_filters(df, cols, f_rating, f_sentiment, f_date_range, f_search):
    if df is None or df.empty:
        return df
    fdf = df.copy()
    if cols.get("rating") and f_rating and "Semua" not in f_rating and cols["rating"] in fdf.columns:
        fdf = fdf[pd.to_numeric(fdf[cols["rating"]], errors="coerce").isin(f_rating)]
    if f_sentiment and "Semua" not in f_sentiment:
        fdf = fdf[fdf["sentimen"].isin(f_sentiment)]
    if cols.get("tanggal") and f_date_range and len(f_date_range) == 2 and cols["tanggal"] in fdf.columns:
        try:
            tgl = fdf[cols["tanggal"]]
            if pd.api.types.is_datetime64_any_dtype(tgl):
                s = pd.to_datetime(f_date_range[0])
                e = pd.to_datetime(f_date_range[1])
                fdf = fdf[tgl.between(s, e)]
        except Exception:
            pass
    if f_search and cols.get("ulasan") and cols["ulasan"] in fdf.columns:
        fdf = fdf[fdf[cols["ulasan"]].astype(str).str.lower()
                  .str.contains(f_search.lower(), na=False)]
    return fdf


# =============================================================================
# CHART CONFIG

# =============================================================================
# CHART CONFIG
# =============================================================================
C_PRIMARY = "#108EE9"
C_DEEP    = "#0B5ED7"
C_ELECTRIC= "#2563EB"
C_SKY     = "#38BDF8"
C_SOFT_BG = "#F3F8FF"
C_TEXT    = "#0F172A"
C_GREEN   = "#10B981"
C_POSITIVE= "#10B981"
C_AMBER   = "#F59E0B"
C_NEUTRAL = "#F59E0B"
C_RED     = "#EF4444"
C_NEGATIVE= "#EF4444"
C_MUTED   = "#64748B"
C_CARD    = "#FFFFFF"
C_BORDER  = "#E2E8F0"
TMPL      = "plotly_white"

def _base_layout(title, height=320, **kwargs):
    layout = {
        "title": {
            "text": f"<b>{title}</b>",
            "font": {"size": 13, "color": "#0F172A", "family": "Inter"},
            "x": 0.01, "y": 0.95
        },
        "template": TMPL,
        "height": height,
        "margin": {"t": 40, "b": 10, "l": 10, "r": 10},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter", "color": "#475569"}
    }
    layout.update(kwargs)
    return layout

def create_donut_chart(values, labels, title, colors=None, height=320):
    fig = go.Figure(go.Pie(
        values=values, labels=labels, hole=0.6,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Jumlah: %{value}<br>%{percent}<extra></extra>",
        marker=dict(colors=colors, line=dict(color="white", width=2)),
    ))
    fig.update_layout(**_base_layout(title, height,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)))
    return fig

def create_bar_chart(x, y, title, xlabel="", ylabel="Jumlah", color=C_PRIMARY, height=320):
    fig = go.Figure(go.Bar(
        x=x, y=y, marker_color=color, marker_line_width=0,
        hovertemplate=f"<b>%{{x}}</b><br>{ylabel}: %{{y}}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(title, height,
        xaxis_title=xlabel, yaxis_title=ylabel, showlegend=False))
    return fig

def create_horizontal_bar_chart(df_q, title="Rata-rata Skor Kuesioner", height=520):
    dfs = df_q.sort_values("rata_rata", ascending=True).copy()
    bar_colors = [C_GREEN if v >= 4.0 else (C_AMBER if v >= 3.0 else C_RED) for v in dfs["rata_rata"]]
    fig = go.Figure(go.Bar(
        x=dfs["rata_rata"], y=dfs["label"], orientation="h",
        marker_color=bar_colors, customdata=dfs["pertanyaan"],
        hovertemplate="<b>%{y}</b><br>%{customdata}<br>Rata-rata: <b>%{x:.2f}</b><extra></extra>",
        text=dfs["rata_rata"].round(2), textposition="outside",
        textfont=dict(size=11, color="#0F172A", family="Inter"),
    ))
    dyn_h = max(height, len(dfs) * 35 + 80)
    fig.update_layout(**_base_layout(title, dyn_h,
        xaxis=dict(range=[0, 5.4], title="Rata-rata Skor", tickformat=".1f"),
        yaxis=dict(title=""), margin=dict(t=40, b=10, l=60, r=40), showlegend=False))
    for xv, lbl, cl in [(3.0, "Cukup", C_AMBER), (4.0, "Kuat", C_GREEN)]:
        fig.add_vline(x=xv, line_dash="dash", line_color=cl,
                      annotation_text=lbl, annotation_position="top", annotation_font_size=10)
    return fig

# =============================================================================
# KEYWORD EXTRACTION
# =============================================================================
STOPWORDS_ID = set("yang dan dengan untuk dari ini itu saya kamu kita sudah bisa tidak sangat lebih pada dalam aplikasi app apk dana nya lah kok min gan aja di ke juga udah tapi karena karna belum buat ada saat".split())
ALLOWED_KEYWORDS = {"transaksi", "saldo", "transfer", "premium", "gagal", "error", "cepat", "mudah", "promo", "voucher", "bank", "bayar", "cicil", "topup", "login"}

def get_keyword_chips(texts, top_n=15):
    all_text = " ".join(str(t).lower() for t in texts if pd.notna(t))
    words = re.findall(r"[a-z]{4,}", all_text)
    filtered = []
    for w in words:
        if w in ALLOWED_KEYWORDS or (w not in STOPWORDS_ID and len(w) > 3):
            filtered.append(w)
    
    top = Counter(filtered).most_common(top_n)
    if not top: return ""
    
    html = '<div class="chip-container">'
    for w, c in top:
        html += f'<div class="chip">{w} <span class="chip-count">{c}</span></div>'
    html += '</div>'
    return html

# =============================================================================
# HTML COMPONENTS
# =============================================================================
def create_kpi_card(icon, label, value, caption, progress=None, p_color=C_PRIMARY):
    prog_html = ""
    if progress is not None:
        prog_html = f'<div class="kpi-progress-bg"><div class="kpi-progress-bar" style="width: {progress}%; background-color: {p_color};"></div></div>'
    return f'''
<div class="kpi-card fade-in">
    <div class="kpi-header">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
    </div>
    <div class="kpi-value">{value}</div>
    <div class="kpi-caption">{caption}</div>
    {prog_html}
</div>
'''

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")

# =============================================================================
# RENDER SECTIONS
# =============================================================================
def render_hero(total_survey, total_ulasan, avg_skor, avg_rating, pct_pos):
    now_str = datetime.now().strftime("%d %B %Y, %H:%M WIB")
    st.markdown(f"""
<div class="hero-section fade-in">
    <div class="hero-title">💳 DANA Insight Command Center</div>
    <div class="hero-subtitle">
        Dashboard interaktif untuk memahami pola penggunaan, skor pengalaman, rating, dan sentimen pengguna aplikasi DANA.
    </div>
    <div class="badge-container">
        <span class="hero-badge">📊 Survey {total_survey} Responden</span>
        <span class="hero-badge">💬 Review {total_ulasan} Ulasan</span>
        <span class="hero-badge">🧠 Sentiment Analysis</span>
        <span class="hero-badge">✨ Interactive Dashboard</span>
    </div>
    <div class="hero-stats">
        <div class="h-stat"><span class="h-stat-val">👥 {total_survey}</span><span class="h-stat-lbl">Responden</span></div>
        <div class="h-stat"><span class="h-stat-val">💬 {total_ulasan}</span><span class="h-stat-lbl">Ulasan</span></div>
        <div class="h-stat"><span class="h-stat-val">📋 {avg_skor:.2f}</span><span class="h-stat-lbl">Skor</span></div>
        <div class="h-stat"><span class="h-stat-val">⭐ {avg_rating:.2f}</span><span class="h-stat-lbl">Rating</span></div>
        <div class="h-stat"><span class="h-stat-val">😊 {pct_pos:.1f}%</span><span class="h-stat-lbl">Positif</span></div>
    </div>
    <div style="position:absolute; bottom:15px; right:20px; font-size:0.75rem; opacity:0.8;">
        🕒 {now_str}
    </div>
</div>
""", unsafe_allow_html=True)

def render_sidebar_filters(survey_df, survey_cols, review_df, review_cols, load_errors):
    with st.sidebar:
        st.markdown('''
        <div style="text-align:center; margin-bottom: 20px;">
            <div style="font-size:2rem;">🎛️</div>
            <div style="font-size:1.1rem; font-weight:800; color:#0F172A;">Control Panel</div>
            <div style="font-size:0.8rem; color:#64748B;">Atur filter dashboard</div>
        </div>
        ''', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with c2:
            if st.button("🗑️ Reset", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
                
        st.markdown("---")
        
        # Survey
        st.markdown("#### 📊 Filter Survei")
        f_gender, f_usia, f_freq = ["Semua"], None, ["Semua"]
        if survey_df is not None and not survey_df.empty:
            g_col = survey_cols.get("gender")
            if g_col and g_col in survey_df.columns:
                opts = sorted(survey_df[g_col].dropna().unique().tolist())
                sel = st.multiselect("Jenis Kelamin", options=opts, default=[], placeholder="Semua gender", key="g_sel")
                f_gender = sel if sel else ["Semua"]
            
            u_col = survey_cols.get("usia")
            if u_col and u_col in survey_df.columns:
                un = pd.to_numeric(survey_df[u_col], errors="coerce").dropna()
                if not un.empty:
                    lo, hi = int(un.min()), int(un.max())
                    if lo == hi: hi = lo + 1
                    f_usia = st.slider("Rentang Usia", lo, hi, (lo, hi), key="u_sel")
            
            fr_col = survey_cols.get("freq")
            if fr_col and fr_col in survey_df.columns:
                fr_opts = sorted(survey_df[fr_col].dropna().unique().tolist())
                sel2 = st.multiselect("Frekuensi Penggunaan", options=fr_opts, default=[], placeholder="Semua frekuensi", key="f_sel")
                f_freq = sel2 if sel2 else ["Semua"]
                
        st.markdown("---")
        
        # Review
        st.markdown("#### 💬 Filter Ulasan")
        f_rating = ["Semua"]
        f_sentiment = ["Semua"]
        f_date_range = None
        f_search = ""
        
        if review_df is not None and not review_df.empty:
            rat_sel = st.multiselect("Rating ⭐", options=[1, 2, 3, 4, 5], default=[], placeholder="Semua rating", format_func=lambda x: f"{'⭐'*x} ({x})", key="r_sel")
            f_rating = rat_sel if rat_sel else ["Semua"]
            sent_sel = st.multiselect("Sentimen", options=["Positif", "Netral", "Negatif"], default=[], placeholder="Semua sentimen", key="s_sel")
            f_sentiment = sent_sel if sent_sel else ["Semua"]
            
            tgl_col = review_cols.get("tanggal")
            if tgl_col and tgl_col in review_df.columns:
                tgl = review_df[tgl_col]
                if pd.api.types.is_datetime64_any_dtype(tgl):
                    valid = tgl.dropna()
                    if not valid.empty:
                        mn, mx = valid.min().date(), valid.max().date()
                        if mn == mx: mx = date.today()
                        dr = st.date_input("Rentang Tanggal", value=(mn, mx), min_value=mn, max_value=mx, key="d_sel")
                        if len(dr) == 2:
                            f_date_range = dr
                            
            f_search = st.text_input("🔍 Cari kata dalam ulasan", placeholder="Ketik kata kunci...", key="q_sel")
        
        st.markdown("---")
        st.markdown("#### ⚙️ Tampilan Tabel")
        f_limit_str = st.selectbox("Jumlah baris tabel", options=["10", "25", "50", "100", "Semua"], index=2, key="l_sel")
        f_limit = None if f_limit_str == "Semua" else int(f_limit_str)
        
        st.markdown('<div style="font-size:0.75rem; color:#64748B; background:#F8FAFC; padding:10px; border-radius:8px; border:1px solid #E2E8F0;">ℹ️ Filter aktif akan otomatis memperbarui grafik, KPI, dan tabel.</div>', unsafe_allow_html=True)
        
        with st.expander("🔧 Debug Info"):
            if load_errors:
                for k, v in load_errors.items(): st.warning(f"[{k}] {v}")
            else:
                st.success("Semua file data terbaca dengan baik.")
                
    return f_gender, f_usia, f_freq, f_rating, f_sentiment, f_date_range, f_search, f_limit

def render_kpi_section(survey_filtered, review_filtered, q_df):
    n_resp = len(survey_filtered) if survey_filtered is not None else 0
    n_ulasan = len(review_filtered) if review_filtered is not None else 0
    avg_q = float(q_df["rata_rata"].mean()) if q_df is not None and not q_df.empty and "rata_rata" in q_df.columns else 0.0
    
    avg_rating = 0.0
    pct_pos = 0.0
    if review_filtered is not None and not review_filtered.empty:
        if "rating" in review_filtered.columns:
            avg_rating = float(pd.to_numeric(review_filtered["rating"], errors="coerce").mean())
        if "sentimen" in review_filtered.columns:
            total = len(review_filtered)
            pos = (review_filtered["sentimen"] == "Positif").sum()
            pct_pos = pos / total * 100 if total > 0 else 0.0
            
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(create_kpi_card("👥", "Responden Survei", f"{n_resp:,}", "berdasarkan filter aktif"), unsafe_allow_html=True)
    with c2: st.markdown(create_kpi_card("💬", "Ulasan Pengguna", f"{n_ulasan:,}", "berdasarkan filter aktif"), unsafe_allow_html=True)
    with c3: st.markdown(create_kpi_card("📋", "Rata-rata Skor", f"{avg_q:.2f}", "skala kuesioner", progress=min(avg_q/5*100, 100), p_color=C_PRIMARY), unsafe_allow_html=True)
    with c4: st.markdown(create_kpi_card("⭐", "Rata-rata Rating", f"{avg_rating:.2f}", "berdasarkan filter aktif", progress=min(avg_rating/5*100, 100), p_color=C_AMBER), unsafe_allow_html=True)
    with c5: st.markdown(create_kpi_card("😊", "Sentimen Positif", f"{pct_pos:.1f}%", "rating ≥ 4", progress=pct_pos, p_color=C_GREEN), unsafe_allow_html=True)

def render_overview(survey_filtered, survey_cols, review_filtered, review_cols):
    st.markdown("### Executive Summary")
    
    # Insights Row
    i1, i2, i3, i4 = st.columns(4)
    g_txt, f_txt, r_txt, s_txt = "-", "-", "-", "-"
    if survey_filtered is not None and not survey_filtered.empty:
        g_col = survey_cols.get("gender")
        if g_col and g_col in survey_filtered.columns:
            top_g = survey_filtered[g_col].value_counts()
            if not top_g.empty: g_txt = f"{top_g.index[0]} ({top_g.values[0]/len(survey_filtered)*100:.0f}%)"
        f_col = survey_cols.get("freq")
        if f_col and f_col in survey_filtered.columns:
            top_f = survey_filtered[f_col].value_counts()
            if not top_f.empty: f_txt = f"{top_f.index[0]}"
            
    if review_filtered is not None and not review_filtered.empty:
        if "rating" in review_filtered.columns:
            avg_r = pd.to_numeric(review_filtered["rating"], errors="coerce").mean()
            r_txt = f"{avg_r:.2f}/5"
        if "sentimen" in review_filtered.columns:
            top_s = review_filtered["sentimen"].value_counts()
            if not top_s.empty: s_txt = f"{top_s.index[0]} ({top_s.values[0]/len(review_filtered)*100:.0f}%)"
            
    with i1: st.markdown(f'<div class="insight-card"><div class="insight-title">👤 Mayoritas Responden</div><div class="kpi-value" style="font-size:1.2rem;">{g_txt}</div></div>', unsafe_allow_html=True)
    with i2: st.markdown(f'<div class="insight-card"><div class="insight-title">📱 Frekuensi Terbanyak</div><div class="kpi-value" style="font-size:1.2rem;">{f_txt}</div></div>', unsafe_allow_html=True)
    with i3: st.markdown(f'<div class="insight-card" style="border-left-color:{C_AMBER};"><div class="insight-title">⭐ Rating Rata-rata</div><div class="kpi-value" style="font-size:1.2rem;">{r_txt}</div></div>', unsafe_allow_html=True)
    with i4: st.markdown(f'<div class="insight-card" style="border-left-color:{C_GREEN};"><div class="insight-title">😊 Sentimen Dominan</div><div class="kpi-value" style="font-size:1.2rem;">{s_txt}</div></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        g_col = survey_cols.get("gender")
        if g_col and g_col in survey_filtered.columns:
            gd = survey_filtered[g_col].value_counts()
            fig = create_donut_chart(gd.values.tolist(), gd.index.tolist(), "Distribusi Jenis Kelamin", colors=[C_PRIMARY, C_ELECTRIC, C_DEEP, C_SKY])
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        f_col = survey_cols.get("freq")
        if f_col and f_col in survey_filtered.columns:
            fd = survey_filtered[f_col].value_counts()
            fig = create_bar_chart(fd.index.tolist(), fd.values.tolist(), "Frekuensi Penggunaan", color=C_PRIMARY)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    u_col = survey_cols.get("usia")
    if u_col and u_col in survey_filtered.columns:
        ua = pd.to_numeric(survey_filtered[u_col], errors="coerce").dropna().astype(int)
        uc = ua.value_counts().sort_index()
        fig = create_bar_chart(uc.index.astype(str).tolist(), uc.values.tolist(), "Distribusi Usia Responden", xlabel="Usia", color=C_ELECTRIC)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_survey_analysis(survey_filtered, survey_cols, q_df):
    st.markdown("### Survey Experience Score")
    if q_df is None or q_df.empty:
        st.warning("Data kuesioner tidak tersedia.")
        return
        
    strong = q_df[q_df["rata_rata"] >= 4.0]
    moderate = q_df[(q_df["rata_rata"] >= 3.0) & (q_df["rata_rata"] < 4.0)]
    weak = q_df[q_df["rata_rata"] < 3.0]
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1: st.markdown(f'<div class="interp-box" style="background:#ECFDF5; border-color:{C_GREEN}; color:#065F46;"><div class="interp-title">🟢 Indikator Kuat / Baik</div><div class="interp-count">{len(strong)}</div><div class="interp-desc">Skor ≥ 4.00</div></div>', unsafe_allow_html=True)
    with ic2: st.markdown(f'<div class="interp-box" style="background:#FFFBEB; border-color:{C_AMBER}; color:#92400E;"><div class="interp-title">🟡 Indikator Cukup</div><div class="interp-count">{len(moderate)}</div><div class="interp-desc">Skor 3.00 – 3.99</div></div>', unsafe_allow_html=True)
    with ic3: st.markdown(f'<div class="interp-box" style="background:#FEF2F2; border-color:{C_RED}; color:#991B1B;"><div class="interp-title">🔴 Perlu Perhatian</div><div class="interp-count">{len(weak)}</div><div class="interp-desc">Skor < 3.00</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    fig = create_horizontal_bar_chart(q_df, "Rata-rata Skor Q1–Q20")
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    def short_q(t): return t[:60] + "…" if len(t) > 60 else t
    with c1:
        st.markdown("#### ✅ Top 5 Indikator Tertinggi")
        for i, row in enumerate(q_df.nlargest(5, "rata_rata").itertuples(), 1):
            st.markdown(f'<div class="rank-card"><div class="rank-badge rank-top">{i}</div><div class="rank-label"><b>{row.label}</b> — {short_q(row.pertanyaan)}</div><div class="rank-score">{row.rata_rata:.2f}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown("#### ⚠️ Bottom 5 Indikator Terendah")
        for i, row in enumerate(q_df.nsmallest(5, "rata_rata").itertuples(), 1):
            st.markdown(f'<div class="rank-card"><div class="rank-badge rank-bottom">{i}</div><div class="rank-label"><b>{row.label}</b> — {short_q(row.pertanyaan)}</div><div class="rank-score">{row.rata_rata:.2f}</div></div>', unsafe_allow_html=True)

    with st.expander("📋 Pemetaan Q1–Q20 Lengkap"):
        for _, row in q_df.iterrows():
            c = C_GREEN if row["rata_rata"]>=4 else (C_AMBER if row["rata_rata"]>=3 else C_RED)
            st.markdown(f'<div style="padding:6px 0; border-bottom:1px solid #E2E8F0; display:flex; gap:10px;"><b style="color:{C_PRIMARY}; width:30px;">{row["label"]}</b> <span style="flex:1; font-size:0.9rem;">{row["pertanyaan"]}</span> <b style="color:{c};">{row["rata_rata"]:.2f}</b></div>', unsafe_allow_html=True)

def render_review_analysis(review_filtered, review_cols, review_raw_count, f_limit):
    st.markdown("### Review Intelligence")
    if review_filtered is None or review_filtered.empty:
        st.info("Data ulasan tidak tersedia / filter kosong.")
        return
        
    filtered_count = len(review_filtered)
    if filtered_count < review_raw_count:
        st.info(f"🔍 Menampilkan **{filtered_count}** dari **{review_raw_count}** ulasan berdasarkan filter yang dipilih.")
    else:
        st.info(f"📊 Menampilkan seluruh **{review_raw_count}** ulasan.")

    st.markdown("#### 🏷️ Top Keyword Ulasan")
    ul_col = review_cols.get("ulasan")
    if ul_col and ul_col in review_filtered.columns:
        st.markdown(get_keyword_chips(review_filtered[ul_col].tolist()), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        if "sentimen" in review_filtered.columns:
            sc = review_filtered["sentimen"].value_counts()
            colors = [C_GREEN if s=="Positif" else (C_AMBER if s=="Netral" else C_RED) for s in sc.index]
            fig = create_donut_chart(sc.values.tolist(), sc.index.tolist(), "Distribusi Sentimen", colors=colors)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        r_col = review_cols.get("rating")
        if r_col and r_col in review_filtered.columns:
            rd = pd.to_numeric(review_filtered[r_col], errors="coerce").dropna().astype(int)
            rc = rd.value_counts().sort_index()
            colors = [C_RED if r<=2 else (C_AMBER if r==3 else C_GREEN) for r in rc.index]
            fig = create_bar_chart([f"{r} ⭐" for r in rc.index], rc.values.tolist(), "Distribusi Rating", color=colors)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    tgl_col = review_cols.get("tanggal")
    if tgl_col and tgl_col in review_filtered.columns:
        tgl = review_filtered[tgl_col]
        if pd.api.types.is_datetime64_any_dtype(tgl):
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            daily = review_filtered.groupby(tgl.dt.date).size().reset_index(name="jumlah")
            fig = go.Figure(go.Scatter(x=daily.iloc[:,0], y=daily["jumlah"], mode="lines+markers", line=dict(color=C_PRIMARY, width=3), fill="tozeroy", fillcolor="rgba(16,142,233,0.1)"))
            fig.update_layout(**_base_layout("Tren Ulasan Harian"))
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("#### 📋 Tabel Ulasan")
    df_disp = review_filtered.copy()
    
    # Hide username
    u_col = review_cols.get("username")
    if u_col and u_col in df_disp.columns:
        df_disp = df_disp.drop(columns=[u_col])
        
    # Order
    cols_order = []
    for c in ["rating", "tanggal", "ulasan", "sentimen"]:
        ac = review_cols.get(c, c)
        if ac in df_disp.columns: cols_order.append(ac)
    for c in df_disp.columns:
        if c not in cols_order: cols_order.append(c)
    df_disp = df_disp[cols_order]
    
    # Insert NO column
    df_disp.insert(0, "No", range(1, len(df_disp) + 1))
    
    if f_limit is not None: df_disp = df_disp.head(f_limit)
    
    try:
        cfg = {"No": st.column_config.NumberColumn("No", width="small")}
        if review_cols.get("rating") in df_disp.columns: cfg[review_cols["rating"]] = st.column_config.NumberColumn("Rating", width="small", format="%d ⭐")
        if review_cols.get("tanggal") in df_disp.columns: cfg[review_cols["tanggal"]] = st.column_config.DatetimeColumn("Tanggal", width="medium", format="DD-MM-YYYY HH:mm")
        if review_cols.get("ulasan") in df_disp.columns: cfg[review_cols["ulasan"]] = st.column_config.TextColumn("Ulasan", width="large")
        st.dataframe(df_disp, use_container_width=True, height=520, hide_index=True, column_config=cfg)
    except:
        st.dataframe(df_disp, use_container_width=True, height=520, hide_index=True)

    st.markdown("#### 📖 Contoh Ulasan Lengkap")
    for i, row in df_disp.head(10).iterrows():
        t = row[review_cols.get("tanggal")] if review_cols.get("tanggal") in row else "-"
        r = row[review_cols.get("rating")] if review_cols.get("rating") in row else 0
        s = row.get("sentimen", "-")
        u = row[review_cols.get("ulasan")] if review_cols.get("ulasan") in row else "-"
        emoji = "✅" if s=="Positif" else ("⚠️" if s=="Netral" else "❌")
        with st.expander(f"{emoji} {s} | {r} ⭐ | {t}"):
            st.write(u)

def render_data_explorer(survey_filtered, review_filtered, survey_raw_count, review_raw_count, f_limit):
    st.markdown("### 📁 Data Explorer")
    st.info("🔒 **Privacy Note:** Nama responden dan username sengaja disembunyikan untuk menjaga privasi data. Tombol download akan mengunduh versi aman ini.")
    
    st.markdown("#### Data Survei")
    if survey_filtered is not None and not survey_filtered.empty:
        fc = len(survey_filtered)
        if fc < survey_raw_count: st.caption(f"Total data asli: **{survey_raw_count}** | Setelah filter: **{fc}**")
        else: st.caption(f"Total data asli: **{survey_raw_count}**")
        
        df_s = survey_filtered.copy()
        df_s.insert(0, "No", range(1, len(df_s) + 1))
        st.dataframe(df_s, use_container_width=True, height=340, hide_index=True)
        st.download_button("⬇️ Download Survey (CSV Publik)", data=convert_df_to_csv(survey_filtered), file_name="survey_publik.csv", mime="text/csv")
    
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    
    st.markdown("#### Data Ulasan")
    if review_filtered is not None and not review_filtered.empty:
        fc = len(review_filtered)
        if fc < review_raw_count: st.caption(f"Total data asli: **{review_raw_count}** | Setelah filter: **{fc}**")
        else: st.caption(f"Total data asli: **{review_raw_count}**")
        
        df_r = review_filtered.copy()
        u_col = next((c for c in df_r.columns if c.lower() in ["username", "user", "pengguna"]), None)
        if u_col: df_r = df_r.drop(columns=[u_col])
        df_r.insert(0, "No", range(1, len(df_r) + 1))
        
        if f_limit is not None: df_disp = df_r.head(f_limit)
        else: df_disp = df_r
        
        st.dataframe(df_disp, use_container_width=True, height=400, hide_index=True)
        st.download_button("⬇️ Download Ulasan (CSV Publik)", data=convert_df_to_csv(review_filtered), file_name="ulasan_publik.csv", mime="text/csv")

def render_storytelling(q_df, review_df):
    st.markdown("### 📝 Kesimpulan Utama")
    
    skor = float(q_df["rata_rata"].mean()) if q_df is not None and not q_df.empty else 0
    skor_txt = "sangat baik" if skor>=4.5 else ("baik" if skor>=4.0 else ("cukup baik" if skor>=3.5 else "perlu perbaikan"))
    
    pct_pos = 0
    if review_df is not None and not review_df.empty and "sentimen" in review_df.columns:
        pct_pos = (review_df["sentimen"]=="Positif").sum() / len(review_df) * 100
    sent_txt = "didominasi positif" if pct_pos>50 else "didominasi negatif"
    
    best_q = q_df.loc[q_df["rata_rata"].idxmax()] if q_df is not None and not q_df.empty else None
    worst_q = q_df.loc[q_df["rata_rata"].idxmin()] if q_df is not None and not q_df.empty else None
    
    st.markdown(f'''
    <div class="insight-card" style="border-left-color:{C_ELECTRIC};">
        <ul style="margin:0; padding-left:20px; color:#334155; line-height:1.7;">
            <li>Secara keseluruhan, pengalaman pengguna DANA dinilai <b>{skor_txt}</b> dengan skor rata-rata survei <b>{skor:.2f}/5.00</b>.</li>
            <li>Sentimen pengguna dari ulasan <b>{sent_txt}</b> ({pct_pos:.1f}% ulasan positif).</li>
            {f"<li><b>Kekuatan Utama:</b> Indikator {best_q['label']} ({best_q['rata_rata']:.2f}) — {best_q['pertanyaan']}.</li>" if best_q is not None else ""}
            {f"<li><b>Area Perbaikan:</b> Indikator {worst_q['label']} ({worst_q['rata_rata']:.2f}) — {worst_q['pertanyaan']}.</li>" if worst_q is not None else ""}
        </ul>
    </div>
    ''', unsafe_allow_html=True)

def render_footer():
    st.markdown('''
    <div class="footer">
        📊 <span>DANA Insight Command Center</span> | Developer: <span>Muhammad Arsyad Arroyan</span><br>
        Built with ❤️ <span>Streamlit</span> &amp; <span>Plotly</span>
    </div>''', unsafe_allow_html=True)

# =============================================================================
# MAIN
# =============================================================================
def main():
    inject_custom_css()
    
    with st.spinner("⏳ Memuat data..."):
        data = load_data()
        
    s_raw, u_raw, k_raw, errs = data["survey"], data["ulasan"], data["kuesioner"], data["errors"]
    
    if errs:
        for k, v in errs.items():
            if "kosong" in v.lower(): st.warning(f"⚠️ {k}: {v}")
            else: st.error(f"❌ {k}: {v}")
            
    s_df, s_cols = prepare_survey_data(s_raw)
    u_df, u_cols = prepare_review_data(u_raw)
    q_df = prepare_questionnaire_data(s_df, s_cols, k_raw)
    
    t_surv = len(s_df) if s_df is not None else 0
    t_rev  = len(u_df) if u_df is not None else 0
    avg_s  = float(q_df["rata_rata"].mean()) if q_df is not None and not q_df.empty else 0
    avg_r  = float(pd.to_numeric(u_df[u_cols.get("rating", "rating")], errors="coerce").mean()) if u_df is not None and not u_df.empty else 0
    pct_p  = ((u_df["sentimen"]=="Positif").sum()/t_rev*100) if t_rev>0 else 0
    
    render_hero(t_surv, t_rev, avg_s, avg_r, pct_p)
    
    f_gen, f_usi, f_frq, f_rat, f_sen, f_dt, f_q, f_lim = render_sidebar_filters(s_df, s_cols, u_df, u_cols, errs)
    
    s_filt = apply_survey_filters(s_df, s_cols, f_gen, f_usi, f_frq)
    u_filt = apply_review_filters(u_df, u_cols, f_rat, f_sen, f_dt, f_q)
    
    render_kpi_section(s_filt, u_filt, q_df)
    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    
    t1, t2, t3, t4 = st.tabs(["🏠 Overview", "📋 Analisis Survei", "💬 Analisis Ulasan", "📁 Data Explorer"])
    with t1: render_overview(s_filt, s_cols, u_filt, u_cols)
    with t2: render_survey_analysis(s_filt, s_cols, q_df)
    with t3: render_review_analysis(u_filt, u_cols, t_rev, f_lim)
    with t4: render_data_explorer(s_filt, u_filt, t_surv, t_rev, f_lim)
    
    render_storytelling(q_df, u_df)
    render_footer()

if __name__ == "__main__":
    main()
