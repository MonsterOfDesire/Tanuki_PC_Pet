import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from tanuki_core.dashboard_presenter import (
    HouseholdMemberPresentation,
    HouseholdRecentEventPresentation,
    HouseholdSummaryPresentation,
)
from tanuki_core.family_summary_binding import DashboardFamilySummaryBinding
from tanuki_core.family_summary_ui import FamilySummaryPanel


class FakeFamilySummaryBinding:
    def __init__(self):
        self.calls = 0
        self.donation_calls = []
        self.donation_enabled = True
        self.value = HouseholdSummaryPresentation(
            title="家庭摘要",
            overview_text="生活費: 1,250 元\n家庭壓力: 37%",
            log_text="#001 補充生活費\n#002 家庭壓力下降",
            living_fund=1250,
            household_pressure=37.4,
            members=(
                HouseholdMemberPresentation(
                    character_name="Air Groove",
                    summoned=True,
                    mood_score=72.0,
                    mood_state="normal",
                    mood_label="平穩",
                ),
                HouseholdMemberPresentation(
                    character_name="Tokai Teio",
                    summoned=False,
                    mood_score=34.0,
                    mood_state="unhappy",
                    mood_label="低落",
                ),
            ),
            recent_events=(
                HouseholdRecentEventPresentation(
                    sequence=2,
                    timestamp_text="07/22 21:46",
                    channel="economy",
                    channel_label="經濟",
                    summary="家庭壓力下降",
                    delta_text="壓力 -3.0",
                ),
            ),
            member_count=2,
            summoned_count=1,
            average_mood=53.0,
            recent_event_count=2,
            recent_fund_delta=250,
            recent_pressure_delta=-3.0,
        )

    def presentation(self):
        self.calls += 1
        return self.value

    def can_donate_fund(self):
        return self.donation_enabled

    def donate_fund(self, amount=100):
        self.donation_calls.append(amount)


class FamilySummaryPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.binding = FakeFamilySummaryBinding()
        self.panel = FamilySummaryPanel(self.binding)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_panel_renders_structured_household_values_and_events(self):
        self.assertEqual(self.panel.fund_value_label.text(), "1,250 元")
        self.assertEqual(self.panel.pressure_value_label.text(), "37%")
        self.assertEqual(self.panel.pressure_bar.value(), 37)
        self.assertEqual(self.panel.summon_value_label.text(), "1 / 2")
        self.assertEqual(tuple(self.panel.member_cards), ("Air Groove", "Tokai Teio"))
        self.assertTrue(
            self.panel.member_cards["Air Groove"].member.summoned
        )
        self.assertEqual(
            self.panel.member_cards["Air Groove"].name_label.text(),
            "氣槽",
        )
        self.assertEqual(
            self.panel.member_cards["Tokai Teio"].name_label.text(),
            "東海帝皇",
        )
        self.assertEqual(
            self.panel.member_cards["Tokai Teio"].mood_bar.value(),
            34,
        )
        self.assertEqual(self.panel.recent_event_table.rowCount(), 1)
        self.assertIn(
            "家庭壓力下降",
            self.panel.recent_event_table.item(0, 2).text(),
        )
        self.assertEqual(
            self.panel.stat_value_labels["average_mood"].text(),
            "53 / 100",
        )
        self.assertEqual(
            self.panel.stat_value_labels["fund_delta"].text(),
            "+250 元",
        )

    def test_panel_omits_redundant_manual_refresh_control(self):
        initial_calls = self.binding.calls

        self.panel.refresh_from_binding()

        self.assertFalse(hasattr(self.panel, "refresh_button"))
        self.assertEqual(self.binding.calls, initial_calls + 1)

    def test_donation_action_uses_family_binding_and_refreshes(self):
        initial_calls = self.binding.calls

        self.panel.donate_button.click()

        self.assertEqual(self.binding.donation_calls, [100])
        self.assertEqual(self.binding.calls, initial_calls + 1)

    def test_donation_action_disables_outside_supported_world_mode(self):
        self.binding.donation_enabled = False

        self.panel.refresh_from_binding()

        self.assertFalse(self.panel.donate_button.isEnabled())
        self.assertIn("黃金傳說", self.panel.donate_button.toolTip())

    def test_achievement_summary_reserves_disabled_slot_without_fake_progress(self):
        self.assertEqual(
            self.panel.achievement_slot.objectName(),
            "tanukiAchievementSummarySlot",
        )
        self.assertFalse(self.panel.achievement_slot.isEnabled())
        self.assertEqual(
            self.panel.achievement_status_label.text(),
            "尚未啟用",
        )
        self.assertFalse(self.panel.achievement_icon_label.pixmap().isNull())
        self.assertIn(
            "尚未啟用",
            self.panel.achievement_slot.accessibleName(),
        )

    def test_panel_handles_uninitialized_household_data(self):
        self.binding.value = HouseholdSummaryPresentation(
            title="家庭摘要",
            overview_text="家庭資料尚未初始化。",
            log_text="目前尚無家庭重點事件。",
        )

        self.panel.refresh_from_binding()

        self.assertEqual(self.panel.fund_value_label.text(), "--")
        self.assertEqual(self.panel.pressure_value_label.text(), "--")
        self.assertEqual(self.panel.recent_event_table.rowCount(), 0)
        self.assertTrue(self.panel.events_empty_label.isVisible())


class DashboardFamilySummaryBindingTests(unittest.TestCase):
    def test_binding_reuses_controller_presentation_entry_point(self):
        expected = object()

        class Controller:
            def __init__(self):
                self.calls = []

            def build_household_summary_presentation(self, dashboard):
                self.calls.append(dashboard)
                return expected

        class Dashboard:
            def __init__(self):
                self.controller = Controller()
                self.world_mode = "golden_legend"
                self.donation_calls = []

            def donate_household_fund(self, amount=100):
                self.donation_calls.append(amount)

        dashboard = Dashboard()
        binding = DashboardFamilySummaryBinding(dashboard)

        result = binding.presentation()

        self.assertIs(result, expected)
        self.assertEqual(dashboard.controller.calls, [dashboard])
        self.assertTrue(binding.can_donate_fund())

        binding.donate_fund(100)

        self.assertEqual(dashboard.donation_calls, [100])


if __name__ == "__main__":
    unittest.main()
