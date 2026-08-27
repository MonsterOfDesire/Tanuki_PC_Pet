from __future__ import annotations

from ctypes import c_void_p
import sys

from PyQt6.QtCore import QEvent, QObject, QTimer


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
    except (AttributeError, TypeError, ValueError):
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
    window = provider(widget)
    if window is None:
        return False

    changed = False
    if join_all_spaces:
        behavior = int(window.collectionBehavior())
        target_behavior = behavior | int(
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
        self.apply()

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
