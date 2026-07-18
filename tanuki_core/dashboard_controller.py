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

    def set_world_mode(self, dashboard, world_mode, save=True):
        previous_mode = getattr(dashboard, "world_mode", "")
        if world_mode not in getattr(dashboard, "world_mode_options", ()):
            world_mode = dashboard.world_mode_options[0]
        dashboard.world_mode = str(world_mode)
        dashboard.sync_settings_provider()
        dashboard.update_world_mode_buttons()
        dashboard.update_household_control_states()
        if world_mode != previous_mode:
            dashboard.apply_world_mode_runtime_transition(world_mode, previous_mode=previous_mode)
        if save:
            dashboard.schedule_save()

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

    def open_household_summary(self, dashboard):
        presentation = self.presenter.build_household_summary(
            dashboard.get_household_state_snapshot(),
            dashboard.get_recent_household_events(limit=128),
        )
        dashboard.show_household_summary(presentation)

    def open_social_log(self, dashboard):
        presentation = self.presenter.build_social_log(
            dashboard.get_recent_household_events(limit=128),
            filter_mode=dashboard.get_social_log_filter_mode(),
            participant_name=dashboard.get_social_log_participant_name(),
        )
        dashboard.show_social_log(presentation)

    def open_relationship_table(self, dashboard):
        presentation = self.presenter.build_relationship_table(
            dashboard.get_household_state_snapshot(),
            pet_names=dashboard.get_pet_display_names(),
        )
        dashboard.show_relationship_table(presentation)

    def open_offer_tray(self, dashboard):
        dashboard.show_offer_tray()

    def donate_household_fund(self, dashboard, amount=100):
        dashboard.apply_household_fund_donation(amount=amount)
        dashboard.refresh_household_summary_if_open()
        dashboard.refresh_social_log_if_open()
        dashboard.refresh_relationship_table_if_open()

    def apply_social_settings(self, dashboard, save=True):
        self.actions.apply_social_cooldowns(
            dashboard.pets_dict,
            dashboard.get_social_cooldown_seconds("Tokai Teio"),
            dashboard.get_social_cooldown_seconds("Tsurumaru Tsuyoshi"),
        )
        if save:
            dashboard.schedule_save()
