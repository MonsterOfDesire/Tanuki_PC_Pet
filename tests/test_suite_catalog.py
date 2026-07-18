import unittest

from tests.suite_catalog import SHARED_FOOD_TEST_LAYERS, classify_test_module


class SuiteCatalogTests(unittest.TestCase):
    def test_classify_test_module_resolves_known_suite(self):
        self.assertEqual(classify_test_module("tests.test_dashboard_controller"), "dashboard")
        self.assertEqual(classify_test_module("tests.test_runtime_clock"), "runtime")
        self.assertEqual(classify_test_module("tests.test_window_tracker_facade"), "windowing")

    def test_classify_test_module_returns_uncategorized_for_unknown_module(self):
        self.assertEqual(classify_test_module("tests.test_unknown"), "uncategorized")

    def test_shared_food_layers_are_ordered_and_do_not_repeat_modules(self):
        self.assertEqual(tuple(SHARED_FOOD_TEST_LAYERS), ("logic", "runtime", "assets"))
        modules = tuple(
            module_name
            for layer_modules in SHARED_FOOD_TEST_LAYERS.values()
            for module_name in layer_modules
        )
        self.assertEqual(len(modules), len(set(modules)))
        self.assertIn("test_shared_food_asset_integration", SHARED_FOOD_TEST_LAYERS["assets"])


if __name__ == "__main__":
    unittest.main()
