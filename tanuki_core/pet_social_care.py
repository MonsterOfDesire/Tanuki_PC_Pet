import random

from PyQt6.QtWidgets import QApplication

from .geometry import get_total_virtual_geometry
from .pet_social_catalog import (
    get_adult_companion_candidates as catalog_get_adult_companion_candidates,
    get_care_move_candidates as catalog_get_care_move_candidates,
    get_child_comfort_candidates as catalog_get_child_comfort_candidates,
    get_child_recovery_candidates as catalog_get_child_recovery_candidates,
    get_idle_candidates as catalog_get_idle_candidates,
    get_move_candidates as catalog_get_move_candidates,
)
from .pet_social_coordinator import (
    ActiveCareContext,
    ActiveSocialContext,
    CARE_DECISION_APPROACH_TICK,
    CARE_DECISION_CANCEL,
    CARE_DECISION_CONTINUE,
    CARE_DECISION_FINISH_FAILURE,
    CARE_DECISION_FINISH_SUCCESS,
    CARE_DECISION_INTERACTION_TICK,
    CARE_DECISION_MOVING_INTERACTION_TICK,
    CARE_DECISION_SIT_TICK,
    CARE_DECISION_START_APPROACH,
    CARE_TRANSITION_COMPANION,
    CARE_TRANSITION_INTERACTION,
    IdleCareContext,
    SOCIAL_CARE_COORDINATOR,
    SOCIAL_DECISION_ACTIVE_FOLLOWING,
    SOCIAL_DECISION_ACTIVE_MIMICKING,
    SOCIAL_DECISION_CONTINUE,
    SOCIAL_DECISION_START_FOLLOWING,
    SOCIAL_DECISION_START_MIMICKING,
    SOCIAL_DECISION_STOP,
    SocialEntryContext,
)
from .pet_social_effects import SOCIAL_CARE_EFFECTS
from .pet_social_rules import (
    CareAdultCandidate,
    CareTargetCandidate,
    build_distress_mood_candidates,
    can_mimic_socially,
    is_distressed_state,
    parse_interaction_action,
    choose_preferred_care_adult_name,
    should_preserve_candidate_animation,
)
from .runtime import app_now


