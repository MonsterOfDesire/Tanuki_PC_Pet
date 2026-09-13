from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tanuki_core.achievement_memory_capture import (
    AchievementMemoryCaptureService,
)


class FakeImage:
    def __init__(self):
        self.saved_paths = []

    def isNull(self):
        return False

    def save(self, path, image_format):
        self.saved_paths.append((path, image_format))
        Path(path).write_bytes(b"png")
        return True


class AchievementMemoryCaptureTests(unittest.TestCase):
    def test_capture_reuses_one_image_for_multiple_first_unlocks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image = FakeImage()
            provider_calls = []
            service = AchievementMemoryCaptureService(
                temporary_directory,
                image_provider=lambda: provider_calls.append(True) or image,
                now_provider=lambda: datetime(
                    2026,
                    9,
                    13,
                    tzinfo=timezone.utc,
                ),
            )

            saved = service.capture(
                ("race.first", "chorus.first"),
                world_mode="sandbox",
            )

            self.assertEqual(len(provider_calls), 1)
            self.assertEqual(len(saved), 2)
            self.assertTrue(all(path.is_file() for path in saved))
            self.assertTrue(
                all((path.parent / "metadata.json").is_file() for path in saved)
            )

    def test_existing_first_unlock_memory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image = FakeImage()
            service = AchievementMemoryCaptureService(
                temporary_directory,
                image_provider=lambda: image,
            )
            first = service.capture(
                ("ambient.rare",),
                world_mode="sandbox",
            )
            second = service.capture(
                ("ambient.rare",),
                world_mode="sandbox",
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(second, ())
            self.assertEqual(len(image.saved_paths), 1)
            self.assertEqual(
                service.latest_capture_path(
                    "sandbox",
                    "ambient.rare",
                ),
                first[0],
            )


if __name__ == "__main__":
    unittest.main()
