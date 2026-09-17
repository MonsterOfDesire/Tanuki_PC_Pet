import unittest

from tanuki_core.pet_window_layer import (
    restore_pet_group_topmost,
    restore_pet_topmost,
)


class FakeWidget:
    def __init__(self, *, visible=True, hwnd=123):
        self.visible = visible
        self.hwnd = hwnd

    def isVisible(self):
        return self.visible

    def winId(self):
        return self.hwnd


class PetWindowLayerTests(unittest.TestCase):
    def test_windows_visible_pet_is_restored_without_platform_cross_talk(self):
        calls = []
        restored = restore_pet_topmost(
            FakeWidget(),
            platform_key="windows",
            is_topmost=lambda _hwnd: False,
            set_topmost=lambda hwnd: calls.append(hwnd) or True,
        )
        self.assertTrue(restored)
        self.assertEqual(calls, [123])

    def test_existing_topmost_pet_keeps_its_relative_z_order(self):
        calls = []

        restored = restore_pet_topmost(
            FakeWidget(),
            platform_key="windows",
            is_topmost=lambda hwnd: hwnd == 123,
            set_topmost=lambda hwnd: calls.append(hwnd) or True,
        )

        self.assertTrue(restored)
        self.assertEqual(calls, [])

    def test_hidden_and_non_windows_pets_are_not_reordered(self):
        calls = []
        provider = lambda hwnd: calls.append(hwnd) or True
        self.assertFalse(
            restore_pet_topmost(
                FakeWidget(visible=False),
                platform_key="windows",
                is_topmost=lambda _hwnd: False,
                set_topmost=provider,
            )
        )
        self.assertFalse(
            restore_pet_topmost(
                FakeWidget(),
                platform_key="macos",
                set_topmost=provider,
            )
        )
        self.assertEqual(calls, [])

    def test_event_driven_group_restore_preserves_existing_peer_order(self):
        calls = []
        widgets = [
            FakeWidget(hwnd=101),
            FakeWidget(hwnd=202),
            FakeWidget(hwnd=303),
        ]

        restored = restore_pet_group_topmost(
            widgets,
            platform_key="windows",
            z_order_provider=lambda _handles: [303, 202, 101],
            set_topmost=lambda hwnd: calls.append(hwnd) or True,
        )

        self.assertTrue(restored)
        self.assertEqual(calls, [101, 202, 303])

    def test_group_restore_ignores_hidden_and_non_windows_widgets(self):
        calls = []
        self.assertFalse(
            restore_pet_group_topmost(
                [FakeWidget(visible=False)],
                platform_key="windows",
                set_topmost=lambda hwnd: calls.append(hwnd) or True,
            )
        )
        self.assertFalse(
            restore_pet_group_topmost(
                [FakeWidget()],
                platform_key="macos",
                set_topmost=lambda hwnd: calls.append(hwnd) or True,
            )
        )
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
