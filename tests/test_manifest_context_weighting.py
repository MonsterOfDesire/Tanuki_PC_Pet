import os
import unittest
from pathlib import Path
from unittest.mock import patch

from tanuki_core.asset_loader import AssetStoreCache, FrameCache
from tanuki_core.asset_manager import AssetManager
from tanuki_core.asset_selection_rules import select_contextual_result


class LastChoiceRng:
    def __init__(self):
        self.weights = []

    def choices(self, population, weights=None, k=1):
        self.weights = list(weights or ())
        return [population[-1]]

    def choice(self, population):
        return population[-1]


class SmileChoiceRng(LastChoiceRng):
    def choices(self, population, weights=None, k=1):
        self.weights = list(weights or ())
        for candidate in reversed(population):
            if len(candidate) > 3 and candidate[3] == "smile":
                return [candidate]
        return [population[-1]]


class ManifestContextWeightingTests(unittest.TestCase):
    def build_tsuyoshi_manager(self):
        character_path = (
            Path(__file__).resolve().parents[1]
            / "assets_cropped"
            / "Tsurumaru Tsuyoshi"
        )

        def fake_extract(gif_path, scale_factor, frame_cache=None):
            return [f"{os.path.basename(gif_path)}@{scale_factor}"]

        with patch(
            "tanuki_core.asset_manager.extract_frames",
            side_effect=fake_extract,
        ):
            return AssetManager(
                str(character_path),
                scale_factor=1.0,
                frame_cache=FrameCache(),
                store_cache=AssetStoreCache(),
            )

    def test_tsuyoshi_bottle_approach_combines_happy_and_smile_weights(self):
        manager = self.build_tsuyoshi_manager()
        rng = SmileChoiceRng()

        result = select_contextual_result(
            manager.asset_records["move"],
            context="bottle_feed_child_approach",
            preferred_moods=("happy", "smile", "think"),
            mood_score=60.0,
            ordered_preferences=False,
            rng=rng,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result[2], "smile")
        self.assertEqual(rng.weights, [1.0, 1.0])

    def test_tsuyoshi_short_click_combines_random_happy_and_smile_assets(self):
        manager = self.build_tsuyoshi_manager()
        rng = SmileChoiceRng()

        result = select_contextual_result(
            manager.asset_records["idle"],
            context="random",
            preferred_moods=("happy", "smile"),
            mood_score=60.0,
            ordered_preferences=False,
            rng=rng,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result[2], "smile")
        self.assertGreater(len(rng.weights), 2)


if __name__ == "__main__":
    unittest.main()
