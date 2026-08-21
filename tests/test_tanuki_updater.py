import argparse
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import tanuki_updater
from tanuki_core.app_version import AppVersion
from tanuki_core.installation_registry import InstallationRecord
from tanuki_core.update_service import ReleaseInfo, UpdateCheckResult


class FakeProgress:
    def __init__(self, title):
        self.events = [("title", title)]

    def show(self, message):
        self.events.append(("show", message))

    def update(self, message):
        self.events.append(("update", message))

    def close(self):
        self.events.append(("close",))


class FakeUpdateClient:
    def __init__(self, release, manifest):
        self.release = release
        self.manifest = manifest

    def check_for_updates(self, **_kwargs):
        return UpdateCheckResult(
            current_version=AppVersion.parse("0.7.0-beta"),
            release=self.release,
            checked_release_count=1,
        )

    def fetch_update_manifest(self, release):
        assert release is self.release
        return self.manifest


def build_complete_release():
    return ReleaseInfo.from_github_payload(
        {
            "tag_name": "v0.8.0-beta",
            "name": "v0.8.0-beta",
            "html_url": "https://example.test/release",
            "body": "notes",
            "prerelease": True,
            "draft": False,
            "published_at": "2026-08-18T00:00:00Z",
            "assets": (
                {
                    "name": "TanukiUpdater.exe",
                    "browser_download_url": "https://example.test/updater",
                },
                {
                    "name": "tanuki-update.json",
                    "browser_download_url": "https://example.test/manifest",
                },
                {
                    "name": "TanukiPet-0.8.0-beta-windows-x64.zip",
                    "browser_download_url": "https://example.test/package",
                },
            ),
        }
    )


class TanukiUpdaterTests(unittest.TestCase):
    def build_args(self, **values):
        defaults = {
            "install_dir": None,
            "current_version": None,
            "locale": None,
            "yes": False,
            "no_restart": True,
            "relocated": False,
        }
        defaults.update(values)
        return argparse.Namespace(**defaults)

    def test_explicit_legacy_directory_uses_unknown_beta_channel(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir)
            (install_dir / "TanukiPet.exe").write_bytes(b"exe")
            args = self.build_args(install_dir=str(install_dir))
            with patch(
                "tanuki_updater.load_installation_record",
                side_effect=FileNotFoundError,
            ):
                record, legacy_selection = tanuki_updater._load_record(args)

            self.assertTrue(legacy_selection)
            self.assertEqual(
                record.version,
                tanuki_updater.UNKNOWN_INSTALLED_VERSION,
            )

    def test_registered_installation_needs_no_folder_selection(self):
        record = InstallationRecord(
            install_dir=str(Path.cwd()),
            version="0.8.0-beta",
        )
        args = self.build_args()
        with patch(
            "tanuki_updater.load_installation_record",
            return_value=record,
        ), patch(
            "tanuki_updater._browse_installation_directory"
        ) as browse:
            actual, legacy_selection = tanuki_updater._load_record(args)

        self.assertIs(actual, record)
        self.assertFalse(legacy_selection)
        browse.assert_not_called()

    def test_cancelled_first_time_folder_selection_is_reported(self):
        args = self.build_args()
        with patch(
            "tanuki_updater.load_installation_record",
            side_effect=FileNotFoundError,
        ), patch(
            "tanuki_updater._browse_installation_directory",
            return_value=None,
        ):
            with self.assertRaises(FileNotFoundError):
                tanuki_updater._load_record(args)

    def test_simplified_chinese_is_a_native_updater_locale(self):
        self.assertEqual(tanuki_updater._locale("zh_CN"), "zh_CN")
        self.assertIn(
            "正在下载更新包",
            tanuki_updater._message("zh_CN", "downloading", percent=50),
        )

    def test_self_check_needs_no_installation_or_network(self):
        with patch("tanuki_updater._load_record") as load_record:
            self.assertEqual(
                tanuki_updater.run_updater(("--self-check",)),
                0,
            )
        load_record.assert_not_called()

    def test_self_check_child_returns_without_recursive_integration(self):
        with patch.dict(
            os.environ,
            {tanuki_updater.SELF_CHECK_CHILD_ENV: "1"},
        ), patch("tanuki_updater._run_self_check") as integration:
            self.assertEqual(
                tanuki_updater.run_updater(("--self-check",)),
                0,
            )
        integration.assert_not_called()

    def test_complete_update_reports_progress_and_preserves_latest_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            install_dir = root / "TanukiPet"
            install_dir.mkdir()
            executable = install_dir / "TanukiPet.exe"
            executable.write_bytes(b"old")
            app_data = root / "LocalAppData" / "Tanuki_PC_Pet"
            record_path = app_data / "installation.json"
            package_path = root / "package.zip"
            package_path.write_bytes(b"package")
            backup_dir = root / ".TanukiPet.backup-new"
            backup_dir.mkdir()
            old_backup = root / ".TanukiPet.backup-old"
            old_backup.mkdir()
            manifest = SimpleNamespace(
                version=AppVersion.parse("0.8.0-beta"),
                size=100,
            )
            client = FakeUpdateClient(build_complete_release(), manifest)
            progress_instances = []
            shown_messages = []

            def progress_factory(title):
                progress = FakeProgress(title)
                progress_instances.append(progress)
                return progress

            def fake_download(
                _manifest,
                _download_root,
                *,
                progress_callback,
            ):
                progress_callback(50, 100)
                progress_callback(100, 100)
                return package_path

            apply_result = SimpleNamespace(
                install_dir=install_dir,
                executable_path=executable,
                backup_dir=backup_dir,
            )
            with patch(
                "tanuki_updater.load_installation_record",
                side_effect=FileNotFoundError,
            ), patch(
                "tanuki_updater.get_installation_record_path",
                return_value=record_path,
            ), patch(
                "tanuki_updater.download_update_package",
                side_effect=fake_download,
            ), patch(
                "tanuki_updater.apply_update_package",
                return_value=apply_result,
            ), patch(
                "tanuki_updater._message_box",
                side_effect=lambda text, *_args, **_kwargs: (
                    shown_messages.append(text) or True
                ),
            ):
                result = tanuki_updater.run_updater(
                    (
                        "--install-dir",
                        str(install_dir),
                        "--current-version",
                        "0.7.0-beta",
                        "--locale",
                        "zh_CN",
                        "--yes",
                        "--no-restart",
                    ),
                    client=client,
                    progress_factory=progress_factory,
                )

            self.assertEqual(result, 0)
            events = progress_instances[0].events
            self.assertIn(("show", "正在检查 GitHub Release…"), events)
            self.assertIn(("update", "正在下载更新包… 50%"), events)
            self.assertIn(("update", "正在下载更新包… 100%"), events)
            self.assertTrue(backup_dir.is_dir())
            self.assertFalse(old_backup.exists())
            self.assertTrue(any("已更新至 0.8.0-beta" in message for message in shown_messages))


if __name__ == "__main__":
    unittest.main()
