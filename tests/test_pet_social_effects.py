import unittest

from tanuki_core.pet_social_effects import SOCIAL_CARE_EFFECTS
from tanuki_core.transformation_state import (
    FORM_TRANSFORMED,
    PetTransformationState,
)


class FakeTimer:
    def __init__(self):
        self.started_with = []

    def start(self, interval):
        self.started_with.append(interval)


class FakeChild:
    def __init__(self):
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0
        self.visible = True
        self.state = ""
        self.mood_score = 40
        self.clear_care_lock_called = False
        self.pop_heart_called = False
        self.recovery_started_at = None
        self.ensure_candidate_animation_args = []

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def isVisible(self):
        return self.visible

    def clear_care_lock(self):
        self.clear_care_lock_called = True
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

    def pop_heart(self):
        self.pop_heart_called = True

    def start_recovery(self, now):
        self.recovery_started_at = now

    def ensure_candidate_animation(self, candidates):
        self.ensure_candidate_animation_args.append(candidates)

    def get_child_comfort_candidates(self):
        return [("idle", "comfort")]


class FakeAdult:
    def __init__(self):
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0
        self.social_cooldown_end = 0.0
        self.star_timer = FakeTimer()
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.is_hugging = False
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_cooldown_end = 0.0
        self.direction = 1
        self.current_frames = []
        self.frame_index = 0
        self.current_purpose = ""
        self.current_action_tag = ""
        self.current_mood_tag = ""
        self.state = ""
        self.released_child = None
        self.changed_state_args = []
        self.ensure_candidate_animation_args = []
        self.care_companion_animation_calls = 0

    def get_social_duration_frames(self, mode):
        return 123 if mode == "following" else 77

    def get_social_cooldown_seconds(self):
        return 5.5

    def get_adult_companion_candidates(self):
        return [("idle", "companion")]

    def ensure_candidate_animation(self, candidates):
        self.ensure_candidate_animation_args.append(candidates)

    def apply_care_companion_animation(self):
        self.care_companion_animation_calls += 1
        return True

    def release_hidden_child_nearby(self, child):
        self.released_child = child

    def change_state(self, purpose, action_type=None):
        self.changed_state_args.append((purpose, action_type))

    def isVisible(self):
        return True

    def show(self):
        pass


