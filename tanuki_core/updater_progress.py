from __future__ import annotations

import os
import threading


class UpdaterProgressWindow:
    """Small stdlib-only progress window for the standalone updater."""

    def __init__(self, title):
        self.title = str(title or "Updater")
        self._thread = None
        self._ready = threading.Event()
        self._window_handle = None
        self._label_handle = None
        self._user32 = None
        self._window_proc = None
        self._initial_message = ""

    def show(self, message):
        message = str(message or "")
        if os.name != "nt":
            print(f"{self.title}: {message}")
            return
        if self._thread is not None and self._thread.is_alive():
            self.update(message)
            return
        self._initial_message = message
        self._ready.clear()
        self._thread = threading.Thread(
            target=self._run_window,
            name="tanuki-updater-progress",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=3.0)
        self.update(message)

    def update(self, message):
        message = str(message or "")
        if os.name != "nt":
            print(f"{self.title}: {message}")
            return
        if self._user32 is None or not self._label_handle:
            return
        self._user32.SetWindowTextW(self._label_handle, message)

    def close(self):
        if os.name != "nt":
            return
        if self._user32 is not None and self._window_handle:
            self._user32.PostMessageW(self._window_handle, 0x0010, 0, 0)
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self._window_handle = None
        self._label_handle = None
        self._user32 = None

    def _run_window(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        comctl32 = ctypes.windll.comctl32
        gdi32 = ctypes.windll.gdi32
        self._user32 = user32

        lresult = ctypes.c_ssize_t
        wparam_type = ctypes.c_size_t
        lparam_type = ctypes.c_ssize_t
        wndproc_type = ctypes.WINFUNCTYPE(
            lresult,
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        )

        class WndClass(ctypes.Structure):
            _fields_ = (
                ("style", wintypes.UINT),
                ("lpfnWndProc", wndproc_type),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            )

        class InitCommonControls(ctypes.Structure):
            _fields_ = (
                ("dwSize", wintypes.DWORD),
                ("dwICC", wintypes.DWORD),
            )

        user32.CreateWindowExW.argtypes = (
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        )
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.DefWindowProcW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        )
        user32.DefWindowProcW.restype = lresult
        user32.SendMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        )
        user32.SendMessageW.restype = lresult
        user32.PostMessageW.argtypes = (
            wintypes.HWND,
            wintypes.UINT,
            wparam_type,
            lparam_type,
        )
        user32.SetWindowTextW.argtypes = (
            wintypes.HWND,
            wintypes.LPCWSTR,
        )
        user32.SetWindowTextW.restype = wintypes.BOOL
        user32.LoadCursorW.argtypes = (
            wintypes.HINSTANCE,
            ctypes.c_void_p,
        )
        user32.LoadCursorW.restype = wintypes.HANDLE
        kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        user32.UnregisterClassW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.HINSTANCE,
        )
        user32.UnregisterClassW.restype = wintypes.BOOL
        gdi32.GetStockObject.restype = wintypes.HANDLE
        hinstance = kernel32.GetModuleHandleW(None)
        class_name = f"TanukiUpdaterProgress_{os.getpid()}"

        @wndproc_type
        def window_proc(hwnd, message, wparam, lparam):
            if message == 0x0010:
                user32.DestroyWindow(hwnd)
                return 0
            if message == 0x0002:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._window_proc = window_proc
        controls = InitCommonControls(
            ctypes.sizeof(InitCommonControls),
            0x00000020,
        )
        comctl32.InitCommonControlsEx(ctypes.byref(controls))
        window_class = WndClass(
            0,
            window_proc,
            0,
            0,
            hinstance,
            None,
            user32.LoadCursorW(None, ctypes.c_void_p(32512)),
            ctypes.c_void_p(6),
            None,
            class_name,
        )
        if not user32.RegisterClassW(ctypes.byref(window_class)):
            self._ready.set()
            return

        width = 460
        height = 145
        x = max(0, (user32.GetSystemMetrics(0) - width) // 2)
        y = max(0, (user32.GetSystemMetrics(1) - height) // 2)
        window = user32.CreateWindowExW(
            0x00000088,
            class_name,
            self.title,
            0x00C00000,
            x,
            y,
            width,
            height,
            None,
            None,
            hinstance,
            None,
        )
        if not window:
            self._ready.set()
            return
        label = user32.CreateWindowExW(
            0,
            "STATIC",
            self._initial_message,
            0x50000000,
            22,
            22,
            410,
            28,
            window,
            None,
            hinstance,
            None,
        )
        progress = user32.CreateWindowExW(
            0,
            "msctls_progress32",
            "",
            0x50000008,
            22,
            66,
            410,
            20,
            window,
            None,
            hinstance,
            None,
        )
        gui_font = gdi32.GetStockObject(17)
        user32.SendMessageW(label, 0x0030, gui_font, 1)
        user32.SendMessageW(progress, 0x040A, 1, 28)
        user32.ShowWindow(window, 5)
        user32.UpdateWindow(window)
        self._window_handle = window
        self._label_handle = label
        self._ready.set()

        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnregisterClassW(class_name, hinstance)
