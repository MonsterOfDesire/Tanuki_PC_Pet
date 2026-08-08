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
        self.preview_result = SimpleNamespace(
            started=True,
            reason="",
        )
        self.preview_active = False
        self.race_preview_result = SimpleNamespace(
            started=True,
            reason="",
        )
        self.race_preview_active = False
        self.transformation_states = {
            "Tokai Teio": {
                "available": True,
                "current_form": "base",
                "target_form": "",
                "active": False,
                "manual_end_requested": False,
                "auto_session": False,
                "auto_world_mode": "",
                "source": "",
            },
            "Symboli Rudolf": {
                "available": True,
                "current_form": "base",
                "target_form": "",
                "active": False,
                "manual_end_requested": False,
                "auto_session": False,
                "auto_world_mode": "",
                "source": "",
            },
        }
        self.transformation_result = SimpleNamespace(
            started=True,
            reason="",
            character_name="Tokai Teio",
            target_form="transformed",
            queued=False,
        )

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

    def set_race_frequency(self, value):
        self.calls.append(("race_frequency", value))
        self.state = replace(self.state, race_frequency=value)

    def set_mood_climate(self, value):
        self.calls.append(("mood_climate", value))
        self.state = replace(self.state, mood_climate=value)

    def run_validation_checks(self):
        self.calls.append(("validate",))

    def preview_rudolf_work(self):
        self.calls.append(("preview_rudolf_work",))
        self.preview_active = bool(self.preview_result.started)
        return self.preview_result

    def is_rudolf_work_preview_active(self):
        self.calls.append(("preview_active",))
        return self.preview_active

    def preview_rudolf_teio_race(self):
        self.calls.append(("preview_race",))
        self.race_preview_active = bool(self.race_preview_result.started)
        return self.race_preview_result

    def is_race_preview_active(self):
        self.calls.append(("race_preview_active",))
        return self.race_preview_active

    def toggle_transformation_preview(self, pet_name):
        self.calls.append(("transformation", pet_name))
        self.transformation_result.character_name = pet_name
        current_form = self.transformation_states[pet_name]["current_form"]
        self.transformation_result.target_form = (
            "base" if current_form == "transformed" else "transformed"
        )
        state = self.transformation_states[pet_name]
        if self.transformation_result.started:
            state.update(
                target_form=self.transformation_result.target_form,
                active=True,
                manual_end_requested=False,
                auto_session=False,
                source="settings_preview",
            )
        elif self.transformation_result.queued:
            state["manual_end_requested"] = True
        return self.transformation_result

    def get_transformation_preview_state(self, pet_name):
        return dict(self.transformation_states[pet_name])


