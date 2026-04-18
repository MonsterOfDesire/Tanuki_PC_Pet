import random

from .runtime import app_now
from .window_motion import compute_perch_collision_x


class WindowingEffects:
    def detach_from_window_surface(self, pet):
        pet.perched_window_hwnd = 0
        pet.window_perch_offset_x = 0
        pet.window_perch_mode = "idle"
        pet.window_perch_origin = "manual"
        pet.window_perch_end_time = 0.0
        pet.refresh_movement_state()

    def attach_to_window_surface(self, pet, surface, origin="manual", preferred_center_x=None, now=None, rng=None):
        now = app_now() if now is None else now
        rng = rng or random
        if not surface or not pet.can_attach_to_window_surface():
            return False
        actor_snapshot = pet.window_tracker.build_actor_snapshot(pet) if pet.window_tracker else None
        if pet.window_tracker and not pet.window_tracker.can_actor_perch_on_surface(surface, actor_snapshot):
            return False
        pet.vy = 0
        pet.perched_window_hwnd = surface.hwnd
        if preferred_center_x is None:
            preferred_center_x = pet.geometry().center().x()
        target_x = surface.clamp_actor_x(preferred_center_x - (pet.width() // 2), pet.width())
        pet.window_perch_offset_x = target_x - surface.rect.left()
        pet.window_perch_mode = "idle"
        pet.window_perch_origin = origin
        pet.window_perch_end_time = now + rng.uniform(6.0, 12.0) if origin == "auto" else 0.0
        target_y = pet.get_window_perch_y(surface)
        pet.move(target_x, target_y)
        pet.state = "idle"
        pet.state_timer = rng.randint(80, 160)
        pet.ensure_candidate_animation(pet.get_window_perch_candidates(), context="random")
        pet.refresh_movement_state()
        return True

    def apply_window_perch_collision(self, pet, delta_x):
        if not pet.perched_window_hwnd or not pet.window_tracker:
            return False
        surface = pet.window_tracker.get_surface_by_hwnd(pet.perched_window_hwnd)
        if not surface:
            return False
        right_bound = surface.rect.left() + surface.rect.width() - pet.width()
        next_x = compute_perch_collision_x(
            current_x=pet.x(),
            delta_x=delta_x,
            left_bound=surface.rect.left(),
            right_bound=right_bound,
        )
        if next_x == pet.x():
            return True
        pet.window_perch_offset_x = next_x - surface.rect.left()
        pet.move(next_x, pet.get_window_perch_y(surface))
        pet.refresh_movement_state()
        return True

    def apply_perch_detach(self, pet):
        self.detach_from_window_surface(pet)
        return False

    def apply_perch_detach_to_taskbar(self, pet, target_x, now=None, rng=None):
        self.detach_from_window_surface(pet)
        if not self.start_taskbar_flight(pet, target_x=target_x, now=now, rng=rng):
            pet.vy = 1.0
        return False

    def start_window_flight(self, pet, surface, now=None, rng=None):
        now = app_now() if now is None else now
        rng = rng or random
        if not surface or not pet.window_tracker:
            return False
        anchor_center_x = pet.window_tracker.get_surface_visible_center_x(
            surface,
            actor_width=pet.width(),
            preferred_center_x=pet.geometry().center().x(),
        )
        if anchor_center_x is None:
            return False
        if pet.perched_window_hwnd:
            self.detach_from_window_surface(pet)
        target_x = surface.clamp_actor_x(anchor_center_x - (pet.width() // 2), pet.width())
        target_y = pet.get_window_perch_y(surface)
        pet.flight_mode = "to_window"
        pet.flight_target_hwnd = surface.hwnd
        pet.flight_target_x = target_x
        pet.flight_target_y = target_y
        pet.window_perch_offset_x = target_x - surface.rect.left()
        pet.vy = 0
        pet.state = "move"
        pet.reset_stationary_move_mode()
        pet.direction = 1 if target_x >= pet.x() else -1
        pet.ensure_candidate_animation(pet.get_free_fly_candidates(), context="random")
        pet.refresh_movement_state()
        return True

    def stop_window_flight(self, pet, apply_cooldown=True, now=None, rng=None):
        now = app_now() if now is None else now
        rng = rng or random
        was_active = pet.flight_mode != "none"
        pet.flight_mode = "none"
        pet.flight_target_hwnd = 0
        pet.flight_target_x = 0
        pet.flight_target_y = 0
        if apply_cooldown and was_active:
            pet.flight_cooldown_end = now + rng.uniform(18.0, 32.0)
        pet.refresh_movement_state()

    def start_taskbar_flight(self, pet, target_x=None, now=None, rng=None):
        _ = app_now() if now is None else now
        _ = rng or random
        if not pet.can_fly_freely():
            return False
        surface = pet.get_surface_snapshot()
        if target_x is None:
            target_x = pet.x()
        pet.flight_mode = "to_taskbar"
        pet.flight_target_hwnd = 0
        pet.flight_target_x = surface.clamp_x(target_x)
        pet.flight_target_y = pet.get_taskbar_walk_y()
        pet.vy = 0
        pet.state = "move"
        pet.reset_stationary_move_mode()
        pet.direction = 1 if pet.flight_target_x >= pet.x() else -1
        pet.ensure_candidate_animation(pet.get_free_fly_candidates(), context="random")
        pet.refresh_movement_state()
        return True

    def apply_window_flight_stop(self, pet, now=None, rng=None):
        self.stop_window_flight(pet, apply_cooldown=False, now=now, rng=rng)
        return False

    def apply_window_flight_taskbar_tick(self, pet, now=None, rng=None):
        rng = rng or random
        pet.vy = 0
        pet.state = "move"
        pet.direction = 1 if pet.flight_target_x >= pet.x() else -1
        pet.ensure_candidate_animation(pet.get_free_fly_candidates(), context="random")
        arrived = pet.move_flight_toward(
            pet.flight_target_x,
            pet.flight_target_y,
            speed=max(2.8, pet.get_window_flight_speed()),
        )
        if arrived:
            pet.move(int(pet.flight_target_x), int(pet.flight_target_y))
            self.stop_window_flight(pet, apply_cooldown=True, now=now, rng=rng)
            pet.state = "idle"
            pet.state_timer = rng.randint(70, 140)
            pet.change_state("idle", "stand")
        else:
            pet.refresh_movement_state()
        return True

    def apply_window_flight_attach(self, pet, surface, anchor_center_x, now=None, rng=None):
        self.stop_window_flight(pet, apply_cooldown=True, now=now, rng=rng)
        return self.attach_to_window_surface(
            pet,
            surface,
            origin="auto",
            preferred_center_x=anchor_center_x,
            now=now,
            rng=rng,
        )

    def apply_window_flight_window_tick(self, pet, surface, anchor_center_x, now=None, rng=None):
        self_state_dx = pet.flight_target_x - pet.x()
        pet.vy = 0
        pet.state = "move"
        pet.direction = 1 if self_state_dx >= 0 else -1
        pet.ensure_candidate_animation(pet.get_free_fly_candidates(), context="random")
        arrived = pet.move_flight_toward(
            pet.flight_target_x,
            pet.flight_target_y,
            speed=pet.get_window_flight_speed(),
        )
        if arrived:
            self.stop_window_flight(pet, apply_cooldown=True, now=now, rng=rng)
            return self.attach_to_window_surface(
                pet,
                surface,
                origin="auto",
                preferred_center_x=anchor_center_x,
                now=now,
                rng=rng,
            )
        pet.refresh_movement_state()
        return True

WINDOWING_EFFECTS = WindowingEffects()
