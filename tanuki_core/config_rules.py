CONFIG_SCHEMA_VERSION = 2

DEFAULT_DASHBOARD_STATE = {
    "care_feature_enabled": True,
    "teio_dur_idx": 3,
    "tsuyoshi_dur_idx": 2,
    "time_scale_idx": 0,
    "display_scale_idx": 0,
    "debug_enabled": False,
}

ROOT_DASHBOARD_KEYS = frozenset(DEFAULT_DASHBOARD_STATE.keys())


def build_default_config_state():
    return {"schema_version": CONFIG_SCHEMA_VERSION, "dashboard": {}, "pets": {}}


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

    migrated["schema_version"] = CONFIG_SCHEMA_VERSION
    if original_schema_version != CONFIG_SCHEMA_VERSION:
        warnings.append(f"config schema {original_schema_version} 已升級到 {CONFIG_SCHEMA_VERSION}")
    return migrated, warnings, original_schema_version


def normalize_config_state(raw):
    migrated, warnings, _original_schema_version = migrate_config_state(raw)
    dashboard = migrated.get("dashboard", {})
    pets = migrated.get("pets", {})
    if not isinstance(dashboard, dict):
        dashboard = {}
        warnings.append("dashboard 區塊不是物件，已重設")
    if not isinstance(pets, dict):
        pets = {}
        warnings.append("pets 區塊不是物件，已重設")

    normalized = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "dashboard": {
            "care_feature_enabled": bool(dashboard.get("care_feature_enabled", DEFAULT_DASHBOARD_STATE["care_feature_enabled"])),
            "teio_dur_idx": dashboard.get("teio_dur_idx", DEFAULT_DASHBOARD_STATE["teio_dur_idx"]),
            "tsuyoshi_dur_idx": dashboard.get("tsuyoshi_dur_idx", DEFAULT_DASHBOARD_STATE["tsuyoshi_dur_idx"]),
            "time_scale_idx": dashboard.get("time_scale_idx", DEFAULT_DASHBOARD_STATE["time_scale_idx"]),
            "display_scale_idx": dashboard.get("display_scale_idx", DEFAULT_DASHBOARD_STATE["display_scale_idx"]),
            "debug_enabled": bool(dashboard.get("debug_enabled", DEFAULT_DASHBOARD_STATE["debug_enabled"])),
        },
        "pets": {},
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
