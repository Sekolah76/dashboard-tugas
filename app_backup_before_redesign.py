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
    page_title="Dashboard Analisis DANA",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CUSTOM CSS
# =============================================================================
def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background: #F8FAFC; }

    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(18px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .fade-in { animation: fadeInUp 0.55s ease forwards; }

    /* ---- Hero ---- */
    .hero-section {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #2563EB 100%);
        border-radius: 20px;
        padding: 44px 40px 36px;
        margin-bottom: 28px;
        color: white;
        position: relative;
        overflow: hidden;
    }
    .hero-section::before {
        content: ''; position: absolute;
        top: -60px; right: -60px;
        width: 240px; height: 240px;
        border-radius: 50%;
        background: rgba(255,255,255,0.07);
    }
    .hero-section::after {
        content: ''; position: absolute;
        bottom: -80px; left: -40px;
        width: 300px; height: 300px;
        border-radius: 50%;
        background: rgba(255,255,255,0.04);
    }
    .hero-title {
        font-size: 2.1rem; font-weight: 800;
        margin: 0 0 10px 0; line-height: 1.2; letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 0.97rem; font-weight: 400;
        opacity: 0.88; margin: 0 0 22px 0;
        max-width: 680px; line-height: 1.65;
    }
    .badge-container { display: flex; flex-wrap: wrap; gap: 10px; }
    .badge {
        background: rgba(255,255,255,0.17);
        border: 1px solid rgba(255,255,255,0.32);
        color: white;
        padding: 5px 14px; border-radius: 20px;
        font-size: 0.77rem; font-weight: 600; letter-spacing: 0.3px;
    }

    /* ---- KPI Card ---- */
    .kpi-card {
        background: white; border-radius: 16px;
        padding: 22px 16px 18px;
        box-shadow: 0 2px 14px rgba(79,70,229,0.09);
        border: 1px solid #E8EAFF;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        text-align: center;
    }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 8px 26px rgba(79,70,229,0.17); }
    .kpi-icon { font-size: 1.7rem; margin-bottom: 6px; }
    .kpi-value { font-size: 1.9rem; font-weight: 800; color: #4F46E5; margin: 0; line-height: 1; }
    .kpi-label { font-size: 0.78rem; color: #64748B; font-weight: 500; margin-top: 6px;
                 text-transform: uppercase; letter-spacing: 0.5px; }

    /* ---- Rank Card ---- */
    .rank-card {
        background: white; border-radius: 12px;
        padding: 14px 16px; margin: 5px 0;
        display: flex; align-items: center; gap: 12px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06); border: 1px solid #F1F5F9;
        transition: box-shadow 0.2s ease;
    }
    .rank-card:hover { box-shadow: 0 4px 14px rgba(79,70,229,0.12); }
    .rank-badge {
        width: 32px; height: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.78rem; font-weight: 700; flex-shrink: 0;
    }
    .rank-top    { background: #D1FAE5; color: #065F46; }
    .rank-bottom { background: #FEE2E2; color: #991B1B; }
    .rank-label  { font-size: 0.81rem; color: #334155; flex: 1; font-weight: 500; line-height: 1.4; }
    .rank-score  { font-size: 0.98rem; font-weight: 700; color: #4F46E5; }

    /* ---- Review Card ---- */
    .review-card {
        background: white; border-radius: 13px;
        padding: 16px 18px; margin: 7px 0;
        box-shadow: 0 1px 8px rgba(0,0,0,0.05); border: 1px solid #F1F5F9;
        border-left: 4px solid #10B981;
    }
    .review-card.negative { border-left-color: #EF4444; }
    .review-user  { font-size: 0.8rem; font-weight: 600; color: #374151; margin-bottom: 4px; }
    .review-text  { font-size: 0.84rem; color: #4B5563; line-height: 1.5; }
    .review-stars { font-size: 0.78rem; color: #F59E0B; margin-top: 5px; }

    /* ---- Insight Card ---- */
    .insight-card {
        background: linear-gradient(135deg, #EEF2FF 0%, #F0F9FF 100%);
        border-radius: 14px; padding: 20px 22px;
        border-left: 4px solid #4F46E5; margin-bottom: 12px;
    }
    .insight-title { font-size: 0.9rem; font-weight: 700; color: #3730A3; margin-bottom: 10px; }
    .insight-item  { font-size: 0.84rem; color: #475569; margin: 5px 0; line-height: 1.5; }

    /* ---- Interp boxes ---- */
    .interp-box {
        border-radius: 12px; padding: 14px 16px;
        border-left: 4px solid;
    }
    .interp-title  { font-size: 0.88rem; font-weight: 700; margin-bottom: 6px; }
    .interp-count  { font-size: 1.8rem; font-weight: 800; margin: 4px 0; }
    .interp-desc   { font-size: 0.78rem; }

    /* ---- Misc ---- */
    .custom-divider { border: none; border-top: 1.5px solid #E2E8F0; margin: 24px 0; }
    .footer {
        text-align: center; padding: 22px 20px;
        color: #94A3B8; font-size: 0.81rem;
        border-top: 1px solid #E2E8F0; margin-top: 28px;
    }
    .footer span { color: #4F46E5; font-weight: 600; }
    .upload-zone {
        background: #F8FAFF; border: 2px dashed #C7D2FE;
        border-radius: 14px; padding: 22px; text-align: center; margin: 10px 0;
    }

    /* ---- Tabs ---- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 5px; background: #EEF2FF; border-radius: 12px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; font-weight: 600; font-size: 0.86rem;
        color: #64748B; padding: 8px 18px;
    }
    .stTabs [aria-selected="true"] {
        background: white !important; color: #4F46E5 !important;
        box-shadow: 0 2px 8px rgba(79,70,229,0.13);
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] { background: white; border-right: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
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
    if cols.get("rating") and f_rating and cols["rating"] in fdf.columns:
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
C_BLUE   = "#4F46E5"
C_PURPLE = "#7C3AED"
C_SKY    = "#0EA5E9"
C_GREEN  = "#10B981"
C_YELLOW = "#F59E0B"
C_RED    = "#EF4444"
C_PINK   = "#EC4899"
TMPL     = "plotly_white"
COLORS   = [C_BLUE, C_PURPLE, C_SKY, C_GREEN, C_YELLOW, C_RED, C_PINK]


def _base_layout(title, height, **kwargs):
    layout = {
        "title": {
            "text": title,
            "font": {"size": 14, "color": "#1E293B"},
            "x": 0.01
        },
        "template": TMPL,
        "height": height,
        "margin": {"t": 50, "b": 12, "l": 12, "r": 12},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }
    layout.update(kwargs)
    return layout


def create_donut_chart(values, labels, title, colors=None, height=340):
    fig = go.Figure(go.Pie(
        values=values, labels=labels, hole=0.55,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Jumlah: %{value}<br>%{percent}<extra></extra>",
        marker=dict(colors=colors or COLORS, line=dict(color="white", width=2)),
    ))
    fig.update_layout(**_base_layout(title, height,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)))
    return fig


def create_bar_chart(x, y, title, xlabel="", ylabel="Jumlah", color=C_BLUE, height=340):
    fig = go.Figure(go.Bar(
        x=x, y=y, marker_color=color,
        hovertemplate=f"<b>%{{x}}</b><br>{ylabel}: %{{y}}<extra></extra>",
    ))
    fig.update_layout(**_base_layout(title, height,
        xaxis_title=xlabel, yaxis_title=ylabel, showlegend=False))
    return fig


def create_horizontal_bar_chart(df_q, title="Rata-rata Skor Kuesioner", height=520):
    """Sorted ascending (bottom = lowest on screen = smallest score)."""
    dfs = df_q.sort_values("rata_rata", ascending=True).copy()
    bar_colors = [C_GREEN if v >= 4.0 else (C_YELLOW if v >= 3.0 else C_RED)
                  for v in dfs["rata_rata"]]
    fig = go.Figure(go.Bar(
        x=dfs["rata_rata"], y=dfs["label"], orientation="h",
        marker_color=bar_colors,
        customdata=dfs["pertanyaan"],
        hovertemplate=(
            "<b>%{y}</b><br>Pertanyaan: %{customdata}<br>"
            "Rata-rata: <b>%{x:.2f}</b><extra></extra>"
        ),
        text=dfs["rata_rata"].round(2),
        textposition="outside",
        textfont=dict(size=10, color="#1E293B"),
    ))
    dyn_h = max(height, len(dfs) * 36 + 90)
    fig.update_layout(**_base_layout(title, dyn_h,
        xaxis=dict(range=[0, 5.4], title="Rata-rata Skor", tickformat=".1f"),
        yaxis=dict(title=""),
        margin=dict(t=50, b=12, l=65, r=65),
        showlegend=False))
    for xv, lbl, cl in [(3.0, "Cukup", C_YELLOW), (4.0, "Kuat", C_GREEN)]:
        fig.add_vline(x=xv, line_dash="dash", line_color=cl,
                      annotation_text=lbl, annotation_position="top",
                      annotation_font_size=9)
    return fig


# =============================================================================
# KPI CARD HTML
# =============================================================================
def create_metric_card(icon, value, label):
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""


# =============================================================================
# CSV DOWNLOAD HELPER
# =============================================================================
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8-sig")


# =============================================================================
# HERO
# =============================================================================
def render_hero():
    now_str = datetime.now().strftime("%d %B %Y, %H:%M WIB")
    st.markdown(f"""
    <div class="hero-section fade-in">
        <div class="hero-title">📊 Dashboard Analisis Penggunaan Aplikasi DANA</div>
        <div class="hero-subtitle">
            Visualisasi data survei responden dan ulasan pengguna untuk memahami pola penggunaan,
            pengalaman transaksi, dan sentimen pengguna terhadap aplikasi DANA.
        </div>
        <div class="badge-container">
            <span class="badge">📈 Streamlit Dashboard</span>
            <span class="badge">📋 Survey Analysis</span>
            <span class="badge">💬 Review Scraping</span>
            <span class="badge">🗂️ Interactive Report</span>
        </div>
        <div style="margin-top:14px; font-size:0.76rem; opacity:0.72;">
            🕒 Last updated: {now_str}
        </div>
    </div>""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
def render_sidebar_filters(survey_df, survey_cols, review_df, review_cols, load_errors):
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center;padding:12px 0 6px;'>
            <div style='font-size:1.5rem;'>📊</div>
            <div style='font-weight:800;font-size:1.02rem;color:#1E293B;margin-top:4px;'>Filter Dashboard</div>
            <div style='font-size:0.73rem;color:#64748B;'>Aplikasi DANA Analytics</div>
        </div>
        <hr style='border-color:#E2E8F0;margin:8px 0 14px;'>
        """, unsafe_allow_html=True)

        # ---- Clear cache button ----
        if st.button("🔄 Refresh Data / Clear Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # ---- Survey filters ----
        st.markdown("#### 👥 Filter Survei")
        f_gender, f_usia, f_freq = ["Semua"], None, ["Semua"]

        if survey_df is not None and not survey_df.empty:
            g_col = survey_cols.get("gender")
            if g_col and g_col in survey_df.columns:
                opts = sorted(survey_df[g_col].dropna().unique().tolist())
                sel = st.multiselect("Jenis Kelamin", options=opts, default=[],
                                     placeholder="Semua gender")
                f_gender = sel if sel else ["Semua"]
            else:
                st.caption("⚠️ Kolom gender tidak terdeteksi")

            u_col = survey_cols.get("usia")
            if u_col and u_col in survey_df.columns:
                un = pd.to_numeric(survey_df[u_col], errors="coerce").dropna()
                if not un.empty:
                    lo, hi = int(un.min()), int(un.max())
                    if lo == hi: hi = lo + 1
                    f_usia = st.slider("Rentang Usia", lo, hi, (lo, hi))

            fr_col = survey_cols.get("freq")
            if fr_col and fr_col in survey_df.columns:
                fr_opts = sorted(survey_df[fr_col].dropna().unique().tolist())
                sel2 = st.multiselect("Frekuensi Penggunaan", options=fr_opts, default=[],
                                      placeholder="Semua frekuensi")
                f_freq = sel2 if sel2 else ["Semua"]
        else:
            st.caption("_Data survei tidak tersedia_")

        st.markdown("---")

        # ---- Review filters ----
        st.markdown("#### 💬 Filter Ulasan")
        f_rating   = [1, 2, 3, 4, 5]
        f_sentiment = ["Semua"]
        f_date_range = None
        f_search   = ""

        if review_df is not None and not review_df.empty:
            f_rating = st.multiselect("Rating ⭐", options=[1, 2, 3, 4, 5],
                                      default=[1, 2, 3, 4, 5],
                                      format_func=lambda x: f"{'⭐'*x} ({x})")
            sent_sel = st.multiselect("Sentimen", options=["Positif", "Netral", "Negatif"],
                                      default=[], placeholder="Semua sentimen")
            f_sentiment = sent_sel if sent_sel else ["Semua"]

            tgl_col = review_cols.get("tanggal")
            if tgl_col and tgl_col in review_df.columns:
                tgl = review_df[tgl_col]
                if pd.api.types.is_datetime64_any_dtype(tgl):
                    valid = tgl.dropna()
                    if not valid.empty:
                        mn, mx = valid.min().date(), valid.max().date()
                        if mn == mx: mx = date.today()
                        dr = st.date_input("Rentang Tanggal", value=(mn, mx),
                                           min_value=mn, max_value=mx)
                        if len(dr) == 2:
                            f_date_range = dr

            f_search = st.text_input("🔍 Cari kata dalam ulasan",
                                     placeholder="Ketik kata kunci...")
        else:
            st.caption("_Data ulasan tidak tersedia_")

        st.markdown("---")

        # ---- Tambahan Limit ----
        st.markdown("#### ⚙️ Tampilan Tabel")
        f_limit_str = st.selectbox("Jumlah ulasan yang ditampilkan", 
                                   options=["10", "25", "50", "100", "Semua"], 
                                   index=2)
        f_limit = None if f_limit_str == "Semua" else int(f_limit_str)

        st.markdown("---")

        # ---- Debug expander ----
        with st.expander("🔧 Debug File Path"):
            st.code(f"""BASE_DIR  : {BASE_DIR}
DATA_DIR  : {DATA_DIR}
Survey    : {SURVEY_PATH}
  → exists : {SURVEY_PATH.exists()}
  → size   : {SURVEY_PATH.stat().st_size if SURVEY_PATH.exists() else 'N/A'} bytes
Review    : {REVIEW_PATH}
  → exists : {REVIEW_PATH.exists()}
  → size   : {REVIEW_PATH.stat().st_size if REVIEW_PATH.exists() else 'N/A'} bytes
Kuesioner : {QUESTIONNAIRE_PATH}
  → exists : {QUESTIONNAIRE_PATH.exists()}
  → size   : {QUESTIONNAIRE_PATH.stat().st_size if QUESTIONNAIRE_PATH.exists() else 'N/A'} bytes
""", language="")
            try:
                files = [f.name for f in DATA_DIR.glob("*") if f.is_file()]
                st.write("Files in data/:", files)
            except Exception as e:
                st.write("Tidak bisa list folder:", e)
            if load_errors:
                st.markdown("**Load errors:**")
                for k, v in load_errors.items():
                    st.warning(f"[{k}] {v}")

        st.markdown("""
        <div style='text-align:center;padding:10px 0 0;font-size:0.7rem;color:#94A3B8;'>
            Built with ❤️ Streamlit
        </div>""", unsafe_allow_html=True)

    return f_gender, f_usia, f_freq, f_rating, f_sentiment, f_date_range, f_search, f_limit


# =============================================================================
# KPI SECTION
# =============================================================================
def render_kpi_section(survey_filtered, review_filtered, q_df):
    n_resp   = len(survey_filtered) if survey_filtered is not None else 0
    n_ulasan = len(review_filtered) if review_filtered is not None else 0

    avg_q = 0.0
    if q_df is not None and "rata_rata" in q_df.columns and not q_df.empty:
        avg_q = float(q_df["rata_rata"].mean())

    avg_rating = 0.0
    pct_pos    = 0.0
    if review_filtered is not None and not review_filtered.empty:
        if "rating" in review_filtered.columns:
            avg_rating = float(pd.to_numeric(review_filtered["rating"], errors="coerce").mean())
        if "sentimen" in review_filtered.columns:
            total = len(review_filtered)
            pos   = (review_filtered["sentimen"] == "Positif").sum()
            pct_pos = pos / total * 100 if total > 0 else 0.0

    c1, c2, c3, c4, c5 = st.columns(5)
    items = [
        (c1, "👥", f"{n_resp:,}", "Responden Survei"),
        (c2, "💬", f"{n_ulasan:,}", "Ulasan Pengguna"),
        (c3, "📋", f"{avg_q:.2f} / 5", "Rata-rata Skor Kuesioner"),
        (c4, "⭐", f"{avg_rating:.1f} / 5" if avg_rating else "—", "Rata-rata Rating"),
        (c5, "😊", f"{pct_pos:.1f}%", "Sentimen Positif"),
    ]
    for col, icon, val, lbl in items:
        with col:
            st.markdown(create_metric_card(icon, val, lbl), unsafe_allow_html=True)


# =============================================================================
# TAB 1 — OVERVIEW
# =============================================================================
def render_overview(survey_filtered, survey_cols, review_filtered, review_cols):
    if survey_filtered is None or survey_filtered.empty:
        st.info("📭 Data survei tidak tersedia atau tidak ada yang cocok dengan filter.")
        return

    col1, col2 = st.columns(2)

    # Gender donut
    with col1:
        g_col = survey_cols.get("gender")
        if g_col and g_col in survey_filtered.columns:
            gd = survey_filtered[g_col].value_counts()
            if not gd.empty:
                fig = create_donut_chart(gd.values.tolist(), gd.index.tolist(),
                                         "Distribusi Jenis Kelamin",
                                         colors=[C_BLUE, C_PINK, C_GREEN, C_YELLOW])
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Distribusi gender responden survei DANA")
        else:
            st.warning("⚠️ Kolom jenis kelamin tidak terdeteksi.")

    # Usia bar
    with col2:
        u_col = survey_cols.get("usia")
        if u_col and u_col in survey_filtered.columns:
            ua = pd.to_numeric(survey_filtered[u_col], errors="coerce").dropna().astype(int)
            if not ua.empty:
                uc = ua.value_counts().sort_index()
                fig = create_bar_chart(uc.index.astype(str).tolist(), uc.values.tolist(),
                                       "Distribusi Usia Responden",
                                       xlabel="Usia (tahun)", ylabel="Jumlah Responden",
                                       color=C_PURPLE)
                st.plotly_chart(fig, use_container_width=True)
                st.caption("Sebaran usia responden survei DANA")
        else:
            st.warning("⚠️ Kolom usia tidak terdeteksi.")

    # Frekuensi bar
    fr_col = survey_cols.get("freq")
    if fr_col and fr_col in survey_filtered.columns:
        fd = survey_filtered[fr_col].value_counts()
        if not fd.empty:
            fig = create_bar_chart(fd.index.tolist(), fd.values.tolist(),
                                   "Frekuensi Penggunaan Aplikasi DANA",
                                   xlabel="Frekuensi", ylabel="Jumlah Responden",
                                   color=C_SKY, height=340)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Seberapa sering responden menggunakan DANA")
    else:
        st.warning("⚠️ Kolom frekuensi tidak terdeteksi.")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ---- Auto Insight ----
    st.markdown("### 💡 Insight Otomatis")
    insights = []

    g_col = survey_cols.get("gender")
    if g_col and g_col in survey_filtered.columns:
        top_g = survey_filtered[g_col].value_counts()
        if not top_g.empty:
            pct = top_g.values[0] / len(survey_filtered) * 100
            insights.append(f"👤 <b>Gender mayoritas</b> responden adalah "
                            f"<b>{top_g.index[0]}</b> "
                            f"({top_g.values[0]} dari {len(survey_filtered)} responden, {pct:.1f}%)")

    u_col = survey_cols.get("usia")
    if u_col and u_col in survey_filtered.columns:
        un = pd.to_numeric(survey_filtered[u_col], errors="coerce").dropna()
        if not un.empty:
            dominant = int(un.mode()[0])
            avg_age  = un.mean()
            insights.append(f"🎂 <b>Usia dominan</b> responden adalah "
                            f"<b>{dominant} tahun</b> (rata-rata {avg_age:.1f} tahun)")

    fr_col = survey_cols.get("freq")
    if fr_col and fr_col in survey_filtered.columns:
        top_f = survey_filtered[fr_col].value_counts()
        if not top_f.empty:
            insights.append(f"📱 <b>Frekuensi penggunaan DANA</b> terbanyak: "
                            f"<b>{top_f.index[0]}</b> ({top_f.values[0]} responden)")

    if review_filtered is not None and not review_filtered.empty:
        if "rating" in review_filtered.columns:
            avg_r = pd.to_numeric(review_filtered["rating"], errors="coerce").mean()
            insights.append(f"⭐ <b>Rata-rata rating</b> ulasan pengguna: <b>{avg_r:.2f} / 5.0</b>")
        if "sentimen" in review_filtered.columns:
            total = len(review_filtered)
            pos   = (review_filtered["sentimen"] == "Positif").sum()
            pct   = pos / total * 100 if total > 0 else 0
            insights.append(f"😊 <b>Sentimen positif</b>: <b>{pct:.1f}%</b> dari {total} ulasan")

    if insights:
        items_html = "".join(
            f'<div class="insight-item">✦ &nbsp;<span>{i}</span></div>' for i in insights
        )
        st.markdown(f"""
        <div class="insight-card">
            <div class="insight-title">📌 Temuan Utama Berdasarkan Data</div>
            {items_html}
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Belum cukup data untuk insight otomatis.")

    with st.expander("📖 Metodologi Singkat"):
        st.markdown("""
        - **Data Survei** digunakan untuk melihat karakteristik dan persepsi responden.
        - **Data Ulasan** digunakan untuk melihat rating dan sentimen pengguna secara agregat.
        - **Sentimen** ditentukan dari rating: ≥4 = Positif, 3 = Netral, ≤2 = Negatif.
        - **Skor Kuesioner** menggunakan skala Likert 1–5 (1 = Sangat Tidak Setuju, 5 = Sangat Setuju).
        """)

    with st.expander("📌 Catatan Interpretasi"):
        st.markdown("""
        **Skor Kuesioner:**
        - 🟢 **≥ 4.00** → Kuat / Baik
        - 🟡 **3.00 – 3.99** → Cukup
        - 🔴 **< 3.00** → Perlu Perhatian

        **Sentimen Ulasan:**
        - 😊 **Positif** → Rating 4–5 ⭐
        - 😐 **Netral** → Rating 3 ⭐
        - 😞 **Negatif** → Rating 1–2 ⭐
        """)


# =============================================================================
# TAB 2 — ANALISIS SURVEI
# =============================================================================
def render_survey_analysis(survey_filtered, survey_cols, q_df):
    if q_df is None or q_df.empty:
        st.warning("⚠️ Data kuesioner tidak tersedia.")
        return

    # Horizontal bar chart
    st.markdown("### 📊 Rata-rata Skor Per Indikator Kuesioner")
    fig = create_horizontal_bar_chart(q_df, "Rata-rata Skor Tiap Pertanyaan Kuesioner (Q1–Q20)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Hover pada bar untuk melihat teks pertanyaan lengkap. Warna: 🟢 Kuat (≥4) · 🟡 Cukup (3–4) · 🔴 Perlu Perhatian (<3)")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Top 5 & Bottom 5
    st.markdown("### 🏆 Indikator Terkuat vs. Perlu Perhatian")
    col1, col2 = st.columns(2)

    def short_q(text, maxlen=62):
        t = str(text)
        return t[:maxlen] + "…" if len(t) > maxlen else t

    with col1:
        st.markdown("#### ✅ Top 5 Tertinggi")
        for i, row in enumerate(q_df.nlargest(5, "rata_rata").itertuples(), 1):
            st.markdown(f"""
            <div class="rank-card">
                <div class="rank-badge rank-top">{i}</div>
                <div class="rank-label"><b>{row.label}</b> — {short_q(row.pertanyaan)}</div>
                <div class="rank-score">{row.rata_rata:.2f}</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("#### ⚠️ Bottom 5 Terendah")
        for i, row in enumerate(q_df.nsmallest(5, "rata_rata").itertuples(), 1):
            st.markdown(f"""
            <div class="rank-card">
                <div class="rank-badge rank-bottom">{i}</div>
                <div class="rank-label"><b>{row.label}</b> — {short_q(row.pertanyaan)}</div>
                <div class="rank-score">{row.rata_rata:.2f}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Interpretasi
    st.markdown("### 🎯 Interpretasi Skor")
    strong   = q_df[q_df["rata_rata"] >= 4.0]
    moderate = q_df[(q_df["rata_rata"] >= 3.0) & (q_df["rata_rata"] < 4.0)]
    weak     = q_df[q_df["rata_rata"] < 3.0]

    ic1, ic2, ic3 = st.columns(3)
    for col, cnt, bg, bc, tc, title, desc in [
        (ic1, len(strong),   "#D1FAE5","#10B981","#065F46","🟢 Kuat / Baik (≥ 4.00)","indikator dengan skor tinggi"),
        (ic2, len(moderate), "#FEF3C7","#F59E0B","#92400E","🟡 Cukup (3.00–3.99)","indikator dengan skor sedang"),
        (ic3, len(weak),     "#FEE2E2","#EF4444","#991B1B","🔴 Perlu Perhatian (< 3.00)","indikator perlu ditingkatkan"),
    ]:
        with col:
            st.markdown(f"""
            <div style='background:{bg};border-radius:12px;padding:16px 18px;border-left:4px solid {bc};'>
                <div style='font-weight:700;color:{tc};font-size:0.88rem;'>{title}</div>
                <div style='font-size:1.85rem;font-weight:800;color:{bc};margin:6px 0;'>{cnt}</div>
                <div style='font-size:0.78rem;color:{tc};'>{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Full question list
    with st.expander("📋 Lihat Daftar Lengkap Pertanyaan (Q1–Q20)"):
        for _, row in q_df.iterrows():
            c = C_GREEN if row["rata_rata"] >= 4.0 else (C_YELLOW if row["rata_rata"] >= 3.0 else C_RED)
            interp = "✅ Kuat" if row["rata_rata"] >= 4.0 else ("🟡 Cukup" if row["rata_rata"] >= 3.0 else "⚠️ Perlu Perhatian")
            st.markdown(f"""
            <div style='display:flex;align-items:flex-start;gap:10px;padding:9px 0;border-bottom:1px solid #F1F5F9;'>
                <div style='background:#EEF2FF;color:#4F46E5;font-weight:700;
                            padding:3px 9px;border-radius:7px;font-size:0.8rem;min-width:38px;text-align:center;'>
                    {row['label']}
                </div>
                <div style='flex:1;font-size:0.83rem;color:#334155;'>{row['pertanyaan']}</div>
                <div style='font-weight:700;color:{c};font-size:0.88rem;min-width:48px;text-align:right;'>
                    {row['rata_rata']:.2f}
                </div>
                <div style='font-size:0.76rem;color:{c};min-width:95px;'>{interp}</div>
            </div>""", unsafe_allow_html=True)

    # Insight kuesioner
    if not q_df.empty:
        best = q_df.loc[q_df["rata_rata"].idxmax()]
        worst = q_df.loc[q_df["rata_rata"].idxmin()]
        avg_all = q_df["rata_rata"].mean()
        st.markdown(f"""
        <div class="insight-card" style="margin-top:16px;">
            <div class="insight-title">📌 Insight Kuesioner</div>
            <div class="insight-item">✦ &nbsp;Rata-rata keseluruhan skor kuesioner: <b>{avg_all:.2f} / 5.00</b></div>
            <div class="insight-item">✦ &nbsp;Indikator tertinggi: <b>{best['label']}</b> — {str(best['pertanyaan'])[:70]} (<b>{best['rata_rata']:.2f}</b>)</div>
            <div class="insight-item">✦ &nbsp;Indikator terendah: <b>{worst['label']}</b> — {str(worst['pertanyaan'])[:70]} (<b>{worst['rata_rata']:.2f}</b>)</div>
        </div>""", unsafe_allow_html=True)


# =============================================================================
# TAB 3 — ANALISIS ULASAN
# =============================================================================
def render_review_analysis(review_filtered, review_cols, review_raw_count, f_limit):
    if review_filtered is None or review_filtered.empty:
        st.info("📭 Data ulasan tidak tersedia atau filter tidak menghasilkan data.")
        return

    filtered_count = len(review_filtered)
    if filtered_count < review_raw_count:
        st.info(f"🔍 Menampilkan **{filtered_count}** dari {review_raw_count} ulasan berdasarkan filter yang dipilih.")
    else:
        st.info(f"📊 Menampilkan seluruh **{review_raw_count}** ulasan.")

    st.markdown("### 📌 Ringkasan Ulasan")
    pos_c = (review_filtered["sentimen"] == "Positif").sum() if "sentimen" in review_filtered.columns else 0
    net_c = (review_filtered["sentimen"] == "Netral").sum() if "sentimen" in review_filtered.columns else 0
    neg_c = (review_filtered["sentimen"] == "Negatif").sum() if "sentimen" in review_filtered.columns else 0
    r_col = review_cols.get("rating")
    avg_r = pd.to_numeric(review_filtered[r_col], errors="coerce").mean() if r_col and r_col in review_filtered.columns else 0.0
    
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric("Total Ulasan", f"{filtered_count:,}")
    mc2.metric("Positif", f"{pos_c:,}")
    mc3.metric("Netral", f"{net_c:,}")
    mc4.metric("Negatif", f"{neg_c:,}")
    mc5.metric("Rata-rata Rating", f"{avg_r:.2f} ⭐")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # Donut sentimen
    with col1:
        if "sentimen" in review_filtered.columns:
            sc = review_filtered["sentimen"].value_counts()
            sent_colors = {"Positif": C_GREEN, "Netral": C_YELLOW, "Negatif": C_RED}
            fig = create_donut_chart(
                sc.values.tolist(), sc.index.tolist(),
                "Distribusi Sentimen Ulasan",
                colors=[sent_colors.get(s, "#94A3B8") for s in sc.index]
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Sentimen berdasarkan rating pengguna (≥4 Positif, 3 Netral, ≤2 Negatif)")

    # Bar rating
    with col2:
        if r_col and r_col in review_filtered.columns:
            rd = pd.to_numeric(review_filtered[r_col], errors="coerce").dropna().astype(int)
            rc = rd.value_counts().sort_index()
            bar_colors = [C_RED if r <= 2 else (C_YELLOW if r == 3 else C_GREEN) for r in rc.index]
            fig2 = go.Figure(go.Bar(
                x=[f"{r} ⭐" for r in rc.index],
                y=rc.values.tolist(),
                marker_color=bar_colors,
                hovertemplate="<b>Rating %{x}</b><br>Jumlah: %{y}<extra></extra>",
            ))
            fig2.update_layout(**_base_layout("Distribusi Rating (1–5 ⭐)", 340,
                               xaxis_title="Rating", yaxis_title="Jumlah Ulasan", showlegend=False))
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("Sebaran rating bintang dari seluruh ulasan")

    # Line chart tren
    tgl_col = review_cols.get("tanggal")
    if tgl_col and tgl_col in review_filtered.columns:
        tgl = review_filtered[tgl_col]
        if pd.api.types.is_datetime64_any_dtype(tgl):
            daily = review_filtered.groupby(tgl.dt.date).size().reset_index(name="jumlah")
            if len(daily) > 1:
                fig3 = go.Figure(go.Scatter(
                    x=daily.iloc[:, 0], y=daily["jumlah"],
                    mode="lines+markers",
                    line=dict(color=C_BLUE, width=2.5),
                    marker=dict(size=5, color=C_PURPLE),
                    fill="tozeroy", fillcolor="rgba(79,70,229,0.06)",
                    hovertemplate="<b>%{x}</b><br>Jumlah Ulasan: %{y}<extra></extra>",
                ))
                fig3.update_layout(**_base_layout("Tren Jumlah Ulasan per Hari", 310,
                                   xaxis_title="Tanggal", yaxis_title="Jumlah Ulasan"))
                st.plotly_chart(fig3, use_container_width=True)
                st.caption("Tren harian ulasan pengguna dari data scraping")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Tabel ulasan
    st.markdown("### 📋 Tabel Ulasan Hasil Filter")
    
    display_review_df = review_filtered.copy()
    if review_cols.get("username") and review_cols["username"] in display_review_df.columns:
        display_review_df = display_review_df.drop(columns=[review_cols["username"]])
        
    cols_order = []
    for c in ["rating", "tanggal", "ulasan", "sentimen"]:
        actual_c = review_cols.get(c, c)
        if actual_c in display_review_df.columns:
            cols_order.append(actual_c)
    
    for c in display_review_df.columns:
        if c not in cols_order:
            cols_order.append(c)
            
    display_review_df = display_review_df[cols_order]
    
    if f_limit is not None:
        display_review_df = display_review_df.head(f_limit)
        
    idx_start = 0
    idx_end = len(display_review_df) - 1 if len(display_review_df) > 0 else 0
    st.caption(f"Menampilkan index {idx_start} sampai {idx_end} (Index tabel dimulai dari 0). Terdapat total {len(display_review_df)} baris pada tabel.")
    
    try:
        col_cfg = {}
        if review_cols.get("rating") in display_review_df.columns:
            col_cfg[review_cols["rating"]] = st.column_config.NumberColumn("Rating", width="small", format="%d ⭐")
        if review_cols.get("tanggal") in display_review_df.columns:
            col_cfg[review_cols["tanggal"]] = st.column_config.DatetimeColumn("Tanggal", width="medium", format="DD-MM-YYYY HH:mm")
        if review_cols.get("ulasan") in display_review_df.columns:
            col_cfg[review_cols["ulasan"]] = st.column_config.TextColumn("Ulasan Pengguna", width="large")
        if "sentimen" in display_review_df.columns:
            col_cfg["sentimen"] = st.column_config.TextColumn("Sentimen", width="small")
            
        st.dataframe(
            display_review_df,
            use_container_width=True,
            height=520,
            hide_index=True,
            column_config=col_cfg
        )
    except Exception:
        st.dataframe(display_review_df, use_container_width=True, height=520)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
    
    st.markdown("### 📖 Contoh Ulasan Lengkap")
    st.caption("Klik untuk membaca isi ulasan selengkapnya (tanpa terpotong).")
    
    for i, row in display_review_df.head(10).iterrows():
        tgl = row[review_cols['tanggal']] if review_cols.get('tanggal') in row else "-"
        rat = row[review_cols['rating']] if review_cols.get('rating') in row else 0
        sen = row['sentimen'] if 'sentimen' in row else "-"
        txt = row[review_cols['ulasan']] if review_cols.get('ulasan') in row else "-"
        
        with st.expander(f"✨ {sen} | Rating {rat} ⭐ | {tgl}"):
            st.write(txt)


# =============================================================================
# TAB 4 — DATA MENTAH
# =============================================================================
def render_raw_data(survey_filtered, review_filtered, review_raw_count, f_limit):
    st.markdown("### 📁 Data Survei")
    if survey_filtered is not None and not survey_filtered.empty:
        st.info(f"Total baris: **{len(survey_filtered)}** | Kolom: **{len(survey_filtered.columns)}**")
        st.dataframe(survey_filtered, use_container_width=True, height=340)
        st.download_button(
            "⬇️ Download Data Survei (CSV)",
            data=convert_df_to_csv(survey_filtered),
            file_name=f"survey_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True,
        )
    else:
        st.info("📭 Data survei tidak tersedia.")

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    st.markdown("### 📁 Data Ulasan")
    if review_filtered is not None and not review_filtered.empty:
        filtered_count = len(review_filtered)
        if filtered_count < review_raw_count:
            st.info(f"Total ulasan asli: **{review_raw_count}** | Setelah filter: **{filtered_count}**")
        else:
            st.info(f"Total ulasan: **{review_raw_count}**")

        display_raw = review_filtered.copy()
        
        # Hide username for display
        u_col = next((c for c in display_raw.columns if c.lower() in ["username", "user", "pengguna"]), None)
        if u_col:
            display_raw = display_raw.drop(columns=[u_col])
            
        if f_limit is not None:
            display_raw = display_raw.head(f_limit)
            
        st.caption(f"Menampilkan {len(display_raw)} data di tabel (Index dimulai dari 0).")
        st.dataframe(display_raw, use_container_width=True, height=400)
        
        st.download_button(
            "⬇️ Download Semua Ulasan Hasil Filter (CSV)",
            data=convert_df_to_csv(review_filtered),
            file_name=f"ulasan_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv", use_container_width=True,
        )
    else:
        st.info("📭 Data ulasan tidak tersedia.")


# =============================================================================
# UPLOAD FALLBACK
# =============================================================================
def render_upload_section(missing_keys):
    if not missing_keys:
        return {}
    uploaded = {}
    st.markdown("""
    <div class='upload-zone'>
        <div style='font-size:1.3rem;'>📁</div>
        <div style='font-weight:700;color:#4F46E5;margin:6px 0 3px;'>Upload File Data Manual</div>
        <div style='font-size:0.8rem;color:#64748B;'>
            File tidak ditemukan di folder <code>data/</code>.<br>
            Upload di sini untuk melanjutkan, atau letakkan file di <code>data/</code> lalu klik Refresh Cache di sidebar.
        </div>
    </div>""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if "survey" in missing_keys:
            f = st.file_uploader("📋 survey_clean.xlsx", type=["xlsx"], key="up_survey")
            if f:
                try:
                    uploaded["survey"] = pd.read_excel(f, engine="openpyxl")
                    st.success("✅ Survey dimuat!")
                except Exception as e:
                    st.error(f"Gagal: {e}")
    with col_b:
        if "ulasan" in missing_keys:
            f = st.file_uploader("💬 ulasan_clean.xlsx", type=["xlsx"], key="up_ulasan")
            if f:
                try:
                    uploaded["ulasan"] = pd.read_excel(f, engine="openpyxl")
                    st.success("✅ Ulasan dimuat!")
                except Exception as e:
                    st.error(f"Gagal: {e}")
    with col_c:
        if "kuesioner" in missing_keys:
            f = st.file_uploader("📊 hasil_kuesioner.csv", type=["csv"], key="up_kuesioner")
            if f:
                try:
                    uploaded["kuesioner"] = pd.read_csv(f)
                    st.success("✅ Kuesioner dimuat!")
                except Exception as e:
                    st.error(f"Gagal: {e}")
    return uploaded


# =============================================================================
# FOOTER
# =============================================================================
def render_footer():
    st.markdown("""
    <hr class="custom-divider">
    <div class="footer">
        📊 <span>Dashboard Analisis Penggunaan Aplikasi DANA</span>
        &nbsp;|&nbsp; Developer: <span>Muhammad Arsyad Arroyan</span>
        &nbsp;|&nbsp; Built with ❤️ <span>Streamlit</span> &amp; <span>Plotly</span>
    </div>""", unsafe_allow_html=True)


# =============================================================================
# MAIN
# =============================================================================
def main():
    inject_custom_css()
    render_hero()

    # ---- Load data ----
    with st.spinner("⏳ Memuat data..."):
        data = load_data()

    survey_raw    = data["survey"]
    ulasan_raw    = data["ulasan"]
    kuesioner_raw = data["kuesioner"]
    load_errors   = data["errors"]

    # Show load errors as warnings (not blocking)
    if load_errors:
        for key, msg in load_errors.items():
            label = {"survey": "survey_clean.xlsx",
                     "ulasan": "ulasan_clean.xlsx",
                     "kuesioner": "hasil_kuesioner.csv"}.get(key, key)
            if "kosong" in msg.lower():
                st.warning(f"⚠️ **{label}**: {msg}")
            elif "tidak ditemukan" in msg.lower():
                st.warning(f"📁 **{label}**: {msg}")
            else:
                st.error(f"❌ **{label}**: {msg}")

    # Upload fallback only for truly missing/unreadable files
    missing_keys = list(load_errors.keys())
    if missing_keys:
        uploaded = render_upload_section(missing_keys)
        if "survey"    in uploaded: survey_raw    = uploaded["survey"]
        if "ulasan"    in uploaded: ulasan_raw    = uploaded["ulasan"]
        if "kuesioner" in uploaded: kuesioner_raw = uploaded["kuesioner"]

    # ---- Prepare data ----
    survey_df, survey_cols = prepare_survey_data(survey_raw)
    review_df, review_cols = prepare_review_data(ulasan_raw)
    q_df = prepare_questionnaire_data(survey_df, survey_cols, kuesioner_raw)

    # ---- Sidebar filters ----
    f_gender, f_usia, f_freq, f_rating, f_sentiment, f_date_range, f_search, f_limit = \
        render_sidebar_filters(survey_df, survey_cols, review_df, review_cols, load_errors)

    # ---- Apply filters ----
    survey_filtered = apply_survey_filters(survey_df, survey_cols, f_gender, f_usia, f_freq)
    review_filtered = apply_review_filters(review_df, review_cols,
                                           f_rating, f_sentiment, f_date_range, f_search)
                                           
    review_raw_count = len(review_df) if review_df is not None else 0

    # Empty filter feedback
    if survey_df is not None and survey_filtered is not None and survey_filtered.empty:
        st.info("🔍 Tidak ada data survei yang cocok dengan filter yang dipilih.")
    if review_df is not None and review_filtered is not None and review_filtered.empty:
        st.info("🔍 Tidak ada data ulasan yang cocok dengan filter yang dipilih.")

    # ---- KPI ----
    st.markdown("### 📌 Ringkasan Utama (KPI)")
    render_kpi_section(survey_filtered, review_filtered, q_df)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # ---- 4 Tabs ----
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏠 Overview",
        "📋 Analisis Survei",
        "💬 Analisis Ulasan",
        "📁 Data Mentah",
    ])
    with tab1: render_overview(survey_filtered, survey_cols, review_filtered, review_cols)
    with tab2: render_survey_analysis(survey_filtered, survey_cols, q_df)
    with tab3: render_review_analysis(review_filtered, review_cols, review_raw_count, f_limit)
    with tab4: render_raw_data(survey_filtered, review_filtered, review_raw_count, f_limit)

    render_footer()


if __name__ == "__main__":
    main()
