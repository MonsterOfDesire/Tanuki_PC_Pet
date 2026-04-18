import unittest

from tanuki_core.pet_social_coordinator import (
    ActiveCareContext,
    ActiveSocialContext,
    CARE_DECISION_APPROACH_TICK,
    CARE_DECISION_CANCEL,
    CARE_DECISION_CONTINUE,
    CARE_DECISION_FINISH_FAILURE,
    CARE_DECISION_FINISH_SUCCESS,
    CARE_DECISION_INTERACTION_TICK,
    CARE_DECISION_SIT_TICK,
    CARE_DECISION_START_APPROACH,
    CARE_TRANSITION_COMPANION,
    CARE_TRANSITION_INTERACTION,
    CARE_TRANSITION_NONE,
    IdleCareContext,
    SOCIAL_CARE_COORDINATOR,
    SOCIAL_DECISION_ACTIVE_FOLLOWING,
    SOCIAL_DECISION_ACTIVE_MIMICKING,
    SOCIAL_DECISION_CONTINUE,
    SOCIAL_DECISION_NONE,
    SOCIAL_DECISION_START_FOLLOWING,
    SOCIAL_DECISION_START_MIMICKING,
    SOCIAL_DECISION_STOP,
    SocialEntryContext,
)
from tanuki_core.pet_social_rules import CareTargetCandidate


