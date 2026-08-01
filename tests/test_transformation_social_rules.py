import unittest

from tanuki_core.transformation_social_rules import (
    amplify_transformed_rudolf_positive_relation_delta,
    get_transformed_rudolf_social_cooldown,
    get_transformed_rudolf_social_distance,
    is_transformed_rudolf_social_pair,
    resolve_transformed_rudolf_influence,
)


class TransformationSocialRulesTests(unittest.TestCase):
    def test_only_selected_base_form_observers_receive_influence(self):
        self.assertTrue(
            is_transformed_rudolf_social_pair(
                observer_name="Air Groove",
                observer_form="base",
                target_name="Symboli Rudolf",
                target_form="transformed",
            )
        )
        self.assertFalse(
            is_transformed_rudolf_social_pair(
                observer_name="Tokai Teio",
                observer_form="transformed",
                target_name="Symboli Rudolf",
                target_form="transformed",
            )
        )
        self.assertFalse(
            is_transformed_rudolf_social_pair(
                observer_name="Sirius Symboli",
                observer_form="base",
                target_name="Symboli Rudolf",
                target_form="transformed",
            )
        )

    def test_influence_requires_visible_unblocked_target_in_range(self):
        active = resolve_transformed_rudolf_influence(
            observer_name="Tsurumaru Tsuyoshi",
            observer_form="base",
            target_name="Symboli Rudolf",
            target_form="transformed",
            target_visible=True,
            target_distance=280.0,
        )
        blocked = resolve_transformed_rudolf_influence(
            observer_name="Tsurumaru Tsuyoshi",
            observer_form="base",
            target_name="Symboli Rudolf",
            target_form="transformed",
            target_visible=True,
            target_distance=280.0,
            blocked_target_name="Symboli Rudolf",
        )

        self.assertTrue(active.active)
        self.assertGreater(active.observe_chance_bonus, 0.0)
        self.assertFalse(blocked.active)

    def test_social_range_and_cooldown_receive_moderate_adjustment(self):
        self.assertEqual(
            get_transformed_rudolf_social_distance(
                350.0,
                influenced=True,
            ),
            472.5,
        )
        self.assertEqual(
            get_transformed_rudolf_social_cooldown(
                10.0,
                influenced=True,
            ),
            6.5,
        )

    def test_only_positive_relation_rewards_are_amplified(self):
        positive = amplify_transformed_rudolf_positive_relation_delta(
            {"familiarity": 0.25, "attachment": 0.08},
            influenced=True,
        )
        awkward = amplify_transformed_rudolf_positive_relation_delta(
            {"trust": -0.08, "tension": 0.20},
            influenced=True,
        )

        self.assertEqual(
            positive,
            {"familiarity": 0.375, "attachment": 0.12},
        )
        self.assertEqual(
            awkward,
            {"trust": -0.08, "tension": 0.20},
        )


if __name__ == "__main__":
    unittest.main()
