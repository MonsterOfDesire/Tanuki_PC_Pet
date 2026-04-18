import unittest

from tanuki_core.dashboard_shell_rules import should_request_slide_out


class DashboardShellRulesTests(unittest.TestCase):
    def test_requests_slide_out_only_when_expanded_and_click_is_outside(self):
        self.assertTrue(should_request_slide_out(is_expanded=True, contains_dashboard=False))
        self.assertFalse(should_request_slide_out(is_expanded=False, contains_dashboard=False))
        self.assertFalse(should_request_slide_out(is_expanded=True, contains_dashboard=True))


if __name__ == "__main__":
    unittest.main()
