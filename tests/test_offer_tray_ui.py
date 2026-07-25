import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from tanuki_core.asset_manager import AssetManager
from tanuki_core.offer_tray_ui import OfferTrayWindow
from tanuki_core.ui_skin_assets import UiSkinAssets
from tanuki_core.ui_skin_spec import SKIN_DIET


class OfferTrayWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.assets = UiSkinAssets(AssetManager.get_resource_path)

    def setUp(self):
        self.window = OfferTrayWindow(assets=self.assets)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_tray_uses_diet_skin_and_all_offer_actions(self):
        self.assertEqual(self.window.skin_frame.skin_spec.key, SKIN_DIET)
        self.assertGreaterEqual(self.window.minimumWidth(), 680)
        self.assertGreaterEqual(self.window.minimumHeight(), 510)
        self.assertEqual(len(self.window.item_badges), 5)
        self.assertEqual(
            tuple(badge.title_label.text() for badge in self.window.item_badges),
            ("拉麵", "蜂蜜", "茶", "奶瓶", "棒棒糖"),
        )
        self.assertEqual(self.window.instruction_label.text(), "拖曳給角色")
        self.assertIn("拖曳到桌面角色", self.window.instruction_label.toolTip())

    def test_tray_uses_embedded_frameless_chrome(self):
        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        )
        self.assertGreater(self.window.chrome_drag_zone.geometry().width(), 0)
        self.assertGreater(self.window.window_chrome.controls.geometry().width(), 0)
        self.assertLess(
            self.window.window_chrome.controls.geometry().right(),
            self.window.width(),
        )

    def test_character_foreground_animates_without_blocking_drag_targets(self):
        foreground = self.window.skin_frame.foreground_layer

        self.assertIsNotNone(foreground.movie)
        self.assertGreater(foreground.geometry().width(), 0)
        self.assertGreater(foreground.geometry().height(), 0)
        self.assertTrue(
            foreground.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        )

    def test_programmatic_anchor_is_clamped_to_the_available_screen(self):
        self.window.user_position_locked = False
        self.window.move_near_anchor(100_000, 100_000)
        self.app.processEvents()
        screen = QGuiApplication.screenAt(self.window.geometry().center()) or self.window.screen()
        available = screen.availableGeometry()

        self.assertLessEqual(self.window.geometry().right(), available.right())
        self.assertLessEqual(self.window.geometry().bottom(), available.bottom())
        self.assertFalse(self.window.user_position_locked)


if __name__ == "__main__":
    unittest.main()
