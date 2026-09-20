import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

from tanuki_core.memory_album import MemoryAlbumEntry, MemoryAlbumSnapshot
from tanuki_core.memory_album_ui import MemoryAlbumPanel, MemoryPhotoCard


class FakeBinding:
    def __init__(self, snapshot):
        self.value = snapshot
        self.modes = []
        self.capacities = []
        self.opened = 0

    def snapshot(self):
        return self.value

    def set_mode(self, mode):
        self.modes.append(mode)
        self.value = MemoryAlbumSnapshot(mode, self.value.capacity, self.value.count, self.value.entries)
        return True

    def set_capacity(self, capacity):
        self.capacities.append(capacity)
        self.value = MemoryAlbumSnapshot(self.value.mode, capacity, self.value.count, self.value.entries)
        return True

    def open_folder(self):
        self.opened += 1
        return True


class MemoryAlbumPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_panel_shows_near_full_and_full_capacity_messages(self):
        binding = FakeBinding(MemoryAlbumSnapshot("events", 20, 16, ()))
        panel = MemoryAlbumPanel(binding)
        panel.refresh_from_binding()
        self.assertIn("即將滿載", panel.status_label.text())
        self.assertIn("抵達上限", panel.status_label.toolTip())

        binding.value = MemoryAlbumSnapshot("events", 20, 20, ())
        panel.refresh_from_binding()
        self.assertIn("相簿已滿", panel.status_label.text())
        self.assertIn("不再拍攝新照片", panel.status_label.toolTip())
        self.assertIn("不會自動刪除", panel.status_label.toolTip())
        self.assertEqual(panel.status_label.property("albumState"), "full")
        panel.deleteLater()

    def test_controls_update_binding_and_open_folder(self):
        binding = FakeBinding(MemoryAlbumSnapshot("off", 20, 0, ()))
        panel = MemoryAlbumPanel(binding)

        panel.set_mode("random")
        panel.set_capacity(50)
        panel.open_folder()

        self.assertEqual(binding.modes, ["random"])
        self.assertEqual(binding.capacities, [50])
        self.assertEqual(binding.opened, 1)
        self.assertFalse(hasattr(panel, "mode_buttons"))
        self.assertEqual(panel.open_folder_button.text(), "照片資料夾")
        panel.deleteLater()

    def test_gallery_builds_polaroid_card_for_existing_photo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            photo_path = Path(temp_dir) / "memory.png"
            image = QImage(64, 48, QImage.Format.Format_ARGB32)
            image.fill(QColor("#88bb66"))
            self.assertTrue(image.save(str(photo_path), "PNG"))
            entry = MemoryAlbumEntry(
                path=photo_path,
                captured_at="2026-09-13T21:21:13+08:00",
                kind="daily",
            )
            binding = FakeBinding(
                MemoryAlbumSnapshot("random", 20, 1, (entry,))
            )
            panel = MemoryAlbumPanel(binding)

            self.assertTrue(panel.refresh_from_binding())
            self.assertEqual(len(panel._cards), 1)
            card = panel._cards[0]
            self.assertIsInstance(card, MemoryPhotoCard)
            self.assertFalse(card._pixmap.isNull())
            self.assertTrue(card.pin_color.isValid())
            card.resize(240, 174)
            self.assertFalse(card.grab().isNull())
            panel.deleteLater()

    def test_photo_card_hover_lifts_without_changing_layout_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            photo_path = Path(temp_dir) / "memory.png"
            image = QImage(64, 48, QImage.Format.Format_ARGB32)
            image.fill(QColor("#88bb66"))
            self.assertTrue(image.save(str(photo_path), "PNG"))
            card = MemoryPhotoCard(
                MemoryAlbumEntry(photo_path, "2026-09-13T21:21:13+08:00")
            )
            original_size = card.sizeHint()

            card.set_hover_progress(1.0)

            self.assertEqual(card.hoverProgress, 1.0)
            self.assertEqual(card.sizeHint(), original_size)
            card.deleteLater()

    def test_photo_card_uses_source_aspect_ratio_without_crop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            photo_path = Path(temp_dir) / "memory.png"
            image = QImage(1600, 900, QImage.Format.Format_ARGB32)
            image.fill(QColor("#557799"))
            self.assertTrue(image.save(str(photo_path), "PNG"))
            card = MemoryPhotoCard(
                MemoryAlbumEntry(photo_path, "2026-09-13T21:21:13+08:00")
            )

            self.assertGreater(card.heightForWidth(320), 200)
            viewport = QRectF(0.0, 0.0, 276.0, 155.25)
            contained = card._contain_target_rect(viewport)

            self.assertAlmostEqual(
                contained.width() / contained.height(),
                16.0 / 9.0,
                places=3,
            )
            self.assertEqual(contained, viewport)
            self.assertLessEqual(
                max(card._pixmap.width(), card._pixmap.height()),
                512,
            )
            self.assertEqual(card._source_size.width(), 1600)
            self.assertEqual(card._source_size.height(), 900)
            card.deleteLater()

    def test_portrait_and_landscape_photos_use_different_card_heights(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            portrait_path = Path(temp_dir) / "portrait.png"
            landscape_path = Path(temp_dir) / "landscape.png"
            portrait = QImage(900, 1200, QImage.Format.Format_ARGB32)
            landscape = QImage(1600, 900, QImage.Format.Format_ARGB32)
            portrait.fill(QColor("#775599"))
            landscape.fill(QColor("#557799"))
            self.assertTrue(portrait.save(str(portrait_path), "PNG"))
            self.assertTrue(landscape.save(str(landscape_path), "PNG"))

            portrait_card = MemoryPhotoCard(
                MemoryAlbumEntry(portrait_path, "2026-09-13T21:21:13+08:00")
            )
            landscape_card = MemoryPhotoCard(
                MemoryAlbumEntry(landscape_path, "2026-09-13T21:21:14+08:00")
            )

            self.assertGreater(
                portrait_card.heightForWidth(240),
                landscape_card.heightForWidth(240),
            )
            portrait_viewport = QRectF(0.0, 0.0, 150.0, 200.0)
            self.assertEqual(
                portrait_card._contain_target_rect(portrait_viewport),
                portrait_viewport,
            )
            portrait_card.deleteLater()
            landscape_card.deleteLater()

    def test_photo_card_uses_system_image_viewer(self):
        entry = MemoryAlbumEntry(
            Path("G:/photos/memory.png"),
            "2026-09-13T21:21:13+08:00",
        )
        card = MemoryPhotoCard(entry)

        with patch(
            "tanuki_core.memory_album_ui.QDesktopServices.openUrl",
            return_value=True,
        ) as opener:
            self.assertTrue(card.open_photo())

        opened_url = opener.call_args.args[0]
        self.assertTrue(opened_url.isLocalFile())
        self.assertTrue(opened_url.toLocalFile().replace("\\", "/").endswith("/photos/memory.png"))
        card.deleteLater()

    def test_gallery_uses_two_or_four_columns_without_odd_book_spread(self):
        self.assertEqual(MemoryAlbumPanel.column_count_for_width(680), 2)
        self.assertEqual(MemoryAlbumPanel.column_count_for_width(960), 4)


if __name__ == "__main__":
    unittest.main()
