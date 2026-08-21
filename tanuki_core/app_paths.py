from __future__ import annotations

import os
from pathlib import Path

from .platform_capabilities import (
    PLATFORM_LINUX,
    PLATFORM_MACOS,
    PLATFORM_WINDOWS,
    normalize_platform_key,
)


APP_DATA_DIRECTORY_NAME = "Tanuki_PC_Pet"
USER_DATA_DIRECTORY_ENV = "TANUKI_USER_DATA_DIR"


def get_user_data_directory(
    *,
    platform=None,
    environ=None,
    home=None,
):
    environ = os.environ if environ is None else environ
    override = str(environ.get(USER_DATA_DIRECTORY_ENV, "") or "").strip()
    if override:
        return Path(override).expanduser().resolve()

    platform_key = normalize_platform_key(platform)
    home_path = Path.home() if home is None else Path(home)
    if platform_key == PLATFORM_WINDOWS:
        local_app_data = str(environ.get("LOCALAPPDATA", "") or "").strip()
        root = Path(local_app_data) if local_app_data else home_path / "AppData" / "Local"
    elif platform_key == PLATFORM_MACOS:
        root = home_path / "Library" / "Application Support"
    elif platform_key == PLATFORM_LINUX:
        xdg_data_home = str(environ.get("XDG_DATA_HOME", "") or "").strip()
        root = Path(xdg_data_home) if xdg_data_home else home_path / ".local" / "share"
    else:
        root = home_path / ".tanuki_pc_pet"
        return root.resolve()
    return (root / APP_DATA_DIRECTORY_NAME).resolve()


def get_runtime_config_path(resource_path_provider, *, platform=None):
    platform_key = normalize_platform_key(platform)
    if (
        platform_key == PLATFORM_MACOS
        or str(os.environ.get(USER_DATA_DIRECTORY_ENV, "") or "").strip()
    ):
        return str(get_user_data_directory(platform=platform_key) / "config.json")
    return str(resource_path_provider("config.json"))
