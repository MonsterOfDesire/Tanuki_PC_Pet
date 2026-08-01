import unittest

from tanuki_core.transformation_rules import (
    AUTO_ACTION_CLEANUP_PREVIEW,
    AUTO_ACTION_END,
    AUTO_ACTION_SCHEDULE,
    AUTO_ACTION_SCHEDULE_MANUAL_END,
    AUTO_ACTION_START,
    TransformationAutoSnapshot,
    TransformationEligibilitySnapshot,
    compute_transformation_whiteness,
    decide_auto_transformation,
    evaluate_transformation_eligibility,
)
from tanuki_core.transformation_state import (
    FORM_BASE,
    FORM_TRANSFORMED,
    TRANSFORMATION_PHASE_REVEALING,
    TRANSFORMATION_PHASE_WHITENING,
)


class TransformationRulesTests(unittest.TestCase):
    def test_base_form_targets_transformed_form(self):
        decision = evaluate_transformation_eligibility(
            TransformationEligibilitySnapshot(
                character_name="Tokai Teio",
                supported=True,
                current_form=FORM_BASE,
            )
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.target_form, FORM_TRANSFORMED)

    def test_transformed_form_targets_base_form(self):
        decision = evaluate_transformation_eligibility(
            TransformationEligibilitySnapshot(
                character_name="Tokai Teio",
                supported=True,
                current_form=FORM_TRANSFORMED,
            )
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.target_form, FORM_BASE)

    def test_airborne_and_busy_participants_are_rejected(self):
        airborne = evaluate_transformation_eligibility(
            TransformationEligibilitySnapshot(
                character_name="Tokai Teio",
                supported=True,
                vertical_velocity=1.0,
            )
        )
        busy = evaluate_transformation_eligibility(
            TransformationEligibilitySnapshot(
                character_name="Tokai Teio",
                supported=True,
                active_activity=True,
            )
        )

        self.assertEqual(airborne.reason, "airborne")
        self.assertEqual(busy.reason, "participant_owned")

    def test_whiteness_rises_then_falls(self):
        self.assertEqual(
            compute_transformation_whiteness(
                TRANSFORMATION_PHASE_WHITENING,
                elapsed_seconds=0.25,
                phase_seconds=0.5,
            ),
            (0.5, False),
        )
        self.assertEqual(
            compute_transformation_whiteness(
                TRANSFORMATION_PHASE_REVEALING,
                elapsed_seconds=0.5,
                phase_seconds=0.5,
            ),
            (0.0, True),
        )

    def test_golden_world_schedules_then_starts_autonomous_transformation(self):
        unscheduled = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="golden_legend",
                current_form=FORM_BASE,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=10.0,
            )
        )
        ready = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="golden_legend",
                current_form=FORM_BASE,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=20.0,
                next_attempt_at=20.0,
            )
        )

        self.assertEqual(unscheduled.action, AUTO_ACTION_SCHEDULE)
        self.assertEqual(ready.action, AUTO_ACTION_START)

    def test_auto_start_waits_until_mood_is_normal(self):
        decision = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="golden_legend",
                current_form=FORM_BASE,
                transitioning=False,
                auto_session=False,
                mood_score=49.0,
                now=20.0,
                next_attempt_at=10.0,
            )
        )

        self.assertEqual(decision.action, "none")
        self.assertEqual(decision.reason, "mood_not_normal")

    def test_auto_form_ends_after_duration_and_preview_is_cleaned_in_golden_world(self):
        expired = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="golden_legend",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=True,
                mood_score=60.0,
                now=31.0,
                form_expires_at=30.0,
            )
        )
        preview = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="golden_legend",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=31.0,
            )
        )

        self.assertEqual(expired.action, AUTO_ACTION_END)
        self.assertEqual(preview.action, AUTO_ACTION_CLEANUP_PREVIEW)

    def test_sandbox_supports_auto_and_times_manual_preview(self):
        unscheduled = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="sandbox",
                current_form=FORM_BASE,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=10.0,
            )
        )
        auto_form = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="sandbox",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=True,
                mood_score=60.0,
                now=31.0,
            )
        )
        manual_preview = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="sandbox",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=31.0,
                form_expires_at=60.0,
            )
        )
        expired_manual_preview = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="sandbox",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=61.0,
                form_expires_at=60.0,
            )
        )
        missing_manual_duration = decide_auto_transformation(
            TransformationAutoSnapshot(
                world_mode="sandbox",
                current_form=FORM_TRANSFORMED,
                transitioning=False,
                auto_session=False,
                mood_score=60.0,
                now=31.0,
            )
        )

        self.assertEqual(unscheduled.action, AUTO_ACTION_SCHEDULE)
        self.assertEqual(auto_form.action, AUTO_ACTION_END)
        self.assertEqual(manual_preview.action, "none")
        self.assertEqual(
            manual_preview.reason,
            "manual_preview_active",
        )
        self.assertEqual(expired_manual_preview.action, AUTO_ACTION_END)
        self.assertEqual(
            expired_manual_preview.reason,
            "manual_duration_complete",
        )
        self.assertEqual(
            missing_manual_duration.action,
            AUTO_ACTION_SCHEDULE_MANUAL_END,
        )


if __name__ == "__main__":
    unittest.main()
