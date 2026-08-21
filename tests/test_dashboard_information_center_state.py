import unittest
from unittest.mock import patch

from PyQt6.QtCore import QRect

from tanuki_core.dashboard_ui import Dashboard
from tanuki_core.information_center_spec import (
    PAGE_ACHIEVEMENTS,
    PAGE_EVENT_LOG,
    PAGE_STATUS_SETTINGS,
)
from tanuki_core.information_center_state import (
    build_information_center_config_state,
)


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in tuple(self.callbacks):
            callback()


class FakeInformationCenterWindow:
    def __init__(self):
        self.state_changed = FakeSignal()
        self.user_position_locked = False
        self.state = build_information_center_config_state()
        self.restore_calls = []
        self.move_calls = []
        self.open_calls = []
        self.achievement_refresh_calls = []

    def restore_config_state(self, state):
        self.state = state
        self.user_position_locked = state.has_saved_position
        self.restore_calls.append(state)

    def capture_config_state(self):
        return self.state

    def move_near_anchor(self, x, y):
        self.move_calls.append((x, y))

    def open_page(self, page_id=None):
        self.open_calls.append(page_id)

    def refresh_achievement_cabinet(self, *, sync_world_mode=False):
        self.achievement_refresh_calls.append(bool(sync_world_mode))
        return True

    def width(self):
        return self.state.width

    def height(self):
        return self.state.height


class FakeDashboard:
    def __init__(self, state):
        self.information_center_window = None
        self.information_center_config_state = state
        self.resource_resolver = lambda path: path
        self.status_settings_binding = object()
        self.family_summary_binding = object()
        self.event_log_binding = object()
        self.relation_summon_binding = object()
        self.achievement_binding = object()
        self.target_rect = QRect(0, 0, 1920, 1080)
        self.save_calls = 0

    def x(self):
        return 100

    def y(self):
        return 200

    def width(self):
        return 360

    def schedule_save(self):
        self.save_calls += 1

    def _handle_information_center_state_changed(self):
        Dashboard._handle_information_center_state_changed(self)

    def show_information_center(self, page_id=None):
        return Dashboard.show_information_center(self, page_id)


class DashboardInformationCenterStateTests(unittest.TestCase):
    def test_achievement_entry_opens_embedded_information_center_page(self):
        dashboard = FakeDashboard(build_information_center_config_state())
        window = FakeInformationCenterWindow()

        with patch(
            "tanuki_core.dashboard_ui.InformationCenterWindow",
            return_value=window,
        ):
            result = Dashboard.show_achievement_cabinet(dashboard)

        self.assertTrue(result)
        self.assertEqual(window.open_calls, [PAGE_ACHIEVEMENTS])
        self.assertEqual(window.achievement_refresh_calls, [True])

    def test_first_open_restores_saved_geometry_and_last_page(self):
        state = build_information_center_config_state(
            x=240,
            y=160,
            width=900,
            height=600,
            page_id=PAGE_EVENT_LOG,
        )
        dashboard = FakeDashboard(state)
        window = FakeInformationCenterWindow()

        with patch(
            "tanuki_core.dashboard_ui.InformationCenterWindow",
            return_value=window,
        ):
            Dashboard.show_information_center(dashboard)

        self.assertEqual(window.restore_calls, [state])
        self.assertEqual(window.move_calls, [])
        self.assertEqual(window.open_calls, [PAGE_EVENT_LOG])
        self.assertEqual(dashboard.save_calls, 0)

    def test_unsaved_position_uses_anchor_but_preserves_last_page(self):
        state = build_information_center_config_state(
            page_id=PAGE_STATUS_SETTINGS,
        )
        dashboard = FakeDashboard(state)
        window = FakeInformationCenterWindow()

        with patch(
            "tanuki_core.dashboard_ui.InformationCenterWindow",
            return_value=window,
        ):
            Dashboard.show_information_center(dashboard)

        self.assertEqual(window.move_calls, [(476, 200)])
        self.assertEqual(window.open_calls, [PAGE_STATUS_SETTINGS])

    def test_window_state_change_updates_pending_state_and_schedules_save(self):
        dashboard = FakeDashboard(build_information_center_config_state())
        window = FakeInformationCenterWindow()

        with patch(
            "tanuki_core.dashboard_ui.InformationCenterWindow",
            return_value=window,
        ):
            Dashboard.show_information_center(dashboard)

        updated_state = build_information_center_config_state(
            x=320,
            y=180,
            width=960,
            height=640,
            page_id=PAGE_EVENT_LOG,
        )
        window.state = updated_state
        window.state_changed.emit()

        self.assertEqual(
            dashboard.information_center_config_state,
            updated_state,
        )
        self.assertEqual(dashboard.save_calls, 1)


if __name__ == "__main__":
    unittest.main()
