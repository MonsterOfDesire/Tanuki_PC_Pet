import random

from PyQt6.QtWidgets import QApplication

from .geometry import get_total_virtual_geometry
from .pet_social_catalog import (
    get_adult_companion_candidates as catalog_get_adult_companion_candidates,
    get_child_comfort_candidates as catalog_get_child_comfort_candidates,
    get_child_recovery_candidates as catalog_get_child_recovery_candidates,
    get_expression_preferred_moods as catalog_get_expression_preferred_moods,
    get_idle_candidates as catalog_get_idle_candidates,
    get_move_candidates as catalog_get_move_candidates,
)
from .pet_intent_rules import INTENT_AMBIENT_IDLE, INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION, INTENT_RANDOM_ROAM
from .pet_ambient_mood_rules import (
    resolve_solitude_event,
)
from .pet_observe_rules import (
    OBSERVE_REENTRY_COOLDOWN,
    POST_OBSERVE_INTERACTION_MAX_DISTANCE,
    resolve_observe_plan,
    resolve_observe_reentry_cooldown,
    resolve_observe_same_target_cooldown,
    resolve_observe_start_decision,
    resolve_observe_target_notice_decision,
    resolve_post_observe_interaction_candidate,
    resolve_post_observe_escape,
    should_pause_observe_backoff,
)
from .pet_social_log_rules import get_social_log_template_count, resolve_social_log_event_plan
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
    build_care_interaction_mood_candidates,
    can_mimic_socially,
    is_distressed_state,
    parse_interaction_action,
    choose_preferred_care_adult_name,
    resolve_care_interaction_motion_order,
    should_preserve_candidate_animation,
)
from .runtime import app_now, get_pet_logic_step_count, get_pet_logic_step_scale


