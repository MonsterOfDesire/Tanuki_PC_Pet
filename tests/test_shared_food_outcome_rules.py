import unittest
from dataclasses import replace

from tanuki_core.shared_food_outcome_rules import (
    get_shared_food_consumer_names,
    preflight_shared_food_outcomes,
    resolve_shared_food_outcome,
)
from tanuki_core.shared_food_profiles import (
    SHARED_FOOD_OUTCOME_HOLDER_GIVES,
    SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
    SHARED_FOOD_OUTCOME_KEYS,
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
    SHARED_FOOD_PROFILES,
    get_shared_food_profile_for_item,
)


class SharedFoodOutcomeRulesTests(unittest.TestCase):
    def test_all_profile_directions_support_all_outcomes(self):
        for profile in SHARED_FOOD_PROFILES:
            for holder_name in profile.allowed_holders:
                for partner_name in profile.partner_names_for_holder(holder_name):
                    self.assertEqual(
                        preflight_shared_food_outcomes(
                            profile,
                            holder_name,
                            partner_name,
                        ),
                        SHARED_FOOD_OUTCOME_KEYS,
                    )

    def test_preflight_filters_outcomes_by_required_capabilities(self):
        profile = get_shared_food_profile_for_item("ramen")
        holder_name = "Symboli Rudolf"
        partner_name = "Tokai Teio"
        holder = profile.capabilities_for(holder_name)
        partner = profile.capabilities_for(partner_name)

        holder_without_consume = replace(holder, consume_candidates=())
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                holder_capabilities=holder_without_consume,
            ),
            (SHARED_FOOD_OUTCOME_HOLDER_GIVES,),
        )

        partner_without_consume = replace(partner, consume_candidates=())
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                partner_capabilities=partner_without_consume,
            ),
            (SHARED_FOOD_OUTCOME_HOLDER_KEEPS,),
        )

        partner_without_approach = replace(partner, approach_candidates=())
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                partner_capabilities=partner_without_approach,
            ),
            (),
        )

    def test_request_and_watch_are_required_for_the_decision_stage(self):
        profile = get_shared_food_profile_for_item("tea")
        holder_name = "Symboli Rudolf"
        partner_name = "Air Groove"
        partner = replace(
            profile.capabilities_for(partner_name),
            request_candidates=(),
        )

        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                partner_capabilities=partner,
            ),
            (),
        )

        holder = replace(
            profile.capabilities_for(holder_name),
            watch_candidates=(),
        )
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                holder_capabilities=holder,
            ),
            (),
        )

    def test_react_capability_filters_only_affected_outcomes(self):
        profile = get_shared_food_profile_for_item("ramen")
        holder_name = "Symboli Rudolf"
        partner_name = "Tokai Teio"

        holder = replace(profile.capabilities_for(holder_name), react_candidates=())
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                holder_capabilities=holder,
            ),
            (SHARED_FOOD_OUTCOME_HOLDER_KEEPS,),
        )

        partner = replace(profile.capabilities_for(partner_name), react_candidates=())
        self.assertEqual(
            preflight_shared_food_outcomes(
                profile,
                holder_name,
                partner_name,
                partner_capabilities=partner,
            ),
            (SHARED_FOOD_OUTCOME_HOLDER_GIVES,),
        )

    def test_explicit_available_outcomes_cannot_bypass_preflight(self):
        profile = get_shared_food_profile_for_item("ramen")
        partner_name = "Tokai Teio"
        partner = replace(
            profile.capabilities_for(partner_name),
            consume_candidates=(),
        )

        result = resolve_shared_food_outcome(
            profile,
            "Symboli Rudolf",
            partner_name,
            roll=0.0,
            available_outcomes=(SHARED_FOOD_OUTCOME_SHARE_BOTH,),
            partner_capabilities=partner,
        )

        self.assertFalse(result.resolved)
        self.assertEqual(result.reason, "no_available_outcomes")

    def test_resolver_rejects_invalid_pair(self):
        profile = get_shared_food_profile_for_item("honey")

        result = resolve_shared_food_outcome(
            profile,
            "Tsurumaru Tsuyoshi",
            "Sirius Symboli",
            roll=0.0,
        )

        self.assertFalse(result.resolved)
        self.assertEqual(result.reason, "invalid_pair")

    def test_resolver_uses_profile_weight_boundaries(self):
        profile = get_shared_food_profile_for_item("ramen")
        cases = (
            (0.0, SHARED_FOOD_OUTCOME_SHARE_BOTH),
            (0.5999, SHARED_FOOD_OUTCOME_SHARE_BOTH),
            (0.60, SHARED_FOOD_OUTCOME_HOLDER_KEEPS),
            (0.7999, SHARED_FOOD_OUTCOME_HOLDER_KEEPS),
            (0.80, SHARED_FOOD_OUTCOME_HOLDER_GIVES),
            (1.0, SHARED_FOOD_OUTCOME_HOLDER_GIVES),
        )

        for roll, expected in cases:
            with self.subTest(roll=roll):
                result = resolve_shared_food_outcome(
                    profile,
                    "Symboli Rudolf",
                    "Tokai Teio",
                    roll=roll,
                )
                self.assertEqual(result.outcome_key, expected)

    def test_resolver_renormalizes_available_outcomes(self):
        profile = get_shared_food_profile_for_item("ramen")

        keeps = resolve_shared_food_outcome(
            profile,
            "Symboli Rudolf",
            "Tokai Teio",
            roll=0.49,
            available_outcomes=(
                SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
                SHARED_FOOD_OUTCOME_HOLDER_GIVES,
            ),
        )
        gives = resolve_shared_food_outcome(
            profile,
            "Symboli Rudolf",
            "Tokai Teio",
            roll=0.50,
            available_outcomes=(
                SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
                SHARED_FOOD_OUTCOME_HOLDER_GIVES,
            ),
        )

        self.assertEqual(keeps.outcome_key, SHARED_FOOD_OUTCOME_HOLDER_KEEPS)
        self.assertEqual(gives.outcome_key, SHARED_FOOD_OUTCOME_HOLDER_GIVES)
        self.assertAlmostEqual(keeps.weight_for(SHARED_FOOD_OUTCOME_HOLDER_KEEPS), 0.5)
        self.assertAlmostEqual(keeps.weight_for(SHARED_FOOD_OUTCOME_HOLDER_GIVES), 0.5)

    def test_resolver_accepts_future_weight_multipliers(self):
        profile = get_shared_food_profile_for_item("ramen")

        keeps = resolve_shared_food_outcome(
            profile,
            "Symboli Rudolf",
            "Tokai Teio",
            roll=0.74,
            weight_multipliers_by_key={
                SHARED_FOOD_OUTCOME_SHARE_BOTH: 0.0,
                SHARED_FOOD_OUTCOME_HOLDER_KEEPS: 3.0,
            },
        )
        gives = resolve_shared_food_outcome(
            profile,
            "Symboli Rudolf",
            "Tokai Teio",
            roll=0.75,
            weight_multipliers_by_key={
                SHARED_FOOD_OUTCOME_SHARE_BOTH: 0.0,
                SHARED_FOOD_OUTCOME_HOLDER_KEEPS: 3.0,
            },
        )

        self.assertEqual(keeps.outcome_key, SHARED_FOOD_OUTCOME_HOLDER_KEEPS)
        self.assertEqual(gives.outcome_key, SHARED_FOOD_OUTCOME_HOLDER_GIVES)
        self.assertAlmostEqual(keeps.weight_for(SHARED_FOOD_OUTCOME_HOLDER_KEEPS), 0.75)

    def test_resolver_reports_when_all_adjusted_weights_are_zero(self):
        profile = get_shared_food_profile_for_item("tea")

        result = resolve_shared_food_outcome(
            profile,
            "Air Groove",
            "Symboli Rudolf",
            roll=0.5,
            weight_multipliers_by_key={key: 0.0 for key in SHARED_FOOD_OUTCOME_KEYS},
        )

        self.assertFalse(result.resolved)
        self.assertEqual(result.reason, "no_positive_outcome_weights")

    def test_consumer_names_follow_resolved_role_order(self):
        self.assertEqual(
            get_shared_food_consumer_names(
                ("partner", "holder"),
                "Sirius Symboli",
                "Tokai Teio",
            ),
            ("Tokai Teio", "Sirius Symboli"),
        )
        self.assertEqual(
            get_shared_food_consumer_names(
                ("partner",),
                "Sirius Symboli",
                "Tokai Teio",
            ),
            ("Tokai Teio",),
        )


if __name__ == "__main__":
    unittest.main()
