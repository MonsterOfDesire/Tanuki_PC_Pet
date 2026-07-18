from __future__ import annotations

import os
import unittest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication
except ImportError as exc:
    QCoreApplication = None
    QApplication = None
    QT_IMPORT_ERROR = exc
else:
    QT_IMPORT_ERROR = None


QT_BINDINGS_AVAILABLE = QApplication is not None


def ensure_qt_application():
    if not QT_BINDINGS_AVAILABLE:
        raise unittest.SkipTest(f"PyQt6 unavailable: {QT_IMPORT_ERROR}")

    app = QCoreApplication.instance()
    if app is None:
        app = QApplication([])
    elif not isinstance(app, QApplication):
        raise RuntimeError("Qt tests require QApplication to be created before QCoreApplication")
    return app


class QtApplicationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.qt_app = ensure_qt_application()
