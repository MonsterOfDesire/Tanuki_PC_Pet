from __future__ import annotations

from PyQt6.QtCore import QObject


class DashboardControlState(QObject):
    """Non-visual state used by pre-launcher Dashboard compatibility APIs."""

    def __init__(
        self,
        text="",
        *,
        enabled=True,
        checked=False,
        value=0,
        parent=None,
    ):
        super().__init__(parent)
        self._text = str(text)
        self._enabled = bool(enabled)
        self._checked = bool(checked)
        self._value = int(value)
        self._signals_blocked = False

    def setText(self, text):
        self._text = str(text)

    def text(self):
        return self._text

    def setEnabled(self, enabled):
        self._enabled = bool(enabled)

    def isEnabled(self):
        return self._enabled

    def setChecked(self, checked):
        self._checked = bool(checked)

    def isChecked(self):
        return self._checked

    def setValue(self, value):
        self._value = int(value)

    def value(self):
        return self._value

    def blockSignals(self, block):
        previous = self._signals_blocked
        self._signals_blocked = bool(block)
        return previous

    def hide(self):
        return None

    def isHidden(self):
        return True
