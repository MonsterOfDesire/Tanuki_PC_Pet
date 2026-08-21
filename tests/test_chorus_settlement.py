import unittest

from tanuki_core.chorus_settlement import build_chorus_settlement_plan
from tanuki_core.chorus_state import ChorusEvent


def build_event(*, event_type="chorus_completed", source="autonomous"):
    return ChorusEvent(
        session_id="chorus-settlement",
        event_type=event_type,
        occurred_at=80.0,
        started_at=20.0,
        source=source,
        world_mode="sandbox",
        participant_roles=(
            ("Tokai Teio", "perform"),
            ("Symboli Rudolf", "perform"),
            ("Air Groove", "audience"),
        ),
        outcome="completed" if event_type == "chorus_completed" else "interrupted",
    )


class ChorusSettlementTests(unittest.TestCase):
    def test_natural_completion_rewards_current_performers_and_audience(self):
        plan = build_chorus_settlement_plan(build_event())

        self.assertEqual(
            tuple(
                (reward.character_name, reward.amount)
                for reward in plan.mood_rewards
            ),
            (
                ("Tokai Teio", 2.0),
                ("Symboli Rudolf", 2.0),
                ("Air Groove", 1.0),
            ),
        )
        self.assertEqual(
            tuple(
                (
                    reward.actor_name,
                    reward.target_name,
                    reward.familiarity,
                    reward.trust,
                )
                for reward in plan.relationship_rewards
            ),
            (
                ("Tokai Teio", "Symboli Rudolf", 2.0, 1.0),
                ("Symboli Rudolf", "Tokai Teio", 2.0, 1.0),
                ("Air Groove", "Tokai Teio", 1.0, 0.0),
                ("Air Groove", "Symboli Rudolf", 1.0, 0.0),
            ),
        )

    def test_interrupted_chorus_has_no_settlement(self):
        plan = build_chorus_settlement_plan(
            build_event(event_type="chorus_interrupted")
        )

        self.assertTrue(plan.empty)

    def test_settings_preview_has_no_settlement(self):
        plan = build_chorus_settlement_plan(
            build_event(source="settings_preview")
        )

        self.assertTrue(plan.empty)


if __name__ == "__main__":
    unittest.main()
