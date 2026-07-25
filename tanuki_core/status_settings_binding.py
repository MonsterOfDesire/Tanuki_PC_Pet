from dataclasses import dataclass


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


class DashboardStatusSettingsBinding:
    """Narrow adapter from the information-center controls to DashboardController paths."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def snapshot(self):
        state = self.dashboard.capture_config_state()
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

    def run_validation_checks(self):
        self.dashboard.run_validation_checks()
