import unittest

from tanuki_core.race_event_adapter import RaceEventAdapter
from tanuki_core.race_state import RaceEvent, RaceStatisticsLedger


class RaceEventAdapterTests(unittest.TestCase):
    def test_completed_race_records_story_event_and_applies_positive_rewards(self):
        calls = []
        mood_rewards = []
        reverse_rewards = []
        event = RaceEvent(
            event_type="race_completed",
            occurred_at=50.0,
            challenger_name="Symboli Rudolf",
            opponent_name="Tokai Teio",
            winner_name="Tokai Teio",
            loser_name="Symboli Rudolf",
            activity_id="race-1",
            activity_started_at=40.0,
            race_course_key="practice_200m",
            race_nominal_meters=200,
            race_distance=842.0,
            race_direction=1,
            race_elapsed_seconds=12.4,
        )

        RaceEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
            apply_winner_mood_reward=(
                lambda name, amount: mood_rewards.append((name, amount))
            ),
            apply_reverse_relationship_reward=(
                lambda *args: reverse_rewards.append(args)
            ),
        )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["event_type"], "race_completed")
        self.assertEqual(
            calls[0]["summary"],
            "帝寶在842px、逆時鐘（朝右）的賽跑中，以12.4秒勝過魯道夫。",
        )
        self.assertEqual(calls[0]["channel"], "social")
        self.assertEqual(calls[0]["metadata"]["race_distance_px"], 842.0)
        self.assertEqual(
            calls[0]["metadata"]["race_course_key"],
            "practice_200m",
        )
        self.assertEqual(calls[0]["metadata"]["race_nominal_meters"], 200)
        self.assertTrue(calls[0]["apply_deltas"])
        self.assertEqual(calls[0]["mood_delta"], 4.0)
        self.assertEqual(
            calls[0]["relation_delta"],
            {"familiarity": 2.0, "trust": 1.0},
        )
        self.assertEqual(mood_rewards, [("Tokai Teio", 4.0)])
        self.assertEqual(
            reverse_rewards,
            [
                (
                    "Symboli Rudolf",
                    "Tokai Teio",
                    {"familiarity": 2.0, "trust": 1.0},
                    50.0,
                )
            ],
        )
        metadata = calls[0]["metadata"]
        self.assertEqual(
            metadata["activity_event_name"],
            "activity.race.completed",
        )
        self.assertEqual(metadata["activity_elapsed_seconds"], 10.0)
        self.assertEqual(metadata["race_rewards"]["loser_penalty"], 0.0)

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
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
