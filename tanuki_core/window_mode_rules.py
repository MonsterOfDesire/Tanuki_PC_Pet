def can_start_window_flight_gate(
    *,
    flight_mode,
    perched_window_hwnd,
    dragging,
    vertical_velocity,
    is_visible,
    state,
    care_mode,
    social_mode,
    is_recovering,
    is_under_care,
    now,
    flight_cooldown_end,
    has_window_tracker,
    can_fly_freely,
    current_purpose,
    current_action_tag,
):
    if (
        flight_mode != "none" or
        perched_window_hwnd or
        dragging or
        vertical_velocity != 0 or
        not is_visible or
        state != "move" or
        care_mode != "none" or
        social_mode != "none" or
        is_recovering or
        is_under_care or
        now < flight_cooldown_end or
        not has_window_tracker or
        not can_fly_freely
    ):
        return False
    _ = current_action_tag
    return current_purpose == "move"
