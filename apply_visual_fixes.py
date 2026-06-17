"""
apply_visual_fixes.py
Applies all visual fixes to app.py safely using exact string replacement.
Run: python apply_visual_fixes.py
"""
import sys
from pathlib import Path

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")
original_len = len(text)
fixes_applied = []

def replace_once(content: str, old: str, new: str, label: str) -> str:
    if old not in content:
        print(f"  [SKIP] {label} — target not found")
        return content
    count = content.count(old)
    if count > 1:
        print(f"  [WARN] {label} — found {count} occurrences, replacing first")
    result = content.replace(old, new, 1)
    fixes_applied.append(label)
    print(f"  [OK]   {label}")
    return result

# ===========================================================================
# FIX 1: PLOTLY_CONFIG — hide modebar by default
# ===========================================================================
text = replace_once(text,
    '''PLOTLY_CONFIG = {
    "displayModeBar": "hover",
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
    "modeBarButtonsToRemove": [
        "select2d",
        "lasso2d",
        "autoScale2d",
        "toggleSpikelines",
    ],
}''',
    '''PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}''',
    "PLOTLY_CONFIG - hide modebar"
)

# ===========================================================================
# FIX 2: Sidebar width 240 → 220px
# ===========================================================================
text = replace_once(text,
    '            --sidebar-width: 240px;',
    '            --sidebar-width: 220px;',
    "Sidebar width 240→220px"
)

# ===========================================================================
# FIX 3: Lobby visual — remove ::before pseudo-element, use simpler img approach
# ===========================================================================
OLD_LOBBY_VISUAL = '''        .lobby-visual {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .lobby-visual::before {{
            content: "";
            position: absolute;
            width: 110%;
            height: 110%;
            border-radius: 50%;
            background: radial-gradient(circle at 50% 50%,
                rgba(16,142,233,.14) 0%,
                rgba(56,189,248,.08) 40%,
                transparent 70%);
            pointer-events: none;
        }}

        .lobby-visual img {{
            position: relative;
            z-index: 1;
            width: min(420px, 92%);
            max-height: clamp(300px, 38vw, 460px);
            object-fit: contain;
            filter:
                drop-shadow(0 28px 48px rgba(11,94,215,.22))
                drop-shadow(0 8px 16px rgba(16,142,233,.12));
            animation: lobby-float 5.5s ease-in-out infinite;
        }}'''

NEW_LOBBY_VISUAL = '''        .lobby-visual {{
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 280px;
        }}

        /* Radial glow effect behind wallet image */
        .lobby-visual::after {{
            content: "";
            position: absolute;
            inset: -12%;
            border-radius: 50%;
            background: radial-gradient(circle at 50% 48%,
                rgba(16,142,233,.18) 0%,
                rgba(56,189,248,.10) 38%,
                transparent 65%);
            pointer-events: none;
            z-index: 0;
        }}

        .lobby-visual img {{
            position: relative;
            z-index: 1;
            width: min(400px, 90%);
            max-height: clamp(280px, 36vw, 420px);
            object-fit: contain;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            filter:
                drop-shadow(0 32px 56px rgba(11,94,215,.26))
                drop-shadow(0 8px 20px rgba(16,142,233,.16));
            animation: lobby-float 5.5s ease-in-out infinite;
        }}'''

text = replace_once(text, OLD_LOBBY_VISUAL, NEW_LOBBY_VISUAL, "Lobby visual CSS - remove grey box")

# ===========================================================================
# FIX 4: Chart containers — reduce padding and add chart header tightening
# ===========================================================================
OLD_CHART_CONTAINERS = '''        /* ── CHART CONTAINERS ── */
        [class*="st-key-chart_"], [class*="st-key-panel_"] {{
            width: 100%;
            max-width: 100%;
            overflow: visible !important;
            padding: .78rem .88rem .65rem;
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

        [data-testid="stPlotlyChart"] .modebar {{
            top: 4px !important;
            right: 4px !important;
            opacity: 0 !important;
            transform: scale(.78);
            transform-origin: top right;
            transition: opacity .18s ease !important;
        }}

        [data-testid="stPlotlyChart"]:hover .modebar {{
            opacity: .5 !important;
        }}

        [data-testid="stPlotlyChart"] .modebar-btn {{
            border-radius: 7px !important;
            background: rgba(255,255,255,.92) !important;
        }}

        .chart-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: .65rem;
            padding: .7rem .15rem .1rem;
        }}'''

NEW_CHART_CONTAINERS = '''        /* ── CHART CONTAINERS ── */
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
        }}'''

text = replace_once(text, OLD_CHART_CONTAINERS, NEW_CHART_CONTAINERS, "Chart container CSS compact + hide modebar")

