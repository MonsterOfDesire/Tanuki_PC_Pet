import unittest

from tanuki_core.race_event_adapter import RaceEventAdapter
from tanuki_core.race_state import RaceEvent, RaceStatisticsLedger


class RaceEventAdapterTests(unittest.TestCase):
    def test_completed_race_records_story_event_without_numeric_deltas(self):
        calls = []
        event = RaceEvent(
            event_type="race_completed",
            occurred_at=50.0,
            challenger_name="Symboli Rudolf",
            opponent_name="Tokai Teio",
            winner_name="Tokai Teio",
            loser_name="Symboli Rudolf",
            activity_id="race-1",
            race_distance=842.0,
            race_direction=1,
            race_elapsed_seconds=12.4,
        )

        RaceEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["event_type"], "race_completed")
        self.assertEqual(
            calls[0]["summary"],
            "帝寶在842px、逆時鐘（朝右）的賽跑中，以12.4秒勝過魯道夫。",
        )
        self.assertEqual(calls[0]["channel"], "social")
        self.assertEqual(calls[0]["metadata"]["race_distance_px"], 842.0)
        self.assertFalse(calls[0]["apply_deltas"])
        self.assertNotIn("mood_delta", calls[0])

    def test_declined_race_records_challenge_participants(self):
        calls = []
        event = RaceEvent(
            event_type="race_declined",
            occurred_at=30.0,
            challenger_name="Sirius Symboli",
            opponent_name="Tokai Teio",
            activity_id="race-2",
        )

        RaceEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(calls[0]["summary"], "帝寶婉拒了天狼星的賽跑挑戰。")
        self.assertEqual(calls[0]["actor_name"], "Tokai Teio")
        self.assertEqual(calls[0]["target_name"], "Sirius Symboli")

    def test_completed_race_updates_persistent_statistics_once(self):
        calls = []
        statistics = RaceStatisticsLedger()
        event = RaceEvent(
            event_type="race_completed",
            occurred_at=50.0,
            challenger_name="Symboli Rudolf",
            opponent_name="Tokai Teio",
            winner_name="Tokai Teio",
            loser_name="Symboli Rudolf",
            activity_id="race-stat-1",
            world_mode="sandbox",
        )
        adapter = RaceEventAdapter()

        adapter.apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
            race_statistics=statistics,
        )
        adapter.apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
            race_statistics=statistics,
        )

        teio = statistics.entries["Tokai Teio"]
        rudolf = statistics.entries["Symboli Rudolf"]
        self.assertEqual((teio.completed_races, teio.wins, teio.losses), (1, 1, 0))
        self.assertEqual((rudolf.completed_races, rudolf.wins, rudolf.losses), (1, 0, 1))
        self.assertEqual(teio.sandbox_races, 1)
        self.assertEqual(teio.autonomous_races, 1)


if __name__ == "__main__":
    unittest.main()
