import unittest

from tanuki_core.pet_intent_rules import (
    INTENT_CARE_CHILD,
    INTENT_FLIGHT_TO_TASKBAR,
    INTENT_RANDOM_ROAM,
    IntentReselectPlan,
    allow_random_behavior_reselect,
    derive_current_intent,
    resolve_intent_reselect_gate,
)


class PetIntentRuleTests(unittest.TestCase):
    def test_derive_current_intent_prefers_active_care_and_window_modes(self):
        care_intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="approach",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
            current_purpose="idle",
            state="idle",
            intent_reconsider_after=0.0,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            social_target_name="",
            care_target_name="Tokai Teio",
        )
        flight_intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="to_taskbar",
            perched_window_hwnd=0,
            current_purpose="move",
            state="move",
            intent_reconsider_after=0.0,
            focus_target_name="",
            expression_animation_context="ambient",
            social_target_name="",
            care_target_name="",
        )

        self.assertEqual(care_intent.intent_kind, INTENT_CARE_CHILD)
        self.assertEqual(care_intent.intent_target_name, "Tokai Teio")
        self.assertEqual(flight_intent.intent_kind, INTENT_FLIGHT_TO_TASKBAR)

    def test_derive_current_intent_uses_ambient_move_when_no_high_priority_mode(self):
        intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
            current_purpose="move",
            state="move",
            intent_reconsider_after=0.0,
            focus_target_name="",
            expression_animation_context="ambient",
            social_target_name="",
            care_target_name="",
        )

        self.assertEqual(intent.intent_kind, INTENT_RANDOM_ROAM)

    def test_derive_current_intent_requires_relational_expression_for_observe(self):
        intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
            current_purpose="idle",
            state="idle",
            intent_reconsider_after=0.0,
            focus_target_name="Tokai Teio",
            expression_animation_context="ambient",
            social_target_name="",
            care_target_name="",
        )

        self.assertEqual(intent.intent_kind, "ambient_idle")

    def test_derive_current_intent_obey_observe_cooldown(self):
        intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
            current_purpose="idle",
            state="idle",
            intent_reconsider_after=10.5,
            focus_target_name="Tokai Teio",
            expression_animation_context="relation_watch",
            social_target_name="",
            care_target_name="",
        )

        self.assertEqual(intent.intent_kind, "ambient_idle")

    def test_derive_current_intent_blocks_observe_during_negative_afterglow(self):
        intent = derive_current_intent(
            now=10.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
            current_purpose="idle",
            state="idle",
            intent_reconsider_after=0.0,
            focus_target_name="Symboli Rudolf",
            expression_animation_context="relation_watch",
            social_target_name="",
            care_target_name="",
            negative_afterglow_active=True,
        )

        self.assertEqual(intent.intent_kind, "ambient_idle")
        self.assertEqual(intent.intent_reason, "idle")

    def test_intent_reselect_gate_only_opens_for_ambient_intents_after_cooldown(self):
        blocked = resolve_intent_reselect_gate(
            now=5.0,
            intent_kind=INTENT_RANDOM_ROAM,
            intent_reconsider_after=8.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
        )
        allowed = resolve_intent_reselect_gate(
            now=9.0,
            intent_kind=INTENT_RANDOM_ROAM,
            intent_reconsider_after=8.0,
            dragging=False,
            is_angry_locked=False,
            is_recovering=False,
            care_lock_active=False,
            care_mode="none",
            social_mode="none",
            flight_mode="none",
            perched_window_hwnd=0,
        )

        self.assertFalse(blocked.allow_reselect)
        self.assertEqual(blocked.reason, "cooldown")
        self.assertTrue(allowed.allow_reselect)
        self.assertGreater(allowed.next_reconsider_after, 9.0)

    def test_random_behavior_reselect_stays_available_for_ambient_idle(self):
        self.assertTrue(allow_random_behavior_reselect(
            intent_kind="ambient_idle",
            intent_gate_open=False,
        ))
        self.assertTrue(allow_random_behavior_reselect(
            intent_kind=INTENT_RANDOM_ROAM,
            intent_gate_open=False,
        ))
        self.assertFalse(allow_random_behavior_reselect(
            intent_kind="observe",
            intent_gate_open=False,
        ))


if __name__ == "__main__":
    unittest.main()
