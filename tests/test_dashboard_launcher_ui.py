import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import QApplication, QLabel

from tanuki_core.asset_manager import AssetManager
from tanuki_core.dashboard_ui import Dashboard
from tanuki_core.dashboard_launcher_binding import (
    DashboardLauncherBinding,
    DashboardLauncherSnapshot,
)
from tanuki_core.dashboard_launcher_ui import (
    COLLAPSED_LAUNCHER_WIDTH,
    EXPANDED_LAUNCHER_WIDTH,
    DashboardLauncherPanel,
)


class FakeLauncherBinding:
    def __init__(self):
        self.calls = []
        self.value = DashboardLauncherSnapshot(
            world_mode_key="golden_legend",
            world_mode_label="黃金傳說",
            time_scale_label="4x",
            care_enabled=True,
            care_label="照護中",
        )

    def snapshot(self):
        return self.value

    def open_information_center(self):
        self.calls.append(("information_center",))

    def open_offer_tray(self):
        self.calls.append(("offer_tray",))

    def open_status_settings(self):
        self.calls.append(("status_settings",))

    def begin_shutdown(self):
        self.calls.append(("shutdown",))


class DashboardLauncherPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.binding = FakeLauncherBinding()
        self.panel = DashboardLauncherPanel(
            self.binding,
            resource_resolver=AssetManager.get_resource_path,
        )
        self.panel.resize(EXPANDED_LAUNCHER_WIDTH, 520)
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.app.processEvents()

    def test_expanded_launcher_uses_large_side_art_brand_icon(self):
        expanded_pixmap = self.panel.expanded_brand_label.pixmap()
        collapsed_pixmap = self.panel.collapsed_brand_label.pixmap()

        self.assertFalse(expanded_pixmap.isNull())
        self.assertFalse(collapsed_pixmap.isNull())
        self.assertGreaterEqual(expanded_pixmap.width(), 58)
        self.assertGreaterEqual(collapsed_pixmap.width(), 52)
        self.assertEqual(
            self.panel.expanded_brand_label.objectName(),
            "tanukiLauncherExpandedBrand",
        )
        title_left = self.panel.title_label.mapTo(
            self.panel,
            self.panel.title_label.rect().topLeft(),
        ).x()
        brand_right = self.panel.expanded_brand_label.mapTo(
            self.panel,
            self.panel.expanded_brand_label.rect().topRight(),
        ).x()
        self.assertGreaterEqual(title_left - brand_right, 12)
        self.assertTrue(self.panel.pin_button.text() == "")
        self.assertFalse(self.panel.pin_button.icon().isNull())

    def test_snapshot_populates_three_runtime_status_chips(self):
        self.assertEqual(
            self.panel.world_status_button.text(),
            "● 黃金傳說",
        )
        self.assertEqual(self.panel.time_status_button.text(), "● 4x")
        self.assertEqual(
            self.panel.care_status_button.text(),
            "● 照護中",
        )
        self.assertEqual(
            self.panel.care_status_button.property("statusState"),
            "enabled",
        )

    def test_primary_and_secondary_actions_delegate_to_binding(self):
        self.panel.information_center_button.click()
        self.panel.offer_tray_button.click()
        self.panel.settings_button.click()
        self.panel.shutdown_button.click()

        self.assertEqual(
            self.binding.calls,
            [
                ("information_center",),
                ("offer_tray",),
                ("status_settings",),
                ("shutdown",),
            ],
        )
        for indicator in (
            self.panel.world_status_button,
            self.panel.time_status_button,
            self.panel.care_status_button,
        ):
            self.assertIsInstance(indicator, QLabel)
            self.assertFalse(hasattr(indicator, "clicked"))

    def test_launcher_collapses_to_persistent_rail_and_expands_by_button(self):
        states = []
        self.panel.expanded_changed.connect(states.append)

        self.panel.collapse_button.click()

        self.assertFalse(self.panel.is_expanded)
        self.assertEqual(self.panel.width(), COLLAPSED_LAUNCHER_WIDTH)
        self.assertIs(
            self.panel.page_stack.currentWidget(),
            self.panel.collapsed_page,
        )
        self.assertLess(
            self.panel.expand_button.y(),
            self.panel.collapsed_information_button.y(),
        )

        self.panel.expand_button.click()

        self.assertTrue(self.panel.is_expanded)
        self.assertEqual(self.panel.width(), EXPANDED_LAUNCHER_WIDTH)
        self.assertEqual(states, [False, True])

    def test_pin_control_is_distinct_from_manual_collapse(self):
        states = []
        self.panel.pinned_changed.connect(states.append)

        self.panel.pin_button.click()

        self.assertTrue(self.panel.is_pinned)
        self.assertTrue(self.panel.is_expanded)
        self.assertEqual(states, [True])

    def test_collapsed_actions_remain_keyboard_and_tooltip_discoverable(self):
        self.panel.set_expanded(False)

        self.assertEqual(
            self.panel.collapsed_information_button.accessibleName(),
            "開啟資訊中心",
        )
        self.assertEqual(
            self.panel.collapsed_settings_button.toolTip(),
            "開啟狀態設定",
        )
        self.assertIn("黃金傳說", self.panel.collapsed_status_dots.toolTip())

    def test_dashboard_uses_launcher_as_the_only_visible_shell_surface(self):
        dashboard = Dashboard(
            QRect(0, 0, 1280, 720),
            {},
            AssetManager.get_resource_path,
        )
        try:
            dashboard.show()
            self.app.processEvents()

            self.assertTrue(dashboard.launcher_panel.isVisible())
            self.assertIs(
                dashboard.launcher_panel.binding,
                dashboard.launcher_binding,
            )
            self.assertEqual(dashboard.layout.count(), 1)
            self.assertIs(
                dashboard.layout.itemAt(0).widget(),
                dashboard.launcher_panel,
            )
            self.assertTrue(dashboard.title_label.isHidden())

            dashboard.time_scale_idx = 2
            dashboard.care_feature_enabled = False
            dashboard.update_time_scale_buttons()
            dashboard.update_care_button_text()

            self.assertEqual(
                dashboard.launcher_panel.time_status_button.text(),
                "● 4x",
            )
            self.assertEqual(
                dashboard.launcher_panel.care_status_button.text(),
                "● 照護關閉",
            )
        finally:
            dashboard.update_timer.stop()
            dashboard.close()
            dashboard.deleteLater()
            self.app.processEvents()

    def test_unpinned_launcher_hides_fully_but_pinned_launcher_keeps_rail(self):
        class FakeSensor:
            def __init__(self):
                self.visible = True

            def hide(self):
                self.visible = False

            def show(self):
                self.visible = True

            def raise_(self):
                pass

        dashboard = Dashboard(
            QRect(0, 0, 1280, 720),
            {},
            AssetManager.get_resource_path,
        )
        sensor = FakeSensor()
        dashboard.anim.setDuration(0)
        dashboard.set_sensor_zone(sensor)
        try:
            dashboard.slide_in([], sensor)
            self.app.processEvents()

            self.assertTrue(dashboard.is_expanded)
            self.assertFalse(sensor.visible)

            dashboard.slide_out()
            self.app.processEvents()

            self.assertFalse(dashboard.is_expanded)
            self.assertTrue(sensor.visible)
            self.assertEqual(dashboard.pos(), dashboard.hide_pos)

            dashboard.slide_in([], sensor)
            dashboard.launcher_panel.set_pinned(True)
            dashboard.slide_out()
            self.app.processEvents()

            self.assertFalse(dashboard.is_expanded)
            self.assertFalse(sensor.visible)
            self.assertFalse(dashboard.launcher_panel.is_expanded)
            self.assertEqual(
                dashboard.width(),
                COLLAPSED_LAUNCHER_WIDTH,
            )
            self.assertEqual(dashboard.pos(), dashboard.show_pos)
        finally:
            dashboard.update_timer.stop()
            dashboard.close()
            dashboard.deleteLater()
            self.app.processEvents()


