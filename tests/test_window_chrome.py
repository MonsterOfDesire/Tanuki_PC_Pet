import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QWidget

from tanuki_core.overlay_window import build_utility_window_flags
from tanuki_core.platform_capabilities import get_platform_capabilities
from tanuki_core.window_chrome import (
    NativeUtilityWindowChrome,
    SkinnedToolWindowChrome,
    create_platform_window_chrome,
)


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
        self.assertFalse(hasattr(self.chrome.controls, "minimize_button"))
        self.assertEqual(self.chrome.controls.pin_button.accessibleName(), "視窗置頂")

    def test_pin_button_preserves_frameless_flag_and_toggles_topmost(self):
        self.chrome.controls.pin_button.click()

        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )
        self.assertTrue(
            bool(self.window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        )

    def test_macos_uses_native_frame_with_only_in_content_pin_control(self):
        capabilities = get_platform_capabilities("darwin")
        window = QWidget(None, build_utility_window_flags(capabilities))
        window.resize(640, 480)
        chrome = create_platform_window_chrome(
            window,
            capabilities=capabilities,
        )
        chrome.refresh_geometry()
        try:
            self.assertIsInstance(chrome, NativeUtilityWindowChrome)
            self.assertFalse(
                bool(
                    window.windowFlags()
                    & Qt.WindowType.FramelessWindowHint
                )
            )
            self.assertTrue(hasattr(chrome.controls, "pin_button"))
            self.assertFalse(hasattr(chrome.controls, "close_button"))
            self.assertFalse(hasattr(chrome.controls, "minimize_button"))
            self.assertEqual(chrome.resize_handles, {})
        finally:
            window.close()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