class PetSocialCareMixin:
    def is_distressed(self):
        return is_distressed_state(
            mood_state=self.mood_state,
            current_mood_tag=self.current_mood_tag,
            current_purpose=self.current_purpose,
            dragging=self.dragging,
            mood_score=self.mood_score,
            distress_ready_at=getattr(self, "distress_ready_at", 0.0),
            now=app_now(),
        )

    def get_preferred_care_adult_name(self, child, all_pets):
        adult_candidates = []
        child_screen = QApplication.screenAt(child.geometry().center()) or QApplication.primaryScreen()
        for pet in all_pets:
            adult_screen = QApplication.screenAt(pet.geometry().center()) or QApplication.primaryScreen()
            adult_candidates.append(CareAdultCandidate(
                name=pet.name,
                is_adult=pet.is_adult,
                is_visible=pet.isVisible(),
                is_busy=(
                    pet.dragging or
                    pet.care_mode != "none" or
                    pet.is_under_care(app_now()) or
                    pet.is_angry_locked
                ),
                distance=pet.distance_to(child),
                same_screen=(adult_screen == child_screen),
            ))
        return choose_preferred_care_adult_name(adult_candidates)

    def is_under_care(self, now):
        return self.care_partner is not None and self.care_lock_mode != "none" and now < self.care_lock_end_time

    def clear_care_lock(self):
        SOCIAL_CARE_EFFECTS.clear_care_lock(self)

    def get_care_release_padding(self):
        return 24

    def clamp_x_to_virtual_geometry(self, x, width, padding=0):
        vr = get_total_virtual_geometry()
        min_x = vr.left() + padding
        max_x = vr.right() - width - padding
        if max_x < min_x:
            min_x = vr.left()
            max_x = vr.right() - width
        return max(min_x, min(max_x, x))

    def get_child_release_position(self, child, direction=None, offset=None):
        if direction is None:
            direction = self.care_move_direction or self.direction or 1
        if offset is None:
            offset = random.randint(40, 60)
        adult_center_x = self.x() + (self.width() // 2)
        child_x = int(adult_center_x + (direction * offset) - (child.width() / 2))
        child_x = self.clamp_x_to_virtual_geometry(
            child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        geom = screen.availableGeometry()
        child_y = geom.bottom() - child.height()
        return child_x, child_y

    def should_finish_moving_interaction_at_edge(self, child, step):
        direction = self.care_move_direction or self.direction or 1
        vr = get_total_virtual_geometry()
        projected_x = self.x() + (step * direction)
        if projected_x < vr.left() or projected_x + self.width() > vr.right():
            return True
        projected_center_x = projected_x + (self.width() // 2)
        projected_child_x = int(projected_center_x + (direction * 60) - (child.width() / 2))
        clamped_child_x = self.clamp_x_to_virtual_geometry(
            projected_child_x,
            child.width(),
            padding=self.get_care_release_padding(),
        )
        return projected_child_x != clamped_child_x

    def release_hidden_child_nearby(self, child):
        child_x, child_y = self.get_child_release_position(child)
        child.move(child_x, child_y)

    def should_ignore_collision(self):
        now = app_now()
        return (
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.flight_mode != "none" or
            self.is_hugging or
            self.care_mode != "none" or
            self.care_partner is not None or
            self.is_under_care(now)
        )

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood = result
        if not frames:
            return False
        self.current_frames = frames
        self.frame_index = 0
        if hasattr(self, "animation_step_budget"):
            self.animation_step_budget = 0.0
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood
        return True

    def change_state_candidates(self, candidates, context=None):
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                self.mood_score,
                is_adult=self.is_adult,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        for mood_tag in preferred_moods:
            for purpose, action_type in candidates:
                frames = self.asset_manager.get_specific_frames(
                    purpose,
                    action_type,
                    mood_tag,
                    mood_score=self.mood_score,
                    context=context,
                )
                if frames and self.apply_animation_result(purpose, (frames, action_type, mood_tag)):
                    return True
        for purpose, action_type in candidates:
            result = self.asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred_moods,
                forbidden=forbidden,
                mood_score=self.mood_score,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def get_severe_moods(self):
        return self.ADULT_SEVERE_MOODS if self.is_adult else self.SEVERE_MOODS

    def get_speed_for_mood_score(self, mood_score):
        if mood_score < 20:
            return 1.1 + (mood_score / 20.0) * 0.6
        if mood_score < 50:
            return 1.5 + ((mood_score - 20.0) / 30.0) * 0.9
        return 0.4 + (mood_score / 100.0) * 2.6

    def get_base_speed(self):
        return self.get_speed_for_mood_score(self.mood_score)

    def get_distressed_move_speed(self):
        return self.get_speed_for_mood_score(35.0)

    def get_care_approach_speed(self):
        return max(2.8, self.get_base_speed() + 0.6)

    def reset_stationary_move_mode(self):
        self.stationary_move_mode = False
        self.stationary_move_key = ""

    def is_stationary_move_candidate(self):
        return (
            self.name == "Tokai Teio" and
            self.current_purpose == "move" and
            self.current_action_tag in {"jog", "walk_drink"}
        )

    def configure_stationary_move_mode(self, context="random", force=False):
        if context != "random" or not self.is_stationary_move_candidate():
            self.reset_stationary_move_mode()
            return
        current_key = f"{context}:{self.current_action_tag}"
        if not force and self.stationary_move_key == current_key:
            return
        self.stationary_move_key = current_key
        stationary_chances = {
            "jog": 0.35,
            "walk_drink": 0.65,
        }
        self.stationary_move_mode = random.random() < stationary_chances.get(self.current_action_tag, 0.0)

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        expanded = list(candidates)
        seen = set(expanded)
        extra_actions = self.asset_manager.get_action_keys_for_context(
            purpose,
            mood_score=self.mood_score,
            context=context,
        )
        for action_type in extra_actions:
            candidate = (purpose, action_type)
            if candidate not in seen:
                expanded.append(candidate)
                seen.add(candidate)
        return expanded

    def ensure_candidate_animation(self, candidates, context=None):
        frames = self.asset_manager.get_specific_frames(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            mood_score=self.mood_score,
            context=context,
        )
        if should_preserve_candidate_animation(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            candidates,
            frames_available=bool(frames),
        ):
            return True
        return self.change_state_candidates(candidates, context=context)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        frames = self.asset_manager.get_specific_frames(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            mood_score=self.mood_score,
            context=context,
        )
        if should_preserve_candidate_animation(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            candidates,
            frames_available=bool(frames),
            preferred_moods=preferred_moods,
            forbidden=forbidden,
        ):
            return True
        return self.change_state_candidates_with_preferences(
            candidates,
            preferred_moods,
            forbidden=forbidden,
            context=context,
        )

    def get_child_comfort_candidates(self):
        return catalog_get_child_comfort_candidates(self.name)

    def get_child_recovery_candidates(self):
        return catalog_get_child_recovery_candidates(self.name)

    def get_adult_companion_candidates(self):
        return catalog_get_adult_companion_candidates()

    def get_move_candidates(self):
        return catalog_get_move_candidates()

    def get_care_move_candidates(self):
        return catalog_get_care_move_candidates()

    def get_idle_candidates(self):
        return catalog_get_idle_candidates()

    def get_randomized_candidates(self, candidates):
        randomized = list(candidates)
        random.shuffle(randomized)
        return randomized

    def start_recovery(self, now):
        self.stop_social_mode(now, apply_cooldown=False)
        self.is_recovering = True
        self.recovery_end_time = now + 8.0
        self.recovery_motion_mode = "stay"
        self.reset_stationary_move_mode()
        self.clear_care_lock()
        self.state = "idle"
        recovery_candidates = self.get_randomized_candidates(self.get_child_recovery_candidates())
        if not self.change_state_candidates(recovery_candidates):
            self.change_state("idle", "stand")
        elif self.current_purpose == "move":
            if self.name == "Tokai Teio" and random.random() < 0.4:
                self.recovery_motion_mode = "walk"
                self.state = "move"

    def maintain_care_lock(self, now):
        if self.care_partner and self.social_mode != "none":
            self.stop_social_mode(now, apply_cooldown=False)
        if self.care_partner and self.care_lock_mode == "none":
            self.state = "idle"
            return True
        if not self.is_under_care(now):
            self.clear_care_lock()
            return False
        if self.care_lock_mode == "hidden":
            if self.isVisible():
                self.hide()
            return True
        if not self.isVisible():
            self.show()
        if self.care_partner:
            self.direction = -1 if self.care_partner.x() < self.x() else 1
        self.state = "idle"
        self.ensure_candidate_animation(self.get_child_comfort_candidates())
        self.mood_score = min(100, self.mood_score + 0.05)
        if hasattr(self, "sync_mood_state_with_score"):
            self.sync_mood_state_with_score()
        return True

    def start_social_mode(self, mode, target, now):
        SOCIAL_CARE_EFFECTS.start_social_mode(self, mode, target, now)

    def stop_social_mode(self, now, apply_cooldown=True):
        SOCIAL_CARE_EFFECTS.stop_social_mode(self, now, apply_cooldown=apply_cooldown)

    def can_strictly_mimic(self, target):
        return bool(self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        ))

    def sync_mimic_animation(self, target):
        frames = self.asset_manager.get_specific_frames(
            target.current_purpose,
            target.current_action_tag,
            target.current_mood_tag,
        )
        if not frames:
            return False
        if (
            self.current_purpose != target.current_purpose or
            self.current_action_tag != target.current_action_tag or
            self.current_mood_tag != target.current_mood_tag
        ):
            self.current_frames = frames
            self.frame_index = 0
            self.current_purpose = target.current_purpose
            self.current_action_tag = target.current_action_tag
            self.current_mood_tag = target.current_mood_tag
        return True

    def select_interaction_animation(self, child):
        child_tokens = set(child.get_child_tokens())
        actions = self.asset_manager.get_action_keys("interaction")
        if not actions:
            return None

        preferred_motion = "move" if self.state == "move" else "idle"
        motion_order = [preferred_motion, "idle" if preferred_motion == "move" else "move"]
        for motion in motion_order:
            for mood in build_distress_mood_candidates(child.current_mood_tag):
                matches = []
                for action_key in actions:
                    parsed = parse_interaction_action(action_key)
                    if not parsed:
                        continue
                    action_motion, _, child_token = parsed
                    if action_motion != motion or child_token not in child_tokens:
                        continue
                    interaction_context = "moving_interaction" if action_motion == "move" else "interaction"
                    frames = self.asset_manager.get_specific_frames(
                        "interaction",
                        action_key,
                        mood,
                        mood_score=child.mood_score,
                        context=interaction_context,
                    )
                    if frames:
                        matches.append((action_key, mood, frames))
                if matches:
                    return random.choice(matches)
        return None

    def start_care_approach(self, child):
        SOCIAL_CARE_EFFECTS.start_care_approach(self, child, app_now())

    def begin_hidden_interaction(self, child, animation_spec, now):
        SOCIAL_CARE_EFFECTS.begin_hidden_interaction(self, child, animation_spec, now)

    def begin_companion_care(self, child, now):
        SOCIAL_CARE_EFFECTS.begin_companion_care(self, child, now)

    def finish_care_mode(self, success=True):
        SOCIAL_CARE_EFFECTS.finish_care_mode(self, success, app_now())

    def cancel_care_mode(self):
        SOCIAL_CARE_EFFECTS.cancel_care_mode(self)

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        delta = target_x - self.x()
        if abs(delta) <= 4:
            return True

        self.direction = 1 if delta > 0 else -1
        base_speed = self.get_base_speed()
        if min_speed is not None:
            base_speed = max(base_speed, min_speed)
        step = max(1, int(base_speed * speed_scale))
        nx = self.x() + (step * self.direction)
        surface = self.get_surface_snapshot()
        nx = surface.clamp_x(nx)
        if nx <= surface.left_bound:
            self.direction = 1
        elif nx >= surface.right_bound:
            self.direction = -1
        self.move(nx, self.y())
        self.refresh_movement_state()
        return abs(target_x - self.x()) <= step

    def update_care_behavior(self, now, all_pets):
        gate = SOCIAL_CARE_COORDINATOR.decide_care_gate(
            is_adult=self.is_adult,
            is_visible=self.isVisible(),
            care_enabled=self.is_care_feature_enabled(),
            care_mode=self.care_mode,
        )
        if gate.action == CARE_DECISION_CANCEL:
            self.cancel_care_mode()
            return False
        if gate.action != CARE_DECISION_CONTINUE:
            return False

        if self.care_mode != "none":
            child = self.care_target
            child_in_all_pets = child in all_pets if child else False
            child_partner_ok = child.care_partner in (None, self) if child else False
            child_visible = child.isVisible() if child else False
            child_mood_score = child.mood_score if child else 0.0
            child_is_distressed = child.is_distressed() if child else False

            moving_step = 0
            moving_hits_edge = False
            if child and self.care_mode == "moving_interaction":
                moving_step = max(1, int(round(self.get_distressed_move_speed())))
                moving_hits_edge = self.should_finish_moving_interaction_at_edge(child, moving_step)

            interaction_spec = None
            if (
                child and
                self.care_mode not in {"interaction", "moving_interaction", "sit"} and
                (child_is_distressed or child_mood_score < 55)
            ):
                interaction_spec = self.select_interaction_animation(child)

            decision = SOCIAL_CARE_COORDINATOR.decide_active_care(ActiveCareContext(
                has_child=child is not None,
                child_in_all_pets=child_in_all_pets,
                child_partner_ok=child_partner_ok,
                child_visible=child_visible,
                mode=self.care_mode,
                now=now,
                care_end_time=self.care_end_time,
                child_mood_score=child_mood_score,
                child_is_distressed=child_is_distressed,
                care_plan=self.care_plan,
                interaction_available=interaction_spec is not None,
                adult_name=self.name,
                adult_x=self.x(),
                child_x=child.x() if child else 0,
                distance_to_child=self.distance_to(child) if child else 0.0,
                moving_interaction_hits_edge=moving_hits_edge,
                roll=random.random(),
            ))

            if decision.action == CARE_DECISION_CANCEL:
                self.cancel_care_mode()
                return False

            if decision.action == CARE_DECISION_FINISH_SUCCESS:
                self.finish_care_mode(success=True)
                return decision.handled

            if decision.action == CARE_DECISION_FINISH_FAILURE:
                self.finish_care_mode(success=False)
                return decision.handled

            if decision.action == CARE_DECISION_INTERACTION_TICK:
                child.mood_score = min(100, child.mood_score + 0.18)
                if hasattr(child, "sync_mood_state_with_score"):
                    child.sync_mood_state_with_score()
                return True

            if decision.action == CARE_DECISION_MOVING_INTERACTION_TICK:
                self.direction = self.care_move_direction or self.direction or 1
                self.state = "move"
                child.mood_score = min(100, child.mood_score + 0.18)
                if hasattr(child, "sync_mood_state_with_score"):
                    child.sync_mood_state_with_score()
                self.move(self.x() + (moving_step * self.direction), self.y())
                return True

            if decision.action == CARE_DECISION_SIT_TICK:
                self.direction = -1 if child.x() < self.x() else 1
                child.direction = -1 if self.x() < child.x() else 1
                self.ensure_candidate_animation(self.get_adult_companion_candidates())
                child.ensure_candidate_animation(child.get_child_comfort_candidates())
                child.mood_score = min(100, child.mood_score + 0.10)
                if hasattr(child, "sync_mood_state_with_score"):
                    child.sync_mood_state_with_score()
                return True

            if decision.action != CARE_DECISION_APPROACH_TICK:
                return False

            if decision.next_care_plan is not None:
                self.care_plan = decision.next_care_plan
            self.state = "move"
            self.ensure_candidate_animation_with_preferences(
                self.expand_candidates_with_context("move", self.get_care_move_candidates(), context="care_approach"),
                ["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
                context="care_approach",
            )
            arrived = self.move_toward_x(
                decision.target_x,
                speed_scale=1.6,
                min_speed=self.get_care_approach_speed(),
            )
            transition = SOCIAL_CARE_COORDINATOR.decide_approach_transition(
                arrived=arrived,
                distance_to_child=self.distance_to(child),
                use_interaction=decision.use_interaction,
            )
            if transition == CARE_TRANSITION_INTERACTION:
                self.begin_hidden_interaction(child, interaction_spec, now)
            elif transition == CARE_TRANSITION_COMPANION:
                self.begin_companion_care(child, now)
            return True

        candidates = []
        for pet in all_pets:
            candidates.append(CareTargetCandidate(
                pet=pet,
                is_self=(pet == self),
                is_adult=pet.is_adult,
                is_visible=pet.isVisible(),
                care_partner=pet.care_partner,
                is_recovering=pet.is_recovering,
                is_distressed=pet.is_distressed(),
                distance=self.distance_to(pet),
                preferred_adult_name=(
                    self.get_preferred_care_adult_name(pet, all_pets)
                    if not pet.is_adult
                    else None
                ),
            ))

        decision = SOCIAL_CARE_COORDINATOR.decide_idle_care(IdleCareContext(
            now=now,
            care_cooldown_end=self.care_cooldown_end,
            adult=self,
            adult_name=self.name,
            target_candidates=candidates,
        ))
        if decision.action != CARE_DECISION_START_APPROACH:
            return False

        self.start_care_approach(decision.target)
        return decision.handled

    def update_social_behavior(self, now, all_pets):
        gate = SOCIAL_CARE_COORDINATOR.decide_social_gate(
            is_social_child=self.name in self.CHILD_NAMES,
            dragging=self.dragging,
        )
        if gate.action != SOCIAL_DECISION_CONTINUE:
            return False

        rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)
        if self.social_mode != "none":
            self.social_timer_frames -= 1
            decision = SOCIAL_CARE_COORDINATOR.decide_active_social(ActiveSocialContext(
                social_mode=self.social_mode,
                has_rudolf=rudolf is not None,
                social_target_matches=rudolf is not None and self.social_target == rudolf,
                distance_to_rudolf=self.distance_to(rudolf) if rudolf else 0.0,
                timer_frames_remaining=self.social_timer_frames,
                social_distance=self.social_distance,
                rudolf_purpose=rudolf.current_purpose if rudolf else "",
                can_mimic=can_mimic_socially(mood_state=self.mood_state),
            ))
            if decision.action == SOCIAL_DECISION_STOP:
                self.stop_social_mode(now)
                return False

            if decision.action == SOCIAL_DECISION_ACTIVE_FOLLOWING:
                self.state = "move"
                follow_x = rudolf.x() + (rudolf.direction * 120)
                self.move_toward_x(follow_x, speed_scale=1.25)
                self.ensure_candidate_animation(self.get_move_candidates())
                return True

            if decision.action == SOCIAL_DECISION_ACTIVE_MIMICKING:
                if not self.sync_mimic_animation(rudolf):
                    self.stop_social_mode(now)
                    return False
                self.direction = rudolf.direction
                self.state = "move" if rudolf.current_purpose == "move" else "idle"
                if rudolf.current_purpose == "move":
                    self.move_toward_x(rudolf.x(), speed_scale=1.05)
                return True

            return False

        decision = SOCIAL_CARE_COORDINATOR.decide_social_entry(SocialEntryContext(
            has_rudolf=rudolf is not None,
            now=now,
            social_cooldown_end=self.social_cooldown_end,
            distance_to_rudolf=self.distance_to(rudolf) if rudolf else 0.0,
            social_distance=self.social_distance,
            rudolf_purpose=rudolf.current_purpose if rudolf else "",
            is_behind=((self.x() - rudolf.x()) * rudolf.direction < 0) if rudolf else False,
            can_strictly_mimic=self.can_strictly_mimic(rudolf) if rudolf else False,
            can_mimic=can_mimic_socially(mood_state=self.mood_state),
        ))

        if decision.action == SOCIAL_DECISION_START_FOLLOWING:
            self.start_social_mode("following", rudolf, now)
            return True

        if decision.action == SOCIAL_DECISION_START_MIMICKING:
            self.start_social_mode("mimicking", rudolf, now)
            return True

        return False
