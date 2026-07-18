import unittest
from pathlib import Path

from tools.check_staged_secrets import filename_findings, scan_staged_path


class StagedSecretScannerTests(unittest.TestCase):
    def test_blocks_sensitive_filenames_without_reading_content(self):
        self.assertEqual(filename_findings("release/example.pfx")[0].rule, "certificate_file")
        self.assertEqual(filename_findings(".env.local")[0].rule, "environment_file")
        self.assertEqual(filename_findings(".env.example"), ())

    def test_reports_rule_name_without_match_content(self):
        data = b"client_" + b"secret = 'example-only-value'"
        findings = scan_staged_path("settings.txt", data)
        self.assertEqual([(item.path, item.rule) for item in findings], [
            ("settings.txt", "credential_assignment"),
        ])

    def test_scanner_does_not_flag_its_own_source(self):
        scanner_path = Path(__file__).resolve().parents[1] / "tools" / "check_staged_secrets.py"
        self.assertEqual(scan_staged_path("tools/check_staged_secrets.py", scanner_path.read_bytes()), ())


if __name__ == "__main__":
    unittest.main()