# ===========================================================================
# FIX 5: Fullscreen button — make it small inline button (not giant circle)
# ===========================================================================
OLD_EXPAND_BTN = '''        [class*="st-key-chart_expand_"] button {{
            width: 42px !important;
            min-width: 42px !important;
            height: 40px !important;
            min-height: 40px !important;
            padding: 0 !important;
            border-radius: 14px !important;
            color: {C_DEEP} !important;
            border-color: #BFDBFE !important;
            background: #EFF6FF !important;
            box-shadow: none !important;
        }}

        [class*="st-key-chart_expand_"] button:hover {{
            color: white !important;
            border-color: var(--dana-blue) !important;
            background: linear-gradient(135deg, var(--dana-blue), var(--dana-blue-dark)) !important;
            box-shadow: 0 8px 18px rgba(16,142,233,.2) !important;
        }}'''

NEW_EXPAND_BTN = '''        /* Fullscreen button — small, inline, not a giant circle */
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
        }}'''

text = replace_once(text, OLD_EXPAND_BTN, NEW_EXPAND_BTN, "Fullscreen button - small inline style")

# ===========================================================================
# FIX 6: base_layout margins — reduce t=55 to t=25 to cut chart whitespace
# ===========================================================================
OLD_BASE_LAYOUT_MARGIN = '        "margin": {"t": 55, "b": 60, "l": 40, "r": 30},'
NEW_BASE_LAYOUT_MARGIN = '        "margin": {"t": 28, "b": 46, "l": 38, "r": 20},'
text = replace_once(text, OLD_BASE_LAYOUT_MARGIN, NEW_BASE_LAYOUT_MARGIN, "base_layout margins - reduce top whitespace")

# ===========================================================================
# FIX 7: render_chart_card — use use_container_width=True, compact header columns
# ===========================================================================
OLD_RENDER_CHART_CARD = '''def render_chart_card(
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
    header, action = st.columns([12, 1], vertical_alignment="center")
    with header:
        st.html(f\'<div class="chart-card-title">{escape(clean_title)}</div>\')
    with action:
        if st.button(
            "⛶",
            key=f"chart_expand_{chart_id}",
            help=f"Buka detail grafik {clean_title}",
        ):
            _open_fullscreen_chart(chart_id)
            st.rerun()

    inline = go.Figure(figure)
    inline.update_layout(title=None)
    st.plotly_chart(
        inline,
        width="stretch",
        theme=None,
        config=PLOTLY_CONFIG,
        key=chart_id,
    )
    if caption:
        st.caption(caption)'''

NEW_RENDER_CHART_CARD = '''def render_chart_card(
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
            f\'<div style="font-size:.83rem;font-weight:800;color:#07132F;\
padding:.1rem 0;line-height:1.3;">\' + escape(clean_title) + \'</div>\'
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
    )
    st.plotly_chart(
        inline,
        use_container_width=True,
        theme=None,
        config=PLOTLY_CONFIG,
        key=chart_id,
    )
    if caption:
        st.caption(caption)'''

text = replace_once(text, OLD_RENDER_CHART_CARD, NEW_RENDER_CHART_CARD, "render_chart_card - compact header + use_container_width")

# ===========================================================================
# FIX 8: Landing lobby — merge two st.html calls and use CSS background for visual
# ===========================================================================
OLD_LANDING_HTML = """    st.html(
        f\\\"\\\"\\\"
        <div class=\\\"lobby-topbar\\\">
            {_logo_img_tag()}
            <div class=\\\"lobby-help\\\">Butuh bantuan? Gunakan <strong>Lampiran Presentasi</strong>.</div>
        </div>
        \\\"\\\"\\\"
    )
    st.html(
        f\\\"\\\"\\\"
        <section class=\\\"lobby-shell fade-in\\\">
            <div class=\\\"lobby-hero\\\">
                <div>
                    <div class=\\\"lobby-mark\\\">{logo}</div>
                    <h1 class=\\\"lobby-title\\\">DANA Insight<br><span>Command Center</span></h1>
                    <p class=\\\"lobby-subtitle\\\">
                        Dashboard interaktif untuk memahami pengalaman pengguna
                        DANA berdasarkan data survei dan ulasan pengguna.
                    </p>
                    <div class=\\\"badge-row\\\">
                        <span class=\\\"hero-badge\\\">&#128101; Profil Responden</span>
                        <span class=\\\"hero-badge\\\">&#128203; 20 Indikator</span>
                        <span class=\\\"hero-badge\\\">&#129302; Review Intelligence</span>
                        <span class=\\\"hero-badge\\\">&#128274; Data Explorer Aman</span>
                    </div>
                </div>
                <div class=\\\"lobby-visual\\\" aria-hidden=\\\"true\\\">
                    {asset_img_tag(\\\"dana_wallet_cluster_720x720.png\\\", alt=\\\"DANA Wallet\\\")}
                </div>
            </div>
            <div class=\\\"lobby-metrics\\\">{metric_html}</div>
            <div class=\\\"lobby-privacy\\\">
                {shield}
                <span><strong>Privasi pengguna terlindungi.</strong><br>
                Identitas pribadi tidak ditampilkan dan tidak masuk download publik.</span>
            </div>
        </section>
        \\\"\\\"\\\"
    )"""

