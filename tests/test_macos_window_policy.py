import unittest

from tanuki_core.macos_window_policy import (
    apply_macos_native_window_policy,
)


class FakeAppKit:
    NSWindowCollectionBehaviorCanJoinAllSpaces = 1 << 0
    NSWindowCollectionBehaviorFullScreenAuxiliary = 1 << 1
    NSWindowStyleMaskNonactivatingPanel = 1 << 4


class FakeNativeWindow:
    def __init__(self):
        self.behavior = 0
        self.style_mask = 0
        self.hides_on_deactivate = True
        self.key_only_when_needed = False

    def collectionBehavior(self):
        return self.behavior

    def setCollectionBehavior_(self, value):
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
    def test_pet_policy_is_nonactivating_and_joins_all_spaces(self):
        native_window = FakeNativeWindow()

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


if __name__ == "__main__":
    unittest.main()
