from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from tanuki_core.app_version import AppVersion
from tanuki_core.installation_registry import (
    InstallationRecord,
    get_installation_record_path,
    load_installation_record,
)
from tanuki_core.update_installer import (
    apply_update_package,
    process_matches_executable,
    validate_installation_directory,
    wait_for_process_exit,
)
from tanuki_core.update_package import download_update_package
from tanuki_core.update_service import GitHubReleaseClient


UNKNOWN_INSTALLED_VERSION = "0.0.0-beta"


UPDATER_MESSAGES = {
    "zh_TW": {
        "title": "狸貓桌寵更新器",
        "not_installed": "找不到狸貓桌寵安裝位置。請先執行一次主程式，或使用 --install-dir 指定資料夾。",
        "select_install": "第一次使用更新器，請選取包含 TanukiPet.exe 的狸貓桌寵資料夾。",
        "older_version": "現有版本",
        "up_to_date": "目前已是最新版本 {version}。",
        "confirm": "將從 {current} 更新至 {latest}。更新器會下載並驗證更新包，是否繼續？",
        "close_app": "請先正常關閉狸貓桌寵，然後按下確定。更新器不會強制終止主程式。",
        "still_running": "主程式仍在執行，已取消更新。",
        "success": "已更新至 {version}。舊版已保留在：\n{backup}",
        "failure": "更新失敗，原版本未被取代或已自動回復。\n\n{reason}",
        "cancelled": "已取消更新。",
    },
    "ja_JP": {
        "title": "たぬきデスクトップペット アップデーター",
        "not_installed": "インストール先が見つかりません。先に本体を一度起動するか、--install-dir で指定してください。",
        "select_install": "初回のみ、TanukiPet.exe が入っているフォルダーを選択してください。",
        "older_version": "現在のバージョン",
        "up_to_date": "現在の {version} は最新バージョンです。",
        "confirm": "{current} から {latest} に更新します。更新パッケージをダウンロードして検証します。続行しますか？",
        "close_app": "先に本体を通常終了してから OK を押してください。アップデーターは強制終了しません。",
        "still_running": "本体がまだ実行中のため、更新を中止しました。",
        "success": "{version} に更新しました。旧バージョンのバックアップ：\n{backup}",
        "failure": "更新に失敗しました。元のバージョンは保持または復元されています。\n\n{reason}",
        "cancelled": "更新をキャンセルしました。",
    },
    "en_US": {
        "title": "Tanuki Desktop Pet Updater",
        "not_installed": "The Tanuki Desktop Pet installation was not found. Run the app once, or pass --install-dir.",
        "select_install": "For the first update, select the folder containing TanukiPet.exe.",
        "older_version": "installed version",
        "up_to_date": "Version {version} is already up to date.",
        "confirm": "Update from {current} to {latest}? The package will be downloaded and verified first.",
        "close_app": "Close Tanuki Desktop Pet normally, then select OK. The updater will not force-terminate it.",
        "still_running": "The app is still running, so the update was cancelled.",
        "success": "Updated to {version}. The previous version is kept at:\n{backup}",
        "failure": "The update failed. The previous version was preserved or restored.\n\n{reason}",
        "cancelled": "The update was cancelled.",
    },
}


def _locale(value):
    return value if value in UPDATER_MESSAGES else "zh_TW"


def _message(locale, key, **values):
    return UPDATER_MESSAGES[_locale(locale)][key].format(**values)


def _message_box(text, title, *, question=False):
    if os.name == "nt":
        import ctypes

        flags = 0x00000001 if question else 0x00000000
        result = ctypes.windll.user32.MessageBoxW(
            None,
            str(text),
            str(title),
            flags | 0x00000040,
        )
        return result == 1
    print(f"{title}: {text}")
    return True


def _browse_installation_directory(title):
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    class BrowseInfo(ctypes.Structure):
        _fields_ = (
            ("hwndOwner", wintypes.HWND),
            ("pidlRoot", ctypes.c_void_p),
            ("pszDisplayName", wintypes.LPWSTR),
            ("lpszTitle", wintypes.LPCWSTR),
            ("ulFlags", wintypes.UINT),
            ("lpfn", ctypes.c_void_p),
            ("lParam", wintypes.LPARAM),
            ("iImage", ctypes.c_int),
        )

    display_name = ctypes.create_unicode_buffer(32768)
    browse_info = BrowseInfo(
        None,
        None,
        display_name,
        str(title),
        0x00000001 | 0x00000040,
        None,
        0,
        0,
    )
    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    shell32.SHBrowseForFolderW.argtypes = (ctypes.POINTER(BrowseInfo),)
    shell32.SHBrowseForFolderW.restype = ctypes.c_void_p
    shell32.SHGetPathFromIDListW.argtypes = (
        ctypes.c_void_p,
        wintypes.LPWSTR,
    )
    shell32.SHGetPathFromIDListW.restype = wintypes.BOOL
    ole32.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    ole32.CoTaskMemFree.restype = None
    ole32.CoInitialize(None)
    try:
        item_id_list = shell32.SHBrowseForFolderW(
            ctypes.byref(browse_info)
        )
        if not item_id_list:
            return None
        try:
            selected_path = ctypes.create_unicode_buffer(32768)
            if not shell32.SHGetPathFromIDListW(
                item_id_list,
                selected_path,
            ):
                return None
            return Path(selected_path.value)
        finally:
            ole32.CoTaskMemFree(item_id_list)
    finally:
        ole32.CoUninitialize()


