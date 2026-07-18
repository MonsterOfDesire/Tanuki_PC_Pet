import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tanuki_core.dashboard_presenter import DashboardPresenter
from tanuki_core.dashboard_tools_actions import ValidationCheckResult
from tanuki_core.household_state import HouseholdState


class DashboardPresenterTests(unittest.TestCase):
    def test_build_debug_button_formats_enabled_state(self):
        presenter = DashboardPresenter()

        presentation = presenter.build_debug_button(True)

        self.assertEqual(presentation.text, "Debug: 開啟")

    def test_build_shutdown_status_returns_expected_view_model(self):
        presenter = DashboardPresenter()

        presentation = presenter.build_shutdown_status()

        self.assertEqual(presentation.status_text, "正在儲存設定...")
        self.assertTrue(presentation.show_status)
        self.assertFalse(presentation.exit_enabled)
        self.assertEqual(presentation.exit_text, "正在關閉...")
        self.assertTrue(presentation.force_expanded)

    def test_build_validation_dialog_uses_warning_when_result_has_warnings(self):
        presenter = DashboardPresenter()
        result = ValidationCheckResult(report="warn report", warnings=("a",))

        presentation = presenter.build_validation_dialog(result)

        self.assertEqual(presentation.title, "檢查結果（有警告）")
        self.assertEqual(presentation.message, "warn report")
        self.assertEqual(presentation.severity, "warning")

    def test_build_validation_dialog_uses_information_when_result_is_clean(self):
        presenter = DashboardPresenter()
        result = ValidationCheckResult(report="ok report", warnings=())

        presentation = presenter.build_validation_dialog(result)

        self.assertEqual(presentation.title, "檢查結果（正常）")
        self.assertEqual(presentation.severity, "information")

    def test_build_household_summary_formats_overview_and_log(self):
        presenter = DashboardPresenter()
        household = SimpleNamespace(living_fund=650, household_pressure=18.5)
        entries = [
            SimpleNamespace(
                sequence=1,
                category="economy",
                event_type="expense",
                summary="帝寶偷喝飲料",
                living_fund_delta=-35,
                household_pressure_delta=8.5,
            ),
            SimpleNamespace(
                sequence=2,
                category="household",
                event_type="note",
                summary="魯道夫正在盤點家用。",
                living_fund_delta=0,
                household_pressure_delta=0.0,
            ),
        ]

        with patch("tanuki_core.dashboard_presenter.datetime") as mock_datetime:
            mock_datetime.fromtimestamp.return_value.strftime.return_value = "12:34:56"
            entries[0].wall_clock_time = 1710000000.0
            entries[1].wall_clock_time = 1710000060.0
            presentation = presenter.build_household_summary(household, entries)

        self.assertEqual(presentation.title, "家庭摘要")
        self.assertIn("生活費: 650 元", presentation.overview_text)
        self.assertIn("家庭壓力: 18%", presentation.overview_text)
        self.assertIn("#001 12:34:56 帝寶偷喝飲料 (生活費 -35, 壓力 +8.5)", presentation.log_text)
        self.assertIn("#002 12:34:56 魯道夫正在盤點家用。", presentation.log_text)

    def test_build_household_summary_filters_out_social_noise(self):
        presenter = DashboardPresenter()
        household = SimpleNamespace(living_fund=900, household_pressure=12.0)
        entries = [
            SimpleNamespace(
                sequence=1,
                wall_clock_time=0.0,
                channel="social",
                category="social",
                importance="normal",
                summary="魯道夫和帝寶聊了幾句。",
                living_fund_delta=0,
                household_pressure_delta=0.0,
            ),
            SimpleNamespace(
                sequence=2,
                wall_clock_time=0.0,
                channel="economy",
                category="economy",
                importance="normal",
                summary="帝寶又偷偷買了飲料。",
                living_fund_delta=-18,
                household_pressure_delta=4.0,
            ),
            SimpleNamespace(
                sequence=3,
                wall_clock_time=0.0,
                channel="item",
                category="player_offer",
                importance="low",
                summary="鶴寶接過奶瓶。",
                living_fund_delta=0,
                household_pressure_delta=0.0,
            ),
        ]

        presentation = presenter.build_household_summary(household, entries)

        self.assertNotIn("聊了幾句", presentation.log_text)
        self.assertIn("帝寶又偷偷買了飲料", presentation.log_text)
        self.assertIn("鶴寶接過奶瓶", presentation.log_text)

    def test_build_household_summary_keeps_only_recent_relevant_entries(self):
        presenter = DashboardPresenter()
        household = SimpleNamespace(living_fund=900, household_pressure=12.0)
        entries = [
            SimpleNamespace(
                sequence=index,
                wall_clock_time=0.0,
                channel="economy",
                category="economy",
                importance="normal",
                summary=f"生活事件 {index}",
                living_fund_delta=-1,
                household_pressure_delta=0.0,
            )
            for index in range(1, 31)
        ]

        presentation = presenter.build_household_summary(household, entries)

        self.assertNotIn("#001", presentation.log_text)
        self.assertNotIn("#006", presentation.log_text)
        self.assertIn("#007", presentation.log_text)
        self.assertIn("#030", presentation.log_text)

    def test_build_social_log_filters_by_channel_and_formats_participants(self):
        presenter = DashboardPresenter()
        entries = [
            SimpleNamespace(
                sequence=1,
                wall_clock_time=1710000000.0,
                channel="social",
                category="social",
                actor_name="Symboli Rudolf",
                target_name="Tokai Teio",
                summary="魯道夫和帝寶短暫聊了幾句。",
                living_fund_delta=0,
                household_pressure_delta=0.0,
                mood_delta=0.0,
                relation_delta={"familiarity": 0.25},
            ),
            SimpleNamespace(
                sequence=2,
                wall_clock_time=1710000060.0,
                channel="economy",
                category="economy",
                actor_name="Tokai Teio",
                target_name="",
                summary="帝寶又偷偷買了飲料。",
                living_fund_delta=-18,
                household_pressure_delta=4.0,
                mood_delta=0.0,
                relation_delta={},
            ),
            SimpleNamespace(
                sequence=3,
                wall_clock_time=1710000120.0,
                channel="item",
                category="player_offer",
                actor_name="Player",
                target_name="Tsurumaru Tsuyoshi",
                summary="鶴寶接過奶瓶，安靜地喝了起來。",
                living_fund_delta=0,
                household_pressure_delta=-3.0,
                mood_delta=0.0,
                relation_delta={},
            ),
        ]

        social = presenter.build_social_log(entries, filter_mode="social")
        economy = presenter.build_social_log(entries, filter_mode="economy")
        item = presenter.build_social_log(entries, filter_mode="item")
        personal = presenter.build_social_log(entries, filter_mode="personal", participant_name="Tokai Teio")

        self.assertIn("[社交] Symboli Rudolf -> Tokai Teio:", social.log_text)
        self.assertIn("關係 familiarity +0.25", social.log_text)
        self.assertIn("生活費 -18", economy.log_text)
        self.assertIn("鶴寶接過奶瓶", item.log_text)
        self.assertIn("#001", personal.log_text)
        self.assertIn("#002", personal.log_text)
        self.assertNotIn("#003", personal.log_text)
        self.assertEqual(personal.participant_names, ("Symboli Rudolf", "Tokai Teio", "Tsurumaru Tsuyoshi"))

    def test_build_social_log_defaults_personal_filter_to_first_known_participant(self):
        presenter = DashboardPresenter()
        entries = [
            SimpleNamespace(
                sequence=1,
                wall_clock_time=0.0,
                channel="social",
                category="social",
                actor_name="Air Groove",
                target_name="Symboli Rudolf",
                summary="氣槽和魯道夫說了幾句話。",
                living_fund_delta=0,
                household_pressure_delta=0.0,
                mood_delta=0.0,
                relation_delta={},
            ),
        ]

        presentation = presenter.build_social_log(entries, filter_mode="personal")

        self.assertEqual(presentation.participant_name, "Air Groove")
        self.assertIn("氣槽和魯道夫", presentation.log_text)

    def test_build_relationship_table_includes_all_pet_pairs_and_details(self):
        presenter = DashboardPresenter()
        household = HouseholdState()
        household.relationships.apply_delta(
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            relation_delta={
                "familiarity": 10.0,
                "trust": 5.0,
                "attachment": 2.0,
                "tension": 1.0,
            },
            updated_at=10.0,
        )

        presentation = presenter.build_relationship_table(
            household,
            pet_names=("Symboli Rudolf", "Tokai Teio", "Air Groove"),
        )

        self.assertEqual(presentation.title, "關係表")
        self.assertIn("[Symboli Rudolf]", presentation.table_text)
        self.assertIn("-> Tokai Teio: 好感度  6.50", presentation.table_text)
        self.assertIn("熟悉 10.00 / 信任  5.00 / 依附  2.00 / 緊張  1.00", presentation.table_text)
        self.assertIn("事件 1", presentation.table_text)
        self.assertIn("-> Air Groove: 好感度  0.00", presentation.table_text)
        self.assertIn("[Air Groove]", presentation.table_text)


if __name__ == "__main__":
    unittest.main()