class DashboardLauncherBindingTests(unittest.TestCase):
    def test_snapshot_and_actions_reuse_dashboard_entry_points(self):
        class Dashboard:
            WORLD_MODE_LABELS = {
                "golden_legend": "黃金傳說",
                "sandbox": "沙盒",
            }

            def __init__(self):
                self.world_mode = "sandbox"
                self.care_feature_enabled = False
                self.calls = []

            def get_time_scale(self):
                return 2.0

            def open_information_center(self, page_id=None):
                self.calls.append(("information_center", page_id))

            def open_offer_tray(self):
                self.calls.append(("offer_tray",))

            def begin_shutdown(self):
                self.calls.append(("shutdown",))

        dashboard = Dashboard()
        binding = DashboardLauncherBinding(dashboard)

        snapshot = binding.snapshot()
        binding.open_information_center()
        binding.open_offer_tray()
        binding.open_status_settings()
        binding.begin_shutdown()

        self.assertEqual(snapshot.world_mode_label, "沙盒")
        self.assertEqual(snapshot.time_scale_label, "2x")
        self.assertEqual(snapshot.care_label, "照護關閉")
        self.assertEqual(
            dashboard.calls,
            [
                ("information_center", None),
                ("offer_tray",),
                ("information_center", "status_settings"),
                ("shutdown",),
            ],
        )


if __name__ == "__main__":
    unittest.main()
