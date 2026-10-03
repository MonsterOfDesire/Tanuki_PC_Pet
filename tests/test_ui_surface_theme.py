"""Verify translucent content backplates, not scene assets or widget geometry."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QFrame, QStyle, QStyleOption

from tanuki_core.ui_theme import DEFAULT_UI_THEME, build_ui_stylesheet
from tanuki_core.ui_surface_materials import SkinContentSurface


def contrast_ratio(text, surface, backdrop):
    alpha = surface.alphaF()
    mixed = [
        alpha * foreground + (1.0 - alpha) * background
        for foreground, background in zip(surface.getRgbF()[:3], backdrop.getRgbF()[:3])
    ]

    def luminance(channels):
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

    values = sorted((luminance(text.getRgbF()[:3]), luminance(mixed)))
    return (values[1] + 0.05) / (values[0] + 0.05)


class ContentSurfaceThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def render_surface(self, role, *, inner=False, size=(320, 200)):
        frame = QFrame()
        self.addCleanup(frame.deleteLater)
        if not inner:
            frame.setObjectName("tanukiSkinContentSurface")
        frame.setProperty("tanukiRole" if inner else "surfaceRole", role)
        frame.setStyleSheet(build_ui_stylesheet())
        frame.resize(*size)
        frame.ensurePolished()
        option = QStyleOption()
        option.initFrom(frame)
        image = QImage(frame.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        frame.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, frame)
        painter.end()
        return image

    def test_family_surface_is_flat_and_retains_transparency(self):
        for role in ("frosted",):
            for size in ((320, 200), (700, 420)):
                with self.subTest(role=role, size=size):
                    image = self.render_surface(role, size=size)
                    x = image.width() // 2
                    top = image.pixelColor(x, image.height() // 10)
                    bottom = image.pixelColor(x, image.height() * 9 // 10)
                    self.assertEqual(top, bottom)
                    self.assertTrue(220 <= top.alpha() < 255)
                    self.assertTrue(220 <= bottom.alpha() < 255)
                    self.assertEqual(image.pixelColor(0, 0).alpha(), 0)

    def test_family_inner_panels_are_flat(self):
        for role in ("familyCard", "familySectionCard", "familyStats"):
            with self.subTest(role=role):
                image = self.render_surface(role, inner=True)
                self.assertEqual(
                    image.pixelColor(160, 20),
                    image.pixelColor(160, 180),
                )

    def test_primary_text_contrast_over_bright_and_dark_backdrops(self):
        for role, text in (
            ("frosted", DEFAULT_UI_THEME.text_primary),
            ("chalkboard", DEFAULT_UI_THEME.text_inverse),
        ):
            image = self.render_surface(role)
            for y in (20, 100, 180):
                for backdrop in ("#000000", "#ffffff"):
                    with self.subTest(role=role, y=y, backdrop=backdrop):
                        self.assertGreaterEqual(
                            contrast_ratio(QColor(text), image.pixelColor(160, y), QColor(backdrop)),
                            4.5,
                        )

    def test_other_page_surface_materials_remain_flat(self):
        for role in ("paper", "glass", "achievement_cabinet", "dark", "chalkboard"):
            with self.subTest(role=role):
                image = self.render_surface(role)
                self.assertEqual(image.pixelColor(160, 20), image.pixelColor(160, 180))

    def test_chalk_texture_is_cached_until_size_changes_and_only_on_event_skin(self):
        surface = SkinContentSurface()
        self.addCleanup(surface.deleteLater)
        surface.setObjectName("tanukiSkinContentSurface")
        surface.setStyleSheet(build_ui_stylesheet())
        surface.setProperty("surfaceRole", "chalkboard")
        surface.resize(320, 200)
        surface.grab()
        texture = surface._chalk_texture
        self.assertIsNotNone(texture)
        pixels = texture.toImage()
        self.assertGreater(len({pixels.pixel(x, y) for x in range(0, 320, 7) for y in range(0, 200, 7)}), 3)
        surface.grab()
        self.assertIs(surface._chalk_texture, texture)
        surface.resize(400, 220)
        surface.grab()
        self.assertIsNot(surface._chalk_texture, texture)
        surface.setProperty("surfaceRole", "frosted")
        surface.grab()
        self.assertIsNone(surface._chalk_texture)


if __name__ == "__main__":
    unittest.main()
