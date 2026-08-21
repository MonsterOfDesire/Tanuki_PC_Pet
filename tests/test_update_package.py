import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tanuki_core.update_package import (
    UpdatePackageManifest,
    download_update_package,
    extract_update_package,
    get_update_package_asset_name,
    verify_update_package,
)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


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

    def test_package_asset_name_is_shared_with_release_validation(self):
        self.assertEqual(
            get_update_package_asset_name("0.8.0-beta"),
            "TanukiPet-0.8.0-beta-windows-x64.zip",
        )

    def test_download_reports_verified_byte_progress(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            source = root / "source.zip"
            source.write_bytes(b"verified package bytes")
            manifest = UpdatePackageManifest.from_payload(
                manifest_payload(source)
            )
            progress = []

            result = download_update_package(
                manifest,
                root / "downloads",
                opener=lambda *_args, **_kwargs: FakeResponse(
                    source.read_bytes()
                ),
                progress_callback=lambda current, total: progress.append(
                    (current, total)
                ),
            )

            self.assertEqual(result.read_bytes(), source.read_bytes())
            self.assertEqual(progress[-1], (manifest.size, manifest.size))

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
