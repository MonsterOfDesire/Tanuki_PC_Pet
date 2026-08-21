from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from .app_version import APP_VERSION, AppVersion
from .app_paths import get_user_data_directory
from .platform_capabilities import get_platform_capabilities
from .ui_localization import DEFAULT_UI_LOCALE, normalize_ui_locale
from .update_package import DEFAULT_EXECUTABLE_NAME


INSTALLATION_RECORD_SCHEMA_VERSION = 1
INSTALLATION_RECORD_DIRECTORY_NAME = "Tanuki_PC_Pet"
INSTALLATION_RECORD_FILE_NAME = "installation.json"


def _is_frozen_runtime():
    return "__compiled__" in globals() or getattr(sys, "frozen", False)


def _runtime_base_path():
    executable = getattr(sys, "executable", None) or sys.argv[0]
    return Path(executable).resolve().parent


def get_installation_record_path(
    local_app_data=None,
    *,
    platform=None,
    home=None,
    environ=None,
):
    if str(local_app_data or "").strip():
        data_directory = Path(local_app_data) / INSTALLATION_RECORD_DIRECTORY_NAME
    else:
        data_directory = get_user_data_directory(
            platform=platform,
            home=home,
            environ=environ,
        )
    return (
        data_directory
        / INSTALLATION_RECORD_FILE_NAME
    )


def _utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class InstallationRecord:
    install_dir: str
    version: str
    executable_name: str = DEFAULT_EXECUTABLE_NAME
    process_id: int = 0
    ui_locale: str = DEFAULT_UI_LOCALE
    updated_at: str = ""
    schema_version: int = INSTALLATION_RECORD_SCHEMA_VERSION

    @classmethod
    def from_payload(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("installation record root must be an object")
        schema_version = int(payload.get("schema_version") or 0)
        if schema_version != INSTALLATION_RECORD_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported installation record schema: {schema_version}"
            )
        install_dir = Path(str(payload.get("install_dir") or ""))
        if not install_dir.is_absolute():
            raise ValueError("installation directory must be absolute")
        executable_name = str(
            payload.get("executable_name") or DEFAULT_EXECUTABLE_NAME
        )
        if Path(executable_name).name != executable_name:
            raise ValueError("installation executable name is invalid")
        version = str(AppVersion.parse(payload.get("version")))
        return cls(
            install_dir=str(install_dir.resolve()),
            version=version,
            executable_name=executable_name,
            process_id=max(0, int(payload.get("process_id") or 0)),
            ui_locale=normalize_ui_locale(payload.get("ui_locale")),
            updated_at=str(payload.get("updated_at") or ""),
            schema_version=schema_version,
        )

    def to_payload(self):
        return asdict(self)


def load_installation_record(path=None):
    path = Path(path or get_installation_record_path())
    with open(path, "r", encoding="utf-8") as stream:
        return InstallationRecord.from_payload(json.load(stream))


def save_installation_record(record, path=None):
    if not isinstance(record, InstallationRecord):
        record = InstallationRecord.from_payload(record)
    path = Path(path or get_installation_record_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        with open(temporary_path, "w", encoding="utf-8") as stream:
            json.dump(
                record.to_payload(),
                stream,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return record


def record_current_installation(ui_locale=DEFAULT_UI_LOCALE, path=None):
    """Record only packaged runs; source checkouts are not installations."""

    if (
        not _is_frozen_runtime()
        or not get_platform_capabilities().standalone_updater
    ):
        return None
    executable_name = Path(sys.executable).name or DEFAULT_EXECUTABLE_NAME
    record = InstallationRecord(
        install_dir=str(_runtime_base_path()),
        version=str(AppVersion.parse(APP_VERSION)),
        executable_name=executable_name,
        process_id=os.getpid(),
        ui_locale=normalize_ui_locale(ui_locale),
        updated_at=_utc_timestamp(),
    )
    return save_installation_record(record, path=path)


def mark_current_installation_stopped(process_id=None, path=None):
    expected_process_id = int(process_id or os.getpid())
    try:
        record = load_installation_record(path=path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    if record.process_id != expected_process_id:
        return False
    save_installation_record(
        InstallationRecord(
            install_dir=record.install_dir,
            version=record.version,
            executable_name=record.executable_name,
            process_id=0,
            ui_locale=record.ui_locale,
            updated_at=_utc_timestamp(),
        ),
        path=path,
    )
    return True
