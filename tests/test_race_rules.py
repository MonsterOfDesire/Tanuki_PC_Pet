import unittest

from tanuki_core.race_rules import (
    RACE_ACTIVITY_KIND,
    RACE_COURSES,
    RACE_CHALLENGE_PHASE,
    RACE_FINISH_PHASE,
    RACE_READY_PHASE,
    RACE_RECOVERY_PHASE,
    RACE_RESPONSE_PHASE,
    RACE_RUNNING_PHASE,
    RACE_TO_START_PHASE,
    RaceEligibilitySnapshot,
    RaceEmergencySnapshot,
    build_race_activity_spec,
    build_race_lane_geometry,
    decide_race_acceptance,
    decide_race_performance,
    evaluate_race_eligibility,
    evaluate_race_emergency_interrupt,
    get_race_expected_speed,
    get_feasible_race_courses,
    get_race_schedule_policy,
    race_finish_is_ready,
    race_pair_has_valid_spacing,
    race_pair_is_close,
    race_pair_spacing_reason,
    resolve_race_finish_band,
    sample_race_speed,
    select_race_course,
)


def eligibility(**overrides):
    values = {
        "character_name": "Tokai Teio",
        "form_key": "base",
        "world_mode": "golden_legend",
        "mood_score": 60.0,
    }
    values.update(overrides)
    return RaceEligibilitySnapshot(**values)


