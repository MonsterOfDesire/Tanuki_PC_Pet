from .dashboard_state_mapper import (
    build_pet_config_state,
    normalize_dashboard_config_state,
    normalize_pet_config_state,
)


class ConfigApplyCoordinator:
    def __init__(self, clamp_pet_position):
        self.clamp_pet_position = clamp_pet_position

    def apply_loaded_state(self, loaded_state, dashboard, pets_dict):
        if not dashboard or not pets_dict:
            return

        dashboard_state = normalize_dashboard_config_state(
            loaded_state.get("dashboard", {}),
            defaults=dashboard.capture_config_state(),
            option_bounds=dashboard.get_option_bounds(),
        )
        dashboard.apply_config_state(dashboard_state)
        dashboard.set_time_scale_index(dashboard.time_scale_idx, save=False)
        dashboard.apply_display_scale(save=False)
        dashboard.apply_social_settings(save=False)

        pets_state = loaded_state.get("pets", {})
        for pet_name, info in pets_dict.items():
            pet = info["pet"]
            state = normalize_pet_config_state(
                pets_state.get(pet_name, {}),
                defaults=build_pet_config_state(
                    x=pet.x(),
                    y=pet.y(),
                    user_visible=pet.user_visible,
                ),
            )
            self.apply_pet_state(
                pet=pet,
                state=state,
                toggle_button=info.get("toggle_button"),
            )

    def apply_pet_state(self, *, pet, state, toggle_button=None):
        pet.user_visible = state.user_visible

        clamped_x, clamped_y = self.clamp_pet_position(pet, state.x, state.y)
        pet.move(clamped_x, clamped_y)

        if pet.user_visible:
            pet.show()
        else:
            pet.hide()
        pet.refresh_movement_state()

        if toggle_button:
            toggle_button.blockSignals(True)
            toggle_button.setChecked(pet.user_visible)
            toggle_button.blockSignals(False)
