import unittest

from tanuki_core.pet_social_catalog import (
    get_adult_companion_candidates,
    get_child_comfort_candidates,
    get_child_recovery_candidates,
    get_expression_preferred_moods,
    get_idle_candidates,
    get_move_candidates,
)


class ChildCandidateCatalogTests(unittest.TestCase):
    def test_tokai_teio_uses_character_specific_comfort_candidates(self):
        self.assertEqual(
            get_child_comfort_candidates("Tokai Teio"),
            [
                ("idle", "side_eat_candy"),
                ("idle", "sit"),
                ("idle", "lie"),
                ("idle", "side"),
            ],
        )

    def test_other_children_use_default_comfort_candidates(self):
        self.assertEqual(
            get_child_comfort_candidates("Tsurumaru Tsuyoshi"),
            [
                ("idle", "drink"),
                ("idle", "eat"),
                ("idle", "side_hug"),
                ("idle", "side_rub"),
                ("idle", "sit_no"),
                ("idle", "squat"),
                ("idle", "side"),
            ],
        )

    def test_tokai_teio_uses_character_specific_recovery_candidates(self):
        self.assertEqual(
            get_child_recovery_candidates("Tokai Teio"),
            [
                ("move", "walk_drink"),
                ("idle", "dance_uma_drink"),
                ("idle", "side_eat_candy"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "sit"),
            ],
        )

    def test_other_children_reuse_comfort_candidates_for_recovery(self):
        self.assertEqual(
            get_child_recovery_candidates("Tsurumaru Tsuyoshi"),
            get_child_comfort_candidates("Tsurumaru Tsuyoshi"),
        )


class SharedCandidateCatalogTests(unittest.TestCase):
    def test_adult_companion_candidates_are_character_specific(self):
        self.assertEqual(
            get_adult_companion_candidates("Symboli Rudolf"),
            [
                ("idle", "sit"),
                ("idle", "sit_read"),
                ("idle", "rest"),
                ("idle", "squat"),
            ],
        )
        self.assertEqual(
            get_adult_companion_candidates("Sirius Symboli"),
            [
                ("idle", "sit"),
                ("idle", "sit_talk"),
                ("idle", "side"),
            ],
        )
        self.assertEqual(
            get_adult_companion_candidates("Air Groove"),
            [("idle", "sit"), ("idle", "side")],
        )
        self.assertEqual(get_adult_companion_candidates("Unknown"), [])

    def test_shared_candidate_lists_match_existing_behavior(self):
        self.assertEqual(
            get_move_candidates(),
            [
                ("move", "walk"),
                ("move", "run"),
                ("move", "jog"),
                ("move", "sneak"),
                ("move", "climb"),
                ("move", "fly"),
                ("move", "fly_up"),
            ],
        )
        self.assertEqual(
            get_idle_candidates(),
            [
                ("idle", "stand"),
                ("idle", "side"),
                ("idle", "sit"),
                ("idle", "rest"),
                ("idle", "lie"),
                ("idle", "squat"),
                ("idle", "observe"),
                ("idle", "photo"),
                ("idle", "photo_ready"),
                ("idle", "dance_three"),
                ("idle", "dance_uma"),
                ("idle", "hear"),
                ("idle", "knock"),
                ("idle", "get"),
                ("idle", "sleep"),
            ],
        )

    def test_catalog_returns_fresh_lists_each_time(self):
        comfort = get_child_comfort_candidates("Tokai Teio")
        comfort.append(("idle", "fake"))

        self.assertNotIn(("idle", "fake"), get_child_comfort_candidates("Tokai Teio"))
        self.assertNotIn(("idle", "fake"), get_idle_candidates())

    def test_expression_catalog_returns_preferred_moods(self):
        self.assertEqual(
            get_expression_preferred_moods("relation_watch"),
            ["glance", "think", "smile", "happy", "confidence", "cool"],
        )
        self.assertEqual(
            get_expression_preferred_moods("relation_close"),
            ["smile", "happy", "confidence", "cool", "glance", "think"],
        )
        self.assertEqual(get_expression_preferred_moods("ambient"), [])


if __name__ == "__main__":
    unittest.main()
