from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from tanuki_core.memory_album import MemoryAlbumService


class FakeImage:
    def isNull(self):
        return False

    def save(self, path, image_format):
        Path(path).write_bytes(b"png")
        return image_format == "PNG"


class MemoryAlbumServiceTests(unittest.TestCase):
    def test_full_album_stops_capture_without_deleting_existing_photos(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(
                temporary_directory,
                now_provider=lambda: datetime(2026, 9, 13, tzinfo=timezone.utc),
            )
            service.root.mkdir(parents=True)
            for index in range(20):
                (service.root / f"20260913-120000-{index:03d}.png").write_bytes(b"old")

            path = service.capture(
                FakeImage(),
                mode="events",
                capacity=20,
                kind="race",
            )

            self.assertIsNone(path)
            self.assertEqual(len(tuple(service.root.glob("*.png"))), 20)
            self.assertTrue(service.snapshot(mode="events", capacity=20).full)

    def test_lowered_capacity_never_removes_photos_and_pauses_capture(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(temporary_directory)
            service.root.mkdir(parents=True)
            for index in range(25):
                (service.root / f"20260913-120000-{index:03d}.png").write_bytes(b"old")

            snapshot = service.snapshot(mode="random", capacity=20)
            path = service.capture(FakeImage(), mode="random", capacity=20)

            self.assertTrue(snapshot.full)
            self.assertIsNone(path)
            self.assertEqual(len(tuple(service.root.glob("*.png"))), 25)

    def test_eighty_percent_sets_near_full_warning(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(temporary_directory)
            service.root.mkdir(parents=True)
            for index in range(16):
                (service.root / f"20260913-120000-{index:03d}.png").write_bytes(b"old")

            snapshot = service.snapshot(mode="events", capacity=20)

            self.assertTrue(snapshot.near_full)
            self.assertFalse(snapshot.full)

    def test_capture_uses_datetime_only_filename_and_writes_index(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(
                temporary_directory,
                now_provider=lambda: datetime(
                    2026, 9, 13, 12, 34, 56, 789000, tzinfo=timezone.utc
                ),
            )

            path = service.capture(
                FakeImage(),
                mode="events",
                capacity=20,
                kind="chorus",
                participants=("Tokai Teio",),
            )

            self.assertEqual(path.name, "20260913-123456-789.png")
            self.assertTrue(service.index_path.is_file())
            self.assertEqual(service.snapshot(mode="events", capacity=20).count, 1)

    def test_moved_photos_stop_counting_even_if_index_still_lists_them(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(temporary_directory)
            service.root.mkdir(parents=True)
            moved_photo = service.root / "20260913-120000-000.png"
            kept_photo = service.root / "20260913-120001-000.png"
            moved_photo.write_bytes(b"png")
            kept_photo.write_bytes(b"png")
            service.index_path.write_text(
                json.dumps(
                    [
                        {"filename": moved_photo.name, "kind": "manual"},
                        {"filename": kept_photo.name, "kind": "manual"},
                    ]
                ),
                encoding="utf-8",
            )

            archive = Path(temporary_directory) / "archive"
            archive.mkdir()
            moved_photo.replace(archive / moved_photo.name)
            snapshot = service.snapshot(mode="events", capacity=20)

            self.assertEqual(snapshot.count, 1)
            self.assertEqual(snapshot.entries[0].path, kept_photo)

    def test_manual_capture_works_while_automatic_mode_is_off(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(
                temporary_directory,
                now_provider=lambda: datetime(
                    2026, 9, 13, 12, 0, tzinfo=timezone.utc
                ),
            )

            path = service.capture_manual(FakeImage(), capacity=20)

            self.assertIsNotNone(path)
            snapshot = service.snapshot(mode="off", capacity=20)
            self.assertEqual(snapshot.count, 1)
            self.assertEqual(snapshot.entries[0].kind, "manual")


if __name__ == "__main__":
    unittest.main()
