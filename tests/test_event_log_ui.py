import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from tanuki_core.dashboard_presenter import (
    SocialLogDetailPresentation,
    SocialLogEffectPresentation,
    SocialLogEntryPresentation,
    SocialLogPresentation,
)
from tanuki_core.dashboard_ui import Dashboard
from tanuki_core.event_log_binding import DashboardEventLogBinding
from tanuki_core.event_log_ui import EventLogPanel
from tanuki_core.information_center_spec import PAGE_EVENT_LOG
from tanuki_core.ui_icons import METRIC_COLORS, create_metric_icon


def _pixmap_contains_color(pixmap, expected_color):
    image = pixmap.toImage()
    expected_rgb = expected_color.rgb() & 0x00FFFFFF
    return any(
        image.pixelColor(x, y).alpha() > 0
        and (image.pixelColor(x, y).rgb() & 0x00FFFFFF) == expected_rgb
        for y in range(image.height())
        for x in range(image.width())
    )


class FakeEventLogBinding:
    def __init__(self):
        self.calls = []

    def presentation(self, filter_mode="all", participant_name=""):
        self.calls.append((filter_mode, participant_name))
        names = ("Symboli Rudolf", "Tokai Teio")
        if filter_mode == "personal" and participant_name not in names:
            participant_name = names[0]
        entries = (
            SocialLogEntryPresentation(
                sequence=102,
                timestamp_text="06/01 09:15",
                channel="social",
                channel_label="社交",
                category="social",
                event_type="chat",
                importance="normal",
                summary=f"mode={filter_mode} participant={participant_name}",
                actor_name="Symboli Rudolf",
                target_name="Tokai Teio",
                participant_text="Symboli Rudolf → Tokai Teio",
                effects=(
                    SocialLogEffectPresentation(
                        key="relationship_familiarity",
                        label="熟悉",
                        value=0.25,
                        value_text="+0.25",
                    ),
                    SocialLogEffectPresentation(
                        key="relationship_trust",
                        label="信任",
                        value=0.12,
                        value_text="+0.12",
                    ),
                    SocialLogEffectPresentation(
                        key="relationship_attachment",
                        label="依附",
                        value=0.08,
                        value_text="+0.08",
                    ),
                    SocialLogEffectPresentation(
                        key="relationship_tension",
                        label="緊張",
                        value=-0.05,
                        value_text="-0.05",
                    ),
                ),
                tags=("social", "chat"),
                details=(
                    SocialLogDetailPresentation("比賽距離", "842 px"),
                    SocialLogDetailPresentation("贏家", "Tokai Teio"),
                ),
            ),
            SocialLogEntryPresentation(
                sequence=101,
                timestamp_text="06/01 08:42",
                channel="economy",
                channel_label="經濟",
                category="economy",
                event_type="income",
                importance="major",
                summary="家庭帳戶收到薪資。",
                actor_name="",
                target_name="",
                participant_text="家庭／系統",
                effects=(
                    SocialLogEffectPresentation(
                        key="living_fund",
                        label="生活費",
                        value=5000.0,
                        value_text="+5,000 元",
                    ),
                ),
                tags=("salary",),
            ),
        )
        return SocialLogPresentation(
            title=f"事件日誌 - {filter_mode}",
            filter_mode=filter_mode,
            participant_name=participant_name,
            participant_names=names,
            log_text=f"mode={filter_mode} participant={participant_name}",
            entries=entries,
        )


class EventLogPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.binding = FakeEventLogBinding()
        self.panel = EventLogPanel(self.binding)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_panel_starts_with_all_filter_and_disabled_character_picker(self):
        self.assertTrue(self.panel.filter_buttons["all"].isChecked())
        self.assertFalse(self.panel.participant_combo.isEnabled())
        self.assertEqual(self.panel.participant_combo.currentIndex(), -1)
        self.assertFalse(self.panel.participant_combo.property("personalActive"))
        self.assertLessEqual(self.panel.participant_combo.maximumWidth(), 104)
        self.assertEqual(self.panel.event_table.rowCount(), 2)
        self.assertTrue(self.panel.event_table.showGrid())
        self.assertEqual(self.panel.event_table.rowHeight(0), 48)
        self.assertFalse(self.panel.filter_buttons["social"].icon().isNull())
        self.assertFalse(
            self.panel.event_table.item(0, self.panel.CHANNEL_COLUMN).icon().isNull()
        )
        self.assertIn(
            "mode=all",
            self.panel.event_table.item(0, self.panel.SUMMARY_COLUMN).text(),
        )

    def test_filter_and_character_selection_request_presentations(self):
        self.panel.filter_buttons["personal"].click()
        self.panel.participant_combo.setCurrentIndex(
            self.panel.participant_combo.findData("Tokai Teio")
        )

        self.assertEqual(self.panel.filter_mode, "personal")
        self.assertTrue(self.panel.participant_combo.isEnabled())
        self.assertTrue(self.panel.participant_combo.property("personalActive"))
        self.assertEqual(self.panel.participant_combo.currentText(), "東海帝皇")
        self.assertEqual(self.panel.participant_combo.currentData(), "Tokai Teio")
        self.assertIn(("personal", ""), self.binding.calls)
        self.assertEqual(self.binding.calls[-1], ("personal", "Tokai Teio"))
        self.assertIn("東海帝皇", self.panel.detail_summary_label.text())

    def test_non_personal_filter_hides_selected_character_name(self):
        self.panel.filter_buttons["personal"].click()
        self.panel.participant_combo.setCurrentIndex(
            self.panel.participant_combo.findData("Tokai Teio")
        )
        self.panel.filter_buttons["social"].click()

        self.assertFalse(self.panel.participant_combo.isEnabled())
        self.assertEqual(self.panel.participant_combo.currentIndex(), -1)
        self.assertFalse(self.panel.participant_combo.property("personalActive"))

    def test_channel_filter_uses_same_event_log_binding(self):
        self.panel.filter_buttons["economy"].click()

        self.assertEqual(self.binding.calls[-1][0], "economy")
        self.assertTrue(self.panel.filter_buttons["economy"].isChecked())

    def test_event_rows_localize_names_without_mutating_entry_keys(self):
        participant_item = self.panel.event_table.item(
            0,
            self.panel.PARTICIPANT_COLUMN,
        )

        self.assertEqual(participant_item.text(), "魯道夫象徵 → 東海帝皇")
        self.assertEqual(self.panel.entries[0].actor_name, "Symboli Rudolf")
        self.assertEqual(self.panel.entries[0].target_name, "Tokai Teio")

    def test_panel_omits_manual_refresh_but_runtime_refresh_keeps_filter(self):
        self.panel.filter_buttons["item"].click()
        previous_calls = len(self.binding.calls)

        self.panel.refresh_from_binding()

        self.assertFalse(hasattr(self.panel, "refresh_button"))
        self.assertEqual(len(self.binding.calls), previous_calls + 1)
        self.assertEqual(self.binding.calls[-1][0], "item")

    def test_selecting_event_updates_structured_detail_panel(self):
        self.panel.event_table.selectRow(1)
        self.panel.event_table.setCurrentCell(1, self.panel.SUMMARY_COLUMN)
        self.app.processEvents()

        self.assertEqual(self.panel.selected_entry.sequence, 101)
        self.assertEqual(self.panel.detail_channel_label.text(), "經濟")
        self.assertEqual(self.panel.detail_summary_label.text(), "家庭帳戶收到薪資。")
        self.assertEqual(
            self.panel.effect_value_labels["living_fund"].text(),
            "+5,000 元",
        )
        self.assertIn("#salary", self.panel.detail_tags_label.text())

    def test_structured_race_details_are_rendered_and_localized(self):
        self.panel.event_table.selectRow(0)
        self.panel.event_table.setCurrentCell(0, self.panel.SUMMARY_COLUMN)
        self.app.processEvents()

        self.assertEqual(
            self.panel.detail_value_labels["比賽距離"].text(),
            "842 px",
        )
        self.assertEqual(
            self.panel.detail_value_labels["贏家"].text(),
            "東海帝皇",
        )

    def test_relationship_effects_use_canonical_relation_icons_and_colors(self):
        for metric_kind, expected_color in METRIC_COLORS.items():
            effect_key = f"relationship_{metric_kind}"
            icon_pixmap = self.panel.effect_icon_labels[effect_key].pixmap()
            expected_pixmap = create_metric_icon(metric_kind, size=18).pixmap(18, 18)

            self.assertEqual(icon_pixmap.toImage(), expected_pixmap.toImage())
            self.assertTrue(_pixmap_contains_color(icon_pixmap, QColor(expected_color)))
            self.assertEqual(
                self.panel.effect_value_labels[effect_key].property("metricKind"),
                metric_kind,
            )

    def test_system_filter_is_available_and_uses_existing_binding(self):
        self.panel.filter_buttons["system"].click()

        self.assertEqual(self.binding.calls[-1][0], "system")
        self.assertTrue(self.panel.filter_buttons["system"].isChecked())

    def test_runtime_refresh_preserves_selected_event_when_it_still_exists(self):
        self.panel.event_table.setCurrentCell(1, self.panel.SUMMARY_COLUMN)
        self.panel.refresh_from_binding()

        self.assertEqual(self.panel.selected_entry.sequence, 101)
        self.assertEqual(self.panel.detail_summary_label.text(), "家庭帳戶收到薪資。")


class DashboardEventLogBindingTests(unittest.TestCase):
    def test_binding_reuses_controller_social_log_presentation_entry_point(self):
        expected = object()

        class Controller:
            def __init__(self):
                self.calls = []

            def build_social_log_presentation(self, dashboard, filter_mode="all", participant_name=""):
                self.calls.append((dashboard, filter_mode, participant_name))
                return expected

        class Dashboard:
            def __init__(self):
                self.controller = Controller()

        dashboard = Dashboard()
        binding = DashboardEventLogBinding(dashboard)

        result = binding.presentation("personal", "Tokai Teio")

        self.assertIs(result, expected)
        self.assertEqual(dashboard.controller.calls, [(dashboard, "personal", "Tokai Teio")])


class DashboardEventLogRefreshTests(unittest.TestCase):
    def test_household_event_refreshes_visible_current_event_log_page(self):
        information_center = SimpleNamespace(
            is_page_visible=lambda page_id: page_id == PAGE_EVENT_LOG,
            refresh_event_log_calls=0,
        )

        def refresh_event_log():
            information_center.refresh_event_log_calls += 1

        information_center.refresh_event_log = refresh_event_log
        dashboard = SimpleNamespace(
            social_log_window=None,
            information_center_window=information_center,
        )

        Dashboard.refresh_social_log_if_open(dashboard)

        self.assertEqual(information_center.refresh_event_log_calls, 1)

    def test_household_event_does_not_refresh_background_information_page(self):
        information_center = SimpleNamespace(
            is_page_visible=lambda page_id: False,
            refresh_event_log_calls=0,
        )

        def refresh_event_log():
            information_center.refresh_event_log_calls += 1

        information_center.refresh_event_log = refresh_event_log
        dashboard = SimpleNamespace(
            social_log_window=None,
            information_center_window=information_center,
        )

        Dashboard.refresh_social_log_if_open(dashboard)

        self.assertEqual(information_center.refresh_event_log_calls, 0)


if __name__ == "__main__":
    unittest.main()
