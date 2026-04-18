import math
import random

from .pet_social_rules import CareTargetCandidate, choose_care_target
from .runtime import app_now
from .window_mode_rules import (
    can_start_window_flight_gate,
)
from .window_motion import (
    compute_flight_step,
    compute_perch_collision_x,
    get_window_flight_speed as calc_window_flight_speed,
    get_window_perch_speed as calc_window_perch_speed,
)
from .window_perch_rules import (
    advance_window_perch_walk,
    decide_window_perch_mode,
)
from .pet_windowing_effects import WINDOWING_EFFECTS
from .windowing_coordinator import (
    WINDOWING_COORDINATOR,
    WINDOW_FLIGHT_DECISION_ATTACH,
    WINDOW_FLIGHT_DECISION_NONE,
    WINDOW_FLIGHT_DECISION_STOP,
    WINDOW_FLIGHT_DECISION_TASKBAR_TICK,
    WINDOW_FLIGHT_DECISION_WINDOW_TICK,
    WINDOW_PERCH_DECISION_NONE,
    WINDOW_PERCH_DECISION_CONTINUE,
    WINDOW_PERCH_DECISION_DETACH,
    WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
    WindowFlightContext,
    WindowPerchContext,
)


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
        surface = self.get_surface_snapshot()
        next_x, next_y, arrived = compute_flight_step(
            current_x=self.x(),
            current_y=self.y(),
            target_x=target_x,
            target_y=target_y,
            speed=speed,
            time_value=app_now(),
            frame_index=self.frame_index,
            left_bound=surface.left_bound,
            right_bound=surface.right_bound,
            bottom_bound=surface.bottom_bound,
            min_y=self.get_airborne_top_bound(),
        )
        self.move(next_x, next_y)
        if arrived:
            return True
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
        return WINDOWING_EFFECTS.detach_from_window_surface(self)

    def attach_to_window_surface(self, surface, origin="manual", preferred_center_x=None):
        return WINDOWING_EFFECTS.attach_to_window_surface(
            self,
            surface,
            origin=origin,
            preferred_center_x=preferred_center_x,
        )

    def try_snap_to_window_surface(self):
        if not self.window_tracker:
            return False
        self.window_tracker.refresh()
        surface = self.window_tracker.find_drop_surface_for_actor(
            self.window_tracker.build_actor_snapshot(self)
        )
        if not surface:
            return False
        return self.attach_to_window_surface(
            surface,
            origin="manual",
            preferred_center_x=self.geometry().center().x(),
        )

    def get_window_perch_speed(self):
        return calc_window_perch_speed(self.get_base_speed())

    def apply_window_perch_collision(self, delta_x):
        return WINDOWING_EFFECTS.apply_window_perch_collision(self, delta_x)

    def update_window_perch(self, all_pets=None):
        surface = None
        can_perch_on_surface = False
        if self.perched_window_hwnd and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
            if surface:
                actor_snapshot = self.window_tracker.build_actor_snapshot(self)
                can_perch_on_surface = self.window_tracker.can_actor_perch_on_surface(
                    surface,
                    actor_snapshot,
                ) and self.window_tracker.is_actor_perch_position_visible(
                    surface,
                    actor_snapshot,
                    preferred_center_x=self.geometry().center().x(),
                )

        distressed_target_x = None
        adult_should_leave_for_care = False
        if self.perched_window_hwnd and can_perch_on_surface and self.is_adult and all_pets and self.is_care_feature_enabled():
            care_target = choose_care_target(
                self,
                self.name,
                [
                    CareTargetCandidate(
                        pet=pet,
                        is_self=(pet == self),
                        is_adult=pet.is_adult,
                        is_visible=pet.isVisible(),
                        care_partner=pet.care_partner,
                        is_recovering=pet.is_recovering,
                        is_distressed=pet.is_distressed(),
                        distance=self.distance_to(pet),
                    )
                    for pet in all_pets
                ],
            )
            if care_target is not None:
                adult_should_leave_for_care = True
                distressed_target_x = care_target.x()

        perch_decision = WINDOWING_COORDINATOR.decide_window_perch(WindowPerchContext(
            is_perched=bool(self.perched_window_hwnd),
            dragging=self.dragging,
            care_mode=self.care_mode,
            social_mode=self.social_mode,
            is_recovering=self.is_recovering,
            has_window_tracker=bool(self.window_tracker),
            has_surface=surface is not None,
            can_perch_on_surface=can_perch_on_surface,
            is_child_distressed=(not self.is_adult and self.is_distressed()),
            adult_should_leave_for_care=adult_should_leave_for_care,
            auto_perch_expired=bool(
                surface and
                self.window_perch_origin == "auto" and
                self.window_perch_end_time and
                app_now() >= self.window_perch_end_time
            ),
            current_x=self.x(),
            fallback_target_x=(
                distressed_target_x if distressed_target_x is not None else
                (surface.rect.center().x() - (self.width() // 2) if surface else None)
            ),
        ))
        if perch_decision.action == WINDOW_PERCH_DECISION_NONE:
            return False
        if perch_decision.action == WINDOW_PERCH_DECISION_DETACH:
            return WINDOWING_EFFECTS.apply_perch_detach(self)
        if perch_decision.action == WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR:
            return WINDOWING_EFFECTS.apply_perch_detach_to_taskbar(self, perch_decision.target_x)
        if perch_decision.action != WINDOW_PERCH_DECISION_CONTINUE:
            return False

        target_x = surface.clamp_actor_x(surface.rect.left() + self.window_perch_offset_x, self.width())
        target_y = self.get_window_perch_y(surface)
        self.vy = 0
        max_offset = max(0, surface.rect.width() - self.width())
        self.state_timer -= 1
        if self.state_timer <= 0:
            walk_candidates = self.get_window_walk_candidates()
            mode_decision = decide_window_perch_mode(
                max_offset=max_offset,
                offset_x=self.window_perch_offset_x,
                direction=self.direction,
                has_walk_candidates=bool(walk_candidates),
                move_roll=random.random(),
                flip_roll=random.random(),
                move_timer=random.randint(55, 120),
                idle_timer=random.randint(70, 150),
            )
            self.window_perch_mode = mode_decision.mode
            self.state = mode_decision.state
            self.state_timer = mode_decision.state_timer
            self.direction = mode_decision.direction
            if mode_decision.use_walk_animation:
                self.change_state_candidates(
                    self.get_randomized_candidates(walk_candidates),
                    context="random",
                )
            else:
                self.change_state_candidates(
                    self.get_randomized_candidates(self.get_window_perch_candidates()),
                    context="random",
                )

        if self.window_perch_mode == "move" and max_offset > 0:
            step = self.get_window_perch_speed()
            walk_decision = advance_window_perch_walk(
                offset_x=self.window_perch_offset_x,
                direction=self.direction,
                step=step,
                max_offset=max_offset,
                boundary_idle_timer=random.randint(60, 120),
            )
            self.window_perch_offset_x = walk_decision.next_offset
            self.direction = walk_decision.direction
            self.window_perch_mode = walk_decision.mode
            self.state = walk_decision.state
            if walk_decision.state_timer is not None:
                self.state_timer = walk_decision.state_timer
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
        if not can_start_window_flight_gate(
            flight_mode=self.flight_mode,
            perched_window_hwnd=self.perched_window_hwnd,
            dragging=self.dragging,
            vertical_velocity=self.vy,
            is_visible=self.isVisible(),
            state=self.state,
            care_mode=self.care_mode,
            social_mode=self.social_mode,
            is_recovering=self.is_recovering,
            is_under_care=self.is_under_care(now),
            now=now,
            flight_cooldown_end=self.flight_cooldown_end,
            has_window_tracker=bool(self.window_tracker),
            can_fly_freely=self.can_fly_freely(),
            current_purpose=self.current_purpose,
            current_action_tag=self.current_action_tag,
        ):
            return False
        return self.window_tracker.find_flight_surface_for_actor(
            self.window_tracker.build_actor_snapshot(self)
        ) is not None

    def start_window_flight(self, surface):
        return WINDOWING_EFFECTS.start_window_flight(self, surface)

    def stop_window_flight(self, apply_cooldown=True):
        return WINDOWING_EFFECTS.stop_window_flight(self, apply_cooldown=apply_cooldown)

    def try_start_window_flight(self, now=None):
        if not self.window_tracker:
            return False
        if not self.can_start_window_flight(now=now):
            return False
        if random.random() >= 0.06:
            return False
        surface = self.window_tracker.find_flight_surface_for_actor(
            self.window_tracker.build_actor_snapshot(self)
        )
        if not surface:
            return False
        return self.start_window_flight(surface)

    def get_window_flight_speed(self):
        return calc_window_flight_speed(self.get_base_speed())

    def start_taskbar_flight(self, target_x=None):
        return WINDOWING_EFFECTS.start_taskbar_flight(self, target_x=target_x)

    def update_window_flight(self):
        surface = None
        can_perch_on_surface = False
        anchor_center_x = None
        distance_to_target = None

        if self.flight_mode != "none" and self.window_tracker and self.flight_mode != "to_taskbar":
            surface = self.window_tracker.get_surface_by_hwnd(self.flight_target_hwnd)
            if surface:
                can_perch_on_surface = self.window_tracker.can_actor_perch_on_surface(
                    surface,
                    self.window_tracker.build_actor_snapshot(self),
                )
                if can_perch_on_surface:
                    preferred_center_x = surface.rect.left() + self.window_perch_offset_x + (self.width() // 2)
                    anchor_center_x = self.window_tracker.get_surface_visible_center_x(
                        surface,
                        actor_width=self.width(),
                        preferred_center_x=preferred_center_x,
                    )
                    if anchor_center_x is not None:
                        self.flight_target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
                        self.flight_target_y = self.get_window_perch_y(surface)
                        dx = self.flight_target_x - self.x()
                        dy = self.flight_target_y - self.y()
                        distance_to_target = math.hypot(dx, dy)

        flight_decision = WINDOWING_COORDINATOR.decide_window_flight(WindowFlightContext(
            mode=self.flight_mode,
            dragging=self.dragging,
            care_mode=self.care_mode,
            social_mode=self.social_mode,
            is_recovering=self.is_recovering,
            has_window_tracker=bool(self.window_tracker),
            has_surface=surface is not None,
            can_perch_on_surface=can_perch_on_surface,
            has_anchor_center=anchor_center_x is not None,
            distance_to_target=distance_to_target,
        ))
        if flight_decision.action == WINDOW_FLIGHT_DECISION_NONE:
            return False
        if flight_decision.action == WINDOW_FLIGHT_DECISION_STOP:
            return WINDOWING_EFFECTS.apply_window_flight_stop(self)

        if flight_decision.action == WINDOW_FLIGHT_DECISION_TASKBAR_TICK:
            return WINDOWING_EFFECTS.apply_window_flight_taskbar_tick(self)

        if flight_decision.action == WINDOW_FLIGHT_DECISION_ATTACH:
            return WINDOWING_EFFECTS.apply_window_flight_attach(self, surface, anchor_center_x)

        if flight_decision.action != WINDOW_FLIGHT_DECISION_WINDOW_TICK:
            return False

        return WINDOWING_EFFECTS.apply_window_flight_window_tick(self, surface, anchor_center_x)
