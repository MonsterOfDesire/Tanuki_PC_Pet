import unittest

from PyQt6.QtCore import Qt

from tanuki_core.overlay_window import (
    apply_platform_tool_window_attributes,
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


if __name__ == "__main__":
    unittest.main()
