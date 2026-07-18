import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tools.check_staged_secrets import filename_findings, get_staged_paths, main, scan_staged_path


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

    @patch("tools.check_staged_secrets.run_git")
    def test_staged_listing_includes_deletions_when_no_filter_is_requested(self, run_git):
        run_git.return_value = SimpleNamespace(returncode=0, stdout=b"deleted.txt\0added.txt\0")
        self.assertEqual(get_staged_paths("repo"), ("deleted.txt", "added.txt"))
        run_git.assert_called_once_with("repo", "diff", "--cached", "--name-only", "-z")

    @patch("tools.check_staged_secrets.get_staged_blob")
    @patch("tools.check_staged_secrets.get_staged_paths")
    @patch("tools.check_staged_secrets.get_repo_root", return_value="repo")
    def test_deletion_only_stage_is_reported_without_reading_deleted_blob(
        self,
        _get_repo_root,
        get_staged_paths_mock,
        get_staged_blob_mock,
    ):
        get_staged_paths_mock.side_effect = [("deleted.txt",), ()]
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("deleted.txt", output.getvalue())
        get_staged_blob_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
