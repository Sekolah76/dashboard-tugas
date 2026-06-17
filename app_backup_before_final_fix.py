import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import base64
from pathlib import Path
from datetime import datetime

# =====================================================================
# 1. CONSTANTS & CONFIG
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"

# Fixed Baseline Data required by user
KPI_BASE = {
    "responden": 50,
    "ulasan": 330,
    "indikator": 20,
    "skor": 4.00,
    "rating": 3.89,
    "sentimen_pos_pct": 70.3,
    "sentimen_neg_pct": 25.8,
    "sentimen_net_pct": 3.9,
    "pos_count": 232,
    "neg_count": 85,
    "net_count": 13,
    "gender_p_pct": 78,
    "gender_p_count": 39,
    "gender_l_pct": 22,
    "gender_l_count": 11,
    "usia_dom_pct": 72,
    "usia_dom_count": 36,
    "freq_dom_pct": 42,
    "freq_dom_count": 21,
    "var_high_name": "X2 – Praktis",
    "var_high_score": 4.26,
    "var_low_name": "M – Kepercayaan",
    "var_low_score": 3.82,
}

# =====================================================================
# 2. HELPERS
# =====================================================================
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

def load_img_html(filename, class_name="", style="", fallback=""):
    path = ASSETS_DIR / filename
    if path.exists():
        mime = "image/svg+xml" if filename.endswith(".svg") else "image/png"
        b64 = get_base64_of_bin_file(path)
        return f'<img src="data:{mime};base64,{b64}" class="{class_name}" style="{style}" />'
    return f'<img src="{fallback}" class="{class_name}" style="{style}" />'

def mask_username(name):
    if len(name) > 4:
        return name[:4] + "***"
    return name + "***"

# =====================================================================
# 3. DATA LOGIC
# =====================================================================
@st.cache_data
def load_data():
    # Build Survey Data
    survey_data = {
        "id": range(1, 51),
        "gender": ["Perempuan"] * 39 + ["Laki-laki"] * 11,
        "usia": ["18-22 Tahun"] * 36 + ["< 18 Tahun"] * 9 + ["23-27 Tahun"] * 3 + ["> 27 Tahun"] * 2,
        "freq": ["Jarang"] * 21 + ["Kadang-kadang"] * 19 + ["Sering"] * 7 + ["Sangat Sering"] * 3
    }
    df_survey = pd.DataFrame(survey_data)
    
    # Build Review Data
    review_data = {
        "id": range(1, 331),
        "pengguna": [f"user_{i}" for i in range(1, 331)],
        "rating": [5]*220 + [4]*12 + [3]*13 + [2]*12 + [1]*73,
        "sentimen": ["Positif"] * 232 + ["Netral"] * 13 + ["Negatif"] * 85,
        "tanggal": ["10 Jun 2026"] * 82 + ["09 Jun 2026"] * 248,
        "ulasan": ["Aplikasi sangat mudah digunakan dan praktis."] * 232 + 
                  ["Biasanya lancar, tapi kadang ngelag dikit."] * 13 + 
                  ["Saldo hilang tiba-tiba dan CS lambat membalas."] * 85,
        "sumber": ["Play Store"] * 180 + ["App Store"] * 150
    }
    df_review = pd.DataFrame(review_data)
    df_review["pengguna"] = df_review["pengguna"].apply(mask_username)
    
    # Questionnaire Data
    q_data = pd.DataFrame({
        "peringkat": range(1, 21),
        "indikator": [
            "P1 Keamanan Transaksi", "P2 Kemudahan Navigasi", "P3 Kecepatan Transaksi", 
            "P4 Keandalan Aplikasi", "P5 Kejelasan Informasi", "P6 Estetika Visual", 
            "P7 Fitur Pembayaran", "P8 Notifikasi Real-time", "P9 Riwayat Transaksi", 
            "P10 Biaya Admin", "P11 Ketersediaan Promo", "P12 Layanan Pelanggan", 
            "P13 Integrasi Merchant", "P14 Metode Top-up", "P15 Kecepatan Login", 
            "P16 Personalisasi Layanan", "P17 Penanganan Keluhan", "P18 Inovasi Fitur", 
            "P19 Program Loyalitas", "P20 Edukasi Pengguna"
        ],
        "skor": [
            4.46, 4.42, 4.35, 4.31, 4.26, 4.24, 4.19, 4.14, 4.05, 4.01,
            3.97, 3.90, 3.87, 3.83, 3.76, 3.72, 3.68, 3.64, 3.64, 3.64
        ]
    })
    
    return {"survey": df_survey, "review": df_review, "kuesioner": q_data}

# =====================================================================
# 4. SESSION STATE
# =====================================================================
def init_session_state():
    if "app_view" not in st.session_state:
        st.session_state.app_view = "landing"
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Overview"
    if "filter_open" not in st.session_state:
        st.session_state.filter_open = False
    if "fullscreen_chart" not in st.session_state:
        st.session_state.fullscreen_chart = None
        
    if "pending_filters" not in st.session_state:
        st.session_state.pending_filters = {
            "s_gender": "Semua",
            "s_usia": "Semua",
            "s_freq": "Semua",
            "r_rating": "Semua",
            "r_sentimen": "Semua",
        }
    if "applied_filters" not in st.session_state:
        st.session_state.applied_filters = st.session_state.pending_filters.copy()

