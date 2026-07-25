import unittest

from tanuki_core.information_center_size_rules import SIZE_16_10
from tanuki_core.information_center_spec import (
    PAGE_EVENT_LOG,
    PAGE_FAMILY_STATUS,
)
from tanuki_core.information_center_state import (
    InformationCenterConfigState,
    build_information_center_config_state,
    clamp_information_center_geometry,
    information_center_config_state_to_payload,
    normalize_information_center_config_state,
)


class InformationCenterStateTests(unittest.TestCase):
    def test_state_round_trip_preserves_geometry_page_and_preset(self):
        state = build_information_center_config_state(
            x=120,
            y=80,
            width=960,
            height=640,
            page_id=PAGE_EVENT_LOG,
            size_preset_id=SIZE_16_10,
        )

        payload = information_center_config_state_to_payload(state)
        restored = normalize_information_center_config_state(payload)

        self.assertEqual(restored, state)
        self.assertTrue(restored.has_saved_position)

    def test_invalid_values_fall_back_without_inventing_a_position(self):
        defaults = InformationCenterConfigState()

        state = normalize_information_center_config_state(
            {
                "x": "bad",
                "y": None,
                "width": -1,
                "height": "bad",
                "page_id": "missing",
                "size_preset_id": "missing",
            },
            defaults=defaults,
        )

        self.assertIsNone(state.x)
        self.assertIsNone(state.y)
        self.assertEqual(state.width, defaults.width)
        self.assertEqual(state.height, defaults.height)
        self.assertEqual(state.page_id, PAGE_FAMILY_STATUS)
        self.assertEqual(state.size_preset_id, "")
        self.assertFalse(state.has_saved_position)

    def test_clamp_geometry_keeps_saved_window_inside_available_screen(self):
        state = build_information_center_config_state(
            x=5000,
            y=-5000,
            width=1600,
            height=1200,
        )

        geometry = clamp_information_center_geometry(
            state,
            available_geometry=(100, 50, 900, 700),
            minimum_size=(720, 420),
        )

        self.assertEqual(geometry, (100, 50, 900, 700))

    def test_clamp_geometry_preserves_unsaved_position_marker(self):
        state = build_information_center_config_state(
            width=900,
            height=600,
        )

        geometry = clamp_information_center_geometry(
            state,
            available_geometry=(100, 50, 1200, 800),
            minimum_size=(720, 420),
        )

        self.assertEqual(geometry, (None, None, 900, 600))


if __name__ == "__main__":
    unittest.main()
