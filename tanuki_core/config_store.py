import json
import os
import shutil
import tempfile

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
            return {"schema_version": self.schema_version, "dashboard": {}, "pets": {}, "household": {}}
        try:
            return self._load_path(self.config_path)
        except Exception as e:
            print(f"讀取 config.json 失敗 {self.config_path}: {e}")
            backup_path = self._backup_path
            if os.path.exists(backup_path):
                try:
                    recovered = self._load_path(backup_path)
                    warning = "主要設定檔損壞，已改用上一份備份"
                    self.validation_warnings.append(warning)
                    print(f"config 載入提示: {warning}")
                    return recovered
                except Exception as backup_error:
                    print(f"讀取 config 備份失敗 {backup_path}: {backup_error}")
                    self.validation_warnings = [str(e), str(backup_error)]
                    return {"schema_version": self.schema_version, "dashboard": {}, "pets": {}, "household": {}}
            self.validation_warnings = [str(e)]
            return {"schema_version": self.schema_version, "dashboard": {}, "pets": {}, "household": {}}

    @property
    def _backup_path(self):
        return f"{self.config_path}.bak"

    def _load_path(self, path):
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        normalized, warnings = normalize_config_state(data)
        self.validation_warnings = list(warnings)
        for warning in warnings:
            print(f"config 載入提示: {warning}")
        return normalized

    @staticmethod
    def _is_valid_json_file(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                json.load(handle)
            return True
        except (OSError, ValueError, TypeError):
            return False

    @staticmethod
    def _write_atomic(path, payload):
        parent_dir = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            dir=parent_dir,
            prefix=f".{os.path.basename(path)}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _backup_current_config(self):
        if not self._is_valid_json_file(self.config_path):
            return
        parent_dir = os.path.dirname(os.path.abspath(self.config_path))
        fd, temp_path = tempfile.mkstemp(
            dir=parent_dir,
            prefix=f".{os.path.basename(self._backup_path)}.",
            suffix=".tmp",
        )
        os.close(fd)
        try:
            shutil.copyfile(self.config_path, temp_path)
            with open(temp_path, "r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(temp_path, self._backup_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

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

        household_state = {}
        if self.dashboard and hasattr(self.dashboard, "capture_household_config_state"):
            household_state = self.dashboard.capture_household_config_state()

        return {
            "schema_version": self.schema_version,
            "dashboard": dashboard_state,
            "pets": pets_state,
            "household": household_state,
        }

    def save_now(self, force=False):
        if not self.dashboard or not self.pets_dict:
            return
        state = self.capture_state()
        payload = self.serialize_state(state)
        if not force and payload == self.last_saved_payload:
            return
        try:
            parent_dir = os.path.dirname(os.path.abspath(self.config_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            self._backup_current_config()
            self._write_atomic(self.config_path, payload)
            self.last_saved_payload = payload
        except Exception as e:
            print(f"寫入 config.json 失敗 {self.config_path}: {e}")
