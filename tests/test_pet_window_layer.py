import unittest

from tanuki_core.pet_window_layer import restore_pet_topmost


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


if __name__ == "__main__":
    unittest.main()
