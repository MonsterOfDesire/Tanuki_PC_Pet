import unittest

from tanuki_core.lightweight_checks import build_lightweight_report, parse_unittest_output


PASS_OUTPUT = """................................\n----------------------------------------------------------------------\nRan 32 tests in 0.020s\n\nOK\n"""
FAIL_OUTPUT = """..E.F\n======================================================================\nERROR: test_alpha (tests.test_alpha.AlphaTests)\n----------------------------------------------------------------------\nboom\n\n======================================================================\nFAIL: test_beta (tests.test_beta.BetaTests)\n----------------------------------------------------------------------\nnope\n\n----------------------------------------------------------------------\nRan 5 tests in 0.004s\n\nFAILED (failures=1, errors=1)\n"""


class LightweightChecksTests(unittest.TestCase):
    def test_parse_unittest_output_for_ok_run(self):
        summary = parse_unittest_output(PASS_OUTPUT)

        self.assertTrue(summary.passed)
        self.assertEqual(summary.total_tests, 32)
        self.assertEqual(summary.failures, 0)
        self.assertEqual(summary.errors, 0)
        self.assertEqual(summary.failing_cases, ())

    def test_parse_unittest_output_for_failed_run(self):
        summary = parse_unittest_output(FAIL_OUTPUT)

        self.assertFalse(summary.passed)
        self.assertEqual(summary.total_tests, 5)
        self.assertEqual(summary.failures, 1)
        self.assertEqual(summary.errors, 1)
        self.assertEqual(
            [(case.kind, case.name, case.suite) for case in summary.failing_cases],
            [
                ("ERROR", "test_alpha (tests.test_alpha.AlphaTests)", "uncategorized"),
                ("FAIL", "test_beta (tests.test_beta.BetaTests)", "uncategorized"),
            ],
        )

    def test_build_lightweight_report_lists_failures(self):
        summary = parse_unittest_output(FAIL_OUTPUT)

        report = build_lightweight_report(summary, ["python", "-m", "unittest"])

        self.assertIn("- Result: `FAIL`", report)
        self.assertIn("- Total tests: `5`", report)
        self.assertIn("- `ERROR` `test_alpha (tests.test_alpha.AlphaTests)` `uncategorized`", report)
        self.assertIn("- `FAIL` `test_beta (tests.test_beta.BetaTests)` `uncategorized`", report)


if __name__ == "__main__":
    unittest.main()
