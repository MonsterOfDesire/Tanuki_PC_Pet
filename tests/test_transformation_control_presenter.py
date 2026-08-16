import unittest

from tanuki_core.transformation_control_presenter import (
    build_transformation_completion_text,
    build_transformation_control_presentation,
)


def _states(**overrides):
    states = {
        "Tokai Teio": {
            "available": True,
            "current_form": "base",
            "target_form": "",
            "active": False,
            "manual_end_requested": False,
            "auto_session": False,
            "source": "",
        },
        "Symboli Rudolf": {
            "available": True,
            "current_form": "base",
            "target_form": "",
            "active": False,
            "manual_end_requested": False,
            "auto_session": False,
            "source": "",
        },
    }
    for character_name, values in overrides.items():
        states[character_name].update(values)
    return states


class TransformationControlPresenterTests(unittest.TestCase):
    def test_sandbox_base_forms_stay_polling_for_autonomous_changes(self):
        presentation = build_transformation_control_presentation(
            _states(),
            world_mode="sandbox",
        )

        self.assertEqual(
            [button.text for button in presentation.buttons],
            ["手動變身帝寶", "手動變身魯道夫象徵"],
        )
        self.assertTrue(all(button.enabled for button in presentation.buttons))
        self.assertEqual(presentation.poll_interval_ms, 400)
        self.assertTrue(presentation.should_poll)
        self.assertFalse(presentation.has_active_operation)
        self.assertEqual(
            presentation.status_text,
            "帝寶、魯道夫象徵目前皆為普通形態；沙盒仍可能自主變身。",
        )

    def test_autonomous_transformed_form_is_identified_from_runtime(self):
        presentation = build_transformation_control_presentation(
            _states(
                **{
                    "Tokai Teio": {
                        "current_form": "transformed",
                        "auto_session": True,
                    }
                }
            ),
            world_mode="sandbox",
        )

        self.assertEqual(presentation.buttons[0].text, "解除帝寶變身")
        self.assertIn("帝寶目前為自主變身形態", presentation.status_text)
        self.assertEqual(presentation.poll_interval_ms, 400)

    def test_manual_transformed_form_has_manual_status(self):
        presentation = build_transformation_control_presentation(
            _states(
                **{
                    "Symboli Rudolf": {
                        "current_form": "transformed",
                    }
                }
            ),
            world_mode="sandbox",
        )

        self.assertEqual(presentation.buttons[1].text, "解除魯道夫象徵變身")
        self.assertIn("魯道夫象徵目前為手動變身形態", presentation.status_text)

    def test_active_transition_uses_fast_polling_and_target_form(self):
        start = build_transformation_control_presentation(
            _states(
                **{
                    "Tokai Teio": {
                        "target_form": "transformed",
                        "active": True,
                    }
                }
            ),
            world_mode="sandbox",
        )
        end = build_transformation_control_presentation(
            _states(
                **{
                    "Tokai Teio": {
                        "current_form": "transformed",
                        "target_form": "base",
                        "active": True,
                    }
                }
            ),
            world_mode="sandbox",
        )

        self.assertEqual(start.buttons[0].text, "帝寶變身中")
        self.assertEqual(end.buttons[0].text, "帝寶解除變身中")
        self.assertEqual(start.poll_interval_ms, 100)
        self.assertTrue(start.has_active_operation)
        self.assertFalse(start.buttons[0].enabled)

    def test_queued_end_waits_for_safe_state(self):
        presentation = build_transformation_control_presentation(
            _states(
                **{
                    "Tokai Teio": {
                        "current_form": "transformed",
                        "manual_end_requested": True,
                    }
                }
            ),
            world_mode="sandbox",
        )

        self.assertEqual(
            presentation.buttons[0].text,
            "等待解除帝寶變身",
        )
        self.assertIn("排入等待", presentation.status_text)
        self.assertEqual(presentation.poll_interval_ms, 100)

    def test_non_sandbox_controls_are_disabled_and_do_not_poll(self):
        presentation = build_transformation_control_presentation(
            _states(),
            world_mode="golden_legend",
        )

        self.assertFalse(any(button.enabled for button in presentation.buttons))
        self.assertFalse(presentation.should_poll)
        self.assertEqual(presentation.poll_interval_ms, 0)

    def test_completion_text_matches_final_target_form(self):
        self.assertEqual(
            build_transformation_completion_text("Tokai Teio", "base"),
            "帝寶已解除變身，目前為普通形態。",
        )
        self.assertEqual(
            build_transformation_completion_text(
                "Symboli Rudolf",
                "transformed",
            ),
            "魯道夫象徵已完成變身，目前為變身形態。",
        )


if __name__ == "__main__":
    unittest.main()
