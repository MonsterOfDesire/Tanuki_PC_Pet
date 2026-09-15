import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

from tanuki_core.memory_album import MemoryAlbumEntry, MemoryAlbumSnapshot
from tanuki_core.memory_album_ui import MemoryAlbumPanel


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

        binding.value = MemoryAlbumSnapshot("events", 20, 20, ())
        panel.refresh_from_binding()
        self.assertIn("不再拍攝新照片", panel.status_label.text())
        self.assertIn("不會自動刪除", panel.status_label.text())
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
        panel.deleteLater()

    def test_gallery_builds_icon_card_for_existing_photo(self):
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
            self.assertFalse(panel._cards[0].icon().isNull())
            panel.deleteLater()


if __name__ == "__main__":
    unittest.main()
