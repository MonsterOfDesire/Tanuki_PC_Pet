import unittest
from unittest.mock import patch

from tanuki_core.macos_window_policy import (
    apply_macos_native_window_policy,
    is_cocoa_qt_platform,
)


class FakeAppKit:
    NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
    NSWindowCollectionBehaviorMoveToActiveSpace = 1 << 1
    NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 8
    NSWindowStyleMaskNonactivatingPanel = 1 << 4


class FakeNativeWindow:
    def __init__(self, *, behavior=0, reject_conflicting_spaces=True):
        self.behavior = int(behavior)
        self.style_mask = 0
        self.hides_on_deactivate = True
        self.key_only_when_needed = False
        self.reject_conflicting_spaces = bool(reject_conflicting_spaces)

    def collectionBehavior(self):
        return self.behavior

    def setCollectionBehavior_(self, value):
        if self.reject_conflicting_spaces and (
            int(value) & FakeAppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            and int(value)
            & FakeAppKit.NSWindowCollectionBehaviorMoveToActiveSpace
        ):
            raise RuntimeError("mutually exclusive Spaces behavior")
        self.behavior = int(value)

    def hidesOnDeactivate(self):
        return self.hides_on_deactivate

    def setHidesOnDeactivate_(self, value):
        self.hides_on_deactivate = bool(value)

    def styleMask(self):
        return self.style_mask

    def setStyleMask_(self, value):
        self.style_mask = int(value)

    def setBecomesKeyOnlyIfNeeded_(self, value):
        self.key_only_when_needed = bool(value)


class MacOSWindowPolicyTests(unittest.TestCase):
    def test_offscreen_qt_platform_never_uses_native_appkit_handles(self):
        with patch.dict(
            "os.environ",
            {"QT_QPA_PLATFORM": "offscreen"},
        ):
            self.assertFalse(is_cocoa_qt_platform())

    def test_pet_policy_is_nonactivating_and_joins_all_spaces(self):
        native_window = FakeNativeWindow(
            behavior=FakeAppKit.NSWindowCollectionBehaviorMoveToActiveSpace
        )

        applied = apply_macos_native_window_policy(
            object(),
            nonactivating=True,
            join_all_spaces=True,
            bridge=(FakeAppKit, object()),
            native_window_provider=lambda _widget: native_window,
        )

        self.assertTrue(applied)
        self.assertEqual(
            native_window.behavior,
            FakeAppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | FakeAppKit.NSWindowCollectionBehaviorFullScreenAuxiliary,
        )
        self.assertEqual(
            native_window.style_mask,
            FakeAppKit.NSWindowStyleMaskNonactivatingPanel,
        )
        self.assertFalse(native_window.hides_on_deactivate)
        self.assertTrue(native_window.key_only_when_needed)

    def test_native_policy_failure_does_not_abort_window_creation(self):
        class BrokenNativeWindow(FakeNativeWindow):
            def collectionBehavior(self):
                raise RuntimeError("native bridge unavailable")

        applied = apply_macos_native_window_policy(
            object(),
            nonactivating=True,
            join_all_spaces=True,
            bridge=(FakeAppKit, object()),
            native_window_provider=lambda _widget: BrokenNativeWindow(),
        )

        self.assertFalse(applied)


if __name__ == "__main__":
    unittest.main()
