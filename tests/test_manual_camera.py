import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, QPoint, QPointF, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

from tanuki_core.manual_camera import (
    MANUAL_CAMERA_INPUT_ALPHA,
    MANUAL_CAMERA_OUTPUT_SIZES,
    ManualCameraController,
    ManualCameraOverlay,
    fit_viewfinder_size,
    interpolate_pointer_center,
    normalize_manual_camera_aspect,
)
from tanuki_core.memory_album import MemoryAlbumService


class FakeOverlay(QObject):
    capture_requested = pyqtSignal(QRect, QSize)
    cancelled = pyqtSignal()

    def __init__(self, aspect_key, hint_text):
        super().__init__()
        self.aspect_key = aspect_key
        self.hint_text = hint_text
        self.shown = False
        self.hidden = False
        self.closed = False

    def show_camera(self):
        self.shown = True

    def hide(self):
        self.hidden = True

    def close(self):
        self.closed = True


class ManualCameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fixed_outputs_scale_down_only_for_small_screens(self):
        self.assertEqual(
            fit_viewfinder_size(QSize(534, 300), QSize(1920, 1080)),
            QSize(534, 300),
        )
        compact = fit_viewfinder_size(
            QSize(1280, 720),
            QSize(1000, 650),
        )
        self.assertLess(compact.width(), 1280)
        self.assertAlmostEqual(
            compact.width() / compact.height(),
            16.0 / 9.0,
            places=2,
        )
        self.assertEqual(normalize_manual_camera_aspect("unknown"), "16:9")
        self.assertEqual(MANUAL_CAMERA_OUTPUT_SIZES["4:3"], QSize(400, 300))
        self.assertEqual(MANUAL_CAMERA_OUTPUT_SIZES["16:9"], QSize(534, 300))

    def test_pointer_follow_uses_subpixel_interpolation_and_converges(self):
        point = QPointF(0.0, 0.0)
        target = QPointF(100.0, 50.0)
        point = interpolate_pointer_center(point, target)
        self.assertEqual(point, QPointF(65.0, 32.5))
        for _ in range(20):
            point = interpolate_pointer_center(point, target)
        self.assertEqual(point, target)

    def test_left_mouse_press_is_the_primary_shutter(self):
        overlay = ManualCameraOverlay(
            aspect_key="4:3",
            hint_text="left click",
        )
        requested = []
        overlay.capture_requested.connect(
            lambda rect, size: requested.append((rect, size))
        )
        overlay.resize(800, 600)
        overlay.show()
        self.app.processEvents()

        QTest.mouseClick(
            overlay,
            Qt.MouseButton.LeftButton,
            pos=overlay.rect().center(),
        )

        self.assertEqual(len(requested), 1)
        self.assertFalse(requested[0][0].isEmpty())
        self.assertEqual(requested[0][1], QSize(400, 300))
        overlay.close()

    def test_clear_viewfinder_keeps_nonzero_native_input_alpha(self):
        overlay = ManualCameraOverlay(
            aspect_key="4:3",
            hint_text="left click",
        )
        overlay.setGeometry(QRect(0, 0, 800, 600))
        overlay.move_viewfinder(QPoint(400, 320), immediate=True)
        image = QImage(overlay.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        overlay.render(image)

        frame_center = overlay._frame_rect_local().center()
        pixel = image.pixelColor(frame_center)
        self.assertEqual(pixel.alpha(), MANUAL_CAMERA_INPUT_ALPHA)
        overlay.close()

    def test_enter_does_not_trigger_camera_shutter(self):
        overlay = ManualCameraOverlay(
            aspect_key="4:3",
            hint_text="left click",
        )
        requested = []
        overlay.capture_requested.connect(
            lambda rect, size: requested.append((rect, size))
        )
        overlay.show()
        self.app.processEvents()

        QTest.keyClick(overlay, Qt.Key.Key_Return)
        QTest.keyClick(overlay, Qt.Key.Key_Enter)

        self.assertEqual(requested, [])
        overlay.close()

    def test_controller_saves_manual_photo_and_closes_overlay(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(temporary_directory)
            overlays = []
            image = QImage(534, 300, QImage.Format.Format_ARGB32)
            image.fill(QColor("#334455"))
            controller = ManualCameraController(
                album_service=service,
                capacity_provider=lambda: 20,
                time_scale_provider=lambda: 1.0,
                hint_provider=lambda: "controls",
                image_provider=lambda rect, size: image,
                overlay_factory=lambda aspect, hint: overlays.append(
                    FakeOverlay(aspect, hint)
                ) or overlays[-1],
            )
            finished = []
            statuses = []
            controller.capture_finished.connect(finished.append)
            controller.status_changed.connect(statuses.append)

            self.assertTrue(controller.start())
            overlay = overlays[0]
            self.assertTrue(overlay.shown)
            self.assertEqual(overlay.hint_text, "controls")
            with patch(
                "tanuki_core.manual_camera.QTimer.singleShot",
                side_effect=lambda _delay, callback: callback(),
            ):
                overlay.capture_requested.emit(
                    QRect(10, 20, 534, 300),
                    QSize(534, 300),
                )

            self.assertTrue(overlay.hidden)
            self.assertTrue(overlay.closed)
            self.assertFalse(controller.active)
            self.assertEqual(statuses[-1], "saved")
            self.assertTrue(finished[-1].is_file())
            self.assertEqual(
                service.snapshot(mode="off", capacity=20).entries[0].kind,
                "manual",
            )

    def test_speed_and_full_album_block_camera_before_overlay_is_created(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            service = MemoryAlbumService(temporary_directory)
            overlays = []
            speed_controller = ManualCameraController(
                album_service=service,
                capacity_provider=lambda: 20,
                time_scale_provider=lambda: 8.0,
                overlay_factory=lambda aspect, hint: overlays.append(
                    FakeOverlay(aspect, hint)
                ) or overlays[-1],
            )
            statuses = []
            speed_controller.status_changed.connect(statuses.append)
            self.assertFalse(speed_controller.start())
            self.assertEqual(statuses, ["speed"])
            self.assertEqual(overlays, [])

            service.root.mkdir(parents=True)
            for index in range(20):
                (service.root / f"photo-{index:02d}.png").write_bytes(b"png")
            full_controller = ManualCameraController(
                album_service=service,
                capacity_provider=lambda: 20,
                time_scale_provider=lambda: 1.0,
                overlay_factory=lambda aspect, hint: overlays.append(
                    FakeOverlay(aspect, hint)
                ) or overlays[-1],
            )
            statuses = []
            full_controller.status_changed.connect(statuses.append)
            self.assertFalse(full_controller.start())
            self.assertEqual(statuses, ["full"])
            self.assertEqual(overlays, [])


if __name__ == "__main__":
    unittest.main()