class PetSocialCareMixin:
    NEGATIVE_AFTERGLOW_DEFAULT_PREFERRED_MOODS = ("hard-cry", "cry", "sad", "scared", "think")
    NEGATIVE_AFTERGLOW_DEFAULT_FORBIDDEN_MOODS = (
        "happy",
        "smile",
        "relief",
        "calm",
        "confidence",
        "cool",
        "glance",
    )
    RESCUE_MIN_SPEED_FLOOR = 5.0

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
        is_offer_locked = getattr(self, "is_offer_locked", None)
        offer_locked = (
            bool(is_offer_locked(now))
            if callable(is_offer_locked)
            else float(getattr(self, "offer_locked_until", 0.0) or 0.0) > now
        )
        return (
            self.dragging or
            self.vy != 0 or
            not self.isVisible() or
            self.flight_mode != "none" or
            self.is_hugging or
            self.care_mode != "none" or
            self.care_partner is not None or
            self.is_under_care(now) or
            offer_locked
        )

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood = result
        if not frames:
            return False
        tsuyoshi_side_stand_armed = bool(getattr(self, "idle_side_stand_armed", False))
        if (
            getattr(self, "name", "") == "Tsurumaru Tsuyoshi" and
            purpose == "idle" and
            action_type == "side_stand" and
            not tsuyoshi_side_stand_armed
        ):
            fallback = self.asset_manager.get_specific_frames("idle", "side_ready", mood, mood_score=self.mood_score)
            if fallback:
                frames = fallback
                action_type = "side_ready"
            else:
                fallback_result = self.asset_manager.get_frames_for_action_by_score(
                    "idle",
                    "side_ready",
                    self.mood_score,
                    is_adult=getattr(self, "is_adult", False),
                )
                if fallback_result:
                    frames, action_type, mood = fallback_result
        self.current_frames = frames
        self.frame_index = 0
        if hasattr(self, "animation_step_budget"):
            self.animation_step_budget = 0.0
        animation_stepper = getattr(self, "animation_stepper", None)
        if animation_stepper is not None:
            animation_stepper.reset()
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood
        if getattr(self, "name", "") == "Tsurumaru Tsuyoshi" and purpose == "idle":
            if action_type == "side_ready":
                self.idle_side_stand_armed = True
            elif action_type == "side_stand":
                self.idle_side_stand_armed = False
            else:
                self.idle_side_stand_armed = False
        return True

    def change_state_candidates(self, candidates, context=None):
        if self.should_apply_negative_afterglow_to_candidates(candidates):
            preferred_moods, forbidden_moods = self.get_negative_afterglow_preferences()
            if preferred_moods and self.change_state_candidates_with_preferences(
                candidates,
                preferred_moods,
                forbidden=forbidden_moods,
                context=context,
                ignore_mood_band=True,
            ):
                return True
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

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None, ignore_mood_band=False):
        mood_score = None if ignore_mood_band else self.mood_score
        for mood_tag in preferred_moods:
            for purpose, action_type in candidates:
                frames = self.asset_manager.get_specific_frames(
                    purpose,
                    action_type,
                    mood_tag,
                    mood_score=mood_score,
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
                mood_score=mood_score,
                context=context,
            )
            if self.apply_animation_result(purpose, result):
                return True
        return False

    def normalize_animation_purposes(self, purposes):
        if not purposes:
            return ()
        if isinstance(purposes, str):
            return (purposes,)
        return tuple(purpose for purpose in purposes if purpose)

    def animation_purpose_matches(self, expected_purposes, current_purpose):
        purposes = self.normalize_animation_purposes(expected_purposes)
        if not purposes:
            return True
        return current_purpose in purposes

    def current_animation_matches_context(self, purpose, context, preferred_moods=None, forbidden=None, ignore_mood_band=False):
        if not context:
            return False
        asset_manager = getattr(self, "asset_manager", None)
        if asset_manager is None:
            return False
        current_purpose = getattr(self, "current_purpose", "")
        current_action = getattr(self, "current_action_tag", "")
        current_mood = getattr(self, "current_mood_tag", "")
        if not self.animation_purpose_matches(purpose, current_purpose):
            return False
        if forbidden and current_mood in set(forbidden):
            return False
        frames = asset_manager.get_specific_frames(
            current_purpose,
            current_action,
            current_mood,
            mood_score=None if ignore_mood_band else getattr(self, "mood_score", None),
            context=context,
        )
        return bool(frames)

    def change_state_for_context_with_preferences(
        self,
        purpose,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        asset_manager = getattr(self, "asset_manager", None)
        if asset_manager is None:
            return False
        if preserve and self.current_animation_matches_context(
            purpose,
            context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            ignore_mood_band=ignore_mood_band,
        ):
            return True
        selector = getattr(asset_manager, "get_contextual_result", None)
        if not callable(selector):
            return False
        result = selector(
            purpose,
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=None if ignore_mood_band else getattr(self, "mood_score", None),
            ordered_preferences=True,
        )
        if not result:
            return False
        frames, action_type, mood_tag = result
        return self.apply_animation_result(purpose, (frames, action_type, mood_tag))

    def change_state_for_context_purposes_with_preferences(
        self,
        purposes,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        asset_manager = getattr(self, "asset_manager", None)
        normalized_purposes = self.normalize_animation_purposes(purposes)
        if asset_manager is None or not normalized_purposes:
            return False
        if preserve and self.current_animation_matches_context(
            normalized_purposes,
            context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            ignore_mood_band=ignore_mood_band,
        ):
            return True
        selector = getattr(asset_manager, "get_contextual_result_for_purposes", None)
        if not callable(selector):
            return False
        result = selector(
            normalized_purposes,
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=None if ignore_mood_band else getattr(self, "mood_score", None),
            ordered_preferences=True,
        )
        if not result:
            return False
        frames, purpose, action_type, mood_tag = result
        return self.apply_animation_result(purpose, (frames, action_type, mood_tag))

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
        if getattr(self, "name", "") in {"Symboli Rudolf", "Sirius Symboli"}:
            return max(self.RESCUE_MIN_SPEED_FLOOR, self.get_base_speed())
        return self.get_base_speed()

    def get_care_approach_speed_scale(self):
        if getattr(self, "name", "") in {"Symboli Rudolf", "Sirius Symboli"}:
            return 1.6
        return 1.0

    def get_random_animation_context(self):
        expression_context = getattr(self, "expression_animation_context", "ambient")
        if expression_context in {"relation_watch", "relation_close"}:
            return [expression_context, "random"]
        return "random"

    def get_expression_animation_preferences(self):
        if (
            getattr(self, "care_mode", "none") != "none" or
            getattr(self, "offer_scene_kind", "none") != "none"
        ):
            preferred = catalog_get_expression_preferred_moods(
                getattr(self, "expression_animation_context", "ambient")
            )
            return preferred, (), False
        negative_afterglow_moods, forbidden_moods = self.get_negative_afterglow_preferences()
        if negative_afterglow_moods:
            return list(negative_afterglow_moods), tuple(forbidden_moods), True
        preferred = catalog_get_expression_preferred_moods(
            getattr(self, "expression_animation_context", "ambient")
        )
        return preferred, (), False

    def get_expression_preferred_moods(self):
        preferred_moods, _forbidden_moods, _ignore_mood_band = self.get_expression_animation_preferences()
        return preferred_moods

    def is_negative_afterglow_active(self, now=None):
        if now is None:
            now = app_now()
        return float(getattr(self, "negative_afterglow_until", 0.0) or 0.0) > float(now)

    def get_negative_afterglow_preferences(self, now=None):
        if not self.is_negative_afterglow_active(now):
            return (), ()
        preferred = tuple(
            getattr(self, "negative_afterglow_preferred_moods", ())
            or self.NEGATIVE_AFTERGLOW_DEFAULT_PREFERRED_MOODS
        )
        forbidden = tuple(
            getattr(self, "negative_afterglow_forbidden_moods", ())
            or self.NEGATIVE_AFTERGLOW_DEFAULT_FORBIDDEN_MOODS
        )
        return preferred, forbidden

    def should_apply_negative_afterglow_to_candidates(self, candidates, now=None):
        if not self.is_negative_afterglow_active(now):
            return False
        if (
            getattr(self, "social_mode", "none") != "none" or
            getattr(self, "care_mode", "none") != "none" or
            getattr(self, "offer_scene_kind", "none") != "none" or
            self.is_under_care(now if now is not None else app_now())
        ):
            return False
        return any(purpose in {"idle", "move"} for purpose, _ in list(candidates or ()))

    def is_care_blocked_by_negative_afterglow(self, now=None):
        if now is None:
            now = app_now()
        return (
            self.is_negative_afterglow_active(now) and
            float(getattr(self, "negative_afterglow_care_block_until", 0.0) or 0.0) > float(now)
        )

    def start_negative_afterglow(
        self,
        duration=5.0,
        preferred_moods=None,
        forbidden_moods=None,
        now=None,
        block_care=False,
    ):
        if now is None:
            now = app_now()
        afterglow_until = float(now) + float(duration)
        self.negative_afterglow_until = max(
            float(getattr(self, "negative_afterglow_until", 0.0) or 0.0),
            afterglow_until,
        )
        if block_care:
            self.negative_afterglow_care_block_until = max(
                float(getattr(self, "negative_afterglow_care_block_until", 0.0) or 0.0),
                afterglow_until,
            )
        self.negative_afterglow_preferred_moods = tuple(
            preferred_moods or self.NEGATIVE_AFTERGLOW_DEFAULT_PREFERRED_MOODS
        )
        self.negative_afterglow_forbidden_moods = tuple(
            forbidden_moods or self.NEGATIVE_AFTERGLOW_DEFAULT_FORBIDDEN_MOODS
        )

    def trigger_ambient_mood_event(self, decision, cooldown_attr, now=None):
        if decision is None or not getattr(decision, "should_trigger", False):
            return False
        if now is None:
            now = app_now()
        self.mood_score = max(0.0, float(self.mood_score) - float(decision.mood_delta))
        start_negative_afterglow = getattr(self, "start_negative_afterglow", None)
        if callable(start_negative_afterglow) and float(getattr(decision, "afterglow_duration", 0.0) or 0.0) > 0.0:
            start_negative_afterglow(
                duration=float(decision.afterglow_duration),
                preferred_moods=list(getattr(decision, "preferred_moods", ()) or ("sad", "think")),
                forbidden_moods=list(getattr(decision, "forbidden_moods", ()) or self.NEGATIVE_AFTERGLOW_DEFAULT_FORBIDDEN_MOODS),
                now=now,
            )
        setattr(self, cooldown_attr, float(now) + float(getattr(decision, "cooldown_seconds", 0.0) or 0.0))
        if hasattr(self, "sync_mood_state_with_score"):
            self.sync_mood_state_with_score()
        self.apply_reaction(list(getattr(decision, "preferred_moods", ()) or ("sad", "think")), is_negative=True)
        return True

    def update_ambient_mood_events(self, now):
        visible_pet_count = int(getattr(self, "perception_visible_adult_count", 0) or 0) + int(
            getattr(self, "perception_visible_child_count", 0) or 0
        )
        if float(getattr(self, "last_company_seen_at", 0.0) or 0.0) <= 0.0:
            self.last_company_seen_at = float(now)

        if visible_pet_count > 0:
            self.last_company_seen_at = float(now)

        if (
            not self.isVisible() or
            getattr(self, "dragging", False) or
            getattr(self, "flight_mode", "none") != "none" or
            getattr(self, "social_mode", "none") != "none" or
            getattr(self, "care_mode", "none") != "none" or
            getattr(self, "offer_scene_kind", "none") != "none" or
            self.is_under_care(now) or
            getattr(self, "is_hugging", False)
        ):
            return False

        solitude_decision = resolve_solitude_event(
            is_adult=getattr(self, "is_adult", False),
            now=now,
            last_company_seen_at=getattr(self, "last_company_seen_at", 0.0),
            visible_pet_count=visible_pet_count,
            cooldown_until=getattr(self, "solitude_event_cooldown_until", 0.0),
            mood_score=getattr(self, "mood_score", 0.0),
        )
        if self.trigger_ambient_mood_event(solitude_decision, "solitude_event_cooldown_until", now=now):
            return True

        return False

    def clear_negative_afterglow(self):
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_care_block_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()

    def apply_expression_idle_behavior(self, random_context):
        if self.state != "idle":
            return False
        preferred_moods, forbidden_moods, ignore_mood_band = self.get_expression_animation_preferences()
        expression_context = getattr(self, "expression_animation_context", "ambient")
        if expression_context not in {"relation_watch", "relation_close"}:
            return False
        return self.change_state_for_context_with_preferences(
            "idle",
            expression_context,
            preferred_moods,
            forbidden=forbidden_moods,
            preserve=True,
            ignore_mood_band=ignore_mood_band,
        )

    def apply_post_observe_interaction_idle_behavior(self, preserve=True):
        if self.state != "idle":
            return False
        preferred_moods, forbidden_moods, ignore_mood_band = self.get_expression_animation_preferences()
        return self.change_state_for_context_purposes_with_preferences(
            ("idle", "move"),
            "post_observe",
            preferred_moods=preferred_moods,
            forbidden=forbidden_moods,
            preserve=preserve,
            ignore_mood_band=ignore_mood_band,
        )

    def enqueue_social_log_event_from_observe(
        self,
        *,
        now,
        target_name,
        source_context,
        roll=None,
        template_index=None,
    ):
        roll = random.random() if roll is None else float(roll)
        if template_index is None:
            template_count = get_social_log_template_count(source_context)
            template_index = random.randrange(template_count) if template_count > 0 else 0
        plan = resolve_social_log_event_plan(
            actor_name=getattr(self, "name", ""),
            target_name=target_name,
            source_context=source_context,
            now=now,
            cooldown_until=getattr(self, "social_log_event_cooldown_until", 0.0),
            roll=roll,
            template_index=template_index,
        )
        if not plan.should_emit:
            return False
        self.pending_social_log_event = {
            "occurred_at": float(now),
            "event_type": plan.event_type,
            "summary": plan.summary,
            "actor_name": getattr(self, "name", ""),
            "target_name": str(target_name or ""),
            "relation_delta": dict(plan.relation_delta),
            "tags": tuple(plan.tags),
            "metadata": dict(plan.metadata),
        }
        self.social_log_event_cooldown_until = plan.cooldown_until
        return True

    def clear_observe_intent(
        self,
        now=None,
        blocked_target_name="",
        blocked_target_dx=0.0,
        escape_roll=None,
        allow_social_log_event=True,
    ):
        previous_target_name = blocked_target_name
        if not previous_target_name and self.intent_kind in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION}:
            previous_target_name = self.intent_target_name
        source_context = getattr(self, "intent_context", "")
        source_intent_kind = getattr(self, "intent_kind", "")
        if source_context not in {"observe", "post_observe_interaction"}:
            source_context = source_intent_kind
        if now is not None and previous_target_name and allow_social_log_event:
            self.enqueue_social_log_event_from_observe(
                now=float(now),
                target_name=previous_target_name,
                source_context=source_context,
            )
        visible_pet_count = int(getattr(self, "perception_visible_adult_count", 0) or 0)
        visible_pet_count += int(getattr(self, "perception_visible_child_count", 0) or 0)
        next_streak_count = 0
        self.intent_locked_until = 0.0
        if self.intent_kind in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION}:
            self.intent_kind = INTENT_AMBIENT_IDLE
            self.intent_target_name = ""
            self.intent_priority = 10
            self.intent_source = "ambient"
            self.intent_reason = ""
            self.intent_context = "ambient_idle"
        if now is not None:
            self.intent_reconsider_after = max(
                float(self.intent_reconsider_after or 0.0),
                float(now) + OBSERVE_REENTRY_COOLDOWN,
            )
            if previous_target_name:
                same_target_cooldown, streak_target_name, streak_count = resolve_observe_same_target_cooldown(
                    previous_target_name=previous_target_name,
                    streak_target_name=getattr(self, "observe_streak_target_name", ""),
                    streak_count=getattr(self, "observe_streak_count", 0),
                    visible_pet_count=visible_pet_count,
                )
                next_streak_count = streak_count
                self.intent_reconsider_after = max(
                    float(self.intent_reconsider_after or 0.0),
                    float(now) + resolve_observe_reentry_cooldown(
                        visible_pet_count=visible_pet_count,
                        streak_count=streak_count,
                    ),
                )
                self.observe_blocked_target_name = previous_target_name
                self.observe_blocked_until = float(now) + same_target_cooldown
                self.observe_streak_target_name = streak_target_name
                self.observe_streak_count = streak_count
        if previous_target_name:
            self.relationship_focus_target_name = ""
            self.relationship_focus_familiarity = 0.0
            self.relationship_focus_trust = 0.0
            self.relationship_focus_attachment = 0.0
            self.relationship_focus_tension = 0.0
            self.expression_animation_context = "ambient"
            self.expression_relation_overlay = "none"
            self.expression_focus_target_name = ""
            self.expression_posture_bias = "neutral"
            self.expression_spacing_bias = "neutral"
            self.expression_look_at_target = False
        self.state_timer = 0
        if self.current_purpose in {"idle", "move"}:
            self.current_purpose = ""
        escape_roll = random.random() if escape_roll is None else float(escape_roll)
        should_escape, escape_direction, escape_state_timer = resolve_post_observe_escape(
            previous_target_name=previous_target_name,
            previous_target_dx=blocked_target_dx,
            current_direction=getattr(self, "direction", 1),
            visible_pet_count=visible_pet_count,
            streak_count=next_streak_count,
            roll=escape_roll,
        )
        if should_escape:
            self.intent_kind = INTENT_RANDOM_ROAM
            self.intent_priority = 20
            self.intent_source = "ambient"
            self.intent_context = "post_observe_escape"
            self.intent_reason = "post_observe_escape"
            self.state = "move"
            self.direction = escape_direction
            self.state_timer = max(int(self.state_timer or 0), int(escape_state_timer))
            reset_stationary = getattr(self, "reset_stationary_move_mode", None)
            if callable(reset_stationary):
                reset_stationary()

    def start_post_observe_interaction(self, target, now, interaction_context, lock_duration):
        if self.is_negative_afterglow_active(now):
            return False
        target_name = getattr(target, "name", "")
        if not target_name:
            return False
        lock_until = float(now) + float(lock_duration or 0.0)
        self.intent_kind = INTENT_POST_OBSERVE_INTERACTION
        self.intent_target_name = target_name
        self.intent_locked_until = lock_until
        self.intent_reconsider_after = max(float(self.intent_reconsider_after or 0.0), lock_until)
        self.intent_priority = 16
        self.intent_source = "ambient"
        self.intent_context = "post_observe_interaction"
        self.intent_reason = "post_observe_interaction"
        self.state = "idle"
        self.state_timer = 0
        self.current_purpose = ""
        self.relationship_focus_target_name = target_name
        self.expression_animation_context = interaction_context
        self.expression_focus_target_name = target_name
        self.expression_look_at_target = True
        if interaction_context == "relation_close":
            self.expression_relation_overlay = "soft_star"
            self.expression_posture_bias = "warm"
            self.expression_spacing_bias = "comfortable"
        else:
            self.expression_relation_overlay = "none"
            self.expression_posture_bias = "curious"
            self.expression_spacing_bias = "neutral"
        self.direction = -1 if target.x() < self.x() else 1
        self.apply_post_observe_interaction_idle_behavior(preserve=False)
        return True

    def update_post_observe_interaction_behavior(self, now, all_pets):
        if self.is_negative_afterglow_active(now):
            if self.intent_kind in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION}:
                self.clear_observe_intent(
                    now=now,
                    escape_roll=1.0,
                    allow_social_log_event=False,
                )
            return False
        if self.intent_kind != INTENT_POST_OBSERVE_INTERACTION or not self.intent_target_name:
            return False
        target_pet = self.get_visible_behavior_target(all_pets, self.intent_target_name)
        target_dx = ((target_pet.x() - self.x()) if target_pet else 0.0)
        target_distance = self.distance_to(target_pet) if target_pet else 0.0
        target_still_near = (
            target_pet is not None and
            float(target_distance) > 0.0 and
            float(target_distance) <= POST_OBSERVE_INTERACTION_MAX_DISTANCE
        )
        if (
            target_pet is None or
            float(self.intent_locked_until or 0.0) <= float(now) or
            float(target_distance) <= 0.0 or
            float(target_distance) > POST_OBSERVE_INTERACTION_MAX_DISTANCE
        ):
            self.clear_observe_intent(
                now=now,
                blocked_target_name=self.intent_target_name,
                blocked_target_dx=target_dx,
                allow_social_log_event=target_still_near,
            )
            return False

        self.state = "idle"
        self.direction = -1 if target_dx < 0 else 1
        if not self.apply_post_observe_interaction_idle_behavior():
            random_context = self.get_random_animation_context()
            self.ensure_candidate_animation(
                self.expand_candidates_with_context("idle", self.get_idle_candidates(), context=random_context),
                context=random_context,
            )
        return True

    def is_observe_notice_target_busy(self, target_pet, now):
        if target_pet is None or not target_pet.isVisible():
            return True
        target_is_under_care = False
        is_under_care = getattr(target_pet, "is_under_care", None)
        if callable(is_under_care):
            target_is_under_care = bool(is_under_care(now))
        return bool(
            getattr(target_pet, "dragging", False) or
            getattr(target_pet, "is_angry_locked", False) or
            getattr(target_pet, "is_recovering", False) or
            getattr(target_pet, "flight_mode", "none") != "none" or
            getattr(target_pet, "perched_window_hwnd", 0) or
            getattr(target_pet, "social_mode", "none") != "none" or
            getattr(target_pet, "care_mode", "none") != "none" or
            target_is_under_care or
            getattr(target_pet, "offer_scene_kind", "none") != "none" or
            getattr(target_pet, "intent_kind", "") in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION}
        )

    def maybe_notify_observe_target(self, target_pet, now, visible_pet_count):
        if target_pet is None:
            return False
        decision = resolve_observe_target_notice_decision(
            now=now,
            target_busy=self.is_observe_notice_target_busy(target_pet, now),
            cooldown_until=getattr(target_pet, "observe_notice_cooldown_until", 0.0),
            visible_pet_count=visible_pet_count,
            roll=random.random(),
        )
        if not decision.should_notice:
            return False

        target_pet.observe_notice_cooldown_until = float(now) + float(decision.cooldown)
        target_pet.intent_reconsider_after = max(
            float(getattr(target_pet, "intent_reconsider_after", 0.0) or 0.0),
            float(now) + float(decision.duration),
        )
        target_pet.state = "idle"
        target_pet.state_timer = max(int(getattr(target_pet, "state_timer", 0) or 0), int(decision.duration * 30))
        target_pet.current_purpose = ""
        target_pet.relationship_focus_target_name = getattr(self, "name", "")
        target_pet.expression_animation_context = (
            "relation_close"
            if getattr(target_pet, "expression_animation_context", "ambient") == "relation_close" else
            "relation_watch"
        )
        target_pet.expression_focus_target_name = getattr(self, "name", "")
        target_pet.expression_look_at_target = True
        target_dx = self.x() - target_pet.x()
        if target_dx:
            target_pet.direction = -1 if target_dx < 0 else 1
        get_random_animation_context = getattr(target_pet, "get_random_animation_context", None)
        random_context = get_random_animation_context() if callable(get_random_animation_context) else "random"
        apply_expression_idle_behavior = getattr(target_pet, "apply_expression_idle_behavior", None)
        if callable(apply_expression_idle_behavior):
            apply_expression_idle_behavior(random_context)
        return True

    def update_observe_behavior(self, now, all_pets):
        if self.is_negative_afterglow_active(now):
            if self.intent_kind in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION}:
                self.clear_observe_intent(
                    now=now,
                    escape_roll=1.0,
                    allow_social_log_event=False,
                )
            return False
        locked_target_name = self.intent_target_name if self.intent_kind == INTENT_OBSERVE else ""
        lock_active = (
            self.intent_kind == INTENT_OBSERVE and
            bool(locked_target_name) and
            float(self.intent_locked_until or 0.0) > float(now)
        )
        preferred_target_name = (
            locked_target_name
            if lock_active
            else self.relationship_focus_target_name
        )
        target_pet = self.get_visible_behavior_target(all_pets, preferred_target_name)
        visible_pet_count = int(getattr(self, "perception_visible_adult_count", 0) or 0)
        visible_pet_count += int(getattr(self, "perception_visible_child_count", 0) or 0)
        observe_streak_count = (
            int(getattr(self, "observe_streak_count", 0) or 0)
            if preferred_target_name and preferred_target_name == getattr(self, "observe_streak_target_name", "")
            else 0
        )
        if (
            not lock_active and
            preferred_target_name and
            getattr(self, "expression_animation_context", "ambient") in {"relation_watch", "relation_close"} and
            float(self.intent_reconsider_after or 0.0) <= float(now)
        ):
            start_decision = resolve_observe_start_decision(
                expression_animation_context=self.expression_animation_context,
                visible_pet_count=visible_pet_count,
                streak_count=observe_streak_count,
                roll=random.random(),
            )
            if not start_decision.should_start:
                self.intent_locked_until = 0.0
                self.intent_kind = INTENT_AMBIENT_IDLE
                self.intent_target_name = ""
                self.intent_priority = 10
                self.intent_source = "ambient"
                self.intent_context = "ambient_idle"
                self.intent_reason = start_decision.reason
                self.intent_reconsider_after = max(
                    float(self.intent_reconsider_after or 0.0),
                    float(now) + float(start_decision.retry_cooldown or 0.0),
                )
                return False
        observe_plan = resolve_observe_plan(
            now=now,
            intent_kind=self.intent_kind,
            locked_target_name=locked_target_name,
            intent_locked_until=self.intent_locked_until,
            intent_reconsider_after=self.intent_reconsider_after,
            focus_target_name=self.relationship_focus_target_name,
            expression_animation_context=self.expression_animation_context,
            target_visible=target_pet is not None,
            target_distance=(self.distance_to(target_pet) if target_pet else 0.0),
            target_dx=((target_pet.x() - self.x()) if target_pet else 0.0),
        )
        if observe_plan.clear_lock:
            target_distance = self.distance_to(target_pet) if target_pet else 0.0
            target_still_near = (
                target_pet is not None and
                float(target_distance) > 0.0 and
                float(target_distance) <= POST_OBSERVE_INTERACTION_MAX_DISTANCE
            )
            interaction_candidate = resolve_post_observe_interaction_candidate(
                previous_target_name=locked_target_name,
                target_visible=target_pet is not None,
                target_distance=target_distance,
                expression_animation_context=self.expression_animation_context,
                visible_pet_count=visible_pet_count,
                streak_count=observe_streak_count,
                roll=random.random(),
            )
            if interaction_candidate.should_start and target_pet is not None:
                return self.start_post_observe_interaction(
                    target_pet,
                    now,
                    interaction_candidate.interaction_context,
                    interaction_candidate.lock_duration,
                )
            self.clear_observe_intent(
                now=now,
                blocked_target_name=locked_target_name,
                blocked_target_dx=((target_pet.x() - self.x()) if target_pet else 0.0),
                allow_social_log_event=target_still_near,
            )
        if not observe_plan.handled:
            return False

        self.intent_kind = INTENT_OBSERVE
        self.intent_target_name = observe_plan.target_name
        self.intent_locked_until = observe_plan.lock_until
        self.intent_reconsider_after = max(
            float(self.intent_reconsider_after or 0.0),
            float(observe_plan.lock_until) + OBSERVE_REENTRY_COOLDOWN,
        )
        self.intent_source = "ambient"
        self.intent_context = "observe"
        self.intent_reason = observe_plan.reason
        if not lock_active:
            self.maybe_notify_observe_target(target_pet, now, visible_pet_count)
        if observe_plan.desired_direction:
            self.direction = observe_plan.desired_direction

        random_context = self.get_random_animation_context()
        target_collision_displaced_until = (
            float(getattr(target_pet, "collision_displaced_until", 0.0))
            if target_pet is not None else 0.0
        )
        if observe_plan.should_backoff and should_pause_observe_backoff(
            now=now,
            subject_collision_displaced_until=getattr(self, "collision_displaced_until", 0.0),
            target_collision_displaced_until=target_collision_displaced_until,
        ):
            self.state = "idle"
            self.intent_reason = "observe_hold_collision_settle"
            if not self.apply_expression_idle_behavior(random_context):
                self.ensure_candidate_animation(
                    self.expand_candidates_with_context("idle", self.get_idle_candidates(), context=random_context),
                    context=random_context,
                )
            return True
        if observe_plan.should_backoff:
            self.state = "move"
            self.ensure_candidate_animation(
                self.expand_candidates_with_context("move", self.get_move_candidates(), context=random_context),
                context=random_context,
            )
            self.move_toward_x(
                self.x() + (observe_plan.desired_direction * observe_plan.backoff_offset),
                speed_scale=0.9,
                min_speed=1.2,
            )
            return True

        if observe_plan.should_hold_idle:
            self.state = "idle"
            if not self.apply_expression_idle_behavior(random_context):
                self.ensure_candidate_animation(
                    self.expand_candidates_with_context("idle", self.get_idle_candidates(), context=random_context),
                    context=random_context,
                )
            return True

        return False

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
            if (
                getattr(self, "name", "") == "Tsurumaru Tsuyoshi" and
                purpose == "idle" and
                context == "random" and
                action_type == "side_stand" and
                not bool(getattr(self, "idle_side_stand_armed", False))
            ):
                continue
            candidate = (purpose, action_type)
            if candidate not in seen:
                expanded.append(candidate)
                seen.add(candidate)
        return expanded

    def get_random_manifest_candidates(self, purpose, context="random"):
        return self.expand_candidates_with_context(purpose, (), context=context)

    def ensure_candidate_animation(self, candidates, context=None):
        ignore_mood_band = self.should_apply_negative_afterglow_to_candidates(candidates)
        frames = self.asset_manager.get_specific_frames(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            mood_score=None if ignore_mood_band else self.mood_score,
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
        ignore_mood_band = self.should_apply_negative_afterglow_to_candidates(candidates)
        frames = self.asset_manager.get_specific_frames(
            self.current_purpose,
            self.current_action_tag,
            self.current_mood_tag,
            mood_score=None if ignore_mood_band else self.mood_score,
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
            ignore_mood_band=ignore_mood_band,
        )

    def get_child_comfort_candidates(self):
        return catalog_get_child_comfort_candidates(self.name)

    def get_child_recovery_candidates(self):
        return catalog_get_child_recovery_candidates(self.name)

    def get_adult_companion_candidates(self):
        return catalog_get_adult_companion_candidates(self.name)

    def get_move_candidates(self):
        return catalog_get_move_candidates()

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
        self.mood_score = min(100, self.mood_score + (0.05 * get_pet_logic_step_scale(self)))
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

    def get_child_context_suffix(self, child):
        tokens = list(child.get_child_tokens()) if child is not None else []
        if not tokens:
            return ""
        return str(tokens[0]).strip().lower().replace(" ", "_")

    def get_care_approach_contexts(self, child):
        suffix = self.get_child_context_suffix(child)
        contexts = []
        if suffix:
            contexts.append(f"care_approach_{suffix}")
        contexts.append("care_approach")
        return contexts

    def apply_care_approach_animation(self, child):
        return self.change_state_for_context_with_preferences(
            "move",
            self.get_care_approach_contexts(child),
            preserve=True,
        )

    def get_care_interaction_contexts(self, motion, child):
        suffix = self.get_child_context_suffix(child)
        contexts = []
        if motion == "move":
            if suffix:
                contexts.append(f"moving_care_interaction_{suffix}")
            contexts.append("moving_care_interaction")
        else:
            if suffix:
                contexts.append(f"care_interaction_{suffix}")
            contexts.append("care_interaction")
        return contexts

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
            if hasattr(self, "animation_step_budget"):
                self.animation_step_budget = 0.0
            animation_stepper = getattr(self, "animation_stepper", None)
            if animation_stepper is not None:
                animation_stepper.reset()
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
        motion_order = resolve_care_interaction_motion_order(preferred_motion, random.random())
        mood_candidates = build_care_interaction_mood_candidates(child.current_mood_tag)
        for motion in motion_order:
            matches = []
            interaction_context = self.get_care_interaction_contexts(motion, child)
            for action_key in actions:
                parsed = parse_interaction_action(action_key)
                if not parsed:
                    continue
                action_motion, _, child_token = parsed
                if action_motion != motion or child_token not in child_tokens:
                    continue
                randomized_moods = list(mood_candidates)
                random.shuffle(randomized_moods)
                for mood in randomized_moods:
                    frames = self.asset_manager.get_specific_frames(
                        "interaction",
                        action_key,
                        mood,
                        mood_score=None,
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
        step = max(1, int(base_speed * speed_scale)) * get_pet_logic_step_count(self)
        nx = target_x if abs(delta) <= step else self.x() + (step * self.direction)
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
                moving_step = (
                    max(1, int(round(self.get_distressed_move_speed()))) *
                    get_pet_logic_step_count(self)
                )
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
            self.apply_care_approach_animation(child)
            arrived = self.move_toward_x(
                decision.target_x,
                speed_scale=self.get_care_approach_speed_scale(),
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
            care_block_checker = getattr(pet, "is_care_blocked_by_negative_afterglow", None)
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
                care_blocked=bool(care_block_checker(now)) if callable(care_block_checker) else False,
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
        if self.is_negative_afterglow_active(now):
            if self.social_mode != "none":
                self.stop_social_mode(now, apply_cooldown=False)
            return False
        gate = SOCIAL_CARE_COORDINATOR.decide_social_gate(
            is_social_child=self.name in self.CHILD_NAMES,
            dragging=self.dragging,
        )
        if gate.action != SOCIAL_DECISION_CONTINUE:
            return False

        rudolf = next((p for p in all_pets if p.name == "Symboli Rudolf" and p.isVisible()), None)
        if self.social_mode != "none":
            self.social_timer_frames -= get_pet_logic_step_count(self)
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
