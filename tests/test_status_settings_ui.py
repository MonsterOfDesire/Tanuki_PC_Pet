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
from tanuki_core.status_settings_ui import (
    MOOD_CLIMATE_TOOLTIPS,
    StatusSettingsPanel,
)
from tanuki_core.ui_controls import ToggleSwitch
from tanuki_core.ui_localization import set_ui_locale


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
        self.chorus_preview_result = SimpleNamespace(
            started=True,
            reason="",
        )
        self.chorus_preview_active = False
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
        self.sleep_states = {
            name: {
                "available": True,
                "visible": True,
                "active": False,
                "phase": "",
                "form_allows_sleep": True,
                "world_mode": "sandbox",
            }
            for name in (
                "Symboli Rudolf",
                "Tokai Teio",
                "Sirius Symboli",
                "Tsurumaru Tsuyoshi",
                "Air Groove",
            )
        }
        self.sleep_result = SimpleNamespace(
            started=True,
            phase_changed=False,
            reason="",
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

    def set_chorus_frequency(self, value):
        self.calls.append(("chorus_frequency", value))
        self.state = replace(self.state, chorus_frequency=value)

    def set_autonomous_sleep_enabled(self, enabled):
        self.calls.append(("autonomous_sleep", enabled))
        self.state = replace(
            self.state,
            autonomous_sleep_enabled=bool(enabled),
        )

    def set_autonomous_transformation_enabled(self, enabled):
        self.calls.append(("autonomous_transformation", enabled))
        self.state = replace(
            self.state,
            autonomous_transformation_enabled=bool(enabled),
        )

    def set_mood_climate(self, value):
        self.calls.append(("mood_climate", value))
        self.state = replace(self.state, mood_climate=value)

    def set_memory_album_mode(self, value):
        self.calls.append(("memory_album_mode", value))
        self.state = replace(self.state, memory_album_mode=value)

    def set_memory_album_capacity(self, value):
        self.calls.append(("memory_album_capacity", value))
        self.state = replace(self.state, memory_album_capacity=value)

    def set_ui_locale(self, value):
        self.calls.append(("ui_locale", value))
        self.state = replace(self.state, ui_locale=value)

    def set_ui_text_size(self, value):
        from tanuki_core.ui_typography import set_ui_text_size
        self.calls.append(("ui_text_size", value))
        self.state = replace(self.state, ui_text_size=value)
        set_ui_text_size(value)

    def check_for_updates(self):
        self.calls.append(("check_updates",))
        self.state = replace(self.state, update_status="checking")
        return True

    def open_update_page(self):
        self.calls.append(("open_update_page",))
        return True

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

    def preview_chorus(self):
        self.calls.append(("preview_chorus",))
        self.chorus_preview_active = bool(
            self.chorus_preview_result.started
        )
        return self.chorus_preview_result

    def is_chorus_preview_active(self):
        self.calls.append(("chorus_preview_active",))
        return self.chorus_preview_active

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

    def toggle_sleep_control(self, pet_name):
        self.calls.append(("sleep_control", pet_name))
        state = self.sleep_states[pet_name]
        if state["active"]:
            state["phase"] = "waking"
            self.sleep_result.started = False
            self.sleep_result.phase_changed = True
        else:
            state["active"] = True
            state["phase"] = "settling"
            self.sleep_result.started = True
            self.sleep_result.phase_changed = False
        return self.sleep_result

    def get_sleep_control_state(self, pet_name):
        return dict(self.sleep_states[pet_name])


class FakeDashboardForBinding:
    def __init__(self):
        self.world_mode_options = ["golden_legend", "sandbox"]
        self.time_scale_options = [1, 2, 4, 8]
        self.display_scale_options = [1.0, 1.5, 2.0, 3.0]
        self.teio_dur_list = [2, 5, 10, 20, 30]
        self.tsuyoshi_dur_list = [2, 10, 20, 40, 60]
        self.race_frequency_options = ["disabled", "frequent", "normal", "occasional"]
        self.chorus_frequency_options = ["disabled", "frequent", "normal", "occasional"]
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
            chorus_frequency="normal",
            autonomous_sleep_enabled=True,
            autonomous_transformation_enabled=True,
            mood_climate="cheerful",
            memory_album_mode="events",
            memory_album_capacity=50,
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

    def set_chorus_frequency(self, value):
        self.calls.append(("chorus_frequency", value))

    def set_autonomous_sleep_enabled(self, value):
        self.calls.append(("autonomous_sleep", value))

    def set_autonomous_transformation_enabled(self, value):
        self.calls.append(("autonomous_transformation", value))

    def set_mood_climate(self, value):
        self.calls.append(("mood_climate", value))

    def set_memory_album_mode(self, value):
        self.calls.append(("memory_album_mode", value))
        return True

    def set_memory_album_capacity(self, value):
        self.calls.append(("memory_album_capacity", value))
        return True

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

    def preview_chorus(self):
        self.calls.append(("preview_chorus",))
        return "chorus-preview-result"

    def is_chorus_preview_active(self):
        self.calls.append(("chorus_preview_active",))
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

    def toggle_sleep_control(self, pet_name):
        self.calls.append(("sleep_control", pet_name))
        return f"sleep-result:{pet_name}"

    def get_sleep_control_state(self, pet_name):
        self.calls.append(("sleep_state", pet_name))
        return {"active": False, "phase": ""}


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
        set_ui_locale("zh_TW")
        self.app.processEvents()

    def test_panel_reflects_snapshot_selection(self):
        self.assertEqual(self.panel._active_tab_key, "mode")
        self.assertTrue(self.panel.settings_tab_buttons["mode"].isChecked())
        self.assertEqual(len(self.panel.settings_tab_buttons), 2)
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
        self.assertTrue(self.panel.autonomous_sleep_switch.isChecked())
        self.assertTrue(
            self.panel.autonomous_transformation_switch.isChecked()
        )
        self.assertEqual(len(self.panel.mood_climate_buttons), 3)
        self.assertEqual(self.panel.findChildren(QCheckBox), [])
        self.assertTrue(self.panel.display_scale_buttons[1].isChecked())
        self.assertTrue(self.panel.teio_duration_buttons[2].isChecked())
        self.assertTrue(self.panel.tsuyoshi_duration_buttons[3].isChecked())
        self.assertTrue(self.panel.memory_album_mode_buttons[0].isChecked())
        self.assertTrue(self.panel.memory_album_capacity_buttons[0].isChecked())

    def test_option_rows_use_shared_segmented_control_styling(self):
        self.assertEqual(
            self.panel.world_mode_control.property("tanukiRole"),
            "settingsSegmentedControl",
        )
        self.assertEqual(self.panel.world_mode_row.spacing(), 0)
        self.assertEqual(
            [
                button.property("segmentPosition")
                for button in self.panel.world_mode_buttons
            ],
            ["first", "last"],
        )
        self.assertEqual(
            [
                button.property("segmentPosition")
                for button in self.panel.race_frequency_buttons
            ],
            ["first", "middle", "middle", "last"],
        )

    def test_language_selector_updates_resource_backed_controls(self):
        self.panel.ui_locale_buttons[3].click()
        self.app.processEvents()

        self.assertEqual(self.binding.state.ui_locale, "en_US")
        self.assertEqual(
            self.panel.locale_update_group.title(),
            "Language and updates",
        )
        self.assertEqual(self.panel.update_check_button.text(), "Check now")

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
            "Symboli Rudolf is in severe mood",
            self.panel.rudolf_work_preview_status.text(),
        )

    def test_simplified_chinese_selector_updates_resource_backed_controls(self):
        self.panel.ui_locale_buttons[1].click()
        self.app.processEvents()

        self.assertEqual(self.binding.state.ui_locale, "zh_CN")
        self.assertEqual(self.panel.locale_update_group.title(), "语言与更新")
        self.assertEqual(self.panel.update_check_button.text(), "立即检查更新")

    def test_update_controls_delegate_without_blocking_panel(self):
        self.panel.update_check_button.click()

        self.assertIn(("check_updates",), self.binding.calls)
        self.assertFalse(self.panel.update_check_button.isEnabled())

    def test_available_release_respects_platform_update_method(self):
        self.binding.state = replace(
            self.binding.state,
            update_status="available",
            update_page_url="https://example.test/release",
            update_updater_url="",
            update_package_ready=False,
            update_method="standalone_updater",
        )
        self.panel.refresh_from_binding()
        self.assertFalse(self.panel.update_open_button.isVisible())

        self.binding.state = replace(
            self.binding.state,
            update_method="manual_release",
        )
        self.panel.refresh_from_binding()
        self.assertTrue(self.panel.update_open_button.isVisible())
        self.assertEqual(self.panel.update_open_button.text(), "查看新版")
        self.assertIn("手動更新", self.panel.update_status_label.text())

        self.binding.state = replace(
            self.binding.state,
            update_updater_url="https://example.test/TanukiUpdater.exe",
            update_package_ready=True,
            update_method="standalone_updater",
        )
        self.panel.refresh_from_binding()
        self.assertTrue(self.panel.update_open_button.isVisible())
        self.panel.update_open_button.click()
        self.assertIn(("open_update_page",), self.binding.calls)

    def test_mood_climate_tooltips_describe_dynamics_not_targets(self):
        tooltips = [
            button.toolTip()
            for button in self.panel.mood_climate_buttons
        ]

        self.assertEqual(
            tooltips,
            [
                MOOD_CLIMATE_TOOLTIPS["cheerful"],
                MOOD_CLIMATE_TOOLTIPS["balanced"],
                MOOD_CLIMATE_TOOLTIPS["expressive"],
            ],
        )
        self.assertTrue(all("目標" not in text for text in tooltips))
        self.assertIn("50%", tooltips[0])
        self.assertIn("60%", tooltips[1])
        self.assertIn("90%", tooltips[2])

    def test_rudolf_imitation_cooldown_uses_localized_character_names(self):
        visible_labels = {
            label.text()
            for label in self.panel.findChildren(QLabel)
        }

        self.assertIn("帝寶", visible_labels)
        self.assertIn("鶴寶", visible_labels)

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
                    + compact_panel.chorus_frequency_buttons
                    + compact_panel.mood_climate_buttons
                    + compact_panel.memory_album_mode_buttons
                    + compact_panel.memory_album_capacity_buttons
                )
            )
        )
        mode_groups = (
            (compact_panel.runtime_group, (compact_panel.world_mode_buttons,)),
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
                    compact_panel.chorus_frequency_buttons,
                    compact_panel.mood_climate_buttons,
                ),
            ),
            (
                compact_panel.memory_group,
                (
                    compact_panel.memory_album_mode_buttons,
                    compact_panel.memory_album_capacity_buttons,
                ),
            ),
        )
        for group, button_rows in mode_groups:
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

    def test_wide_mode_tab_uses_balanced_two_column_cards(self):
        host = QWidget()
        host.setFixedSize(988, 383)
        wide_panel = StatusSettingsPanel(self.binding, parent=host)
        wide_panel.setGeometry(host.rect())
        host.show()
        self.app.processEvents()

        self.assertFalse(wide_panel._single_column_layout)
        expected_positions = {
            wide_panel.basic_card: (0, 0, 1, 1),
            wide_panel.rhythm_group: (0, 1, 1, 1),
            wide_panel.social_group: (1, 0, 1, 1),
            wide_panel.memory_card: (1, 1, 1, 1),
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
        self.assertTrue(wide_panel.social_group.isVisible())
        self.assertFalse(wide_panel.developer_group.isVisible())
        self.assertEqual(
            wide_panel.settings_scroll.horizontalScrollBar().maximum(),
            0,
        )
        host.close()
        wide_panel.deleteLater()
        host.deleteLater()

    def test_long_text_locales_use_single_column_before_text_can_clip(self):
        for locale in ("ja_JP", "en_US"):
            with self.subTest(locale=locale):
                binding = FakeStatusSettingsBinding()
                binding.state = replace(binding.state, ui_locale=locale)
                host = QWidget()
                host.setFixedSize(988, 383)
                panel = StatusSettingsPanel(binding, parent=host)
                panel.setGeometry(host.rect())
                host.show()
                self.app.processEvents()

                self.assertTrue(panel._single_column_layout)
                panel._select_tab("developer")
                self.app.processEvents()
                self.assertEqual(
                    panel.settings_scroll.horizontalScrollBar().maximum(),
                    0,
                )
                for button in (
                    tuple(panel.transformation_preview_buttons.values())
                    + tuple(panel.sleep_control_buttons.values())
                ):
                    top_left = button.mapTo(
                        panel.developer_group,
                        QPoint(0, 0),
                    )
                    self.assertGreaterEqual(top_left.x(), 0)
                    self.assertLessEqual(
                        top_left.x() + button.width(),
                        panel.developer_group.width() + 1,
                    )

                host.close()
                panel.deleteLater()
                host.deleteLater()

    def test_tab_navigation_separates_mode_and_developer_tools(self):
        self.panel._select_tab("developer")
        self.app.processEvents()

        self.assertEqual(
            self.panel._active_tab_key,
            "developer",
        )
        self.assertTrue(
            self.panel.settings_tab_buttons["developer"].isChecked()
        )
        self.assertTrue(self.panel.developer_group.isVisible())
        self.assertFalse(self.panel.runtime_group.isVisible())
        self.assertFalse(self.panel.memory_group.isVisible())

    def test_compact_layout_keeps_two_named_tabs_visible(self):
        host = QWidget()
        host.setFixedSize(600, 260)
        panel = StatusSettingsPanel(self.binding, parent=host)
        panel.setGeometry(host.rect())
        host.show()
        self.app.processEvents()

        self.assertEqual(panel.settings_tab_buttons["mode"].text(), "模式設定")
        self.assertEqual(
            panel.settings_tab_buttons["developer"].toolTip(),
            "開發工具",
        )

        host.close()
        panel.deleteLater()
        host.deleteLater()

    def test_simplified_chinese_keeps_regular_two_column_layout(self):
        binding = FakeStatusSettingsBinding()
        binding.state = replace(binding.state, ui_locale="zh_CN")
        host = QWidget()
        host.setFixedSize(988, 383)
        panel = StatusSettingsPanel(binding, parent=host)
        panel.setGeometry(host.rect())
        host.show()
        self.app.processEvents()

        self.assertFalse(panel._single_column_layout)
        self.assertEqual(
            panel.settings_scroll.horizontalScrollBar().maximum(),
            0,
        )

        host.close()
        panel.deleteLater()
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
        self.panel.autonomous_sleep_switch.click()
        self.panel.autonomous_transformation_switch.click()
        self.panel.debug_switch.click()
        self.panel.social_status_switch.click()
        self.panel.race_frequency_buttons[3].click()
        self.panel.chorus_frequency_buttons[1].click()
        self.panel.mood_climate_buttons[2].click()
        self.panel.memory_album_mode_buttons[2].click()
        self.panel.memory_album_capacity_buttons[1].click()

        self.assertEqual(
            self.binding.calls,
            [
                ("time", 3),
                ("display", 2),
                ("teio", 4),
                ("tsuyoshi", 1),
                ("world_mode", "sandbox"),
                ("care", False),
                ("autonomous_sleep", False),
                ("autonomous_transformation", False),
                ("debug", True),
                ("social_status", True),
                ("race_frequency", "frequent"),
                ("chorus_frequency", "occasional"),
                ("mood_climate", "expressive"),
                ("memory_album_mode", "random"),
                ("memory_album_capacity", 50),
            ],
        )

    def test_frequency_display_order_and_value_callbacks_are_stable_across_locales(self):
        order = ("disabled", "occasional", "normal", "frequent")
        legacy_order = ("disabled", "frequent", "normal", "occasional")
        for locale in ("zh_TW", "zh_CN", "ja_JP", "en_US"):
            with self.subTest(locale=locale):
                self.binding.state = replace(
                    self.binding.state, ui_locale=locale,
                    race_frequency="frequent", chorus_frequency="occasional",
                    race_frequency_options=legacy_order,
                    chorus_frequency_options=legacy_order,
                )
                self.panel.refresh_from_binding()
                self.assertEqual(self.binding.state.race_frequency_options, order)
                self.assertEqual(self.binding.state.chorus_frequency_options, order)
                self.assertTrue(self.panel.race_frequency_buttons[3].isChecked())
                self.assertTrue(self.panel.chorus_frequency_buttons[1].isChecked())
                if locale == "zh_TW":
                    self.assertEqual([button.text() for button in self.panel.race_frequency_buttons],
                                     ["不啟用", "偶爾", "普通", "經常"])
                for prefix in ("race", "chorus"):
                    for index, value in enumerate(order):
                        getattr(self.panel, f"{prefix}_frequency_buttons")[index].click()
                        self.assertEqual(self.binding.calls[-1], (f"{prefix}_frequency", value))
                        self.assertEqual(getattr(self.binding.state, f"{prefix}_frequency"), value)
                self.assertEqual(len(self.panel.mood_climate_buttons), 3)

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

    def test_chorus_preview_is_sandbox_only_and_resets_after_completion(self):
        self.assertFalse(self.panel.chorus_preview_button.isEnabled())

        self.panel.world_mode_buttons[1].click()
        self.panel.chorus_preview_button.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("world_mode", "sandbox"),
                ("preview_chorus",),
            ],
        )
        self.assertIn("合奏預覽已開始", self.panel.chorus_preview_status.text())
        self.assertTrue(self.panel.chorus_preview_poll_timer.isActive())

        self.binding.chorus_preview_active = False
        self.panel._poll_chorus_preview_status()

        self.assertIn("不寫事件", self.panel.chorus_preview_status.text())
        self.assertFalse(self.panel.chorus_preview_poll_timer.isActive())

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

    def test_sleep_control_is_sandbox_only_and_tracks_runtime_phase(self):
        teio_button = self.panel.sleep_control_buttons["Tokai Teio"]
        self.assertFalse(teio_button.isEnabled())

        self.panel.world_mode_buttons[1].click()
        teio_button.click()

        self.assertIn(
            ("sleep_control", "Tokai Teio"),
            self.binding.calls,
        )
        self.assertEqual(teio_button.text(), "喚醒帝寶")
        self.assertIn("進入睡眠", self.panel.sleep_control_status.text())

        teio_button.click()

        self.assertEqual(teio_button.text(), "帝寶喚醒中")
        self.assertFalse(teio_button.isEnabled())
        self.assertIn("喚醒過場", self.panel.sleep_control_status.text())

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
        self.assertEqual(rudolf_button.text(), "解除魯道夫象徵變身")
        self.assertIn(
            "魯道夫象徵目前為自主變身形態",
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
        self.assertEqual(snapshot.chorus_frequency, "normal")
        self.assertTrue(snapshot.autonomous_sleep_enabled)
        self.assertTrue(snapshot.autonomous_transformation_enabled)
        self.assertEqual(snapshot.mood_climate, "cheerful")
        self.assertEqual(snapshot.memory_album_mode, "events")
        self.assertEqual(snapshot.memory_album_capacity, 50)

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
        binding.set_chorus_frequency("frequent")
        binding.set_autonomous_sleep_enabled(False)
        binding.set_autonomous_transformation_enabled(False)
        binding.set_mood_climate("balanced")
        binding.set_memory_album_mode("random")
        binding.set_memory_album_capacity(100)
        binding.run_validation_checks()
        preview_result = binding.preview_rudolf_work()
        preview_active = binding.is_rudolf_work_preview_active()
        race_preview_result = binding.preview_rudolf_teio_race()
        race_preview_active = binding.is_race_preview_active()
        chorus_preview_result = binding.preview_chorus()
        chorus_preview_active = binding.is_chorus_preview_active()
        transformation_result = binding.toggle_transformation_preview(
            "Tokai Teio"
        )
        transformation_state = binding.get_transformation_preview_state(
            "Tokai Teio"
        )
        sleep_result = binding.toggle_sleep_control("Tokai Teio")
        sleep_state = binding.get_sleep_control_state("Tokai Teio")

        self.assertEqual(preview_result, "preview-result")
        self.assertTrue(preview_active)
        self.assertEqual(race_preview_result, "race-preview-result")
        self.assertTrue(race_preview_active)
        self.assertEqual(chorus_preview_result, "chorus-preview-result")
        self.assertTrue(chorus_preview_active)
        self.assertEqual(
            transformation_result,
            "transformation-result:Tokai Teio",
        )
        self.assertEqual(
            transformation_state["current_form"],
            "transformed",
        )
        self.assertEqual(sleep_result, "sleep-result:Tokai Teio")
        self.assertFalse(sleep_state["active"])
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
                ("chorus_frequency", "frequent"),
                ("autonomous_sleep", False),
                ("autonomous_transformation", False),
                ("mood_climate", "balanced"),
                ("memory_album_mode", "random"),
                ("memory_album_capacity", 100),
                ("validate",),
                ("preview_rudolf_work",),
                ("preview_active",),
                ("preview_race",),
                ("race_preview_active",),
                ("preview_chorus",),
                ("chorus_preview_active",),
                ("transformation", "Tokai Teio"),
                ("transformation_state", "Tokai Teio"),
                ("sleep_control", "Tokai Teio"),
                ("sleep_state", "Tokai Teio"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
