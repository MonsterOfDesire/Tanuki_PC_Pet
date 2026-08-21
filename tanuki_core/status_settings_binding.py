from dataclasses import dataclass

from .update_runtime_controller import UpdateStatusSnapshot


@dataclass(frozen=True)
class StatusSettingsSnapshot:
    world_mode: str
    world_mode_options: tuple[str, ...]
    care_feature_enabled: bool
    debug_enabled: bool
    social_status_enabled: bool
    time_scale_options: tuple[float, ...]
    time_scale_index: int
    display_scale_options: tuple[float, ...]
    display_scale_index: int
    teio_duration_options: tuple[int, ...]
    teio_duration_index: int
    tsuyoshi_duration_options: tuple[int, ...]
    tsuyoshi_duration_index: int
    race_frequency: str = "normal"
    race_frequency_options: tuple[str, ...] = (
        "frequent",
        "normal",
        "occasional",
    )
    chorus_frequency: str = "normal"
    chorus_frequency_options: tuple[str, ...] = (
        "frequent",
        "normal",
        "occasional",
    )
    mood_climate: str = "cheerful"
    mood_climate_options: tuple[str, ...] = (
        "cheerful",
        "balanced",
        "expressive",
    )
    ui_locale: str = "zh_TW"
    ui_locale_options: tuple[str, ...] = (
        "zh_TW",
        "zh_CN",
        "ja_JP",
        "en_US",
    )
    update_status: str = "idle"
    update_current_version: str = ""
    update_available_version: str = ""
    update_page_url: str = ""
    update_updater_url: str = ""
    update_error_message: str = ""
    update_package_ready: bool = False


class DashboardStatusSettingsBinding:
    """Narrow adapter from the information-center controls to DashboardController paths."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def snapshot(self):
        state = self.dashboard.capture_config_state()
        update_status_provider = getattr(
            self.dashboard,
            "get_update_status_snapshot",
            None,
        )
        update_status = (
            update_status_provider()
            if callable(update_status_provider)
            else UpdateStatusSnapshot()
        )
        return StatusSettingsSnapshot(
            world_mode=str(state.world_mode),
            world_mode_options=tuple(
                str(value)
                for value in self.dashboard.world_mode_options
            ),
            care_feature_enabled=bool(state.care_feature_enabled),
            debug_enabled=bool(state.debug_enabled),
            social_status_enabled=bool(
                state.social_status_enabled
            ),
            time_scale_options=tuple(float(value) for value in self.dashboard.time_scale_options),
            time_scale_index=int(state.time_scale_idx),
            display_scale_options=tuple(float(value) for value in self.dashboard.display_scale_options),
            display_scale_index=int(state.display_scale_idx),
            teio_duration_options=tuple(int(value) for value in self.dashboard.teio_dur_list),
            teio_duration_index=int(state.teio_dur_idx),
            tsuyoshi_duration_options=tuple(int(value) for value in self.dashboard.tsuyoshi_dur_list),
            tsuyoshi_duration_index=int(state.tsuyoshi_dur_idx),
            race_frequency=str(state.race_frequency),
            race_frequency_options=tuple(
                str(value)
                for value in self.dashboard.race_frequency_options
            ),
            chorus_frequency=str(
                getattr(state, "chorus_frequency", "normal")
            ),
            chorus_frequency_options=tuple(
                str(value)
                for value in getattr(
                    self.dashboard,
                    "chorus_frequency_options",
                    ("frequent", "normal", "occasional"),
                )
            ),
            mood_climate=str(state.mood_climate),
            mood_climate_options=tuple(
                str(value)
                for value in self.dashboard.mood_climate_options
            ),
            ui_locale=str(getattr(state, "ui_locale", "zh_TW")),
            ui_locale_options=tuple(
                str(value)
                for value in getattr(
                    self.dashboard,
                    "ui_locale_options",
                    ("zh_TW", "zh_CN", "ja_JP", "en_US"),
                )
            ),
            update_status=str(update_status.state),
            update_current_version=str(update_status.current_version),
            update_available_version=str(update_status.available_version),
            update_page_url=str(update_status.release_page_url),
            update_updater_url=str(update_status.updater_download_url),
            update_error_message=str(update_status.error_message),
            update_package_ready=bool(
                update_status.update_bundle_available
            ),
        )

    def set_debug_enabled(self, enabled):
        self.dashboard.set_debug_enabled(bool(enabled))

    def set_world_mode(self, world_mode):
        self.dashboard.set_world_mode(str(world_mode))

    def set_care_feature_enabled(self, enabled):
        self.dashboard.set_care_enabled(bool(enabled))

    def set_social_status_enabled(self, enabled):
        self.dashboard.set_social_status_enabled(bool(enabled))

    def set_time_scale_index(self, index):
        self.dashboard.set_time_scale_index(int(index))

    def set_display_scale_index(self, index):
        self.dashboard.set_display_scale_index(int(index))

    def set_social_duration_index(self, character_key, index):
        if character_key not in {"teio", "tsuyoshi"}:
            raise ValueError(f"unknown social duration character: {character_key}")
        self.dashboard.set_duration(character_key, int(index))

    def set_race_frequency(self, value):
        self.dashboard.set_race_frequency(str(value))

    def set_chorus_frequency(self, value):
        self.dashboard.set_chorus_frequency(str(value))

    def set_mood_climate(self, value):
        self.dashboard.set_mood_climate(str(value))

    def set_ui_locale(self, value):
        self.dashboard.set_ui_locale(str(value))

    def check_for_updates(self):
        return self.dashboard.check_for_updates()

    def open_update_page(self):
        return self.dashboard.open_update_page()

    def run_validation_checks(self):
        self.dashboard.run_validation_checks()

    def preview_rudolf_work(self):
        return self.dashboard.preview_rudolf_work()

    def is_rudolf_work_preview_active(self):
        return bool(
            self.dashboard.is_rudolf_work_preview_active()
        )

    def preview_rudolf_teio_race(self):
        return self.dashboard.preview_rudolf_teio_race()

    def is_race_preview_active(self):
        return bool(self.dashboard.is_race_preview_active())

    def preview_chorus(self):
        return self.dashboard.preview_chorus()

    def is_chorus_preview_active(self):
        return bool(self.dashboard.is_chorus_preview_active())

    def toggle_transformation_preview(self, pet_name):
        return self.dashboard.toggle_transformation_preview(
            str(pet_name or "")
        )

    def get_transformation_preview_state(self, pet_name):
        return dict(
            self.dashboard.get_transformation_preview_state(
                str(pet_name or "")
            )
            or {}
        )

    def toggle_sleep_control(self, pet_name):
        return self.dashboard.toggle_sleep_control(str(pet_name or ""))

    def get_sleep_control_state(self, pet_name):
        return dict(
            self.dashboard.get_sleep_control_state(str(pet_name or ""))
            or {}
        )