class CareCoordinatorTests(unittest.TestCase):
    def test_care_gate_cancels_active_mode_when_feature_unavailable(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_care_gate(
            is_adult=True,
            is_visible=False,
            care_enabled=True,
            care_mode="approach",
        )

        self.assertEqual(decision.action, CARE_DECISION_CANCEL)

    def test_care_gate_allows_processing_when_prerequisites_pass(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_care_gate(
            is_adult=True,
            is_visible=True,
            care_enabled=True,
            care_mode="none",
        )

        self.assertEqual(decision.action, CARE_DECISION_CONTINUE)

    def test_active_care_cancels_when_target_becomes_invalid(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=False,
            child_in_all_pets=False,
            child_partner_ok=False,
            child_visible=False,
            mode="approach",
            now=0.0,
            care_end_time=1.0,
            child_mood_score=0.0,
            child_is_distressed=True,
            care_plan="auto",
            interaction_available=False,
            adult_name="Air Groove",
            adult_x=100,
            child_x=120,
            distance_to_child=80,
            moving_interaction_hits_edge=False,
            roll=0.2,
        ))

        self.assertEqual(decision.action, CARE_DECISION_CANCEL)

    def test_active_interaction_mode_ticks_until_end(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=True,
            child_in_all_pets=True,
            child_partner_ok=True,
            child_visible=False,
            mode="interaction",
            now=1.0,
            care_end_time=2.0,
            child_mood_score=40.0,
            child_is_distressed=True,
            care_plan="auto",
            interaction_available=False,
            adult_name="Air Groove",
            adult_x=100,
            child_x=120,
            distance_to_child=80,
            moving_interaction_hits_edge=False,
            roll=0.2,
        ))

        self.assertEqual(decision.action, CARE_DECISION_INTERACTION_TICK)
        self.assertTrue(decision.handled)

    def test_moving_interaction_finishes_when_edge_is_reached(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=True,
            child_in_all_pets=True,
            child_partner_ok=True,
            child_visible=False,
            mode="moving_interaction",
            now=1.0,
            care_end_time=3.0,
            child_mood_score=40.0,
            child_is_distressed=True,
            care_plan="auto",
            interaction_available=False,
            adult_name="Air Groove",
            adult_x=100,
            child_x=120,
            distance_to_child=80,
            moving_interaction_hits_edge=True,
            roll=0.2,
        ))

        self.assertEqual(decision.action, CARE_DECISION_FINISH_SUCCESS)
        self.assertTrue(decision.handled)

    def test_sit_mode_stays_active_before_child_recovers(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=True,
            child_in_all_pets=True,
            child_partner_ok=True,
            child_visible=True,
            mode="sit",
            now=1.0,
            care_end_time=4.0,
            child_mood_score=60.0,
            child_is_distressed=True,
            care_plan="auto",
            interaction_available=False,
            adult_name="Air Groove",
            adult_x=100,
            child_x=120,
            distance_to_child=80,
            moving_interaction_hits_edge=False,
            roll=0.2,
        ))

        self.assertEqual(decision.action, CARE_DECISION_SIT_TICK)
        self.assertTrue(decision.handled)

    def test_approach_mode_finishes_without_success_when_child_already_recovered(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=True,
            child_in_all_pets=True,
            child_partner_ok=True,
            child_visible=True,
            mode="approach",
            now=1.0,
            care_end_time=4.0,
            child_mood_score=55.0,
            child_is_distressed=False,
            care_plan="auto",
            interaction_available=False,
            adult_name="Air Groove",
            adult_x=100,
            child_x=120,
            distance_to_child=80,
            moving_interaction_hits_edge=False,
            roll=0.2,
        ))

        self.assertEqual(decision.action, CARE_DECISION_FINISH_FAILURE)

    def test_approach_mode_resolves_plan_and_target_x(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
            has_child=True,
            child_in_all_pets=True,
            child_partner_ok=True,
            child_visible=True,
            mode="approach",
            now=1.0,
            care_end_time=4.0,
            child_mood_score=30.0,
            child_is_distressed=True,
            care_plan="auto",
            interaction_available=True,
            adult_name="Symboli Rudolf",
            adult_x=100,
            child_x=220,
            distance_to_child=80,
            moving_interaction_hits_edge=False,
            roll=0.20,
        ))

        self.assertEqual(decision.action, CARE_DECISION_APPROACH_TICK)
        self.assertEqual(decision.next_care_plan, "interaction")
        self.assertTrue(decision.use_interaction)
        self.assertEqual(decision.target_x, 220)

    def test_idle_care_starts_approach_for_nearest_eligible_target(self):
        adult = object()
        target = object()
        decision = SOCIAL_CARE_COORDINATOR.decide_idle_care(IdleCareContext(
            now=5.0,
            care_cooldown_end=1.0,
            adult=adult,
            adult_name="Air Groove",
            target_candidates=(
                CareTargetCandidate(
                    pet=target,
                    is_self=False,
                    is_adult=False,
                    is_visible=True,
                    care_partner=None,
                    is_recovering=False,
                    is_distressed=True,
                    distance=80,
                ),
            ),
        ))

        self.assertEqual(decision.action, CARE_DECISION_START_APPROACH)
        self.assertIs(decision.target, target)
        self.assertTrue(decision.handled)

    def test_approach_transition_chooses_interaction_or_companion(self):
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_approach_transition(
                arrived=False,
                distance_to_child=200,
                use_interaction=True,
            ),
            CARE_TRANSITION_NONE,
        )
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_approach_transition(
                arrived=True,
                distance_to_child=200,
                use_interaction=True,
            ),
            CARE_TRANSITION_INTERACTION,
        )
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_approach_transition(
                arrived=False,
                distance_to_child=120,
                use_interaction=False,
            ),
            CARE_TRANSITION_COMPANION,
        )


