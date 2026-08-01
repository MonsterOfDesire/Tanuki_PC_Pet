import unittest

from tanuki_core.pet_relationship_rules import (
    RelationshipFocus,
    advance_relationship_entry,
    choose_relationship_focus,
    derive_expression_state,
    derive_relational_situation_tag,
)
from tanuki_core.pet_runtime_state import RelationshipEntry


class PetRelationshipRuleTests(unittest.TestCase):
    def test_relationship_entry_gains_familiarity_from_proximity_and_trust_from_care(self):
        updated = advance_relationship_entry(
            RelationshipEntry(),
            distance=120.0,
            same_anchor=True,
            social_active=False,
            care_active=True,
            now=10.0,
        )

        self.assertGreater(updated.familiarity, 0.0)
        self.assertGreater(updated.trust, 0.0)
        self.assertGreater(updated.attachment, 0.0)
        self.assertEqual(updated.last_seen_at, 10.0)
        self.assertEqual(updated.last_interaction_at, 10.0)

    def test_choose_relationship_focus_prefers_active_target_then_nearest_visible(self):
        entries = {
            "Tokai Teio": RelationshipEntry(familiarity=12.0, trust=4.0, attachment=8.0, tension=1.0),
            "Symboli Rudolf": RelationshipEntry(familiarity=30.0, trust=18.0, attachment=22.0, tension=0.0),
        }
        focus = choose_relationship_focus(
            entries=entries,
            social_target_name="Tokai Teio",
            care_target_name="",
            observe_target_name="",
            observe_target_distance=0.0,
            observe_target_visible=False,
            nearest_visible_pet_name="Symboli Rudolf",
            nearest_visible_pet_distance=120.0,
            blocked_target_name="",
        )

        self.assertEqual(focus.target_name, "Tokai Teio")
        self.assertEqual(focus.familiarity, 12.0)

    def test_choose_relationship_focus_prefers_locked_observe_target_within_keep_distance(self):
        entries = {
            "Air Groove": RelationshipEntry(familiarity=14.0, trust=4.0, attachment=6.0, tension=0.0),
            "Tokai Teio": RelationshipEntry(familiarity=8.0, trust=1.0, attachment=0.0, tension=0.0),
        }

        focus = choose_relationship_focus(
            entries=entries,
            social_target_name="",
            care_target_name="",
            observe_target_name="Air Groove",
            observe_target_distance=240.0,
            observe_target_visible=True,
            nearest_visible_pet_name="Tokai Teio",
            nearest_visible_pet_distance=80.0,
            blocked_target_name="",
        )

        self.assertEqual(focus.target_name, "Air Groove")

    def test_choose_relationship_focus_ignores_far_nearest_visible_target(self):
        focus = choose_relationship_focus(
            entries={"Symboli Rudolf": RelationshipEntry(familiarity=20.0)},
            social_target_name="",
            care_target_name="",
            observe_target_name="",
            observe_target_distance=0.0,
            observe_target_visible=False,
            nearest_visible_pet_name="Symboli Rudolf",
            nearest_visible_pet_distance=340.0,
            blocked_target_name="",
        )

        self.assertEqual(focus.target_name, "")

    def test_choose_relationship_focus_accepts_explicit_extended_distance(self):
        focus = choose_relationship_focus(
            entries={
                "Symboli Rudolf": RelationshipEntry(
                    familiarity=20.0,
                )
            },
            nearest_visible_pet_name="Symboli Rudolf",
            nearest_visible_pet_distance=300.0,
            nearest_visible_max_distance=320.0,
        )

        self.assertEqual(focus.target_name, "Symboli Rudolf")

    def test_choose_relationship_focus_ignores_blocked_same_target(self):
        entries = {
            "Tokai Teio": RelationshipEntry(familiarity=12.0, trust=4.0, attachment=8.0, tension=1.0),
        }

        focus = choose_relationship_focus(
            entries=entries,
            social_target_name="",
            care_target_name="",
            observe_target_name="",
            observe_target_distance=0.0,
            observe_target_visible=False,
            nearest_visible_pet_name="Tokai Teio",
            nearest_visible_pet_distance=120.0,
            blocked_target_name="Tokai Teio",
        )

        self.assertEqual(focus.target_name, "")

    def test_expression_state_uses_social_and_care_contexts_before_ambient_relation(self):
        social_expression = derive_expression_state(
            situation_tag="social",
            social_mode="following",
            care_mode="none",
            care_lock_active=False,
            focus=RelationshipFocus(target_name="Symboli Rudolf", familiarity=30.0, trust=15.0, attachment=25.0),
        )
        ambient_expression = derive_expression_state(
            situation_tag="stable",
            social_mode="none",
            care_mode="none",
            care_lock_active=False,
            focus=RelationshipFocus(target_name="Tokai Teio", familiarity=18.0, trust=8.0, attachment=30.0),
        )

        self.assertEqual(social_expression.animation_context, "social_follow")
        self.assertEqual(social_expression.relation_overlay, "star")
        self.assertEqual(ambient_expression.animation_context, "relation_close")
        self.assertTrue(ambient_expression.look_at_target)

    def test_expression_state_enters_relation_watch_with_lower_familiarity_threshold(self):
        expression = derive_expression_state(
            situation_tag="stable",
            social_mode="none",
            care_mode="none",
            care_lock_active=False,
            focus=RelationshipFocus(target_name="Tsurumaru Tsuyoshi", familiarity=6.0, trust=1.0, attachment=0.0),
        )

        self.assertEqual(expression.animation_context, "relation_watch")
        self.assertTrue(expression.look_at_target)

    def test_relational_situation_tag_promotes_stable_to_social_for_close_focus(self):
        situation_tag = derive_relational_situation_tag(
            "stable",
            focus=RelationshipFocus(target_name="Symboli Rudolf", familiarity=6.0, trust=1.0, attachment=0.0),
            focus_distance=180.0,
        )
        far_tag = derive_relational_situation_tag(
            "stable",
            focus=RelationshipFocus(target_name="Symboli Rudolf", familiarity=6.0, trust=1.0, attachment=0.0),
            focus_distance=260.0,
        )

        self.assertEqual(situation_tag, "social")
        self.assertEqual(far_tag, "stable")


if __name__ == "__main__":
    unittest.main()
