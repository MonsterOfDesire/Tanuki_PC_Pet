import unittest

from PyQt6.QtCore import Qt

from tanuki_core.overlay_window import (
    WINDOW_ROLE_PET,
    WINDOW_ROLE_UTILITY,
    apply_platform_tool_window_attributes,
    build_overlay_window_flags,
    build_utility_window_flags,
)
from tanuki_core.platform_capabilities import get_platform_capabilities


class FakeWidget:
    def __init__(self):
        self.attributes = []

    def setAttribute(self, attribute, enabled):
        self.attributes.append((attribute, enabled))


class OverlayWindowTests(unittest.TestCase):
    def test_macos_keeps_tool_windows_visible_when_inactive(self):
        widget = FakeWidget()

        apply_platform_tool_window_attributes(
            widget,
            capabilities=get_platform_capabilities("darwin"),
        )

        self.assertEqual(
            widget.attributes,
            [(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)],
        )

    def test_windows_does_not_apply_macos_attribute(self):
        widget = FakeWidget()

        apply_platform_tool_window_attributes(
            widget,
            capabilities=get_platform_capabilities("win32"),
        )

        self.assertEqual(widget.attributes, [])

    def test_macos_utility_window_does_not_stay_visible_when_inactive(self):
        widget = FakeWidget()

        apply_platform_tool_window_attributes(
            widget,
            capabilities=get_platform_capabilities("darwin"),
            role=WINDOW_ROLE_UTILITY,
        )

        self.assertEqual(widget.attributes, [])

    def test_macos_pet_overlay_is_nonactivating_but_windows_flags_are_unchanged(self):
        macos = get_platform_capabilities("darwin")
        windows = get_platform_capabilities("win32")
        mac_flags = build_overlay_window_flags(
            macos,
            role=WINDOW_ROLE_PET,
        )
        windows_flags = build_overlay_window_flags(
            windows,
            role=WINDOW_ROLE_PET,
        )

        self.assertTrue(
            bool(mac_flags & Qt.WindowType.WindowDoesNotAcceptFocus)
        )
        self.assertFalse(
            bool(windows_flags & Qt.WindowType.WindowDoesNotAcceptFocus)
        )

    def test_only_macos_utility_windows_use_native_window_type(self):
        mac_flags = build_utility_window_flags(
            get_platform_capabilities("darwin")
        )
        windows_flags = build_utility_window_flags(
            get_platform_capabilities("win32")
        )

        self.assertEqual(
            mac_flags & Qt.WindowType.WindowType_Mask,
            Qt.WindowType.Window,
        )
        self.assertEqual(
            windows_flags & Qt.WindowType.WindowType_Mask,
            Qt.WindowType.Tool,
        )
        self.assertTrue(
            bool(mac_flags & Qt.WindowType.WindowCloseButtonHint)
        )
        self.assertFalse(
            bool(mac_flags & Qt.WindowType.WindowMinimizeButtonHint)
        )
        self.assertFalse(
            bool(mac_flags & Qt.WindowType.WindowMaximizeButtonHint)
        )


if __name__ == "__main__":
    unittest.main()
