from __future__ import annotations


TEST_SUITE_MEMBERS = {
    "assets": {
        "test_asset_loader",
        "test_asset_selection_rules",
        "test_asset_store",
        "test_manifest_rules",
    },
    "config": {
        "test_config_apply_coordinator",
        "test_config_rules",
        "test_config_save_scheduler",
        "test_config_store",
    },
    "dashboard": {
        "test_dashboard_actions",
        "test_dashboard_controller",
        "test_dashboard_presenter",
        "test_dashboard_shell_lifecycle",
        "test_dashboard_shell_rules",
        "test_dashboard_shutdown_controller",
        "test_dashboard_state_mapper",
        "test_dashboard_tools_actions",
    },
    "pet": {
        "test_pet_collision_rules",
        "test_pet_logic",
        "test_pet_overlay_renderer",
        "test_pet_physics",
        "test_pet_random_rules",
        "test_pet_runtime_state",
        "test_pet_social_catalog",
        "test_pet_social_coordinator",
        "test_pet_social_effects",
        "test_pet_social_rules",
        "test_pet_tick_coordinator",
    },
    "runtime": {
        "test_runtime_clock",
    },
    "tooling": {
        "test_tooling_lightweight_checks",
    },
    "windowing": {
        "test_pet_windowing_effects",
        "test_window_mode_rules",
        "test_window_motion",
        "test_window_perch_rules",
        "test_window_surface_rules",
        "test_window_surface_selector",
        "test_window_tracker_facade",
        "test_window_tracker_policy",
        "test_windowing_coordinator",
    },
}


def classify_test_module(module_name: str) -> str:
    module_stem = module_name.rsplit(".", 1)[-1]
    for suite_name, members in TEST_SUITE_MEMBERS.items():
        if module_stem in members:
            return suite_name
    return "uncategorized"
