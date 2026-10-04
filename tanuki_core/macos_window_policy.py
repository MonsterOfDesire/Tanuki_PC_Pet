from __future__ import annotations

from ctypes import c_void_p
import os
import sys

from PyQt6.QtCore import QEvent, QObject, QTimer
from PyQt6.QtGui import QGuiApplication


def is_cocoa_qt_platform():
    requested_platform = str(
        os.environ.get("QT_QPA_PLATFORM", "") or ""
    ).strip().lower()
    if requested_platform and requested_platform != "cocoa":
        return False
    app = QGuiApplication.instance()
    if app is None:
        return requested_platform in {"", "cocoa"}
    return str(app.platformName() or "").strip().lower() == "cocoa"


def _load_appkit_bridge():
    if sys.platform != "darwin":
        return None
    try:
        import AppKit
        import objc
    except ImportError:
        return None
    return AppKit, objc


def get_native_nswindow(widget, bridge=None):
    bridge = bridge or _load_appkit_bridge()
    if bridge is None:
        return None
    _appkit, objc = bridge
    try:
        native_view = objc.objc_object(
            c_void_p=c_void_p(int(widget.winId()))
        )
        return native_view.window()
    except Exception:
        # PyObjC can surface Objective-C exceptions while a Qt native view is
        # being replaced.  The AppKit policy is optional and must never make
        # the application fail during window construction.
        return None


def apply_macos_native_window_policy(
    widget,
    *,
    nonactivating=False,
    join_all_spaces=False,
    bridge=None,
    native_window_provider=None,
):
    bridge = bridge or _load_appkit_bridge()
    if bridge is None:
        return False
    appkit, _objc = bridge
    provider = native_window_provider or (
        lambda candidate: get_native_nswindow(candidate, bridge=bridge)
    )
    try:
        window = provider(widget)
        if window is None:
            return False

        changed = False
        if join_all_spaces:
            behavior = int(window.collectionBehavior())
            # Qt Tool windows can start with MoveToActiveSpace.  AppKit 26
            # raises NSInternalInconsistencyException if that mutually
            # exclusive flag is combined with CanJoinAllSpaces.
            move_to_active_space = int(
                getattr(
                    appkit,
                    "NSWindowCollectionBehaviorMoveToActiveSpace",
                    0,
                )
            )
            target_behavior = behavior & ~move_to_active_space
            target_behavior |= int(
                appkit.NSWindowCollectionBehaviorCanJoinAllSpaces
            )
            target_behavior |= int(
                appkit.NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            if target_behavior != behavior:
                window.setCollectionBehavior_(target_behavior)
                changed = True
            if bool(window.hidesOnDeactivate()):
                window.setHidesOnDeactivate_(False)
                changed = True

        if nonactivating:
            style_mask = int(window.styleMask())
            target_style_mask = style_mask | int(
                appkit.NSWindowStyleMaskNonactivatingPanel
            )
            if target_style_mask != style_mask:
                window.setStyleMask_(target_style_mask)
                changed = True
            set_key_only_when_needed = getattr(
                window,
                "setBecomesKeyOnlyIfNeeded_",
                None,
            )
            if callable(set_key_only_when_needed):
                set_key_only_when_needed(True)

        return changed or bool(nonactivating or join_all_spaces)
    except Exception:
        # Native window policy improves macOS integration, but the Qt window
        # remains usable without it.  A bridge or OS-policy failure must fail
        # closed instead of terminating TanukiPet before its first window.
        return False


class MacOSNativeWindowPolicyController(QObject):
    def __init__(
        self,
        widget,
        *,
        nonactivating=False,
        join_all_spaces=False,
    ):
        super().__init__(widget)
        self.widget = widget
        self.nonactivating = bool(nonactivating)
        self.join_all_spaces = bool(join_all_spaces)
        self._apply_scheduled = False
        self._applying = False
        widget.installEventFilter(self)
        # Defer native handle access until Qt has completed the current window
        # construction pass. Show/WinIdChange will also request reapplication.
        self.schedule_apply()

    def eventFilter(self, watched, event):
        if watched is self.widget and event.type() in {
            QEvent.Type.Show,
            QEvent.Type.WinIdChange,
            QEvent.Type.PlatformSurface,
        }:
            self.schedule_apply()
        return False

    def schedule_apply(self):
        if self._apply_scheduled:
            return
        self._apply_scheduled = True
        QTimer.singleShot(0, self.apply)

    def apply(self):
        self._apply_scheduled = False
        if self._applying:
            return False
        self._applying = True
        try:
            return apply_macos_native_window_policy(
                self.widget,
                nonactivating=self.nonactivating,
                join_all_spaces=self.join_all_spaces,
            )
        finally:
            self._applying = False


def install_macos_native_window_policy(
    widget,
    *,
    nonactivating=False,
    join_all_spaces=False,
):
    if (
        sys.platform != "darwin"
        or not is_cocoa_qt_platform()
        or not bool(nonactivating or join_all_spaces)
        or not callable(getattr(widget, "installEventFilter", None))
    ):
        return None
    existing = getattr(widget, "_macos_native_window_policy", None)
    if existing is not None:
        return existing
    controller = MacOSNativeWindowPolicyController(
        widget,
        nonactivating=nonactivating,
        join_all_spaces=join_all_spaces,
    )
    widget._macos_native_window_policy = controller
    return controller
