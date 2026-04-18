import unittest

from tanuki_core.pet_collision_rules import (
    CollisionSnapshot,
    compute_collision_resolution,
)


class PetCollisionRuleTests(unittest.TestCase):
    def test_collision_resolution_pushes_subject_away(self):
        resolution = compute_collision_resolution(
            subject=CollisionSnapshot(center_x=100, center_y=100, radius=40, mass=1.0, is_adult=False),
            neighbors=[
                CollisionSnapshot(center_x=80, center_y=100, radius=40, mass=2.0, is_adult=True),
            ],
            mood_score=60.0,
        )

        self.assertGreater(resolution.delta_x, 0)
        self.assertEqual(resolution.colliding_adult_indices, (0,))

    def test_low_mood_reduces_collision_push_strength(self):
        subject = CollisionSnapshot(center_x=100, center_y=100, radius=40, mass=1.0, is_adult=False)
        neighbors = [CollisionSnapshot(center_x=80, center_y=100, radius=40, mass=2.0, is_adult=True)]

        normal = compute_collision_resolution(subject, neighbors, mood_score=60.0)
        low = compute_collision_resolution(subject, neighbors, mood_score=10.0)

        self.assertGreater(abs(normal.delta_x), abs(low.delta_x))

    def test_small_overlap_does_not_trigger_push(self):
        resolution = compute_collision_resolution(
            subject=CollisionSnapshot(center_x=100, center_y=100, radius=30, mass=1.0, is_adult=False),
            neighbors=[
                CollisionSnapshot(center_x=156, center_y=100, radius=30, mass=1.0, is_adult=True),
            ],
            mood_score=60.0,
        )

        self.assertEqual(resolution.delta_x, 0)
        self.assertEqual(resolution.colliding_adult_indices, ())


if __name__ == "__main__":
    unittest.main()
