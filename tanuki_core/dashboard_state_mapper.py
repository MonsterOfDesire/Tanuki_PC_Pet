from dataclasses import dataclass, field

from .information_center_state import (
    InformationCenterConfigState,
    information_center_config_state_to_payload,
    normalize_information_center_config_state,
)
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
    social_status_enabled: bool = False
    race_frequency: str = "normal"
    chorus_frequency: str = "normal"
    mood_climate: str = "cheerful"
    information_center: InformationCenterConfigState = field(
        default_factory=InformationCenterConfigState
    )


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


def safe_option(value, default, options):
    return str(value) if value in tuple(options or ()) else str(default)


def build_dashboard_config_state(
    *,
    world_mode,
    care_feature_enabled,
    teio_dur_idx,
    tsuyoshi_dur_idx,
    time_scale_idx,
    display_scale_idx,
    debug_enabled,
    social_status_enabled=False,
    race_frequency="normal",
    chorus_frequency="normal",
    mood_climate="cheerful",
    information_center=None,
):
    return DashboardConfigState(
        world_mode=safe_world_mode(world_mode, WORLD_MODE_OPTIONS[0]),
        care_feature_enabled=bool(care_feature_enabled),
        teio_dur_idx=int(teio_dur_idx),
        tsuyoshi_dur_idx=int(tsuyoshi_dur_idx),
        time_scale_idx=int(time_scale_idx),
        display_scale_idx=int(display_scale_idx),
        debug_enabled=bool(debug_enabled),
        social_status_enabled=bool(social_status_enabled),
        race_frequency=safe_option(
            race_frequency,
            RuntimeSettings.RACE_FREQUENCY_OPTIONS[1],
            RuntimeSettings.RACE_FREQUENCY_OPTIONS,
        ),
        chorus_frequency=safe_option(
            chorus_frequency,
            RuntimeSettings.CHORUS_FREQUENCY_OPTIONS[1],
            RuntimeSettings.CHORUS_FREQUENCY_OPTIONS,
        ),
        mood_climate=safe_option(
            mood_climate,
            RuntimeSettings.MOOD_CLIMATE_OPTIONS[0],
            RuntimeSettings.MOOD_CLIMATE_OPTIONS,
        ),
        information_center=(
            information_center
            if isinstance(information_center, InformationCenterConfigState)
            else InformationCenterConfigState()
        ),
    )


def normalize_dashboard_config_state(raw_state, defaults, option_bounds):
    default_information_center = getattr(
        defaults,
        "information_center",
        InformationCenterConfigState(),
    )
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
        social_status_enabled=bool(
            raw_state.get(
                "social_status_enabled",
                getattr(defaults, "social_status_enabled", False),
            )
        ),
        race_frequency=safe_option(
            raw_state.get(
                "race_frequency",
                getattr(defaults, "race_frequency", "normal"),
            ),
            getattr(defaults, "race_frequency", "normal"),
            RuntimeSettings.RACE_FREQUENCY_OPTIONS,
        ),
        chorus_frequency=safe_option(
            raw_state.get(
                "chorus_frequency",
                getattr(defaults, "chorus_frequency", "normal"),
            ),
            getattr(defaults, "chorus_frequency", "normal"),
            RuntimeSettings.CHORUS_FREQUENCY_OPTIONS,
        ),
        mood_climate=safe_option(
            raw_state.get(
                "mood_climate",
                getattr(defaults, "mood_climate", "cheerful"),
            ),
            getattr(defaults, "mood_climate", "cheerful"),
            RuntimeSettings.MOOD_CLIMATE_OPTIONS,
        ),
        information_center=normalize_information_center_config_state(
            raw_state.get("information_center", {}),
            defaults=default_information_center,
        ),
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
        "social_status_enabled": bool(state.social_status_enabled),
        "race_frequency": str(
            getattr(state, "race_frequency", "normal")
        ),
        "chorus_frequency": str(
            getattr(state, "chorus_frequency", "normal")
        ),
        "mood_climate": str(
            getattr(state, "mood_climate", "cheerful")
        ),
        "information_center": information_center_config_state_to_payload(
            getattr(
                state,
                "information_center",
                InformationCenterConfigState(),
            )
        ),
    }


def apply_dashboard_config_to_settings(settings_provider, state):
    settings_provider.world_mode = safe_world_mode(state.world_mode, WORLD_MODE_OPTIONS[0])
    settings_provider.care_feature_enabled = bool(state.care_feature_enabled)
    settings_provider.debug_enabled = bool(state.debug_enabled)
    settings_provider.social_status_enabled = bool(
        state.social_status_enabled
    )
    settings_provider.teio_dur_idx = int(state.teio_dur_idx)
    settings_provider.tsuyoshi_dur_idx = int(state.tsuyoshi_dur_idx)
    settings_provider.time_scale_idx = int(state.time_scale_idx)
    settings_provider.display_scale_idx = int(state.display_scale_idx)
    settings_provider.race_frequency = safe_option(
        getattr(state, "race_frequency", "normal"),
        "normal",
        RuntimeSettings.RACE_FREQUENCY_OPTIONS,
    )
    settings_provider.chorus_frequency = safe_option(
        getattr(state, "chorus_frequency", "normal"),
        "normal",
        RuntimeSettings.CHORUS_FREQUENCY_OPTIONS,
    )
    settings_provider.mood_climate = safe_option(
        getattr(state, "mood_climate", "cheerful"),
        "cheerful",
        RuntimeSettings.MOOD_CLIMATE_OPTIONS,
    )


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
