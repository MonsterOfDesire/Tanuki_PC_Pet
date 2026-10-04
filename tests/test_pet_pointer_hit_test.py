import unittest

from tanuki_core.pet_pointer_hit_test import visible_frame_pixel_hit


class FakeColor:
    def __init__(self, alpha):
        self._alpha = int(alpha)

    def alpha(self):
        return self._alpha


class FakeImage:
    def __init__(self, alpha_rows):
        self.alpha_rows = alpha_rows

    def pixelColor(self, x, y):
        return FakeColor(self.alpha_rows[y][x])


class FakeFrame:
    def __init__(self, alpha_rows):
        self.alpha_rows = alpha_rows

    def isNull(self):
        return False

    def width(self):
        return len(self.alpha_rows[0])

    def height(self):
        return len(self.alpha_rows)

    def toImage(self):
        return FakeImage(self.alpha_rows)


class PetPointerHitTestTests(unittest.TestCase):
    def setUp(self):
        self.frame = FakeFrame(
            [
                [0, 0, 0, 0],
                [0, 0, 255, 0],
                [0, 0, 0, 0],
            ]
        )

    def hit(self, x, y, *, flipped=False, tolerance=0):
        return visible_frame_pixel_hit(
            self.frame,
            widget_width=10,
            widget_height=8,
            local_x=x,
            local_y=y,
            flipped=flipped,
            edge_tolerance_px=tolerance,
        )

    def test_transparent_widget_padding_does_not_hit(self):
        self.assertFalse(self.hit(0, 0))

    def test_opaque_pixel_hits_at_bottom_centered_draw_position(self):
        self.assertTrue(self.hit(5, 6))

    def test_horizontal_flip_maps_to_visible_source_pixel(self):
        self.assertTrue(self.hit(4, 6, flipped=True))
        self.assertFalse(self.hit(5, 6, flipped=True))

    def test_small_edge_tolerance_keeps_narrow_parts_clickable(self):
        self.assertTrue(self.hit(5, 5, tolerance=1))


if __name__ == "__main__":
    unittest.main()
