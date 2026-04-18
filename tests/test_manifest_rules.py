import json
import tempfile
import unittest
from pathlib import Path

from tanuki_core.manifest_rules import normalize_manifest_entry
from tanuki_core.validation import load_manifest_entries


class ManifestRuleTests(unittest.TestCase):
    def test_normalize_manifest_entry_keeps_valid_tokens(self):
        normalized, warnings = normalize_manifest_entry(
            {
                "band": ["normal", "low"],
                "contexts": ["random", "sit"],
                "weight": 1.5,
            },
            file_name="ok.gif",
        )

        self.assertEqual(normalized["band"], ["normal", "low"])
        self.assertEqual(normalized["contexts"], ["random", "sit"])
        self.assertEqual(normalized["weight"], 1.5)
        self.assertEqual(warnings, [])

    def test_normalize_manifest_entry_warns_on_invalid_band_and_bad_weight(self):
        normalized, warnings = normalize_manifest_entry(
            {
                "band": ["nornal"],
                "contexts": ["random"],
                "weight": "oops",
            },
            file_name="idle_sit-laugh.gif",
        )

        self.assertEqual(normalized["band"], [])
        self.assertEqual(normalized["weight"], 1.0)
        self.assertTrue(any("無效 band 'nornal'" in warning for warning in warnings))
        self.assertTrue(any("weight 無法轉成數字" in warning for warning in warnings))

    def test_load_manifest_entries_collects_entry_level_warnings(self):
        payload = {
            "idle_sit-laugh.gif": {
                "band": ["nornal"],
                "contexts": ["random"],
                "weight": 1.0,
            },
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "manifest_edit.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            normalized, warnings = load_manifest_entries(str(path))

        self.assertIn("idle_sit-laugh.gif", normalized)
        self.assertTrue(any("無效 band 'nornal'" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
