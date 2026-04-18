import unittest

from tanuki_core.asset_loader import AssetStore


class AssetStoreTests(unittest.TestCase):
    def test_empty_store_has_no_frames_or_actions(self):
        store = AssetStore.empty()

        self.assertEqual(store.get_any_available_frames(), [])
        self.assertEqual(store.get_action_keys("idle"), [])
        self.assertFalse(store.has_action("idle", "sit"))
        self.assertIsNone(store.get_record("idle", "sit", "happy"))

    def test_store_helpers_read_nested_asset_maps(self):
        store = AssetStore(
            manifest_data={"idle_sit-happy.gif": {"band": ["normal"]}},
            assets={"idle": {"sit": {"happy": ["frame-1"]}}},
            asset_records={
                "idle": {
                    "sit": {
                        "happy": {
                            "frames": ["frame-1"],
                            "file_name": "idle_sit-happy.gif",
                            "manifest": {"band": ["normal"]},
                        }
                    }
                }
            },
        )

        self.assertEqual(store.get_any_available_frames(), ["frame-1"])
        self.assertEqual(store.get_action_keys("idle"), ["sit"])
        self.assertTrue(store.has_action("idle", "sit"))
        self.assertEqual(store.get_record("idle", "sit", "happy")["file_name"], "idle_sit-happy.gif")


if __name__ == "__main__":
    unittest.main()
