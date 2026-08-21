import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tanuki_core.installation_registry import (
    InstallationRecord,
    load_installation_record,
    mark_current_installation_stopped,
    record_current_installation,
    save_installation_record,
)


class InstallationRegistryTests(unittest.TestCase):
    def test_round_trip_normalizes_version_locale_and_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "installation.json"
            install_dir = Path(temp_dir) / "TanukiPet"
            install_dir.mkdir()

            save_installation_record(
                InstallationRecord(
                    install_dir=str(install_dir),
                    version="v0.8.0-beta",
                    process_id=123,
                    ui_locale="ja-JP",
                ),
                path=path,
            )
            record = load_installation_record(path)

            self.assertEqual(record.install_dir, str(install_dir.resolve()))
            self.assertEqual(record.version, "0.8.0-beta")
            self.assertEqual(record.ui_locale, "ja_JP")
            self.assertEqual(record.process_id, 123)

    def test_packaged_runtime_records_and_clears_process_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "installation.json"
            executable = Path(temp_dir) / "TanukiPet.exe"
            executable.write_bytes(b"exe")
            with patch(
                "tanuki_core.installation_registry._is_frozen_runtime",
                return_value=True,
            ), patch(
                "tanuki_core.installation_registry.sys.executable",
                str(executable),
            ):
                record = record_current_installation("en_US", path=path)

            self.assertEqual(record.install_dir, str(Path(temp_dir).resolve()))
            self.assertEqual(record.ui_locale, "en_US")
            self.assertGreater(record.process_id, 0)
            self.assertTrue(
                mark_current_installation_stopped(
                    process_id=record.process_id,
                    path=path,
                )
            )
            self.assertEqual(load_installation_record(path).process_id, 0)

    def test_invalid_relative_installation_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "installation.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "install_dir": "relative",
                        "version": "0.8.0",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "must be absolute"):
                load_installation_record(path)


if __name__ == "__main__":
    unittest.main()
