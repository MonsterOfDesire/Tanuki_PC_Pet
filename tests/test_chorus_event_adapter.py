import unittest

from tanuki_core.chorus_event_adapter import ChorusEventAdapter
from tanuki_core.chorus_state import ChorusEvent


class ChorusEventAdapterTests(unittest.TestCase):
    def test_completed_chorus_records_event_and_applies_rewards_once(self):
        calls = []
        mood_rewards = []
        relationship_rewards = []
        event = ChorusEvent(
            session_id="chorus-1",
            event_type="chorus_completed",
            occurred_at=30.0,
            started_at=10.0,
            source="autonomous",
            world_mode="sandbox",
            participant_roles=(
                ("Tokai Teio", "perform"),
                ("Symboli Rudolf", "perform"),
                ("Air Groove", "audience"),
            ),
            outcome="completed",
        )
        adapter = ChorusEventAdapter()

        for _repeat in range(2):
            adapter.apply(
                event,
                record_household_event=lambda **kwargs: calls.append(kwargs),
                apply_mood_reward=(
                    lambda name, amount: mood_rewards.append((name, amount))
                ),
                apply_relationship_reward=(
                    lambda actor, target, delta, now: relationship_rewards.append(
                        (actor, target, delta, now)
                    )
                ),
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["category"], "social")
        self.assertEqual(calls[0]["event_type"], "chorus_completed")
        self.assertFalse(calls[0]["apply_deltas"])
        self.assertEqual(
            calls[0]["metadata"]["activity_event_name"],
            "activity.chorus.completed",
        )
        self.assertEqual(
            mood_rewards,
            [
                ("Tokai Teio", 2.0),
                ("Symboli Rudolf", 2.0),
                ("Air Groove", 1.0),
            ],
        )
        self.assertEqual(len(relationship_rewards), 4)
        self.assertEqual(
            relationship_rewards[0],
            (
                "Tokai Teio",
                "Symboli Rudolf",
                {"familiarity": 2.0, "trust": 1.0},
                30.0,
            ),
        )

    def test_settings_preview_does_not_record_or_apply_rewards(self):
        calls = []
        rewards = []
        event = ChorusEvent(
            session_id="chorus-preview",
            event_type="chorus_completed",
            occurred_at=30.0,
            started_at=10.0,
            source="settings_preview",
            world_mode="sandbox",
            participant_roles=(("Tokai Teio", "perform"),),
            outcome="completed",
        )

        entry = ChorusEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
            apply_mood_reward=lambda *args: rewards.append(args),
            apply_relationship_reward=lambda *args: rewards.append(args),
        )

        self.assertIsNone(entry)
        self.assertEqual(calls, [])
        self.assertEqual(rewards, [])

    def test_single_performer_is_described_as_solo(self):
        calls = []
        event = ChorusEvent(
            session_id="chorus-solo",
            event_type="chorus_completed",
            occurred_at=70.0,
            started_at=10.0,
            source="autonomous",
            world_mode="sandbox",
            participant_roles=(
                ("Sirius Symboli", "perform"),
                ("Air Groove", "audience"),
            ),
            outcome="completed",
        )

        ChorusEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
        )

        self.assertIn("完成了一場獨奏", calls[0]["summary"])
        self.assertEqual(
            calls[0]["metadata"]["performance_kind"],
            "solo",
        )

    def test_single_performer_interrupt_is_described_as_solo(self):
        calls = []
        event = ChorusEvent(
            session_id="chorus-solo-stop",
            event_type="chorus_interrupted",
            occurred_at=30.0,
            started_at=10.0,
            source="autonomous",
            world_mode="sandbox",
            participant_roles=(("Symboli Rudolf", "perform"),),
            outcome="interrupted",
            reason="child_care_needed",
        )

        ChorusEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
        )

        self.assertTrue(calls[0]["summary"].startswith("獨奏因"))

    def test_child_care_interrupt_uses_generic_child_summary(self):
        calls = []
        event = ChorusEvent(
            session_id="chorus-care",
            event_type="chorus_interrupted",
            occurred_at=30.0,
            started_at=10.0,
            source="autonomous",
            world_mode="sandbox",
            participant_roles=(("Symboli Rudolf", "perform"),),
            outcome="interrupted",
            reason="child_care_needed",
        )

        ChorusEventAdapter().apply(
            event,
            record_household_event=lambda **kwargs: calls.append(kwargs),
        )

        self.assertEqual(len(calls), 1)
        self.assertIn("有小孩需要照護", calls[0]["summary"])
        self.assertEqual(
            calls[0]["metadata"]["activity_reason"],
            "child_care_needed",
        )


if __name__ == "__main__":
    unittest.main()