class FakeDashboardForBinding:
    def __init__(self):
        self.world_mode_options = ["golden_legend", "sandbox"]
        self.time_scale_options = [1, 2, 4, 8]
        self.display_scale_options = [1.0, 1.5, 2.0, 3.0]
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.race_frequency_options = ["frequent", "normal", "occasional"]
        self.mood_climate_options = ["cheerful", "balanced", "expressive"]
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
            race_frequency="normal",
            mood_climate="cheerful",
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

    def set_race_frequency(self, value):
        self.calls.append(("race_frequency", value))

    def set_mood_climate(self, value):
        self.calls.append(("mood_climate", value))

    def run_validation_checks(self):
        self.calls.append(("validate",))

    def preview_rudolf_work(self):
        self.calls.append(("preview_rudolf_work",))
        return "preview-result"

    def is_rudolf_work_preview_active(self):
        self.calls.append(("preview_active",))
        return True

    def preview_rudolf_teio_race(self):
        self.calls.append(("preview_race",))
        return "race-preview-result"

    def is_race_preview_active(self):
        self.calls.append(("race_preview_active",))
        return True

    def toggle_transformation_preview(self, pet_name):
        self.calls.append(("transformation", pet_name))
        return f"transformation-result:{pet_name}"

    def get_transformation_preview_state(self, pet_name):
        self.calls.append(("transformation_state", pet_name))
        return {
            "available": True,
            "current_form": "transformed",
            "active": False,
        }


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
        self.assertTrue(compact_panel._single_column_layout)
        self.assertGreater(
            compact_panel.settings_scroll.verticalScrollBar().maximum(),
            0,
        )
        self.assertEqual(
            compact_panel.settings_scroll.horizontalScrollBar().maximum(),
            0,
        )
        self.assertTrue(
            all(
                button.property("compact")
                for button in (
                    compact_panel.world_mode_buttons
                    + compact_panel.time_scale_buttons
                    + compact_panel.display_scale_buttons
                    + compact_panel.teio_duration_buttons
                    + compact_panel.tsuyoshi_duration_buttons
                    + compact_panel.race_frequency_buttons
                    + compact_panel.mood_climate_buttons
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
            (
                compact_panel.rhythm_group,
                (
                    compact_panel.race_frequency_buttons,
                    compact_panel.mood_climate_buttons,
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

    def test_wide_layout_stacks_settings_beside_full_height_developer_tools(self):
        host = QWidget()
        host.setFixedSize(988, 383)
        wide_panel = StatusSettingsPanel(self.binding, parent=host)
        wide_panel.setGeometry(host.rect())
        host.show()
        self.app.processEvents()

        self.assertFalse(wide_panel._single_column_layout)
        expected_positions = {
            wide_panel.runtime_group: (0, 0, 1, 1),
            wide_panel.timing_group: (1, 0, 1, 1),
            wide_panel.social_group: (2, 0, 1, 1),
            wide_panel.rhythm_group: (3, 0, 1, 1),
            wide_panel.developer_group: (0, 1, 4, 1),
        }
        actual_positions = {}
        for index in range(wide_panel.grid_layout.count()):
            item = wide_panel.grid_layout.itemAt(index)
            widget = item.widget()
            if widget in expected_positions:
                actual_positions[widget] = (
                    wide_panel.grid_layout.getItemPosition(index)
                )

        self.assertEqual(actual_positions, expected_positions)
        self.assertGreater(
            wide_panel.developer_group.height(),
            wide_panel.social_group.height(),
        )
        self.assertEqual(
            wide_panel.settings_scroll.horizontalScrollBar().maximum(),
            0,
        )
        host.close()
        wide_panel.deleteLater()
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
        self.panel.race_frequency_buttons[0].click()
        self.panel.mood_climate_buttons[2].click()

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
                ("race_frequency", "frequent"),
                ("mood_climate", "expressive"),
            ],
        )

    def test_validation_action_uses_existing_binding_path(self):
        self.panel.validation_button.click()

        self.assertEqual(self.binding.calls, [("validate",)])

    def test_rudolf_work_preview_is_sandbox_only_and_reports_start(self):
        self.assertFalse(
            self.panel.rudolf_work_preview_button.isEnabled()
        )

        self.panel.world_mode_buttons[1].click()
        self.panel.rudolf_work_preview_button.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("world_mode", "sandbox"),
                ("preview_rudolf_work",),
            ],
        )
        self.assertIn(
            "魯道夫工作預覽已開始",
            self.panel.rudolf_work_preview_status.text(),
        )

        self.binding.preview_active = False
        self.panel._poll_rudolf_work_preview_status()

        self.assertEqual(
            self.panel.rudolf_work_preview_status.text(),
            "只播放工作與休息動畫，不套用金錢、家庭壓力或心情結算。",
        )
        self.assertFalse(
            self.panel.rudolf_work_preview_poll_timer.isActive()
        )

    def test_rudolf_work_preview_explains_severe_mood(self):
        self.binding.state = replace(
            self.binding.state,
            world_mode="sandbox",
        )
        self.binding.preview_result = SimpleNamespace(
            started=False,
            reason="severe_mood",
        )
        self.panel.refresh_from_binding()

        self.panel.rudolf_work_preview_button.click()

        self.assertIn(
            "severe",
            self.panel.rudolf_work_preview_status.text(),
        )

    def test_race_preview_is_sandbox_only_and_resets_after_completion(self):
        self.assertFalse(self.panel.race_preview_button.isEnabled())

        self.panel.world_mode_buttons[1].click()
        self.panel.race_preview_button.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("world_mode", "sandbox"),
                ("preview_race",),
            ],
        )
        self.assertIn(
            "競賽預覽已開始",
            self.panel.race_preview_status.text(),
        )
        self.assertTrue(self.panel.race_preview_poll_timer.isActive())

        self.binding.race_preview_active = False
        self.panel._poll_race_preview_status()

        self.assertIn(
            "不寫入事件",
            self.panel.race_preview_status.text(),
        )
        self.assertFalse(self.panel.race_preview_poll_timer.isActive())

    def test_race_preview_explains_transformed_teio_capability_gate(self):
        self.binding.state = replace(
            self.binding.state,
            world_mode="sandbox",
        )
        self.binding.race_preview_result = SimpleNamespace(
            started=False,
            reason="Tokai Teio:form_blocks_race",
        )
        self.panel.refresh_from_binding()

        self.panel.race_preview_button.click()

        self.assertIn("帝寶目前形態不能參賽", self.panel.race_preview_status.text())

    def test_race_preview_explains_that_participants_must_be_nearby(self):
        self.binding.state = replace(
            self.binding.state,
            world_mode="sandbox",
        )
        self.binding.race_preview_result = SimpleNamespace(
            started=False,
            reason="participants_too_far",
        )
        self.panel.refresh_from_binding()

        self.panel.race_preview_button.click()

        self.assertIn("距離太遠", self.panel.race_preview_status.text())

    def test_race_preview_explains_that_overlapping_participants_must_separate(self):
        self.binding.state = replace(
            self.binding.state,
            world_mode="sandbox",
        )
        self.binding.race_preview_result = SimpleNamespace(
            started=False,
            reason="participants_too_close",
        )
        self.panel.refresh_from_binding()

        self.panel.race_preview_button.click()

        self.assertIn("距離太近", self.panel.race_preview_status.text())

    def test_transformation_preview_is_sandbox_only_and_refreshes_form(self):
        teio_button = self.panel.transformation_preview_buttons[
            "Tokai Teio"
        ]
        self.assertFalse(teio_button.isEnabled())

        self.panel.world_mode_buttons[1].click()
        teio_button.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("world_mode", "sandbox"),
                ("transformation", "Tokai Teio"),
            ],
        )
        self.assertIn(
            "帝寶變身中",
            self.panel.transformation_preview_status.text(),
        )
        self.assertTrue(
            self.panel.transformation_preview_poll_timer.isActive()
        )

        self.binding.transformation_states["Tokai Teio"].update(
            current_form="transformed",
            target_form="",
            active=False,
            source="",
        )
        self.panel._poll_transformation_preview_status()

        self.assertEqual(teio_button.text(), "解除帝寶變身")
        self.assertEqual(
            self.panel.transformation_preview_status.text(),
            "帝寶已完成變身，目前為變身形態。",
        )
        self.assertTrue(
            self.panel.transformation_preview_poll_timer.isActive()
        )

    def test_queued_transformation_end_waits_for_safe_runtime_state(self):
        self.panel.world_mode_buttons[1].click()
        self.binding.transformation_states["Tokai Teio"].update(
            current_form="transformed",
            active=False,
        )
        self.binding.transformation_result.started = False
        self.binding.transformation_result.queued = True
        teio_button = self.panel.transformation_preview_buttons[
            "Tokai Teio"
        ]

        teio_button.click()
        self.binding.transformation_states["Tokai Teio"][
            "manual_end_requested"
        ] = True
        self.panel.refresh_from_binding()

        self.assertIn(
            "排入等待",
            self.panel.transformation_preview_status.text(),
        )
        self.assertEqual(
            teio_button.text(),
            "等待解除帝寶變身",
        )
        self.assertFalse(teio_button.isEnabled())
        self.assertTrue(
            self.panel.transformation_preview_poll_timer.isActive()
        )

    def test_autonomous_form_then_manual_end_uses_final_runtime_state(self):
        self.panel.world_mode_buttons[1].click()
        teio_state = self.binding.transformation_states["Tokai Teio"]
        teio_state.update(
            current_form="transformed",
            target_form="",
            active=False,
            auto_session=True,
            auto_world_mode="sandbox",
            source="",
        )

        self.panel._poll_transformation_preview_status()

        teio_button = self.panel.transformation_preview_buttons[
            "Tokai Teio"
        ]
        self.assertEqual(teio_button.text(), "解除帝寶變身")
        self.assertIn(
            "帝寶目前為自主變身形態",
            self.panel.transformation_preview_status.text(),
        )

        teio_button.click()
        self.assertEqual(teio_button.text(), "帝寶解除變身中")

        teio_state.update(
            current_form="base",
            target_form="",
            active=False,
            manual_end_requested=False,
            auto_session=False,
            auto_world_mode="",
            source="",
        )
        self.panel._poll_transformation_preview_status()

        self.assertEqual(teio_button.text(), "手動變身帝寶")
        self.assertEqual(
            self.panel.transformation_preview_status.text(),
            "帝寶已解除變身，目前為普通形態。",
        )
        self.assertNotIn(
            "再次按下",
            self.panel.transformation_preview_status.text(),
        )

    def test_autonomous_runtime_change_is_detected_without_button_click(self):
        self.panel.world_mode_buttons[1].click()
        self.binding.transformation_states["Symboli Rudolf"].update(
            current_form="transformed",
            auto_session=True,
            auto_world_mode="sandbox",
        )

        self.panel._poll_transformation_preview_status()

        rudolf_button = self.panel.transformation_preview_buttons[
            "Symboli Rudolf"
        ]
        self.assertEqual(rudolf_button.text(), "解除魯道夫變身")
        self.assertIn(
            "魯道夫目前為自主變身形態",
            self.panel.transformation_preview_status.text(),
        )
        self.assertEqual(
            self.panel.transformation_preview_poll_timer.interval(),
            400,
        )

    def test_transformation_polling_stops_when_panel_is_hidden(self):
        self.panel.world_mode_buttons[1].click()
        self.assertTrue(
            self.panel.transformation_preview_poll_timer.isActive()
        )

        self.panel.hide()
        self.app.processEvents()

        self.assertFalse(
            self.panel.transformation_preview_poll_timer.isActive()
        )

        self.panel.show()
        self.app.processEvents()

        self.assertTrue(
            self.panel.transformation_preview_poll_timer.isActive()
        )

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
        self.assertEqual(snapshot.race_frequency, "normal")
        self.assertEqual(snapshot.mood_climate, "cheerful")

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
        binding.set_race_frequency("occasional")
        binding.set_mood_climate("balanced")
        binding.run_validation_checks()
        preview_result = binding.preview_rudolf_work()
        preview_active = binding.is_rudolf_work_preview_active()
        race_preview_result = binding.preview_rudolf_teio_race()
        race_preview_active = binding.is_race_preview_active()
        transformation_result = binding.toggle_transformation_preview(
            "Tokai Teio"
        )
        transformation_state = binding.get_transformation_preview_state(
            "Tokai Teio"
        )

        self.assertEqual(preview_result, "preview-result")
        self.assertTrue(preview_active)
        self.assertEqual(race_preview_result, "race-preview-result")
        self.assertTrue(race_preview_active)
        self.assertEqual(
            transformation_result,
            "transformation-result:Tokai Teio",
        )
        self.assertEqual(
            transformation_state["current_form"],
            "transformed",
        )
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
                ("race_frequency", "occasional"),
                ("mood_climate", "balanced"),
                ("validate",),
                ("preview_rudolf_work",),
                ("preview_active",),
                ("preview_race",),
                ("race_preview_active",),
                ("transformation", "Tokai Teio"),
                ("transformation_state", "Tokai Teio"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
