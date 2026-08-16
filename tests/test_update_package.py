import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tanuki_core.update_package import (
    UpdatePackageManifest,
    extract_update_package,
    verify_update_package,
)


def manifest_payload(package_path, *, digest=None, size=None):
    data = package_path.read_bytes()
    return {
        "schema_version": 1,
        "version": "0.8.0-beta",
        "executable_name": "TanukiPet.exe",
        "package": {
            "name": "TanukiPet-0.8.0-beta-windows-x64.zip",
            "url": "https://example.test/update.zip",
            "sha256": digest or hashlib.sha256(data).hexdigest(),
            "size": len(data) if size is None else size,
        },
    }


class UpdatePackageTests(unittest.TestCase):
    def test_manifest_validates_shape_and_https(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            package = Path(temporary_dir) / "update.zip"
            package.write_bytes(b"data")
            manifest = UpdatePackageManifest.from_payload(
                manifest_payload(package)
            )
            self.assertEqual(str(manifest.version), "0.8.0-beta")

            invalid = manifest_payload(package)
            invalid["package"]["url"] = "http://example.test/update.zip"
            with self.assertRaises(ValueError):
                UpdatePackageManifest.from_payload(invalid)

    def test_verifies_size_and_sha256(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            package = Path(temporary_dir) / "update.zip"
            package.write_bytes(b"verified")
            manifest = UpdatePackageManifest.from_payload(
                manifest_payload(package)
            )
            self.assertTrue(verify_update_package(package, manifest))

            wrong = UpdatePackageManifest.from_payload(
                manifest_payload(package, digest="0" * 64)
            )
            with self.assertRaises(ValueError):
                verify_update_package(package, wrong)

    def test_extracts_verified_archive_and_requires_executable(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            package = root / "update.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("TanukiPet.exe", b"binary")
                archive.writestr("_internal/data.txt", b"asset")
            manifest = UpdatePackageManifest.from_payload(
                manifest_payload(package)
            )
            destination = root / "staging"

            extract_update_package(package, destination, manifest)

            self.assertEqual(
                (destination / "_internal" / "data.txt").read_bytes(),
                b"asset",
            )

    def test_rejects_archive_path_traversal_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            package = root / "unsafe.zip"
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("../outside.txt", b"bad")
            destination = root / "staging"

            with self.assertRaises(ValueError):
                extract_update_package(package, destination)
            self.assertFalse((root / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
