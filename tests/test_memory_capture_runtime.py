from types import SimpleNamespace
import random
import unittest

from tanuki_core.memory_capture_runtime import MemoryCaptureRuntime


class FakeImage:
    def isNull(self):
        return False


class FakeAchievementService:
    def __init__(self):
        self.staged = []
        self.discard_count = 0

    def stage_performing_candidate(self, kind, image, *, metadata=None):
        self.staged.append((kind, image, metadata))
        return True

    def discard_performing_candidates(self):
        self.staged.clear()
        self.discard_count += 1


class FakeAlbumService:
    def __init__(self):
        self.captured = []

    def capture(self, image, **kwargs):
        self.captured.append((image, kwargs))
        return f"memory-{len(self.captured)}.png"

    def snapshot(self, **kwargs):
        return SimpleNamespace(full=False)


class FakePet:
    def __init__(self, name, *, kind="none", phase="none", activity_id=""):
        self.name = name
        self.user_visible = True
        self.activity_state = SimpleNamespace(
            activity_kind=kind,
            phase=phase,
            activity_id=activity_id,
        )
        self.transformation_state = SimpleNamespace(
            current_form="base",
            phase="idle",
            whiteness=0.0,
        )
        self.offer_scene_kind = "none"
        self.current_purpose = "idle"
        self.care_mode = "none"
        self.social_mode = "none"

    def x(self):
        return 0

    def width(self):
        return 100


