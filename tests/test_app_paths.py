from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tanuki_core.app_paths import (
    get_runtime_config_path,
    get_user_data_directory,
)


class AppPathsTests(unittest.TestCase):
    def test_macos_uses_application_support(self):
        path = get_user_data_directory(
            platform="darwin",
            environ={},
            home="/Users/tester",
        )

        self.assertTrue(
            path.as_posix().endswith(
                "/Users/tester/Library/Application Support/Tanuki_PC_Pet"
            )
        )

    def test_windows_preserves_local_app_data_location(self):
        path = get_user_data_directory(
            platform="win32",
            environ={"LOCALAPPDATA": "C:/Users/tester/AppData/Local"},
            home="C:/Users/tester",
        )

        self.assertEqual(path.name, "Tanuki_PC_Pet")
        self.assertEqual(path.parent.name, "Local")

    def test_explicit_user_data_override_is_cross_platform(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = get_user_data_directory(
                platform="darwin",
                environ={"TANUKI_USER_DATA_DIR": temp_dir},
            )

            self.assertEqual(path, Path(temp_dir).resolve())

    def test_macos_config_never_targets_app_bundle_resources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                "os.environ",
                {"TANUKI_USER_DATA_DIR": temp_dir},
                clear=False,
            ):
                path = get_runtime_config_path(
                    lambda name: f"/Applications/TanukiPet.app/{name}",
                    platform="darwin",
                )

            self.assertEqual(
                Path(path).resolve(),
                (Path(temp_dir) / "config.json").resolve(),
            )

    def test_windows_config_keeps_existing_portable_location(self):
        path = get_runtime_config_path(
            lambda name: f"C:/Portable/TanukiPet/{name}",
            platform="win32",
        )

        self.assertEqual(path, "C:/Portable/TanukiPet/config.json")


if __name__ == "__main__":
    unittest.main()
