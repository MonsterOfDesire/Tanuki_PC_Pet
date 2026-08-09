import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from tanuki_core.asset_manager import AssetManager
from tanuki_core.information_center_spec import (
    INFORMATION_CENTER_PAGE_SPECS,
    PAGE_EVENT_LOG,
    PAGE_FAMILY_STATUS,
    PAGE_RELATION_SUMMON,
    PAGE_STATUS_SETTINGS,
    PAGE_ACHIEVEMENTS,
)
from tanuki_core.information_center_ui import InformationCenterWindow
from tanuki_core.information_center_size_rules import SIZE_16_10, SIZE_COMPACT
from tanuki_core.information_center_state import (
    build_information_center_config_state,
)
from tanuki_core.status_settings_binding import StatusSettingsSnapshot
from tanuki_core.dashboard_presenter import (
    HouseholdRecentEventPresentation,
    HouseholdSummaryPresentation,
    RelationshipRowPresentation,
    SocialLogEntryPresentation,
    SocialLogPresentation,
)
from tanuki_core.relation_summon_binding import (
    RelationSummonPresentation,
    SummonMemberPresentation,
)
from tanuki_core.achievement_presenter import (
    AchievementCabinetSnapshot,
    AchievementCardSnapshot,
    AchievementModeSnapshot,
    AchievementTierSnapshot,
)


class FakeStatusSettingsBinding:
    def snapshot(self):
        return StatusSettingsSnapshot(
            world_mode="golden_legend",
            world_mode_options=("golden_legend", "sandbox"),
            care_feature_enabled=True,
            debug_enabled=False,
            social_status_enabled=False,
            time_scale_options=(1.0, 2.0, 4.0, 8.0),
            time_scale_index=0,
            display_scale_options=(1.0, 1.5, 2.0, 3.0),
            display_scale_index=0,
            teio_duration_options=(2, 5, 10, 20, 30),
            teio_duration_index=0,
            tsuyoshi_duration_options=(2, 10, 20, 40, 60),
            tsuyoshi_duration_index=0,
        )

    def set_debug_enabled(self, enabled):
        pass

    def set_world_mode(self, world_mode):
        pass

    def set_care_feature_enabled(self, enabled):
        pass

    def set_social_status_enabled(self, enabled):
        pass

    def set_time_scale_index(self, index):
        pass

    def set_display_scale_index(self, index):
        pass

    def set_social_duration_index(self, character_key, index):
        pass

    def run_validation_checks(self):
        pass


class FakeFamilySummaryBinding:
    def presentation(self):
        return HouseholdSummaryPresentation(
            title="家庭摘要",
            overview_text="生活費: 800 元\n家庭壓力: 20%",
            log_text="#001 家庭事件",
            living_fund=800,
            household_pressure=20.0,
            recent_events=(
                HouseholdRecentEventPresentation(
                    sequence=1,
                    timestamp_text="#001",
                    channel="system",
                    channel_label="系統",
                    summary="家庭事件",
                    delta_text="",
                ),
            ),
            recent_event_count=1,
        )


class FakeEventLogBinding:
    def presentation(self, filter_mode="all", participant_name=""):
        return SocialLogPresentation(
            title="事件日誌 - 全部",
            filter_mode=filter_mode,
            participant_name=participant_name,
            participant_names=("Tokai Teio",),
            log_text="#001 測試事件",
            entries=(
                SocialLogEntryPresentation(
                    sequence=1,
                    timestamp_text="時序 #001",
                    channel="system",
                    channel_label="系統",
                    category="system",
                    event_type="test",
                    importance="normal",
                    summary="測試事件",
                    actor_name="",
                    target_name="",
                    participant_text="家庭／系統",
                    effects=(),
                    tags=("test",),
                ),
            ),
        )


class FakeRelationSummonBinding:
    def presentation(self, selected_character_name=""):
        selected_character_name = selected_character_name or "Air Groove"
        return RelationSummonPresentation(
            title="角色關係＋召喚",
            selected_character_name=selected_character_name,
            members=(SummonMemberPresentation("Air Groove", True),),
            relationship_rows=(
                RelationshipRowPresentation(
                    actor_name="Air Groove",
                    target_name="Tokai Teio",
                    affinity=12.0,
                    familiarity=20.0,
                    trust=10.0,
                    attachment=5.0,
                    tension=1.0,
                    event_count=2,
                ),
            ),
        )

    def set_summoned(self, character_name, summoned):
        return True