class RaceRulesTests(unittest.TestCase):
    def test_activity_spec_owns_both_participants_through_all_race_phases(self):
        spec = build_race_activity_spec()

        self.assertEqual(spec.kind, RACE_ACTIVITY_KIND)
        self.assertEqual(
            tuple(phase.name for phase in spec.phases),
            (
                RACE_CHALLENGE_PHASE,
                RACE_RESPONSE_PHASE,
                RACE_TO_START_PHASE,
                RACE_READY_PHASE,
                RACE_RUNNING_PHASE,
                RACE_FINISH_PHASE,
                RACE_RECOVERY_PHASE,
            ),
        )
        self.assertEqual(spec.collision_policy, "ignore")
        self.assertIn("drag", spec.blocked_operations)

    def test_normal_and_low_are_eligible_but_severe_is_rejected(self):
        self.assertTrue(evaluate_race_eligibility(eligibility()).allowed)
        self.assertTrue(
            evaluate_race_eligibility(eligibility(mood_score=35.0)).allowed
        )

        severe = evaluate_race_eligibility(eligibility(mood_score=10.0))

        self.assertFalse(severe.allowed)
        self.assertEqual(severe.reason, "severe_mood")

    def test_preview_and_grounded_busy_gates_are_explicit(self):
        self.assertTrue(
            evaluate_race_eligibility(
                eligibility(world_mode="sandbox"),
                preview=True,
            ).allowed
        )
        self.assertEqual(
            evaluate_race_eligibility(
                eligibility(grounded=False)
            ).reason,
            "participant_airborne",
        )
        self.assertEqual(
            evaluate_race_eligibility(eligibility(busy=True)).reason,
            "participant_busy",
        )

    def test_sandbox_autonomous_schedule_is_enabled_and_more_frequent(self):
        golden = get_race_schedule_policy("golden_legend")
        sandbox = get_race_schedule_policy("sandbox")

        self.assertIsNotNone(sandbox)
        self.assertLess(sandbox.initial_min_seconds, golden.initial_min_seconds)
        self.assertLess(sandbox.retry_min_seconds, golden.retry_min_seconds)
        self.assertLess(sandbox.cooldown_min_seconds, golden.cooldown_min_seconds)

    def test_frequency_setting_scales_every_schedule_window(self):
        frequent = get_race_schedule_policy("sandbox", "frequent")
        normal = get_race_schedule_policy("sandbox", "normal")
        occasional = get_race_schedule_policy("sandbox", "occasional")

        self.assertEqual(
            frequent.initial_min_seconds,
            normal.initial_min_seconds * 0.5,
        )
        self.assertEqual(
            occasional.retry_max_seconds,
            normal.retry_max_seconds * 2.0,
        )
        self.assertEqual(
            occasional.cooldown_min_seconds,
            normal.cooldown_min_seconds * 2.0,
        )

    def test_normal_teio_always_accepts_and_low_teio_can_decline(self):
        normal = decide_race_acceptance(
            opponent_name="Tokai Teio",
            opponent_form="base",
            mood_score=60.0,
            roll=0.999,
        )
        low = decide_race_acceptance(
            opponent_name="Tokai Teio",
            opponent_form="base",
            mood_score=35.0,
            roll=0.8,
        )

        self.assertTrue(normal.accepted)
        self.assertEqual(normal.probability, 1.0)
        self.assertFalse(low.accepted)

    def test_only_child_care_or_tsuyoshi_honey_interrupts_race(self):
        calm = evaluate_race_emergency_interrupt(RaceEmergencySnapshot())
        care = evaluate_race_emergency_interrupt(
            RaceEmergencySnapshot(distressed_child_names=("Tokai Teio",))
        )
        honey = evaluate_race_emergency_interrupt(
            RaceEmergencySnapshot(tsuyoshi_has_honey=True)
        )

        self.assertFalse(calm.should_interrupt)
        self.assertEqual(care.reason, "child_care_needed")
        self.assertEqual(honey.reason, "tsuyoshi_honey_guard_needed")

    def test_lane_geometry_uses_exact_discrete_course_distance(self):
        lane = build_race_lane_geometry(
            left_bound=100.0,
            right_bound=1000.0,
            participant_widths=(120.0, 80.0),
            course_distance=500.0,
        )

        self.assertGreaterEqual(lane.challenger_start_x, 100.0)
        self.assertGreater(lane.opponent_start_x, lane.challenger_start_x)
        self.assertLessEqual(lane.finish_x + 120.0, 1000.0)
        self.assertEqual(lane.distance, 500.0)

    def test_course_catalog_has_requested_distances_and_probabilities(self):
        self.assertEqual(
            tuple((course.distance_px, course.weight) for course in RACE_COURSES),
            (
                (500.0, 0.10),
                (720.0, 0.30),
                (1100.0, 0.40),
                (1500.0, 0.20),
            ),
        )

    def test_course_selection_uses_requested_weights_when_all_fit(self):
        feasible = get_feasible_race_courses(
            left_bound=0.0,
            right_bound=2400.0,
            participant_widths=(100.0, 100.0),
            participant_radii=(50.0, 50.0),
        )

        self.assertEqual(feasible, RACE_COURSES)
        self.assertEqual(select_race_course(feasible, roll=0.099).distance_px, 500.0)
        self.assertEqual(select_race_course(feasible, roll=0.100).distance_px, 720.0)
        self.assertEqual(select_race_course(feasible, roll=0.399).distance_px, 720.0)
        self.assertEqual(select_race_course(feasible, roll=0.400).distance_px, 1100.0)
        self.assertEqual(select_race_course(feasible, roll=0.799).distance_px, 1100.0)
        self.assertEqual(select_race_course(feasible, roll=0.800).distance_px, 1500.0)

    def test_unavailable_courses_are_removed_and_weights_are_renormalized(self):
        feasible = get_feasible_race_courses(
            left_bound=0.0,
            right_bound=1200.0,
            participant_widths=(100.0, 100.0),
            participant_radii=(50.0, 50.0),
        )

        self.assertEqual(
            tuple(course.distance_px for course in feasible),
            (500.0, 720.0),
        )
        self.assertEqual(select_race_course(feasible, roll=0.249).distance_px, 500.0)
        self.assertEqual(select_race_course(feasible, roll=0.250).distance_px, 720.0)

    def test_course_selection_returns_none_when_even_500px_does_not_fit(self):
        feasible = get_feasible_race_courses(
            left_bound=100.0,
            right_bound=620.0,
            participant_widths=(120.0, 80.0),
        )

        self.assertEqual(feasible, ())
        self.assertIsNone(select_race_course(feasible, roll=0.0))

    def test_lane_geometry_offsets_full_size_racers_without_leaving_bounds(self):
        lane = build_race_lane_geometry(
            left_bound=0.0,
            right_bound=1920.0,
            participant_widths=(480.0, 480.0),
            participant_radii=(100.0, 100.0),
            course_distance=1100.0,
        )

        self.assertGreaterEqual(
            lane.opponent_start_x - lane.challenger_start_x,
            224.0,
        )
        self.assertGreaterEqual(lane.challenger_start_x, 0.0)
        self.assertLessEqual(lane.finish_x + 480.0, 1920.0)

    def test_lane_starts_near_participants_and_uses_the_more_open_side(self):
        lane = build_race_lane_geometry(
            left_bound=0.0,
            right_bound=1920.0,
            participant_widths=(100.0, 100.0),
            course_distance=1100.0,
            participant_positions=(1400.0, 1500.0),
        )

        self.assertEqual(lane.direction, -1)
        self.assertAlmostEqual(
            (lane.challenger_start_x + lane.opponent_start_x) / 2.0,
            1450.0,
        )
        self.assertEqual(lane.distance, 1100.0)
        self.assertLess(lane.finish_x, lane.challenger_start_x)

    def test_challenge_distance_and_finish_regroup_thresholds_are_explicit(self):
        self.assertTrue(race_pair_is_close(420.0))
        self.assertFalse(race_pair_is_close(420.1))
        self.assertFalse(
            race_finish_is_ready(winner_arrived=True, separation=150.1)
        )
        self.assertTrue(
            race_finish_is_ready(winner_arrived=True, separation=150.0)
        )

    def test_challenge_spacing_distinguishes_overlap_from_remote_distance(self):
        radii = (100.0, 100.0)

        self.assertEqual(
            race_pair_spacing_reason(223.9, participant_radii=radii),
            "participants_too_close",
        )
        self.assertTrue(
            race_pair_has_valid_spacing(224.0, participant_radii=radii)
        )
        self.assertEqual(
            race_pair_spacing_reason(420.1, participant_radii=radii),
            "participants_too_far",
        )

    def test_continuous_speed_ranking_matches_character_form_and_mood_policy(self):
        def speed(name, form, mood):
            return get_race_expected_speed(
                character_name=name,
                form_key=form,
                mood_score=mood,
            )

        transformed_rudolf = speed("Symboli Rudolf", "transformed", 75.0)
        good_sirius = speed("Sirius Symboli", "base", 75.0)
        good_teio = speed("Tokai Teio", "base", 75.0)
        good_rudolf = speed("Symboli Rudolf", "base", 75.0)
        low_sirius = speed("Sirius Symboli", "base", 35.0)
        low_rudolf = speed("Symboli Rudolf", "base", 35.0)
        low_teio = speed("Tokai Teio", "base", 35.0)

        self.assertGreater(transformed_rudolf, good_sirius)
        self.assertGreater(good_sirius, good_teio)
        self.assertGreater(good_teio, good_rudolf)
        self.assertAlmostEqual(good_rudolf, low_sirius)
        self.assertGreater(low_sirius, low_rudolf)
        self.assertGreaterEqual(low_rudolf, low_teio)

    def test_speed_changes_continuously_across_the_old_band_boundary(self):
        speeds = tuple(
            get_race_expected_speed(
                character_name="Sirius Symboli",
                form_key="base",
                mood_score=mood,
            )
            for mood in (49.0, 50.0, 51.0)
        )

        self.assertLess(speeds[0], speeds[1])
        self.assertLess(speeds[1], speeds[2])
        self.assertAlmostEqual(speeds[1] - speeds[0], speeds[2] - speeds[1])

    def test_small_speed_variation_preserves_base_speed_as_main_factor(self):
        slow_roll = sample_race_speed(6.0, roll=0.0)
        fast_roll = sample_race_speed(6.0, roll=1.0)
        decision = decide_race_performance(
            challenger_name="Sirius Symboli",
            challenger_form="base",
            challenger_mood_score=75.0,
            challenger_roll=0.25,
            opponent_name="Tokai Teio",
            opponent_form="base",
            opponent_mood_score=75.0,
            opponent_roll=0.75,
        )

        self.assertAlmostEqual(fast_roll - slow_roll, 0.30)
        self.assertEqual(decision.winner_name, "Sirius Symboli")

    def test_finish_band_treats_adult_loss_to_teio_as_appreciative(self):
        self.assertEqual(
            resolve_race_finish_band(
                character_name="Symboli Rudolf",
                opponent_name="Tokai Teio",
                winner=False,
            ),
            "normal",
        )
        self.assertEqual(
            resolve_race_finish_band(
                character_name="Sirius Symboli",
                opponent_name="Symboli Rudolf",
                winner=False,
            ),
            "low",
        )
        self.assertEqual(
            resolve_race_finish_band(
                character_name="Tokai Teio",
                opponent_name="Symboli Rudolf",
                winner=False,
            ),
            "low",
        )


if __name__ == "__main__":
    unittest.main()
