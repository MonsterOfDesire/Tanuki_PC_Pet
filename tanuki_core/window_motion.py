import math


def get_window_perch_speed(base_speed):
    return max(1, int(round(max(1.2, float(base_speed) * 0.8))))


def get_window_flight_speed(base_speed):
    return max(2.6, float(base_speed) + 1.1)


def compute_flight_step(
    current_x,
    current_y,
    target_x,
    target_y,
    speed,
    time_value,
    frame_index,
    left_bound,
    right_bound,
    bottom_bound,
    min_y,
):
    dx = float(target_x - current_x)
    dy = float(target_y - current_y)
    dist = math.hypot(dx, dy)
    arrival_threshold = max(10.0, float(speed) * 1.4)
    if dist <= arrival_threshold:
        return int(round(target_x)), int(round(target_y)), True

    travel = min(float(speed), dist)
    ratio = travel / dist if dist > 0 else 1.0
    next_x = current_x + (dx * ratio)
    next_y = current_y + (dy * ratio)
    if abs(dx) > 18:
        next_y += math.sin((float(time_value) * 6.0) + (int(frame_index) * 0.35)) * 1.4

    next_x = max(int(left_bound), min(int(right_bound), int(round(next_x))))
    next_y = max(int(min_y), min(int(bottom_bound), int(round(next_y))))
    return next_x, next_y, False


def compute_perch_collision_x(current_x, delta_x, left_bound, right_bound):
    return max(int(left_bound), min(int(right_bound), int(round(current_x + delta_x))))
