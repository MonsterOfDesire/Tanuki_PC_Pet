from pathlib import Path
import tempfile
import unittest
import zipfile

from tanuki_core.installation_registry import load_installation_record
from tanuki_core.update_installer import (
    apply_update_package,
    validate_installation_directory,
    wait_for_process_exit,
)
from tanuki_core.update_package import (
    UpdatePackageManifest,
    calculate_sha256,
)


def build_package(root, files, version="0.8.0-beta"):
    package_path = root / "TanukiPet-0.8.0-beta-windows-x64.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        for file_name, content in files.items():
            archive.writestr(file_name, content)
    manifest = UpdatePackageManifest.from_payload(
        {
            "schema_version": 1,
            "version": version,
            "executable_name": "TanukiPet.exe",
            "package": {
                "name": package_path.name,
                "url": f"https://example.test/{package_path.name}",
                "sha256": calculate_sha256(package_path),
                "size": package_path.stat().st_size,
            },
        }
    )
    return package_path, manifest


class UpdateInstallerTests(unittest.TestCase):
    def test_update_swaps_build_preserves_config_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            install_dir = root / "TanukiPet"
            install_dir.mkdir()
            (install_dir / "TanukiPet.exe").write_bytes(b"old")
            (install_dir / "config.json").write_text(
                '{"ui_locale":"ja_JP"}',
                encoding="utf-8",
            )
            package_path, manifest = build_package(
                root,
                {
                    "TanukiPet.exe": b"new",
                    "_internal/runtime.dat": b"runtime",
                },
            )
            record_path = root / "installation.json"

            result = apply_update_package(
                package_path,
                manifest,
                install_dir,
                installation_record_path=record_path,
                ui_locale="ja_JP",
            )

            self.assertEqual(
                (install_dir / "TanukiPet.exe").read_bytes(),
                b"new",
            )
            self.assertEqual(
                (install_dir / "config.json").read_text(encoding="utf-8"),
                '{"ui_locale":"ja_JP"}',
            )
            self.assertEqual(
                (result.backup_dir / "TanukiPet.exe").read_bytes(),
                b"old",
            )
            record = load_installation_record(record_path)
            self.assertEqual(record.version, "0.8.0-beta")
            self.assertEqual(record.ui_locale, "ja_JP")

    def test_invalid_package_does_not_move_existing_installation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            install_dir = root / "TanukiPet"
            install_dir.mkdir()
            executable = install_dir / "TanukiPet.exe"
            executable.write_bytes(b"old")
            package_path, manifest = build_package(
                root,
                {"readme.txt": b"missing executable"},
            )

            with self.assertRaisesRegex(ValueError, "missing TanukiPet.exe"):
                apply_update_package(
                    package_path,
                    manifest,
                    install_dir,
                    installation_record_path=root / "installation.json",
                )

            self.assertEqual(executable.read_bytes(), b"old")
            self.assertTrue(install_dir.is_dir())

    def test_wait_for_process_exit_uses_injected_status(self):
        states = iter((True, True, False))
        self.assertTrue(
            wait_for_process_exit(
                42,
                timeout_seconds=1,
                poll_interval_seconds=0.01,
                running_provider=lambda _process_id: next(states),
            )
        )

    def test_installation_must_contain_expected_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "missing TanukiPet.exe"):
                validate_installation_directory(temp_dir)


if __name__ == "__main__":
    unittest.main()
