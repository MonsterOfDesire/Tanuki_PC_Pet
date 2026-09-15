from __future__ import annotations

import ctypes
from ctypes import wintypes


WINDOWS_PET_TOPMOST_REFRESH_SECONDS = 2.0
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
    except Exception:
        return False
