"""
Patch script to add sidebar navigation, move filter panel to sidebar,
and replace st.tabs with sidebar-controlled content in app.py.
"""
import re

src = "app.py"
with open(src, "r", encoding="utf-8") as f:
    content = f.read()

# ─── PATCH 4: Define render_sidebar_nav() ────────────────────────────────────
# Insert before render_filter_panel
nav_func = '''def render_sidebar_nav() -> None:
    """Render the main navigation menu in the sidebar."""
    logo_html = render_image_asset(
        "dana_logo_wordmark_header_480x120.png",
        class_name="sidebar-logo",
        alt="DANA Insight",
        fallback=f'<div class="sidebar-logo-fallback">{icon_svg("users")} DANA Insight</div>'
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

    tabs = [
        ("Overview", "users"),
        ("Analisis Survei", "reviews"),
        ("Analisis Ulasan", "sentiment"),
        ("Data Explorer", "score"),
        ("Lampiran Presentasi", "menu")
    ]

    st.sidebar.html('<div class="sidebar-nav-section"><div class="sidebar-nav-label">Main Menu</div></div>')
    
    for tab_name, icon_name in tabs:
        active_class = " active" if st.session_state.active_tab == tab_name else ""
        icon_html = icon_svg(icon_name)
        
        # We use a button styled with CSS, but Streamlit buttons have their own wrapper.
        # Instead, we can use an unstyled radio button or just regular buttons.
        # Streamlit 1.35+ allows styling buttons via CSS or use radio.
        # The easiest way to have a stateful menu is st.sidebar.radio, but styling it is hard.
        # So we will use a radio button for functionality, and CSS to style it.
        pass

    # Actually, using a simple radio button is safest for Streamlit.
    st.sidebar.markdown(
        """
        <style>
        /* Hide radio button circles and style the labels as nav items */
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 0.5rem 0.75rem !important;
            margin-bottom: 0.2rem !important;
            border-radius: 10px !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background-color: #F1F5F9 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] div[data-testid="stMarkdownContainer"] p {
            font-size: 0.85rem !important;
            font-weight: 600 !important;
            color: #475569 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] [data-checked="true"] {
            background: linear-gradient(135deg, #EFF6FF, #DBEAFE) !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] [data-checked="true"] div[data-testid="stMarkdownContainer"] p {
            color: #004AAD !important;
            font-weight: 700 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] [role="radio"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_javascript=True
    )

    selected_tab = st.sidebar.radio(
        "Navigasi",
        options=[t[0] for t in tabs],
        index=[t[0] for t in tabs].index(st.session_state.active_tab),
        label_visibility="collapsed"
    )
    
    if selected_tab != st.session_state.active_tab:
        st.session_state.active_tab = selected_tab
        st.rerun()

    st.sidebar.html('<div class="sidebar-divider"></div><div class="sidebar-filter-header"><div class="sidebar-filter-title">Filter Panel</div></div>')


def render_filter_panel('''

content = content.replace("def render_filter_panel(", nav_func, 1)


# ─── PATCH 5: Modify render_filter_panel to remove the old header ────────────
# Remove the custom control panel header since it's now in the sidebar
old_panel_header = """
    with st.container(key="control_panel"):
        panel_logo = render_image_asset(
            "dana_logo_wordmark_header_480x120.png",
            class_name="control-panel-brand",
            alt="DANA inspired wordmark",
            fallback=DANA_LOGO_SVG,
        )
        st.html(
            f\"\"\"
            {panel_logo}
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
            \"\"\"
        )

        action_left, action_right = st.columns(2)"""

new_panel_header = """
    with st.container(key="control_panel"):
        action_left, action_right = st.columns(2)"""

content = content.replace(old_panel_header, new_panel_header, 1)

# ─── PATCH 6: Replace st.tabs with active_tab logic in render_dashboard_content ──
old_tabs_code = """
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
        render_output_and_presentation(audit_frame, invariant_errors)"""

new_tabs_code = """
    active_tab = st.session_state.get("active_tab", "Overview")
    
    if active_tab == "Overview":
        render_overview(
            survey_filtered,
            survey_columns,
            reviews_filtered,
            review_columns,
            survey_total,
            review_total,
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
    elif active_tab == "Lampiran Presentasi":
        render_output_and_presentation(audit_frame, invariant_errors)"""

content = content.replace(old_tabs_code, new_tabs_code, 1)

# ─── PATCH 7: Modify main() to use st.sidebar ────────────────────────────────
old_main_layout = """
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
        render_dashboard_content("""

new_main_layout = """
    render_sidebar_nav()
    
    with st.sidebar:
        if st.session_state.get("show_filter_panel", True):
            filters = render_filter_panel(options, defaults, data["errors"])
        else:
            filters = st.session_state.active_filters.copy()

    with st.container():
        render_dashboard_content("""

content = content.replace(old_main_layout, new_main_layout, 1)

# Also fix the top header to include the "Filter" toggle button if we want to toggle it,
# but for now we just put the filters in the sidebar.

with open(src, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Patched sidebar navigation and removed old tabs layout.")
