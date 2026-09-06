import unittest

from tanuki_core.autonomous_offer_rules import (
    AutonomousOfferOpportunity,
    choose_autonomous_offer_opportunity,
)
from tanuki_core.achievement_gameplay_bridge import AchievementGameplayBridge


class AutonomousOfferRuleTests(unittest.TestCase):
    def test_weighted_selection_uses_one_stable_roll(self):
        opportunities = (
            AutonomousOfferOpportunity("ramen", "A", weight=1.0),
            AutonomousOfferOpportunity("tea", "B", weight=3.0),
        )

        self.assertEqual(
            choose_autonomous_offer_opportunity(
                opportunities,
                roll=0.10,
            ).actor_name,
            "A",
        )
        self.assertEqual(
            choose_autonomous_offer_opportunity(
                opportunities,
                roll=0.50,
            ).actor_name,
            "B",
        )

    def test_autonomous_sources_use_autonomous_achievement_eligibility(self):
        self.assertEqual(
            AchievementGameplayBridge._offer_execution_mode(
                "autonomous_offer"
            ),
            "autonomous",
        )
        self.assertEqual(
            AchievementGameplayBridge._offer_execution_mode(
                "autonomous_ground"
            ),
            "autonomous",
        )
        self.assertEqual(
            AchievementGameplayBridge._offer_execution_mode("offer_tray"),
            "player_gameplay",
        )


if __name__ == "__main__":
    unittest.main()
