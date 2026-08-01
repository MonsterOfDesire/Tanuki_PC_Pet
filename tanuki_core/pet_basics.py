import math
import random

from PyQt6.QtCore import Qt

from .asset_manager import AssetManager
from .geometry import DesktopGeometry, PetMovementState


class PetBasicsMixin:
    def get_effective_scale(self):
        return self.base_scale * self.display_scale_multiplier

    def apply_display_scale(self, multiplier):
        multiplier = max(0.5, float(multiplier))
        if abs(self.display_scale_multiplier - multiplier) < 0.001:
            return

        old_center_x = self.geometry().center().x()
        old_bottom_y = self.y() + self.height()
        old_visible = self.isVisible()
        old_signature = (self.current_purpose, self.current_action_tag, self.current_mood_tag)

        self.display_scale_multiplier = multiplier
        active_path_provider = getattr(
            self,
            "get_active_character_path",
            None,
        )
        active_character_path = (
            active_path_provider()
            if callable(active_path_provider)
            else self.character_path
        )
        self.asset_manager = AssetManager(
            active_character_path,
            scale_factor=self.get_effective_scale(),
            frame_cache=self.asset_manager.frame_cache,
            store_cache=self.asset_manager.store_cache,
        )
        self.setFixedSize(int(600 * self.get_effective_scale()), int(600 * self.get_effective_scale()))
        self.radius = (100 * self.get_effective_scale())

        target_x = old_center_x - (self.width() // 2)
        target_y = old_bottom_y - self.height()

        if self.perched_window_hwnd and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
            actor_snapshot = self.window_tracker.build_actor_snapshot(self)
            if surface and self.window_tracker.can_actor_perch_on_surface(surface, actor_snapshot):
                target_x = surface.clamp_actor_x(old_center_x - (self.width() // 2), self.width())
                self.window_perch_offset_x = target_x - surface.rect.left()
                target_y = self.get_window_perch_y(surface)
            else:
                self.detach_from_window_surface()
        elif self.flight_mode == "to_window" and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.flight_target_hwnd)
            if surface:
                anchor_center_x = self.window_tracker.get_surface_visible_center_x(
                    surface,
                    actor_width=self.width(),
                    preferred_center_x=old_center_x,
                )
                if anchor_center_x is not None:
                    self.flight_target_x = surface.clamp_actor_x(anchor_center_x - (self.width() // 2), self.width())
                    self.flight_target_y = self.get_window_perch_y(surface)
                    self.window_perch_offset_x = self.flight_target_x - surface.rect.left()

        clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(self, target_x, target_y)
        self.move(clamped_x, clamped_y)

        purpose, action_type, mood = old_signature
        frames = None
        if purpose and action_type and mood:
            frames = self.asset_manager.get_specific_frames(purpose, action_type, mood, mood_score=self.mood_score)
        if frames:
            self.apply_animation_result(purpose, (frames, action_type, mood))
        elif self.state == "move":
            self.change_state("move")
        else:
            self.change_state("idle", "stand")

        if old_visible and self.user_visible:
            self.show()
        elif not self.user_visible:
            self.hide()
        self.refresh_movement_state()
        self.update()

    def reset_clicks(self):
        self.click_count = 0

    def unlock_interaction(self):
        self.is_angry_locked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.change_state("idle", "stand")

    def update_bar_opacity(self, value):
        self.bar_opacity = value
        self.update()

    def animate_heart(self, value):
        self.heart_opacity = 1.0 - (value ** 2)
        self.heart_y_offset = int(value * 60)
        self.update()

    def animate_log_icon(self, value):
        self.log_icon_opacity = 1.0 - (value ** 2)
        self.log_icon_y_offset = int(value * 42)
        self.update()

    def pop_heart(self):
        if not self.heart_pixmap.isNull():
            self.show_heart = True
            self.heart_anim.start()

    def pop_log_icon(self):
        if not self.log_icon_pixmap.isNull():
            self.show_log_icon = True
            self.log_icon_anim.stop()
            self.log_icon_anim.start()

    def is_debug_enabled(self):
        provider = getattr(self, "settings_provider", None)
        return bool(provider and getattr(provider, "debug_enabled", False))

    def is_social_status_enabled(self):
        provider = getattr(self, "settings_provider", None)
        return bool(
            provider
            and getattr(provider, "social_status_enabled", False)
        )

    def get_behavior_probe_label(self):
        intent_kind = str(getattr(self, "intent_kind", "") or "")
        intent_context = str(getattr(self, "intent_context", "") or "")
        expression_context = str(getattr(self, "expression_animation_context", "") or "")
        goal_label = ""
        if intent_kind == "post_observe_interaction" or intent_context == "post_observe_interaction":
            goal_label = "post_observe"
        elif intent_kind == "observe" or intent_context == "observe":
            goal_label = "observe"
        elif intent_kind in {"", "none", "random_roam", "ambient_idle"}:
            goal_label = "random"

        expression_label = ""
        if expression_context in {"relation_watch", "relation_close"}:
            expression_label = expression_context

        if goal_label and expression_label:
            return f"{goal_label} / {expression_label}"
        if goal_label:
            return goal_label
        if expression_label:
            return expression_label
        return ""

    def is_care_feature_enabled(self):
        provider = getattr(self, "settings_provider", None)
        if provider is None:
            return True
        return bool(getattr(provider, "care_feature_enabled", True))

    def get_debug_lines(self):
        provider = getattr(self, "settings_provider", None)
        lines = [
            f"{self.name} mood={int(self.mood_score)} state={self.state}",
            f"{self.current_purpose}/{self.current_action_tag}/{self.current_mood_tag}",
            f"intent={self.movement_state.intent} anchor={self.movement_state.anchor}",
            f"goal={self.intent_kind} situ={self.perception_situation_tag} expr={self.expression_animation_context}",
        ]
        if self.perched_window_hwnd and self.window_tracker:
            surface = self.window_tracker.get_surface_by_hwnd(self.perched_window_hwnd)
            if surface:
                lines.append(f"window={surface.title[:28]}")
        elif self.flight_mode != "none":
            lines.append(f"flight={self.flight_mode} -> ({int(self.flight_target_x)}, {int(self.flight_target_y)})")
        elif self.care_mode != "none":
            lines.append(f"care={self.care_mode}")
        elif self.social_mode != "none":
            lines.append(f"social={self.social_mode}")
        if getattr(self, "offer_scene_kind", "none") != "none":
            lines.append(f"offer={self.offer_scene_kind}")
        if self.relationship_focus_target_name:
            lines.append(
                f"focus={self.relationship_focus_target_name} "
                f"fam={int(self.relationship_focus_familiarity)} "
                f"att={int(self.relationship_focus_attachment)}"
            )
        if provider and hasattr(provider, "get_time_scale"):
            lines.append(f"time={provider.get_time_scale():g}x")
        profiler = getattr(self, "runtime_profiler", None)
        if profiler is not None and self.is_debug_enabled():
            lines.extend(profiler.build_debug_lines(
                provider.get_time_scale() if provider and hasattr(provider, "get_time_scale") else 1.0
            ))
        return lines

    def wrap_debug_lines(self, font_metrics, max_width):
        wrapped = []
        max_width = max(80, int(max_width))
        for raw_line in self.get_debug_lines():
            words = raw_line.split(" ")
            if len(words) <= 1:
                words = [raw_line]
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if font_metrics.horizontalAdvance(candidate) <= max_width:
                    current = candidate
                    continue
                if current:
                    wrapped.append(current)
                    current = ""
                if font_metrics.horizontalAdvance(word) <= max_width:
                    current = word
                    continue
                chunk = ""
                for char in word:
                    candidate_chunk = chunk + char
                    if chunk and font_metrics.horizontalAdvance(candidate_chunk) > max_width:
                        wrapped.append(chunk)
                        chunk = char
                    else:
                        chunk = candidate_chunk
                current = chunk
            if current:
                wrapped.append(current)
        return wrapped

    def get_social_cooldown_seconds(self):
        provider = getattr(self, "settings_provider", None)
        if provider:
            cooldown = provider.get_social_cooldown_seconds(self.name)
            if cooldown:
                return cooldown
        return self.social_cooldown_duration

    def get_social_duration_frames(self, mode):
        if mode == "following":
            return random.randint(200, 400)
        if mode == "mimicking":
            return random.randint(60, 80)
        return 0

    def get_child_tokens(self):
        return self.CHILD_TOKEN_MAP.get(self.name, [self.name])

    def distance_to(self, other):
        return math.hypot(
            self.geometry().center().x() - other.geometry().center().x(),
            self.geometry().center().y() - other.geometry().center().y(),
        )

    def get_surface_snapshot(self):
        return DesktopGeometry.get_surface_snapshot(self)

    def refresh_movement_state(self, surface=None):
        if surface is None:
            surface = self.get_surface_snapshot()
        if self.vy != 0:
            intent = "falling"
            locomotion = "airborne"
            anchor = "air"
            support_surface = "air"
        else:
            if self.flight_mode != "none":
                intent = f"flight:{self.flight_mode}"
                locomotion = "moving"
                anchor = "air"
                support_surface = "air"
            elif self.perched_window_hwnd:
                intent = "perched:window"
                locomotion = "moving" if self.state == "move" else "idle"
                anchor = "window_top"
                support_surface = "window_top"
            elif self.care_mode != "none":
                intent = f"care:{self.care_mode}"
            elif self.social_mode != "none":
                intent = f"social:{self.social_mode}"
            elif self.is_recovering:
                intent = "recovery"
            else:
                intent = self.state or "idle"
            if self.flight_mode == "none" and not self.perched_window_hwnd:
                locomotion = "moving" if self.state == "move" else "idle"
                support_surface = "desktop_floor" if surface.on_floor else "screen_space"
                anchor = "floor" if surface.on_floor else "air"
        self.movement_state = PetMovementState(
            intent=intent,
            locomotion=locomotion,
            anchor=anchor,
            support_surface=support_surface,
            near_left_edge=surface.near_left_edge,
            near_right_edge=surface.near_right_edge,
            dock_edge=surface.dock_edge,
        )
        return self.movement_state

    def get_taskbar_walk_y(self):
        surface = self.get_surface_snapshot()
        if surface.dock_edge == "bottom" and surface.dock_thickness > 0:
            return surface.screen_floor_top_y
        return surface.floor_top_y

    def get_airborne_top_bound(self, visible_ratio=0.35):
        surface = self.get_surface_snapshot()
        return surface.top_bound - int(self.height() * (1.0 - visible_ratio))

    def get_window_perch_y(self, surface):
        return max(self.get_airborne_top_bound(), surface.perch_y(self.height()))

    def get_drag_preferred_moods(self):
        if self.mood_score >= 50:
            return ["happy", "smile", "laugh"]
        if self.mood_score >= 20:
            return ["sad", "angry", "cry", "awkward", "think"]
        return ["cry", "hard-cry", "sad", "angry", "scold", "scared"]

    def apply_drag_animation(self):
        preferred_moods = self.get_drag_preferred_moods()
        result = self.asset_manager.get_contextual_result(
            "drag",
            context="drag",
            preferred_moods=preferred_moods,
            mood_score=self.mood_score,
        )
        legacy_assets = getattr(self.asset_manager, "assets", None)
        if not result and (
            legacy_assets is None or "drag" in legacy_assets
        ):
            result = self.asset_manager.get_frames_by_score(
                "drag",
                mood_score=self.mood_score,
                is_adult=self.is_adult,
                context="drag",
            )
        if self.apply_animation_result("drag", result):
            return True
        context_fallback = getattr(
            self,
            "change_state_for_context_any_purpose_with_preferences",
            None,
        )
        if not callable(context_fallback):
            return False
        return bool(
            context_fallback(
                "drag",
                preferred_moods=preferred_moods,
            )
        )

    def apply_hard_landing_animation(self):
        context_selector = getattr(
            self,
            "change_state_for_context_any_purpose_with_preferences",
            None,
        )
        if not callable(context_selector):
            return False
        applied = bool(context_selector("hard_landing"))
        if not applied:
            applied = bool(
                context_selector(
                    "hard_landing",
                    ignore_mood_band=True,
                )
            )
        if applied:
            self.state_timer = 80
            reset_stationary = getattr(
                self,
                "reset_stationary_move_mode",
                None,
            )
            if callable(reset_stationary):
                reset_stationary()
        return applied
