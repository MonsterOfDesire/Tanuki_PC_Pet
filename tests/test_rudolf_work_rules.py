import unittest

from tanuki_core.rudolf_work_rules import (
    RUDOLF_NAME,
    RUDOLF_WORK_ACTIVITY_KIND,
    RUDOLF_WORK_PROFILE,
    RUDOLF_WORK_REST_PHASE,
    RUDOLF_WORK_WORKING_PHASE,
    RudolfWorkEligibilitySnapshot,
    build_rudolf_work_result,
    evaluate_rudolf_work_capability,
    evaluate_rudolf_work_eligibility,
    evaluate_rudolf_work_preview_eligibility,
)


class FakeAssetManager:
    def __init__(self, results):
        self.results = dict(results)
        self.calls = []

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.calls.append((tuple(purposes), context, mood_score))
        return self.results.get((context, mood_score))


def eligibility_snapshot(**overrides):
    values = {
        "character_name": RUDOLF_NAME,
        "world_mode": "golden_legend",
        "mood_score": 60.0,
        "living_fund": 800,
        "household_pressure": 10.0,
        "now": 100.0,
        "next_eligible_at": 0.0,
    }
    values.update(overrides)
    return RudolfWorkEligibilitySnapshot(**values)


class RudolfWorkProfileTests(unittest.TestCase):
    def test_profile_uses_context_and_band_policy_without_action_candidates(self):
        profile = RUDOLF_WORK_PROFILE

        self.assertEqual(profile.activity_spec.kind, RUDOLF_WORK_ACTIVITY_KIND)
        self.assertEqual(
            tuple(phase.name for phase in profile.activity_spec.phases),
            (RUDOLF_WORK_WORKING_PHASE, RUDOLF_WORK_REST_PHASE),
        )
        self.assertEqual(
            profile.working_animation.contexts,
            ("activity_work_stationary",),
        )
        self.assertEqual(
            profile.rest_animation.contexts,
            ("activity_work_rest",),
        )
        self.assertEqual(profile.rest_animation.band_policy, "ignore")
        self.assertEqual(
            profile.transport_animation.contexts,
            ("activity_work_transport",),
        )
        self.assertEqual(profile.enabled_work_modes, ("stationary",))

    def test_profile_blocks_other_behaviors_and_ignores_collision(self):
        spec = RUDOLF_WORK_PROFILE.activity_spec

        self.assertIn("offer", spec.blocked_operations)
        self.assertIn("drag", spec.blocked_operations)
        self.assertIn("windowing", spec.blocked_operations)
        self.assertEqual(spec.collision_policy, "ignore")
        self.assertEqual(spec.phases[0].interrupt_policy, "force_only")
        self.assertEqual(spec.phases[1].interrupt_policy, "allow")


class RudolfWorkEligibilityTests(unittest.TestCase):
    def test_normal_or_low_mood_can_work_when_household_needs_help(self):
        normal = evaluate_rudolf_work_eligibility(
            eligibility_snapshot(mood_score=60.0)
        )
        low = evaluate_rudolf_work_eligibility(
            eligibility_snapshot(
                mood_score=35.0,
                living_fund=1200,
                household_pressure=30.0,
            )
        )

        self.assertTrue(normal.allowed)
        self.assertEqual(normal.mood_band, "normal")
        self.assertTrue(low.allowed)
        self.assertEqual(low.mood_band, "low")

    def test_severe_mood_is_rejected_before_work_starts(self):
        decision = evaluate_rudolf_work_eligibility(
            eligibility_snapshot(mood_score=10.0)
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "severe_mood")
        self.assertEqual(decision.mood_band, "severe")

    def test_mode_cooldown_character_and_household_are_explicit_gates(self):
        cases = (
            (
                eligibility_snapshot(world_mode="sandbox"),
                "world_mode_disabled",
            ),
            (
                eligibility_snapshot(now=10.0, next_eligible_at=20.0),
                "cooldown_active",
            ),
            (
                eligibility_snapshot(
                    living_fund=1200,
                    household_pressure=10.0,
                ),
                "household_stable",
            ),
            (
                eligibility_snapshot(character_name="Tokai Teio"),
                "unsupported_character",
            ),
        )

        for snapshot, reason in cases:
            with self.subTest(reason=reason):
                decision = evaluate_rudolf_work_eligibility(snapshot)
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.reason, reason)

    def test_sandbox_preview_ignores_household_need_but_keeps_mood_gate(self):
        allowed = evaluate_rudolf_work_preview_eligibility(
            eligibility_snapshot(
                world_mode="sandbox",
                living_fund=9999,
                household_pressure=0.0,
            )
        )
        severe = evaluate_rudolf_work_preview_eligibility(
            eligibility_snapshot(
                world_mode="sandbox",
                mood_score=10.0,
            )
        )
        wrong_mode = evaluate_rudolf_work_preview_eligibility(
            eligibility_snapshot(world_mode="golden_legend")
        )

        self.assertTrue(allowed.allowed)
        self.assertFalse(severe.allowed)
        self.assertEqual(severe.reason, "severe_mood")
        self.assertFalse(wrong_mode.allowed)
        self.assertEqual(
            wrong_mode.reason,
            "preview_requires_sandbox",
        )

    def test_capability_preflight_requires_work_and_ignore_band_rest_contexts(self):
        manager = FakeAssetManager(
            {
                ("activity_work_stationary", 30.0): (
                    ["work-frame"],
                    "idle",
                    "manifest-work",
                    "hurry",
                ),
                ("activity_work_rest", None): (
                    ["rest-frame"],
                    "idle",
                    "manifest-rest",
                    "exhausted",
                ),
            }
        )

        result = evaluate_rudolf_work_capability(
            manager,
            mood_score=35.0,
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            manager.calls,
            [
                (
                    ("idle", "move"),
                    "activity_work_stationary",
                    30.0,
                ),
                (
                    ("idle", "move"),
                    "activity_work_rest",
                    None,
                ),
            ],
        )

    def test_capability_preflight_reports_missing_phase(self):
        manager = FakeAssetManager(
            {
                ("activity_work_stationary", 60.0): (
                    ["work-frame"],
                    "idle",
                    "manifest-work",
                    "happy",
                ),
            }
        )

        result = evaluate_rudolf_work_capability(
            manager,
            mood_score=60.0,
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason, "no_manifest_match")
        self.assertEqual(result.phase_name, RUDOLF_WORK_REST_PHASE)

    def test_completed_work_result_uses_small_fixed_household_deltas(self):
        result = build_rudolf_work_result()

        self.assertEqual(result["settlement_key"], "rudolf_work_v1")
        self.assertEqual(result["living_fund_delta"], 80)
        self.assertEqual(result["household_pressure_delta"], -6.0)
        self.assertEqual(result["mood_delta"], -6.0)
        self.assertEqual(result["completion_ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
