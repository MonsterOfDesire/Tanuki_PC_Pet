import math
import os
import random
import time

from PyQt6.QtCore import Qt, QTimer, QVariantAnimation
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

from .asset_manager import AssetManager
from .geometry import DesktopGeometry, PetMovementState
from .pet_basics import PetBasicsMixin
from .pet_behavior_layers import PetBehaviorLayersMixin
from .pet_collision_rules import CollisionSnapshot, compute_collision_resolution
from .pet_logic import (
    CLICK_RELEASE,
    LONG_HOLD_RELEASE,
    compute_mood_update,
    decide_release_interaction,
    derive_mood_state,
)
from .pet_physics import compute_gravity_step
from .pet_random_rules import (
    NORMAL_RANDOM_DIRECTION_FLIP_CHANCE,
    SEVERE_RANDOM_DIRECTION_FLIP_CHANCE,
    build_random_state_transition,
    derive_random_visual_purpose,
    extend_random_state_timer,
    get_idle_action_override,
    resolve_random_stuck_behavior,
    should_refresh_severe_random_state,
)
from .pet_overlay_renderer import PetOverlayRenderer
from .pet_runtime_state import PET_STATE_PROXY_FIELDS, build_pet_runtime_state
from .pet_social_care import PetSocialCareMixin
from .pet_tick_coordinator import PetTickCoordinator
from .pet_intent_rules import (
    INTENT_OBSERVE,
    INTENT_POST_OBSERVE_INTERACTION,
    allow_random_behavior_reselect,
)
from .pet_windowing import PetWindowingMixin
from .runtime import SIM_CLOCK, app_now, get_pet_logic_step_count


SAFE_WINDOW_MODE = os.environ.get("TANUKI_SAFE_WINDOW_MODE", "0") == "1"


def build_overlay_window_flags():
    flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
    if not SAFE_WINDOW_MODE:
        flags |= Qt.WindowType.Tool
    return flags


def forwarded_state_property(state_attr, field_name):
    def getter(self):
        return getattr(getattr(self, state_attr), field_name)

    def setter(self, value):
        setattr(getattr(self, state_attr), field_name, value)

    return property(getter, setter)


