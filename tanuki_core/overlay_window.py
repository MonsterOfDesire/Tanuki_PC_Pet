import os

from PyQt6.QtCore import Qt

from .platform_capabilities import get_platform_capabilities


SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"


def build_overlay_window_flags():
    flags = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    return flags


def apply_platform_tool_window_attributes(widget, capabilities=None):
    capabilities = capabilities or get_platform_capabilities()
    if capabilities.keep_tool_windows_visible_when_inactive:
        widget.setAttribute(
            Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow,
            True,
        )
    return widget
