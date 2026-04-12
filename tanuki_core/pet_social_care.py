import random

from PyQt6.QtWidgets import QApplication

from .geometry import get_total_virtual_geometry
from .runtime import app_now


class PetSocialCareMixin:
    def is_distressed(self):
        if self.current_mood_tag in self.DISTRESS_MOODS:
            return True
        return self.mood_state == "depressed" and self.current_mood_tag not in {"happy", "smile", "confidence", "cool"}

    def is_under_care(self, now):
        return self.care_partner is not None and self.care_lock_mode != "none" and now < self.care_lock_end_time

    def clear_care_lock(self):
        if self.care_lock_mode == "hidden" and not self.isVisible():
            self.show()
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0

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
            self.perched_window_hwnd != 0 or
            self.edge_mode != "none" or
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
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if frames:
                return True
        return self.change_state_candidates(candidates, context=context)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        if any(self.current_purpose == purpose and self.current_action_tag == action for purpose, action in candidates):
            frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=self.mood_score,
                context=context,
            )
            if self.current_mood_tag in preferred_moods and frames:
                return True
        return self.change_state_candidates_with_preferences(
            candidates,
            preferred_moods,
            forbidden=forbidden,
            context=context,
        )

    def get_child_comfort_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("idle", "drink"),
                ("idle", "eat"),
                ("idle", "side_eat_candy"),
                ("idle", "sit"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "side_hug"),
            ]
        return [
            ("idle", "drink"),
            ("idle", "eat"),
            ("idle", "side_hug"),
            ("idle", "side_rub"),
            ("idle", "sit_no"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_child_recovery_candidates(self):
        if self.name == "Tokai Teio":
            return [
                ("move", "walk_drink"),
                ("idle", "dance_uma_drink"),
                ("idle", "side_eat_candy"),
                ("idle", "lie"),
                ("idle", "side"),
                ("idle", "sit"),
            ]
        return self.get_child_comfort_candidates()

    def get_adult_companion_candidates(self):
        return [
            ("idle", "sit"),
            ("idle", "sit_talk"),
            ("idle", "sit_read"),
            ("idle", "rest"),
            ("idle", "squat"),
            ("idle", "side"),
        ]

    def get_move_candidates(self):
        return [
            ("move", "walk"),
            ("move", "run"),
            ("move", "jog"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_care_move_candidates(self):
        return [
            ("move", "run"),
            ("move", "jog"),
            ("move", "walk"),
            ("move", "sneak"),
            ("move", "climb"),
            ("move", "fly"),
            ("move", "fly_up"),
        ]

    def get_idle_candidates(self):
        return [
            ("idle", "stand"),
            ("idle", "side"),
            ("idle", "sit"),
            ("idle", "rest"),
            ("idle", "lie"),
            ("idle", "squat"),
            ("idle", "observe"),
            ("idle", "photo"),
            ("idle", "photo_ready"),
            ("idle", "dance_three"),
            ("idle", "dance_uma"),
            ("idle", "hear"),
            ("idle", "knock"),
            ("idle", "get"),
            ("idle", "sleep"),
        ]

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
        return True

    def start_social_mode(self, mode, target, now):
        self.social_mode = mode
        self.social_target = target
        self.social_started_at = now
        self.social_timer_frames = self.get_social_duration_frames(mode)
        self.star_timer.start(30)

    def stop_social_mode(self, now, apply_cooldown=True):
        if apply_cooldown and self.social_mode != "none":
            self.social_cooldown_end = now + self.get_social_cooldown_seconds()
        self.social_mode = "none"
        self.social_target = None
        self.social_started_at = 0.0
        self.social_timer_frames = 0

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

    def parse_interaction_action(self, action_key):
        if action_key.startswith("move_"):
            motion = "move"
            rest = action_key[len("move_"):]
        elif action_key.startswith("idle_"):
            motion = "idle"
            rest = action_key[len("idle_"):]
        else:
            return None
        if "_" not in rest:
            return None
        action_desc, child_token = rest.rsplit("_", 1)
        return motion, action_desc, child_token

    def get_distress_mood_candidates(self, child):
        moods = []
        for mood in [child.current_mood_tag, "sad", "cry", "hard-cry", "happy"]:
            if mood and mood not in moods:
                moods.append(mood)
        return moods

    def select_interaction_animation(self, child):
        child_tokens = set(child.get_child_tokens())
        actions = self.asset_manager.get_action_keys("interaction")
        if not actions:
            return None

        preferred_motion = "move" if self.state == "move" else "idle"
        motion_order = [preferred_motion, "idle" if preferred_motion == "move" else "move"]
        for motion in motion_order:
            for mood in self.get_distress_mood_candidates(child):
                matches = []
                for action_key in actions:
                    parsed = self.parse_interaction_action(action_key)
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
        self.stop_social_mode(app_now(), apply_cooldown=False)
        self.care_mode = "approach"
        self.care_target = child
        self.care_plan = "auto"
        child.care_partner = self

    def decide_care_plan(self, child, has_interaction):
        if not has_interaction:
            return "companion"
        interaction_weights = {
            "Symboli Rudolf": 0.65,
            "Sirius Symboli": 0.50,
            "Air Groove": 0.40,
        }
        interaction_chance = interaction_weights.get(self.name, 0.50)
        if random.random() < interaction_chance:
            return "interaction"
        return "companion"

    def begin_hidden_interaction(self, child, animation_spec, now):
        action_key, mood, frames = animation_spec
        parsed = self.parse_interaction_action(action_key)
        motion = parsed[0] if parsed else "idle"
        self.care_mode = "moving_interaction" if motion == "move" else "interaction"
        self.care_end_time = now + 3.0
        self.is_hugging = True
        self.care_move_direction = self.direction or 1
        child.care_partner = self
        child.care_lock_mode = "hidden"
        child.care_lock_end_time = self.care_end_time
        child.hide()
        self.current_frames = frames
        self.frame_index = 0
        self.current_purpose = "interaction"
        self.current_action_tag = action_key
        self.current_mood_tag = mood
        self.state = "move" if self.care_mode == "moving_interaction" else "idle"

    def begin_companion_care(self, child, now):
        self.care_mode = "sit"
        self.care_end_time = now + 5.0
        child.care_partner = self
        child.care_lock_mode = "comfort"
        child.care_lock_end_time = self.care_end_time
        child.show()
        self.state = "idle"
        self.ensure_candidate_animation(self.get_adult_companion_candidates())
        child.state = "idle"
        child.ensure_candidate_animation(child.get_child_comfort_candidates())

    def finish_care_mode(self, success=True):
        now = app_now()
        child = self.care_target
        previous_mode = self.care_mode
        if child:
            if previous_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
            if success:
                child.mood_score = min(100, child.mood_score + 25)
                child.pop_heart()
                child.start_recovery(now)
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"
        self.care_cooldown_end = now + 4.0
        self.state = "idle"
        self.change_state("idle", "stand")

    def cancel_care_mode(self):
        child = self.care_target
        if child:
            if self.care_mode == "moving_interaction":
                self.release_hidden_child_nearby(child)
            if not child.isVisible():
                child.show()
            child.clear_care_lock()
        self.is_hugging = False
        self.care_mode = "none"
        self.care_target = None
        self.care_end_time = 0.0
        self.care_move_direction = 0
        self.care_plan = "auto"

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
        if not self.is_adult or not self.isVisible():
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        care_enabled = self.dashboard.care_feature_enabled if self.dashboard else True
        if not care_enabled:
            if self.care_mode != "none":
                self.cancel_care_mode()
            return False

        if self.care_mode != "none":
            child = self.care_target
            if (
                not child or
                child not in all_pets or
                child.care_partner not in (None, self) or
                (not child.isVisible() and self.care_mode not in {"interaction", "moving_interaction"})
            ):
                self.cancel_care_mode()
                return False

            if self.care_mode == "interaction":
                if now >= self.care_end_time:
                    self.finish_care_mode(success=True)
                else:
                    child.mood_score = min(100, child.mood_score + 0.18)
                return True

            if self.care_mode == "moving_interaction":
                self.direction = self.care_move_direction or self.direction or 1
                self.state = "move"
                child.mood_score = min(100, child.mood_score + 0.18)
                step = max(1, int(round(self.get_distressed_move_speed())))
                if now >= self.care_end_time or self.should_finish_moving_interaction_at_edge(child, step):
                    self.finish_care_mode(success=True)
                else:
                    self.move(self.x() + (step * self.direction), self.y())
                return True

            if self.care_mode == "sit":
                self.direction = -1 if child.x() < self.x() else 1
                child.direction = -1 if self.x() < child.x() else 1
                self.ensure_candidate_animation(self.get_adult_companion_candidates())
                child.ensure_candidate_animation(child.get_child_comfort_candidates())
                child.mood_score = min(100, child.mood_score + 0.10)
                if now >= self.care_end_time or child.mood_score >= 70:
                    self.finish_care_mode(success=True)
                return True

            if not child.is_distressed() and child.mood_score >= 55:
                self.finish_care_mode(success=False)
                return False

            interaction_spec = self.select_interaction_animation(child)
            if self.care_plan == "auto":
                self.care_plan = self.decide_care_plan(child, interaction_spec is not None)
            elif self.care_plan == "interaction" and not interaction_spec:
                self.care_plan = "companion"

            use_interaction = self.care_plan == "interaction" and interaction_spec is not None
            offset = 120 if self.x() <= child.x() else -120
            target_x = child.x() if use_interaction else child.x() - offset
            self.state = "move"
            self.ensure_candidate_animation_with_preferences(
                self.expand_candidates_with_context("move", self.get_care_move_candidates(), context="care_approach"),
                ["hurry", "cool", "effort", "confidence", "smile", "happy"],
                forbidden=["cry", "hard-cry", "scared"],
                context="care_approach",
            )
            arrived = self.move_toward_x(
                target_x,
                speed_scale=1.6,
                min_speed=self.get_care_approach_speed(),
            )
            if arrived or self.distance_to(child) < 140:
                if use_interaction:
                    self.begin_hidden_interaction(child, interaction_spec, now)
                else:
                    self.begin_companion_care(child, now)
            return True

        if now < self.care_cooldown_end:
            return False

        radius = None if self.name == "Sirius Symboli" else 1000
        candidates = []
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
            candidates.append((dist, pet))

        if not candidates:
            return False

        candidates.sort(key=lambda item: item[0])
        self.start_care_approach(candidates[0][1])
        return True

    def update_social_behavior(self, now, all_pets):
        if self.name not in self.CHILD_NAMES or self.dragging:
            return False

        rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)
        if self.social_mode != "none":
            if not rudolf or self.social_target != rudolf:
                self.stop_social_mode(now)
                return False

            dist = self.distance_to(rudolf)
            self.social_timer_frames -= 1
            timed_out = self.social_timer_frames <= 0
            if timed_out or dist > (self.social_distance + 150):
                self.stop_social_mode(now)
                return False

            if self.social_mode == "following":
                if rudolf.current_purpose != "move":
                    self.stop_social_mode(now)
                    return False
                self.state = "move"
                follow_x = rudolf.x() + (rudolf.direction * 120)
                self.move_toward_x(follow_x, speed_scale=1.25)
                self.ensure_candidate_animation(self.get_move_candidates())
                return True

            if self.social_mode == "mimicking":
                if not self.sync_mimic_animation(rudolf):
                    self.stop_social_mode(now)
                    return False
                self.direction = rudolf.direction
                self.state = "move" if rudolf.current_purpose == "move" else "idle"
                if rudolf.current_purpose == "move":
                    self.move_toward_x(rudolf.x(), speed_scale=1.05)
                return True

        if not rudolf or now < self.social_cooldown_end:
            return False

        dist = self.distance_to(rudolf)
        is_behind = (self.x() - rudolf.x()) * rudolf.direction < 0
        if dist >= self.social_distance:
            return False

        if rudolf.current_purpose == "move" and is_behind:
            self.start_social_mode("following", rudolf, now)
            return True

        if self.can_strictly_mimic(rudolf):
            self.start_social_mode("mimicking", rudolf, now)
            return True

        return False
