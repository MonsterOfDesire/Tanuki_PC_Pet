import unittest

from tanuki_core.pet_social_log_rules import (
    SOCIAL_LOG_COOLDOWN_SECONDS,
    get_social_log_template_count,
    resolve_social_log_event_plan,
)


class PetSocialLogRulesTests(unittest.TestCase):
    def test_observe_social_log_plan_emits_low_importance_relationship_note(self):
        plan = resolve_social_log_event_plan(
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            source_context="observe",
            now=10.0,
            roll=0.0,
            template_index=0,
        )

        self.assertTrue(plan.should_emit)
        self.assertEqual(plan.event_type, "observe_social_log")
        self.assertIn("Symboli Rudolf", plan.summary)
        self.assertIn("Tokai Teio", plan.summary)
        self.assertEqual(plan.relation_delta, {"familiarity": 0.12})
        self.assertEqual(plan.tags, ("observe", "ambient_social"))
        self.assertEqual(plan.cooldown_until, 10.0 + SOCIAL_LOG_COOLDOWN_SECONDS)

    def test_post_observe_social_log_plan_has_stronger_relation_delta(self):
        plan = resolve_social_log_event_plan(
            actor_name="Air Groove",
            target_name="Symboli Rudolf",
            source_context="post_observe_interaction",
            now=20.0,
            roll=0.0,
            template_index=1,
        )

        self.assertTrue(plan.should_emit)
        self.assertEqual(plan.event_type, "post_observe_social_log")
        self.assertEqual(plan.relation_delta, {"familiarity": 0.25, "attachment": 0.08})
        self.assertEqual(plan.tags, ("observe", "post_observe", "small_talk"))

    def test_awkward_social_log_plan_can_emit_negative_relationship_delta(self):
        plan = resolve_social_log_event_plan(
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            source_context="post_observe_interaction",
            now=20.0,
            roll=0.0,
            template_index=16,
        )

        self.assertTrue(plan.should_emit)
        self.assertEqual(plan.relation_delta, {"trust": -0.08, "attachment": -0.03, "tension": 0.20})
        self.assertIn("minor_tension", plan.tags)

    def test_social_log_plan_respects_roll_and_cooldown(self):
        missed = resolve_social_log_event_plan(
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            source_context="observe",
            now=10.0,
            roll=0.99,
        )
        cooldown = resolve_social_log_event_plan(
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            source_context="observe",
            now=10.0,
            cooldown_until=20.0,
            roll=0.0,
        )

        self.assertFalse(missed.should_emit)
        self.assertEqual(missed.reason, "roll_miss")
        self.assertFalse(cooldown.should_emit)
        self.assertEqual(cooldown.reason, "cooldown")

    def test_social_log_template_pool_has_expanded_daily_life_variation(self):
        self.assertEqual(get_social_log_template_count("observe"), 24)
        self.assertEqual(get_social_log_template_count("post_observe_interaction"), 25)

        observe_plan = resolve_social_log_event_plan(
            actor_name="Symboli Rudolf",
            target_name="Air Groove",
            source_context="observe",
            now=10.0,
            roll=0.0,
            template_index=23,
        )
        post_plan = resolve_social_log_event_plan(
            actor_name="Tokai Teio",
            target_name="Tsurumaru Tsuyoshi",
            source_context="post_observe_interaction",
            now=10.0,
            roll=0.0,
            template_index=23,
        )

        self.assertIn("Symboli Rudolf", observe_plan.summary)
        self.assertIn("Air Groove", observe_plan.summary)
        self.assertIn("Tokai Teio", post_plan.summary)
        self.assertIn("Tsurumaru Tsuyoshi", post_plan.summary)


if __name__ == "__main__":
    unittest.main()
