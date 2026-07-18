from dataclasses import dataclass

from .settings_provider import RuntimeSettings


WORLD_MODE_OPTIONS = RuntimeSettings.WORLD_MODE_OPTIONS

@dataclass(frozen=True)
class DashboardConfigState:
    world_mode: str
    care_feature_enabled: bool
    teio_dur_idx: int
    tsuyoshi_dur_idx: int
    time_scale_idx: int
    display_scale_idx: int
    debug_enabled: bool


@dataclass(frozen=True)
class DashboardOptionBounds:
    teio_duration_count: int
    tsuyoshi_duration_count: int
    time_scale_count: int
    display_scale_count: int


@dataclass(frozen=True)
class PetConfigState:
    x: int
    y: int
    user_visible: bool


def safe_index(value, default, size):
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = default
    return max(0, min(size - 1, index))


def safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def safe_world_mode(value, default):
    if value in WORLD_MODE_OPTIONS:
        return str(value)
    return str(default)


def build_dashboard_config_state(
    *,
    world_mode,
    care_feature_enabled,
    teio_dur_idx,
    tsuyoshi_dur_idx,
    time_scale_idx,
    display_scale_idx,
    debug_enabled,
):
    return DashboardConfigState(
        world_mode=safe_world_mode(world_mode, WORLD_MODE_OPTIONS[0]),
        care_feature_enabled=bool(care_feature_enabled),
        teio_dur_idx=int(teio_dur_idx),
        tsuyoshi_dur_idx=int(tsuyoshi_dur_idx),
        time_scale_idx=int(time_scale_idx),
        display_scale_idx=int(display_scale_idx),
        debug_enabled=bool(debug_enabled),
    )


def normalize_dashboard_config_state(raw_state, defaults, option_bounds):
    return DashboardConfigState(
        world_mode=safe_world_mode(raw_state.get("world_mode", defaults.world_mode), defaults.world_mode),
        care_feature_enabled=bool(raw_state.get("care_feature_enabled", defaults.care_feature_enabled)),
        teio_dur_idx=safe_index(
            raw_state.get("teio_dur_idx", defaults.teio_dur_idx),
            defaults.teio_dur_idx,
            option_bounds.teio_duration_count,
        ),
        tsuyoshi_dur_idx=safe_index(
            raw_state.get("tsuyoshi_dur_idx", defaults.tsuyoshi_dur_idx),
            defaults.tsuyoshi_dur_idx,
            option_bounds.tsuyoshi_duration_count,
        ),
        time_scale_idx=safe_index(
            raw_state.get("time_scale_idx", defaults.time_scale_idx),
            defaults.time_scale_idx,
            option_bounds.time_scale_count,
        ),
        display_scale_idx=safe_index(
            raw_state.get("display_scale_idx", defaults.display_scale_idx),
            defaults.display_scale_idx,
            option_bounds.display_scale_count,
        ),
        debug_enabled=bool(raw_state.get("debug_enabled", defaults.debug_enabled)),
    )


def dashboard_config_state_to_payload(state):
    return {
        "world_mode": str(state.world_mode),
        "care_feature_enabled": bool(state.care_feature_enabled),
        "teio_dur_idx": int(state.teio_dur_idx),
        "tsuyoshi_dur_idx": int(state.tsuyoshi_dur_idx),
        "time_scale_idx": int(state.time_scale_idx),
        "display_scale_idx": int(state.display_scale_idx),
        "debug_enabled": bool(state.debug_enabled),
    }


def apply_dashboard_config_to_settings(settings_provider, state):
    settings_provider.world_mode = safe_world_mode(state.world_mode, WORLD_MODE_OPTIONS[0])
    settings_provider.care_feature_enabled = bool(state.care_feature_enabled)
    settings_provider.debug_enabled = bool(state.debug_enabled)
    settings_provider.teio_dur_idx = int(state.teio_dur_idx)
    settings_provider.tsuyoshi_dur_idx = int(state.tsuyoshi_dur_idx)
    settings_provider.time_scale_idx = int(state.time_scale_idx)
    settings_provider.display_scale_idx = int(state.display_scale_idx)


def build_pet_config_state(*, x, y, user_visible):
    return PetConfigState(
        x=int(x),
        y=int(y),
        user_visible=bool(user_visible),
    )


def normalize_pet_config_state(raw_state, defaults):
    return PetConfigState(
        x=safe_int(raw_state.get("x", defaults.x), defaults.x),
        y=safe_int(raw_state.get("y", defaults.y), defaults.y),
        user_visible=bool(raw_state.get("user_visible", defaults.user_visible)),
    )


def pet_config_state_to_payload(state):
    return {
        "x": int(state.x),
        "y": int(state.y),
        "user_visible": bool(state.user_visible),
    }
