from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import time
import uuid

from .installation_registry import InstallationRecord, save_installation_record
from .update_package import extract_update_package


PRESERVED_FILE_NAMES = ("config.json",)


@dataclass(frozen=True)
class UpdateApplyResult:
    install_dir: Path
    executable_path: Path
    backup_dir: Path


def validate_installation_directory(
    install_dir,
    executable_name="TanukiPet.exe",
    *,
    require_executable=True,
):
    install_dir = Path(install_dir).resolve()
    executable_name = str(executable_name or "")
    if Path(executable_name).name != executable_name or not executable_name:
        raise ValueError("update executable name is invalid")
    if install_dir.parent == install_dir:
        raise ValueError("refusing to update a filesystem root")
    try:
        if install_dir == Path.home().resolve():
            raise ValueError("refusing to update the user home directory")
    except RuntimeError:
        pass
    if not install_dir.is_dir():
        raise ValueError(f"installation directory does not exist: {install_dir}")
    executable_path = install_dir / executable_name
    if require_executable and not executable_path.is_file():
        raise ValueError(
            f"installation directory is missing {executable_name}"
        )
    return install_dir


def is_process_running(process_id):
    process_id = int(process_id or 0)
    if process_id <= 0:
        return False
    if process_id == os.getpid():
        return True
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information,
            False,
            process_id,
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True


def process_matches_executable(process_id, executable_path):
    """Avoid treating a recycled PID as the still-running pet process."""

    process_id = int(process_id or 0)
    expected_path = Path(executable_path).resolve()
    if process_id <= 0:
        return False
    if os.name != "nt":
        return is_process_running(process_id)
    import ctypes

    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        process_query_limited_information,
        False,
        process_id,
    )
    if not handle:
        return False
    try:
        buffer_length = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(buffer_length.value)
        succeeded = ctypes.windll.kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(buffer_length),
        )
        if not succeeded:
            return True
        return Path(buffer.value).resolve() == expected_path
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def wait_for_process_exit(
    process_id,
    *,
    timeout_seconds=180.0,
    poll_interval_seconds=0.2,
    running_provider=is_process_running,
):
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    while running_provider(process_id):
        if time.monotonic() >= deadline:
            return False
        time.sleep(max(0.01, float(poll_interval_seconds)))
    return True


def _copy_preserved_files(install_dir, staging_dir):
    for file_name in PRESERVED_FILE_NAMES:
        source = install_dir / file_name
        if not source.is_file():
            continue
        destination = staging_dir / file_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _unique_sibling_path(install_dir, label):
    token = uuid.uuid4().hex[:10]
    return install_dir.parent / f".{install_dir.name}.{label}-{token}"


def apply_update_package(
    package_path,
    manifest,
    install_dir,
    *,
    installation_record_path=None,
    ui_locale="zh_TW",
):
    install_dir = validate_installation_directory(
        install_dir,
        manifest.executable_name,
    )
    staging_dir = _unique_sibling_path(install_dir, "update-staging")
    backup_dir = _unique_sibling_path(install_dir, "backup")
    swapped_old_installation = False
    try:
        extract_update_package(
            package_path,
            staging_dir,
            manifest=manifest,
        )
        _copy_preserved_files(install_dir, staging_dir)
        install_dir.rename(backup_dir)
        swapped_old_installation = True
        try:
            staging_dir.rename(install_dir)
        except Exception:
            backup_dir.rename(install_dir)
            swapped_old_installation = False
            raise
        executable_path = install_dir / manifest.executable_name
        if not executable_path.is_file():
            raise ValueError(
                f"installed update is missing {manifest.executable_name}"
            )
        save_installation_record(
            InstallationRecord(
                install_dir=str(install_dir),
                version=str(manifest.version),
                executable_name=manifest.executable_name,
                process_id=0,
                ui_locale=ui_locale,
            ),
            path=installation_record_path,
        )
        return UpdateApplyResult(
            install_dir=install_dir,
            executable_path=executable_path,
            backup_dir=backup_dir,
        )
    except Exception:
        if swapped_old_installation and backup_dir.is_dir():
            if install_dir.is_dir():
                failed_dir = _unique_sibling_path(
                    install_dir,
                    "failed-update",
                )
                install_dir.rename(failed_dir)
            backup_dir.rename(install_dir)
        raise
    finally:
        if staging_dir.is_dir():
            shutil.rmtree(staging_dir, ignore_errors=True)
