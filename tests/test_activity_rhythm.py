import unittest
from types import SimpleNamespace

from tanuki_core.activity_rhythm import clamp_percent, format_compact_duration
from tanuki_core.app_runtime import TanukiAppRuntime
from tanuki_core.race_state import RaceScheduleState
from tanuki_core.sleep_rules import SleepScheduleState
from tanuki_core.transformation_state import PetTransformationState


class ActivityRhythmTests(unittest.TestCase):
    def test_percent_is_clamped(self):
        self.assertEqual(clamp_percent(-10), 0.0)
        self.assertEqual(clamp_percent(42.5), 42.5)
        self.assertEqual(clamp_percent(120), 100.0)

    def test_duration_uses_compact_minute_format(self):
        self.assertEqual(format_compact_duration(59.6), "1分00秒")
        self.assertEqual(format_compact_duration(125), "2分05秒")

    def test_runtime_snapshot_combines_race_sleep_and_transformation_clocks(self):
        transformation = PetTransformationState(auto_next_attempt_at=150.0)
        pet = SimpleNamespace(
            name="Tokai Teio",
            user_visible=True,
            transformation_state=transformation,
        )

        class Coordinator:
            @staticmethod
            def get_active_activities():
                return ()

            @staticmethod
            def get_activity_for_participant(_name):
                return None

        runtime = SimpleNamespace(
            activity_coordinator=Coordinator(),
            race_executor=SimpleNamespace(
                schedule=RaceScheduleState(
                    next_proposal_at=160.0,
                    last_wait_reason="cooldown",
                )
            ),
            sleep_executor=SimpleNamespace(
                schedules={
                    "Tokai Teio": SleepScheduleState(
                        next_proposal_at=200.0,
                        awake_since=40.0,
                    )
                }
            ),
            pets_list=(pet,),
        )

        snapshot = TanukiAppRuntime.get_activity_rhythm_snapshot(
            runtime,
            now=100.0,
        )

        self.assertEqual(snapshot.race_status, "cooldown")
        self.assertEqual(snapshot.race_remaining_seconds, 60.0)
        self.assertEqual(snapshot.members[0].sleepiness_percent, 37.5)
        self.assertEqual(
            snapshot.members[0].transformation_remaining_seconds,
            50.0,
        )


if __name__ == "__main__":
    unittest.main()