def _record_for_directory(install_dir, args):
    install_dir = validate_installation_directory(install_dir)
    existing_record = None
    try:
        candidate = load_installation_record()
        if Path(candidate.install_dir).resolve() == install_dir:
            existing_record = candidate
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    version = (
        args.current_version
        or (existing_record.version if existing_record else "")
        or UNKNOWN_INSTALLED_VERSION
    )
    return InstallationRecord(
        install_dir=str(install_dir),
        version=str(AppVersion.parse(version)),
        executable_name=(
            existing_record.executable_name
            if existing_record
            else "TanukiPet.exe"
        ),
        process_id=(existing_record.process_id if existing_record else 0),
        ui_locale=(
            args.locale
            or (existing_record.ui_locale if existing_record else "zh_TW")
        ),
    )


def _load_record(args):
    if args.install_dir:
        return _record_for_directory(args.install_dir, args), True
    try:
        return load_installation_record(), False
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    updater_dir = Path(
        sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
    ).resolve().parent
    if (updater_dir / "TanukiPet.exe").is_file():
        return _record_for_directory(updater_dir, args), True
    locale = _locale(args.locale)
    selected_dir = _browse_installation_directory(
        _message(locale, "select_install")
    )
    if selected_dir is None:
        raise FileNotFoundError("installation selection was cancelled")
    return _record_for_directory(selected_dir, args), True


def _relocate_if_needed(install_dir, argv):
    if not getattr(sys, "frozen", False):
        return False
    updater_path = Path(sys.executable).resolve()
    install_dir = Path(install_dir).resolve()
    try:
        updater_path.relative_to(install_dir)
    except ValueError:
        return False
    runtime_dir = (
        get_installation_record_path().parent
        / "updater-runtime"
    )
    runtime_dir.mkdir(parents=True, exist_ok=True)
    relocated_path = runtime_dir / (
        f"TanukiUpdater-{uuid.uuid4().hex[:10]}.exe"
    )
    shutil.copy2(updater_path, relocated_path)
    subprocess.Popen([str(relocated_path), *argv, "--relocated"])
    return True


def _build_parser():
    parser = argparse.ArgumentParser(description="Tanuki PC Pet updater")
    parser.add_argument("--install-dir")
    parser.add_argument("--current-version")
    parser.add_argument("--locale", choices=tuple(UPDATER_MESSAGES))
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--no-restart", action="store_true")
    parser.add_argument("--relocated", action="store_true")
    return parser


def run_updater(argv=None, *, client=None):
    args = _build_parser().parse_args(argv)
    try:
        record, legacy_selection = _load_record(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        locale = _locale(args.locale)
        title = _message(locale, "title")
        detail = _message(locale, "not_installed")
        if str(exc):
            detail = f"{detail}\n\n{exc}"
        _message_box(detail, title)
        return 2
    locale = _locale(args.locale or record.ui_locale)
    title = _message(locale, "title")
    if not args.relocated and _relocate_if_needed(record.install_dir, sys.argv[1:]):
        return 0
    try:
        current_version = AppVersion.parse(record.version)
        client = client or GitHubReleaseClient(timeout_seconds=20.0)
        check = client.check_for_updates(
            current_version=current_version,
            include_prereleases=current_version.is_prerelease,
        )
        if not check.update_available or check.release is None:
            _message_box(
                _message(locale, "up_to_date", version=current_version),
                title,
            )
            return 0
        release = check.release
        if not args.yes and not _message_box(
            _message(
                locale,
                "confirm",
                current=(
                    _message(locale, "older_version")
                    if current_version == AppVersion.parse(
                        UNKNOWN_INSTALLED_VERSION
                    )
                    else current_version
                ),
                latest=release.version,
            ),
            title,
            question=True,
        ):
            return 1
        manifest = client.fetch_update_manifest(release)
        download_root = (
            get_installation_record_path().parent
            / "updates"
            / str(manifest.version)
        )
        package_path = download_update_package(manifest, download_root)
        if record.process_id:
            if not args.yes:
                _message_box(_message(locale, "close_app"), title)
            expected_executable = (
                Path(record.install_dir) / record.executable_name
            )
            if not wait_for_process_exit(
                record.process_id,
                running_provider=lambda process_id: (
                    process_matches_executable(
                        process_id,
                        expected_executable,
                    )
                ),
            ):
                _message_box(_message(locale, "still_running"), title)
                return 3
        elif legacy_selection and not args.yes:
            _message_box(_message(locale, "close_app"), title)
        result = apply_update_package(
            package_path,
            manifest,
            record.install_dir,
            ui_locale=locale,
        )
        if not args.no_restart:
            subprocess.Popen([str(result.executable_path)])
        _message_box(
            _message(
                locale,
                "success",
                version=manifest.version,
                backup=result.backup_dir,
            ),
            title,
        )
        return 0
    except Exception as exc:
        _message_box(
            _message(locale, "failure", reason=str(exc) or type(exc).__name__),
            title,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(run_updater())
