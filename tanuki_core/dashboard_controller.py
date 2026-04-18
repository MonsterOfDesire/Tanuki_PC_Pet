from .dashboard_actions import DashboardActions
from .dashboard_presenter import DashboardPresenter
from .dashboard_tools_actions import DashboardToolsActions
from .runtime import SIM_CLOCK, app_now
from .shutdown_controller import DashboardShutdownController


class DashboardController:
    def __init__(
        self,
        actions=None,
        tools_actions=None,
        presenter=None,
        shutdown_controller=None,
    ):
        self.actions = actions or DashboardActions(sim_clock=SIM_CLOCK, now_provider=app_now)
        self.tools_actions = tools_actions or DashboardToolsActions()
        self.presenter = presenter or DashboardPresenter()
        self.shutdown_controller = shutdown_controller or DashboardShutdownController()

    def begin_shutdown(self, dashboard):
        dashboard.apply_shutdown_status_presentation(self.presenter.build_shutdown_status())
        self.shutdown_controller.execute()

    def set_care_enabled(self, dashboard, enabled, save=True):
        dashboard.care_feature_enabled = bool(enabled)
        dashboard.sync_settings_provider()
        dashboard.update_care_button_text()
        if save:
            dashboard.schedule_save()

    def toggle_care(self, dashboard):
        self.set_care_enabled(dashboard, not dashboard.care_feature_enabled)

    def set_debug_enabled(self, dashboard, enabled, save=True):
        dashboard.debug_enabled = bool(enabled)
        dashboard.sync_settings_provider()
        dashboard.update_debug_button_text()
        self.tools_actions.apply_debug_refresh(dashboard.pets_dict)
        if save:
            dashboard.schedule_save()

    def toggle_debug(self, dashboard):
        self.set_debug_enabled(dashboard, not dashboard.debug_enabled)

    def handle_pet_toggle(self, dashboard, pet, checked):
        self.actions.apply_pet_visibility(pet, checked)
        dashboard.schedule_save()

    def set_duration(self, dashboard, char, index, save=True):
        if char == "teio":
            dashboard.teio_dur_idx = int(index)
        else:
            dashboard.tsuyoshi_dur_idx = int(index)
        dashboard.sync_settings_provider()
        dashboard.update_duration_buttons()
        self.apply_social_settings(dashboard, save=False)
        if save:
            dashboard.schedule_save()

    def set_time_scale_index(self, dashboard, index, save=True):
        dashboard.time_scale_idx = max(0, min(len(dashboard.time_scale_options) - 1, int(index)))
        dashboard.sync_settings_provider()
        dashboard.update_time_scale_buttons()
        self.actions.apply_time_scale(dashboard.get_time_scale())
        if save:
            dashboard.schedule_save()

    def set_display_scale_index(self, dashboard, index, save=True):
        dashboard.display_scale_idx = max(0, min(len(dashboard.display_scale_options) - 1, int(index)))
        dashboard.sync_settings_provider()
        dashboard.update_display_scale_buttons()
        self.apply_display_scale(dashboard, save=False)
        if save:
            dashboard.schedule_save()

    def apply_display_scale(self, dashboard, save=True):
        self.actions.apply_display_scale(dashboard.pets_dict, dashboard.get_display_scale_multiplier())
        if save:
            dashboard.schedule_save()

    def run_validation_checks(self, dashboard):
        result = self.tools_actions.build_validation_result(
            dashboard.resource_resolver,
            config_store=dashboard.config_store,
        )
        dashboard.show_tools_dialog(self.presenter.build_validation_dialog(result))

    def apply_social_settings(self, dashboard, save=True):
        self.actions.apply_social_cooldowns(
            dashboard.pets_dict,
            dashboard.get_social_cooldown_seconds("Tokai Teio"),
            dashboard.get_social_cooldown_seconds("Tsurumaru Tsuyoshi"),
        )
        if save:
            dashboard.schedule_save()
