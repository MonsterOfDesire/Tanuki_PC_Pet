import json
import os

from .config_apply_coordinator import ConfigApplyCoordinator
from .dashboard_state_mapper import (
    build_pet_config_state,
    dashboard_config_state_to_payload,
    pet_config_state_to_payload,
)
from .validation import CONFIG_SCHEMA_VERSION, normalize_config_state


class ConfigStore:
    def __init__(self, config_path, clamp_pet_position, apply_coordinator=None):
        self.config_path = config_path
        self.clamp_pet_position = clamp_pet_position
        self.apply_coordinator = apply_coordinator or ConfigApplyCoordinator(clamp_pet_position)
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

    def serialize_state(self, state):
        return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)

    def apply_loaded_state(self):
        if not self.dashboard or not self.pets_dict:
            return
        self.apply_coordinator.apply_loaded_state(
            self.loaded_state,
            self.dashboard,
            self.pets_dict,
        )

    def capture_state(self):
        dashboard_state = {}
        if self.dashboard:
            dashboard_state = dashboard_config_state_to_payload(self.dashboard.capture_config_state())

        pets_state = {}
        for pet_name, info in self.pets_dict.items():
            pet = info["pet"]
            pets_state[pet_name] = pet_config_state_to_payload(
                build_pet_config_state(
                    x=pet.x(),
                    y=pet.y(),
                    user_visible=getattr(pet, "user_visible", pet.isVisible()),
                )
            )

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
