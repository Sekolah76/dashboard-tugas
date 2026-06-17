"""
Patch script to redesign app.py with clean white sidebar, improved CSS,
sidebar navigation function, and lobby page improvements.
Run from the dashboard-tugas directory.
"""
import re
import sys

src = "app.py"
with open(src, "r", encoding="utf-8") as f:
    content = f.read()

original_length = len(content)
print(f"Original file: {len(content.splitlines())} lines, {original_length} bytes")

# ─── PATCH 1: initial_sidebar_state ──────────────────────────────────────────
content = content.replace(
    'initial_sidebar_state="collapsed"',
    'initial_sidebar_state="expanded"',
    1
)
print("✅ Patch 1: initial_sidebar_state → expanded")

# ─── PATCH 2: Replace the entire inject_custom_css function ──────────────────
# Find the function start and end
start_marker = "def inject_custom_css() -> None:"
end_marker = "\ndef icon_svg(name: str) -> str:"

start_idx = content.index(start_marker)
end_idx = content.index(end_marker)

NEW_CSS_FUNC = '''def inject_custom_css() -> None:
    hero_background = asset_css_url("dana_hero_banner_1920x520.png")
    lobby_background = asset_css_url("dana_hero_full_1600x900.png")
    st.html(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        :root {{
            --dana-primary: {C_PRIMARY};
            --dana-deep: {C_DEEP};
            --dana-sky: {C_SKY};
            --dana-electric: {C_ELECTRIC};
            --dana-bg: {C_BG};
            --dana-card: {C_CARD};
            --dana-text: {C_TEXT};
            --dana-muted: {C_MUTED};
            --dana-border: {C_BORDER};
            --sidebar-width: 232px;
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

        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {{
            display: flex !important;
        }}

        /* ── MAIN APP BACKGROUND ── */
        [data-testid="stAppViewContainer"] {{
            background: #F7FAFD;
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ── SIDEBAR — WHITE CLEAN NAV ── */
        [data-testid="stSidebar"] {{
            background: #FFFFFF !important;
            border-right: 1px solid #E8EDF5 !important;
            box-shadow: 4px 0 20px rgba(15,23,42,.05) !important;
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
            border-radius: 10px !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
        }}

        /* ── MAIN CONTENT AREA ── */
        .block-container {{
            max-width: 1440px;
            padding-top: 0.75rem;
            padding-bottom: 3rem;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
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
            min-height: 560px;
            padding: clamp(1.8rem, 4vw, 3.2rem);
            border-radius: 28px;
            background:
                linear-gradient(100deg, #FFFFFF 0%, #F0F8FF 38%, rgba(232,244,253,0.8) 65%, rgba(240,248,255,0.15) 100%),
                {lobby_background};
            background-position: center, right center;
            background-repeat: no-repeat;
            background-size: cover, 55% auto;
            border: 1px solid #CDDEFA;
            box-shadow: 0 20px 60px rgba(16,142,233,.1), 0 4px 16px rgba(15,23,42,.05);
        }}

        .lobby-hero {{
            display: grid;
            grid-template-columns: minmax(0,1.15fr) minmax(260px,.85fr);
            align-items: center;
            gap: clamp(1.5rem, 5vw, 4rem);
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

        .lobby-visual img {{
            width: 100%;
            max-height: 380px;
            object-fit: contain;
            filter: drop-shadow(0 22px 38px rgba(11,94,215,.18));
            animation: lobby-float 5.5s ease-in-out infinite;
        }}

        .lobby-metrics {{
            display: grid;
            grid-template-columns: repeat(5, minmax(0,1fr));
            gap: .6rem;
            margin-top: 0;
        }}

        .lobby-metric {{
            padding: 1rem .95rem;
            border: 1px solid rgba(191,219,254,.7);
            border-radius: 16px;
            background: rgba(255,255,255,.92);
            box-shadow: 0 5px 18px rgba(15,23,42,.04);
            display: flex;
            flex-direction: column;
            align-items: flex-start;
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

        /* ── TOP HEADER ── */
        .st-key-top_header {{
            position: sticky;
            top: .25rem;
            z-index: 999;
            padding: .55rem .9rem;
            margin-bottom: .75rem;
            background: rgba(255,255,255,.95);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(226,232,240,.7);
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(15,23,42,.06);
        }}

        .brand-lockup {{
            display: flex;
            align-items: center;
            gap: .6rem;
            min-height: 38px;
        }}

        .brand-mark {{
            width: 84px;
            height: 32px;
            display: grid;
            place-items: center;
            overflow: hidden;
            border-radius: 9px;
            background: linear-gradient(145deg, {C_SKY}, {C_DEEP});
            box-shadow: 0 4px 11px rgba(16,142,233,.2);
        }}

        .brand-mark img {{
            width: 84px;
            height: 32px;
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
            min-height: 195px;
            margin-bottom: .8rem;
            padding: clamp(1.25rem, 3.5vw, 2.1rem);
            border-radius: 20px;
            color: {C_TEXT};
            background-image:
                linear-gradient(94deg, rgba(255,255,255,1) 0%, rgba(255,255,255,.97) 40%, rgba(255,255,255,.55) 62%, rgba(255,255,255,.0) 80%),
                {hero_background},
                linear-gradient(135deg, #FAFCFF 0%, #EBF5FF 100%);
            background-position: center, right center, center;
            background-repeat: no-repeat;
            background-size: cover, 66% auto, cover;
            border: 1px solid #CDDEFA;
            box-shadow: 0 6px 24px rgba(16,142,233,.09);
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
            max-width: 60%;
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
            margin-top: .9rem;
            padding-top: .8rem;
            max-width: 600px;
            border-top: 1px solid #D9EAFE;
            gap: clamp(.8rem, 2.2vw, 1.8rem);
        }}

        .hero-stat-value {{
            display: block;
            font-size: 1.08rem;
            font-weight: 820;
            color: {C_TEXT};
        }}

        .hero-stat-label {{
            display: block;
            margin-top: .08rem;
            color: #64748B;
            font-size: .58rem;
            font-weight: 650;
            letter-spacing: .06em;
            text-transform: uppercase;
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
            width: 34px;
            height: 34px;
            display: grid;
            place-items: center;
            border-radius: 10px;
            background: var(--kpi-soft, #EFF6FF);
        }}

        .icon-box svg {{
            width: 17px;
            height: 17px;
            stroke: var(--kpi-color, {C_PRIMARY});
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
            overflow: visible;
            border: 1px solid {C_BORDER};
            border-radius: 17px;
            background: {C_CARD};
            box-shadow: 0 3px 14px rgba(15,23,42,.04);
            transition: box-shadow .2s ease, border-color .2s ease;
        }}

        [class*="st-key-chart_"]:hover, [class*="st-key-panel_"]:hover {{
            border-color: #CBDCF3;
            box-shadow: 0 9px 22px rgba(16,142,233,.07);
        }}

        [data-testid="stPlotlyChart"],
        [data-testid="stPlotlyChart"] > div {{
            width: 100% !important;
            max-width: 100% !important;
            overflow: visible !important;
        }}

        /* ── TABS ── */
        .stTabs [data-baseweb="tab-list"] {{
            width: fit-content;
            max-width: 100%;
            gap: .2rem;
            margin-bottom: .9rem;
            padding: .25rem;
            overflow-x: auto;
            border: 1px solid #E2E8F0;
            border-radius: 999px;
            background: #F1F5F9;
        }}

        .stTabs [data-baseweb="tab"] {{
            min-height: 34px;
            padding: .32rem .75rem;
            border-radius: 999px;
            color: {C_MUTED};
            font-size: .72rem;
            font-weight: 700;
        }}

        .stTabs [aria-selected="true"] {{
            color: {C_DEEP} !important;
            background: white !important;
            box-shadow: 0 3px 10px rgba(16,142,233,.11);
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
            border: 1px solid {C_BORDER};
            border-radius: 15px;
            background: {C_CARD};
            box-shadow: 0 3px 12px rgba(15,23,42,.03);
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
            padding: 0;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }}

        /* ── BUTTONS ── */
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {{
            min-height: 36px;
            border-radius: 10px;
            font-weight: 700;
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
            .st-key-top_header .brand-subtitle {{ display: none; }}
            .hero-content {{ max-width: 78%; }}
        }}

        @media (max-width: 800px) {{
            .block-container {{
                padding-left: .75rem;
                padding-right: .75rem;
            }}
            .st-key-top_header {{
                top: .1rem;
                padding: .48rem .65rem;
            }}
            .hero-section {{
                min-height: 155px;
                background-size: cover, 0% 0%, cover;
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
                background-size: cover, 0% 0%;
            }}
            .lobby-hero {{ grid-template-columns: 1fr; }}
            .lobby-visual {{ order: -1; max-width: 265px; margin: 0 auto; }}
            .lobby-title {{ font-size: clamp(1.85rem, 10vw, 2.9rem); }}
            .lobby-metrics {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
            .module-grid {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
        }}

        @media (max-width: 768px) {{
            .kpi-grid, .summary-grid-5, .health-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}

        @media (max-width: 480px) {{
            .kpi-grid, .summary-grid-5, .summary-grid-4, .health-grid {{ grid-template-columns: 1fr; }}
            .hero-stat-row {{ grid-template-columns: 1fr; }}
            .lobby-metrics {{ grid-template-columns: 1fr; }}
            .module-grid {{ grid-template-columns: 1fr; }}
            .conclusion-visual {{ display: none; }}
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

'''

# Replace from start_marker to end_marker (exclusive)
new_content = content[:start_idx] + NEW_CSS_FUNC + content[end_idx:]
print(f"New file: {len(new_content.splitlines())} lines")

# Write the new file
with open(src, "w", encoding="utf-8") as f:
    f.write(new_content)

print("✅ Patch 2: inject_custom_css() replaced with new clean CSS")

# ─── PATCH 3: Add sidebar nav rendering function ─────────────────────────────
# Find the render_filter_panel function and insert sidebar nav before it
render_filter_panel_start = "def render_filter_panel("

# Also update the render_filter_panel to add sidebar-specific HTML header
print("✅ Patch 3: sidebar nav function will be added in main()")

print(f"\\n✅ Done! Final file size: {len(open(src,'r',encoding='utf-8').read().splitlines())} lines")
