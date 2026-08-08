from .dashboard_state_mapper import WORLD_MODE_OPTIONS
from .information_center_state import (
    InformationCenterConfigState,
    information_center_config_state_to_payload,
    normalize_information_center_config_state,
)
from .settings_provider import RuntimeSettings


CONFIG_SCHEMA_VERSION = 6

DEFAULT_INFORMATION_CENTER_STATE = information_center_config_state_to_payload(
    InformationCenterConfigState()
)

DEFAULT_DASHBOARD_STATE = {
    "world_mode": WORLD_MODE_OPTIONS[0],
    "care_feature_enabled": True,
    "teio_dur_idx": 3,
    "tsuyoshi_dur_idx": 2,
    "time_scale_idx": 0,
    "display_scale_idx": 0,
    "debug_enabled": False,
    "social_status_enabled": False,
    "race_frequency": "normal",
    "mood_climate": "cheerful",
    "information_center": DEFAULT_INFORMATION_CENTER_STATE,
}

ROOT_DASHBOARD_KEYS = frozenset(DEFAULT_DASHBOARD_STATE.keys())


def resolve_config_autosave_target(config_store_provider, autosave_enabled=False):
    if not autosave_enabled or not config_store_provider:
        return None
    return config_store_provider()


def build_default_config_state():
    return {"schema_version": CONFIG_SCHEMA_VERSION, "dashboard": {}, "pets": {}, "household": {}}


def coerce_config_schema_version(raw_version):
    try:
        version = int(raw_version or 1)
    except (TypeError, ValueError):
        return 1, [f"config schema_version={raw_version!r} 無法識別，已改用 1"]
    if version < 1:
        return 1, [f"config schema_version={version} 無效，已改用 1"]
    if version > CONFIG_SCHEMA_VERSION:
        return CONFIG_SCHEMA_VERSION, [f"config schema {version} 高於目前支援版本，將以 {CONFIG_SCHEMA_VERSION} 解析"]
    return version, []


def migrate_legacy_root_dashboard(raw):
    warnings = []
    migrated = dict(raw)
    if "dashboard" in migrated:
        return migrated, warnings
    legacy_dashboard = {
        key: migrated.pop(key)
        for key in list(migrated.keys())
        if key in ROOT_DASHBOARD_KEYS
    }
    if legacy_dashboard:
        migrated["dashboard"] = legacy_dashboard
        warnings.append("已將舊版 root-level dashboard 欄位搬移到 dashboard 區塊")
    return migrated, warnings


def migrate_config_state(raw):
    if not isinstance(raw, dict):
        return build_default_config_state(), ["config 根節點不是物件，已重設"], 1

    warnings = []
    migrated, migrate_warnings = migrate_legacy_root_dashboard(raw)
    warnings.extend(migrate_warnings)
    schema_version, version_warnings = coerce_config_schema_version(migrated.get("schema_version", 1))
    warnings.extend(version_warnings)
    migrated = dict(migrated)
    original_schema_version = schema_version

    if schema_version < 2:
        dashboard = migrated.get("dashboard", {})
        if isinstance(dashboard, dict) and "debug_enabled" not in dashboard:
            dashboard = dict(dashboard)
            dashboard["debug_enabled"] = DEFAULT_DASHBOARD_STATE["debug_enabled"]
            migrated["dashboard"] = dashboard
        schema_version = 2

    if schema_version < 3:
        dashboard = migrated.get("dashboard", {})
        if isinstance(dashboard, dict) and "world_mode" not in dashboard:
            dashboard = dict(dashboard)
            dashboard["world_mode"] = DEFAULT_DASHBOARD_STATE["world_mode"]
            migrated["dashboard"] = dashboard
        if "household" in migrated and not isinstance(migrated.get("household"), dict):
            warnings.append("household 區塊不是物件，已重設")
        if "household" not in migrated or not isinstance(migrated.get("household"), dict):
            migrated["household"] = {}
        schema_version = 3

    if schema_version < 4:
        dashboard = migrated.get("dashboard", {})
        if isinstance(dashboard, dict) and "information_center" not in dashboard:
            dashboard = dict(dashboard)
            dashboard["information_center"] = dict(
                DEFAULT_INFORMATION_CENTER_STATE
            )
            migrated["dashboard"] = dashboard
        schema_version = 4

    if schema_version < 5:
        dashboard = migrated.get("dashboard", {})
        if (
            isinstance(dashboard, dict)
            and "social_status_enabled" not in dashboard
        ):
            dashboard = dict(dashboard)
            dashboard["social_status_enabled"] = (
                DEFAULT_DASHBOARD_STATE["social_status_enabled"]
            )
            migrated["dashboard"] = dashboard
        schema_version = 5

    if schema_version < 6:
        dashboard = migrated.get("dashboard", {})
        if isinstance(dashboard, dict):
            dashboard = dict(dashboard)
            dashboard.setdefault(
                "race_frequency",
                DEFAULT_DASHBOARD_STATE["race_frequency"],
            )
            dashboard.setdefault(
                "mood_climate",
                DEFAULT_DASHBOARD_STATE["mood_climate"],
            )
            migrated["dashboard"] = dashboard
        schema_version = 6

    migrated["schema_version"] = CONFIG_SCHEMA_VERSION
    if original_schema_version != CONFIG_SCHEMA_VERSION:
        warnings.append(f"config schema {original_schema_version} 已升級到 {CONFIG_SCHEMA_VERSION}")
    return migrated, warnings, original_schema_version


