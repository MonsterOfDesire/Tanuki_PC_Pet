from __future__ import annotations

import ctypes
from ctypes import wintypes

from .runtime_debug_log import log_suppressed_exception


HWND_TOPMOST = -1
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200
PET_TOPMOST_FLAGS = (
    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_NOOWNERZORDER
)


def _is_windows_topmost(hwnd):
    user32 = ctypes.windll.user32
    getter = getattr(user32, "GetWindowLongPtrW", None)
    if getter is None:
        getter = user32.GetWindowLongW
    getter.argtypes = (wintypes.HWND, ctypes.c_int)
    getter.restype = ctypes.c_ssize_t
    return bool(
        int(getter(wintypes.HWND(int(hwnd)), GWL_EXSTYLE))
        & WS_EX_TOPMOST
    )


def _set_windows_topmost(hwnd):
    user32 = ctypes.windll.user32
    set_window_pos = user32.SetWindowPos
    set_window_pos.argtypes = (
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    )
    set_window_pos.restype = wintypes.BOOL
    return bool(
        set_window_pos(
            wintypes.HWND(int(hwnd)),
            wintypes.HWND(HWND_TOPMOST),
            0,
            0,
            0,
            0,
            PET_TOPMOST_FLAGS,
        )
    )


def _windows_z_order(hwnds):
    targets = {int(hwnd) for hwnd in hwnds if int(hwnd)}
    if not targets:
        return []
    ordered = []
    callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @callback_type
    def collect(hwnd, _lparam):
        value = int(hwnd)
        if value in targets:
            ordered.append(value)
        return True

    ctypes.windll.user32.EnumWindows(collect, 0)
    ordered.extend(hwnd for hwnd in targets if hwnd not in ordered)
    return ordered


def restore_pet_topmost(
    widget,
    *,
    platform_key,
    is_topmost=None,
    set_topmost=None,
):
    """Restore a lost Windows topmost flag without reordering topmost peers."""
    if str(platform_key or "") != "windows" or widget is None:
        return False
    try:
        if not bool(widget.isVisible()):
            return False
        hwnd = int(widget.winId())
        if not hwnd:
            return False
        topmost_checker = is_topmost or _is_windows_topmost
        if bool(topmost_checker(hwnd)):
            return True
        provider = set_topmost or _set_windows_topmost
        return bool(provider(hwnd))
    except Exception as error:
        log_suppressed_exception("pet_window_layer.restore_topmost", error)
        return False


def restore_pet_group_topmost(
    widgets,
    *,
    platform_key,
    z_order_provider=None,
    set_topmost=None,
):
    """Raise the visible pet group once while preserving peer z-order.

    This is intended for event-driven recovery after another application takes
    the foreground. It deliberately does not run on every pet tick.
    """
    if str(platform_key or "") != "windows":
        return False
    handles = []
    try:
        for widget in widgets or ():
            if widget is None or not bool(widget.isVisible()):
                continue
            hwnd = int(widget.winId())
            if hwnd:
                handles.append(hwnd)
        if not handles:
            return False
        order_provider = z_order_provider or _windows_z_order
        top_to_bottom = list(order_provider(handles) or handles)
        known = set(handles)
        top_to_bottom = [hwnd for hwnd in top_to_bottom if hwnd in known]
        top_to_bottom.extend(
            hwnd for hwnd in handles if hwnd not in top_to_bottom
        )
        provider = set_topmost or _set_windows_topmost
        # SetWindowPos(HWND_TOPMOST) promotes to the top of the topmost band.
        # Replaying back-to-front keeps the user's most recently raised pet on
        # top instead of causing the old periodic peer-order flicker.
        restored = False
        for hwnd in reversed(top_to_bottom):
            restored = bool(provider(hwnd)) or restored
        return restored
    except Exception as error:
        log_suppressed_exception("pet_window_layer.restore_group_topmost", error)
        return False