class MemoryCaptureRuntimeTests(unittest.TestCase):
    def test_reset_random_schedule_starts_from_current_time(self):
        current_time = [100.0]
        runtime = MemoryCaptureRuntime(
            achievement_service=FakeAchievementService(),
            album_service=FakeAlbumService(),
            album_settings_provider=lambda: {
                "mode": "random",
                "capacity": 20,
                "achievement_enabled": False,
            },
            image_provider=lambda pets: FakeImage(),
            now_provider=lambda: current_time[0],
            rng=random.Random(7),
        )
        first_schedule = runtime._next_random_at

        current_time[0] = 300.0
        reset_schedule = runtime.reset_random_schedule()

        self.assertGreaterEqual(first_schedule, 100.0 + 8 * 60)
        self.assertLessEqual(first_schedule, 100.0 + 15 * 60)
        self.assertGreaterEqual(reset_schedule, 300.0 + 8 * 60)
        self.assertLessEqual(reset_schedule, 300.0 + 15 * 60)

    def test_random_mode_captures_daily_frame_when_schedule_is_due(self):
        current_time = [100.0]
        album = FakeAlbumService()
        runtime = MemoryCaptureRuntime(
            achievement_service=FakeAchievementService(),
            album_service=album,
            album_settings_provider=lambda: {
                "mode": "random",
                "capacity": 20,
                "achievement_enabled": False,
            },
            image_provider=lambda pets: FakeImage(),
            now_provider=lambda: current_time[0],
            rng=random.Random(11),
        )
        runtime._next_random_at = 101.0

        current_time[0] = 102.0
        saved = runtime.tick((FakePet("Tokai Teio"),))

        self.assertEqual(saved, ("memory-1.png",))
        self.assertEqual(album.captured[0][1]["kind"], "daily")
        self.assertGreater(runtime._next_random_at, current_time[0])

    def test_running_race_stages_achievement_and_album_frame_once(self):
        achievement = FakeAchievementService()
        album = FakeAlbumService()
        changed = []
        runtime = MemoryCaptureRuntime(
            achievement_service=achievement,
            album_service=album,
            album_settings_provider=lambda: {
                "mode": "events",
                "capacity": 20,
                "achievement_enabled": True,
            },
            album_changed=lambda: changed.append(True),
            image_provider=lambda pets: FakeImage(),
            now_provider=lambda: 100.0,
        )
        pets = (
            FakePet("Symboli Rudolf", kind="race", phase="running", activity_id="r1"),
            FakePet("Tokai Teio", kind="race", phase="running", activity_id="r1"),
        )

        runtime.tick(pets)
        runtime.tick(pets)

        self.assertEqual([item[0] for item in achievement.staged], ["race"])
        self.assertEqual(len(album.captured), 1)
        self.assertEqual(album.captured[0][1]["kind"], "race")
        self.assertEqual(changed, [True])

    def test_sleep_waking_replaces_exact_candidate_without_second_album_photo(self):
        achievement = FakeAchievementService()
        album = FakeAlbumService()
        runtime = MemoryCaptureRuntime(
            achievement_service=achievement,
            album_service=album,
            album_settings_provider=lambda: {
                "mode": "events",
                "capacity": 20,
                "achievement_enabled": True,
                "time_scale": 1.0,
            },
            image_provider=lambda pets: FakeImage(),
            now_provider=lambda: 100.0,
        )
        sleeper = FakePet(
            "Sirius Symboli",
            kind="sleep",
            phase="sleeping",
            activity_id="sleep-sirius",
        )

        runtime.tick((sleeper,))
        sleeper.activity_state.phase = "waking"
        runtime.tick((sleeper,))

        self.assertEqual(len(achievement.staged), 2)
        self.assertEqual(
            achievement.staged[-1][2]["activity_id"],
            "sleep-sirius",
        )
        self.assertEqual(achievement.staged[-1][2]["phase"], "waking")
        self.assertEqual(len(album.captured), 1)
        self.assertEqual(album.captured[0][1]["kind"], "sleep")

    def test_off_mode_does_not_capture_when_achievement_memory_is_disabled(self):
        achievement = FakeAchievementService()
        album = FakeAlbumService()
        runtime = MemoryCaptureRuntime(
            achievement_service=achievement,
            album_service=album,
            album_settings_provider=lambda: {
                "mode": "off",
                "capacity": 20,
                "achievement_enabled": False,
            },
            image_provider=lambda pets: FakeImage(),
            now_provider=lambda: 100.0,
        )

        runtime.tick((FakePet("Tokai Teio", kind="chorus", phase="performing", activity_id="c1"),))

        self.assertEqual(achievement.staged, [])
        self.assertEqual(album.captured, [])

    def test_non_one_x_disables_achievement_and_album_capture(self):
        achievement = FakeAchievementService()
        album = FakeAlbumService()
        image_calls = []
        runtime = MemoryCaptureRuntime(
            achievement_service=achievement,
            album_service=album,
            album_settings_provider=lambda: {
                "mode": "random",
                "capacity": 20,
                "achievement_enabled": True,
                "time_scale": 8.0,
            },
            image_provider=(
                lambda pets: image_calls.append(tuple(pets)) or FakeImage()
            ),
            now_provider=lambda: 100.0,
        )
        runtime._next_random_at = 99.0

        saved = runtime.tick((
            FakePet(
                "Tokai Teio",
                kind="chorus",
                phase="performing",
                activity_id="chorus-fast",
            ),
        ))

        self.assertEqual(saved, ())
        self.assertEqual(image_calls, [])
        self.assertEqual(achievement.staged, [])
        self.assertEqual(achievement.discard_count, 1)
        self.assertEqual(album.captured, [])

    def test_return_to_one_x_skips_fast_scene_and_restarts_random_wait(self):
        current_time = [100.0]
        settings = {
            "mode": "random",
            "capacity": 20,
            "achievement_enabled": True,
            "time_scale": 8.0,
        }
        achievement = FakeAchievementService()
        album = FakeAlbumService()
        image_calls = []
        runtime = MemoryCaptureRuntime(
            achievement_service=achievement,
            album_service=album,
            album_settings_provider=lambda: settings,
            image_provider=(
                lambda pets: image_calls.append(tuple(pets)) or FakeImage()
            ),
            now_provider=lambda: current_time[0],
            rng=random.Random(19),
        )
        runtime._next_random_at = 99.0
        pets = (
            FakePet(
                "Symboli Rudolf",
                kind="race",
                phase="running",
                activity_id="race-fast",
            ),
        )

        runtime.tick(pets)
        current_time[0] = 101.0
        settings["time_scale"] = 1.0
        saved = runtime.tick(pets)

        self.assertEqual(saved, ())
        self.assertEqual(image_calls, [])
        self.assertEqual(achievement.staged, [])
        self.assertEqual(album.captured, [])
        self.assertGreaterEqual(
            runtime._next_random_at,
            current_time[0] + 8 * 60,
        )
        self.assertLessEqual(
            runtime._next_random_at,
            current_time[0] + 15 * 60,
        )


if __name__ == "__main__":
    unittest.main()
