import unittest

from tanuki_core.pet_ai_decision import (
    AI_STAGE_AMBIENT_MOOD,
    AI_STAGE_CARE,
    AI_STAGE_OBSERVE,
    AI_STAGE_POST_OBSERVE,
    AI_STAGE_SOCIAL,
    build_pet_ai_stage_plan,
)


class PetAiDecisionTests(unittest.TestCase):
    def test_followup_disabled_has_no_stages(self):
        plan = build_pet_ai_stage_plan(
            should_attempt_followup=False,
            care_lock_maintained=False,
            active_post_observe=False,
            active_observe=False,
            refresh_high_level=True,
        )
        self.assertEqual(plan.stages, ())
        self.assertFalse(plan.high_level_allowed)

    def test_care_lock_suppresses_all_followup_handlers(self):
        plan = build_pet_ai_stage_plan(
            should_attempt_followup=True,
            care_lock_maintained=True,
            active_post_observe=True,
            active_observe=False,
            refresh_high_level=True,
        )
        self.assertEqual(plan.stages, ())

    def test_low_frequency_gate_keeps_care_and_social_each_tick(self):
        plan = build_pet_ai_stage_plan(
            should_attempt_followup=True,
            care_lock_maintained=False,
            active_post_observe=False,
            active_observe=False,
            refresh_high_level=False,
        )
        self.assertEqual(plan.stages, (AI_STAGE_CARE, AI_STAGE_SOCIAL))
        self.assertFalse(plan.high_level_allowed)

    def test_active_observe_preserves_full_stage_order(self):
        plan = build_pet_ai_stage_plan(
            should_attempt_followup=True,
            care_lock_maintained=False,
            active_post_observe=False,
            active_observe=True,
            refresh_high_level=False,
        )
        self.assertEqual(plan.stages, (
            AI_STAGE_CARE,
            AI_STAGE_SOCIAL,
            AI_STAGE_POST_OBSERVE,
            AI_STAGE_OBSERVE,
            AI_STAGE_AMBIENT_MOOD,
        ))
        self.assertTrue(plan.high_level_allowed)


if __name__ == "__main__":
    unittest.main()
