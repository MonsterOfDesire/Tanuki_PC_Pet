import unittest

from tanuki_core.pet_ambient_mood_rules import (
    OFFER_MISS_COOLDOWN_SECONDS,
    SOLITUDE_EVENT_COOLDOWN_SECONDS,
    resolve_offer_miss_event,
    resolve_solitude_event,
)


class PetAmbientMoodRulesTests(unittest.TestCase):
    def test_solitude_event_triggers_after_long_alone_period(self):
        decision = resolve_solitude_event(
            is_adult=True,
            now=100.0,
            last_company_seen_at=55.0,
            visible_pet_count=0,
            cooldown_until=0.0,
            mood_score=60.0,
        )

        self.assertTrue(decision.should_trigger)
        self.assertEqual(decision.event_kind, "solitude")
        self.assertEqual(decision.mood_delta, 3.0)
        self.assertEqual(decision.cooldown_seconds, SOLITUDE_EVENT_COOLDOWN_SECONDS)

    def test_offer_miss_event_triggers_only_before_hover_timeout_scene(self):
        triggered = resolve_offer_miss_event(
            now=12.5,
            hover_started_at=10.0,
            hover_timeout_seconds=5.0,
            cooldown_until=0.0,
        )
        blocked = resolve_offer_miss_event(
            now=15.1,
            hover_started_at=10.0,
            hover_timeout_seconds=5.0,
            cooldown_until=0.0,
        )

        self.assertTrue(triggered.should_trigger)
        self.assertEqual(triggered.event_kind, "offer_miss")
        self.assertEqual(triggered.mood_delta, 4.0)
        self.assertEqual(triggered.cooldown_seconds, OFFER_MISS_COOLDOWN_SECONDS)
        self.assertFalse(blocked.should_trigger)
        self.assertEqual(blocked.reason, "handled_by_timeout_scene")


if __name__ == "__main__":
    unittest.main()
