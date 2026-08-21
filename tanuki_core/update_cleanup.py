from __future__ import annotations

from pathlib import Path
import shutil


def _same_path(first, second) -> bool:
    if first is None or second is None:
        return False
    try:
        return Path(first).resolve() == Path(second).resolve()
    except (OSError, RuntimeError):
        return False


def cleanup_updater_runtime(runtime_dir, *, current_executable=None):
    """Remove relocated updater executables left by earlier runs."""

    runtime_dir = Path(runtime_dir)
    if not runtime_dir.is_dir():
        return ()
    removed = []
    for candidate in runtime_dir.glob("TanukiUpdater-*.exe"):
        if not candidate.is_file() or _same_path(
            candidate,
            current_executable,
        ):
            continue
        try:
            candidate.unlink()
        except OSError:
            continue
        removed.append(candidate)
    return tuple(removed)


def cleanup_update_downloads(updates_dir, *, keep_directory=None):
    """Clear packages from the updater-owned download directory."""

    updates_dir = Path(updates_dir)
    if not updates_dir.is_dir():
        return ()
    removed = []
    for candidate in updates_dir.iterdir():
        if _same_path(candidate, keep_directory):
            continue
        try:
            if candidate.is_dir():
                shutil.rmtree(candidate)
            elif candidate.is_file():
                candidate.unlink()
            else:
                continue
        except OSError:
            continue
        removed.append(candidate)
    return tuple(removed)


def cleanup_installation_artifacts(
    install_dir,
    *,
    keep_backup_dir=None,
):
    """Keep the newest rollback backup and remove older updater artifacts."""

    install_dir = Path(install_dir).resolve()
    parent = install_dir.parent
    if not parent.is_dir():
        return ()
    patterns = (
        f".{install_dir.name}.backup-*",
        f".{install_dir.name}.failed-update-*",
    )
    removed = []
    for pattern in patterns:
        for candidate in parent.glob(pattern):
            if not candidate.is_dir() or _same_path(
                candidate,
                keep_backup_dir,
            ):
                continue
            try:
                shutil.rmtree(candidate)
            except OSError:
                continue
            removed.append(candidate)
    return tuple(removed)
