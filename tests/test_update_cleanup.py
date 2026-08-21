from pathlib import Path
import tempfile
import unittest

from tanuki_core.update_cleanup import (
    cleanup_installation_artifacts,
    cleanup_update_downloads,
    cleanup_updater_runtime,
)


class UpdateCleanupTests(unittest.TestCase):
    def test_runtime_cleanup_keeps_current_relocated_executable(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            current = root / "TanukiUpdater-current.exe"
            stale = root / "TanukiUpdater-stale.exe"
            unrelated = root / "notes.txt"
            current.write_bytes(b"current")
            stale.write_bytes(b"stale")
            unrelated.write_text("keep", encoding="utf-8")

            removed = cleanup_updater_runtime(
                root,
                current_executable=current,
            )

            self.assertEqual(removed, (stale,))
            self.assertTrue(current.is_file())
            self.assertTrue(unrelated.is_file())

    def test_download_cleanup_only_operates_inside_owned_directory(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            updates = root / "updates"
            keep = updates / "0.8.0-beta"
            stale = updates / "0.7.0-beta"
            keep.mkdir(parents=True)
            stale.mkdir()
            (stale / "package.zip").write_bytes(b"old")
            outside = root / "outside.txt"
            outside.write_text("keep", encoding="utf-8")

            cleanup_update_downloads(updates, keep_directory=keep)

            self.assertTrue(keep.is_dir())
            self.assertFalse(stale.exists())
            self.assertTrue(outside.is_file())

    def test_installation_cleanup_keeps_latest_backup_only(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            install = root / "TanukiPet"
            install.mkdir()
            keep = root / ".TanukiPet.backup-new"
            stale = root / ".TanukiPet.backup-old"
            failed = root / ".TanukiPet.failed-update-old"
            unrelated = root / "TanukiPet-not-an-updater-backup"
            for directory in (keep, stale, failed, unrelated):
                directory.mkdir()

            cleanup_installation_artifacts(
                install,
                keep_backup_dir=keep,
            )

            self.assertTrue(keep.is_dir())
            self.assertFalse(stale.exists())
            self.assertFalse(failed.exists())
            self.assertTrue(unrelated.is_dir())


if __name__ == "__main__":
    unittest.main()
