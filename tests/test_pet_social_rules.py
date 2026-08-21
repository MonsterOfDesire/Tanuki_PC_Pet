import unittest

from tanuki_core.pet_social_rules import (
    CareAdultCandidate,
    CARE_PLAN_COMPANION,
    CARE_PLAN_INTERACTION,
    CareTargetCandidate,
    SOCIAL_ENTRY_FOLLOWING,
    SOCIAL_ENTRY_MIMICKING,
    SOCIAL_ENTRY_NONE,
    build_care_interaction_mood_candidates,
    build_distress_mood_candidates,
    can_mimic_socially,
    child_care_need_is_active,
    is_distressed_state,
    choose_care_target,
    choose_preferred_care_adult_name,
    decide_care_plan,
    decide_social_entry,
    parse_interaction_action,
    resolve_care_interaction_motion_order,
    should_preserve_candidate_animation,
)


class InteractionRuleTests(unittest.TestCase):
    def test_parse_move_interaction_action(self):
        parsed = parse_interaction_action("move_hug_teio")

        self.assertEqual(parsed, ("move", "hug", "teio"))

    def test_parse_idle_interaction_action(self):
        parsed = parse_interaction_action("idle_pat_child")

        self.assertEqual(parsed, ("idle", "pat", "child"))

    def test_parse_interaction_action_rejects_invalid_keys(self):
        self.assertIsNone(parse_interaction_action("hug_teio"))
        self.assertIsNone(parse_interaction_action("movehug"))

    def test_distress_mood_candidates_keep_current_mood_first_and_deduplicate(self):
        self.assertEqual(
            build_distress_mood_candidates("happy"),
            ["happy", "sad", "cry", "hard-cry"],
        )
        self.assertEqual(
            build_distress_mood_candidates("sad"),
            ["sad", "cry", "hard-cry", "happy"],
        )
        self.assertEqual(
            build_distress_mood_candidates(None),
            ["sad", "cry", "hard-cry", "happy"],
        )

    def test_care_interaction_mood_candidates_include_recovery_moods(self):
        self.assertEqual(
            build_care_interaction_mood_candidates("cry"),
            ["cry", "happy", "smile", "relief", "calm", "think", "sad", "hard-cry"],
        )

    def test_care_interaction_motion_order_can_prefer_stationary_or_moving(self):
        self.assertEqual(resolve_care_interaction_motion_order("move", 0.49), ["idle", "move"])
        self.assertEqual(resolve_care_interaction_motion_order("move", 0.50), ["move", "idle"])

    def test_is_distressed_state_requires_depressed_state_not_just_sad_animation(self):
        self.assertTrue(
            is_distressed_state(
                mood_state="depressed",
                current_mood_tag="sad",
                current_purpose="idle",
                dragging=False,
            )
        )
        self.assertFalse(
            is_distressed_state(
                mood_state="normal",
                current_mood_tag="sad",
                current_purpose="drag",
                dragging=True,
            )
        )
        self.assertTrue(can_mimic_socially(mood_state="normal"))
        self.assertFalse(can_mimic_socially(mood_state="unhappy"))

    def test_is_distressed_state_allows_cry_animation_to_trigger_before_mood_tick(self):
        self.assertTrue(
            is_distressed_state(
                mood_state="normal",
                current_mood_tag="cry",
                current_purpose="idle",
                dragging=False,
                mood_score=10,
            )
        )

    def test_is_distressed_state_does_not_trigger_on_scared_before_actual_cry(self):
        self.assertFalse(
            is_distressed_state(
                mood_state="normal",
                current_mood_tag="scared",
                current_purpose="idle",
                dragging=False,
                mood_score=10,
            )
        )

    def test_preserve_candidate_animation_keeps_eligible_fallback_animation(self):
        self.assertTrue(
            should_preserve_candidate_animation(
                "move",
                "run",
                "scold",
                [("move", "run"), ("move", "walk")],
                frames_available=True,
                preferred_moods=["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
            )
        )

    def test_preserve_candidate_animation_rejects_forbidden_mood_when_reselection_needed(self):
        self.assertFalse(
            should_preserve_candidate_animation(
                "move",
                "run",
                "cry",
                [("move", "run"), ("move", "walk")],
                frames_available=True,
                preferred_moods=["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
            )
        )


class CarePlanRuleTests(unittest.TestCase):
    def test_care_plan_falls_back_to_companion_when_interaction_missing(self):
        plan = decide_care_plan("Symboli Rudolf", has_interaction=False, roll=0.0)

        self.assertEqual(plan, CARE_PLAN_COMPANION)

    def test_care_plan_uses_character_weight_thresholds(self):
        self.assertEqual(
            decide_care_plan("Symboli Rudolf", has_interaction=True, roll=0.64),
            CARE_PLAN_INTERACTION,
        )
        self.assertEqual(
            decide_care_plan("Air Groove", has_interaction=True, roll=0.41),
            CARE_PLAN_COMPANION,
        )

    def test_care_plan_uses_default_weight_for_other_characters(self):
        self.assertEqual(
            decide_care_plan("Tokai Teio", has_interaction=True, roll=0.49),
            CARE_PLAN_INTERACTION,
        )
        self.assertEqual(
            decide_care_plan("Tokai Teio", has_interaction=True, roll=0.50),
            CARE_PLAN_COMPANION,
        )


class CareTargetRuleTests(unittest.TestCase):
    def test_child_care_need_is_shared_across_visible_distressed_children(self):
        self.assertTrue(
            child_care_need_is_active(
                is_child=True,
                is_visible=True,
                care_enabled=True,
                is_recovering=False,
                is_distressed=True,
            )
        )
        self.assertFalse(
            child_care_need_is_active(
                is_child=True,
                is_visible=True,
                care_enabled=True,
                is_recovering=True,
                is_distressed=True,
            )
        )

    def test_choose_care_target_selects_nearest_eligible_child(self):
        adult = object()
        child_far = object()
        child_near = object()

        target = choose_care_target(adult, "Air Groove", [
            CareTargetCandidate(child_far, False, False, True, None, False, True, 400, "Air Groove"),
            CareTargetCandidate(child_near, False, False, True, None, False, True, 120, "Air Groove"),
        ])

        self.assertIs(target, child_near)

    def test_choose_care_target_filters_out_ineligible_children(self):
        adult = object()
        partner = object()
        child_ok = object()

        target = choose_care_target(adult, "Air Groove", [
            CareTargetCandidate(adult, True, False, True, None, False, True, 50, "Air Groove"),
            CareTargetCandidate(object(), False, True, True, None, False, True, 40, "Air Groove"),
            CareTargetCandidate(object(), False, False, False, None, False, True, 30, "Air Groove"),
            CareTargetCandidate(object(), False, False, True, partner, False, True, 20, "Air Groove"),
            CareTargetCandidate(object(), False, False, True, None, True, True, 10, "Air Groove"),
            CareTargetCandidate(object(), False, False, True, None, False, False, 5, "Air Groove"),
            CareTargetCandidate(child_ok, False, False, True, adult, False, True, 200, "Air Groove"),
        ])

        self.assertIs(target, child_ok)

    def test_choose_care_target_filters_child_with_temporary_care_block(self):
        adult = object()
        blocked_child = object()

        target = choose_care_target(adult, "Air Groove", [
            CareTargetCandidate(
                blocked_child,
                False,
                False,
                True,
                None,
                False,
                True,
                120,
                "Air Groove",
                care_blocked=True,
            ),
        ])

        self.assertIsNone(target)

    def test_choose_care_target_filters_child_in_activity(self):
        adult = object()
        busy_child = object()

        target = choose_care_target(
            adult,
            "Air Groove",
            [
                CareTargetCandidate(
                    busy_child,
                    False,
                    False,
                    True,
                    None,
                    False,
                    True,
                    120,
                    "Air Groove",
                    activity_busy=True,
                ),
            ],
        )

        self.assertIsNone(target)

    def test_sirius_symboli_ignores_default_search_radius(self):
        adult = object()
        distant_child = object()

        target = choose_care_target(adult, "Sirius Symboli", [
            CareTargetCandidate(distant_child, False, False, True, None, False, True, 1800, "Sirius Symboli"),
        ])

        self.assertIs(target, distant_child)

    def test_other_adults_do_not_target_children_beyond_radius(self):
        adult = object()
        distant_child = object()

        target = choose_care_target(adult, "Air Groove", [
            CareTargetCandidate(distant_child, False, False, True, None, False, True, 1800, "Air Groove"),
        ])

        self.assertIsNone(target)

    def test_choose_care_target_respects_preferred_adult_name(self):
        adult = object()
        target = choose_care_target(adult, "Sirius Symboli", [
            CareTargetCandidate(object(), False, False, True, None, False, True, 120, "Air Groove"),
        ])
        self.assertIsNone(target)

    def test_choose_preferred_care_adult_name_prefers_nearest_available_adult(self):
        preferred = choose_preferred_care_adult_name([
            CareAdultCandidate("Sirius Symboli", True, True, False, 300, same_screen=False),
            CareAdultCandidate("Symboli Rudolf", True, True, False, 80, same_screen=True),
            CareAdultCandidate("Air Groove", True, True, True, 40, same_screen=True),
        ])

        self.assertEqual(preferred, "Symboli Rudolf")

    def test_choose_preferred_care_adult_name_falls_back_to_sirius_when_nearer_adult_cannot_search(self):
        preferred = choose_preferred_care_adult_name([
            CareAdultCandidate("Sirius Symboli", True, True, False, 1200, same_screen=False),
            CareAdultCandidate("Symboli Rudolf", True, True, False, 300, same_screen=False),
            CareAdultCandidate("Air Groove", True, True, False, 1400, same_screen=True),
        ])

        self.assertEqual(preferred, "Sirius Symboli")


class SocialEntryRuleTests(unittest.TestCase):
    def test_social_entry_prefers_following_when_rudolf_is_moving_and_child_is_behind(self):
        entry = decide_social_entry(
            distance=80,
            social_distance=120,
            rudolf_purpose="move",
            is_behind=True,
            can_strictly_mimic=True,
        )

        self.assertEqual(entry, SOCIAL_ENTRY_FOLLOWING)

    def test_social_entry_uses_mimicking_when_close_enough_and_following_does_not_apply(self):
        entry = decide_social_entry(
            distance=80,
            social_distance=120,
            rudolf_purpose="idle",
            is_behind=False,
            can_strictly_mimic=True,
            can_mimic=True,
        )

        self.assertEqual(entry, SOCIAL_ENTRY_MIMICKING)

    def test_social_entry_blocks_mimicking_when_mood_is_not_normal(self):
        entry = decide_social_entry(
            distance=80,
            social_distance=120,
            rudolf_purpose="idle",
            is_behind=False,
            can_strictly_mimic=True,
            can_mimic=False,
        )

        self.assertEqual(entry, SOCIAL_ENTRY_NONE)

    def test_social_entry_blocks_mimicking_when_rudolf_is_dragged(self):
        entry = decide_social_entry(
            distance=80,
            social_distance=120,
            rudolf_purpose="drag",
            is_behind=False,
            can_strictly_mimic=True,
            can_mimic=True,
        )

        self.assertEqual(entry, SOCIAL_ENTRY_NONE)

    def test_social_entry_returns_none_when_target_is_too_far(self):
        entry = decide_social_entry(
            distance=180,
            social_distance=120,
            rudolf_purpose="move",
            is_behind=True,
            can_strictly_mimic=True,
        )

        self.assertEqual(entry, SOCIAL_ENTRY_NONE)


if __name__ == "__main__":
    unittest.main()
