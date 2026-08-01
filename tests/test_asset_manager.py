import json
import os
import tempfile
import unittest
from unittest.mock import patch

from tanuki_core.asset_loader import AssetStoreCache, FrameCache
from tanuki_core.asset_manager import AssetManager


class AssetManagerTests(unittest.TestCase):
    def test_startup_preloads_all_runtime_manifest_contexts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in (
                "idle_stand-happy.gif",
                "idle_watch-happy.gif",
                "idle_sleep-happy.gif",
                "move_walk_shake-happy.gif",
            ):
                open(os.path.join(temp_dir, file_name), "wb").close()
            with open(os.path.join(temp_dir, "manifest_edit.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "idle_stand-happy.gif": {
                            "band": ["normal"],
                            "contexts": ["random"],
                            "weight": 1.0,
                        },
                        "idle_watch-happy.gif": {
                            "band": ["normal"],
                            "contexts": ["relation_watch"],
                            "weight": 1.0,
                        },
                        "idle_sleep-happy.gif": {
                            "band": ["normal"],
                            "contexts": ["future_sleep"],
                            "weight": 1.0,
                        },
                        "move_walk_shake-happy.gif": {
                            "band": ["normal"],
                            "contexts": ["post_observe"],
                            "weight": 1.0,
                        },
                    },
                    handle,
                )

            extracted = []

            def fake_extract(gif_path, scale_factor, frame_cache=None):
                file_name = os.path.basename(gif_path)
                extracted.append(file_name)
                return [f"{file_name}@{scale_factor}"]

            with patch("tanuki_core.asset_manager.extract_frames", side_effect=fake_extract):
                manager = AssetManager(
                    temp_dir,
                    scale_factor=0.5,
                    frame_cache=FrameCache(),
                    store_cache=AssetStoreCache(),
                )

                self.assertEqual(
                    extracted,
                    ["idle_stand-happy.gif", "idle_watch-happy.gif", "move_walk_shake-happy.gif"],
                )
                self.assertIsNotNone(manager.get_record("idle", "watch", "happy"))

                with patch(
                    "tanuki_core.asset_manager.get_runtime_asset_file_names_for_contexts"
                ) as context_file_lookup:
                    result = manager.get_contextual_result(
                        "idle",
                        context="relation_watch",
                        mood_score=80,
                    )

                self.assertEqual(result, (["idle_watch-happy.gif@0.5"], "watch", "happy"))
                context_file_lookup.assert_not_called()
                self.assertEqual(
                    extracted,
                    ["idle_stand-happy.gif", "idle_watch-happy.gif", "move_walk_shake-happy.gif"],
                )
                self.assertIsNone(manager.get_record("idle", "sleep", "happy"))

                multi_result = manager.get_contextual_result_for_purposes(
                    ("idle", "move"),
                    context="post_observe",
                    preferred_moods=["happy"],
                    ordered_preferences=True,
                )

                self.assertEqual(
                    multi_result,
                    (["move_walk_shake-happy.gif@0.5"], "move", "walk_shake", "happy"),
                )

                any_purpose_result = manager.get_contextual_result_for_any_purpose(
                    context="post_observe",
                    preferred_moods=["happy"],
                    ordered_preferences=True,
                )

                self.assertEqual(
                    any_purpose_result,
                    (["move_walk_shake-happy.gif@0.5"], "move", "walk_shake", "happy"),
                )


if __name__ == "__main__":
    unittest.main()
