import os
import tempfile
import unittest
from collections import OrderedDict

from tanuki_core.asset_loader import (
    AssetStoreCache,
    FrameCache,
    get_runtime_asset_file_names,
    get_runtime_asset_file_names_for_contexts,
    is_runtime_manifest_entry,
    load_asset_indexes,
    load_asset_store,
    parse_asset_filename,
)


class AssetLoaderTests(unittest.TestCase):
    def test_parse_asset_filename_extracts_purpose_action_and_mood(self):
        self.assertEqual(parse_asset_filename("move_walk-happy.gif"), ("move", "walk", "happy"))
        self.assertEqual(parse_asset_filename("idle-normal.gif"), ("idle", "default", "normal"))

    def test_load_asset_indexes_builds_assets_and_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = os.path.join(temp_dir, "idle_sit-happy.gif")
            second = os.path.join(temp_dir, "move_walk-sad.gif")
            open(first, "wb").close()
            open(second, "wb").close()

            manifest_data = {
                "idle_sit-happy.gif": {"band": ["normal"]},
                "move_walk-sad.gif": {"band": ["low"]},
            }

            def fake_extractor(gif_path, scale_factor):
                return [f"{os.path.basename(gif_path)}@{scale_factor}"]

            assets, records = load_asset_indexes(
                temp_dir,
                manifest_data,
                0.5,
                frame_extractor=fake_extractor,
            )

            self.assertEqual(assets["idle"]["sit"]["happy"], ["idle_sit-happy.gif@0.5"])
            self.assertEqual(assets["move"]["walk"]["sad"], ["move_walk-sad.gif@0.5"])
            self.assertEqual(records["idle"]["sit"]["happy"]["file_name"], "idle_sit-happy.gif")
            self.assertEqual(records["move"]["walk"]["sad"]["manifest"], {"band": ["low"]})

    def test_load_asset_indexes_reports_bad_file_and_continues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            good = os.path.join(temp_dir, "idle_sit-happy.gif")
            bad = os.path.join(temp_dir, "idle_sit-sad.gif")
            open(good, "wb").close()
            open(bad, "wb").close()

            failures = []

            def fake_extractor(gif_path, scale_factor):
                if gif_path.endswith("idle_sit-sad.gif"):
                    raise ValueError("broken gif")
                return [f"{os.path.basename(gif_path)}@{scale_factor}"]

            assets, records = load_asset_indexes(
                temp_dir,
                {},
                0.5,
                frame_extractor=fake_extractor,
                error_sink=lambda file_name, exc: failures.append((file_name, str(exc))),
            )

            self.assertEqual(assets["idle"]["sit"]["happy"], ["idle_sit-happy.gif@0.5"])
            self.assertNotIn("sad", records["idle"]["sit"])
            self.assertEqual(failures, [("idle_sit-sad.gif", "broken gif")])

    def test_load_asset_store_wraps_indexes_and_manifest_as_single_runtime_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = os.path.join(temp_dir, "idle_sit-happy.gif")
            open(first, "wb").close()

            def fake_extractor(gif_path, scale_factor):
                return [f"{os.path.basename(gif_path)}@{scale_factor}"]

            store = load_asset_store(
                temp_dir,
                {"idle_sit-happy.gif": {"band": ["normal"]}},
                0.5,
                frame_extractor=fake_extractor,
            )

            self.assertEqual(store.assets["idle"]["sit"]["happy"], ["idle_sit-happy.gif@0.5"])
            self.assertEqual(store.get_record("idle", "sit", "happy")["manifest"], {"band": ["normal"]})

    def test_runtime_manifest_entry_excludes_future_disabled_and_zero_weight(self):
        self.assertTrue(is_runtime_manifest_entry({"contexts": ["random"], "weight": 1.0}))
        self.assertTrue(is_runtime_manifest_entry({"contexts": ["future_sleep", "random"], "weight": 1.0}))
        self.assertFalse(is_runtime_manifest_entry({"contexts": ["future_sleep"], "weight": 1.0}))
        self.assertFalse(is_runtime_manifest_entry({"contexts": ["disabled"], "weight": 1.0}))
        self.assertFalse(is_runtime_manifest_entry({"contexts": ["random"], "weight": 0.0}))
        self.assertFalse(is_runtime_manifest_entry({"contexts": [], "weight": 1.0}))

    def test_runtime_asset_file_names_prefers_active_manifest_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in (
                "idle_stand-happy.gif",
                "idle_sleep-happy.gif",
                "idle_disabled-happy.gif",
                "idle_zero-happy.gif",
                "idle_unlisted-happy.gif",
            ):
                open(os.path.join(temp_dir, file_name), "wb").close()

            file_names = get_runtime_asset_file_names(
                temp_dir,
                {
                    "idle_stand-happy.gif": {"contexts": ["random"], "weight": 1.0},
                    "idle_sleep-happy.gif": {"contexts": ["future_sleep"], "weight": 1.0},
                    "idle_disabled-happy.gif": {"contexts": ["disabled"], "weight": 1.0},
                    "idle_zero-happy.gif": {"contexts": ["random"], "weight": 0.0},
                    "missing.gif": {"contexts": ["random"], "weight": 1.0},
                },
            )

            self.assertEqual(file_names, ["idle_stand-happy.gif"])

    def test_runtime_asset_file_names_falls_back_when_manifest_has_no_active_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in ("idle_sleep-happy.gif", "idle_disabled-happy.gif"):
                open(os.path.join(temp_dir, file_name), "wb").close()

            file_names = get_runtime_asset_file_names(
                temp_dir,
                {
                    "idle_sleep-happy.gif": {"contexts": ["future_sleep"], "weight": 1.0},
                    "idle_disabled-happy.gif": {"contexts": ["disabled"], "weight": 1.0},
                },
            )

            self.assertEqual(file_names, ["idle_disabled-happy.gif", "idle_sleep-happy.gif"])

    def test_runtime_asset_file_names_for_contexts_filters_to_requested_contexts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for file_name in (
                "idle_stand-happy.gif",
                "idle_watch-happy.gif",
                "idle_sleep-happy.gif",
                "idle_disabled-happy.gif",
            ):
                open(os.path.join(temp_dir, file_name), "wb").close()

            file_names = get_runtime_asset_file_names_for_contexts(
                temp_dir,
                {
                    "idle_stand-happy.gif": {"contexts": ["random"], "weight": 1.0},
                    "idle_watch-happy.gif": {"contexts": ["relation_watch"], "weight": 1.0},
                    "idle_sleep-happy.gif": {"contexts": ["future_sleep"], "weight": 1.0},
                    "idle_disabled-happy.gif": {"contexts": ["disabled"], "weight": 1.0},
                },
                ["random", "window_perch"],
            )

            self.assertEqual(file_names, ["idle_stand-happy.gif"])

    def test_frame_cache_reuses_raw_frames_across_scales_but_scales_per_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            gif_path = os.path.join(temp_dir, "idle_sit-happy.gif")
            open(gif_path, "wb").close()

            raw_calls = []
            scale_calls = []
            cache = FrameCache(signature_getter=lambda path: ("static",))

            def fake_raw_loader(path):
                raw_calls.append(path)
                return [f"raw:{os.path.basename(path)}"]

            def fake_scaler(raw_frames, scale_factor):
                scale_calls.append(scale_factor)
                return [f"{raw_frames[0]}@{scale_factor}"]

            first = cache.get_scaled_frames(
                gif_path,
                0.5,
                raw_loader=fake_raw_loader,
                scaler=fake_scaler,
            )
            second = cache.get_scaled_frames(
                gif_path,
                0.5,
                raw_loader=fake_raw_loader,
                scaler=fake_scaler,
            )
            third = cache.get_scaled_frames(
                gif_path,
                0.75,
                raw_loader=fake_raw_loader,
                scaler=fake_scaler,
            )

            self.assertEqual(first, ["raw:idle_sit-happy.gif@0.5"])
            self.assertIs(first, second)
            self.assertEqual(third, ["raw:idle_sit-happy.gif@0.75"])
            self.assertEqual(raw_calls, [gif_path])
            self.assertEqual(scale_calls, [0.5, 0.75])

    def test_frame_cache_invalidates_when_file_signature_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            gif_path = os.path.join(temp_dir, "idle_sit-happy.gif")
            open(gif_path, "wb").close()

            current_signature = {"value": ("sig-1",)}
            raw_calls = []
            cache = FrameCache(signature_getter=lambda path: current_signature["value"])

            def fake_raw_loader(path):
                raw_calls.append((path, current_signature["value"]))
                return [f"raw:{current_signature['value'][0]}"]

            def fake_scaler(raw_frames, scale_factor):
                return [f"{raw_frames[0]}@{scale_factor}"]

            first = cache.get_scaled_frames(gif_path, 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
            current_signature["value"] = ("sig-2",)
            second = cache.get_scaled_frames(gif_path, 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)

            self.assertEqual(first, ["raw:sig-1@0.5"])
            self.assertEqual(second, ["raw:sig-2@0.5"])
            self.assertEqual(raw_calls, [(gif_path, ("sig-1",)), (gif_path, ("sig-2",))])

    def test_frame_cache_eviction_prunes_oldest_raw_and_scaled_entries(self):
        cache = FrameCache(
            signature_getter=lambda path: (path,),
            max_raw_entries=2,
            max_scaled_entries=2,
        )

        def fake_raw_loader(path):
            return [f"raw:{path}"]

        def fake_scaler(raw_frames, scale_factor):
            return [f"{raw_frames[0]}@{scale_factor}"]

        cache.get_scaled_frames("a.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("b.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("c.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)

        self.assertEqual(
            list(cache.raw_frames.keys()),
            [("b.gif", ("b.gif",)), ("c.gif", ("c.gif",))],
        )
        self.assertEqual(
            list(cache.scaled_frames.keys()),
            [
                ("b.gif", ("b.gif",), 0.5),
                ("c.gif", ("c.gif",), 0.5),
            ],
        )

    def test_frame_cache_moves_recently_used_entries_to_the_end(self):
        cache = FrameCache(
            signature_getter=lambda path: (path,),
            max_raw_entries=2,
            max_scaled_entries=2,
        )

        def fake_raw_loader(path):
            return [f"raw:{path}"]

        def fake_scaler(raw_frames, scale_factor):
            return [f"{raw_frames[0]}@{scale_factor}"]

        cache.get_scaled_frames("a.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("b.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("a.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("c.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)

        self.assertEqual(
            list(cache.scaled_frames.keys()),
            [
                ("a.gif", ("a.gif",), 0.5),
                ("c.gif", ("c.gif",), 0.5),
            ],
        )

    def test_frame_cache_can_clear_single_path(self):
        cache = FrameCache(signature_getter=lambda path: (path,))

        def fake_raw_loader(path):
            return [f"raw:{path}"]

        def fake_scaler(raw_frames, scale_factor):
            return [f"{raw_frames[0]}@{scale_factor}"]

        cache.get_scaled_frames("a.gif", 0.5, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.get_scaled_frames("a.gif", 0.75, raw_loader=fake_raw_loader, scaler=fake_scaler)
        cache.clear_path("a.gif")

        self.assertEqual(cache.raw_frames, OrderedDict())
        self.assertEqual(cache.scaled_frames, OrderedDict())
        self.assertEqual(cache.file_signatures, {})

    def test_asset_store_cache_reuses_same_character_and_scale_store(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = os.path.join(temp_dir, "idle_sit-happy.gif")
            open(first, "wb").close()
            manifest_path = os.path.join(temp_dir, "manifest_edit.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                handle.write("{}")

            extractor_calls = []
            store_cache = AssetStoreCache()

            def fake_extractor(gif_path, scale_factor):
                extractor_calls.append((gif_path, scale_factor))
                return [f"{os.path.basename(gif_path)}@{scale_factor}"]

            store_one = load_asset_store(
                temp_dir,
                {"idle_sit-happy.gif": {"band": ["normal"]}},
                0.5,
                frame_extractor=fake_extractor,
                store_cache=store_cache,
            )
            store_two = load_asset_store(
                temp_dir,
                {"idle_sit-happy.gif": {"band": ["normal"]}},
                0.5,
                frame_extractor=fake_extractor,
                store_cache=store_cache,
            )

            self.assertIs(store_one, store_two)
            self.assertEqual(extractor_calls, [(first, 0.5)])

    def test_asset_store_cache_invalidates_when_manifest_signature_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = os.path.join(temp_dir, "idle_sit-happy.gif")
            open(first, "wb").close()
            manifest_path = os.path.join(temp_dir, "manifest_edit.json")
            with open(manifest_path, "w", encoding="utf-8") as handle:
                handle.write("{}")

            extractor_calls = []
            store_cache = AssetStoreCache()

            def fake_extractor(gif_path, scale_factor):
                extractor_calls.append((gif_path, scale_factor))
                return [f"{os.path.basename(gif_path)}@{scale_factor}:{len(extractor_calls)}"]

            store_one = load_asset_store(
                temp_dir,
                {"idle_sit-happy.gif": {"band": ["normal"]}},
                0.5,
                frame_extractor=fake_extractor,
                store_cache=store_cache,
            )

            with open(manifest_path, "w", encoding="utf-8") as handle:
                handle.write('{"changed": true}')

            store_two = load_asset_store(
                temp_dir,
                {"idle_sit-happy.gif": {"band": ["normal"], "contexts": ["random"]}},
                0.5,
                frame_extractor=fake_extractor,
                store_cache=store_cache,
            )

            self.assertIsNot(store_one, store_two)
            self.assertEqual(len(extractor_calls), 2)

    def test_asset_store_cache_prunes_oldest_entries(self):
        store_cache = AssetStoreCache(max_entries=2)
        store_cache.stores[("a", 0.5)] = (("sig-a",), object())
        store_cache.stores[("b", 0.5)] = (("sig-b",), object())
        store_cache.stores[("c", 0.5)] = (("sig-c",), object())

        store_cache._prune_cache()

        self.assertEqual(list(store_cache.stores.keys()), [("b", 0.5), ("c", 0.5)])

    def test_asset_store_cache_moves_reused_entry_to_end(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir, tempfile.TemporaryDirectory() as third_dir:
            for temp_dir in (first_dir, second_dir, third_dir):
                open(os.path.join(temp_dir, "idle_sit-happy.gif"), "wb").close()
                with open(os.path.join(temp_dir, "manifest_edit.json"), "w", encoding="utf-8") as handle:
                    handle.write("{}")

            store_cache = AssetStoreCache(max_entries=2)

            def fake_extractor(gif_path, scale_factor):
                return [f"{os.path.basename(gif_path)}@{scale_factor}"]

            load_asset_store(first_dir, {}, 0.5, frame_extractor=fake_extractor, store_cache=store_cache)
            load_asset_store(second_dir, {}, 0.5, frame_extractor=fake_extractor, store_cache=store_cache)
            load_asset_store(first_dir, {}, 0.5, frame_extractor=fake_extractor, store_cache=store_cache)
            load_asset_store(third_dir, {}, 0.5, frame_extractor=fake_extractor, store_cache=store_cache)

            remaining_paths = [key[0] for key in store_cache.stores.keys()]
            self.assertIn(os.path.abspath(first_dir), remaining_paths)
            self.assertIn(os.path.abspath(third_dir), remaining_paths)

    def test_asset_store_cache_can_clear_character(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            store_cache = AssetStoreCache()
            store_cache.stores[(os.path.abspath(first_dir), 0.5)] = (("sig-a",), object())
            store_cache.stores[(os.path.abspath(first_dir), 0.75)] = (("sig-b",), object())
            store_cache.stores[(os.path.abspath(second_dir), 0.5)] = (("sig-c",), object())

            store_cache.clear_character(first_dir)

            self.assertEqual(list(store_cache.stores.keys()), [(os.path.abspath(second_dir), 0.5)])


if __name__ == "__main__":
    unittest.main()
