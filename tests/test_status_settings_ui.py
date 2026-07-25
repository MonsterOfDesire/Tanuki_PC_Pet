import os
import unittest
from dataclasses import replace
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QCheckBox, QLabel, QWidget

from tanuki_core.status_settings_binding import (
    DashboardStatusSettingsBinding,
    StatusSettingsSnapshot,
)
from tanuki_core.status_settings_ui import StatusSettingsPanel
from tanuki_core.ui_controls import ToggleSwitch


class FakeStatusSettingsBinding:
    def __init__(self):
        self.state = StatusSettingsSnapshot(
            world_mode="golden_legend",
            world_mode_options=("golden_legend", "sandbox"),
            care_feature_enabled=True,
            debug_enabled=False,
            social_status_enabled=False,
            time_scale_options=(1.0, 2.0, 4.0, 8.0),
            time_scale_index=0,
            display_scale_options=(1.0, 1.5, 2.0, 3.0),
            display_scale_index=1,
            teio_duration_options=(2, 5, 10, 20, 30),
            teio_duration_index=2,
            tsuyoshi_duration_options=(2, 10, 20, 40, 60),
            tsuyoshi_duration_index=3,
        )
        self.calls = []

    def snapshot(self):
        return self.state

    def set_debug_enabled(self, enabled):
        self.calls.append(("debug", enabled))
        self.state = replace(self.state, debug_enabled=bool(enabled))

    def set_world_mode(self, world_mode):
        self.calls.append(("world_mode", world_mode))
        self.state = replace(self.state, world_mode=str(world_mode))

    def set_care_feature_enabled(self, enabled):
        self.calls.append(("care", enabled))
        self.state = replace(
            self.state,
            care_feature_enabled=bool(enabled),
        )

    def set_social_status_enabled(self, enabled):
        self.calls.append(("social_status", enabled))
        self.state = replace(
            self.state,
            social_status_enabled=bool(enabled),
        )

    def set_time_scale_index(self, index):
        self.calls.append(("time", index))
        self.state = replace(self.state, time_scale_index=index)

    def set_display_scale_index(self, index):
        self.calls.append(("display", index))
        self.state = replace(self.state, display_scale_index=index)

    def set_social_duration_index(self, character_key, index):
        self.calls.append((character_key, index))
        field_name = f"{character_key}_duration_index"
        self.state = replace(self.state, **{field_name: index})

    def run_validation_checks(self):
        self.calls.append(("validate",))


class FakeDashboardForBinding:
    def __init__(self):
        self.world_mode_options = ["golden_legend", "sandbox"]
        self.time_scale_options = [1, 2, 4, 8]
        self.display_scale_options = [1.0, 1.5, 2.0, 3.0]
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.calls = []

    def capture_config_state(self):
        return SimpleNamespace(
            world_mode="sandbox",
            care_feature_enabled=False,
            debug_enabled=True,
            social_status_enabled=False,
            time_scale_idx=2,
            display_scale_idx=1,
            teio_dur_idx=3,
            tsuyoshi_dur_idx=4,
        )

    def set_debug_enabled(self, value):
        self.calls.append(("debug", value))

    def set_world_mode(self, world_mode):
        self.calls.append(("world_mode", world_mode))

    def set_care_enabled(self, enabled):
        self.calls.append(("care", enabled))

    def set_social_status_enabled(self, enabled):
        self.calls.append(("social_status", enabled))

    def set_time_scale_index(self, index):
        self.calls.append(("time", index))

    def set_display_scale_index(self, index):
        self.calls.append(("display", index))

    def set_duration(self, character_key, index):
        self.calls.append((character_key, index))

    def run_validation_checks(self):
        self.calls.append(("validate",))


class StatusSettingsPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.binding = FakeStatusSettingsBinding()
        self.panel = StatusSettingsPanel(self.binding)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_panel_reflects_snapshot_selection(self):
        self.assertTrue(self.panel.world_mode_buttons[0].isChecked())
        self.assertIsInstance(self.panel.care_switch, ToggleSwitch)
        self.assertIsInstance(self.panel.debug_switch, ToggleSwitch)
        self.assertIsInstance(
            self.panel.social_status_switch,
            ToggleSwitch,
        )
        self.assertTrue(self.panel.care_switch.isChecked())
        self.assertFalse(self.panel.debug_switch.isChecked())
        self.assertFalse(self.panel.social_status_switch.isChecked())
        self.assertEqual(self.panel.findChildren(QCheckBox), [])
        self.assertTrue(self.panel.display_scale_buttons[1].isChecked())
        self.assertTrue(self.panel.teio_duration_buttons[2].isChecked())
        self.assertTrue(self.panel.tsuyoshi_duration_buttons[3].isChecked())

    def test_social_cooldown_uses_localized_full_character_names(self):
        visible_labels = {
            label.text()
            for label in self.panel.findChildren(QLabel)
        }

        self.assertIn("東海帝皇", visible_labels)
        self.assertIn("鶴丸強志", visible_labels)

    def test_compact_width_reduces_spacing_without_overlapping_options(self):
        host = QWidget()
        host.setFixedSize(600, 260)
        compact_panel = StatusSettingsPanel(self.binding, parent=host)
        compact_panel.setGeometry(host.rect())
        host.show()
        self.app.processEvents()

        self.assertTrue(compact_panel._compact_layout)
        self.assertTrue(
            all(
                button.property("compact")
                for button in (
                    compact_panel.world_mode_buttons
                    + compact_panel.time_scale_buttons
                    + compact_panel.display_scale_buttons
                    + compact_panel.teio_duration_buttons
                    + compact_panel.tsuyoshi_duration_buttons
                )
            )
        )
        for group, button_rows in (
            (
                compact_panel.runtime_group,
                (compact_panel.world_mode_buttons,),
            ),
            (
                compact_panel.timing_group,
                (
                    compact_panel.time_scale_buttons,
                    compact_panel.display_scale_buttons,
                ),
            ),
            (
                compact_panel.social_group,
                (
                    compact_panel.teio_duration_buttons,
                    compact_panel.tsuyoshi_duration_buttons,
                ),
            ),
        ):
            for buttons in button_rows:
                geometries = []
                for button in buttons:
                    top_left = button.mapTo(group, QPoint(0, 0))
                    geometries.append(
                        (
                            top_left.x(),
                            top_left.x() + button.width(),
                        )
                    )
                    self.assertGreaterEqual(top_left.x(), 0)
                    self.assertLessEqual(
                        top_left.x() + button.width(),
                        group.width() + 1,
                    )
                for previous, current in zip(geometries, geometries[1:]):
                    self.assertLessEqual(previous[1], current[0])
        host.close()
        compact_panel.deleteLater()
        host.deleteLater()

    def test_wide_width_restores_regular_option_spacing(self):
        self.panel.resize(900, 300)
        self.app.processEvents()

        self.assertFalse(self.panel._compact_layout)
        self.assertTrue(
            all(
                not button.property("compact")
                for button in self.panel.teio_duration_buttons
            )
        )

    def test_panel_delegates_setting_changes_to_binding(self):
        self.panel.time_scale_buttons[3].click()
        self.panel.display_scale_buttons[2].click()
        self.panel.teio_duration_buttons[4].click()
        self.panel.tsuyoshi_duration_buttons[1].click()
        self.panel.world_mode_buttons[1].click()
        self.panel.care_switch.click()
        self.panel.debug_switch.click()
        self.panel.social_status_switch.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("time", 3),
                ("display", 2),
                ("teio", 4),
                ("tsuyoshi", 1),
                ("world_mode", "sandbox"),
                ("care", False),
                ("debug", True),
                ("social_status", True),
            ],
        )

    def test_validation_action_uses_existing_binding_path(self):
        self.panel.validation_button.click()

        self.assertEqual(self.binding.calls, [("validate",)])

    def test_external_state_refresh_updates_controls(self):
        self.binding.state = replace(
            self.binding.state,
            debug_enabled=True,
            time_scale_index=2,
        )

        self.panel.refresh_from_binding()

        self.assertTrue(self.panel.debug_switch.isChecked())
        self.assertTrue(self.panel.time_scale_buttons[2].isChecked())


class DashboardStatusSettingsBindingTests(unittest.TestCase):
    def test_snapshot_reuses_dashboard_config_state_and_options(self):
        dashboard = FakeDashboardForBinding()
        binding = DashboardStatusSettingsBinding(dashboard)

        snapshot = binding.snapshot()

        self.assertTrue(snapshot.debug_enabled)
        self.assertEqual(snapshot.world_mode, "sandbox")
        self.assertFalse(snapshot.care_feature_enabled)
        self.assertFalse(snapshot.social_status_enabled)
        self.assertEqual(snapshot.time_scale_index, 2)
        self.assertEqual(snapshot.display_scale_options, (1.0, 1.5, 2.0, 3.0))
        self.assertEqual(snapshot.tsuyoshi_duration_index, 4)

    def test_actions_delegate_to_existing_dashboard_controller_entry_points(self):
        dashboard = FakeDashboardForBinding()
        binding = DashboardStatusSettingsBinding(dashboard)

        binding.set_debug_enabled(False)
        binding.set_world_mode("golden_legend")
        binding.set_care_feature_enabled(True)
        binding.set_social_status_enabled(True)
        binding.set_time_scale_index(1)
        binding.set_display_scale_index(3)
        binding.set_social_duration_index("teio", 2)
        binding.run_validation_checks()

        self.assertEqual(
            dashboard.calls,
            [
                ("debug", False),
                ("world_mode", "golden_legend"),
                ("care", True),
                ("social_status", True),
                ("time", 1),
                ("display", 3),
                ("teio", 2),
                ("validate",),
            ],
        )


if __name__ == "__main__":
    unittest.main()
