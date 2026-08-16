import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools import build_update_package


class BuildUpdatePackageToolTests(unittest.TestCase):
    def test_builds_flat_onedir_zip_and_machine_readable_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "TanukiPet"
            source.mkdir()
            (source / "TanukiPet.exe").write_bytes(b"exe")
            (source / "_internal").mkdir()
            (source / "_internal" / "asset.dat").write_bytes(b"asset")
            output = root / "release"
            url = (
                "https://example.test/"
                "TanukiPet-0.8.0-beta-windows-x64.zip"
            )

            result = build_update_package.main(
                (
                    "--source-dir",
                    str(source),
                    "--version",
                    "0.8.0-beta",
                    "--output-dir",
                    str(output),
                    "--package-url",
                    url,
                )
            )

            self.assertEqual(result, 0)
            package = output / "TanukiPet-0.8.0-beta-windows-x64.zip"
            with zipfile.ZipFile(package, "r") as archive:
                self.assertIn("TanukiPet.exe", archive.namelist())
                self.assertIn("_internal/asset.dat", archive.namelist())
            manifest = json.loads(
                (output / "tanuki-update.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["version"], "0.8.0-beta")
            self.assertEqual(manifest["package"]["url"], url)
            self.assertEqual(
                manifest["package"]["size"],
                package.stat().st_size,
            )
            self.assertEqual(len(manifest["package"]["sha256"]), 64)

    def test_missing_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            source = Path(temporary_dir) / "empty"
            source.mkdir()
            with self.assertRaises(ValueError):
                build_update_package.build_zip(
                    source,
                    Path(temporary_dir) / "output.zip",
                )

    def test_mutable_user_config_is_not_published(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "TanukiPet"
            source.mkdir()
            (source / "TanukiPet.exe").write_bytes(b"exe")
            (source / "config.json").write_text(
                '{"private":"state"}',
                encoding="utf-8",
            )

            package = build_update_package.build_zip(
                source,
                root / "output.zip",
            )

            with zipfile.ZipFile(package, "r") as archive:
                self.assertNotIn("config.json", archive.namelist())


if __name__ == "__main__":
    unittest.main()
