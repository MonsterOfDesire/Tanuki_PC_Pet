import unittest

from tanuki_core.dashboard_tools_actions import DashboardToolsActions


class FakePet:
    def __init__(self):
        self.update_calls = 0

    def update(self):
        self.update_calls += 1


class FakeConfigStore:
    def __init__(self, config_path):
        self.config_path = config_path


class DashboardToolsActionsTests(unittest.TestCase):
    def test_apply_debug_refresh_updates_each_pet(self):
        teio = FakePet()
        rudolf = FakePet()
        actions = DashboardToolsActions()

        result = actions.apply_debug_refresh(
            {
                "Tokai Teio": {"pet": teio},
                "Symboli Rudolf": {"pet": rudolf},
                "Empty": {},
            }
        )

        self.assertEqual(teio.update_calls, 1)
        self.assertEqual(rudolf.update_calls, 1)
        self.assertEqual(result.refreshed_pet_count, 2)

    def test_build_validation_result_uses_bound_config_path_when_available(self):
        captured = []

        def fake_builder(assets_dir, config_path):
            captured.append((assets_dir, config_path))
            return "report", ["warn"]

        actions = DashboardToolsActions(validation_report_builder=fake_builder)
        result = actions.build_validation_result(
            lambda name: f"/resolved/{name}",
            config_store=FakeConfigStore("/custom/config.json"),
        )

        self.assertEqual(captured, [("/resolved/assets_cropped", "/custom/config.json")])
        self.assertEqual(result.report, "report")
        self.assertTrue(result.has_warnings)

    def test_build_validation_result_falls_back_to_resolver_config_path(self):
        captured = []

        def fake_builder(assets_dir, config_path):
            captured.append((assets_dir, config_path))
            return "ok", []

        actions = DashboardToolsActions(validation_report_builder=fake_builder)
        result = actions.build_validation_result(lambda name: f"/resolved/{name}")

        self.assertEqual(captured, [("/resolved/assets_cropped", "/resolved/config.json")])
        self.assertEqual(result.report, "ok")
        self.assertFalse(result.has_warnings)


if __name__ == "__main__":
    unittest.main()