def normalize_config_state(raw):
    migrated, warnings, _original_schema_version = migrate_config_state(raw)
    dashboard = migrated.get("dashboard", {})
    pets = migrated.get("pets", {})
    household = migrated.get("household", {})
    if not isinstance(dashboard, dict):
        dashboard = {}
        warnings.append("dashboard 區塊不是物件，已重設")
    if not isinstance(pets, dict):
        pets = {}
        warnings.append("pets 區塊不是物件，已重設")
    if not isinstance(household, dict):
        household = {}
        warnings.append("household 區塊不是物件，已重設")
    information_center = dashboard.get("information_center", {})
    if not isinstance(information_center, dict):
        information_center = {}
        warnings.append("dashboard.information_center 區塊不是物件，已重設")
    normalized_information_center = (
        information_center_config_state_to_payload(
            normalize_information_center_config_state(
                information_center,
                defaults=InformationCenterConfigState(),
            )
        )
    )

    normalized = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "dashboard": {
            "world_mode": dashboard.get("world_mode", DEFAULT_DASHBOARD_STATE["world_mode"])
            if dashboard.get("world_mode") in WORLD_MODE_OPTIONS
            else DEFAULT_DASHBOARD_STATE["world_mode"],
            "care_feature_enabled": bool(dashboard.get("care_feature_enabled", DEFAULT_DASHBOARD_STATE["care_feature_enabled"])),
            "teio_dur_idx": dashboard.get("teio_dur_idx", DEFAULT_DASHBOARD_STATE["teio_dur_idx"]),
            "tsuyoshi_dur_idx": dashboard.get("tsuyoshi_dur_idx", DEFAULT_DASHBOARD_STATE["tsuyoshi_dur_idx"]),
            "time_scale_idx": dashboard.get("time_scale_idx", DEFAULT_DASHBOARD_STATE["time_scale_idx"]),
            "display_scale_idx": dashboard.get("display_scale_idx", DEFAULT_DASHBOARD_STATE["display_scale_idx"]),
            "debug_enabled": bool(dashboard.get("debug_enabled", DEFAULT_DASHBOARD_STATE["debug_enabled"])),
            "social_status_enabled": bool(
                dashboard.get(
                    "social_status_enabled",
                    DEFAULT_DASHBOARD_STATE["social_status_enabled"],
                )
            ),
            "race_frequency": (
                dashboard.get(
                    "race_frequency",
                    DEFAULT_DASHBOARD_STATE["race_frequency"],
                )
                if dashboard.get("race_frequency")
                in RuntimeSettings.RACE_FREQUENCY_OPTIONS
                else DEFAULT_DASHBOARD_STATE["race_frequency"]
            ),
            "mood_climate": (
                dashboard.get(
                    "mood_climate",
                    DEFAULT_DASHBOARD_STATE["mood_climate"],
                )
                if dashboard.get("mood_climate")
                in RuntimeSettings.MOOD_CLIMATE_OPTIONS
                else DEFAULT_DASHBOARD_STATE["mood_climate"]
            ),
            "information_center": normalized_information_center,
        },
        "pets": {},
        "household": dict(household),
    }

    for pet_name, pet_state in pets.items():
        if not isinstance(pet_state, dict):
            warnings.append(f"{pet_name}: 狀態不是物件，已忽略")
            continue
        normalized["pets"][pet_name] = {
            "x": pet_state.get("x", 0),
            "y": pet_state.get("y", 0),
            "user_visible": bool(pet_state.get("user_visible", True)),
        }
    return normalized, warnings
