import ast
import unittest
from pathlib import Path


CORE_DIR = Path(__file__).resolve().parents[1] / "tanuki_core"
APP_RUNTIME_PATH = CORE_DIR / "app_runtime.py"


class AppRuntimeArchitectureTests(unittest.TestCase):
    def test_domain_modules_do_not_import_app_runtime(self):
        guarded_suffixes = (
            "_coordinator.py",
            "_executor.py",
            "_profiles.py",
            "_rules.py",
            "_state.py",
        )
        violations = []
        for path in sorted(CORE_DIR.glob("*.py")):
            if not path.name.endswith(guarded_suffixes):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and str(
                    node.module or ""
                ).endswith("app_runtime"):
                    violations.append(path.name)
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.endswith("app_runtime"):
                            violations.append(path.name)

        self.assertEqual(violations, [])

    def test_bootstrap_timer_and_binding_logic_live_outside_facade(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")

        self.assertNotIn("timer.timeout.connect", source)
        self.assertNotIn("dashboard.set_household_data_providers", source)
        self.assertNotIn("QTimer.singleShot", source)
        self.assertLessEqual(len(source.splitlines()), 2850)

    def test_activity_and_transformation_lifecycle_live_outside_facade(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")

        self.assertIn("ActivityRuntimeController", source)
        self.assertIn("TransformationRuntimeController", source)
        self.assertNotIn("self.race_executor.update(", source)
        self.assertNotIn("self.chorus_executor.update(", source)
        self.assertNotIn("self.sleep_executor.update(", source)
        self.assertNotIn("self.transformation_executor.update_auto(", source)
        self.assertNotIn("self.transformation_executor.request_manual_toggle(", source)
        self.assertLessEqual(len(source.splitlines()), 2350)

    def test_offer_item_scene_lifecycle_lives_outside_facade(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")

        self.assertIn("OfferItemSceneRuntimeController", source)
        self.assertNotIn("self.item_scene_coordinator.update(", source)
        self.assertNotIn("self.ground_item_coordinator.update_items(", source)
        self.assertNotIn("self.direct_hover_scene_executor.update_", source)
        self.assertNotIn("self.bottle_honey_scene_executor.update_", source)
        self.assertNotIn("self.shared_food_scene_executor.update_", source)
        self.assertLessEqual(len(source.splitlines()), 2000)

    def test_offer_animation_and_event_details_live_outside_facade(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")

        self.assertIn("OfferAnimationSupport", source)
        self.assertIn("OfferEventAdapter", source)
        self.assertNotIn("resolve_offer_hotspot_match", source)
        self.assertNotIn("get_direct_offer_preview_context", source)
        self.assertNotIn("offer_bottle_success", source)
        self.assertNotIn("build_honey_guard_metadata(", source)
        self.assertLessEqual(len(source.splitlines()), 1500)

    def test_offer_executors_use_explicit_execution_port(self):
        executor_names = (
            "direct_hover_scene_executor.py",
            "bottle_honey_scene_executor.py",
            "shared_food_scene_executor.py",
        )
        for executor_name in executor_names:
            source = (CORE_DIR / executor_name).read_text(encoding="utf-8")
            self.assertIn("adapt_offer_scene_executor", source)
            self.assertNotRegex(source, r"\bruntime\.")

        port_source = (
            CORE_DIR / "offer_scene_execution_port.py"
        ).read_text(encoding="utf-8")
        for boundary_name in (
            "OfferSceneStatePort",
            "OfferAnimationExecutionPort",
            "OfferItemExecutionPort",
            "OfferEventExecutionPort",
        ):
            self.assertIn(boundary_name, port_source)

    def test_offer_compatibility_methods_live_in_adapter(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        app_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "TanukiAppRuntime"
        )
        method_names = {
            node.name
            for node in app_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("update_offer_scene", method_names)
        self.assertNotIn("record_offer_event", method_names)
        self.assertNotIn("apply_scene_context_with_preferences", method_names)
        self.assertLessEqual(len(method_names), 50)
        self.assertLessEqual(len(source.splitlines()), 800)

    def test_final_facade_is_composition_only(self):
        source = APP_RUNTIME_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        app_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "TanukiAppRuntime"
        )
        method_names = {
            node.name
            for node in app_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("HouseholdAppAdapterMixin", source)
        self.assertIn("GameplayAppAdapterMixin", source)
        self.assertIn("GameplayRewardAdapter", source)
        self.assertNotIn("recent_household_events", method_names)
        self.assertNotIn("update_rudolf_work", method_names)
        self.assertNotIn("apply_race_mood_reward", method_names)
        self.assertLessEqual(len(method_names), 30)
        self.assertGreaterEqual(len(source.splitlines()), 400)
        self.assertLessEqual(len(source.splitlines()), 600)


if __name__ == "__main__":
    unittest.main()
