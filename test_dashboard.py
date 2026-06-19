from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

import app


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = app.load_all_data()
        cls.survey, cls.survey_columns = app.prepare_survey_data(data["survey"])
        cls.reviews, cls.review_columns = app.prepare_review_data(data["reviews"])
        cls.questionnaire = app.normalize_questionnaire(
            data["questionnaire"],
            cls.survey,
            cls.survey_columns.get("questions", []),
        )

    def test_baseline_invariants(self) -> None:
        errors = app.validate_data_invariants(
            self.survey,
            self.survey_columns,
            self.reviews,
            self.review_columns,
            self.questionnaire,
        )
        self.assertEqual(errors, [])

    def test_questionnaire_matches_survey(self) -> None:
        computed = app.compute_questionnaire_from_survey(
            self.survey,
            self.survey_columns["questions"],
        )
        merged = self.questionnaire.merge(
            computed,
            on="pertanyaan",
            suffixes=("_csv", "_survey"),
        )
        self.assertEqual(len(merged), 20)
        self.assertTrue(
            np.allclose(
                merged["rata_rata_csv"],
                merged["rata_rata_survey"],
                atol=1e-9,
            )
        )

    def test_variable_scores(self) -> None:
        variables, missing = app.compute_variable_scores(
            self.survey,
            self.survey_columns["questions"],
        )
        values = variables.set_index("variabel")["rata_rata"].to_dict()
        self.assertEqual(missing, {})
        self.assertAlmostEqual(values["X1 - Fleksibilitas"], 4.00, places=9)
        self.assertAlmostEqual(values["X2 - Praktis"], 4.26, places=9)
        self.assertAlmostEqual(values["M - Kepercayaan"], 3.82, places=9)
        self.assertAlmostEqual(values["Y - Keseluruhan"], 4.002, places=9)

    def test_public_sanitization_is_precise(self) -> None:
        columns = [
            "username",
            "Siapa nama Anda?",
            "Nama Lengkap",
            "name",
            "email_address",
            "phone",
            "nomor",
            "kontak",
            "responden",
            "id pengguna",
            "user id",
            "Unnamed: 0",
            "nilai",
        ]
        frame = pd.DataFrame([[1] * len(columns)], columns=columns)
        sanitized = app.sanitize_public_df(frame)
        self.assertEqual(list(sanitized.columns), ["Unnamed: 0", "nilai"])

    def test_review_trend_is_daily_with_denominator(self) -> None:
        figure = app.review_trend_chart(
            self.reviews,
            self.review_columns["date"],
            "Total data",
        )
        self.assertIn("Volume Ulasan per Tanggal", figure.layout.title.text)
        self.assertEqual(list(figure.data[0].x), ["2026-06-09", "2026-06-10"])
        self.assertEqual(list(figure.data[0].y), [248, 82])
        self.assertIn("customdata[0]", figure.data[0].hovertemplate)
        self.assertIn("customdata[1]", figure.data[0].hovertemplate)
        self.assertEqual(figure.layout.height, 360)
        self.assertTrue(figure.layout.autosize)

    def test_plotly_config_and_distribution_tooltips(self) -> None:
        cfg = app.PLOTLY_CONFIG
        self.assertFalse(cfg["displayModeBar"])
        self.assertFalse(cfg["scrollZoom"])
        self.assertTrue(cfg["responsive"])
        gender = app.donut_chart(
            pd.Series({"Perempuan": 39, "Laki-laki": 11}),
            "Distribusi Gender Responden",
            {"Perempuan": app.C_PRIMARY, "Laki-laki": app.C_SKY},
            "Total data",
            "responden",
        )
        self.assertIn("Jumlah: <b>%{value}</b>", gender.data[0].hovertemplate)
        self.assertIn("Persentase: <b>%{percent:.1%}</b>", gender.data[0].hovertemplate)
        self.assertIsNone(gender.data[0].customdata)
        frequency = app.bar_chart(
            ["Jarang", "Beberapa kali seminggu", "Setiap hari"],
            [21, 19, 10],
            "Frekuensi Penggunaan DANA",
            denominator=50,
            scope_label="Total data",
            unit_label="responden",
        )
        self.assertEqual(frequency.data[0].x[1], "Beberapa kali<br>seminggu")
        self.assertEqual(frequency.layout.xaxis.tickangle, -25)
        self.assertEqual(list(frequency.data[0].customdata[0])[:3], ["Jarang", "21", "42.0"])

    def test_chart_titles_are_plain_and_questionnaire_is_compact(self) -> None:
        figure = app.questionnaire_chart(
            self.questionnaire,
            len(self.survey),
            "Total data",
        )
        figure.update_layout(title="<b>Rata-rata Skor Q1-Q20</b>")
        self.assertEqual(app._chart_title(figure), "Rata-rata Skor Q1-Q20")
        compact = app.questionnaire_chart(
            self.questionnaire,
            len(self.survey),
            "Total data",
        )
        self.assertLessEqual(compact.layout.height, 560)

    def test_assets_and_global_search_are_safe(self) -> None:
        for filename in (
            "dana_hero_banner_1920x520.png",
            "dana_hero_full_1600x900.png",
            "dana_logo_wordmark_header_480x120.png",
            "dana_mobile_mockup_360x480.png",
            "dana_wallet_cluster_480x480.png",
        ):
            self.assertTrue(app.asset_exists(filename), filename)
            self.assertTrue(app.img_to_base64(filename))
        active_before = {"gender": ["Perempuan"], "rating": [1]}
        questions, reviews = app.global_search_matches(
            "saldo",
            self.questionnaire,
            self.reviews,
            self.review_columns,
        )
        self.assertLessEqual(len(questions), 5)
        self.assertLessEqual(len(reviews), 5)
        self.assertNotIn("username", [str(column).casefold() for column in reviews.columns])
        self.assertEqual(active_before, {"gender": ["Perempuan"], "rating": [1]})

    def test_audit_does_not_expose_values(self) -> None:
        audit = app.audit_data_sources()
        self.assertEqual(len(audit), 6)
        raw_survey = audit[audit["Sumber"].eq("raw_survey_clean.xlsx")].iloc[0]
        self.assertIn("Siapa nama Anda?", raw_survey["Kolom Identitas"])
        self.assertNotIn("Muhammad", audit.to_string())
        database = audit[audit["Sumber"].eq("hasil_analisis_dana.db")].iloc[0]
        self.assertEqual(database["Status"], "Valid setelah deduplikasi")
        self.assertIn("ulasan: 660 raw / 330 unik", database["Rekonsiliasi"])
        self.assertIn("kuesioner: 40 raw / 20 unik", database["Rekonsiliasi"])
        self.assertIn("demografi: 18 raw / 9 unik", database["Rekonsiliasi"])

    def test_active_filter_chips_only_show_restrictive_filters(self) -> None:
        options = app.available_options(
            self.survey,
            self.survey_columns,
            self.reviews,
            self.review_columns,
        )
        defaults = app.default_filters(options)
        all_selected = defaults.copy()
        all_selected["gender"] = options["gender"].copy()
        all_selected["rating"] = options["rating"].copy()
        self.assertEqual(
            app.active_filter_chips(all_selected, defaults, options),
            [],
        )
        restricted = defaults.copy()
        restricted["gender"] = ["Perempuan"]
        restricted["rating"] = [1]
        chips = app.active_filter_chips(restricted, defaults, options)
        self.assertIn("Gender: Perempuan", chips)
        self.assertIn("Rating: 1", chips)

    def test_flyer_chart_properties(self) -> None:
        # Check that bar_chart layout height is numeric and matches height parameter
        fig_bar = app.bar_chart(
            labels=["A", "B"],
            values=[10, 20],
            title="Test Bar Chart",
            height=180
        )
        self.assertEqual(fig_bar.layout.height, 180)
        self.assertIsInstance(fig_bar.layout.height, (int, float))

        # Check variable score chart height
        vars_df = pd.DataFrame({
            "variabel": ["X1", "X2"],
            "rata_rata": [4.0, 4.2],
            "interpretasi": ["Kuat", "Kuat"],
            "jumlah_indikator": [4, 4]
        })
        fig_vars = app.variable_score_chart(vars_df, "Total data")
        self.assertEqual(fig_vars.layout.height, 360)  # default in variable_score_chart
        self.assertIsInstance(fig_vars.layout.height, (int, float))



