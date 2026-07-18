import unittest

from tanuki_core.shared_food_partner_rules import (
    SharedFoodParticipantState,
    calculate_shared_food_approach_timeout,
    evaluate_shared_food_partner_eligibility,
)


class SharedFoodPartnerRulesTests(unittest.TestCase):
    def evaluate(self, *, distance=500.0, holder=None, partner=None):
        return evaluate_shared_food_partner_eligibility(
            holder=holder or SharedFoodParticipantState(),
            partner=partner or SharedFoodParticipantState(),
            distance=distance,
            join_distance=500.0,
        )

    def test_join_distance_is_inclusive(self):
        self.assertTrue(self.evaluate(distance=500.0).eligible)
        decision = self.evaluate(distance=500.01)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.reason, "partner_too_far")

    def test_unavailable_participant_states_are_rejected(self):
        cases = (
            (SharedFoodParticipantState(dragging=True), None, "holder_dragging"),
            (None, SharedFoodParticipantState(dragging=True), "partner_dragging"),
            (None, SharedFoodParticipantState(recovering=True), "partner_recovering"),
            (None, SharedFoodParticipantState(social_mode="following"), "partner_social_busy"),
            (None, SharedFoodParticipantState(perched=True), "partner_perched"),
            (None, SharedFoodParticipantState(busy=True), "partner_busy"),
            (None, SharedFoodParticipantState(has_held_item=True), "partner_holding_item"),
            (
                None,
                SharedFoodParticipantState(offer_scene_kind="care_interaction"),
                "partner_offer_busy",
            ),
        )
        for holder, partner, reason in cases:
            with self.subTest(reason=reason):
                decision = self.evaluate(holder=holder, partner=partner)
                self.assertFalse(decision.eligible)
                self.assertEqual(decision.reason, reason)

    def test_hover_preview_can_be_replaced_by_shared_food(self):
        decision = self.evaluate(
            holder=SharedFoodParticipantState(offer_scene_kind="hover_preview"),
            partner=SharedFoodParticipantState(offer_scene_kind="hover_preview"),
        )
        self.assertTrue(decision.eligible)

    def test_approach_timeout_uses_travel_distance_plus_buffer(self):
        timeout = calculate_shared_food_approach_timeout(
            distance=500.0,
            approach_distance=120.0,
            speed_per_tick=2.0,
            tick_seconds=0.03,
            wait_buffer_seconds=2.0,
            maximum_seconds=8.0,
        )
        self.assertAlmostEqual(timeout, 7.7)


if __name__ == "__main__":
    unittest.main()