class TanukiPet(PetBehaviorLayersMixin, PetBasicsMixin, PetSocialCareMixin, PetWindowingMixin, QWidget):
    """
    使用明確的優先序來處理 AI，避免救助 / 模仿 / 隨機行為互相覆蓋。
    """

    ADULT_NAMES = {"Symboli Rudolf", "Sirius Symboli", "Air Groove"}
    CHILD_NAMES = {"Tokai Teio", "Tsurumaru Tsuyoshi"}
    AUTONOMOUS_FLY_DISABLED_NAMES = {"Tsurumaru Tsuyoshi"}
    CHILD_TOKEN_MAP = {
        "Tokai Teio": ["Teio"],
        "Tsurumaru Tsuyoshi": ["Tsuyoshi"],
    }
    DISTRESS_MOODS = {"sad", "cry", "hard-cry"}
    SEVERE_MOODS = {"scold", "hard-cry", "cry", "exhausted", "scared"}
    ADULT_SEVERE_MOODS = {"scold", "sad", "angry", "exhausted"}
    STAR_BASE_INTERVAL_MS = 30
    ANIMATION_BASE_INTERVAL_MS = 80
    ANIMATION_MIN_INTERVAL_MS = 17

    def __init__(self, char_id, char_folder, scale=0.8, settings_provider=None, window_tracker=None):
        super().__init__()
        self.char_id = char_id
        self.name = char_id
        self.character_path = char_folder
        self.base_scale = float(scale)
        self.display_scale_multiplier = 1.0
        self.asset_manager = AssetManager(char_folder, scale_factor=self.get_effective_scale())
        runtime_state = build_pet_runtime_state(self.name)
        self.behavior_state = runtime_state.behavior
        self.interaction_state = runtime_state.interaction
        self.motion_state = runtime_state.motion
        self.social_state = runtime_state.social
        self.care_state = runtime_state.care
        self.windowing_state = runtime_state.windowing
        self.perception_state = runtime_state.perception
        self.intent_state = runtime_state.intent
        self.relationship_state = runtime_state.relationship
        self.expression_state = runtime_state.expression
        self.movement_state = PetMovementState()
        self.current_frames = []
        self.frame_index = 0
        self.overlay_renderer = PetOverlayRenderer()
        self.original_face_left = True
        self.click_reset_timer = QTimer(self)
        self.click_reset_timer.setSingleShot(True)
        self.click_reset_timer.timeout.connect(self.reset_clicks)
        self.lock_timer = QTimer(self)
        self.lock_timer.setSingleShot(True)
        self.lock_timer.timeout.connect(self.unlock_interaction)
        self.is_adult = self.name in self.ADULT_NAMES
        self.setFixedSize(int(600 * self.get_effective_scale()), int(600 * self.get_effective_scale()))
        self.star_pixmap = QPixmap(AssetManager.get_resource_path("star.png"))
        self.star_opacity = 0.0
        self.star_y_offset = 0
        self.star_anim_counter = 0
        self.star_timer = QTimer(self)
        self.star_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.star_timer.timeout.connect(self.advance_star_animation)
        self.star_timer.start(self.STAR_BASE_INTERVAL_MS)

        self.settings_provider = settings_provider
        self.window_tracker = window_tracker

        self.bar_opacity = 0.0
        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.setDuration(300)
        self.fade_anim.valueChanged.connect(self.update_bar_opacity)
        self.heart_pixmap = QPixmap(AssetManager.get_resource_path("heart.png"))
        self.show_heart = False
        self.heart_opacity = 0.0
        self.heart_y_offset = 0
        self.heart_anim = QVariantAnimation(self)
        self.heart_anim.setDuration(1000)
        self.heart_anim.setStartValue(0.0)
        self.heart_anim.setEndValue(1.0)
        self.heart_anim.valueChanged.connect(self.animate_heart)
        self.heart_anim.finished.connect(lambda: setattr(self, "show_heart", False))
        self.log_icon_pixmap = QPixmap(AssetManager.get_resource_path("think.png"))
        self.show_log_icon = False
        self.log_icon_opacity = 0.0
        self.log_icon_y_offset = 0
        self.log_icon_anim = QVariantAnimation(self)
        self.log_icon_anim.setDuration(1100)
        self.log_icon_anim.setStartValue(0.0)
        self.log_icon_anim.setEndValue(1.0)
        self.log_icon_anim.valueChanged.connect(self.animate_log_icon)
        self.log_icon_anim.finished.connect(lambda: setattr(self, "show_log_icon", False))
        self.radius = 100 * self.get_effective_scale()
        self.mass = 2 if self.is_adult else 0.8
        self.setWindowFlags(build_overlay_window_flags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.anim_timer = QTimer(self)
        self.anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.anim_timer.timeout.connect(self.advance_animation_timer)
        self.animation_frame_accumulator = 0.0
        self.anim_timer.start(self.ANIMATION_BASE_INTERVAL_MS)
        SIM_CLOCK.register_timer(
            self.anim_timer,
            self.ANIMATION_BASE_INTERVAL_MS,
            minimum_interval_ms=self.ANIMATION_MIN_INTERVAL_MS,
        )
        self.tick_coordinator = PetTickCoordinator()
        self.change_state("idle", "stand")
        self.last_x = self.x()
        self.refresh_movement_state()
        self.show()

    def paintEvent(self, event):
        if not self.current_frames:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pixmap = self.current_frames[self.frame_index]
        draw_x = (self.width() - pixmap.width()) // 2
        draw_y = self.height() - pixmap.height()
        overlay_scale = max(1.0, math.sqrt(self.display_scale_multiplier))
        should_flip = (self.direction == 1) if self.original_face_left else (self.direction == -1)
        self.overlay_renderer.draw_character(painter, self.width(), pixmap, draw_x, draw_y, should_flip)
        self.overlay_renderer.draw_mood_bar(painter, self.width(), draw_y, self.mood_score, self.bar_opacity)
        self.overlay_renderer.draw_heart(
            painter,
            self.width(),
            draw_y,
            overlay_scale,
            self.heart_pixmap,
            self.show_heart,
            self.heart_opacity,
            self.heart_y_offset,
        )
        self.overlay_renderer.draw_stars(
            painter,
            self.width(),
            draw_y,
            overlay_scale,
            self.star_pixmap,
            self.star_opacity,
            self.star_y_offset,
            self.star_anim_counter,
        )
        self.overlay_renderer.draw_log_icon(
            painter,
            self.width(),
            draw_y,
            overlay_scale,
            self.log_icon_pixmap,
            self.show_log_icon,
            self.log_icon_opacity,
            self.log_icon_y_offset,
        )
        painter.setOpacity(1.0)

        if self.is_debug_enabled():
            max_debug_width = max(120, self.width() - 16)
            lines = self.wrap_debug_lines(painter.fontMetrics(), max_debug_width)
            self.overlay_renderer.draw_debug_overlay(painter, lines, max_debug_width, self.width())
        self.overlay_renderer.draw_head_status_label(
            painter,
            self.get_behavior_probe_label(),
            self.width(),
            draw_y,
        )

    def next_frame(self, steps=1):
        if self.current_frames:
            self.frame_index = (self.frame_index + int(steps)) % len(self.current_frames)
            self.update()

    def advance_animation_timer(self):
        is_visible = getattr(self, "isVisible", None)
        if callable(is_visible) and not is_visible():
            return
        if float(SIM_CLOCK.speed) <= 1.0 + 1e-6:
            self.animation_frame_accumulator = 0.0
            self.next_frame()
            return
        timer = getattr(self, "anim_timer", None)
        interval_getter = getattr(timer, "interval", None)
        if not callable(interval_getter):
            self.next_frame()
            return
        step_delta = SIM_CLOCK.get_timer_step_delta(
            self.ANIMATION_BASE_INTERVAL_MS,
            actual_interval_ms=interval_getter(),
        )
        accumulator = float(getattr(self, "animation_frame_accumulator", 0.0)) + float(step_delta)
        frame_steps = int(accumulator)
        self.animation_frame_accumulator = accumulator - frame_steps
        if frame_steps > 0:
            self.next_frame(steps=frame_steps)

    def advance_star_animation(self):
        self.update_star_animation()

    def update_mood(self, all_pets):
        my_center = self.geometry().center()
        nearby_count = 0
        has_adult_nearby = False
        for other in all_pets:
            if other == self or not other.isVisible():
                continue
            other_center = other.geometry().center()
            if math.hypot(my_center.x() - other_center.x(), my_center.y() - other_center.y()) < 250:
                nearby_count += 1
                has_adult_nearby = has_adult_nearby or other.is_adult

        old_state = self.mood_state
        mood_update = compute_mood_update(
            current_score=self.mood_score,
            lonely_timer=self.lonely_timer,
            is_adult=self.is_adult,
            nearby_count=nearby_count,
            has_adult_nearby=has_adult_nearby,
            noise=random.uniform(-1, 1),
        )
        self.mood_score = mood_update.mood_score
        self.lonely_timer = mood_update.lonely_timer
        self.mood_state = mood_update.mood_state
        self.distress_ready_at = 0.0
        if old_state != self.mood_state:
            self.refresh_animation_for_mood_change()

    def sync_mood_state_with_score(self):
        self.mood_score = max(0.0, min(100.0, float(self.mood_score)))
        old_state = self.mood_state
        self.mood_state = derive_mood_state(self.mood_score)
        if self.mood_state != "depressed":
            self.distress_ready_at = 0.0
        if old_state != self.mood_state:
            self.refresh_animation_for_mood_change()

    def refresh_animation_for_mood_change(self, now=None):
        if self.is_scene_animation_locked(now):
            return False
        target_purpose = self.current_purpose or ("move" if self.state == "move" else "idle")
        self.change_state(target_purpose, self.current_action_tag)
        return True

    def tick(self, all_pets):
        profiler = getattr(self, "runtime_profiler", None)
        profiler_started_at = time.perf_counter() if profiler is not None else 0.0
        now = app_now()
        if self.is_offer_locked(now):
            self.apply_offer_behavior_layer_override()
            if self.vy != 0:
                self.apply_gravity()
            self.check_boundary_stuck()
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.tick",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        window_perch_handled = False
        window_flight_handled = False
        tick_window_plan = self.tick_coordinator.build_tick_window_plan(self.dragging)
        if tick_window_plan.try_window_perch:
            window_perch_handled = self.update_window_perch(all_pets)
        if tick_window_plan.try_window_flight and not window_perch_handled:
            window_flight_handled = self.update_window_flight()

        tick_plan = self.tick_coordinator.resolve_tick_execution_plan(
            dragging=self.dragging,
            window_perch_handled=window_perch_handled,
            window_flight_handled=window_flight_handled,
            vertical_velocity=self.vy,
        )
        if tick_plan.should_refresh_and_return:
            self.refresh_behavior_layers(all_pets, now=now)
            if profiler is not None:
                profiler.record_section(
                    "pet.tick",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return

        if tick_plan.should_apply_gravity:
            self.apply_gravity()
        if tick_plan.should_check_boundary_stuck:
            self.check_boundary_stuck()
        self.refresh_movement_state()
        if tick_plan.should_run_ai:
            self.refresh_behavior_layers(all_pets, now=now)
            self.update_ai_behavior(all_pets)
            if profiler is not None:
                profiler.record_section(
                    "pet.tick",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        self.refresh_behavior_layers(all_pets, now=now)
        if profiler is not None:
            profiler.record_section(
                "pet.tick",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )

    def apply_gravity(self):
        surface = self.get_surface_snapshot()
        current_y = self.y()
        current_vy = self.vy
        fall_origin_y = self.fall_origin_y
        total_mood_penalty = 0.0
        reaction_moods = ()
        for _ in range(get_pet_logic_step_count(self)):
            gravity_step = compute_gravity_step(
                current_y=current_y,
                current_vy=current_vy,
                gravity=self.gravity,
                floor_top_y=surface.floor_top_y,
                bounce=self.bounce,
                fall_origin_y=fall_origin_y,
                max_fall_distance=surface.floor_top_y - surface.top_bound,
                is_adult=self.is_adult,
            )
            current_y = gravity_step.next_y
            current_vy = gravity_step.next_vy
            fall_origin_y = gravity_step.fall_origin_y
            total_mood_penalty += float(gravity_step.mood_penalty)
            if gravity_step.reaction_moods:
                reaction_moods = gravity_step.reaction_moods
        self.fall_origin_y = fall_origin_y
        self.vy = current_vy
        if self.y() != current_y:
            self.move(self.x(), current_y)
        if total_mood_penalty > 0:
            self.mood_score = max(0.0, self.mood_score - total_mood_penalty)
            self.apply_reaction(list(reaction_moods), is_negative=True)
        self.refresh_movement_state()

    def update_star_animation(self):
        offer_active = getattr(self, "offer_scene_kind", "none") != "none"
        target_opacity = 1.0 if self.social_mode in ["following", "mimicking"] and not offer_active else 0.0
        if self.star_opacity < target_opacity:
            self.star_opacity = min(1.0, self.star_opacity + 0.1)
        elif self.star_opacity > target_opacity:
            self.star_opacity = max(0.0, self.star_opacity - 0.1)
        self.star_anim_counter = (self.star_anim_counter + 1) % 360
        self.star_y_offset = int(math.sin(self.star_anim_counter * 0.1) * 5)
        if self.star_opacity > 0:
            self.update()
        else:
            self.star_timer.stop()

    def update_random_behavior(self, allow_reselect=True):
        expression_context = self.get_random_animation_context()
        random_context = "random"
        if self.mood_score < 20 and self.current_purpose != "interaction":
            self.last_x = self.x()
            self.state_timer -= get_pet_logic_step_count(self)
            should_refresh_severe = should_refresh_severe_random_state(
                self.current_mood_tag,
                self.get_severe_moods(),
                self.state_timer,
            )
            if should_refresh_severe and (allow_reselect or self.current_mood_tag not in self.get_severe_moods()):
                transition = build_random_state_transition(
                    next_state=random.choice(["idle", "move"]),
                    next_state_timer=random.randint(60, 110),
                    flip_roll=random.random(),
                    flip_threshold=SEVERE_RANDOM_DIRECTION_FLIP_CHANCE,
                )
                self.state = transition.next_state
                self.state_timer = transition.next_state_timer
                if transition.clear_current_purpose:
                    self.current_purpose = ""
                if transition.reset_stationary_mode:
                    self.reset_stationary_move_mode()
                if transition.flip_direction:
                    self.direction *= -1
            elif should_refresh_severe and not allow_reselect:
                self.state_timer = extend_random_state_timer(self.state_timer, 30)

            severe_candidates = self.get_random_manifest_candidates(
                "move" if self.state == "move" else "idle",
                context=random_context,
            )
            if self.current_purpose != ("move" if self.state == "move" else "idle"):
                if self.change_state_candidates(
                    self.get_randomized_candidates(severe_candidates),
                    context=random_context,
                ):
                    self.configure_stationary_move_mode("random", force=True)

            if self.state == "move":
                if self.try_start_window_flight(app_now()):
                    return
                if not self.stationary_move_mode:
                    self.move_logic()
                if self.current_purpose != "move":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.get_random_manifest_candidates("move", context=random_context)
                        ),
                        context=random_context,
                    ):
                        self.configure_stationary_move_mode("random", force=True)
            else:
                self.reset_stationary_move_mode()
                if self.current_purpose != "idle":
                    if self.change_state_candidates(
                        self.get_randomized_candidates(
                            self.get_random_manifest_candidates("idle", context=random_context)
                        ),
                        context=random_context,
                    ):
                        self.reset_stationary_move_mode()
            return

        if self.state == "move":
            if self.try_start_window_flight(app_now()):
                return
            stuck_resolution = resolve_random_stuck_behavior(
                stationary_move_mode=self.stationary_move_mode,
                position_delta=self.x() - self.last_x,
                stuck_count=self.stuck_count,
                recovery_state_timer=random.randint(30, 80),
            )
            self.stuck_count = stuck_resolution.next_stuck_count
            if stuck_resolution.flip_direction:
                self.direction *= -1
            if stuck_resolution.next_state_timer is not None:
                self.state_timer = stuck_resolution.next_state_timer

        self.last_x = self.x()
        self.state_timer -= get_pet_logic_step_count(self)
        if self.state_timer <= 0 and allow_reselect:
            transition = build_random_state_transition(
                next_state=random.choice(["idle", "move"]),
                next_state_timer=random.randint(100, 150),
                flip_roll=random.random(),
                flip_threshold=NORMAL_RANDOM_DIRECTION_FLIP_CHANCE,
            )
            self.state = transition.next_state
            self.state_timer = transition.next_state_timer
            if transition.clear_current_purpose:
                self.current_purpose = ""
            if transition.reset_stationary_mode:
                self.reset_stationary_move_mode()
            if transition.flip_direction:
                self.direction *= -1
        elif self.state_timer <= 0:
            self.state_timer = extend_random_state_timer(self.state_timer, 30)

        base_speed = self.get_base_speed()
        visual_purpose = derive_random_visual_purpose(self.state, base_speed)
        expression_handled = False
        if visual_purpose == "idle":
            expression_handled = self.apply_expression_idle_behavior(expression_context)
        current_visual_frames = None
        preserve_visual_mood_score = self.mood_score
        preserve_context = expression_context if expression_handled else random_context
        should_apply_negative_afterglow = getattr(self, "should_apply_negative_afterglow_to_candidates", None)
        if callable(should_apply_negative_afterglow) and should_apply_negative_afterglow(
            [(visual_purpose, self.current_action_tag)]
        ):
            preserve_visual_mood_score = None
        if self.current_purpose == visual_purpose and self.current_action_tag and self.current_mood_tag:
            current_visual_frames = self.asset_manager.get_specific_frames(
                self.current_purpose,
                self.current_action_tag,
                self.current_mood_tag,
                mood_score=preserve_visual_mood_score,
                context=preserve_context,
            )
        if self.current_purpose != visual_purpose or not current_visual_frames:
            candidates = self.get_random_manifest_candidates(
                visual_purpose,
                context=random_context,
            )
            if self.change_state_candidates(self.get_randomized_candidates(candidates), context=random_context):
                self.configure_stationary_move_mode("random", force=True)

        if self.state == "move":
            if not self.stationary_move_mode:
                self.move_logic()
            if self.current_purpose != "move":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.get_random_manifest_candidates("move", context=random_context)
                    ),
                    context=random_context,
                ):
                    self.configure_stationary_move_mode("random", force=True)
        else:
            self.reset_stationary_move_mode()
            if self.current_purpose != "idle":
                if self.change_state_candidates(
                    self.get_randomized_candidates(
                        self.get_random_manifest_candidates("idle", context=random_context)
                    ),
                    context=random_context,
                ):
                    self.reset_stationary_move_mode()

    def update_ai_behavior(self, all_pets):
        profiler = getattr(self, "runtime_profiler", None)
        profiler_started_at = time.perf_counter() if profiler is not None else 0.0
        now = app_now()
        initial_ai_plan = self.tick_coordinator.resolve_initial_ai_plan(
            is_angry_locked=self.is_angry_locked,
            is_recovering=self.is_recovering,
            recovery_expired=now > self.recovery_end_time if self.is_recovering else False,
            recovery_motion_mode=self.recovery_motion_mode,
            current_purpose=self.current_purpose,
        )
        if initial_ai_plan.should_refresh_and_return:
            if initial_ai_plan.should_move_recovery_walk:
                self.move_logic()
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.ai",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        if initial_ai_plan.should_finish_recovery:
            self.is_recovering = False
            self.recovery_motion_mode = "stay"
            self.reset_stationary_move_mode()
            self.change_state("idle", "stand")

        care_lock_maintained = self.maintain_care_lock(now)
        care_behavior_handled = False
        social_behavior_handled = False
        post_observe_interaction_handled = False
        observe_behavior_handled = False
        ambient_mood_event_handled = False
        active_post_observe_interaction = (
            self.intent_kind == INTENT_POST_OBSERVE_INTERACTION and
            bool(self.intent_target_name)
        )
        active_observe = (
            self.intent_kind == INTENT_OBSERVE and
            bool(self.intent_target_name)
        )
        high_level_followup_allowed = active_post_observe_interaction or active_observe
        if (
            initial_ai_plan.should_attempt_followup and
            not care_lock_maintained and
            not high_level_followup_allowed
        ):
            high_level_followup_allowed = self.should_refresh_high_level_ai()

        if initial_ai_plan.should_attempt_followup and not care_lock_maintained:
            care_behavior_handled = self.update_care_behavior(now, all_pets)
        if initial_ai_plan.should_attempt_followup and not care_lock_maintained and not care_behavior_handled:
            social_behavior_handled = self.update_social_behavior(now, all_pets)
        if (
            initial_ai_plan.should_attempt_followup and
            not care_lock_maintained and
            not care_behavior_handled and
            not social_behavior_handled and
            high_level_followup_allowed
        ):
            post_observe_interaction_handled = self.update_post_observe_interaction_behavior(now, all_pets)
        if (
            initial_ai_plan.should_attempt_followup and
            not care_lock_maintained and
            not care_behavior_handled and
            not social_behavior_handled and
            not post_observe_interaction_handled and
            high_level_followup_allowed
        ):
            observe_behavior_handled = self.update_observe_behavior(now, all_pets)
        if (
            initial_ai_plan.should_attempt_followup and
            not care_lock_maintained and
            not care_behavior_handled and
            not social_behavior_handled and
            not post_observe_interaction_handled and
            not observe_behavior_handled and
            high_level_followup_allowed
        ):
            ambient_mood_event_handled = self.update_ambient_mood_events(now)

        followup_ai_plan = self.tick_coordinator.resolve_followup_ai_plan(
            care_lock_maintained=care_lock_maintained,
            care_behavior_handled=care_behavior_handled,
            social_behavior_handled=social_behavior_handled,
        )
        if observe_behavior_handled:
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.ai",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        if ambient_mood_event_handled:
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.ai",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        if post_observe_interaction_handled:
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.ai",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        if followup_ai_plan.should_refresh_and_return:
            self.refresh_movement_state()
            if profiler is not None:
                profiler.record_section(
                    "pet.ai",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return
        if followup_ai_plan.should_run_random:
            intent_plan = self.tick_coordinator.resolve_intent_reselect_plan(
                now=now,
                intent_kind=self.intent_kind,
                intent_reconsider_after=self.intent_reconsider_after,
                dragging=self.dragging,
                is_angry_locked=self.is_angry_locked,
                is_recovering=self.is_recovering,
                care_lock_maintained=care_lock_maintained,
                care_mode=self.care_mode,
                social_mode=self.social_mode,
                flight_mode=self.flight_mode,
                perched_window_hwnd=self.perched_window_hwnd,
            )
            if intent_plan.next_reconsider_after is not None:
                self.intent_reconsider_after = intent_plan.next_reconsider_after
            allow_random_reselect = allow_random_behavior_reselect(
                intent_kind=self.intent_kind,
                intent_gate_open=intent_plan.allow_reselect,
            )
            self.update_random_behavior(allow_reselect=allow_random_reselect)
        self.refresh_movement_state()
        if profiler is not None:
            profiler.record_section(
                "pet.ai",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )

    def move_logic(self):
        base_speed = self.get_base_speed()
        step = max(1, int(base_speed)) * get_pet_logic_step_count(self)
        next_x = self.x() + (step * self.direction)
        surface = self.get_surface_snapshot()
        clamped_x = surface.clamp_x(next_x)
        if clamped_x != next_x:
            self.direction *= -1
        else:
            self.move(clamped_x, self.y())
        self.refresh_movement_state()

    def check_boundary_stuck(self):
        surface = self.get_surface_snapshot()
        if self.x() < surface.left_bound:
            self.move(surface.left_bound + 5, self.y())
            self.direction = 1
        elif self.x() > surface.right_bound:
            self.move(surface.right_bound - 5, self.y())
            self.direction = -1
        self.refresh_movement_state()

    def apply_reaction(self, preferred_moods, is_negative=False):
        forbidden = ["happy", "smile", "confidence", "cool", "glance"] if is_negative else []
        result = self.asset_manager.get_safe_reaction_result("idle", preferred_moods, forbidden=forbidden)
        if self.apply_animation_result("idle", result):
            self.state = "idle"
            self.state_timer = 80
            self.reset_stationary_move_mode()

    def change_state(self, purpose, action_type=None):
        if (
            purpose in {"idle", "move"} and
            action_type and
            hasattr(self, "get_negative_afterglow_preferences")
        ):
            preferred_moods, forbidden_moods = self.get_negative_afterglow_preferences()
            if preferred_moods:
                for mood_tag in preferred_moods:
                    frames = self.asset_manager.get_specific_frames(
                        purpose,
                        action_type,
                        mood_tag,
                        mood_score=None,
                    )
                    if frames and self.apply_animation_result(purpose, (frames, action_type, mood_tag)):
                        return
                result = self.asset_manager.get_frames_for_action_by_preferences(
                    purpose,
                    action_type,
                    preferred_moods,
                    forbidden=forbidden_moods,
                    mood_score=None,
                )
                if self.apply_animation_result(purpose, result):
                    return
        result = self.asset_manager.get_frames_by_score(purpose, action_type, self.mood_score, is_adult=self.is_adult)
        if result:
            frames, selected_action_type, selected_mood_tag = result
            action_overrides = get_idle_action_override(
                getattr(self, "name", ""),
                current_purpose=getattr(self, "current_purpose", ""),
                current_action_tag=getattr(self, "current_action_tag", ""),
                next_purpose=purpose,
                next_action_tag=selected_action_type,
            )
            for fallback_action_type in action_overrides:
                fallback_result = self.asset_manager.get_frames_for_action_by_score(
                    purpose,
                    fallback_action_type,
                    mood_score=self.mood_score,
                    is_adult=self.is_adult,
                )
                if fallback_result:
                    result = fallback_result
                    break
        self.apply_animation_result(purpose, result)

    def resolve_collision(self, all_pets):
        if self.should_ignore_collision():
            return
        now = app_now()
        my_center = self.geometry().center()
        neighbors = []
        neighbor_pets = []
        for other in all_pets:
            if other == self or other.should_ignore_collision():
                continue
            other_center = other.geometry().center()
            neighbors.append(
                CollisionSnapshot(
                    center_x=other_center.x(),
                    center_y=other_center.y(),
                    radius=other.radius,
                    mass=other.mass,
                    is_adult=other.is_adult,
                )
            )
            neighbor_pets.append(other)

        resolution = compute_collision_resolution(
            subject=CollisionSnapshot(
                center_x=my_center.x(),
                center_y=my_center.y(),
                radius=self.radius,
                mass=self.mass,
                is_adult=self.is_adult,
            ),
            neighbors=neighbors,
            mood_score=self.mood_score,
        )
        for index in resolution.colliding_adult_indices:
            neighbor_pets[index].mood_score = min(100, neighbor_pets[index].mood_score + 0.01)
        if resolution.delta_x:
            self.collision_displaced_until = app_now() + 0.25
            if self.perched_window_hwnd and self.apply_window_perch_collision(resolution.delta_x):
                return
            self.move(self.x() + resolution.delta_x, self.y())

    def trigger_care_event(self, child):
        spec = self.select_interaction_animation(child)
        if spec:
            self.begin_hidden_interaction(child, spec, app_now())
        else:
            self.begin_companion_care(child, app_now())

    def finish_care(self, child=None):
        self.finish_care_mode(success=True)

    def enterEvent(self, event):
        self.fade_anim.setStartValue(self.bar_opacity)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()

    def leaveEvent(self, event):
        self.fade_anim.setStartValue(self.bar_opacity)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

    def mousePressEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(app_now()) or self.is_offer_locked(app_now()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self.flight_mode != "none":
                self.stop_window_flight(apply_cooldown=False)
            self.dragging = True
            self.vy = 0
            self.fall_origin_y = None
            self.drag_start_time = time.time()
            self.drag_pos = event.globalPosition().toPoint() - self.pos()
            self.apply_drag_animation()
            self.refresh_movement_state()

    def mouseMoveEvent(self, event):
        if self.dragging:
            if self.perched_window_hwnd:
                self.detach_from_window_surface()
            target_pos = event.globalPosition().toPoint() - self.drag_pos
            clamped_x, clamped_y = DesktopGeometry.clamp_drag_position(self, target_pos.x(), target_pos.y())
            self.move(clamped_x, clamped_y)
            self.refresh_movement_state()

    def mouseReleaseEvent(self, event):
        if self.is_angry_locked or self.care_mode != "none" or self.is_under_care(app_now()) or self.is_offer_locked(app_now()):
            return
        if event.button() == Qt.MouseButton.LeftButton:
            duration = time.time() - self.drag_start_time
            self.dragging = False
            if duration >= 0.2 and self.try_snap_to_window_surface():
                self.refresh_movement_state()
                return
            decision = decide_release_interaction(duration, self.click_count)
            if decision.kind == CLICK_RELEASE:
                self.click_count = decision.next_click_count
                if decision.starts_click_reset_timer:
                    self.click_reset_timer.start(3000)
                self.state, self.state_timer = "idle", 100
                self.mood_score = max(0, min(100, self.mood_score + decision.mood_delta))
                if decision.triggers_angry_lock:
                    self.is_angry_locked = True
                    self.setCursor(Qt.CursorShape.ForbiddenCursor)
                    self.apply_reaction(["scold", "angry"], is_negative=True)
                    self.lock_timer.start(5000)
                else:
                    self.pop_heart()
                    self.apply_reaction(["happy", "smile"])
            elif decision.kind == LONG_HOLD_RELEASE:
                self.mood_score = max(0, min(100, self.mood_score + decision.mood_delta))
                self.apply_reaction(["scold", "hard-cry", "exhausted"], is_negative=True)
            else:
                self.change_state("idle")
            self.refresh_movement_state()

    def is_offer_locked(self, now=None):
        now = app_now() if now is None else float(now)
        return (
            getattr(self, "offer_scene_kind", "none") != "none" or
            float(getattr(self, "offer_locked_until", 0.0) or 0.0) > now
        )

    def is_scene_animation_locked(self, now=None):
        now = app_now() if now is None else float(now)
        if self.is_offer_locked(now):
            return True
        if getattr(self, "care_mode", "none") != "none":
            return True
        is_under_care = getattr(self, "is_under_care", None)
        return bool(is_under_care(now)) if callable(is_under_care) else False


for _state_attr, _field_names in PET_STATE_PROXY_FIELDS.items():
    for _field_name in _field_names:
        setattr(TanukiPet, _field_name, forwarded_state_property(_state_attr, _field_name))
