import unittest
from pathlib import Path

from tanuki_core.asset_action_audit import build_asset_action_audit_report
from tanuki_core.manifest_xlsx_converter import validate_manifest_xlsx
from tanuki_core.shared_food_outcome_rules import preflight_shared_food_outcomes
from tanuki_core.shared_food_profiles import (
    SHARED_FOOD_OUTCOME_KEYS,
    SHARED_FOOD_PROFILES,
)
from tanuki_core.validation import load_manifest_entries


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets_cropped"


class SharedFoodAssetIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit_report = build_asset_action_audit_report(ASSETS_DIR)

    def test_real_assets_cover_every_shared_food_context_requirement(self):
        requirements = tuple(
            requirement
            for requirement in self.audit_report.requirements
            if requirement.feature == "shared_food"
        )
        issues = tuple(
            issue
            for issue in self.audit_report.candidate_issues
            if issue.feature == "shared_food"
        )

        self.assertEqual(len(requirements), 36)
        self.assertEqual(issues, ())

    def test_shared_food_workbooks_match_runtime_json(self):
        character_names = sorted(
            {
                character_name
                for profile in SHARED_FOOD_PROFILES
                for character_name in profile.capabilities_by_name
            }
        )
        for character_name in character_names:
            with self.subTest(character=character_name):
                character_dir = ASSETS_DIR / character_name
                xlsx_entries, xlsx_issues = validate_manifest_xlsx(character_dir)
                json_entries, json_warnings = load_manifest_entries(
                    str(character_dir / "manifest_edit.json")
                )

                self.assertEqual(xlsx_issues, ())
                self.assertEqual(json_warnings, [])
                self.assertEqual(xlsx_entries, json_entries)

    def test_all_six_real_profile_directions_support_all_outcomes(self):
        directions = []
        for profile in SHARED_FOOD_PROFILES:
            for holder_name in profile.allowed_holders:
                for partner_name in profile.partner_names_for_holder(holder_name):
                    directions.append((profile.item_kind, holder_name, partner_name))
                    self.assertEqual(
                        preflight_shared_food_outcomes(
                            profile,
                            holder_name,
                            partner_name,
                        ),
                        SHARED_FOOD_OUTCOME_KEYS,
                    )

        self.assertEqual(len(directions), 6)


if __name__ == "__main__":
    unittest.main()
