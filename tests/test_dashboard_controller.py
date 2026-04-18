import unittest

from tanuki_core.dashboard_controller import DashboardController
from tanuki_core.dashboard_presenter import DashboardButtonPresentation, DashboardDialogPresentation, DashboardStatusPresentation
from tanuki_core.dashboard_tools_actions import ValidationCheckResult


class FakeActions:
    def __init__(self):
        self.time_scales = []
        self.display_scale_calls = []
        self.social_calls = []
        self.visibility_calls = []

    def apply_time_scale(self, scale):
        self.time_scales.append(scale)

    def apply_display_scale(self, pets_dict, multiplier):
        self.display_scale_calls.append((pets_dict, multiplier))

    def apply_social_cooldowns(self, pets_dict, teio_seconds, tsuyoshi_seconds):
        self.social_calls.append((pets_dict, teio_seconds, tsuyoshi_seconds))

    def apply_pet_visibility(self, pet, checked):
        self.visibility_calls.append((pet, checked))


class FakeToolsActions:
    def __init__(self):
        self.debug_refresh_calls = []
        self.validation_calls = []

    def apply_debug_refresh(self, pets_dict):
        self.debug_refresh_calls.append(pets_dict)

    def build_validation_result(self, resource_resolver, config_store=None):
        self.validation_calls.append((resource_resolver, config_store))
        return ValidationCheckResult(report="ok", warnings=())


class FakePresenter:
    def build_debug_button(self, enabled):
        return DashboardButtonPresentation(text=f"debug-{enabled}")

    def build_shutdown_status(self):
        return DashboardStatusPresentation(
            status_text="saving",
            show_status=True,
            exit_enabled=False,
            exit_text="closing",
            force_expanded=True,
        )

    def build_validation_dialog(self, result):
        return DashboardDialogPresentation(
            title="validation",
            message=result.report,
            severity="information",
        )


class FakeShutdownController:
    def __init__(self):
        self.execute_calls = 0

    def execute(self):
        self.execute_calls += 1


class FakeDashboard:
    def __init__(self):
        self.care_feature_enabled = False
        self.debug_enabled = False
        self.teio_dur_idx = 0
        self.tsuyoshi_dur_idx = 0
        self.time_scale_options = [0.5, 1.0, 2.0]
        self.time_scale_idx = 1
        self.display_scale_options = [1.0, 1.5, 2.0]
        self.display_scale_idx = 0
        self.pets_dict = {"Tokai Teio": {"pet": object()}}
        self.resource_resolver = object()
        self.config_store = object()
        self.sync_calls = 0
        self.care_button_updates = 0
        self.debug_button_updates = 0
        self.duration_button_updates = 0
        self.time_scale_button_updates = 0
        self.display_scale_button_updates = 0
        self.save_calls = 0
        self.shutdown_presentations = []
        self.validation_presentations = []

    def sync_settings_provider(self):
        self.sync_calls += 1

    def update_care_button_text(self):
        self.care_button_updates += 1

    def update_debug_button_text(self):
        self.debug_button_updates += 1

    def update_duration_buttons(self):
        self.duration_button_updates += 1

    def update_time_scale_buttons(self):
        self.time_scale_button_updates += 1

    def update_display_scale_buttons(self):
        self.display_scale_button_updates += 1

    def schedule_save(self):
        self.save_calls += 1

    def get_time_scale(self):
        return float(self.time_scale_options[self.time_scale_idx])

    def get_display_scale_multiplier(self):
        return float(self.display_scale_options[self.display_scale_idx])

    def get_social_cooldown_seconds(self, pet_name):
        if pet_name == "Tokai Teio":
            return 5.0
        if pet_name == "Tsurumaru Tsuyoshi":
            return 20.0
        return 0.0

    def apply_shutdown_status_presentation(self, presentation):
        self.shutdown_presentations.append(presentation)

    def show_tools_dialog(self, presentation):
        self.validation_presentations.append(presentation)


class DashboardControllerTests(unittest.TestCase):
    def build_controller(self):
        self.actions = FakeActions()
        self.tools = FakeToolsActions()
        self.presenter = FakePresenter()
        self.shutdown = FakeShutdownController()
        return DashboardController(
            actions=self.actions,
            tools_actions=self.tools,
            presenter=self.presenter,
            shutdown_controller=self.shutdown,
        )

    def test_set_care_enabled_updates_state_and_saves(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.set_care_enabled(dashboard, True)

        self.assertTrue(dashboard.care_feature_enabled)
        self.assertEqual(dashboard.sync_calls, 1)
        self.assertEqual(dashboard.care_button_updates, 1)
        self.assertEqual(dashboard.save_calls, 1)

    def test_set_debug_enabled_refreshes_debug_and_saves(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.set_debug_enabled(dashboard, True)

        self.assertTrue(dashboard.debug_enabled)
        self.assertEqual(dashboard.sync_calls, 1)
        self.assertEqual(dashboard.debug_button_updates, 1)
        self.assertEqual(self.tools.debug_refresh_calls, [dashboard.pets_dict])
        self.assertEqual(dashboard.save_calls, 1)

    def test_handle_pet_toggle_delegates_visibility_and_save(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()
        pet = object()

        controller.handle_pet_toggle(dashboard, pet, False)

        self.assertEqual(self.actions.visibility_calls, [(pet, False)])
        self.assertEqual(dashboard.save_calls, 1)

    def test_set_duration_updates_index_and_applies_social_settings(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.set_duration(dashboard, "tsuyoshi", 2)

        self.assertEqual(dashboard.tsuyoshi_dur_idx, 2)
        self.assertEqual(dashboard.sync_calls, 1)
        self.assertEqual(dashboard.duration_button_updates, 1)
        self.assertEqual(self.actions.social_calls, [(dashboard.pets_dict, 5.0, 20.0)])
        self.assertEqual(dashboard.save_calls, 1)

    def test_set_time_scale_index_clamps_and_applies_scale(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.set_time_scale_index(dashboard, 9)

        self.assertEqual(dashboard.time_scale_idx, 2)
        self.assertEqual(dashboard.time_scale_button_updates, 1)
        self.assertEqual(self.actions.time_scales, [2.0])
        self.assertEqual(dashboard.save_calls, 1)

    def test_set_display_scale_index_clamps_and_applies_scale(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.set_display_scale_index(dashboard, 99)

        self.assertEqual(dashboard.display_scale_idx, 2)
        self.assertEqual(dashboard.display_scale_button_updates, 1)
        self.assertEqual(self.actions.display_scale_calls, [(dashboard.pets_dict, 2.0)])
        self.assertEqual(dashboard.save_calls, 1)

    def test_run_validation_checks_builds_and_shows_dialog(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.run_validation_checks(dashboard)

        self.assertEqual(self.tools.validation_calls, [(dashboard.resource_resolver, dashboard.config_store)])
        self.assertEqual(len(dashboard.validation_presentations), 1)
        self.assertEqual(dashboard.validation_presentations[0].title, "validation")

    def test_begin_shutdown_applies_status_then_executes_shutdown(self):
        controller = self.build_controller()
        dashboard = FakeDashboard()

        controller.begin_shutdown(dashboard)

        self.assertEqual(len(dashboard.shutdown_presentations), 1)
        self.assertEqual(dashboard.shutdown_presentations[0].status_text, "saving")
        self.assertEqual(self.shutdown.execute_calls, 1)


if __name__ == "__main__":
    unittest.main()
