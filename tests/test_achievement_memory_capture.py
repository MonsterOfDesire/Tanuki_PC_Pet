from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from tanuki_core.achievement_memory_capture import (
    AchievementMemoryCaptureService,
)


class FakeImage:
    def __init__(self):
        self.saved_paths = []

    def isNull(self):
        return False

    def copy(self):
        return self

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

    def test_performing_candidate_is_used_instead_of_unlock_time_capture(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate = FakeImage()
            provider_calls = []
            service = AchievementMemoryCaptureService(
                temporary_directory,
                image_provider=lambda: provider_calls.append(True),
            )
            self.assertTrue(
                service.stage_performing_candidate(
                    "race",
                    candidate,
                    metadata={"scene_key": "race-1"},
                )
            )

            saved = service.capture(
                ("race.all_course_lengths",),
                world_mode="sandbox",
            )

            self.assertEqual(len(saved), 1)
            self.assertEqual(provider_calls, [])
            metadata = json.loads(
                (saved[0].parent / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(metadata["capture_moment"], "performing")
            self.assertEqual(metadata["scene"]["scene_key"], "race-1")

    def test_discard_performing_candidates_prevents_stale_frame_reuse(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate = FakeImage()
            fallback = FakeImage()
            provider_calls = []
            service = AchievementMemoryCaptureService(
                temporary_directory,
                image_provider=(
                    lambda: provider_calls.append(True) or fallback
                ),
            )
            service.stage_performing_candidate(
                "race",
                candidate,
                metadata={"scene_key": "speed-ineligible-race"},
            )

            service.discard_performing_candidates()
            saved = service.capture(
                ("race.first",),
                world_mode="sandbox",
            )

            self.assertEqual(len(saved), 1)
            self.assertEqual(provider_calls, [True])
            self.assertEqual(candidate.saved_paths, [])
            self.assertEqual(len(fallback.saved_paths), 1)

    def test_sleep_unlock_uses_exact_waking_session_not_latest_sleeper(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            sirius_sleeping = FakeImage()
            sirius_waking = FakeImage()
            tsuyoshi_sleeping = FakeImage()
            service = AchievementMemoryCaptureService(temporary_directory)
            service.stage_performing_candidate(
                "sleep",
                sirius_sleeping,
                metadata={
                    "activity_id": "sleep-sirius",
                    "phase": "sleeping",
                    "participants": ["Sirius Symboli"],
                },
            )
            service.stage_performing_candidate(
                "sleep",
                tsuyoshi_sleeping,
                metadata={
                    "activity_id": "sleep-tsuyoshi",
                    "phase": "sleeping",
                    "participants": ["Tsurumaru Tsuyoshi"],
                },
            )
            service.stage_performing_candidate(
                "sleep",
                sirius_waking,
                metadata={
                    "activity_id": "sleep-sirius",
                    "phase": "waking",
                    "participants": ["Sirius Symboli"],
                },
            )
            context = SimpleNamespace(
                event_name="activity.sleep.completed",
                payload={
                    "activity_id": "sleep-sirius",
                    "character_name": "Sirius Symboli",
                },
                participants=(
                    {"name": "Sirius Symboli", "role": "sleeper"},
                ),
            )

            saved = service.capture(
                ("sleep.first_natural_finish",),
                world_mode="sandbox",
                capture_context=context,
            )

            self.assertEqual(len(saved), 1)
            self.assertEqual(sirius_sleeping.saved_paths, [])
            self.assertEqual(tsuyoshi_sleeping.saved_paths, [])
            self.assertEqual(len(sirius_waking.saved_paths), 1)
            metadata = json.loads(
                (saved[0].parent / "metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(metadata["scene"]["activity_id"], "sleep-sirius")
            self.assertEqual(metadata["scene"]["phase"], "waking")

    def test_exact_context_does_not_fall_back_to_another_character(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            wrong_candidate = FakeImage()
            fallback = FakeImage()
            service = AchievementMemoryCaptureService(temporary_directory)
            service.stage_performing_candidate(
                "sleep",
                wrong_candidate,
                metadata={
                    "activity_id": "sleep-tsuyoshi",
                    "phase": "sleeping",
                    "participants": ["Tsurumaru Tsuyoshi"],
                },
            )
            context = SimpleNamespace(
                event_name="activity.sleep.completed",
                payload={
                    "activity_id": "sleep-sirius",
                    "character_name": "Sirius Symboli",
                },
                participants=(),
            )

            saved = service.capture(
                ("sleep.first_natural_finish",),
                world_mode="sandbox",
                fallback_image=fallback,
                capture_context=context,
            )

            self.assertEqual(len(saved), 1)
            self.assertEqual(wrong_candidate.saved_paths, [])
            self.assertEqual(len(fallback.saved_paths), 1)

    def test_participant_fallback_rejects_stale_same_character_frame(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            stale_candidate = FakeImage()
            fallback = FakeImage()
            service = AchievementMemoryCaptureService(temporary_directory)
            service.stage_performing_candidate(
                "transformation",
                stale_candidate,
                metadata={
                    "scene_key": "old-transformation",
                    "captured_at": 10.0,
                    "participants": ["Tokai Teio"],
                },
            )
            context = SimpleNamespace(
                event_name="activity.transformation.completed",
                occurred_at=100.0,
                payload={"character_name": "Tokai Teio"},
                participants=(),
            )

            service.capture(
                ("transformation.teio_first_autonomous",),
                world_mode="sandbox",
                fallback_image=fallback,
                capture_context=context,
            )

            self.assertEqual(stale_candidate.saved_paths, [])
            self.assertEqual(len(fallback.saved_paths), 1)

    def test_clear_capture_removes_only_one_achievement_memory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            image = FakeImage()
            service = AchievementMemoryCaptureService(
                temporary_directory,
                image_provider=lambda: image,
            )
            capture_path = service.capture(
                ("race.first",),
                world_mode="sandbox",
            )[0]
            unrelated_path = capture_path.parent / "keep.txt"
            unrelated_path.write_text("keep", encoding="utf-8")

            removed = service.clear_capture("sandbox", "race.first")

            self.assertTrue(removed)
            self.assertFalse(capture_path.exists())
            self.assertFalse((capture_path.parent / "metadata.json").exists())
            self.assertEqual(
                unrelated_path.read_text(encoding="utf-8"),
                "keep",
            )
            self.assertEqual(
                len(
                    service.capture(
                        ("race.first",),
                        world_mode="sandbox",
                    )
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
