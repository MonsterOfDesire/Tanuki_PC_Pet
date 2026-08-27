import os

from PyQt6.QtCore import Qt

from .macos_window_policy import install_macos_native_window_policy
from .platform_capabilities import get_platform_capabilities


SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"
WINDOW_ROLE_PET = "pet"
WINDOW_ROLE_PERSISTENT_OVERLAY = "persistent_overlay"
WINDOW_ROLE_PERSISTENT_TOOL = "persistent_tool"
WINDOW_ROLE_UTILITY = "utility"


def build_overlay_window_flags(capabilities=None, *, role=WINDOW_ROLE_PERSISTENT_OVERLAY):
    capabilities = capabilities or get_platform_capabilities()
    flags = (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    if (
        role == WINDOW_ROLE_PET
        and capabilities.pet_overlay_avoids_application_activation
    ):
        flags |= Qt.WindowType.WindowDoesNotAcceptFocus
    return flags


def build_utility_window_flags(capabilities=None):
    capabilities = capabilities or get_platform_capabilities()
    if capabilities.native_utility_window_chrome:
        return (
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
    return Qt.WindowType.Tool


def apply_platform_tool_window_attributes(
    widget,
    capabilities=None,
    *,
    role=WINDOW_ROLE_PERSISTENT_OVERLAY,
):
    capabilities = capabilities or get_platform_capabilities()
    if (
        role != WINDOW_ROLE_UTILITY
        and capabilities.keep_tool_windows_visible_when_inactive
    ):
        widget.setAttribute(
            Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow,
            True,
        )
    if (
        role == WINDOW_ROLE_PET
        and capabilities.pet_overlay_avoids_application_activation
    ):
        widget.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )
    install_macos_native_window_policy(
        widget,
        nonactivating=(
            role == WINDOW_ROLE_PET
            and capabilities.native_pet_nonactivating_panel
        ),
        join_all_spaces=(
            role in {WINDOW_ROLE_PET, WINDOW_ROLE_PERSISTENT_OVERLAY}
            and capabilities.persistent_overlays_join_all_spaces
        ),
    )
    return widget
