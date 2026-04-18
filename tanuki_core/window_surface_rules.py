def is_surface_perch_allowed(surface_rect, screen_rect):
    if screen_rect is None:
        return True
    nearly_full_width = surface_rect.width() >= int(screen_rect.width() * 0.97)
    nearly_full_height = surface_rect.height() >= int(screen_rect.height() * 0.94)
    near_top = surface_rect.top() <= (screen_rect.top() + 10)
    covers_screen = (
        surface_rect.left() <= (screen_rect.left() + 12) and
        surface_rect.right() >= (screen_rect.right() - 12) and
        surface_rect.bottom() >= (screen_rect.bottom() - 12)
    )
    return not ((near_top and nearly_full_width and nearly_full_height) or covers_screen)


def can_actor_perch_on_surface(surface, screen_rect, actor_height):
    if not is_surface_perch_allowed(surface.rect, screen_rect):
        return False
    if screen_rect is None:
        return True
    min_perch_y = screen_rect.top() - int(actor_height * 0.65)
    return surface.perch_y(actor_height) >= min_perch_y


def build_surface_center_candidates(surface_rect, actor_width=0, preferred_center_x=None, exact=False, top_edge_inset=18):
    half_width = actor_width // 2 if actor_width else 0
    min_center = surface_rect.left() + max(top_edge_inset, half_width)
    max_center = surface_rect.right() - max(top_edge_inset, actor_width - half_width)
    if max_center < min_center:
        return []

    candidates = []
    if preferred_center_x is not None:
        preferred_center_x = max(min_center, min(max_center, int(preferred_center_x)))
        candidates.append(preferred_center_x)

    if not exact:
        center_x = surface_rect.center().x()
        left_mid = surface_rect.left() + int(surface_rect.width() * 0.35)
        right_mid = surface_rect.left() + int(surface_rect.width() * 0.65)
        for probe_x in [center_x, left_mid, right_mid]:
            candidates.append(max(min_center, min(max_center, int(probe_x))))

    unique_candidates = []
    seen = set()
    for probe_x in candidates:
        if probe_x in seen:
            continue
        seen.add(probe_x)
        unique_candidates.append(probe_x)
    return unique_candidates


def is_surface_top_segment_visible(
    surface,
    center_x,
    screen_rect,
    get_top_surface_at_point,
    actor_width=0,
    top_edge_inset=18,
    top_edge_y_offsets=(8, 18, 28),
):
    if not surface.contains_x(center_x):
        return False
    if screen_rect is None:
        return False

    span = max(14, int(actor_width * 0.22)) if actor_width else 0
    probe_xs = [int(center_x)]
    if span:
        probe_xs.extend([int(center_x - span), int(center_x + span)])

    for probe_x in probe_xs:
        if probe_x < (surface.rect.left() + top_edge_inset):
            return False
        if probe_x > (surface.rect.right() - top_edge_inset):
            return False
        point_visible = False
        for y_offset in top_edge_y_offsets:
            probe_y = min(surface.rect.bottom() - 6, surface.rect.top() + y_offset)
            if not rect_contains_point(screen_rect, probe_x, probe_y):
                continue
            top_surface = get_top_surface_at_point(probe_x, probe_y)
            if top_surface and top_surface.hwnd == surface.hwnd:
                point_visible = True
                break
        if not point_visible:
            return False
    return True


def get_surface_visible_center_x(
    surface,
    surface_allowed,
    is_top_segment_visible,
    actor_width=0,
    preferred_center_x=None,
    exact=False,
    top_edge_inset=18,
):
    if not surface_allowed:
        return None

    candidates = build_surface_center_candidates(
        surface.rect,
        actor_width=actor_width,
        preferred_center_x=preferred_center_x,
        exact=exact,
        top_edge_inset=top_edge_inset,
    )
    for probe_x in candidates:
        if is_top_segment_visible(surface, probe_x, actor_width=actor_width):
            return probe_x
    return None


def rect_contains_point(rect, x, y):
    return rect.left() <= int(x) <= rect.right() and rect.top() <= int(y) <= rect.bottom()
