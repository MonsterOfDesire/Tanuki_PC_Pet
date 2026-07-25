import os
import tempfile
import unittest

from tanuki_core.asset_manager import AssetManager
from tanuki_core.ui_skin_assets import UiSkinAssetError, UiSkinAssets


class UiSkinAssetsTests(unittest.TestCase):
    def test_project_ui_assets_match_declared_contract(self):
        assets = UiSkinAssets(AssetManager.get_resource_path)

        self.assertEqual(assets.validate_assets(), ())

    def test_missing_asset_is_reported_without_loading_pixmap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            assets = UiSkinAssets(lambda relative_path: os.path.join(temp_dir, relative_path))

            issues = assets.validate_assets(("diet_background",))

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].asset_key, "diet_background")
        self.assertEqual(issues[0].message, "file is missing")

    def test_unknown_asset_raises_domain_error(self):
        assets = UiSkinAssets(AssetManager.get_resource_path)

        with self.assertRaises(UiSkinAssetError):
            assets.resolve_asset_path("missing")


if __name__ == "__main__":
    unittest.main()
