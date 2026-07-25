import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QLabel

from tanuki_core.asset_manager import AssetManager
from tanuki_core.skinned_window_frame import SkinnedWindowFrame
from tanuki_core.ui_skin_assets import UiSkinAssets
from tanuki_core.ui_skin_spec import (
    SKIN_EVENT_LOG,
    SKIN_FAMILY_STATUS,
    SKIN_RELATION_SUMMON,
    SKIN_STATUS_SETTINGS,
)
from tanuki_core.ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet


class SkinnedWindowFrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.assets = UiSkinAssets(AssetManager.get_resource_path)

    def test_frame_applies_scene_content_and_foreground_geometry(self):
        frame = SkinnedWindowFrame(self.assets, SKIN_RELATION_SUMMON)
        frame.resize(1200, 675)
        self.app.processEvents()

        minimum_content = frame.skin_spec.minimum_content_size
        self.assertGreaterEqual(frame.content_geometry().width(), minimum_content[0])
        self.assertGreaterEqual(frame.content_geometry().height(), minimum_content[1])
        self.assertGreater(frame.foreground_geometry().width(), 0)
        self.assertGreater(frame.foreground_geometry().height(), 0)
        self.assertGreater(frame.occlusion_geometry().width(), 0)
        frame.close()

    def test_scene_viewport_keeps_source_aspect_and_contains_all_layers(self):
        frame = SkinnedWindowFrame(self.assets, SKIN_RELATION_SUMMON)
        frame.show()
        test_sizes = (
            (1920, 1080),
            (1280, 720),
            (1280, 800),
            frame.skin_spec.minimum_frame_size,
        )

        for width, height in test_sizes:
            with self.subTest(size=(width, height)):
                frame.resize(width, height)
                self.app.processEvents()
                scene = frame.scene_geometry()
                self.assertAlmostEqual(scene.width() / scene.height(), 16.0 / 9.0, places=2)
                self.assertGreaterEqual(scene.x(), 0)
                self.assertGreaterEqual(scene.y(), 0)
                self.assertLessEqual(scene.right(), frame.width())
                self.assertLessEqual(scene.bottom(), frame.height())
                for geometry in (
                    frame.content_geometry(),
                    frame.occlusion_geometry(),
                ):
                    self.assertGreaterEqual(geometry.x(), 0)
                    self.assertGreaterEqual(geometry.y(), 0)
                    self.assertLessEqual(geometry.right(), scene.width())
                    self.assertLessEqual(geometry.bottom(), scene.height())
                foreground = frame.foreground_geometry()
                self.assertLess(foreground.x(), scene.width())
                self.assertLess(foreground.y(), scene.height())
                self.assertGreater(foreground.right(), 0)
                self.assertGreater(foreground.bottom(), 0)
        frame.close()

    def test_compact_frames_crop_outer_scene_and_keep_content_visible(self):
        for skin_key in (
            SKIN_RELATION_SUMMON,
            SKIN_EVENT_LOG,
            SKIN_FAMILY_STATUS,
            SKIN_STATUS_SETTINGS,
        ):
            with self.subTest(skin_key=skin_key):
                frame = SkinnedWindowFrame(self.assets, skin_key)
                frame.show()
                frame.resize(*frame.skin_spec.minimum_window_size)
                self.app.processEvents()

                scene = frame.scene_geometry()
                content = frame.content_geometry()
                content_left = scene.x() + content.x()
                content_top = scene.y() + content.y()
                content_right = content_left + content.width()
                content_bottom = content_top + content.height()

                self.assertTrue(scene.x() < 0 or scene.y() < 0)
                self.assertGreaterEqual(content_left, -1)
                self.assertGreaterEqual(content_top, -1)
                self.assertLessEqual(content_right, frame.width() + 1)
                self.assertLessEqual(content_bottom, frame.height() + 1)
                self.assertGreaterEqual(
                    content.width(),
                    frame.skin_spec.minimum_content_size[0],
                )
                self.assertGreaterEqual(
                    content.height(),
                    frame.skin_spec.minimum_content_size[1],
                )
                frame.close()

    def test_relation_foreground_uses_background_frame_mapping(self):
        frame = SkinnedWindowFrame(self.assets, SKIN_RELATION_SUMMON)

        frame._sync_foreground_frame(0)
        first_mapped_frame = frame.foreground_layer.movie.currentFrameNumber()
        frame._sync_foreground_frame(2)
        second_mapped_frame = frame.foreground_layer.movie.currentFrameNumber()

        self.assertEqual(first_mapped_frame, 3)
        self.assertEqual(second_mapped_frame, 0)
        frame.close()

    def test_relation_occlusion_masks_text_pixels_instead_of_blank_board_area(self):
        frame = SkinnedWindowFrame(self.assets, SKIN_RELATION_SUMMON)
        frame.resize(1920, 1080)
        self.app.processEvents()

        mask = frame.occlusion_surface.mask()

        self.assertFalse(mask.isEmpty())
        self.assertFalse(mask.contains(QPoint(800, 500)))
        self.assertFalse(mask.contains(QPoint(1000, 600)))
        frame.close()

    def test_frame_can_switch_skin_without_replacing_content_widget(self):
        frame = SkinnedWindowFrame(self.assets, SKIN_RELATION_SUMMON)
        label = QLabel("content")
        frame.set_content_widget(label)

        frame.set_skin(SKIN_STATUS_SETTINGS)

        self.assertIs(label.parent(), frame.content_surface)
        self.assertEqual(frame.skin_spec.key, SKIN_STATUS_SETTINGS)
        frame.close()

    def test_avatar_first_frame_loader_preserves_declared_source_size(self):
        pixmap = self.assets.load_first_frame("avatar_tokai_teio")

        self.assertEqual((pixmap.width(), pixmap.height()), (281, 382))

    def test_theme_stylesheet_uses_central_tokens(self):
        stylesheet = build_ui_stylesheet(DEFAULT_UI_THEME)

        self.assertIn(DEFAULT_UI_THEME.accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.relation_accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.event_accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.family_accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.settings_accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.offer_accent, stylesheet)
        self.assertIn(DEFAULT_UI_THEME.danger, stylesheet)
        self.assertIn('pageAccent="relation_summon"', stylesheet)
        self.assertIn('pageAccent="event_log"', stylesheet)
        self.assertIn('pageAccent="family_status"', stylesheet)
        self.assertIn('pageAccent="status_settings"', stylesheet)
        self.assertIn('QLabel[tanukiRole="relationLegend"]', stylesheet)
        self.assertIn("font-size: 17px;", stylesheet)
        self.assertIn('QLabel[tanukiRole="relationFormula"]', stylesheet)
        self.assertIn("color: #17120f;", stylesheet)
        self.assertIn("font-size: 12px;", stylesheet)
        self.assertIn("font-weight: 800;", stylesheet)
        self.assertIn('surfaceRole="chalkboard"', stylesheet)


if __name__ == "__main__":
    unittest.main()
