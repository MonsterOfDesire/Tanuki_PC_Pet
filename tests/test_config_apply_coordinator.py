import unittest

from tanuki_core.config_apply_coordinator import ConfigApplyCoordinator
from tanuki_core.dashboard_state_mapper import DashboardConfigState, DashboardOptionBounds


class FakeDashboard:
    def __init__(self):
        self.applied_states = []
        self.time_scale_calls = []
        self.display_scale_calls = []
        self.social_settings_calls = []

    def capture_config_state(self):
        return DashboardConfigState(
            care_feature_enabled=True,
            teio_dur_idx=3,
            tsuyoshi_dur_idx=2,
            time_scale_idx=0,
            display_scale_idx=0,
            debug_enabled=False,
        )

    def get_option_bounds(self):
        return DashboardOptionBounds(
            teio_duration_count=5,
            tsuyoshi_duration_count=5,
            time_scale_count=4,
            display_scale_count=4,
        )

    def apply_config_state(self, state):
        self.applied_states.append(state)
        self.time_scale_idx = state.time_scale_idx
        self.display_scale_idx = state.display_scale_idx

    def set_time_scale_index(self, index, save=True):
        self.time_scale_calls.append((index, save))

    def apply_display_scale(self, save=True):
        self.display_scale_calls.append(save)

    def apply_social_settings(self, save=True):
        self.social_settings_calls.append(save)


class FakePet:
    def __init__(self):
        self._x = 120
        self._y = 340
        self.user_visible = True
        self.move_calls = []
        self.show_calls = 0
        self.hide_calls = 0
        self.refresh_calls = 0

    def x(self):
        return self._x

    def y(self):
        return self._y

    def move(self, x, y):
        self._x = x
        self._y = y
        self.move_calls.append((x, y))

    def show(self):
        self.show_calls += 1

    def hide(self):
        self.hide_calls += 1

    def refresh_movement_state(self):
        self.refresh_calls += 1


class FakeToggleButton:
    def __init__(self):
        self.block_calls = []
        self.checked = None

    def blockSignals(self, blocked):
        self.block_calls.append(blocked)

    def setChecked(self, checked):
        self.checked = checked


class ConfigApplyCoordinatorTests(unittest.TestCase):
    def test_apply_loaded_state_updates_dashboard_and_pets(self):
        dashboard = FakeDashboard()
        pet = FakePet()
        toggle = FakeToggleButton()
        coordinator = ConfigApplyCoordinator(lambda pet, x, y: (x + 10, y + 20))

        coordinator.apply_loaded_state(
            {
                "dashboard": {
                    "care_feature_enabled": False,
                    "time_scale_idx": 2,
                    "display_scale_idx": 1,
                },
                "pets": {
                    "Tokai Teio": {
                        "x": 400,
                        "y": 500,
                        "user_visible": False,
                    }
                },
            },
            dashboard,
            {"Tokai Teio": {"pet": pet, "toggle_button": toggle}},
        )

        self.assertEqual(len(dashboard.applied_states), 1)
        self.assertEqual(dashboard.time_scale_calls, [(2, False)])
        self.assertEqual(dashboard.display_scale_calls, [False])
        self.assertEqual(dashboard.social_settings_calls, [False])
        self.assertEqual(pet.move_calls, [(410, 520)])
        self.assertFalse(pet.user_visible)
        self.assertEqual(pet.hide_calls, 1)
        self.assertEqual(pet.refresh_calls, 1)
        self.assertEqual(toggle.block_calls, [True, False])
        self.assertFalse(toggle.checked)


if __name__ == "__main__":
    unittest.main()
