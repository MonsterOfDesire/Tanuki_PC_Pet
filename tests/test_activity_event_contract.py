import unittest

from tanuki_core.activity_event_contract import (
    ACTIVITY_EVENT_RACE_COMPLETED,
    build_activity_event_metadata,
)


class ActivityEventContractTests(unittest.TestCase):
    def test_builds_versioned_payload_with_normalized_participants(self):
        payload = build_activity_event_metadata(
            event_name=ACTIVITY_EVENT_RACE_COMPLETED,
            event_id="race-1:race_completed",
            activity_id="race-1",
            activity_kind="race",
            participants={"Tokai Teio": "challenger"},
            source="race_schedule",
            execution_mode="autonomous",
            world_mode="sandbox",
            phase="finish",
            started_at=10.0,
            ended_at=22.5,
            outcome="completed",
        )

        self.assertEqual(payload["activity_event_schema_version"], 1)
        self.assertEqual(
            payload["activity_event_name"],
            "activity.race.completed",
        )
        self.assertEqual(payload["activity_elapsed_seconds"], 12.5)
        self.assertEqual(
            payload["activity_participants"],
            [{"name": "Tokai Teio", "role": "challenger"}],
        )

    def test_unknown_event_name_is_rejected(self):
        with self.assertRaises(ValueError):
            build_activity_event_metadata(
                event_name="activity.unknown",
                activity_id="activity-1",
                activity_kind="unknown",
            )


if __name__ == "__main__":
    unittest.main()
