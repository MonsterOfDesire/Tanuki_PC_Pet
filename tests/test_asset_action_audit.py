import json
import tempfile
import unittest
from pathlib import Path

from tanuki_core.asset_action_audit import (
    AssetActionRecord,
    CandidateRequirement,
    audit_candidate_context_requirements,
    audit_random_manifest_coverage,
    audit_candidate_requirements,
    build_asset_action_audit_report,
    collect_hardcoded_requirements,
    parse_asset_filename,
)


class AssetActionAuditTests(unittest.TestCase):
    def test_project_assets_have_no_hardcoded_candidate_issues(self):
        assets_dir = Path(__file__).resolve().parents[1] / "assets_cropped"

        report = build_asset_action_audit_report(assets_dir)

        self.assertEqual(report.candidate_issues, ())

    def test_parse_asset_filename_matches_runtime_rule(self):
        purpose, action, mood = parse_asset_filename("idle_side_sit_ramen-hard-happy.gif")

        self.assertEqual(purpose, "idle")
        self.assertEqual(action, "side_sit_ramen")
        self.assertEqual(mood, "hard-happy")

    def test_report_lists_inventory_and_manifest_sync_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            character_dir = root / "Air Groove"
            character_dir.mkdir()
            (character_dir / "idle_drink-happy.gif").write_bytes(b"")
            (character_dir / "idle_drink-sad.gif").write_bytes(b"")
            (character_dir / "move_walk-happy.gif").write_bytes(b"")
            (character_dir / "manifest_edit.json").write_text(
                json.dumps(
                    {
                        "idle_drink-happy.gif": {"contexts": ["random"]},
                        "stale_entry.gif": {"contexts": ["random"]},
                    }
                ),
                encoding="utf-8",
            )

            report = build_asset_action_audit_report(root)

        inventory = report.inventories["Air Groove"]
        manifest_result = report.manifest_results[0]
        self.assertEqual(inventory.total_assets, 3)
        self.assertEqual(inventory.purpose_counts, {"idle": 2, "move": 1})
        self.assertEqual(inventory.action_moods[("idle", "drink")], ("happy", "sad"))
        self.assertIn("stale_entry.gif", manifest_result.manifest_missing_files)
        self.assertIn("idle_drink-sad.gif", manifest_result.assets_missing_manifest)
        self.assertIn("move_walk-happy.gif", manifest_result.assets_missing_manifest)

    def test_candidate_audit_reports_missing_actions_and_empty_roles(self):
        records = (
            AssetActionRecord(
                character="Symboli Rudolf",
                file_name="idle_get-happy.gif",
                purpose="idle",
                action="get",
                mood="happy",
            ),
        )
        requirements = (
            CandidateRequirement(
                feature="offer",
                role="direct_offer_preview",
                character="Symboli Rudolf",
                candidates=(("idle", "get"),),
            ),
            CandidateRequirement(
                feature="shared_food",
                role="holder_hold",
                character="Symboli Rudolf",
                candidates=(),
            ),
            CandidateRequirement(
                feature="offer",
                role="exact_stage",
                character="Symboli Rudolf",
                candidates=(("idle", "get"),),
                exact_mood="sad",
            ),
            CandidateRequirement(
                feature="offer",
                role="missing_action",
                character="Symboli Rudolf",
                candidates=(("move", "run"),),
            ),
        )

        issues = audit_candidate_requirements(records, requirements)
        issue_kinds = [issue.issue for issue in issues]

        self.assertNotIn("direct_offer_preview", [issue.role for issue in issues])
        self.assertIn("no_candidates_defined", issue_kinds)
        self.assertIn("missing_exact_mood", issue_kinds)
        self.assertIn("missing_action", issue_kinds)

    def test_random_manifest_coverage_reports_complete_idle_move_bands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            character_dir = root / "Symboli Rudolf"
            character_dir.mkdir()
            for file_name in (
                "idle_stand-happy.gif",
                "idle_stand-sad.gif",
                "idle_stand-cry.gif",
                "move_walk-happy.gif",
                "move_walk-sad.gif",
                "move_walk-cry.gif",
            ):
                (character_dir / file_name).write_bytes(b"")
            (character_dir / "manifest_edit.json").write_text(
                json.dumps(
                    {
                        "animations": {
                            "idle_stand-happy.gif": {"band": ["normal"], "contexts": ["random"]},
                            "idle_stand-sad.gif": {"band": ["low"], "contexts": ["random"]},
                            "idle_stand-cry.gif": {"band": ["severe"], "contexts": ["random"]},
                            "move_walk-happy.gif": {"band": ["normal"], "contexts": ["random"]},
                            "move_walk-sad.gif": {"band": ["low"], "contexts": ["random"]},
                            "move_walk-cry.gif": {"band": ["severe"], "contexts": ["random"]},
                        },
                    }
                ),
                encoding="utf-8",
            )
            records = (
                AssetActionRecord("Symboli Rudolf", "idle_stand-happy.gif", "idle", "stand", "happy"),
                AssetActionRecord("Symboli Rudolf", "idle_stand-sad.gif", "idle", "stand", "sad"),
                AssetActionRecord("Symboli Rudolf", "idle_stand-cry.gif", "idle", "stand", "cry"),
                AssetActionRecord("Symboli Rudolf", "move_walk-happy.gif", "move", "walk", "happy"),
                AssetActionRecord("Symboli Rudolf", "move_walk-sad.gif", "move", "walk", "sad"),
                AssetActionRecord("Symboli Rudolf", "move_walk-cry.gif", "move", "walk", "cry"),
            )

            coverage, issues = audit_random_manifest_coverage(root, records)

        self.assertFalse(issues)
        coverage_by_key = {
            (entry.character, entry.purpose, entry.band): entry.asset_count
            for entry in coverage
        }
        self.assertEqual(coverage_by_key[("Symboli Rudolf", "idle", "normal")], 1)
        self.assertEqual(coverage_by_key[("Symboli Rudolf", "move", "severe")], 1)

    def test_random_manifest_coverage_reports_missing_band(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            character_dir = root / "Tokai Teio"
            character_dir.mkdir()
            (character_dir / "idle_stand-happy.gif").write_bytes(b"")
            (character_dir / "move_walk-happy.gif").write_bytes(b"")
            (character_dir / "manifest_edit.json").write_text(
                json.dumps(
                    {
                        "idle_stand-happy.gif": {"band": ["normal"], "contexts": ["random"]},
                        "move_walk-happy.gif": {"band": ["normal"], "contexts": ["random"]},
                    }
                ),
                encoding="utf-8",
            )
            records = (
                AssetActionRecord("Tokai Teio", "idle_stand-happy.gif", "idle", "stand", "happy"),
                AssetActionRecord("Tokai Teio", "move_walk-happy.gif", "move", "walk", "happy"),
            )

            _coverage, issues = audit_random_manifest_coverage(root, records)

        missing = {(issue.character, issue.purpose, issue.band) for issue in issues}
        self.assertIn(("Tokai Teio", "idle", "low"), missing)
        self.assertIn(("Tokai Teio", "move", "severe"), missing)

    def test_relation_contexts_are_not_reported_as_hardcoded_requirements(self):
        requirements = collect_hardcoded_requirements()

        self.assertNotIn("relation", {requirement.feature for requirement in requirements})

    def test_random_catalog_candidates_are_not_hardcoded_requirements(self):
        requirements = collect_hardcoded_requirements()

        self.assertNotIn("random", {requirement.feature for requirement in requirements})

    def test_shared_food_audit_reads_character_capability_pools(self):
        requirements = tuple(
            requirement
            for requirement in collect_hardcoded_requirements()
            if requirement.feature == "shared_food"
        )

        self.assertEqual(
            {requirement.role for requirement in requirements},
            {"hold", "approach", "consume", "request", "watch", "react"},
        )
        self.assertEqual(
            {requirement.item_kind for requirement in requirements},
            {"ramen", "tea", "honey"},
        )
        self.assertTrue(all(requirement.candidates for requirement in requirements))
        self.assertTrue(
            all("capabilities_by_name" in requirement.source for requirement in requirements)
        )
        self.assertEqual(
            {requirement.required_context for requirement in requirements},
            {
                "shared_food_hold",
                "shared_food_approach",
                "shared_food_consume",
                "shared_food_request",
                "shared_food_watch",
                "shared_food_react",
            },
        )
        self.assertTrue(all(requirement.preferred_moods for requirement in requirements))

    def test_context_audit_requires_preferred_mood_with_shared_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            character_dir = root / "Symboli Rudolf"
            character_dir.mkdir()
            records = (
                AssetActionRecord(
                    "Symboli Rudolf",
                    "move_walk-happy.gif",
                    "move",
                    "walk",
                    "happy",
                ),
                AssetActionRecord(
                    "Symboli Rudolf",
                    "move_walk-sad.gif",
                    "move",
                    "walk",
                    "sad",
                ),
            )
            requirement = CandidateRequirement(
                feature="shared_food",
                role="approach",
                character="Symboli Rudolf",
                candidates=(("move", "walk"),),
                item_kind="ramen",
                required_context="shared_food_approach",
                preferred_moods=("happy", "smile"),
            )
            (character_dir / "manifest_edit.json").write_text(
                json.dumps(
                    {
                        "animations": {
                            "move_walk-happy.gif": {
                                "contexts": ["window_walk"],
                            },
                            "move_walk-sad.gif": {
                                "contexts": ["shared_food_approach"],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            issues = audit_candidate_context_requirements(root, records, (requirement,))

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].issue, "missing_preferred_context")
            self.assertEqual(issues[0].required_context, "shared_food_approach")

            manifest_path = character_dir / "manifest_edit.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["animations"]["move_walk-happy.gif"]["contexts"].append(
                "shared_food_approach"
            )
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")

            self.assertFalse(
                audit_candidate_context_requirements(root, records, (requirement,))
            )


if __name__ == "__main__":
    unittest.main()
