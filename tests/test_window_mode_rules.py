import unittest

from tanuki_core.window_mode_rules import (
    can_start_window_flight_gate,
)


class WindowModeRuleTests(unittest.TestCase):
    def test_window_flight_gate_requires_clean_runtime_state(self):
        self.assertTrue(
            can_start_window_flight_gate(
                flight_mode="none",
                perched_window_hwnd=0,
                dragging=False,
                vertical_velocity=0,
                is_visible=True,
                state="move",
                care_mode="none",
                social_mode="none",
                is_recovering=False,
                is_under_care=False,
                now=10.0,
                flight_cooldown_end=5.0,
                has_window_tracker=True,
                can_fly_freely=True,
                current_purpose="move",
                current_action_tag="fly",
            )
        )
        self.assertFalse(
            can_start_window_flight_gate(
                flight_mode="none",
                perched_window_hwnd=123,
                dragging=False,
                vertical_velocity=0,
                is_visible=True,
                state="move",
                care_mode="none",
                social_mode="none",
                is_recovering=False,
                is_under_care=False,
                now=10.0,
                flight_cooldown_end=5.0,
                has_window_tracker=True,
                can_fly_freely=True,
                current_purpose="move",
                current_action_tag="fly",
            )
        )

    def test_window_flight_gate_rejects_non_flight_animation(self):
        self.assertFalse(
            can_start_window_flight_gate(
                flight_mode="none",
                perched_window_hwnd=0,
                dragging=False,
                vertical_velocity=0,
                is_visible=True,
                state="move",
                care_mode="none",
                social_mode="none",
                is_recovering=False,
                is_under_care=False,
                now=10.0,
                flight_cooldown_end=5.0,
                has_window_tracker=True,
                can_fly_freely=True,
                current_purpose="move",
                current_action_tag="walk",
            )
        )

if __name__ == "__main__":
    unittest.main()
