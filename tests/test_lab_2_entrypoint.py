import contextlib
import io
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import lab_2


class Lab2EntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_returns_runtime_exit_code(self):
        with patch.object(lab_2, "run_application", return_value=0):
            self.assertEqual(lab_2.main(), 0)

    def test_missing_resource_reports_path_and_returns_failure(self):
        stderr = io.StringIO()
        missing_path = r"C:\TanukiPet\assets_cropped"
        with (
            patch.object(
                lab_2,
                "run_application",
                side_effect=FileNotFoundError(missing_path),
            ),
            patch.object(lab_2.QMessageBox, "critical") as critical,
            contextlib.redirect_stderr(stderr),
        ):
            exit_code = lab_2.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Required resource not found", stderr.getvalue())
        self.assertIn(missing_path, stderr.getvalue())
        critical.assert_called_once()
        _parent, title, message = critical.call_args.args
        self.assertEqual(title, lab_2.STARTUP_ERROR_TITLE)
        self.assertIn(missing_path, message)


if __name__ == "__main__":
    unittest.main()
