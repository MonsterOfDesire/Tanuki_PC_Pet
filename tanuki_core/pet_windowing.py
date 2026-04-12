import math
import random

from .runtime import app_now


class PetWindowingMixin:
    def get_window_perch_candidates(self):
        candidates = []
        for action_type in [
            "sit", "sit_talk", "sit_read",
            "side", "side_face", "side_face_hand", "side_face_stretch",
            "side_rub", "side_hug", "side_stretch", "side_play",
            "side_fan", "side_ready", "side_stand",
            "drink", "eat", "get",
            "stand", "observe", "rest", "lie", "squat",
            "hear", "photo", "photo_ready", "dance_uma", "dance_three",
        ]:
            if self.asset_manager.has_action("idle", action_type):
                candidates.append(("idle", action_type))
        return self.expand_candidates_with_context("idle", candidates or self.get_idle_candidates(), context="random")

    def get_window_walk_candidates(self):
        candidates = []
        for action_type in ["walk", "jog", "sneak"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        if candidates:
            return candidates
        for action_type in self.asset_manager.get_action_keys("move"):
            if action_type in {"fly_up"}:
                continue
            if action_type not in {"walk", "jog", "sneak"}:
                candidates.append(("move", action_type))
        return candidates

    def can_fly_freely(self):
        return self.name not in self.AUTONOMOUS_FLY_DISABLED_NAMES and bool(self.get_free_fly_candidates())

    def has_free_fly_animation(self):
        return self.can_fly_freely()

    def get_free_fly_candidates(self):
        candidates = []
        for action_type in ["fly_up", "fly"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        return candidates

    def move_flight_toward(self, target_x, target_y, speed=None):
        if speed is None:
            speed = max(2.8, self.get_base_speed() + 1.2)
        dx = float(target_x - self.x())
        dy = float(target_y - self.y())
        dist = math.hypot(dx, dy)
        if dist <= max(10.0, speed * 1.4):
            self.move(int(round(target_x)), int(round(target_y)))
            return True

        travel = min(float(speed), dist)
        ratio = travel / dist if dist > 0 else 1.0
        next_x = self.x() + (dx * ratio)
        next_y = self.y() + (dy * ratio)
        if abs(dx) > 18:
            next_y += math.sin((app_now() * 6.0) + (self.frame_index * 0.35)) * 1.4

        surface = self.get_surface_snapshot()
        min_y = self.get_airborne_top_bound()
        next_x = surface.clamp_x(next_x)
        next_y = max(min_y, min(surface.bottom_bound, int(round(next_y))))
        self.move(next_x, next_y)
        return False

    def can_attach_to_window_surface(self):
        now = app_now()
        return (
            not self.dragging and
            self.care_mode == "none" and
            self.social_mode == "none" and
            not self.is_recovering and
            self.flight_mode == "none" and
            not self.is_under_care(now)
        )

    def detach_from_window_surface(self):
        self.perched_window_hwnd = 0
        self.window_perch_offset_x = 0
        self.window_perch_mode = "idle"
        self.window_perch_origin = "manual"
        self.window_perch_end_time = 0.0
        self.refresh_movement_state()

    def attach_to_window_surface(self, surface, origin="manual", preferred_center_x=None):
        if not surface or not self.can_attach_to_window_surface():
            return False
        if self.window_tracker and not self.window_tracker.can_pet_perch_on_surface(surface, self):
            return False
        if self.edge_mode != "none":
            self.stop_edge_mode(apply_cooldown=False)
        self.vy = 0
        self.perched_window_hwnd = surface.hwnd
        if preferred_center_x is None:
            preferred_center_x = self.geometry().center().x()
        target_x = surface.clamp_actor_x(preferred_center_x - (self.width() // 2), self.width())
        self.window_perch_offset_x = target_x - surface.rect.left()
        self.window_perch_mode = "idle"
        self.window_perch_origin = origin
        self.window_perch_end_time = app_now() + random.uniform(6.0, 12.0) if origin == "auto" else 0.0
        target_y = self.get_window_perch_y(surface)
        self.move(target_x, target_y)
        self.state = "idle"
        self.state_timer = random.randint(80, 160)
        self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def try_snap_to_window_surface(self):
        if not self.window_tracker:
            return False
        self.window_tracker.refresh()
        surface = self.window_tracker.find_drop_surface(self)
        if not surface:
            return False
        return self.attach_to_window_surface(
            surface,
            origin="manual",
            preferred_center_x=self.geometry().center().x(),
        )

    def get_window_perch_speed(self):
        return max(1, int(round(max(1.2, self.get_base_speed() * 0.8))))

    def update_window_perch(self, all_pets=None):
        if not self.perched_window_hwnd:
            return False
        if self.dragging or self.care_mode != "none" or self.social_mode != "none" or self.is_recovering:
            self.detach_from_window_surface()
            return False
        if not self.window_tracker:
            self.detach_from_window_surface()
            return False

        surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
        if not surface:
            self.detach_from_window_surface()
            return False
        if not self.window_tracker.can_pet_perch_on_surface(surface, self):
            target_center_x = self.x() + (self.width() // 2)
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=target_center_x - (self.width() // 2)):
                self.vy = 1.0
            return False

        if not self.is_adult and self.is_distressed():
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=self.x()):
                self.vy = 1.0
            return False

        if self.is_adult and all_pets and self.dashboard and self.dashboard.care_feature_enabled:
            radius = None if self.name == "Sirius Symboli" else 1000
            for pet in all_pets:
                if pet == self or pet.is_adult or not pet.isVisible():
                    continue
                if pet.care_partner not in (None, self):
                    continue
                if pet.is_recovering or not pet.is_distressed():
                    continue
                dist = self.distance_to(pet)
                if radius is not None and dist > radius:
                    continue
                self.detach_from_window_surface()
                if not self.start_taskbar_flight(target_x=pet.x()):
                    self.vy = 1.0
                return False

        if self.window_perch_origin == "auto" and self.window_perch_end_time and app_now() >= self.window_perch_end_time:
            target_center_x = surface.rect.center().x() - (self.width() // 2)
            self.detach_from_window_surface()
            if not self.start_taskbar_flight(target_x=target_center_x):
                self.vy = 1.0
            return False

        target_x = surface.clamp_actor_x(surface.rect.left() + self.window_perch_offset_x, self.width())
        target_y = self.get_window_perch_y(surface)
        self.vy = 0
        max_offset = max(0, surface.rect.width() - self.width())
        self.state_timer -= 1
        if self.state_timer <= 0:
            can_walk = bool(self.get_window_walk_candidates()) and max_offset >= 30
            if can_walk and random.random() < 0.62:
                self.window_perch_mode = "move"
                self.state = "move"
                self.state_timer = random.randint(55, 120)
                if self.window_perch_offset_x <= 5:
                    self.direction = 1
                elif self.window_perch_offset_x >= max(5, max_offset - 5):
                    self.direction = -1
                elif random.random() < 0.5:
                    self.direction *= -1
                self.change_state_candidates(
                    self.get_randomized_candidates(self.get_window_walk_candidates()),
                    context="random",
                )
            else:
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(70, 150)
                if random.random() < 0.35:
                    self.direction *= -1
                self.change_state_candidates(
                    self.get_randomized_candidates(self.get_window_perch_candidates()),
                    context="random",
                )

        if self.window_perch_mode == "move" and max_offset > 0:
            step = self.get_window_perch_speed()
            next_offset = self.window_perch_offset_x + (step * self.direction)
            if next_offset <= 0:
                next_offset = 0
                self.direction = 1
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(60, 120)
            elif next_offset >= max_offset:
                next_offset = max_offset
                self.direction = -1
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(60, 120)
            self.window_perch_offset_x = int(next_offset)
            target_x = surface.rect.left() + self.window_perch_offset_x
            if not self.ensure_candidate_animation(self.get_window_walk_candidates(), context="random"):
                self.window_perch_mode = "idle"
                self.state = "idle"
                self.state_timer = random.randint(70, 150)
                self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        else:
            self.window_perch_mode = "idle"
            self.state = "idle"
            self.ensure_candidate_animation(self.get_window_perch_candidates(), context="random")
        if self.x() != target_x or self.y() != target_y:
            self.move(target_x, target_y)
        self.refresh_movement_state()
        return True

    def can_start_window_flight(self, now=None):
        if now is None:
            now = app_now()
        if (
            self.flight_mode != "none" or
            self.perched_window_hwnd or
            self.edge_mode != "none" or
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.state != "move" or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering or
            self.is_under_care(now) or
            now < self.flight_cooldown_end or
            not self.window_tracker or
            not self.can_fly_freely()
        ):
            return False
        if self.current_purpose != "move" or self.current_action_tag not in {"fly", "fly_up"}:
            return False
        return self.window_tracker.find_flight_surface(self) is not None

    def start_window_flight(self, surface):
        if not surface:
            return False
        if not self.window_tracker:
            return False
        anchor_center_x = self.window_tracker.get_surface_visible_center_x(
            surface,
            actor_width=self.width(),
            preferred_center_x=self.geometry().center().x(),
        )
        if anchor_center_x is None:
            return False
        if self.perched_window_hwnd:
            self.detach_from_window_surface()
        if self.edge_mode != "none":
            self.stop_edge_mode(apply_cooldown=False)
        target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
        target_y = self.get_window_perch_y(surface)
        self.flight_mode = "to_window"
        self.flight_target_hwnd = surface.hwnd
        self.flight_target_x = target_x
        self.flight_target_y = target_y
        self.window_perch_offset_x = target_x - surface.rect.left()
        self.vy = 0
        self.state = "move"
        self.reset_stationary_move_mode()
        self.direction = 1 if target_x >= self.x() else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def stop_window_flight(self, apply_cooldown=True):
        was_active = self.flight_mode != "none"
        self.flight_mode = "none"
        self.flight_target_hwnd = 0
        self.flight_target_x = 0
        self.flight_target_y = 0
        if apply_cooldown and was_active:
            self.flight_cooldown_end = app_now() + random.uniform(18.0, 32.0)
        self.refresh_movement_state()

    def try_start_window_flight(self, now=None):
        if not self.window_tracker:
            return False
        if not self.can_start_window_flight(now=now):
            return False
        if random.random() >= 0.06:
            return False
        surface = self.window_tracker.find_flight_surface(self)
        if not surface:
            return False
        return self.start_window_flight(surface)

    def get_window_flight_speed(self):
        return max(2.6, self.get_base_speed() + 1.1)

    def start_taskbar_flight(self, target_x=None):
        if not self.can_fly_freely():
            return False
        surface = self.get_surface_snapshot()
        if target_x is None:
            target_x = self.x()
        self.flight_mode = "to_taskbar"
        self.flight_target_hwnd = 0
        self.flight_target_x = surface.clamp_x(target_x)
        self.flight_target_y = self.get_taskbar_walk_y()
        self.vy = 0
        self.state = "move"
        self.reset_stationary_move_mode()
        self.direction = 1 if self.flight_target_x >= self.x() else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def update_window_flight(self):
        if self.flight_mode == "none":
            return False
        if (
            self.dragging or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering
        ):
            self.stop_window_flight(apply_cooldown=False)
            return False
        if not self.window_tracker:
            self.stop_window_flight(apply_cooldown=False)
            return False

        if self.flight_mode == "to_taskbar":
            self.vy = 0
            self.state = "move"
            self.direction = 1 if self.flight_target_x >= self.x() else -1
            self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
            arrived = self.move_flight_toward(
                self.flight_target_x,
                self.flight_target_y,
                speed=max(2.8, self.get_window_flight_speed()),
            )
            if arrived:
                self.move(int(self.flight_target_x), int(self.flight_target_y))
                self.stop_window_flight(apply_cooldown=True)
                self.state = "idle"
                self.state_timer = random.randint(70, 140)
                self.change_state("idle", "stand")
            else:
                self.refresh_movement_state()
            return True

        surface = self.window_tracker.get_surface_by_hwnd(self.flight_target_hwnd)
        if not surface:
            self.stop_window_flight(apply_cooldown=False)
            return False
        if not self.window_tracker.can_pet_perch_on_surface(surface, self):
            self.stop_window_flight(apply_cooldown=False)
            return False

        preferred_center_x = surface.rect.left() + self.window_perch_offset_x + (self.width() // 2)
        anchor_center_x = self.window_tracker.get_surface_visible_center_x(
            surface,
            actor_width=self.width(),
            preferred_center_x=preferred_center_x,
        )
        if anchor_center_x is None:
            self.stop_window_flight(apply_cooldown=False)
            return False

        self.flight_target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
        self.flight_target_y = self.get_window_perch_y(surface)
        dx = self.flight_target_x - self.x()
        dy = self.flight_target_y - self.y()
        if math.hypot(dx, dy) <= 14:
            self.stop_window_flight(apply_cooldown=True)
            return self.attach_to_window_surface(
                surface,
                origin="auto",
                preferred_center_x=anchor_center_x,
            )

        self.vy = 0
        self.state = "move"
        self.direction = 1 if dx >= 0 else -1
        self.ensure_candidate_animation(self.get_free_fly_candidates(), context="random")
        arrived = self.move_flight_toward(
            self.flight_target_x,
            self.flight_target_y,
            speed=self.get_window_flight_speed(),
        )
        if arrived:
            self.stop_window_flight(apply_cooldown=True)
            return self.attach_to_window_surface(
                surface,
                origin="auto",
                preferred_center_x=anchor_center_x,
            )
        self.refresh_movement_state()
        return True

    def has_vertical_edge_animation(self):
        return self.EDGE_INTERACTION_ENABLED and self.can_fly_freely()

    def get_edge_move_candidates(self):
        candidates = []
        for action_type in ["fly_up", "fly"]:
            if self.asset_manager.has_action("move", action_type):
                candidates.append(("move", action_type))
        return candidates

    def can_play_edge_move_animation(self):
        for purpose, action_type in self.get_edge_move_candidates():
            result = self.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                self.mood_score,
                is_adult=self.is_adult,
                context="random",
            )
            if result:
                return True
        return False

    def get_edge_idle_candidates(self):
        candidates = []
        for action_type in ["side", "stand", "observe", "rest", "sit"]:
            if self.asset_manager.has_action("idle", action_type):
                candidates.append(("idle", action_type))
        return candidates or self.get_idle_candidates()

    def get_edge_vertical_speed(self, descending=False):
        base_speed = max(2.0, self.get_base_speed() + 0.3)
        if descending:
            base_speed += 0.4
        return max(1, int(round(base_speed)))

    def can_start_edge_mode(self, now=None):
        if not self.EDGE_INTERACTION_ENABLED:
            return False, "none"
        if now is None:
            now = app_now()
        if (
            self.edge_mode != "none" or
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.state != "move" or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering or
            self.is_under_care(now) or
            now < self.edge_cooldown_end
        ):
            return False, "none"
        if not self.has_vertical_edge_animation() or not self.can_play_edge_move_animation():
            return False, "none"
        side = self.get_edge_attach_target()
        return side != None, side or "none"

    def start_edge_mode(self, side, now=None):
        if now is None:
            now = app_now()
        if side not in {"left", "right"}:
            return False
        surface = self.get_surface_snapshot()
        available_height = surface.floor_top_y - surface.top_bound
        if available_height < 120:
            return False
        max_climb = max(80, min(available_height - 40, 360))
        min_climb = min(140, max_climb)
        climb_distance = random.randint(min_climb, max_climb)
        self.edge_mode = "climb_up"
        self.edge_side = side
        self.edge_target_y = max(surface.top_bound, surface.floor_top_y - climb_distance)
        self.edge_return_x = 0
        self.edge_pause_until = 0.0
        self.reset_stationary_move_mode()
        self.state = "move"
        self.direction = -1 if side == "left" else 1
        self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
        self.refresh_movement_state()
        return True

    def stop_edge_mode(self, apply_cooldown=True):
        previous_side = self.edge_side
        was_active = self.edge_mode != "none"
        self.edge_mode = "none"
        self.edge_side = "none"
        self.edge_target_y = 0
        self.edge_return_x = 0
        self.edge_pause_until = 0.0
        if apply_cooldown and was_active:
            self.edge_cooldown_end = app_now() + random.uniform(8.0, 14.0)
        if previous_side == "left":
            self.direction = 1
        elif previous_side == "right":
            self.direction = -1
        self.state = "idle"
        self.state_timer = random.randint(60, 120)
        self.change_state("idle", "stand")
        self.refresh_movement_state()

    def try_start_edge_mode(self, now=None):
        can_start, side = self.can_start_edge_mode(now=now)
        if not can_start:
            return False
        chance = 0.24
        if random.random() >= chance:
            return False
        return self.start_edge_mode(side, now=now)

    def update_edge_behavior(self, now):
        if not self.EDGE_INTERACTION_ENABLED:
            if self.edge_mode != "none":
                self.stop_edge_mode(apply_cooldown=False)
            return False
        if self.edge_mode == "none":
            return False
        if (
            self.dragging or
            self.vy != 0 or
            self.care_mode != "none" or
            self.social_mode != "none" or
            self.is_recovering
        ):
            self.stop_edge_mode(apply_cooldown=False)
            return False

        surface = self.get_surface_snapshot()
        edge_x = surface.left_bound if self.edge_side == "left" else surface.right_bound
        self.direction = -1 if self.edge_side == "left" else 1

        if self.edge_mode == "climb_up":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            step = self.get_edge_vertical_speed(descending=False)
            next_y = max(self.edge_target_y, self.y() - step)
            self.move(edge_x, next_y)
            if next_y <= self.edge_target_y:
                self.edge_mode = "perch"
                self.edge_pause_until = now + random.uniform(0.8, 1.6)
            self.refresh_movement_state()
            return True

        if self.edge_mode == "perch":
            self.state = "idle"
            self.ensure_candidate_animation(self.get_edge_idle_candidates(), context="random")
            self.move(edge_x, self.y())
            if now >= self.edge_pause_until:
                inward = random.randint(90, 220)
                self.edge_return_x = surface.clamp_x(edge_x + inward if self.edge_side == "left" else edge_x - inward)
                self.edge_target_y = self.get_taskbar_walk_y()
                self.edge_mode = "return_taskbar"
            self.refresh_movement_state()
            return True

        if self.edge_mode == "climb_down":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            step = self.get_edge_vertical_speed(descending=True)
            next_y = min(surface.floor_top_y, self.y() + step)
            self.move(edge_x, next_y)
            if next_y >= surface.floor_top_y:
                self.move(edge_x, surface.floor_top_y)
                self.stop_edge_mode(apply_cooldown=True)
            else:
                self.refresh_movement_state()
            return True

        if self.edge_mode == "return_taskbar":
            self.state = "move"
            self.ensure_candidate_animation(self.get_edge_move_candidates(), context="random")
            self.direction = 1 if self.edge_return_x >= self.x() else -1
            arrived = self.move_flight_toward(
                self.edge_return_x,
                self.edge_target_y,
                speed=max(2.8, self.get_window_flight_speed()),
            )
            if arrived:
                self.move(self.edge_return_x, self.edge_target_y)
                self.stop_edge_mode(apply_cooldown=True)
            else:
                self.refresh_movement_state()
            return True

        self.stop_edge_mode(apply_cooldown=False)
        return False
