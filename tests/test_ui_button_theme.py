"""Paint the scoped button skins without changing any page layout or binding."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QPushButton,
    QStyle,
    QStyleOptionButton,
)

from tanuki_core.ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from tanuki_core.status_settings_art import NoticeboardAction, NoticeboardOption


class RoundedButtonThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def render_button(self, role, *, checked=False, enabled=True, state=None):
        button = QPushButton()
        self.addCleanup(button.deleteLater)
        button.setProperty("tanukiRole", role)
        button.setCheckable(role == "eventFilter")
        button.setChecked(checked)
        button.setEnabled(enabled)
        button.setStyleSheet(build_ui_stylesheet())
        button.resize(100, 30)
        button.ensurePolished()
        option = QStyleOptionButton()
        button.initStyleOption(option)
        option.state &= ~(
            QStyle.StateFlag.State_MouseOver
            | QStyle.StateFlag.State_HasFocus
            | QStyle.StateFlag.State_Sunken
        )
        if state is not None:
            option.state |= state
        image = QImage(button.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        button.style().drawControl(
            QStyle.ControlElement.CE_PushButton, option, painter, button
        )
        painter.end()
        return image

    def test_both_button_roles_have_rounded_corners_and_flat_fill(self):
        for role in ("eventFilter", "familyAction"):
            with self.subTest(role=role):
                image = self.render_button(role)
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                self.assertEqual(image.pixelColor(50, 15).alpha(), 255)
                self.assertEqual(
                    image.pixelColor(50, 5),
                    image.pixelColor(50, 24),
                )

    def test_selected_filter_is_brighter_and_remains_selected_while_hovering(self):
        normal = self.render_button("eventFilter")
        selected = self.render_button("eventFilter", checked=True)
        hovered = self.render_button(
            "eventFilter", checked=True, state=QStyle.StateFlag.State_MouseOver
        )
        self.assertGreater(
            selected.pixelColor(50, 15).lightness(),
            normal.pixelColor(50, 15).lightness(),
        )
        self.assertGreater(
            hovered.pixelColor(50, 15).lightness(),
            selected.pixelColor(50, 15).lightness(),
        )

    def test_hover_and_press_states_are_distinct_without_changing_dimensions(self):
        for role in ("eventFilter", "familyAction"):
            with self.subTest(role=role):
                normal = self.render_button(role)
                hovered = self.render_button(role, state=QStyle.StateFlag.State_MouseOver)
                pressed = self.render_button(role, state=QStyle.StateFlag.State_Sunken)
                self.assertEqual(normal.size(), hovered.size())
                self.assertEqual(normal.size(), pressed.size())
                self.assertGreater(
                    hovered.pixelColor(50, 15).lightness(),
                    normal.pixelColor(50, 15).lightness(),
                )
                self.assertNotEqual(pressed.pixelColor(50, 15), normal.pixelColor(50, 15))
                self.assertEqual(
                    pressed.pixelColor(50, 5),
                    pressed.pixelColor(50, 24),
                )

    def test_noticeboard_option_and_action_use_flat_surfaces(self):
        for cls in (NoticeboardOption, NoticeboardAction):
            with self.subTest(widget=cls.__name__):
                button = cls("")
                self.addCleanup(button.deleteLater)
                button.resize(140, 32)
                if isinstance(button, NoticeboardOption):
                    button.setCheckable(True)
                    button.setChecked(True)
                else:
                    button.primary = True
                normal = button.grab().toImage()
                self.assertEqual(normal.pixelColor(20, 8), normal.pixelColor(20, 22))
                button.setDown(True)
                pressed = button.grab().toImage()
                self.assertNotEqual(normal.pixelColor(20, 15), pressed.pixelColor(20, 15))

    def test_disabled_buttons_are_muted_even_when_filter_is_checked(self):
        for role in ("eventFilter", "familyAction"):
            with self.subTest(role=role):
                enabled = self.render_button(role, checked=True)
                disabled = self.render_button(role, checked=True, enabled=False)
                self.assertLess(
                    disabled.pixelColor(50, 15).saturation(),
                    enabled.pixelColor(50, 15).saturation(),
                )

    def test_keyboard_focus_uses_visible_outline_not_a_thicker_border(self):
        for role, expected in (
            ("eventFilter", DEFAULT_UI_THEME.focus),
            ("familyAction", "#8b682c"),
        ):
            with self.subTest(role=role):
                focused = self.render_button(role, state=QStyle.StateFlag.State_HasFocus)
                normal = self.render_button(role)
                self.assertEqual(focused.pixelColor(50, 0).name(), expected)
                self.assertEqual(focused.pixelColor(50, 2), normal.pixelColor(50, 2))


if __name__ == "__main__":
    unittest.main()
