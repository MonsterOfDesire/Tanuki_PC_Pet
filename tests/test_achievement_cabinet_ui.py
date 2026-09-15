import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from tanuki_core.achievement_cabinet_ui import (
    AchievementCabinetPanel,
    AchievementUnlockToast,
    _locked_silhouette,
    _trim_transparent_bounds,
)
from tanuki_core.achievement_catalog import load_achievement_catalog
from tanuki_core.achievement_presenter import (
    build_achievement_cabinet_snapshot,
    build_achievement_unlock_notification,
)
from tanuki_core.achievement_state import AchievementState
from tanuki_core.asset_manager import AssetManager


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "UI"
    / "trophies"
    / "achievement_catalog_draft.json"
)


class AchievementCabinetUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.catalog = load_achievement_catalog(CATALOG_PATH)

    def setUp(self):
        self.state = AchievementState()
        self.snapshot = build_achievement_cabinet_snapshot(
            self.catalog,
            self.state,
        )

    def test_panel_browses_modes_without_changing_runtime_mode(self):
        panel = AchievementCabinetPanel(AssetManager.get_resource_path)
        panel.resize(900, 500)
        panel.set_snapshot(self.snapshot, "sandbox")

        panel.select_mode("golden_legend")

        self.assertEqual(panel.current_world_mode, "golden_legend")
        self.assertEqual(panel.progress_label.text(), "已取得 0 / 2")
        self.assertEqual(panel.current_tier, "G3")
        panel.deleteLater()

    def test_capture_toggle_uses_binding_and_defaults_off(self):
        class Binding:
            def __init__(self, snapshot):
                self._snapshot = snapshot
                self.enabled = False

            def snapshot(self):
                return self._snapshot

            def capture_enabled(self):
                return self.enabled

            def set_capture_enabled(self, enabled):
                self.enabled = bool(enabled)
                return self.enabled

        binding = Binding(self.snapshot)
        panel = AchievementCabinetPanel(
            AssetManager.get_resource_path,
            binding=binding,
        )

        self.assertFalse(panel.capture_toggle.isChecked())
        panel.capture_toggle.setChecked(True)

        self.assertTrue(binding.enabled)
        panel.deleteLater()

    def test_unlocked_card_requires_two_stage_reset_confirmation(self):
        definition = self.catalog.get("race.first_natural_finish")
        self.state.progress_for(
            definition.world_mode,
            definition.achievement_id,
        ).unlock(1_700_000_000.0)

        class Binding:
            def __init__(self, catalog, state):
                self.catalog = catalog
                self.state = state
                self.reset_calls = []

            def snapshot(self):
                return build_achievement_cabinet_snapshot(
                    self.catalog,
                    self.state,
                )

            def capture_enabled(self):
                return False

            def reset_achievement(self, world_mode, achievement_id):
                self.reset_calls.append((world_mode, achievement_id))
                return self.state.reset_achievement(
                    world_mode,
                    achievement_id,
                )

        binding = Binding(self.catalog, self.state)
        panel = AchievementCabinetPanel(
            AssetManager.get_resource_path,
            binding=binding,
        )
        panel.select_mode(definition.world_mode)
        panel.select_tier(definition.tier)
        card = next(
            widget
            for widget in panel.card_widgets
            if widget.snapshot.slot_key == definition.achievement_id
        )

        self.assertIsNotNone(card.reset_button)
        self.assertFalse(card._handle_reset_clicked())
        self.assertEqual(binding.reset_calls, [])
        self.assertIn("再次", card.reset_button.text())

        card._reset_armed_at -= 1.0
        self.assertTrue(card._handle_reset_clicked())
        self.assertEqual(
            binding.reset_calls,
            [(definition.world_mode, definition.achievement_id)],
        )
        self.assertFalse(
            self.state.is_unlocked(
                definition.world_mode,
                definition.achievement_id,
            )
        )
        replacement = next(
            widget
            for widget in panel.card_widgets
            if widget.snapshot.slot_key == definition.achievement_id
        )
        self.assertIsNone(replacement.reset_button)
        panel.deleteLater()

    def test_locked_card_does_not_reveal_title_method_or_progress(self):
        panel = AchievementCabinetPanel(AssetManager.get_resource_path)
        panel.set_snapshot(self.snapshot, "sandbox")
        locked = panel.card_widgets[0]

        panel.show_card_detail(locked.snapshot)

        self.assertFalse(locked.snapshot.unlocked)
        self.assertEqual(locked.title_label.text(), "")
        self.assertEqual(panel.detail_title_label.text(), "")
        self.assertNotIn("初次", panel.detail_method_label.text())
        panel.deleteLater()

    def test_responsive_grid_uses_five_three_or_two_columns(self):
        self.assertEqual(AchievementCabinetPanel.column_count_for_width(900), 5)
        self.assertEqual(AchievementCabinetPanel.column_count_for_width(620), 3)
        self.assertEqual(AchievementCabinetPanel.column_count_for_width(420), 2)

    def test_locked_silhouette_has_a_visible_light_outline(self):
        source = _trim_transparent_bounds(
            QPixmap(
                AssetManager.get_resource_path(
                    "UI/trophies/race/3008.png"
                )
            )
        )

        silhouette = _locked_silhouette(source)
        image = silhouette.toImage()
        has_light_outline = any(
            image.pixelColor(x, y).alpha() > 0
            and image.pixelColor(x, y).red() > 220
            and image.pixelColor(x, y).green() > 220
            and image.pixelColor(x, y).blue() > 220
            for y in range(image.height())
            for x in range(image.width())
        )

        self.assertGreater(silhouette.width(), source.width())
        self.assertGreater(silhouette.height(), source.height())
        self.assertTrue(has_light_outline)

    def test_unlock_toast_is_non_modal_and_auto_hides(self):
        self.state.progress_for(
            "sandbox",
            "race.first_natural_finish",
        ).unlock(1_700_000_000.0)
        snapshot = build_achievement_cabinet_snapshot(
            self.catalog,
            self.state,
        )
        notification = build_achievement_unlock_notification(
            snapshot,
            ("race.first_natural_finish",),
        )
        toast = AchievementUnlockToast(AssetManager.get_resource_path)

        shown = toast.show_notification(
            notification,
            anchor_rect=QRect(0, 0, 1280, 720),
            duration_ms=1000,
        )
        self.app.processEvents()

        self.assertTrue(shown)
        self.assertTrue(toast.isVisible())
        self.assertTrue(toast.hide_timer.isActive())
        self.assertFalse(toast.isModal())

        toast.close()
        toast.deleteLater()
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
