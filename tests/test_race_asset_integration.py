import json
import unittest
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets_cropped"
RACE_CONTEXT_PREFIX = "activity_race_"


def load_entries(character_name, *, transformed=False):
    path = ASSETS_DIR / character_name
    if transformed:
        path /= "transformed"
    payload = json.loads(
        (path / "manifest_edit.json").read_text(encoding="utf-8")
    )
    return payload["animations"]


def context_bands(entries, context):
    bands = set()
    for metadata in entries.values():
        if context in metadata.get("contexts", ()):
            bands.update(metadata.get("band", ()))
    return bands


def context_filenames(entries, context):
    return {
        filename
        for filename, metadata in entries.items()
        if context in metadata.get("contexts", ())
    }


class RaceAssetIntegrationTests(unittest.TestCase):
    def assert_context_has_band(self, entries, context, band):
        self.assertIn(
            band,
            context_bands(entries, context),
            f"{context} missing {band}",
        )

    def test_base_racers_cover_normal_and_low_runtime_policy(self):
        common_phase_bands = {
            "activity_race_challenge": ("normal", "low"),
            "activity_race_consider": ("normal", "low"),
            "activity_race_accept": ("normal", "low"),
            "activity_race_to_start": ("normal", "low"),
            "activity_race_ready": ("normal", "low"),
            "activity_race_running": ("normal", "low"),
            "activity_race_recovery": ("normal", "low"),
            "activity_race_finish_win": ("normal",),
            "activity_race_finish_lose": ("low",),
        }
        for character_name in (
            "Tokai Teio",
            "Sirius Symboli",
            "Symboli Rudolf",
        ):
            entries = load_entries(character_name)
            for context, bands in common_phase_bands.items():
                for band in bands:
                    with self.subTest(
                        character=character_name,
                        context=context,
                        band=band,
                    ):
                        self.assert_context_has_band(entries, context, band)

    def test_decline_policy_matches_each_character_manifest(self):
        teio = load_entries("Tokai Teio")
        sirius = load_entries("Sirius Symboli")
        rudolf = load_entries("Symboli Rudolf")

        self.assertNotIn(
            "normal",
            context_bands(teio, "activity_race_decline"),
        )
        self.assert_context_has_band(teio, "activity_race_decline", "low")
        for entries in (sirius, rudolf):
            self.assert_context_has_band(
                entries,
                "activity_race_decline",
                "normal",
            )
            self.assert_context_has_band(
                entries,
                "activity_race_decline",
                "low",
            )

    def test_adults_have_normal_finish_lose_for_appreciative_teio_loss(self):
        for character_name in ("Sirius Symboli", "Symboli Rudolf"):
            with self.subTest(character=character_name):
                self.assert_context_has_band(
                    load_entries(character_name),
                    "activity_race_finish_lose",
                    "normal",
                )

    def test_consider_context_uses_stationary_idle_assets(self):
        variants = (
            ("Tokai Teio", False),
            ("Sirius Symboli", False),
            ("Symboli Rudolf", False),
            ("Symboli Rudolf", True),
        )
        for character_name, transformed in variants:
            filenames = context_filenames(
                load_entries(character_name, transformed=transformed),
                "activity_race_consider",
            )
            with self.subTest(
                character=character_name,
                transformed=transformed,
            ):
                self.assertTrue(filenames)
                self.assertTrue(
                    all(filename.startswith("idle_") for filename in filenames)
                )

    def test_sirius_teio_special_running_has_both_eligible_bands(self):
        entries = load_entries("Sirius Symboli")

        self.assertEqual(
            context_bands(entries, "activity_race_running_teio"),
            {"normal", "low", "severe"},
        )

    def test_transformed_rudolf_has_normal_only_complete_race_profile(self):
        entries = load_entries("Symboli Rudolf", transformed=True)
        required_contexts = {
            "activity_race_challenge",
            "activity_race_consider",
            "activity_race_accept",
            "activity_race_decline",
            "activity_race_to_start",
            "activity_race_ready",
            "activity_race_running",
            "activity_race_finish_win",
            "activity_race_finish_lose",
            "activity_race_recovery",
        }

        for context in required_contexts:
            self.assertEqual(context_bands(entries, context), {"normal"})

    def test_transformed_teio_has_no_race_contexts(self):
        entries = load_entries("Tokai Teio", transformed=True)

        self.assertFalse(
            any(
                context.startswith(RACE_CONTEXT_PREFIX)
                for metadata in entries.values()
                for context in metadata.get("contexts", ())
            )
        )


if __name__ == "__main__":
    unittest.main()
