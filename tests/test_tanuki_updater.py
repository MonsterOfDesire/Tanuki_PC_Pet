import argparse
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import tanuki_updater
from tanuki_core.installation_registry import InstallationRecord


class TanukiUpdaterTests(unittest.TestCase):
    def build_args(self, **values):
        defaults = {
            "install_dir": None,
            "current_version": None,
            "locale": None,
            "yes": False,
            "no_restart": True,
            "relocated": False,
        }
        defaults.update(values)
        return argparse.Namespace(**defaults)

    def test_explicit_legacy_directory_uses_unknown_beta_channel(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            install_dir = Path(temp_dir)
            (install_dir / "TanukiPet.exe").write_bytes(b"exe")
            args = self.build_args(install_dir=str(install_dir))
            with patch(
                "tanuki_updater.load_installation_record",
                side_effect=FileNotFoundError,
            ):
                record, legacy_selection = tanuki_updater._load_record(args)

            self.assertTrue(legacy_selection)
            self.assertEqual(
                record.version,
                tanuki_updater.UNKNOWN_INSTALLED_VERSION,
            )

    def test_registered_installation_needs_no_folder_selection(self):
        record = InstallationRecord(
            install_dir=str(Path.cwd()),
            version="0.8.0-beta",
        )
        args = self.build_args()
        with patch(
            "tanuki_updater.load_installation_record",
            return_value=record,
        ), patch(
            "tanuki_updater._browse_installation_directory"
        ) as browse:
            actual, legacy_selection = tanuki_updater._load_record(args)

        self.assertIs(actual, record)
        self.assertFalse(legacy_selection)
        browse.assert_not_called()

    def test_cancelled_first_time_folder_selection_is_reported(self):
        args = self.build_args()
        with patch(
            "tanuki_updater.load_installation_record",
            side_effect=FileNotFoundError,
        ), patch(
            "tanuki_updater._browse_installation_directory",
            return_value=None,
        ):
            with self.assertRaises(FileNotFoundError):
                tanuki_updater._load_record(args)


if __name__ == "__main__":
    unittest.main()
