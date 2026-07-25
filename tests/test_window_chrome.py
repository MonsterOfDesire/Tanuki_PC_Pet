import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QWidget

from tanuki_core.window_chrome import SkinnedToolWindowChrome


class SkinnedToolWindowChromeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = QWidget(None, Qt.WindowType.Tool)
        self.window.resize(640, 480)
        self.drag_handle = QFrame(self.window)
        self.chrome = SkinnedToolWindowChrome(
            self.window,
            drag_widgets=(self.drag_handle,),
        )
        self.chrome.refresh_geometry()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def test_chrome_declares_frameless_controls_and_resize_handles(self):
        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        )
        self.assertEqual(len(self.chrome.resize_handles), 8)
        self.assertTrue(all(handle.width() > 0 for handle in self.chrome.resize_handles.values()))
        self.assertFalse(self.chrome.controls.close_button.icon().isNull())
        self.assertEqual(self.chrome.controls.pin_button.accessibleName(), "視窗置頂")

    def test_pin_button_preserves_frameless_flag_and_toggles_topmost(self):
        self.chrome.controls.pin_button.click()

        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )
        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        )


if __name__ == "__main__":
    unittest.main()
