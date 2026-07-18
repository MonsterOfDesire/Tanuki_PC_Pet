import unittest

from tanuki_core.pet_perception_rules import NearbyPetObservation, derive_situation_tag, summarize_perception


class PetPerceptionRuleTests(unittest.TestCase):
    def test_summarize_perception_tracks_nearest_visible_and_distressed_targets(self):
        snapshot = summarize_perception(
            (
                NearbyPetObservation("Symboli Rudolf", 180.0, True, is_visible=True, is_distressed=False),
                NearbyPetObservation("Tokai Teio", 120.0, False, is_visible=True, is_distressed=True),
                NearbyPetObservation("Air Groove", 240.0, True, is_visible=False, is_distressed=False),
            ),
            anchor="floor",
            support_surface="desktop_floor",
            dragging=False,
            is_angry_locked=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            care_lock_active=False,
            vertical_velocity=0.0,
            is_adult=True,
            window_perch_available=True,
            window_flight_target_available=False,
        )

        self.assertEqual(snapshot.nearest_visible_pet_name, "Tokai Teio")
        self.assertEqual(snapshot.nearest_distressed_child_name, "Tokai Teio")
        self.assertEqual(snapshot.visible_adult_count, 1)
        self.assertEqual(snapshot.visible_child_count, 1)
        self.assertTrue(snapshot.window_perch_available)

    def test_situation_tag_prioritizes_lock_and_care_over_social(self):
        self.assertEqual(
            derive_situation_tag(
                dragging=True,
                is_angry_locked=False,
                care_mode="none",
                social_mode="following",
                is_recovering=False,
                care_lock_active=False,
                vertical_velocity=0.0,
                anchor="floor",
                is_adult=False,
                has_nearest_visible_pet=True,
                has_nearest_distressed_child=False,
            ),
            "locked",
        )
        self.assertEqual(
            derive_situation_tag(
                dragging=False,
                is_angry_locked=False,
                care_mode="none",
                social_mode="none",
                is_recovering=False,
                care_lock_active=False,
                vertical_velocity=0.0,
                anchor="floor",
                is_adult=True,
                has_nearest_visible_pet=True,
                has_nearest_distressed_child=True,
            ),
            "care",
        )

    def test_air_anchor_or_vertical_velocity_marks_hazard(self):
        snapshot = summarize_perception(
            (),
            anchor="air",
            support_surface="air",
            dragging=False,
            is_angry_locked=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            care_lock_active=False,
            vertical_velocity=2.0,
            is_adult=False,
            window_perch_available=False,
            window_flight_target_available=True,
        )

        self.assertEqual(snapshot.situation_tag, "hazard")

    def test_visible_neighbor_without_active_social_stays_stable(self):
        snapshot = summarize_perception(
            (NearbyPetObservation("Tokai Teio", 120.0, False, is_visible=True, is_distressed=False),),
            anchor="floor",
            support_surface="desktop_floor",
            dragging=False,
            is_angry_locked=False,
            care_mode="none",
            social_mode="none",
            is_recovering=False,
            care_lock_active=False,
            vertical_velocity=0.0,
            is_adult=False,
            window_perch_available=False,
            window_flight_target_available=False,
        )

        self.assertEqual(snapshot.situation_tag, "stable")


if __name__ == "__main__":
    unittest.main()
