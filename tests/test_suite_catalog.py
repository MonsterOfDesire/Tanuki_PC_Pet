import unittest

from tests.suite_catalog import classify_test_module


class SuiteCatalogTests(unittest.TestCase):
    def test_classify_test_module_resolves_known_suite(self):
        self.assertEqual(classify_test_module("tests.test_dashboard_controller"), "dashboard")
        self.assertEqual(classify_test_module("tests.test_runtime_clock"), "runtime")
        self.assertEqual(classify_test_module("tests.test_window_tracker_facade"), "windowing")

    def test_classify_test_module_returns_uncategorized_for_unknown_module(self):
        self.assertEqual(classify_test_module("tests.test_unknown"), "uncategorized")


if __name__ == "__main__":
    unittest.main()