class FakeAchievementBinding:
    def snapshot(self):
        card = AchievementCardSnapshot(
            slot_key="race.first_natural_finish",
            tier="G3",
            unlocked=False,
            image_relative_path="UI/trophies/race/3008.png",
            accessible_name="未取得的 G3 獎盃",
        )
        return AchievementCabinetSnapshot(
            modes=(
                AchievementModeSnapshot(
                    world_mode="sandbox",
                    mode_label="沙盒",
                    tiers=(
                        AchievementTierSnapshot("G1", (), 0, 0),
                        AchievementTierSnapshot("G2", (), 0, 0),
                        AchievementTierSnapshot("G3", (card,), 0, 1),
                    ),
                    unlocked_count=0,
                    total_count=1,
                ),
            )
        )

    def runtime_world_mode(self):
        return "sandbox"


class InformationCenterWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = InformationCenterWindow(AssetManager.get_resource_path)
        self.window.resize(1120, 720)
        self.app.processEvents()

    def tearDown(self):
        self.window.dock_all_pages()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_window_builds_five_navigation_pages(self):
        self.assertEqual(len(self.window.navigation_buttons), 5)
        self.assertEqual(len(self.window.pages), 5)
        self.assertEqual(
            tuple(self.window.navigation_buttons),
            tuple(page.page_id for page in INFORMATION_CENTER_PAGE_SPECS),
        )
        self.assertEqual(
            {
                page_id: button.property("pageAccent")
                for page_id, button in self.window.navigation_buttons.items()
            },
            {
                page_spec.page_id: page_spec.page_id
                for page_spec in INFORMATION_CENTER_PAGE_SPECS
            },
        )

    def test_navigation_bar_replaces_native_title_bar(self):
        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        )
        self.assertIs(
            self.window.window_chrome.controls.parent(),
            self.window.navigation_frame,
        )
        self.assertEqual(
            self.window.window_chrome.controls.close_button.toolTip(),
            "關閉",
        )

    def test_window_exposes_recommended_size_menu(self):
        self.assertEqual(len(self.window.size_actions), 4)
        self.assertTrue(self.window.size_button.menu().actions())

    def test_size_preset_resizes_without_disabling_manual_resize(self):
        emitted = []
        state_changes = []
        self.window.size_preset_applied.connect(emitted.append)
        self.window.state_changed.connect(lambda: state_changes.append(True))

        self.window.apply_size_preset(SIZE_16_10)
        preset_size = self.window.size()
        self.window.resize(preset_size.width() + 20, preset_size.height() + 20)
        self.app.processEvents()

        self.assertEqual(self.window.last_size_preset_id, SIZE_16_10)
        self.assertEqual(emitted, [SIZE_16_10])
        self.assertEqual(state_changes, [True])
        self.assertNotEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertEqual(self.window.width(), preset_size.width() + 20)

    def test_visible_manual_resize_emits_state_change(self):
        state_changes = []
        self.window.show()
        self.app.processEvents()
        self.window.state_changed.connect(lambda: state_changes.append(True))

        self.window.resize(
            self.window.width() + 10,
            self.window.height() + 10,
        )
        self.app.processEvents()

        self.assertEqual(state_changes, [True])

    def test_compact_preset_crops_scenery_and_compacts_navigation(self):
        self.window.show()
        self.app.processEvents()
        self.window.apply_size_preset(SIZE_COMPACT)
        self.app.processEvents()

        self.assertEqual(self.window.size(), self.window.minimumSize())
        self.assertFalse(self.window.navigation_title.isVisible())
        self.assertEqual(self.window.size_button.text(), "")
        self.assertEqual(self.window.detach_button.text(), "")
        self.assertFalse(self.window.detach_button.icon().isNull())
        self.assertTrue(
            all(
                button.text() == "" and not button.icon().isNull()
                for button in self.window.navigation_buttons.values()
            )
        )

        for page_id in self.window.pages:
            with self.subTest(page_id=page_id):
                self.window.select_page(page_id)
                self.app.processEvents()
                page = self.window.pages[page_id]
                scene = page.scene_geometry()
                content = page.content_geometry()
                content_left = scene.x() + content.x()
                content_top = scene.y() + content.y()

                self.assertTrue(scene.x() < 0 or scene.y() < 0)
                self.assertGreaterEqual(content_left, -1)
                self.assertGreaterEqual(content_top, -1)
                self.assertLessEqual(
                    content_left + content.width(),
                    page.width() + 1,
                )
                self.assertLessEqual(
                    content_top + content.height(),
                    page.height() + 1,
                )

    def test_family_summary_is_selected_by_default(self):
        self.assertEqual(self.window.current_page_id, PAGE_FAMILY_STATUS)
        self.assertTrue(self.window.navigation_buttons[PAGE_FAMILY_STATUS].isChecked())

    def test_achievement_page_is_embedded_and_cannot_detach(self):
        self.window.select_page(PAGE_ACHIEVEMENTS)

        self.assertIsNotNone(self.window.achievement_cabinet_panel)
        self.assertFalse(self.window.detach_button.isEnabled())
        self.assertIsNone(self.window.detach_page(PAGE_ACHIEVEMENTS))
        self.assertFalse(self.window.is_page_detached(PAGE_ACHIEVEMENTS))

    def test_achievement_page_accepts_runtime_binding(self):
        binding = FakeAchievementBinding()

        self.window.set_achievement_binding(binding)
        self.window.select_page(PAGE_ACHIEVEMENTS)

        panel = self.window.achievement_cabinet_panel
        self.assertIs(panel.binding, binding)
        self.assertEqual(panel.current_world_mode, "sandbox")
        self.assertEqual(panel.progress_label.text(), "已取得 0 / 1")
        self.assertEqual(len(panel.card_widgets), 1)

    def test_status_settings_page_accepts_runtime_binding(self):
        binding = FakeStatusSettingsBinding()

        self.window.set_status_settings_binding(binding)
        self.window.select_page(PAGE_STATUS_SETTINGS)

        self.assertIs(self.window.status_settings_panel.binding, binding)
        self.assertTrue(self.window.status_settings_panel.settings_grid.isEnabled())
        self.assertEqual(len(self.window.status_settings_panel.time_scale_buttons), 4)

    def test_family_summary_page_accepts_presenter_binding(self):
        binding = FakeFamilySummaryBinding()

        self.window.set_family_summary_binding(binding)
        self.window.select_page(PAGE_FAMILY_STATUS)

        self.assertIs(self.window.family_summary_panel.binding, binding)
        self.assertEqual(self.window.family_summary_panel.fund_value_label.text(), "800 元")
        self.assertIn(
            "家庭事件",
            self.window.family_summary_panel.recent_event_table.item(0, 2).text(),
        )

    def test_event_log_page_accepts_presenter_binding(self):
        binding = FakeEventLogBinding()

        self.window.set_event_log_binding(binding)
        self.window.select_page(PAGE_EVENT_LOG)

        self.assertIs(self.window.event_log_panel.binding, binding)
        self.assertTrue(self.window.event_log_panel.filter_buttons["all"].isChecked())
        self.assertEqual(self.window.event_log_panel.event_table.rowCount(), 1)
        self.assertIn(
            "測試事件",
            self.window.event_log_panel.detail_summary_label.text(),
        )

    def test_relation_summon_page_accepts_runtime_binding(self):
        binding = FakeRelationSummonBinding()

        self.window.set_relation_summon_binding(binding)
        self.window.select_page(PAGE_RELATION_SUMMON)

        self.assertIs(self.window.relation_summon_panel.binding, binding)
        self.assertTrue(
            self.window.relation_summon_panel.avatar_buttons["Air Groove"].isChecked()
        )
        self.assertEqual(
            self.window.relation_summon_panel.relationship_list.item(0).data(
                Qt.ItemDataRole.UserRole
            ),
            ("Air Groove", "Tokai Teio"),
        )

    def test_switching_page_changes_skin_without_resizing_window(self):
        original_size = self.window.size()

        self.window.select_page(PAGE_EVENT_LOG)

        self.assertEqual(self.window.current_page_id, PAGE_EVENT_LOG)
        self.assertEqual(
            self.window.page_stack.currentWidget(),
            self.window.page_hosts[PAGE_EVENT_LOG],
        )
        self.assertEqual(self.window.size(), original_size)
        self.assertTrue(self.window.navigation_buttons[PAGE_EVENT_LOG].isChecked())

    def test_detach_reuses_page_widget_and_preserves_stack_indexes(self):
        self.window.show()
        self.app.processEvents()
        page = self.window.pages[PAGE_FAMILY_STATUS]
        original_indexes = dict(self.window.page_indexes)

        detached_window = self.window.detach_page(PAGE_FAMILY_STATUS)
        self.app.processEvents()

        self.assertIs(detached_window.page, page)
        self.assertIs(page.parentWidget(), detached_window.page_host)
        self.assertTrue(detached_window.isVisible())
        self.assertTrue(page._animation_active)
        self.assertEqual(
            detached_window.window_chrome.controls.close_button.toolTip(),
            "關閉並歸回資訊中心",
        )
        self.assertTrue(self.window.is_page_detached(PAGE_FAMILY_STATUS))
        self.assertEqual(self.window.page_stack.count(), 5)
        self.assertEqual(self.window.page_indexes, original_indexes)
        self.assertEqual(
            self.window.current_page_id,
            PAGE_ACHIEVEMENTS,
        )
        self.assertTrue(
            self.window.navigation_buttons[PAGE_FAMILY_STATUS].property(
                "detached"
            )
        )

    def test_detached_navigation_button_recalls_window_without_switching_stack(self):
        self.window.show()
        self.app.processEvents()
        detached_window = self.window.detach_page(PAGE_FAMILY_STATUS)
        self.app.processEvents()
        current_page_id = self.window.current_page_id
        detached_window.hide()
        self.app.processEvents()

        self.window.navigation_buttons[PAGE_FAMILY_STATUS].click()
        self.app.processEvents()

        self.assertTrue(detached_window.isVisible())
        self.assertEqual(self.window.current_page_id, current_page_id)
        self.assertTrue(
            self.window.navigation_buttons[current_page_id].isChecked()
        )

    def test_closing_detached_window_docks_and_activates_page(self):
        self.window.show()
        self.app.processEvents()
        page = self.window.pages[PAGE_FAMILY_STATUS]
        detached_window = self.window.detach_page(PAGE_FAMILY_STATUS)
        self.app.processEvents()

        detached_window.close()
        self.app.processEvents()

        self.assertFalse(
            self.window.is_page_detached(PAGE_FAMILY_STATUS)
        )
        self.assertIs(
            page.parentWidget(),
            self.window.page_hosts[PAGE_FAMILY_STATUS],
        )
        self.assertEqual(
            self.window.current_page_id,
            PAGE_FAMILY_STATUS,
        )
        self.assertTrue(page._animation_active)
        self.assertTrue(
            self.window.navigation_buttons[PAGE_FAMILY_STATUS].isChecked()
        )

    def test_multiple_pages_can_detach_and_dock_independently(self):
        self.window.show()
        self.app.processEvents()

        family_window = self.window.detach_page(PAGE_FAMILY_STATUS)
        settings_window = self.window.detach_page(PAGE_STATUS_SETTINGS)
        self.app.processEvents()

        self.assertEqual(
            set(self.window.detached_page_windows),
            {PAGE_FAMILY_STATUS, PAGE_STATUS_SETTINGS},
        )
        family_window.close()
        self.app.processEvents()

        self.assertFalse(
            self.window.is_page_detached(PAGE_FAMILY_STATUS)
        )
        self.assertTrue(
            self.window.is_page_detached(PAGE_STATUS_SETTINGS)
        )
        self.assertTrue(settings_window.isVisible())

    def test_all_detachable_pages_leave_achievement_page_docked(self):
        self.window.show()
        self.app.processEvents()
        for page_id in (
            PAGE_FAMILY_STATUS,
            PAGE_STATUS_SETTINGS,
            PAGE_RELATION_SUMMON,
            PAGE_EVENT_LOG,
        ):
            self.window.detach_page(page_id)
            self.app.processEvents()

        self.assertEqual(len(self.window.detached_page_windows), 4)
        self.assertFalse(self.window.detach_button.isEnabled())
        self.assertEqual(self.window.current_page_id, PAGE_ACHIEVEMENTS)
        self.window.navigation_buttons[PAGE_RELATION_SUMMON].click()
        self.app.processEvents()
        self.assertEqual(
            self.window.current_page_id,
            PAGE_ACHIEVEMENTS,
        )
        self.assertTrue(
            self.window.navigation_buttons[PAGE_ACHIEVEMENTS].isChecked()
        )
        event_window = self.window.detached_page_windows[PAGE_EVENT_LOG]

        event_window.close()
        self.app.processEvents()

        self.assertEqual(len(self.window.detached_page_windows), 3)
        self.assertEqual(self.window.current_page_id, PAGE_EVENT_LOG)
        self.assertTrue(self.window.detach_button.isEnabled())

    def test_detached_page_visibility_does_not_depend_on_main_window(self):
        self.window.show()
        self.app.processEvents()
        detached_window = self.window.detach_page(PAGE_EVENT_LOG)
        self.app.processEvents()
        self.window.hide()
        self.app.processEvents()

        self.assertTrue(detached_window.isVisible())
        self.assertTrue(self.window.is_page_visible(PAGE_EVENT_LOG))
        self.assertFalse(
            self.window.is_page_visible(self.window.current_page_id)
        )

    def test_relation_page_retains_foreground_layer(self):
        self.window.select_page(PAGE_RELATION_SUMMON)

        page = self.window.pages[PAGE_RELATION_SUMMON]
        margins = page.content_layout.contentsMargins()
        self.assertEqual((margins.left(), margins.right()), (8, 8))
        self.assertGreater(page.foreground_geometry().width(), 0)
        self.assertGreater(page.foreground_geometry().height(), 0)

    def test_only_visible_page_runs_animation(self):
        self.window.show()
        self.app.processEvents()
        self.window.select_page(PAGE_RELATION_SUMMON)
        self.app.processEvents()

        self.assertTrue(self.window.pages[PAGE_RELATION_SUMMON]._animation_active)
        self.assertFalse(self.window.pages[PAGE_STATUS_SETTINGS]._animation_active)

    def test_programmatic_move_does_not_lock_user_position(self):
        self.window.move_near_anchor(40, 50)
        self.app.processEvents()

        self.assertFalse(self.window.user_position_locked)

    def test_restore_config_state_restores_page_geometry_and_preset_silently(self):
        screen_geometry = self.window.screen().availableGeometry()
        minimum_size = self.window.minimumSize()
        width = min(
            screen_geometry.width(),
            minimum_size.width() + 40,
        )
        height = min(
            screen_geometry.height(),
            minimum_size.height() + 40,
        )
        emitted = []
        self.window.state_changed.connect(lambda: emitted.append(True))

        self.window.restore_config_state(
            build_information_center_config_state(
                x=screen_geometry.x(),
                y=screen_geometry.y(),
                width=width,
                height=height,
                page_id=PAGE_EVENT_LOG,
                size_preset_id=SIZE_16_10,
            )
        )
        self.app.processEvents()

        state = self.window.capture_config_state()
        self.assertEqual(state.x, screen_geometry.x())
        self.assertEqual(state.y, screen_geometry.y())
        self.assertEqual(state.width, width)
        self.assertEqual(state.height, height)
        self.assertEqual(state.page_id, PAGE_EVENT_LOG)
        self.assertEqual(state.size_preset_id, SIZE_16_10)
        self.assertTrue(self.window.user_position_locked)
        self.assertEqual(emitted, [])

    def test_open_without_page_keeps_restored_last_page(self):
        self.window.restore_config_state(
            build_information_center_config_state(
                page_id=PAGE_STATUS_SETTINGS,
            )
        )

        self.window.open_page()
        self.app.processEvents()

        self.assertEqual(
            self.window.current_page_id,
            PAGE_STATUS_SETTINGS,
        )


if __name__ == "__main__":
    unittest.main()
