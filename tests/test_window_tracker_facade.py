import unittest
from dataclasses import dataclass
import sys
import types


class _FakeQObject:
    pass


class _FakePoint:
    def __init__(self, x, y):
        self._x = x
        self._y = y

    def x(self):
        return self._x

    def y(self):
        return self._y


class _FakeQRect:
    def __init__(self, left, top, width, height):
        self._left = left
        self._top = top
        self._width = width
        self._height = height

    def left(self):
        return self._left

    def top(self):
        return self._top

    def width(self):
        return self._width

    def height(self):
        return self._height

    def contains(self, point):
        return (
            self._left <= point.x() <= (self._left + self._width - 1)
            and self._top <= point.y() <= (self._top + self._height - 1)
        )


fake_qtcore = types.ModuleType("PyQt6.QtCore")
fake_qtcore.QObject = _FakeQObject
fake_qtcore.QPoint = _FakePoint
fake_qtcore.QRect = _FakeQRect

fake_qtwidgets = types.ModuleType("PyQt6.QtWidgets")
fake_qtwidgets.QApplication = type(
    "_FakeQApplication",
    (),
    {
        "screenAt": staticmethod(lambda *_args, **_kwargs: None),
        "primaryScreen": staticmethod(lambda: None),
    },
)

fake_pyqt6 = types.ModuleType("PyQt6")
fake_pyqt6.QtCore = fake_qtcore
fake_pyqt6.QtWidgets = fake_qtwidgets

sys.modules.setdefault("PyQt6", fake_pyqt6)
sys.modules.setdefault("PyQt6.QtCore", fake_qtcore)
sys.modules.setdefault("PyQt6.QtWidgets", fake_qtwidgets)

from tanuki_core.window_tracker import WindowTracker


@dataclass(frozen=True)
class FakeRect:
    left_value: int
    top_value: int
    width_value: int
    height_value: int

    def left(self):
        return self.left_value

    def top(self):
        return self.top_value

    def width(self):
        return self.width_value

    def height(self):
        return self.height_value

    def contains(self, point):
        return (
            self.left_value <= point.x() <= (self.left_value + self.width_value - 1)
            and self.top_value <= point.y() <= (self.top_value + self.height_value - 1)
        )


@dataclass(frozen=True)
class FakeSnapshot:
    hwnd: int
    rect: FakeRect
    title: str
    class_name: str
    pid: int = 100
    owner_hwnd: int = 0
    style: int = 0
    ex_style: int = 0
    is_visible: bool = True
    is_iconic: bool = False
    is_cloaked: bool = False


class FakeBackend:
    def __init__(self, snapshots, own_pid=999):
        self.available = True
        self.own_pid = own_pid
        self._snapshots = snapshots

    def enumerate_window_snapshots(self):
        return list(self._snapshots)


class WindowTrackerTests(unittest.TestCase):
    def test_refresh_builds_surface_map_from_backend_snapshots(self):
        tracker = WindowTracker(
            backend=FakeBackend(
                [
                    FakeSnapshot(1, FakeRect(0, 0, 400, 300), "Editor", "CabinetWClass"),
                    FakeSnapshot(2, FakeRect(10, 10, 100, 60), "Tiny", "CabinetWClass"),
                ]
            )
        )

        tracker.refresh()

        self.assertEqual(len(tracker.surfaces), 1)
        self.assertEqual(tracker.surfaces[0].hwnd, 1)
        self.assertIs(tracker.get_surface_by_hwnd(1), tracker.surfaces[0])


if __name__ == "__main__":
    unittest.main()
