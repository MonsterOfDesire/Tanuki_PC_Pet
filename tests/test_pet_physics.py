import unittest

from tanuki_core.pet_physics import (
    HARD_LANDING_REACTION_MOODS,
    compute_fall_mood_penalty,
    compute_gravity_step,
)


class PetPhysicsTests(unittest.TestCase):
    def test_hard_landing_penalty_scales_with_fall_ratio(self):
        short_fall = compute_fall_mood_penalty(90, 600)
        medium_fall = compute_fall_mood_penalty(270, 600)
        high_fall = compute_fall_mood_penalty(540, 600)

        self.assertLess(short_fall, medium_fall)
        self.assertLess(medium_fall, high_fall)
        self.assertAlmostEqual(medium_fall, 41.75)

    def test_window_top_like_drop_reaches_about_fifty_mood_penalty(self):
        penalty = compute_fall_mood_penalty(336, 560)

        self.assertGreaterEqual(penalty, 50.0)
        self.assertLess(penalty, 60.0)

    def test_adult_fall_penalty_is_half_of_child_penalty(self):
        child_penalty = compute_fall_mood_penalty(336, 560, is_adult=False)
        adult_penalty = compute_fall_mood_penalty(336, 560, is_adult=True)

        self.assertAlmostEqual(adult_penalty, child_penalty * 0.5)

    def test_gravity_step_tracks_fall_origin_while_airborne(self):
        result = compute_gravity_step(
            current_y=100,
            current_vy=0.0,
            gravity=1.2,
            floor_top_y=400,
            bounce=-0.3,
            fall_origin_y=None,
            max_fall_distance=400,
        )

        self.assertEqual(result.fall_origin_y, 100)
        self.assertGreater(result.next_y, 100)

    def test_hard_landing_applies_penalty_and_bounce(self):
        result = compute_gravity_step(
            current_y=304,
            current_vy=16.0,
            gravity=1.2,
            floor_top_y=320,
            bounce=-0.3,
            fall_origin_y=40,
            max_fall_distance=320,
            is_adult=False,
        )

        self.assertLess(result.next_vy, 0.0)
        self.assertGreater(result.mood_penalty, 12.0)
        self.assertEqual(result.reaction_moods, HARD_LANDING_REACTION_MOODS)
        self.assertIsNone(result.fall_origin_y)

    def test_soft_landing_bounces_without_penalty(self):
        result = compute_gravity_step(
            current_y=300,
            current_vy=4.0,
            gravity=1.2,
            floor_top_y=304,
            bounce=-0.3,
            fall_origin_y=260,
            max_fall_distance=304,
            is_adult=False,
        )

        self.assertLess(result.next_vy, 0.0)
        self.assertEqual(result.mood_penalty, 0.0)
        self.assertEqual(result.reaction_moods, ())


if __name__ == "__main__":
    unittest.main()