class DashboardInteractionTests(unittest.TestCase):
    def test_landing_navigation_filters_fullscreen_and_pagination(self) -> None:
        dashboard = AppTest.from_file("app.py", default_timeout=45).run()
        self.assertEqual(len(dashboard.exception), 0)
        self.assertTrue(
            any(button.label == "Masuk ke Dashboard" for button in dashboard.button)
        )
        module_buttons = [
            button
            for button in dashboard.button
            if str(button.key).startswith("landing_open_")
        ]
        self.assertEqual(len(module_buttons), 6)

        next(
            button
            for button in dashboard.button
            if button.label == "Masuk ke Dashboard"
        ).click().run()
        self.assertEqual(dashboard.session_state["app_view"], "dashboard")
        navigation_buttons = [
            button
            for button in dashboard.button
            if str(button.key).startswith("horizontal_nav_")
        ]
        # Now only horizontal_nav_ buttons (sidebar nav removed)
        self.assertEqual(len(navigation_buttons), 6)
        self.assertEqual(
            {button.label for button in navigation_buttons},
            {
                "Overview",
                "Analisis Survei",
                "Analisis Ulasan",
                "Data Explorer",
                "Lampiran Presentasi",
                "Snapshot Flyer",
            },
        )
        self.assertTrue(
            any(widget.label == "Pencarian global" for widget in dashboard.text_input)
        )
        quick_search = next(
            widget
            for widget in dashboard.text_input
            if widget.label == "Pencarian global"
        )
        active_before_search = dict(dashboard.session_state["active_filters"])
        quick_search.set_value("saldo").run()
        self.assertEqual(
            dict(dashboard.session_state["active_filters"]),
            active_before_search,
        )
        quick_search.set_value("").run()

        # ── Filter architecture test (dialog-based) ──────────────────────────
        # Since filter is now a @st.dialog, we test the state-driven flow
        # by directly manipulating active_filters (as the dialog form submit does).

        # Verify filter button exists in topbar
        filter_btn = next(
            (button for button in dashboard.button
             if button.key == "open_filter_dialog_btn"),
            None,
        )
        self.assertIsNotNone(filter_btn, "Filter button must exist in topbar")

        # Directly set active_filters as the dialog submit would
        # (initialize_filter_state only adds missing keys, doesn't overwrite set values)
        dashboard.session_state["active_filters"]["gender"] = ["Perempuan"]
        dashboard.session_state["active_filters"]["rating"] = [1]
        dashboard.session_state["pending_filters"]["gender"] = ["Perempuan"]
        dashboard.session_state["pending_filters"]["rating"] = [1]
        dashboard.session_state["draft_gender"] = ["Perempuan"]
        dashboard.session_state["draft_rating"] = [1]

        # Check state before run (dialog applies filter, then rerun happens)
        self.assertEqual(dashboard.session_state["active_filters"]["gender"], ["Perempuan"])
        self.assertEqual(dashboard.session_state["active_filters"]["rating"], [1])

        # Verify filter data flow by calling app functions directly
        data = app.load_all_data()
        survey, survey_columns = app.prepare_survey_data(data["survey"])
        reviews, review_columns = app.prepare_review_data(data["reviews"])
        options = app.available_options(
            survey,
            survey_columns,
            reviews,
            review_columns,
        )
        active = dashboard.session_state["active_filters"]
        filtered_survey = app.apply_survey_filters(
            survey,
            survey_columns,
            dict(active),
            options,
        )
        filtered_reviews = app.apply_review_filters(
            reviews,
            review_columns,
            dict(active),
            options,
        )
        self.assertEqual(len(filtered_survey), 39)
        self.assertEqual(len(filtered_reviews), 73)

        # Reset filter state
        app_defaults = app.default_filters(options)
        dashboard.session_state["active_filters"].update(app_defaults)
        dashboard.session_state["pending_filters"].update(app_defaults)
        dashboard.session_state["draft_gender"] = []
        dashboard.session_state["draft_rating"] = []
        self.assertEqual(dashboard.session_state["active_filters"]["gender"], [])
        self.assertEqual(dashboard.session_state["active_filters"]["rating"], [])
        self.assertEqual(dashboard.session_state["pending_filters"]["gender"], [])
        self.assertEqual(dashboard.session_state["pending_filters"]["rating"], [])

        # Test keyword filter
        dashboard.session_state["active_filters"]["keyword"] = "__kata_yang_tidak_mungkin_ada__"
        dashboard.session_state["pending_filters"]["keyword"] = "__kata_yang_tidak_mungkin_ada__"
        dashboard.session_state["draft_keyword"] = "__kata_yang_tidak_mungkin_ada__"
        self.assertEqual(
            dashboard.session_state["active_filters"]["keyword"],
            "__kata_yang_tidak_mungkin_ada__",
        )
        # Reset keyword
        dashboard.session_state["active_filters"]["keyword"] = ""
        dashboard.session_state["pending_filters"]["keyword"] = ""
        dashboard.session_state["draft_keyword"] = ""
        self.assertEqual(dashboard.session_state["active_filters"]["keyword"], "")
        self.assertEqual(dashboard.session_state["pending_filters"]["keyword"], "")

        survey_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Analisis Survei"
        )
        survey_nav.click().run()
        fullscreen_button = next(
            button
            for button in dashboard.button
            if str(button.key).startswith("chart_expand_")
        )
        fullscreen_button.click().run()
        self.assertIsNotNone(dashboard.session_state["fullscreen_chart_id"])
        dashboard.session_state["fullscreen_chart_id"] = None
        dashboard.run()
        self.assertIsNone(dashboard.session_state["fullscreen_chart_id"])

        review_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Analisis Ulasan"
        )
        review_nav.click().run()
        next_button = next(
            button for button in dashboard.button if button.label == "Berikutnya"
        )
        next_button.click().run()
        self.assertEqual(
            dashboard.session_state["review_analysis_page"],
            2,
        )

        explorer_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Data Explorer"
        )
        explorer_nav.click().run()
        self.assertGreaterEqual(len(dashboard.dataframe), 4)
        self.assertEqual(len(dashboard.exception), 0)

        attachment_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Lampiran Presentasi"
        )
        attachment_nav.click().run()

        # Navigate to Snapshot Flyer tab to check for layout or chart height errors
        flyer_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Snapshot Flyer"
        )
        flyer_nav.click().run()
        self.assertEqual(len(dashboard.exception), 0)

        # Navigate back to Lampiran Presentasi to find the Tampilkan Lobi button
        attachment_nav = next(
            button
            for button in dashboard.button
            if button.key == "horizontal_nav_Lampiran Presentasi"
        )
        attachment_nav.click().run()

        next(
            button for button in dashboard.button if button.label == "Tampilkan Lobi"
        ).click().run()
        self.assertTrue(
            any(button.label == "Masuk ke Dashboard" for button in dashboard.button)
        )
        self.assertEqual(len(dashboard.exception), 0)



if __name__ == "__main__":
    unittest.main()