class SocialCareEffectsTests(unittest.TestCase):
    def test_start_and_stop_social_mode_manage_timer_and_cooldown(self):
        adult = FakeAdult()
        target = object()

        SOCIAL_CARE_EFFECTS.start_social_mode(adult, "following", target, 12.5)

        self.assertEqual(adult.social_mode, "following")
        self.assertIs(adult.social_target, target)
        self.assertEqual(adult.social_started_at, 12.5)
        self.assertEqual(adult.social_timer_frames, 123)
        self.assertEqual(adult.star_timer.started_with, [30])

        SOCIAL_CARE_EFFECTS.stop_social_mode(adult, 20.0, apply_cooldown=True)

        self.assertEqual(adult.social_mode, "none")
        self.assertIsNone(adult.social_target)
        self.assertEqual(adult.social_started_at, 0.0)
        self.assertEqual(adult.social_timer_frames, 0)
        self.assertEqual(adult.social_cooldown_end, 25.5)

    def test_transformed_rudolf_social_target_shortens_child_cooldown(self):
        child = FakeAdult()
        child.name = "Tokai Teio"
        child.transformation_state = PetTransformationState()
        target = FakeAdult()
        target.name = "Symboli Rudolf"
        target.transformation_state = PetTransformationState(
            current_form=FORM_TRANSFORMED,
        )
        SOCIAL_CARE_EFFECTS.start_social_mode(
            child,
            "following",
            target,
            12.5,
        )

        SOCIAL_CARE_EFFECTS.stop_social_mode(
            child,
            20.0,
            apply_cooldown=True,
        )

        self.assertAlmostEqual(
            child.social_cooldown_end,
            20.0 + 5.5 * 0.65,
        )

    def test_start_care_approach_clears_social_without_cooldown(self):
        adult = FakeAdult()
        child = FakeChild()
        adult.social_mode = "following"

        SOCIAL_CARE_EFFECTS.start_care_approach(adult, child, 10.0)

        self.assertEqual(adult.social_mode, "none")
        self.assertEqual(adult.care_mode, "approach")
        self.assertIs(adult.care_target, child)
        self.assertEqual(adult.care_plan, "auto")
        self.assertIs(child.care_partner, adult)
        self.assertEqual(adult.social_cooldown_end, 0.0)

    def test_begin_hidden_interaction_sets_hidden_lock_and_animation_state(self):
        adult = FakeAdult()
        child = FakeChild()

        SOCIAL_CARE_EFFECTS.begin_hidden_interaction(
            adult,
            child,
            ("move_hug_Teio", "sad", ["frame-a"]),
            33.0,
        )

        self.assertEqual(adult.care_mode, "moving_interaction")
        self.assertEqual(adult.care_end_time, 36.0)
        self.assertTrue(adult.is_hugging)
        self.assertEqual(adult.care_move_direction, 1)
        self.assertFalse(child.isVisible())
        self.assertIs(child.care_partner, adult)
        self.assertEqual(child.care_lock_mode, "hidden")
        self.assertEqual(child.care_lock_end_time, 36.0)
        self.assertEqual(adult.current_purpose, "interaction")
        self.assertEqual(adult.current_action_tag, "move_hug_Teio")
        self.assertEqual(adult.current_mood_tag, "sad")
        self.assertEqual(adult.state, "move")

    def test_begin_companion_care_syncs_both_adult_and_child(self):
        adult = FakeAdult()
        child = FakeChild()
        child.visible = False

        SOCIAL_CARE_EFFECTS.begin_companion_care(adult, child, 40.0)

        self.assertEqual(adult.care_mode, "sit")
        self.assertEqual(adult.care_end_time, 45.0)
        self.assertTrue(child.isVisible())
        self.assertIs(child.care_partner, adult)
        self.assertEqual(child.care_lock_mode, "comfort")
        self.assertEqual(child.care_lock_end_time, 45.0)
        self.assertEqual(adult.state, "idle")
        self.assertEqual(child.state, "idle")
        self.assertEqual(adult.care_companion_animation_calls, 1)
        self.assertEqual(adult.ensure_candidate_animation_args, [])
        self.assertEqual(child.ensure_candidate_animation_args, [[("idle", "comfort")]])

    def test_finish_care_mode_success_releases_child_and_starts_recovery(self):
        adult = FakeAdult()
        child = FakeChild()
        child.visible = False
        adult.care_mode = "moving_interaction"
        adult.care_target = child
        adult.is_hugging = True
        adult.care_move_direction = 1

        SOCIAL_CARE_EFFECTS.finish_care_mode(adult, success=True, now=50.0)

        self.assertIs(adult.released_child, child)
        self.assertTrue(child.isVisible())
        self.assertTrue(child.clear_care_lock_called)
        self.assertEqual(child.mood_score, 65)
        self.assertTrue(child.pop_heart_called)
        self.assertEqual(child.recovery_started_at, 50.0)
        self.assertFalse(adult.is_hugging)
        self.assertEqual(adult.care_mode, "none")
        self.assertIsNone(adult.care_target)
        self.assertEqual(adult.care_plan, "auto")
        self.assertEqual(adult.care_cooldown_end, 54.0)
        self.assertEqual(adult.changed_state_args, [("idle", "stand")])

    def test_cancel_care_mode_restores_child_without_reward(self):
        adult = FakeAdult()
        child = FakeChild()
        child.visible = False
        adult.care_mode = "moving_interaction"
        adult.care_target = child
        adult.is_hugging = True

        SOCIAL_CARE_EFFECTS.cancel_care_mode(adult)

        self.assertIs(adult.released_child, child)
        self.assertTrue(child.isVisible())
        self.assertTrue(child.clear_care_lock_called)
        self.assertFalse(adult.is_hugging)
        self.assertEqual(adult.care_mode, "none")
        self.assertIsNone(adult.care_target)
        self.assertEqual(adult.care_plan, "auto")


if __name__ == "__main__":
    unittest.main()
