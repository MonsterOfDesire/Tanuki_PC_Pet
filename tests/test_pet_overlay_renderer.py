import unittest

from tanuki_core.pet_overlay_renderer import compute_debug_overlay_layout, compute_star_draw_specs


class PetOverlayRendererTests(unittest.TestCase):
    def test_compute_star_draw_specs_returns_three_centered_specs(self):
        specs = compute_star_draw_specs(
            widget_width=200,
            draw_y=150,
            overlay_scale=1.5,
            star_y_offset=4,
            star_anim_counter=0,
        )

        self.assertEqual(len(specs), 3)
        self.assertEqual(specs[0].size, 37)
        self.assertEqual(specs[1].x - specs[0].x, 45)
        for spec in specs:
            self.assertTrue(101 <= spec.y <= 107)

    def test_compute_debug_overlay_layout_respects_max_width(self):
        layout = compute_debug_overlay_layout(
            line_widths=(60, 180, 210),
            line_height=14,
            max_debug_width=160,
            widget_width=220,
        )

        self.assertEqual(layout.box_x, 30)
        self.assertEqual(layout.box_width, 160)
        self.assertEqual(layout.box_height, 52)


if __name__ == "__main__":
    unittest.main()
