import json
import os

from PyQt6.QtCore import QObject

from .validation import CONFIG_SCHEMA_VERSION, normalize_config_state


class ConfigStore(QObject):
    def __init__(self, config_path, clamp_pet_position):
        super().__init__()
        self.config_path = config_path
        self.clamp_pet_position = clamp_pet_position
        self.dashboard = None
        self.pets_dict = {}
        self.schema_version = CONFIG_SCHEMA_VERSION
        self.validation_warnings = []
        self.loaded_state = self.load()
        self.last_saved_payload = ""

    def load(self):
        if not os.path.exists(self.config_path):
            return {"schema_version": self.schema_version, "dashboard": {}, "pets": {}}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            normalized, warnings = normalize_config_state(data)
            self.validation_warnings = warnings
            for warning in warnings:
                print(f"config 載入提示: {warning}")
            return normalized
        except Exception as e:
            print(f"讀取 config.json 失敗 {self.config_path}: {e}")
            self.validation_warnings = [str(e)]
            return {"schema_version": self.schema_version, "dashboard": {}, "pets": {}}

    def bind(self, dashboard, pets_dict):
        self.dashboard = dashboard
        self.pets_dict = pets_dict
        dashboard.config_store = self
        self.apply_loaded_state()
        self.last_saved_payload = self.serialize_state(self.capture_state())

    def schedule_save(self):
        return

    def serialize_state(self, state):
        return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)

    def safe_index(self, value, default, size):
        try:
            index = int(value)
        except (TypeError, ValueError):
            index = default
        return max(0, min(size - 1, index))

    def apply_loaded_state(self):
        if not self.dashboard or not self.pets_dict:
            return

        dashboard_state = self.loaded_state.get("dashboard", {})
        self.dashboard.set_care_enabled(
            dashboard_state.get("care_feature_enabled", self.dashboard.care_feature_enabled),
            save=False,
        )
        self.dashboard.teio_dur_idx = self.safe_index(
            dashboard_state.get("teio_dur_idx", self.dashboard.teio_dur_idx),
            self.dashboard.teio_dur_idx,
            len(self.dashboard.teio_dur_list),
        )
        self.dashboard.tsuyoshi_dur_idx = self.safe_index(
            dashboard_state.get("tsuyoshi_dur_idx", self.dashboard.tsuyoshi_dur_idx),
            self.dashboard.tsuyoshi_dur_idx,
            len(self.dashboard.tsuyoshi_dur_list),
        )
        self.dashboard.time_scale_idx = self.safe_index(
            dashboard_state.get("time_scale_idx", self.dashboard.time_scale_idx),
            self.dashboard.time_scale_idx,
            len(self.dashboard.time_scale_options),
        )
        self.dashboard.display_scale_idx = self.safe_index(
            dashboard_state.get("display_scale_idx", self.dashboard.display_scale_idx),
            self.dashboard.display_scale_idx,
            len(self.dashboard.display_scale_options),
        )
        self.dashboard.set_debug_enabled(
            dashboard_state.get("debug_enabled", self.dashboard.debug_enabled),
            save=False,
        )
        self.dashboard.update_duration_buttons()
        self.dashboard.update_time_scale_buttons()
        self.dashboard.update_display_scale_buttons()
        self.dashboard.set_time_scale_index(self.dashboard.time_scale_idx)
        self.dashboard.apply_display_scale()
        self.dashboard.apply_social_settings()

        pets_state = self.loaded_state.get("pets", {})
        for pet_name, info in self.pets_dict.items():
            pet = info["pet"]
            state = pets_state.get(pet_name, {})
            pet.user_visible = bool(state.get("user_visible", pet.user_visible))

            x = state.get("x", pet.x())
            y = state.get("y", pet.y())
            clamped_x, clamped_y = self.clamp_pet_position(pet, x, y)
            pet.move(clamped_x, clamped_y)

            if pet.user_visible:
                pet.show()
            else:
                pet.hide()
            pet.refresh_movement_state()

            toggle_button = info.get("toggle_button")
            if toggle_button:
                toggle_button.blockSignals(True)
                toggle_button.setChecked(pet.user_visible)
                toggle_button.blockSignals(False)

    def capture_state(self):
        dashboard_state = {}
        if self.dashboard:
            dashboard_state = {
                "care_feature_enabled": bool(self.dashboard.care_feature_enabled),
                "teio_dur_idx": int(self.dashboard.teio_dur_idx),
                "tsuyoshi_dur_idx": int(self.dashboard.tsuyoshi_dur_idx),
                "time_scale_idx": int(self.dashboard.time_scale_idx),
                "display_scale_idx": int(self.dashboard.display_scale_idx),
                "debug_enabled": bool(self.dashboard.debug_enabled),
            }

        pets_state = {}
        for pet_name, info in self.pets_dict.items():
            pet = info["pet"]
            pets_state[pet_name] = {
                "x": int(pet.x()),
                "y": int(pet.y()),
                "user_visible": bool(getattr(pet, "user_visible", pet.isVisible())),
            }

        return {
            "schema_version": self.schema_version,
            "dashboard": dashboard_state,
            "pets": pets_state,
        }

    def save_now(self, force=False):
        if not self.dashboard or not self.pets_dict:
            return
        state = self.capture_state()
        payload = self.serialize_state(state)
        if not force and payload == self.last_saved_payload:
            return
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(payload)
            self.last_saved_payload = payload
        except Exception as e:
            print(f"寫入 config.json 失敗 {self.config_path}: {e}")
