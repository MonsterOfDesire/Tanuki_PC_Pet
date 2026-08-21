from __future__ import annotations

from dataclasses import dataclass
import sys


PLATFORM_WINDOWS = "windows"
PLATFORM_MACOS = "macos"
PLATFORM_LINUX = "linux"
PLATFORM_OTHER = "other"


def normalize_platform_key(value=None):
    value = str(sys.platform if value is None else value).strip().lower()
    if value in {"win32", "cygwin", "windows"}:
        return PLATFORM_WINDOWS
    if value in {"darwin", "mac", "macos"}:
        return PLATFORM_MACOS
    if value.startswith("linux"):
        return PLATFORM_LINUX
    return PLATFORM_OTHER


@dataclass(frozen=True)
class PlatformCapabilities:
    platform_key: str
    window_tracking: bool
    global_mouse_listener: bool
    standalone_updater: bool
    keep_tool_windows_visible_when_inactive: bool

    @property
    def window_perching(self):
        return self.window_tracking

    @property
    def window_to_window_flight(self):
        return self.window_tracking

    @property
    def update_method(self):
        return (
            "standalone_updater"
            if self.standalone_updater
            else "manual_release"
        )


def get_platform_capabilities(platform=None):
    platform_key = normalize_platform_key(platform)
    if platform_key == PLATFORM_WINDOWS:
        return PlatformCapabilities(
            platform_key=platform_key,
            window_tracking=True,
            global_mouse_listener=True,
            standalone_updater=True,
            keep_tool_windows_visible_when_inactive=False,
        )
    if platform_key == PLATFORM_MACOS:
        return PlatformCapabilities(
            platform_key=platform_key,
            window_tracking=False,
            global_mouse_listener=False,
            standalone_updater=False,
            keep_tool_windows_visible_when_inactive=True,
        )
    return PlatformCapabilities(
        platform_key=platform_key,
        window_tracking=False,
        global_mouse_listener=False,
        standalone_updater=False,
        keep_tool_windows_visible_when_inactive=False,
    )


def build_capability_report(platform=None):
    capabilities = get_platform_capabilities(platform)
    return {
        "platform": capabilities.platform_key,
        "window_tracking": capabilities.window_tracking,
        "window_perching": capabilities.window_perching,
        "window_to_window_flight": capabilities.window_to_window_flight,
        "global_mouse_listener": capabilities.global_mouse_listener,
        "update_method": capabilities.update_method,
    }
