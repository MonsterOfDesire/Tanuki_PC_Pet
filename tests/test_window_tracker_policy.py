import unittest
from dataclasses import dataclass

from tanuki_core.window_tracker_policy import WindowSurface, build_window_surface


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


@dataclass(frozen=True)
class FakeSnapshot:
    hwnd: int = 1
    rect: FakeRect = FakeRect(10, 20, 400, 300)
    title: str = "Editor"
    class_name: str = "CabinetWClass"
    pid: int = 100
    owner_hwnd: int = 0
    style: int = 0
    ex_style: int = 0
    is_visible: bool = True
    is_iconic: bool = False
    is_cloaked: bool = False


class WindowTrackerPolicyTests(unittest.TestCase):
    def build_surface(self, snapshot):
        return build_window_surface(
            snapshot,
            own_pid=999,
            min_window_width=180,
            min_window_height=80,
            ws_ex_toolwindow=0x00000080,
            ws_child=0x40000000,
            ws_popup=0x80000000,
            ws_caption=0x00C00000,
        )

    def test_build_window_surface_returns_surface_for_valid_snapshot(self):
        surface = self.build_surface(FakeSnapshot())

        self.assertIsInstance(surface, WindowSurface)
        self.assertEqual(surface.hwnd, 1)
        self.assertEqual(surface.title, "Editor")

    def test_build_window_surface_rejects_hidden_or_iconic_or_cloaked_windows(self):
        self.assertIsNone(self.build_surface(FakeSnapshot(is_visible=False)))
        self.assertIsNone(self.build_surface(FakeSnapshot(is_iconic=True)))
        self.assertIsNone(self.build_surface(FakeSnapshot(is_cloaked=True)))

    def test_build_window_surface_rejects_own_or_owned_windows(self):
        self.assertIsNone(self.build_surface(FakeSnapshot(pid=999)))
        self.assertIsNone(self.build_surface(FakeSnapshot(owner_hwnd=55)))

    def test_build_window_surface_rejects_disallowed_window_styles(self):
        self.assertIsNone(self.build_surface(FakeSnapshot(style=0x40000000)))
        self.assertIsNone(self.build_surface(FakeSnapshot(ex_style=0x00000080)))
        self.assertIsNone(self.build_surface(FakeSnapshot(style=0x80000000)))

    def test_build_window_surface_rejects_excluded_classes_missing_titles_and_tiny_windows(self):
        self.assertIsNone(self.build_surface(FakeSnapshot(class_name="WorkerW")))
        self.assertIsNone(self.build_surface(FakeSnapshot(title="")))
        self.assertIsNone(self.build_surface(FakeSnapshot(rect=FakeRect(10, 20, 100, 60))))


if __name__ == "__main__":
    unittest.main()
