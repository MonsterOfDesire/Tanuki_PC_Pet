import unittest
from types import SimpleNamespace


try:
    from PyQt6.QtCore import Qt
    from tanuki_core.offer_ground_item_ui import GroundOfferItemWidget
    from tanuki_core.offer_tray_ui import OfferItemBadge
except (ImportError, ModuleNotFoundError) as exc:
    Qt = None
    GroundOfferItemWidget = None
    OfferItemBadge = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class FakeReleaseEvent:
    def button(self):
        return Qt.MouseButton.LeftButton

    def globalPosition(self):
        return SimpleNamespace(toPoint=lambda: "release-position")


class FakeTrayBadge:
    def __init__(self):
        self.drag_ghost = None
        self.drag_started = True
        self.item_definition = SimpleNamespace(kind="ramen")
        self.calls = []
        self.drop_handler = lambda item_kind, pos: self.calls.append(("drop", item_kind, pos))
        self.clear_hover_handler = lambda: self.calls.append(("clear",))

    def releaseMouse(self):
        return None

    def setCursor(self, cursor):
        _ = cursor


class FakeGroundItem:
    def __init__(self):
        self.draggable = True
        self.drag_started = True
        self.item_kind = "ramen"
        self.calls = []
        self.drop_handler = lambda widget, item_kind, pos: self.calls.append(
            ("drop", widget, item_kind, pos)
        )
        self.clear_hover_handler = lambda: self.calls.append(("clear",))

    def releaseMouse(self):
        return None

    def setCursor(self, cursor):
        _ = cursor


@unittest.skipIf(OfferItemBadge is None, f"PyQt6 unavailable: {IMPORT_ERROR}")
class OfferReleaseUiTests(unittest.TestCase):
    def test_tray_drag_release_delegates_hover_finalization_to_drop_handler(self):
        badge = FakeTrayBadge()

        OfferItemBadge.mouseReleaseEvent(badge, FakeReleaseEvent())

        self.assertEqual(badge.calls, [("drop", "ramen", "release-position")])
        self.assertFalse(badge.drag_started)

    def test_ground_item_release_delegates_hover_finalization_to_drop_handler(self):
        item = FakeGroundItem()

        GroundOfferItemWidget.mouseReleaseEvent(item, FakeReleaseEvent())

        self.assertEqual(item.calls, [("drop", item, "ramen", "release-position")])
        self.assertFalse(item.drag_started)


if __name__ == "__main__":
    unittest.main()