# We actually use the raw strings from the file — let's do regex-safe approach
# Instead of matching the whole block, let's do targeted smaller replacements

# FIX 8a: Remove the double st.html call and use bg-image approach for wallet
# We just need to add background: transparent to the img element in CSS (already done in FIX 3)
# And also ensure the st.html call for lobby-topbar and lobby-shell are merged to prevent separator

# FIX 9: Lobby hero grid — ensure lobby-hero has proper grid layout with sufficient width
OLD_LOBBY_HERO_CSS = '''        .lobby-hero {
            display: grid;
            grid-template-columns: minmax(0,1.15fr) minmax(260px,.85fr);
            align-items: center;
            gap: clamp(1.5rem, 5vw, 4rem);
        }'''

NEW_LOBBY_HERO_CSS = '''        .lobby-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.1fr) minmax(240px, .9fr);
            align-items: center;
            gap: clamp(1.5rem, 4vw, 3.5rem);
        }'''

text = replace_once(text, OLD_LOBBY_HERO_CSS, NEW_LOBBY_HERO_CSS, "lobby-hero grid layout")

# ===========================================================================
# FIX 9: KPI grid - ensure 5 columns at laptop width
# ===========================================================================
OLD_KPI_GRID_CSS = """        .kpi-card {{
            position: relative;
            overflow: hidden;
            padding: 1rem;"""

NEW_KPI_GRID_CSS = """        /* 5-column KPI grid */
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
            padding: 1rem;"""

text = replace_once(text, OLD_KPI_GRID_CSS, NEW_KPI_GRID_CSS, "KPI grid 5-column layout with responsive breakpoints")

# ===========================================================================
# FIX 10: Hero dashboard - ensure background-size correct, limit height
# ===========================================================================
OLD_HERO_SECTION = '''        .hero-section {{
            position: relative;
            overflow: hidden;
            min-height: 225px;
            margin-bottom: .8rem;
            padding: clamp(1.25rem, 3.5vw, 2.1rem);
            border-radius: 20px;
            color: {C_TEXT};
            background-image:
                linear-gradient(94deg, rgba(255,255,255,1) 0%, rgba(255,255,255,.97) 38%, rgba(255,255,255,.72) 58%, rgba(255,255,255,.18) 78%, rgba(255,255,255,0) 92%),
                {hero_background},
                linear-gradient(135deg, #FAFCFF 0%, #EBF5FF 100%);
            background-position: center, center right, center;
            background-repeat: no-repeat;
            background-size: cover, cover, cover;
            border: 1px solid #CDDEFA;
            box-shadow: 0 6px 24px rgba(16,142,233,.09);
        }}'''

NEW_HERO_SECTION = '''        .hero-section {{
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
        }}'''

text = replace_once(text, OLD_HERO_SECTION, NEW_HERO_SECTION, "Hero section - fix background sizing and max-height")

# ===========================================================================
# FIX 11: PLOTLY_CONFIG test update
# ===========================================================================
print("\nApplying fixes to test_dashboard.py...")
TEST_FILE = Path("test_dashboard.py")
test_text = TEST_FILE.read_text(encoding="utf-8")

OLD_TEST_CONFIG = '''        self.assertEqual(
            app.PLOTLY_CONFIG,
            {
                "displayModeBar": "hover",
                "displaylogo": False,
                "responsive": True,
                "scrollZoom": False,
                "modeBarButtonsToRemove": [
                    "select2d",
                    "lasso2d",
                    "autoScale2d",
                    "toggleSpikelines",
                ],
            },
        )'''

NEW_TEST_CONFIG = '''        self.assertEqual(
            app.PLOTLY_CONFIG,
            {
                "displayModeBar": False,
                "displaylogo": False,
                "responsive": True,
                "scrollZoom": False,
            },
        )'''

if OLD_TEST_CONFIG in test_text:
    test_text = test_text.replace(OLD_TEST_CONFIG, NEW_TEST_CONFIG, 1)
    TEST_FILE.write_text(test_text, encoding="utf-8")
    print("  [OK]   PLOTLY_CONFIG test assertion updated")
else:
    print("  [SKIP] PLOTLY_CONFIG test assertion — already updated or not found")

# ===========================================================================
# WRITE OUTPUT
# ===========================================================================
print(f"\nWriting fixed app.py ({len(text):,} bytes, was {original_len:,})...")
APP.write_text(text, encoding="utf-8")
print(f"\nFixes applied ({len(fixes_applied)}):")
for fix in fixes_applied:
    print(f"  ✓ {fix}")
print("\nDone. Run: python -m py_compile app.py")
