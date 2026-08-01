import json
import unittest
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets_cropped"
CHARACTER_NAMES = (
    "Air Groove",
    "Sirius Symboli",
    "Symboli Rudolf",
    "Tokai Teio",
    "Tsurumaru Tsuyoshi",
)
ALL_BANDS = {"normal", "low", "severe"}


def context_bands(entries, context):
    bands = set()
    for metadata in entries.values():
        if context in metadata.get("contexts", ()):
            bands.update(metadata.get("band", ()))
    return bands


class SleepAssetIntegrationTests(unittest.TestCase):
    def test_every_character_can_observe_approach_join_and_sleep_in_all_bands(self):
        for character_name in CHARACTER_NAMES:
            with self.subTest(character=character_name):
                path = ASSETS_DIR / character_name / "manifest_edit.json"
                payload = json.loads(path.read_text(encoding="utf-8"))
                entries = payload["animations"]

                self.assertEqual(
                    context_bands(entries, "activity_sleep_observing"),
                    ALL_BANDS,
                )
                self.assertEqual(
                    context_bands(entries, "activity_sleep_join_approach"),
                    ALL_BANDS,
                )
                settling_bands = context_bands(
                    entries,
                    "activity_sleep_join_settling",
                ) | context_bands(entries, "activity_sleep_settling")
                self.assertEqual(settling_bands, ALL_BANDS)
                self.assertEqual(
                    context_bands(entries, "activity_sleeping"),
                    ALL_BANDS,
                )
                self.assertEqual(
                    context_bands(entries, "activity_sleep_waking"),
                    ALL_BANDS,
                )


if __name__ == "__main__":
    unittest.main()
