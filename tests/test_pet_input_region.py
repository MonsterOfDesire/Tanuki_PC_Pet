import os
import types
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from tanuki_core.pet_input_region import PetInputRegionController


class PetInputRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def build_pet(self):
        image = QImage(4, 3, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        image.setPixelColor(2, 1, QColor(255, 255, 255, 255))
        frame = QPixmap.fromImage(image)
        pet = QWidget()
        pet.setFixedSize(10, 8)
        pet.current_frames = [frame]
        pet.frame_index = 0
        pet.direction = -1
        pet.original_face_left = True
        pet.display_scale_multiplier = 1.0
        pet.bar_opacity = 0.0
        pet.show_heart = False
        pet.star_opacity = 0.0
        pet.show_log_icon = False
        pet.activity_state = types.SimpleNamespace(active=False)
        pet.is_debug_enabled = lambda: False
        pet.is_social_status_enabled = lambda: False
        return pet

    def test_transparent_widget_padding_is_outside_native_input_region(self):
        pet = self.build_pet()
        controller = PetInputRegionController(enabled=True)
        try:
            self.assertTrue(controller.refresh(pet, force=True))

            self.assertTrue(pet.mask().contains(QPoint(5, 6)))
            self.assertFalse(pet.mask().contains(QPoint(0, 0)))
            self.assertFalse(pet.mask().contains(QPoint(3, 6)))
        finally:
            pet.close()
            pet.deleteLater()

    def test_flipped_character_updates_native_input_region(self):
        pet = self.build_pet()
        pet.direction = 1
        controller = PetInputRegionController(enabled=True)
        try:
            controller.refresh(pet, force=True)

            self.assertTrue(pet.mask().contains(QPoint(4, 6)))
            self.assertFalse(pet.mask().contains(QPoint(5, 6)))
        finally:
            pet.close()
            pet.deleteLater()


if __name__ == "__main__":
    unittest.main()
