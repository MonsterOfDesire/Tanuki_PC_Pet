import json
import unittest
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets_cropped"
MANIFESTS = (
    ASSETS_DIR / "Air Groove" / "manifest_edit.json",
    ASSETS_DIR / "Sirius Symboli" / "manifest_edit.json",
    ASSETS_DIR / "Symboli Rudolf" / "manifest_edit.json",
    ASSETS_DIR / "Symboli Rudolf" / "transformed" / "manifest_edit.json",
    ASSETS_DIR / "Tokai Teio" / "manifest_edit.json",
    ASSETS_DIR / "Tokai Teio" / "transformed" / "manifest_edit.json",
    ASSETS_DIR / "Tsurumaru Tsuyoshi" / "manifest_edit.json",
)
CHORUS_CONTEXTS = {
    "activity_chorus_approach",
    "activity_chorus_finish",
    "activity_chorus_observe",
    "activity_chorus_perform",
}


class ChorusAssetIntegrationTests(unittest.TestCase):
    def test_all_forms_have_every_chorus_context(self):
        for path in MANIFESTS:
            payload = json.loads(path.read_text(encoding="utf-8"))
            entries = payload["animations"]
            found = {
                context
                for entry in entries.values()
                for context in entry.get("contexts", ())
                if context.startswith("activity_chorus_")
            }
            self.assertTrue(
                CHORUS_CONTEXTS.issubset(found),
                f"{path} missing {sorted(CHORUS_CONTEXTS - found)}",
            )

    def test_preferred_sirius_guitars_and_rudolf_drums_keep_requested_weights(self):
        sirius = json.loads(
            (ASSETS_DIR / "Sirius Symboli" / "manifest_edit.json").read_text(
                encoding="utf-8"
            )
        )["animations"]
        rudolf = json.loads(
            (ASSETS_DIR / "Symboli Rudolf" / "manifest_edit.json").read_text(
                encoding="utf-8"
            )
        )["animations"]

        self.assertEqual(
            sirius["idle_music_electricguitar_solo-cool.gif"]["weight"],
            0.5,
        )
        self.assertEqual(
            sirius["idle_music_electricguitar-happy.gif"]["weight"],
            3.0,
        )
        self.assertEqual(
            sirius["idle_music_guitar-happy.gif"]["weight"],
            5.0,
        )
        self.assertEqual(
            rudolf["idle_music_bigdrum-happy.gif"]["weight"],
            5.0,
        )
        self.assertEqual(
            rudolf["idle_music_drum-happy.gif"]["weight"],
            5.0,
        )


if __name__ == "__main__":
    unittest.main()
