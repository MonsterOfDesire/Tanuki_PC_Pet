import os
import unittest
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QRect, QEvent, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics, QHelpEvent
from PyQt6.QtWidgets import QApplication, QLabel, QToolTip, QWidget
from PyQt6.QtTest import QTest
from types import SimpleNamespace

from tanuki_core.config_rules import normalize_config_state
from tanuki_core.dashboard_state_mapper import (
    build_dashboard_config_state, dashboard_config_state_to_payload,
    apply_dashboard_config_to_settings,
    normalize_dashboard_config_state, DashboardOptionBounds,
)
from tanuki_core.settings_provider import RuntimeSettings
from tanuki_core.dashboard_controller import DashboardController
from tanuki_core.status_settings_ui import StatusSettingsPanel, MOOD_CLIMATE_TOOLTIPS
from tanuki_core.ui_theme import apply_ui_theme
from tanuki_core.ui_typography import (
    get_ui_text_size, set_ui_text_size, ui_font_pixels, UI_TEXT_SIZE_FACTORS,
)
from tanuki_core.ui_localization import set_ui_locale, translate_ui
from tests.test_status_settings_ui import FakeStatusSettingsBinding
from tests.test_dashboard_launcher_ui import FakeLauncherBinding
from tanuki_core.asset_manager import AssetManager
from tanuki_core.dashboard_launcher_ui import DashboardLauncherPanel
from tanuki_core.offer_tray_ui import OfferTrayWindow
from tanuki_core.information_center_ui import InformationCenterWindow


class UiTypographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        # The offscreen plugin may not enumerate Windows font fallbacks.
        for filename in ("msjh.ttc", "msjhbd.ttc"):
            path = Path("C:/Windows/Fonts") / filename
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))

    def tearDown(self):
        set_ui_text_size("medium")
        set_ui_locale("zh_TW")

    def test_requested_text_size_factors(self):
        self.assertEqual(UI_TEXT_SIZE_FACTORS, {"small": 0.8, "medium": 1.0, "large": 1.5})
        for value, pixels in (("small", 8), ("medium", 10), ("large", 15)):
            set_ui_text_size(value)
            self.assertEqual(ui_font_pixels(10), pixels)

    def test_first_launch_without_text_size_defaults_to_medium_at_one_hundred_percent(self):
        normalized, _ = normalize_config_state({})
        settings = RuntimeSettings()
        self.assertEqual(normalized["dashboard"]["ui_text_size"], "medium")
        self.assertEqual(settings.ui_text_size, "medium")
        set_ui_text_size(settings.ui_text_size)
        self.assertEqual(ui_font_pixels(20), 20)

    def test_text_size_survives_config_round_trip_and_old_config_defaults(self):
        state = build_dashboard_config_state(
            world_mode="sandbox", care_feature_enabled=True,
            teio_dur_idx=2, tsuyoshi_dur_idx=2, time_scale_idx=0,
            display_scale_idx=0, debug_enabled=False, ui_text_size="large",
        )
        raw = {"dashboard": dashboard_config_state_to_payload(state)}
        normalized, _ = normalize_config_state(raw)
        self.assertEqual(normalized["dashboard"]["ui_text_size"], "large")
        settings = RuntimeSettings()
        apply_dashboard_config_to_settings(settings, state)
        self.assertEqual(settings.ui_text_size, "large")
        restored = normalize_dashboard_config_state(
            normalized["dashboard"], state, DashboardOptionBounds(5, 5, 4, 4)
        )
        self.assertEqual(restored.ui_text_size, "large")
        for value in (None, "huge", 123):
            normalized, _ = normalize_config_state({"dashboard": {"ui_text_size": value}})
            self.assertEqual(normalized["dashboard"]["ui_text_size"], "medium")

    def test_live_theme_changes_and_new_windows_share_size_without_drift(self):
        host = QWidget()
        apply_ui_theme(host)
        label = QLabel("Readable text", host)
        label.setProperty("tanukiRole", "settingsLabel")
        host.show()
        self.app.processEvents()
        base = QFontMetrics(label.font()).height()
        set_ui_text_size("large")
        self.app.processEvents()
        self.assertGreater(QFontMetrics(label.font()).height(), base)
        later = QWidget()
        apply_ui_theme(later)
        self.assertEqual(later.styleSheet(), host.styleSheet())
        set_ui_text_size("small")
        set_ui_text_size("medium")
        self.app.processEvents()
        self.assertEqual(QFontMetrics(label.font()).height(), base)
        host.close()
        later.close()
        host.deleteLater()
        later.deleteLater()

    def test_controller_saves_text_size_through_existing_config_path(self):
        calls = []
        dashboard = SimpleNamespace(
            sync_settings_provider=lambda: calls.append("sync"),
            retranslate_ui=lambda: calls.append("refresh"),
            schedule_save=lambda: calls.append("save"),
        )
        DashboardController().set_ui_text_size(dashboard, "large")
        self.assertEqual(dashboard.ui_text_size, "large")
        self.assertEqual(calls, ["sync", "refresh", "save"])

    def test_launcher_and_tray_update_in_all_locales_without_resizing_icons(self):
        launcher = DashboardLauncherPanel(
            FakeLauncherBinding(),
            resource_resolver=AssetManager.get_resource_path,
        )
        tray = OfferTrayWindow()
        launcher.show()
        tray.show()
        self.app.processEvents()
        brand_size = launcher.expanded_brand_label.pixmap().size()
        try:
            for locale in ("zh_TW", "zh_CN", "ja_JP", "en_US"):
                set_ui_locale(locale)
                launcher.retranslate_ui()
                tray.retranslate_ui()
                heights = []
                for size in ("small", "medium", "large"):
                    set_ui_text_size(size)
                    self.app.processEvents()
                    for widget in (
                        launcher.title_label,
                        launcher.information_center_button,
                        launcher.offer_tray_button,
                    ):
                        if isinstance(widget, QLabel) and widget.wordWrap():
                            text_rect = widget.fontMetrics().boundingRect(
                                QRect(0, 0, widget.width(), 1000),
                                Qt.TextFlag.TextWordWrap,
                                widget.text(),
                            )
                            self.assertLessEqual(text_rect.height(), widget.height(), (locale, size))
                            continue
                        self.assertGreaterEqual(
                            widget.width(),
                            widget.fontMetrics().horizontalAdvance(widget.text()),
                            (locale, size, widget.text()),
                        )
                    for badge in tray.item_badges:
                        self.assertGreaterEqual(
                            badge.title_label.height(),
                            badge.title_label.fontMetrics().height(),
                            (locale, size, badge.title_label.text()),
                        )
                    heights.append(tray.item_badges[0].title_label.fontMetrics().height())
                    self.assertEqual(launcher.expanded_brand_label.pixmap().size(), brand_size)
                self.assertGreater(heights[2], heights[1])
                self.assertGreaterEqual(heights[1], heights[0])
        finally:
            launcher.close()
            tray.close()
            launcher.deleteLater()
            tray.deleteLater()

    def test_tooltip_event_displays_in_page_description_without_native_popup(self):
        panel = StatusSettingsPanel(FakeStatusSettingsBinding())
        panel.resize(1280, 800)
        panel.show()
        self.app.processEvents()
        button = panel.mood_climate_buttons[0]
        point = button.rect().center()
        event = QHelpEvent(QEvent.Type.ToolTip, point, button.mapToGlobal(point))
        QApplication.sendEvent(button, event)
        self.app.processEvents()
        self.assertTrue(panel.hover_help.label.isVisible())
        self.assertEqual(panel.hover_help.label.text(), button.toolTip())
        self.assertIs(panel.hover_help.label.window(), panel.window())
        self.assertEqual(panel.hover_help.label.focusPolicy(), Qt.FocusPolicy.NoFocus)
        self.assertTrue(panel.hover_help.label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        QToolTip.hideText()
        panel.close()
        panel.deleteLater()

    def test_real_hover_shows_climate_help_and_mouse_exit_hides_it(self):
        binding = FakeStatusSettingsBinding()
        binding.state = replace(binding.state, world_mode="sandbox")
        window = InformationCenterWindow(
            AssetManager.get_resource_path,
            status_settings_binding=binding,
        )
        window.resize(1280, 800)
        from tanuki_core.information_center_spec import PAGE_STATUS_SETTINGS
        window.select_page(PAGE_STATUS_SETTINGS)
        window.show()
        self.app.processEvents()
        panel = window.status_settings_panel
        try:
            button = panel.mood_climate_buttons[0]
            self.assertTrue(panel.transformation_preview_poll_timer.isActive())
            panel.transformation_preview_poll_timer.setInterval(100)
            QTest.mouseMove(window, QPoint(2, 2))
            QTest.mouseMove(window, button.mapTo(window, button.rect().center()))
            QTest.qWait(panel.hover_help.HOVER_DELAY_MS + 80)
            self.assertTrue(panel.hover_help.label.isVisible())
            self.assertEqual(panel.hover_help.label.text(), button.toolTip())
            self.assertTrue(panel.rect().contains(panel.hover_help.label.geometry()))
            QTest.qWait(700)  # Several runtime polls must not dismiss the help.
            self.assertTrue(panel.hover_help.label.isVisible())
            QTest.mouseMove(window, QPoint(2, 2))
            self.app.processEvents()
            self.assertFalse(panel.hover_help.label.isVisible())
        finally:
            window.close()
            window.deleteLater()

    def test_hover_help_does_not_activate_window_and_survives_option_rebuild(self):
        binding = FakeStatusSettingsBinding()
        panel = StatusSettingsPanel(binding)
        panel.resize(1280, 800)
        panel.show()
        other = QWidget()
        other.show()
        QApplication.setActiveWindow(other)
        self.app.processEvents()
        try:
            button = panel.mood_climate_buttons[1]
            QTest.mouseMove(panel, QPoint(2, 2))
            QTest.mouseMove(panel, button.mapTo(panel, button.rect().center()))
            QTest.qWait(panel.hover_help.HOVER_DELAY_MS + 80)
            self.assertTrue(panel.hover_help.label.isVisible())
            self.assertIs(self.app.activeWindow(), other)
            panel.refresh_from_binding(force_rebuild=True)
            QTest.qWait(panel.hover_help.HOVER_DELAY_MS + 80)
            panel.hover_help.show_help()  # A delayed request must not use a deleted widget.
            self.app.processEvents()
            current = panel.mood_climate_buttons[1]
            QTest.mouseMove(panel, QPoint(2, 2))
            QTest.mouseMove(panel, current.mapTo(panel, current.rect().center()))
            QTest.qWait(panel.hover_help.HOVER_DELAY_MS + 80)
            self.assertTrue(panel.hover_help.label.isVisible())
            self.assertEqual(panel.hover_help.label.text(), current.toolTip())
        finally:
            panel.close()
            other.close()
            panel.deleteLater()
            other.deleteLater()

    def test_information_navigation_compacts_before_large_translations_clip(self):
        window = InformationCenterWindow(AssetManager.get_resource_path)
        window.resize(1280, 800)
        window.show()
        set_ui_text_size("large")
        try:
            for locale in ("zh_TW", "zh_CN", "ja_JP", "en_US"):
                set_ui_locale(locale)
                window.retranslate_ui()
                self.app.processEvents()
                if window._navigation_compact:
                    self.assertTrue(all(not b.text() and b.toolTip() for b in window.navigation_buttons.values()))
                else:
                    self.assertGreaterEqual(
                        window.navigation_title.width(),
                        window.navigation_title.fontMetrics().horizontalAdvance(window.navigation_title.text()),
                        locale,
                    )
                    for button in window.navigation_buttons.values():
                        self.assertGreaterEqual(button.width(), button.sizeHint().width(), (locale, button.text()))
            set_ui_locale("en_US")
            window.retranslate_ui()
            self.assertTrue(window._navigation_compact)
        finally:
            window.close()
            window.deleteLater()

    def test_tooltips_cover_rows_and_options_after_language_refresh(self):
        binding = FakeStatusSettingsBinding()
        panel = StatusSettingsPanel(binding)
        for locale in ("zh_TW", "zh_CN", "ja_JP", "en_US"):
            binding.state = replace(binding.state, ui_locale=locale)
            panel.refresh_from_binding()
            panel.refresh_from_binding()  # Existing options, not a rebuild.
            for value, button in zip(binding.state.mood_climate_options, panel.mood_climate_buttons):
                self.assertEqual(button.toolTip(), translate_ui(
                    f"settings.mood_climate_tooltips.{value}",
                    default=MOOD_CLIMATE_TOOLTIPS[value],
                ))
            for name in (
                "world_mode", "time_scale", "display_scale", "ui_text_size",
                "teio_duration", "tsuyoshi_duration", "race_frequency",
                "chorus_frequency", "mood_climate", "memory_album_mode",
                "memory_album_capacity", "ui_locale",
            ):
                self.assertTrue(all(b.toolTip() for b in getattr(panel, f"{name}_buttons")), (locale, name))
            self.assertEqual(panel.care_toggle_row.toolTip(), panel.care_switch.toolTip())
            self.assertEqual(panel.care_toggle_row._text_label.toolTip(), panel.care_switch.toolTip())
        self.assertTrue(panel.testAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips))
        panel.close()
        panel.deleteLater()

    def test_large_text_four_locales_keeps_options_visible_in_narrow_layout(self):
        binding = FakeStatusSettingsBinding()
        host = QWidget()
        apply_ui_theme(host)
        panel = StatusSettingsPanel(binding, parent=host)
        host.resize(760, 540)
        panel.setGeometry(host.rect())
        host.show()
        set_ui_text_size("large")
        for locale in ("zh_TW", "zh_CN", "ja_JP", "en_US"):
            binding.state = replace(binding.state, ui_locale=locale, ui_text_size="large")
            panel.refresh_from_binding()
            self.app.processEvents()
            self.assertEqual(panel.settings_scroll.horizontalScrollBar().maximum(), 0, locale)
            for buttons in (panel.ui_text_size_buttons, panel.ui_locale_buttons, panel.race_frequency_buttons):
                for button in buttons:
                    font = QFont(button.font())
                    font.setPixelSize(ui_font_pixels(max(12, round(14*button.art_scale))))
                    font.setBold(button.isChecked())
                    self.assertGreaterEqual(button.width(), QFontMetrics(font).horizontalAdvance(button.text()), (locale, button.text()))
                    self.assertGreaterEqual(button.height(), QFontMetrics(font).height(), (locale, button.text(), button.minimumHeight(), button.maximumHeight(), button.art_scale))
        panel.ui_text_size_buttons[0].click()
        self.assertEqual(binding.state.ui_text_size, "small")
        self.assertEqual(get_ui_text_size(), "small")
        host.close()
        host.deleteLater()


if __name__ == "__main__":
    unittest.main()
