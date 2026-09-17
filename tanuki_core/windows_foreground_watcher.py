from __future__ import annotations

import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QObject, pyqtSignal


EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002


class WindowsForegroundWatcher(QObject):
    """Emit external foreground-window changes without periodic polling."""

    foreground_changed = pyqtSignal(int)

    def __init__(self, *, platform_key, parent=None):
        super().__init__(parent)
        self.platform_key = str(platform_key or "")
        self._hook = None
        self._callback = None

    @property
    def active(self):
        return bool(self._hook)

    def start(self, *, hook_installer=None):
        if self.platform_key != "windows" or self.active:
            return self.active
        callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
            None,
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.HWND,
            wintypes.LONG,
            wintypes.LONG,
            wintypes.DWORD,
            wintypes.DWORD,
        )

        @callback_type
        def callback(_hook, event, hwnd, _object_id, _child_id, _thread, _time):
            if int(event) == EVENT_SYSTEM_FOREGROUND and int(hwnd or 0):
                self.foreground_changed.emit(int(hwnd))

        self._callback = callback
        try:
            if hook_installer is not None:
                hook = hook_installer(callback)
            else:
                setter = ctypes.windll.user32.SetWinEventHook
                setter.argtypes = (
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.HMODULE,
                    callback_type,
                    wintypes.DWORD,
                    wintypes.DWORD,
                    wintypes.DWORD,
                )
                setter.restype = wintypes.HANDLE
                hook = setter(
                    EVENT_SYSTEM_FOREGROUND,
                    EVENT_SYSTEM_FOREGROUND,
                    None,
                    callback,
                    0,
                    0,
                    WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
                )
            self._hook = int(hook or 0) or None
        except Exception:
            self._hook = None
        if not self._hook:
            self._callback = None
            return False
        return True

    def stop(self, *, unhook=None):
        hook = self._hook
        # Keep the ctypes callback alive until Windows has removed the hook.
        # Releasing it first leaves a short window where user32 could call a
        # freed function pointer during shutdown.
        callback = self._callback
        self._hook = None
        if not hook:
            self._callback = None
            return False
        try:
            if unhook is not None:
                result = bool(unhook(hook))
            else:
                function = ctypes.windll.user32.UnhookWinEvent
                function.argtypes = (wintypes.HANDLE,)
                function.restype = wintypes.BOOL
                result = bool(function(wintypes.HANDLE(hook)))
            return result
        except Exception:
            return False
        finally:
            self._callback = None
            del callback
