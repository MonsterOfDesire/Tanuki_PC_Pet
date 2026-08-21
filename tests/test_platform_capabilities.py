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
        self.assertEqual(capabilities.update_method, "standalone_updater")

    def test_macos_uses_explicit_limited_capabilities(self):
        capabilities = get_platform_capabilities("darwin")

        self.assertFalse(capabilities.window_perching)
        self.assertFalse(capabilities.window_to_window_flight)
        self.assertFalse(capabilities.global_mouse_listener)
        self.assertTrue(
            capabilities.keep_tool_windows_visible_when_inactive
        )
        self.assertEqual(capabilities.update_method, "manual_release")

    def test_capability_report_is_serializable_shape(self):
        report = build_capability_report("darwin")

        self.assertEqual(report["platform"], "macos")
        self.assertFalse(report["window_tracking"])
        self.assertEqual(report["update_method"], "manual_release")


if __name__ == "__main__":
    unittest.main()
