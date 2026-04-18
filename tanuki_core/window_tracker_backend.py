import ctypes
import os
import sys
from ctypes import wintypes
from dataclasses import dataclass

from PyQt6.QtCore import QRect


@dataclass(frozen=True)
class WindowSnapshot:
    hwnd: int
    rect: QRect
    title: str
    class_name: str
    pid: int
    owner_hwnd: int
    style: int
    ex_style: int
    is_visible: bool
    is_iconic: bool
    is_cloaked: bool


class Win32WindowTrackerBackend:
    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    GW_OWNER = 4
    GA_ROOT = 2
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_CLOAKED = 14

    def __init__(self):
        self.available = (sys.platform == "win32")
        self.own_pid = os.getpid()
        if self.available:
            self.user32 = ctypes.windll.user32
            self.dwmapi = getattr(ctypes.windll, "dwmapi", None)
            self.enum_windows_proc = ctypes.WINFUNCTYPE(
                wintypes.BOOL,
                wintypes.HWND,
                wintypes.LPARAM,
            )
        else:
            self.user32 = None
            self.dwmapi = None
            self.enum_windows_proc = None

    def enumerate_window_snapshots(self):
        if not self.available:
            return []

        collected = []

        @self.enum_windows_proc
        def enum_proc(hwnd, _lparam):
            snapshot = self.read_window_snapshot(hwnd)
            if snapshot:
                collected.append(snapshot)
            return True

        self.user32.EnumWindows(enum_proc, 0)
        return collected

    def get_window_rect(self, hwnd):
        rect = wintypes.RECT()
        if self.dwmapi:
            try:
                hr = self.dwmapi.DwmGetWindowAttribute(
                    hwnd,
                    self.DWMWA_EXTENDED_FRAME_BOUNDS,
                    ctypes.byref(rect),
                    ctypes.sizeof(rect),
                )
                if hr == 0:
                    return rect
            except Exception:
                pass
        self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return rect

    def get_window_text(self, hwnd):
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value

    def get_class_name(self, hwnd):
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, buffer, len(buffer))
        return buffer.value

    def is_window_cloaked(self, hwnd):
        if not self.dwmapi:
            return False
        cloaked = wintypes.DWORD()
        try:
            hr = self.dwmapi.DwmGetWindowAttribute(
                hwnd,
                self.DWMWA_CLOAKED,
                ctypes.byref(cloaked),
                ctypes.sizeof(cloaked),
            )
            return hr == 0 and bool(cloaked.value)
        except Exception:
            return False

    def read_window_snapshot(self, hwnd):
        hwnd = self.user32.GetAncestor(hwnd, self.GA_ROOT)
        if not hwnd:
            return None

        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        rect = self.get_window_rect(hwnd)
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        return WindowSnapshot(
            hwnd=int(hwnd),
            rect=QRect(rect.left, rect.top, width, height),
            title=self.get_window_text(hwnd).strip(),
            class_name=self.get_class_name(hwnd),
            pid=pid.value,
            owner_hwnd=int(self.user32.GetWindow(hwnd, self.GW_OWNER) or 0),
            style=self.user32.GetWindowLongW(hwnd, self.GWL_STYLE),
            ex_style=self.user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE),
            is_visible=bool(self.user32.IsWindowVisible(hwnd)),
            is_iconic=bool(self.user32.IsIconic(hwnd)),
            is_cloaked=self.is_window_cloaked(hwnd),
        )