# =====================================================================
# 5. GLOBAL CSS (PURE CSS, NO JS)
# =====================================================================
def inject_global_css():
    st.markdown("""
    <style>
    :root {
        --dana-blue: #0078FF;
        --dana-blue-2: #0A84FF;
        --dana-blue-dark: #0057D9;
        --navy: #071437;
        --text-main: #0B1536;
        --text-muted: #516482;
        --bg-main: #F5FAFF;
        --card: #FFFFFF;
        --border: #D9E8FF;
        --green: #16C784;
        --red: #F43F5E;
        --yellow: #FBBF24;
    }
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-main);
    }
    
    .stApp {
        background: var(--bg-main);
    }
    
    /* Hide Streamlit Chrome */
    header[data-testid="stHeader"] {display:none !important;}
    #MainMenu {display:none !important;}
    footer {display:none !important;}
    
    /* Animations */
    @keyframes fadeIn { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    .fade-in { animation: fadeIn 0.4s ease-out forwards; }
    
    /* Buttons */
    .btn-primary {
        background: var(--dana-blue); color: white; border: none; padding: 12px 24px; 
        border-radius: 12px; font-weight: 600; cursor: pointer; text-decoration: none; 
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        box-shadow: 0 4px 12px rgba(0, 120, 255, 0.2); transition: all 0.2s;
    }
    .btn-primary:hover { background: var(--dana-blue-dark); transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0, 120, 255, 0.3); color:white;}
    
    .btn-outline {
        background: transparent; color: var(--dana-blue); border: 1.5px solid var(--dana-blue); 
        padding: 12px 24px; border-radius: 12px; font-weight: 600; cursor: pointer; 
        text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        transition: all 0.2s;
    }
    .btn-outline:hover { background: rgba(0,120,255,0.05); transform: translateY(-2px); }
    
    /* Custom Streamlit Buttons for Tabs/Navigation */
    div.stButton > button {
        border-radius: 10px; font-weight: 600; padding: 8px 16px; border: 1px solid transparent; 
        background: transparent; color: var(--text-muted); transition: all 0.2s; box-shadow: none;
    }
    div.stButton > button:hover {
        color: var(--dana-blue); background: rgba(0,120,255,0.05); border-color: rgba(0,120,255,0.1);
    }
    
    /* Glass Cards */
    .dana-card {
        background: var(--card); border: 1px solid var(--border); border-radius: 22px; 
        padding: 24px; box-shadow: 0 10px 30px rgba(0, 102, 255, 0.04); transition: all 0.3s ease;
    }
    .dana-card:hover {
        transform: translateY(-4px); box-shadow: 0 16px 40px rgba(0, 102, 255, 0.08); border-color: var(--dana-blue-2);
    }
    
    /* KPI Row */
    .kpi-container { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
    .kpi-card {
        flex: 1; min-width: 150px; background: white; border: 1px solid var(--border); border-radius: 16px; 
        padding: 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 4px 15px rgba(0,102,255,0.03);
        animation: fadeIn 0.5s ease-out forwards;
    }
    .kpi-icon { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
    .kpi-val { font-size: 28px; font-weight: 800; color: var(--navy); line-height: 1.2; }
    .kpi-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; margin-top: 4px; }
    
    /* Tab System */
    .tabs-wrapper { display: flex; gap: 8px; border-bottom: 2px solid var(--border); margin-bottom: 24px; overflow-x: auto; padding-bottom: 8px;}
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important; border-right: 1px solid var(--border) !important; width: 250px !important;
    }
    
    /* Table Styling */
    div[data-testid="stDataFrame"] {
        border-radius: 16px; overflow: hidden; border: 1px solid var(--border);
    }
    
    /* Fullscreen Modal */
    .fs-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(7, 20, 55, 0.6); 
        backdrop-filter: blur(5px); z-index: 99999; display: flex; align-items: center; justify-content: center;
        animation: fadeIn 0.3s ease-out;
    }
    .fs-modal {
        background: white; width: 92vw; height: 88vh; border-radius: 24px; padding: 24px; 
        display: flex; flex-direction: column; box-shadow: 0 24px 60px rgba(0,0,0,0.2);
    }
    
    /* Search Bar Input */
    input[type="text"] {
        border-radius: 20px; border: 1px solid var(--border); padding: 8px 16px; outline: none; background: #F8FAFC; color: var(--navy); font-size: 14px;
    }
    input[type="text"]:focus { border-color: var(--dana-blue); }
    </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 6. COMPONENTS
# =====================================================================
def render_kpis():
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card" style="animation-delay: 0.1s;">
            <div class="kpi-icon" style="background: linear-gradient(135deg, #0078FF, #0057D9); color: white;">👥</div>
            <div><div class="kpi-val">{KPI_BASE['responden']}</div><div class="kpi-label">Responden</div></div>
        </div>
        <div class="kpi-card" style="animation-delay: 0.2s;">
            <div class="kpi-icon" style="background: linear-gradient(135deg, #06B6D4, #008AA1); color: white;">💬</div>
            <div><div class="kpi-val">{KPI_BASE['ulasan']}</div><div class="kpi-label">Ulasan</div></div>
        </div>
        <div class="kpi-card" style="animation-delay: 0.3s;">
            <div class="kpi-icon" style="background: linear-gradient(135deg, #7C3AED, #5B21B6); color: white;">⭐</div>
            <div><div class="kpi-val">{KPI_BASE['skor']:.2f}</div><div class="kpi-label">Skor Kuesioner</div></div>
        </div>
        <div class="kpi-card" style="animation-delay: 0.4s;">
            <div class="kpi-icon" style="background: linear-gradient(135deg, #FBBF24, #D97706); color: white;">🌟</div>
            <div><div class="kpi-val">{KPI_BASE['rating']:.2f}</div><div class="kpi-label">Rating Rata-rata</div></div>
        </div>
        <div class="kpi-card" style="animation-delay: 0.5s;">
            <div class="kpi-icon" style="background: linear-gradient(135deg, #16C784, #059669); color: white;">😊</div>
            <div><div class="kpi-val">{KPI_BASE['sentimen_pos_pct']}%</div><div class="kpi-label">Sentimen Positif</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_chart_card(title, fig, chart_id, height=350):
    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding: 0 8px;">
        <h4 style="margin: 0; color: var(--navy); font-size: 16px;">{title}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    config = {'displayModeBar': False, 'responsive': True}
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter", color="#516482"))
    
    c1, c2 = st.columns([10, 1])
    with c1:
        st.plotly_chart(fig, use_container_width=True, config=config, key=f"plot_{chart_id}")
    with c2:
        if st.button("⛶", key=f"fs_{chart_id}", help="Buka mode Fullscreen"):
            st.session_state.fullscreen_chart = chart_id
            st.rerun()

def build_donut(labels, values, colors):
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.65, marker_colors=colors, textinfo='percent', hoverinfo='label+value')])
    fig.update_layout(showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    return fig

def build_bar(x, y, color):
    fig = go.Figure(data=[go.Bar(x=x, y=y, marker_color=color, text=y, textposition='auto')])
    return fig

def render_fullscreen_modal(data):
    st.markdown('<div class="fs-overlay">', unsafe_allow_html=True)
    st.markdown('<div class="fs-modal">', unsafe_allow_html=True)
    
    cid = st.session_state.fullscreen_chart
    c1, c2 = st.columns([10, 1])
    with c1: st.markdown(f"<h3 style='color:var(--navy); margin-top:0;'>Fullscreen View: {cid}</h3>", unsafe_allow_html=True)
    with c2: 
        if st.button("❌ Tutup", key="close_fs"):
            st.session_state.fullscreen_chart = None
            st.rerun()
            
    # Chart routing logic
    fig = None
    config = {'displayModeBar': True, 'responsive': True}
    
    if cid == "gender_dist":
        fig = build_donut(["Perempuan", "Laki-laki"], [39, 11], ["#F43F5E", "#06B6D4"])
    elif cid == "usia_dist":
        fig = build_bar(["<18", "18-22", "23-27", ">27"], [9, 36, 3, 2], "#0078FF")
    elif cid == "freq_dist":
        fig = build_bar(["Jarang", "Kadang", "Sering", "Sangat"], [21, 19, 7, 3], "#0078FF")
    elif cid == "vol_dist":
        fig = build_bar(["09 Jun", "10 Jun"], [248, 82], "#0078FF")
    elif cid == "kuesioner_score":
        dfq = data["kuesioner"].sort_values("skor")
        colors = ['#16C784' if v>=4 else '#FBBF24' for v in dfq['skor']]
        fig = go.Figure(data=[go.Bar(y=dfq['indikator'], x=dfq['skor'], orientation='h', marker_color=colors, text=dfq['skor'], textposition='outside')])
    elif cid == "sentimen_dist":
        fig = build_donut(["Positif", "Netral", "Negatif"], [232, 13, 85], ["#16C784", "#FBBF24", "#F43F5E"])
    elif cid == "rating_dist":
        fig = build_bar(["1", "2", "3", "4", "5"], [73, 12, 13, 12, 220], "#F43F5E")
        
    if fig:
        fig.update_layout(height=650, margin=dict(l=40, r=40, t=20, b=40), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Inter"))
        st.plotly_chart(fig, use_container_width=True, config=config, key=f"fs_plot_{cid}")
        
    st.markdown('</div></div>', unsafe_allow_html=True)

# =====================================================================
# 7. FILTER SYSTEM
# =====================================================================
def render_filter_drawer():
    with st.sidebar:
        st.markdown("<h3 style='color:var(--navy); margin-bottom: 24px;'>🎛️ Filter & Control</h3>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:8px;'>SUMBER DATA</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: st.checkbox("Survei", value=True, disabled=True)
        with c2: st.checkbox("Ulasan", value=True, disabled=True)
        
        st.markdown("<hr style='border:none; border-top:1px solid var(--border);'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:12px; font-weight:600; color:var(--text-muted); margin-bottom:8px;'>FILTER ULASAN</div>", unsafe_allow_html=True)
        
        opts_sentimen = ["Semua", "Positif", "Netral", "Negatif"]
        st.session_state.pending_filters["r_sentimen"] = st.selectbox("Sentimen", opts_sentimen, index=opts_sentimen.index(st.session_state.applied_filters["r_sentimen"]))
        
        opts_rating = ["Semua", "5", "4", "3", "2", "1"]
        st.session_state.pending_filters["r_rating"] = st.selectbox("Rating", opts_rating, index=opts_rating.index(st.session_state.applied_filters["r_rating"]))
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Terapkan Filter", type="primary", use_container_width=True):
            st.session_state.applied_filters = st.session_state.pending_filters.copy()
            st.rerun()
            
        if st.button("Reset Filter", use_container_width=True):
            st.session_state.pending_filters = {"s_gender": "Semua", "s_usia": "Semua", "s_freq": "Semua", "r_rating": "Semua", "r_sentimen": "Semua"}
            st.session_state.applied_filters = st.session_state.pending_filters.copy()
            st.rerun()

def apply_filters(data):
    s_df = data["survey"].copy()
    r_df = data["review"].copy()
    af = st.session_state.applied_filters
    
    if af["r_sentimen"] != "Semua":
        r_df = r_df[r_df["sentimen"] == af["r_sentimen"]]
    if af["r_rating"] != "Semua":
        r_df = r_df[r_df["rating"] == int(af["r_rating"])]
        
    return {"survey": s_df, "review": r_df, "kuesioner": data["kuesioner"]}

# =====================================================================
# 8. PAGES
# =====================================================================
def render_landing_page():
    # Header
    st.markdown(f"""
    <div class="fade-in" style="background: rgba(255,255,255,0.9); padding: 16px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); position: sticky; top:0; z-index:100; backdrop-filter: blur(10px);">
        <div>{load_img_html("dana_logo_wordmark_header_480x120.png", style="height: 36px;")}</div>
        <div style="display: flex; gap: 24px; align-items: center; font-weight: 600; font-size: 14px;">
            <span style="color: var(--text-muted); cursor:pointer;">Butuh bantuan?</span>
            <span style="color: var(--dana-blue); cursor:pointer;">Masuk</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Hero
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown("<div class='fade-in' style='padding: 80px 40px;'>", unsafe_allow_html=True)
        st.markdown("<h1 style='color: var(--navy); font-size: 64px; line-height: 1.1; margin-bottom: 24px; font-weight:800;'>DANA Insight<br>Command Center</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: var(--text-muted); font-size: 18px; line-height: 1.6; margin-bottom: 40px; max-width: 520px;'>Dashboard interaktif untuk memahami pengalaman pengguna DANA berdasarkan data survei dan ulasan pengguna.</p>", unsafe_allow_html=True)
        
        btn1, btn2, _ = st.columns([1.2, 1.2, 1])
        with btn1:
            if st.button("📊 Masuk ke Dashboard", type="primary", use_container_width=True):
                st.session_state.app_view = "dashboard"
                st.session_state.active_tab = "Overview"
                st.rerun()
        with btn2:
            if st.button("📄 Lihat Ringkasan", use_container_width=True):
                st.session_state.app_view = "dashboard"
                st.session_state.active_tab = "Lampiran Presentasi"
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"<div class='fade-in' style='padding: 40px; text-align: right;'>{load_img_html('dana_landing_start_1920x1080.png', style='max-width: 100%; object-fit: contain;')}</div>", unsafe_allow_html=True)
        
    st.markdown("<div style='padding: 0 40px;'>", unsafe_allow_html=True)
    render_kpis()
    
    st.markdown("<h3 style='margin-top: 40px; margin-bottom: 20px; font-weight:800; color:var(--navy);'>Modul yang Tersedia</h3>", unsafe_allow_html=True)
    m1, m2, m3, m4, m5 = st.columns(5)
    
    modules = [
        ("Overview", m1, "🏠", "Ringkasan performa utama"),
        ("Analisis Survei", m2, "📋", "Analisis mendalam data survei"),
        ("Analisis Ulasan", m3, "💬", "Eksplorasi opini pengguna"),
        ("Data Explorer", m4, "📊", "Eksplorasi data mentah"),
        ("Lampiran Presentasi", m5, "📁", "Materi ringkasan pelaporan")
    ]
    
    for title, col, icon, desc in modules:
        with col:
            st.markdown(f"""
            <div class="dana-card" style="padding: 20px; text-align: left; height: 160px; display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div style="font-size:24px; margin-bottom:12px; background:var(--bg-main); width:40px; height:40px; display:flex; align-items:center; justify-content:center; border-radius:10px; color:var(--dana-blue);">{icon}</div>
                    <h4 style="margin: 0 0 8px 0; font-size: 15px; font-weight:700;">{title}</h4>
                    <p style="margin: 0; font-size: 13px; color: var(--text-muted); line-height:1.4;">{desc}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Masuk {title}", key=f"btn_mod_{title}"):
                st.session_state.app_view = "dashboard"
                st.session_state.active_tab = title
                st.rerun()

    st.markdown("""
    <div style="background: white; border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-top: 40px; margin-bottom: 60px; display: flex; align-items: flex-start; gap: 16px; box-shadow: 0 10px 30px rgba(0,102,255,0.03);">
        <div style="font-size:24px; color:var(--dana-blue);">🛡️</div>
        <div>
            <div style="color: var(--navy); font-weight: 700; font-size:16px; margin-bottom:4px;">Privasi Pengguna Terlindungi</div>
            <div style="color: var(--text-muted); font-size: 14px;">Seluruh identitas pribadi pengguna disamarkan. Data yang ditampilkan bersifat agregat dan anonim.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_dashboard(data):
    # Sidebar rendering (conditionally inside pages that need filter drawer, but here we use main sidebar for nav)
    with st.sidebar:
        st.markdown(f"<div style='padding: 20px 0 40px 0; text-align:center;'>{load_img_html('dana_logo_wordmark_header_480x120.png', style='height: 32px;')}</div>", unsafe_allow_html=True)
        
        tabs = [("Overview", "🏠"), ("Analisis Survei", "📋"), ("Analisis Ulasan", "💬"), ("Data Explorer", "📊"), ("Lampiran Presentasi", "📁")]
        for tab, icon in tabs:
            is_active = st.session_state.active_tab == tab
            bg = "rgba(0,120,255,0.08)" if is_active else "transparent"
            color = "var(--dana-blue)" if is_active else "var(--text-muted)"
            fw = "700" if is_active else "600"
            
            if st.button(f"{icon} {tab}", key=f"side_{tab}", use_container_width=True):
                st.session_state.active_tab = tab
                st.rerun()
                
            st.markdown(f"""
            <style>
            button[data-testid="baseButton-secondary"]:has(div:contains("{icon} {tab}")) {{
                background-color: {bg} !important; color: {color} !important; font-weight: {fw} !important;
                justify-content: flex-start; padding: 12px 20px !important; border-radius: 12px !important;
            }}
            </style>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='position:absolute; bottom:30px; width:100%; font-size:11px; color:var(--text-muted); text-align:center;'>Data terakhir diperbarui<br><b style='color:var(--navy);'>15 Jun 2026 08:35 WIB</b> 🔄</div>", unsafe_allow_html=True)

    # Topbar
    st.markdown("""
    <div class="fade-in" style="display: flex; justify-content: space-between; align-items: center; padding: 16px 32px; background: rgba(255,255,255,0.9); backdrop-filter: blur(10px); border-radius: 20px; border: 1px solid var(--border); margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.02);">
        <div style="font-weight: 800; color: var(--navy); font-size: 20px;">DANA Insight Command Center</div>
        <div style="display: flex; align-items: center; gap: 20px;">
            <input type="text" placeholder="Cari..." />
            <div style="display: flex; align-items: center; gap: 8px; background: #ECFDF5; padding: 6px 12px; border-radius: 20px; border: 1px solid #A7F3D0;">
                <span style="width:8px; height:8px; background:#10B981; border-radius:50%; display:inline-block;"></span>
                <span style="color: #047857; font-size: 12px; font-weight: 700;">Data Real-time</span>
            </div>
            <span style="font-size:20px; cursor:pointer; color:var(--text-muted);">🔔</span>
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="background: var(--dana-blue); color: white; width: 36px; height: 36px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold;">AD</div>
                <div style="font-size:13px;"><b style="color:var(--navy);">Admin</b><br><span style="color:var(--text-muted);">Administrator</span></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Horizontal Tabs
    st.markdown('<div class="tabs-wrapper fade-in">', unsafe_allow_html=True)
    cols = st.columns(5)
    tabs = ["Overview", "Analisis Survei", "Analisis Ulasan", "Data Explorer", "Lampiran Presentasi"]
    for i, tab in enumerate(tabs):
        with cols[i]:
            if st.button(tab, key=f"top_{tab}", use_container_width=True):
                st.session_state.active_tab = tab
                st.rerun()
            if st.session_state.active_tab == tab:
                st.markdown(f"""
                <style>
                button[data-testid="baseButton-secondary"]:has(div:contains("{tab}")) {{
                    color: var(--dana-blue) !important; border-bottom: 3px solid var(--dana-blue) !important; border-radius:0 !important;
                }}
                </style>
                """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Apply Filters
    f_data = apply_filters(data)

    # Routes
    if st.session_state.active_tab == "Overview":
        render_overview(f_data)
    elif st.session_state.active_tab == "Analisis Survei":
        render_survey(f_data)
    elif st.session_state.active_tab == "Analisis Ulasan":
        render_filter_drawer()
        render_review(f_data)
    elif st.session_state.active_tab == "Data Explorer":
        render_filter_drawer()
        render_explorer(f_data)
    elif st.session_state.active_tab == "Lampiran Presentasi":
        render_attachment(f_data)

    if st.session_state.fullscreen_chart:
        render_fullscreen_modal(f_data)

def render_overview(data):
    st.markdown(f"""
    <div class="fade-in" style="background: linear-gradient(135deg, var(--dana-blue) 0%, var(--dana-blue-dark) 100%); border-radius: 24px; padding: 40px; color: white; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; box-shadow: 0 20px 40px rgba(0,102,255,0.15);">
        <div>
            <h2 style="margin: 0 0 12px 0; font-size: 36px; font-weight:800;">DANA Insight Command Center</h2>
            <p style="margin: 0; opacity: 0.9; font-size: 16px; max-width:600px;">Dashboard interaktif untuk analisis survei & ulasan pengguna DANA secara komprehensif.</p>
        </div>
        <div style="background:rgba(255,255,255,0.2); padding:10px 20px; border-radius:12px; backdrop-filter:blur(10px); font-weight:600; cursor:pointer;">
            ⚙️ Filter Data
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    render_kpis()
    
    st.markdown("""
    <div style="background: #EAF5FF; border: 1px solid var(--dana-blue); border-radius: 12px; padding: 16px 20px; margin-bottom:24px; color:var(--dana-blue-dark); font-weight:500; display:flex; align-items:center; gap:12px;">
        <span>🎛️</span> <b>Menampilkan seluruh data.</b> Tidak ada filter yang mempersempit dataset. Menampilkan seluruh 50 responden & 330 ulasan.
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([2.5, 1])
    with c1:
        mi1, mi2, mi3, mi4 = st.columns(4)
        mi_data = [
            ("Mayoritas Responden", "Perempuan (78%)", "berdasarkan data yang tampil", "👥"),
            ("Frekuensi Terbanyak", "Jarang", "pola penggunaan dominan", "📊"),
            ("Rating Rata-rata", "3.89 / 5", "hasil ulasan pengguna", "⭐"),
            ("Sentimen Dominan", "Positif (70%)", "berdasarkan rating", "😊")
        ]
        cols = [mi1, mi2, mi3, mi4]
        for i, (t, v, sd, icon) in enumerate(mi_data):
            with cols[i]:
                st.markdown(f"""
                <div class="dana-card" style="padding:20px;">
                    <div style="display:flex; gap:12px; align-items:flex-start;">
                        <div style="font-size:24px; background:var(--bg-main); width:40px; height:40px; display:flex; align-items:center; justify-content:center; border-radius:10px;">{icon}</div>
                        <div>
                            <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">{t}</div>
                            <div style="font-size: 18px; color: var(--navy); font-weight: 800; margin-top: 4px;">{v}</div>
                            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">{sd}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        cr1, cr2 = st.columns(2)
        with cr1:
            st.markdown('<div class="dana-card" style="margin-bottom:20px;">', unsafe_allow_html=True)
            render_chart_card("Distribusi Gender Responden", build_donut(["Perempuan", "Laki-laki"], [39, 11], ["#F43F5E", "#06B6D4"]), "gender_dist")
            st.markdown('</div><div class="dana-card">', unsafe_allow_html=True)
            render_chart_card("Kelompok Usia Responden", build_bar(["18-22", "23-27", "> 27", "< 18"], [36, 3, 2, 9], "#0A84FF"), "usia_dist")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with cr2:
            st.markdown('<div class="dana-card" style="margin-bottom:20px;">', unsafe_allow_html=True)
            render_chart_card("Frekuensi Penggunaan DANA", build_bar(["Jarang", "Kadang", "Sering", "Sangat"], [21, 19, 7, 3], "#0A84FF"), "freq_dist")
            st.markdown('</div><div class="dana-card">', unsafe_allow_html=True)
            render_chart_card("Volume Ulasan per Tanggal", build_bar(["09 Jun", "10 Jun"], [248, 82], "#0A84FF"), "vol_dist")
            st.markdown('</div>', unsafe_allow_html=True)
            
    with c2:
        st.markdown("""
        <div class="dana-card" style="height: 100%;">
            <h3 style="margin-top: 0; color:var(--navy); font-weight:800; display:flex; align-items:center; gap:8px;">🎯 Kesimpulan Utama</h3>
            <ul style="font-size: 14px; line-height: 1.8; color: var(--text-main); padding-left: 24px; margin-top:20px;">
                <li style="margin-bottom:12px;">Mayoritas responden berjenis kelamin <b>Perempuan</b> = 39 dari 50 = <b>78%</b>.</li>
                <li style="margin-bottom:12px;">Kelompok usia dominan adalah <b>18–22 Tahun</b> = 36 dari 50 = <b>72%</b>.</li>
                <li style="margin-bottom:12px;">Frekuensi penggunaan DANA dominan: <b>Jarang</b> = 21 dari 50 = <b>42%</b>.</li>
                <li style="margin-bottom:12px;">Variabel tertinggi: <b>X2 – Praktis</b> = 4.26.</li>
                <li style="margin-bottom:12px;">Variabel terendah: <b>M – Kepercayaan</b> = 3.82.</li>
                <li style="margin-bottom:12px;">Sentimen positif 232 dari 330 = <span style="color:var(--green); font-weight:700;">70.3%</span>.</li>
                <li style="margin-bottom:12px;">Sentimen negatif 85 dari 330 = <span style="color:var(--red); font-weight:700;">25.8%</span>.</li>
                <li style="margin-bottom:12px;">Sentimen netral 13 dari 330 = <span style="color:var(--yellow); font-weight:700;">3.9%</span>.</li>
            </ul>
            <div style="background:var(--bg-main); padding:16px; border-radius:12px; margin-top:24px; font-size:13px; border:1px solid var(--border);">
                Secara keseluruhan, DANA memiliki skor kepuasan yang tinggi. Fokus perbaikan disarankan pada area Indikator terendah dan keluhan terbanyak.
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_survey(data):
    st.markdown("""
    <div class="fade-in" style="background: white; border:1px solid var(--border); border-radius: 24px; padding: 40px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.02);">
        <div>
            <h2 style="margin: 0 0 12px 0; font-size: 36px; font-weight:800; color:var(--navy);">Analisis Survei</h2>
            <p style="margin: 0; color: var(--text-muted); font-size: 16px; max-width:600px;">Analisis mendalam hasil survei untuk pengambilan keputusan berbasis data.</p>
        </div>
        <div style="background:var(--bg-main); color:var(--dana-blue); border:1px solid var(--dana-blue); padding:10px 20px; border-radius:12px; font-weight:600; cursor:pointer;">
            ⚙️ Filter Data
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    render_kpis()
    
    c1, c2, c3, c4 = st.columns([1,1,1,1.5])
    with c1: st.markdown("""<div class="dana-card" style="border-top: 4px solid var(--green); text-align:center;"><div style="font-size:12px; font-weight:700; color:var(--text-muted);">INDIKATOR KUAT / BAIK</div><div style="font-size:36px; font-weight:800; color:var(--navy); margin:8px 0;">13</div><div style="font-size:12px; color:var(--green); font-weight:600;">≥ 4.00</div></div>""", unsafe_allow_html=True)
    with c2: st.markdown("""<div class="dana-card" style="border-top: 4px solid var(--yellow); text-align:center;"><div style="font-size:12px; font-weight:700; color:var(--text-muted);">INDIKATOR CUKUP</div><div style="font-size:36px; font-weight:800; color:var(--navy); margin:8px 0;">7</div><div style="font-size:12px; color:var(--yellow); font-weight:600;">3.00 - 3.99</div></div>""", unsafe_allow_html=True)
    with c3: st.markdown("""<div class="dana-card" style="border-top: 4px solid var(--red); text-align:center;"><div style="font-size:12px; font-weight:700; color:var(--text-muted);">PERLU PERHATIAN</div><div style="font-size:36px; font-weight:800; color:var(--navy); margin:8px 0;">0</div><div style="font-size:12px; color:var(--red); font-weight:600;">< 3.00</div></div>""", unsafe_allow_html=True)
    with c4: st.markdown("""<div class="dana-card" style="height:100%;"><div style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:12px;">ANALISIS VARIABEL PENELITIAN</div><div style="display:flex; justify-content:space-between; text-align:center;"><div style="flex:1;"><b>X1</b><br><span style="color:var(--green); font-weight:800; font-size:20px;">4.08</span></div><div style="flex:1;"><b>X2</b><br><span style="color:var(--green); font-weight:800; font-size:20px;">4.26</span></div><div style="flex:1;"><b>M</b><br><span style="color:var(--yellow); font-weight:800; font-size:20px;">3.82</span></div><div style="flex:1;"><b>Y</b><br><span style="color:var(--green); font-weight:800; font-size:20px;">4.12</span></div></div></div>""", unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="dana-card" style="height:100%;">', unsafe_allow_html=True)
        dfq = data["kuesioner"].sort_values("skor")
        colors = ['#16C784' if v>=4 else '#FBBF24' for v in dfq['skor']]
        fig = go.Figure(data=[go.Bar(y=dfq['indikator'], x=dfq['skor'], orientation='h', marker_color=colors, text=dfq['skor'], textposition='outside')])
        fig.add_vline(x=4.0, line_dash="dash", line_color="gray", annotation_text="Rata-rata Target (4.00)")
        render_chart_card("Skor 20 Indikator Kuesioner", fig, "kuesioner_score", height=600)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="dana-card" style="margin-bottom: 20px;">
            <h4 style="margin-top:0; color:var(--navy); font-weight:800;">🏆 Top 5 Indikator Tertinggi</h4>
            <div style="margin-top:16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>1. P1 - Keamanan Transaksi</span><b style="color:var(--green);">4.46</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>2. P2 - Kemudahan Navigasi</span><b style="color:var(--green);">4.42</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>3. P3 - Kecepatan Transaksi</span><b style="color:var(--green);">4.35</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>4. P4 - Keandalan Aplikasi</span><b style="color:var(--green);">4.31</b></div>
                <div style="display:flex; justify-content:space-between;"><span>5. P5 - Kejelasan Informasi</span><b style="color:var(--green);">4.26</b></div>
            </div>
        </div>
        <div class="dana-card" style="margin-bottom: 20px;">
            <h4 style="margin-top:0; color:var(--navy); font-weight:800;">⚠️ Bottom 5 Indikator Terendah</h4>
            <div style="margin-top:16px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>1. P16 - Personalisasi Layanan</span><b style="color:var(--yellow);">3.72</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>2. P17 - Penanganan Keluhan</span><b style="color:var(--yellow);">3.68</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>3. P18 - Inovasi Fitur</span><b style="color:var(--yellow);">3.64</b></div>
                <div style="display:flex; justify-content:space-between; margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border);"><span>4. P19 - Program Loyalitas</span><b style="color:var(--yellow);">3.64</b></div>
                <div style="display:flex; justify-content:space-between;"><span>5. P20 - Edukasi Pengguna</span><b style="color:var(--yellow);">3.64</b></div>
            </div>
        </div>
        <div class="dana-card" style="background:var(--dana-blue); color:white;">
            <h4 style="margin-top:0; color:white; font-weight:800;">💡 Insight Utama</h4>
            <p style="font-size:14px; line-height:1.6; opacity:0.9;">Sebagian besar indikator (65%) berada pada kategori Kuat/Baik. Fokus perbaikan strategis harus ditujukan pada personalisasi layanan dan penanganan keluhan.</p>
            <button style="width:100%; padding:10px; border-radius:10px; border:none; background:white; color:var(--dana-blue); font-weight:700; margin-top:10px; cursor:pointer;">Unduh Laporan Analisis</button>
        </div>
        """, unsafe_allow_html=True)

def render_review(data):
    df_u = data["review"]
    t_ulasan = len(df_u)
    
    st.markdown("""
    <div style="background: #EAF5FF; border: 1px solid var(--dana-blue); border-radius: 12px; padding: 16px 20px; margin-bottom:24px; color:var(--dana-blue-dark); font-weight:500; display:flex; align-items:center; gap:12px;">
        <span>ℹ️</span> Menampilkan ringkasan dari hasil ulasan. Data ulasan diambil dari berbagai kanal dan periode waktu yang dipilih.
    </div>
    """, unsafe_allow_html=True)
    
    if t_ulasan == 0:
        st.markdown("""
        <div class="dana-card" style="text-align:center; padding: 60px 20px;">
            <div style="font-size:48px; margin-bottom:16px;">📭</div>
            <h3 style="color:var(--navy);">Tidak ada ulasan ditemukan</h3>
            <p style="color:var(--text-muted);">Silakan ubah filter untuk menampilkan data.</p>
        </div>
        """, unsafe_allow_html=True)
        return
        
    p_pos = (df_u['sentimen'] == 'Positif').sum()
    p_net = (df_u['sentimen'] == 'Netral').sum()
    p_neg = (df_u['sentimen'] == 'Negatif').sum()
    avg_r = df_u['rating'].mean()
    
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.markdown(f"<div class='kpi-card' style='padding:16px;'><div class='kpi-icon' style='background:#0A84FF; color:white;'>💬</div><div><div class='kpi-val'>{t_ulasan}</div><div class='kpi-label'>Total Ulasan</div></div></div>", unsafe_allow_html=True)
    with k2: st.markdown(f"<div class='kpi-card' style='padding:16px;'><div class='kpi-icon' style='background:#16C784; color:white;'>😊</div><div><div class='kpi-val'>{p_pos}</div><div class='kpi-label'>Positif ({(p_pos/t_ulasan*100):.1f}%)</div></div></div>", unsafe_allow_html=True)
    with k3: st.markdown(f"<div class='kpi-card' style='padding:16px;'><div class='kpi-icon' style='background:#FBBF24; color:white;'>😐</div><div><div class='kpi-val'>{p_net}</div><div class='kpi-label'>Netral ({(p_net/t_ulasan*100):.1f}%)</div></div></div>", unsafe_allow_html=True)
    with k4: st.markdown(f"<div class='kpi-card' style='padding:16px;'><div class='kpi-icon' style='background:#F43F5E; color:white;'>😡</div><div><div class='kpi-val'>{p_neg}</div><div class='kpi-label'>Negatif ({(p_neg/t_ulasan*100):.1f}%)</div></div></div>", unsafe_allow_html=True)
    with k5: st.markdown(f"<div class='kpi-card' style='padding:16px;'><div class='kpi-icon' style='background:#7C3AED; color:white;'>⭐</div><div><div class='kpi-val'>{avg_r:.2f}</div><div class='kpi-label'>Rata-rata Rating</div></div></div>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="dana-card" style="height:450px;">', unsafe_allow_html=True)
        render_chart_card("Distribusi Sentimen", build_donut(["Positif", "Netral", "Negatif"], [p_pos, p_net, p_neg], ['#16C784', '#FBBF24', '#F43F5E']), "sentimen_dist", height=300)
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="dana-card" style="height:450px;">', unsafe_allow_html=True)
        r_counts = df_u['rating'].value_counts().sort_index()
        # fill missing indices
        for i in range(1,6):
            if i not in r_counts: r_counts[i] = 0
        r_counts = r_counts.sort_index()
        render_chart_card("Distribusi Rating", build_bar([str(x) for x in r_counts.index], r_counts.values, "#F43F5E"), "rating_dist", height=300)
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="dana-card" style="height:450px;">', unsafe_allow_html=True)
        v_counts = df_u['tanggal'].value_counts().sort_index()
        render_chart_card("Volume Ulasan per Tanggal", build_bar([str(x) for x in v_counts.index], v_counts.values, "#0A84FF"), "vol_dist", height=300)
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown('<div class="dana-card" style="margin-top:24px;">', unsafe_allow_html=True)
    st.markdown("<h4 style='color:var(--navy); font-weight:800; margin-top:0;'>Tabel Contoh Ulasan</h4>", unsafe_allow_html=True)
    st.dataframe(df_u.head(50), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_explorer(data):
    st.markdown("<h2 style='color:var(--navy); font-weight:800;'>Data Explorer</h2>", unsafe_allow_html=True)
    
    st.markdown('<div class="dana-card" style="margin-bottom:24px;">', unsafe_allow_html=True)
    st.markdown("<h4 style='color:var(--navy); font-weight:800; margin-top:0;'>Data Survei Responden</h4>", unsafe_allow_html=True)
    st.dataframe(data["survey"], use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="dana-card">', unsafe_allow_html=True)
    st.markdown("<h4 style='color:var(--navy); font-weight:800; margin-top:0;'>Data Ulasan Pengguna</h4>", unsafe_allow_html=True)
    st.dataframe(data["review"], use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_attachment(data):
    st.markdown("<h2 style='color:var(--navy); font-weight:800; margin-bottom:24px;'>Lampiran Presentasi</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="dana-card" style="margin-bottom:24px; border-left: 6px solid var(--dana-blue);">
        <h3 style="margin-top:0; color:var(--navy); font-weight:800;">Kesimpulan Utama</h3>
        <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:24px; margin-top:20px;">
            <div style="flex:1; min-width:200px;">
                <b style="color:var(--text-muted); font-size:12px; letter-spacing:1px;">PROFIL RESPONDEN</b><br>
                <div style="font-size:32px; font-weight:800; color:var(--navy); margin:8px 0;">50 <span style="font-size:16px; font-weight:600;">Responden</span></div>
                <ul style="padding-left:16px; font-size:14px; margin-top:8px; line-height:1.6;">
                    <li>Perempuan: <b>78% (39)</b></li>
                    <li>Laki-laki: <b>22% (11)</b></li>
                    <li>Usia dominan: <b>18-22 Tahun (72%)</b></li>
                </ul>
            </div>
            <div style="flex:1; min-width:200px;">
                <b style="color:var(--text-muted); font-size:12px; letter-spacing:1px;">HASIL KUESIONER</b><br>
                <div style="display:flex; gap:24px; margin-top:8px;">
                    <div><b style="font-size:32px; font-weight:800; color:var(--navy);">4.00</b><br><span style="font-size:12px; color:var(--text-muted); font-weight:600;">Skor Rata-rata</span></div>
                    <div><b style="font-size:32px; font-weight:800; color:var(--green);">4.26</b><br><span style="font-size:12px; color:var(--text-muted); font-weight:600;">Tertinggi (X2)</span></div>
                    <div><b style="font-size:32px; font-weight:800; color:var(--red);">3.82</b><br><span style="font-size:12px; color:var(--text-muted); font-weight:600;">Terendah (M)</span></div>
                </div>
            </div>
            <div style="flex:1; min-width:200px;">
                <b style="color:var(--text-muted); font-size:12px; letter-spacing:1px;">SENTIMEN & RATING</b><br>
                <div style="font-size:32px; font-weight:800; color:var(--green); margin:8px 0;">70.3% <span style="font-size:16px; font-weight:600;">Positif</span></div>
                <div style="font-size:24px; font-weight:800; color:var(--yellow); margin:8px 0;">3.89 <span style="font-size:16px; font-weight:600;">Rating Rata-rata</span></div>
                <p style="font-size:13px; color:var(--text-muted); margin-top:12px; line-height:1.5;">Mayoritas sentimen positif berasal dari kemudahan & kepraktisan aplikasi DANA.</p>
            </div>
        </div>
    </div>
    
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:20px;">
        <div class="dana-card" style="text-align:center; padding:24px; cursor:pointer;"><div style="font-size:40px; margin-bottom:12px;">📊</div><b style="color:var(--navy);">Dashboard Streamlit</b><br><span style="font-size:13px; color:var(--dana-blue); font-weight:600; margin-top:8px; display:inline-block;">Buka Tautan ↗</span></div>
        <div class="dana-card" style="text-align:center; padding:24px; cursor:pointer;"><div style="font-size:40px; margin-bottom:12px;">💻</div><b style="color:var(--navy);">Source Code</b><br><span style="font-size:13px; color:var(--dana-blue); font-weight:600; margin-top:8px; display:inline-block;">Buka Tautan ↗</span></div>
        <div class="dana-card" style="text-align:center; padding:24px; cursor:pointer;"><div style="font-size:40px; margin-bottom:12px;">📁</div><b style="color:var(--navy);">Repository GitHub</b><br><span style="font-size:13px; color:var(--dana-blue); font-weight:600; margin-top:8px; display:inline-block;">Buka Tautan ↗</span></div>
        <div class="dana-card" style="text-align:center; padding:24px; cursor:pointer;"><div style="font-size:40px; margin-bottom:12px;">☁️</div><b style="color:var(--navy);">Streamlit Cloud</b><br><span style="font-size:13px; color:var(--dana-blue); font-weight:600; margin-top:8px; display:inline-block;">Buka Tautan ↗</span></div>
    </div>
    
    <div style="background: white; border: 1px solid var(--border); border-radius: 16px; padding: 20px; margin-top: 24px; display: flex; align-items: center; justify-content:center; gap: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.02);">
        <span style="font-size:20px;">ℹ️</span>
        <span style="color: var(--text-muted); font-size: 14px; font-weight:500;">Semua tautan di atas bersifat publik dan dapat diakses untuk keperluan presentasi, demonstrasi, dan evaluasi.</span>
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# MAIN RUNNER
# =====================================================================
def main():
    st.set_page_config(page_title="DANA Insight Command Center", page_icon="💳", layout="wide", initial_sidebar_state="collapsed")
    init_session_state()
    inject_global_css()
    
    data = load_data()
    
    if st.session_state.app_view == "landing":
        render_landing_page()
    else:
        render_dashboard(data)

if __name__ == "__main__":
    main()