class SocialCoordinatorTests(unittest.TestCase):
    def test_social_gate_blocks_non_child_or_dragging_pets(self):
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_social_gate(
                is_social_child=False,
                dragging=False,
            ).action,
            SOCIAL_DECISION_NONE,
        )
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_social_gate(
                is_social_child=True,
                dragging=True,
            ).action,
            SOCIAL_DECISION_NONE,
        )
        self.assertEqual(
            SOCIAL_CARE_COORDINATOR.decide_social_gate(
                is_social_child=True,
                dragging=False,
            ).action,
            SOCIAL_DECISION_CONTINUE,
        )

    def test_active_following_stops_when_rudolf_is_missing_or_stops_moving(self):
        missing = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
            social_mode="following",
            has_rudolf=False,
            social_target_matches=False,
            distance_to_rudolf=0,
            timer_frames_remaining=10,
            social_distance=120,
            rudolf_purpose="move",
            can_mimic=True,
        ))
        stopped = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
            social_mode="following",
            has_rudolf=True,
            social_target_matches=True,
            distance_to_rudolf=60,
            timer_frames_remaining=10,
            social_distance=120,
            rudolf_purpose="idle",
            can_mimic=True,
        ))

        self.assertEqual(missing.action, SOCIAL_DECISION_STOP)
        self.assertEqual(stopped.action, SOCIAL_DECISION_STOP)

    def test_active_social_returns_following_or_mimicking_modes(self):
        following = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
            social_mode="following",
            has_rudolf=True,
            social_target_matches=True,
            distance_to_rudolf=60,
            timer_frames_remaining=10,
            social_distance=120,
            rudolf_purpose="move",
            can_mimic=True,
        ))
        mimicking = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
            social_mode="mimicking",
            has_rudolf=True,
            social_target_matches=True,
            distance_to_rudolf=60,
            timer_frames_remaining=10,
            social_distance=120,
            rudolf_purpose="idle",
            can_mimic=True,
        ))

        self.assertEqual(following.action, SOCIAL_DECISION_ACTIVE_FOLLOWING)
        self.assertTrue(following.handled)
        self.assertEqual(mimicking.action, SOCIAL_DECISION_ACTIVE_MIMICKING)
        self.assertTrue(mimicking.handled)

    def test_active_mimicking_stops_when_pet_can_no_longer_mimic(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
            social_mode="mimicking",
            has_rudolf=True,
            social_target_matches=True,
            distance_to_rudolf=60,
            timer_frames_remaining=10,
            social_distance=120,
            rudolf_purpose="idle",
            can_mimic=False,
        ))

        self.assertEqual(decision.action, SOCIAL_DECISION_STOP)

    def test_social_entry_starts_following_or_mimicking(self):
        following = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=True,
            now=5.0,
            social_cooldown_end=0.0,
            distance_to_rudolf=80,
            social_distance=120,
            rudolf_purpose="move",
            is_behind=True,
            can_strictly_mimic=True,
            can_mimic=True,
        ))
        mimicking = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=True,
            now=5.0,
            social_cooldown_end=0.0,
            distance_to_rudolf=80,
            social_distance=120,
            rudolf_purpose="idle",
            is_behind=False,
            can_strictly_mimic=True,
            can_mimic=True,
        ))

        self.assertEqual(following.action, SOCIAL_DECISION_START_FOLLOWING)
        self.assertEqual(mimicking.action, SOCIAL_DECISION_START_MIMICKING)

    def test_social_entry_respects_cooldown_and_distance(self):
        cooldown = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=True,
            now=2.0,
            social_cooldown_end=5.0,
            distance_to_rudolf=80,
            social_distance=120,
            rudolf_purpose="move",
            is_behind=True,
            can_strictly_mimic=True,
            can_mimic=True,
        ))
        too_far = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=True,
            now=6.0,
            social_cooldown_end=5.0,
            distance_to_rudolf=180,
            social_distance=120,
            rudolf_purpose="move",
            is_behind=True,
            can_strictly_mimic=True,
            can_mimic=True,
        ))

        self.assertEqual(cooldown.action, SOCIAL_DECISION_NONE)
        self.assertEqual(too_far.action, SOCIAL_DECISION_NONE)

    def test_social_entry_keeps_low_mood_child_out_of_mimicking(self):
        decision = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=True,
            now=6.0,
            social_cooldown_end=0.0,
            distance_to_rudolf=80,
            social_distance=120,
            rudolf_purpose="idle",
            is_behind=False,
            can_strictly_mimic=True,
            can_mimic=False,
        ))

        self.assertEqual(decision.action, SOCIAL_DECISION_NONE)


if __name__ == "__main__":
    unittest.main()
