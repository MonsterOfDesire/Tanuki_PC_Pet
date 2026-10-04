from __future__ import annotations


DEFAULT_ALPHA_THRESHOLD = 12
DEFAULT_EDGE_TOLERANCE_PX = 3


def visible_frame_pixel_hit(
    frame,
    *,
    widget_width,
    widget_height,
    local_x,
    local_y,
    flipped=False,
    alpha_threshold=DEFAULT_ALPHA_THRESHOLD,
    edge_tolerance_px=DEFAULT_EDGE_TOLERANCE_PX,
):
    if frame is None:
        return False
    is_null = getattr(frame, "isNull", None)
    if callable(is_null) and is_null():
        return False

    frame_width = int(frame.width())
    frame_height = int(frame.height())
    if frame_width <= 0 or frame_height <= 0:
        return False

    draw_x = (int(widget_width) - frame_width) // 2
    draw_y = int(widget_height) - frame_height
    frame_x = int(local_x) - draw_x
    frame_y = int(local_y) - draw_y
    tolerance = max(0, int(edge_tolerance_px))
    if (
        frame_x < -tolerance
        or frame_y < -tolerance
        or frame_x >= frame_width + tolerance
        or frame_y >= frame_height + tolerance
    ):
        return False

    source_x = frame_width - 1 - frame_x if flipped else frame_x
    source_y = frame_y
    image = frame.toImage()
    threshold = max(0, min(255, int(alpha_threshold)))
    for y in range(
        max(0, source_y - tolerance),
        min(frame_height, source_y + tolerance + 1),
    ):
        for x in range(
            max(0, source_x - tolerance),
            min(frame_width, source_x + tolerance + 1),
        ):
            if int(image.pixelColor(x, y).alpha()) >= threshold:
                return True
    return False
