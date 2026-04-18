import unittest

from tanuki_core.dashboard_presenter import DashboardPresenter
from tanuki_core.dashboard_tools_actions import ValidationCheckResult


class DashboardPresenterTests(unittest.TestCase):
    def test_build_debug_button_formats_enabled_state(self):
        presenter = DashboardPresenter()

        presentation = presenter.build_debug_button(True)

        self.assertEqual(presentation.text, "Debug: 開啟")

    def test_build_shutdown_status_returns_expected_view_model(self):
        presenter = DashboardPresenter()

        presentation = presenter.build_shutdown_status()

        self.assertEqual(presentation.status_text, "正在儲存設定...")
        self.assertTrue(presentation.show_status)
        self.assertFalse(presentation.exit_enabled)
        self.assertEqual(presentation.exit_text, "正在關閉...")
        self.assertTrue(presentation.force_expanded)

    def test_build_validation_dialog_uses_warning_when_result_has_warnings(self):
        presenter = DashboardPresenter()
        result = ValidationCheckResult(report="warn report", warnings=("a",))

        presentation = presenter.build_validation_dialog(result)

        self.assertEqual(presentation.title, "檢查結果（有警告）")
        self.assertEqual(presentation.message, "warn report")
        self.assertEqual(presentation.severity, "warning")

    def test_build_validation_dialog_uses_information_when_result_is_clean(self):
        presenter = DashboardPresenter()
        result = ValidationCheckResult(report="ok report", warnings=())

        presentation = presenter.build_validation_dialog(result)

        self.assertEqual(presentation.title, "檢查結果（正常）")
        self.assertEqual(presentation.severity, "information")


if __name__ == "__main__":
    unittest.main()
