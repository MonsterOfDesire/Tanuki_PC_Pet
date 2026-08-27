import unittest

from tanuki_core.platform_capabilities import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_OTHER,
    PLATFORM_WINDOWS,
    build_capability_report,
    get_platform_capabilities,
    normalize_platform_key,
)


class PlatformCapabilitiesTests(unittest.TestCase):
    def test_platform_aliases_are_normalized(self):
        self.assertEqual(normalize_platform_key("win32"), PLATFORM_WINDOWS)
        self.assertEqual(normalize_platform_key("darwin"), PLATFORM_MACOS)
        self.assertEqual(normalize_platform_key("linux2"), PLATFORM_LINUX)
        self.assertEqual(normalize_platform_key("plan9"), PLATFORM_OTHER)

    def test_windows_keeps_desktop_integration_and_updater(self):
        capabilities = get_platform_capabilities("win32")

        self.assertTrue(capabilities.window_perching)
        self.assertTrue(capabilities.window_to_window_flight)
        self.assertTrue(capabilities.global_mouse_listener)
        self.assertFalse(capabilities.precise_pet_pointer_hit_test)
        self.assertFalse(
            capabilities.pet_overlay_avoids_application_activation
        )
        self.assertFalse(capabilities.native_utility_window_chrome)
        self.assertTrue(capabilities.edge_hover_sensor)
        self.assertFalse(capabilities.alpha_pet_input_region)
        self.assertFalse(capabilities.native_pet_nonactivating_panel)
        self.assertFalse(capabilities.persistent_overlays_join_all_spaces)
        self.assertFalse(capabilities.floor_anchor_guard)
        self.assertEqual(capabilities.update_method, "standalone_updater")

    def test_macos_uses_explicit_limited_capabilities(self):
        capabilities = get_platform_capabilities("darwin")

        self.assertFalse(capabilities.window_perching)
        self.assertFalse(capabilities.window_to_window_flight)
        self.assertFalse(capabilities.global_mouse_listener)
        self.assertTrue(
            capabilities.keep_tool_windows_visible_when_inactive
        )
        self.assertTrue(capabilities.precise_pet_pointer_hit_test)
        self.assertTrue(
            capabilities.pet_overlay_avoids_application_activation
        )
        self.assertTrue(capabilities.native_utility_window_chrome)
        self.assertFalse(capabilities.edge_hover_sensor)
        self.assertTrue(capabilities.alpha_pet_input_region)
        self.assertTrue(capabilities.native_pet_nonactivating_panel)
        self.assertTrue(capabilities.persistent_overlays_join_all_spaces)
        self.assertTrue(capabilities.floor_anchor_guard)
        self.assertEqual(capabilities.update_method, "manual_release")

    def test_capability_report_is_serializable_shape(self):
        report = build_capability_report("darwin")

        self.assertEqual(report["platform"], "macos")
        self.assertFalse(report["window_tracking"])
        self.assertTrue(report["precise_pet_pointer_hit_test"])
        self.assertTrue(report["native_utility_window_chrome"])
        self.assertFalse(report["edge_hover_sensor"])
        self.assertTrue(report["alpha_pet_input_region"])
        self.assertTrue(report["native_pet_nonactivating_panel"])
        self.assertTrue(report["persistent_overlays_join_all_spaces"])
        self.assertTrue(report["floor_anchor_guard"])
        self.assertEqual(report["update_method"], "manual_release")


if __name__ == "__main__":
    unittest.main()
