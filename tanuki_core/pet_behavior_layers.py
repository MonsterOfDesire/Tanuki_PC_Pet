import time
from dataclasses import replace

from .pet_intent_rules import (
    INTENT_OBSERVE,
    INTENT_POST_OBSERVE_INTERACTION,
    SLEEP_JOIN_INTENT_KINDS,
    derive_current_intent,
)
from .pet_perception_rules import NearbyPetObservation, summarize_perception
from .pet_relationship_rules import (
    RelationshipObservation,
    advance_relationship_entry,
    choose_relationship_focus,
    derive_expression_state,
    derive_relational_situation_tag,
)
from .pet_runtime_state import RelationshipEntry
from .runtime import SIM_CLOCK, app_now, get_pet_logic_step_scale
from .transformation_profiles import get_pet_form_key, pet_is_transforming
from .transformation_social_rules import (
    TRANSFORMED_RUDOLF_FOCUS_DISTANCE,
    TRANSFORMED_RUDOLF_NAME,
    resolve_transformed_rudolf_influence,
)


class PetBehaviorLayersMixin:
    def get_transformed_rudolf_influence(
        self,
        all_pets,
        *,
        blocked_target_name="",
    ):
        rudolf = next(
            (
                pet
                for pet in tuple(all_pets or ())
                if getattr(pet, "name", "")
                == TRANSFORMED_RUDOLF_NAME
            ),
            None,
        )
        return resolve_transformed_rudolf_influence(
            observer_name=getattr(self, "name", ""),
            observer_form=get_pet_form_key(self),
            target_name=getattr(rudolf, "name", ""),
            target_form=get_pet_form_key(rudolf),
            target_visible=bool(
                rudolf is not None
                and rudolf.isVisible()
                and not pet_is_transforming(rudolf)
            ),
            target_distance=(
                self.distance_to(rudolf) if rudolf is not None else 0.0
            ),
            blocked_target_name=blocked_target_name,
        )

    def _advance_refresh_scheduler(self, *, skip_attr, divisor_attr, divisor, force=False):
        current_divisor = max(1, int(getattr(self, divisor_attr, 1) or 1))
        if divisor != current_divisor:
            setattr(self, divisor_attr, divisor)
            setattr(self, skip_attr, 0)
        if force or divisor <= 1:
            setattr(self, divisor_attr, divisor)
            setattr(self, skip_attr, float(divisor))
            return True
        remaining = max(0.0, float(getattr(self, skip_attr, 0.0) or 0.0))
        if remaining <= 0:
            setattr(self, divisor_attr, divisor)
            setattr(self, skip_attr, float(divisor))
            return True
        remaining -= get_pet_logic_step_scale(self)
        if remaining > 1e-6:
            setattr(self, skip_attr, remaining)
            return False
        overshoot = max(0.0, -remaining)
        next_remaining = float(divisor) - (overshoot % float(divisor))
        if next_remaining <= 1e-6:
            next_remaining = float(divisor)
        setattr(self, skip_attr, next_remaining)
        return True

    def get_behavior_layer_refresh_divisor(self, speed=None):
        speed = float(SIM_CLOCK.speed if speed is None else speed)
        if speed >= 8.0:
            return 4
        if speed >= 4.0:
            return 2
        return 1

    def should_refresh_behavior_layers(self, force=False, speed=None):
        divisor = self.get_behavior_layer_refresh_divisor(speed=speed)
        return self._advance_refresh_scheduler(
            skip_attr="behavior_layer_refresh_skip_counter",
            divisor_attr="behavior_layer_refresh_divisor",
            divisor=divisor,
            force=force,
        )

    def get_high_level_ai_refresh_divisor(self, speed=None):
        speed = float(SIM_CLOCK.speed if speed is None else speed)
        if speed >= 8.0:
            return 4
        if speed >= 4.0:
            return 2
        return 1

    def should_refresh_high_level_ai(self, force=False, speed=None):
        divisor = self.get_high_level_ai_refresh_divisor(speed=speed)
        return self._advance_refresh_scheduler(
            skip_attr="high_level_ai_refresh_skip_counter",
            divisor_attr="high_level_ai_refresh_divisor",
            divisor=divisor,
            force=force,
        )

    def apply_offer_behavior_layer_override(self):
        if getattr(self, "offer_scene_kind", "none") == "none":
            return
        self.perception_situation_tag = "locked"
        self.expression_animation_context = "ambient"
        self.expression_relation_overlay = "none"
        self.expression_focus_target_name = ""
        self.expression_posture_bias = "neutral"
        self.expression_spacing_bias = "neutral"
        self.expression_look_at_target = False
        self.relationship_focus_target_name = ""
        self.relationship_focus_familiarity = 0.0
        self.relationship_focus_trust = 0.0
        self.relationship_focus_attachment = 0.0
        self.relationship_focus_tension = 0.0

    def get_visible_behavior_target(self, all_pets, target_name):
        if not target_name:
            return None
        for other in all_pets:
            if other == self or not other.isVisible():
                continue
            if other.name == target_name:
                return other
        return None

    def get_locked_observe_focus(self, all_pets, now=None):
        if now is None:
            now = app_now()
        if (
            self.intent_kind not in {INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION} or
            not self.intent_target_name or
            float(self.intent_locked_until or 0.0) <= float(now)
        ):
            return "", None, 0.0
        target = self.get_visible_behavior_target(all_pets, self.intent_target_name)
        if target is None:
            return self.intent_target_name, None, 0.0
        return self.intent_target_name, target, self.distance_to(target)

    def get_blocked_observe_target_name(self, now=None):
        if now is None:
            now = app_now()
        if (
            not self.observe_blocked_target_name or
            float(self.observe_blocked_until or 0.0) <= float(now)
        ):
            return ""
        return self.observe_blocked_target_name

    def get_behavior_layer_anchor(self):
        surface = self.get_surface_snapshot()
        if self.vy != 0 or self.flight_mode != "none":
            return "air", "air"
        if self.perched_window_hwnd:
            return "window_top", "window_top"
        if surface.on_floor:
            return "floor", "desktop_floor"
        return "air", "screen_space"

    def get_perception_window_flags(self):
        if not self.window_tracker or not self.isVisible() or self.dragging:
            return False, False
        actor_snapshot = self.window_tracker.build_actor_snapshot(self)
        perch_available = bool(
            self.perched_window_hwnd or
            self.window_tracker.find_drop_surface_for_actor(actor_snapshot)
        )
        flight_available = bool(
            self.flight_mode != "none" or
            self.window_tracker.find_flight_surface_for_actor(actor_snapshot)
        )
        return perch_available, flight_available

    def update_perception_state(self, all_pets):
        anchor, support_surface = self.get_behavior_layer_anchor()
        perch_available, flight_available = self.get_perception_window_flags()
        observations = []
        for other in all_pets:
            if other == self:
                continue
            observations.append(NearbyPetObservation(
                name=other.name,
                distance=self.distance_to(other),
                is_adult=other.is_adult,
                is_visible=other.isVisible(),
                is_distressed=(other.is_distressed() if other.isVisible() else False),
            ))
        snapshot = summarize_perception(
            observations,
            anchor=anchor,
            support_surface=support_surface,
            dragging=self.dragging,
            is_angry_locked=self.is_angry_locked,
            care_mode=self.care_mode,
            social_mode=self.social_mode,
            is_recovering=self.is_recovering,
            care_lock_active=self.is_under_care(app_now()),
            vertical_velocity=self.vy,
            is_adult=self.is_adult,
            window_perch_available=perch_available,
            window_flight_target_available=flight_available,
        )
        self.perception_anchor = snapshot.anchor
        self.perception_support_surface = snapshot.support_surface
        self.perception_nearest_visible_pet_name = snapshot.nearest_visible_pet_name
        self.perception_nearest_visible_pet_distance = snapshot.nearest_visible_pet_distance
        self.perception_nearest_distressed_child_name = snapshot.nearest_distressed_child_name
        self.perception_nearest_distressed_child_distance = snapshot.nearest_distressed_child_distance
        self.perception_visible_adult_count = snapshot.visible_adult_count
        self.perception_visible_child_count = snapshot.visible_child_count
        self.perception_window_perch_available = snapshot.window_perch_available
        self.perception_window_flight_target_available = snapshot.window_flight_target_available
        self.perception_situation_tag = snapshot.situation_tag

    def update_relationship_state(self, all_pets, now=None):
        if now is None:
            now = app_now()
        social_target_name = getattr(self.social_target, "name", "") if self.social_target else ""
        care_target_name = getattr(self.care_target, "name", "") if self.care_target else ""
        care_partner_name = getattr(self.care_partner, "name", "") if self.care_partner else ""
        active_care_name = care_target_name or care_partner_name
        observe_target_name, observe_target, observe_target_distance = self.get_locked_observe_focus(all_pets, now=now)
        blocked_target_name = self.get_blocked_observe_target_name(now=now)
        entries = dict(self.relationship_entries)

        for other in all_pets:
            if other == self or not other.isVisible():
                continue
            observation = RelationshipObservation(
                name=other.name,
                distance=self.distance_to(other),
                same_anchor=(getattr(other.movement_state, "anchor", "") == self.perception_anchor),
                is_visible=other.isVisible(),
                social_active=(self.social_mode != "none" and other.name == social_target_name),
                care_active=(
                    (self.care_mode != "none" and other.name == active_care_name) or
                    (self.is_under_care(now) and other.name == active_care_name)
                ),
            )
            entry = entries.get(observation.name, RelationshipEntry())
            entries[observation.name] = advance_relationship_entry(
                entry,
                distance=observation.distance,
                same_anchor=observation.same_anchor,
                social_active=observation.social_active,
                care_active=observation.care_active,
                now=now,
            )

        transformed_rudolf = self.get_transformed_rudolf_influence(
            all_pets,
            blocked_target_name=blocked_target_name,
        )
        nearest_visible_pet_name = (
            transformed_rudolf.target_name
            if transformed_rudolf.active
            else self.perception_nearest_visible_pet_name
        )
        nearest_visible_pet_distance = (
            transformed_rudolf.target_distance
            if transformed_rudolf.active
            else self.perception_nearest_visible_pet_distance
        )

        focus = choose_relationship_focus(
            entries=entries,
            social_target_name=social_target_name,
            care_target_name=active_care_name,
            observe_target_name=observe_target_name,
            observe_target_distance=observe_target_distance,
            observe_target_visible=(observe_target is not None),
            nearest_visible_pet_name=nearest_visible_pet_name,
            nearest_visible_pet_distance=nearest_visible_pet_distance,
            nearest_visible_max_distance=(
                TRANSFORMED_RUDOLF_FOCUS_DISTANCE
                if transformed_rudolf.active
                else None
            ),
            blocked_target_name=blocked_target_name,
        )
        self.relationship_entries = entries
        self.relationship_focus_target_name = focus.target_name
        self.relationship_focus_familiarity = focus.familiarity
        self.relationship_focus_trust = focus.trust
        self.relationship_focus_attachment = focus.attachment
        self.relationship_focus_tension = focus.tension

    def update_expression_state(self, all_pets, now=None):
        if now is None:
            now = app_now()
        observe_target_name, observe_target, observe_target_distance = self.get_locked_observe_focus(all_pets, now=now)
        blocked_target_name = self.get_blocked_observe_target_name(now=now)
        transformed_rudolf = self.get_transformed_rudolf_influence(
            all_pets,
            blocked_target_name=blocked_target_name,
        )
        focus = choose_relationship_focus(
            entries=self.relationship_entries,
            social_target_name=getattr(self.social_target, "name", "") if self.social_target else "",
            care_target_name=(
                getattr(self.care_target, "name", "") if self.care_target else
                getattr(self.care_partner, "name", "") if self.care_partner else ""
            ),
            observe_target_name=observe_target_name,
            observe_target_distance=observe_target_distance,
            observe_target_visible=(observe_target is not None),
            nearest_visible_pet_name=(
                transformed_rudolf.target_name
                if transformed_rudolf.active
                else self.perception_nearest_visible_pet_name
            ),
            nearest_visible_pet_distance=(
                transformed_rudolf.target_distance
                if transformed_rudolf.active
                else self.perception_nearest_visible_pet_distance
            ),
            nearest_visible_max_distance=(
                TRANSFORMED_RUDOLF_FOCUS_DISTANCE
                if transformed_rudolf.active
                else None
            ),
            blocked_target_name=blocked_target_name,
        )
        if (
            transformed_rudolf.active
            and focus.target_name == transformed_rudolf.target_name
        ):
            focus = replace(
                focus,
                familiarity=max(
                    focus.familiarity,
                    transformed_rudolf.expression_familiarity_floor,
                ),
            )
        expression = derive_expression_state(
            situation_tag=self.perception_situation_tag,
            social_mode=self.social_mode,
            care_mode=self.care_mode,
            care_lock_active=self.is_under_care(now),
            focus=focus,
        )
        focus_target = self.get_visible_behavior_target(all_pets, focus.target_name)
        if focus_target is not None:
            self.perception_situation_tag = derive_relational_situation_tag(
                self.perception_situation_tag,
                focus=focus,
                focus_distance=self.distance_to(focus_target),
            )
            if (
                expression.look_at_target and
                self.social_mode == "none" and
                self.care_mode == "none" and
                self.flight_mode == "none" and
                not self.perched_window_hwnd and
                not self.dragging and
                self.state == "idle"
            ):
                self.direction = -1 if focus_target.x() < self.x() else 1
        self.expression_animation_context = expression.animation_context
        self.expression_relation_overlay = expression.relation_overlay
        self.expression_focus_target_name = expression.focus_target_name
        self.expression_posture_bias = expression.posture_bias
        self.expression_spacing_bias = expression.spacing_bias
        self.expression_look_at_target = expression.look_at_target

    def sync_intent_state(self, now=None):
        if now is None:
            now = app_now()
        is_negative_afterglow_active = getattr(self, "is_negative_afterglow_active", None)
        negative_afterglow_active = bool(
            is_negative_afterglow_active(now)
            if callable(is_negative_afterglow_active) else False
        )
        social_target_name = getattr(self.social_target, "name", "") if self.social_target else ""
        care_target_name = (
            getattr(self.care_target, "name", "") if self.care_target else
            getattr(self.care_partner, "name", "") if self.care_partner else ""
        )
        snapshot = derive_current_intent(
            now=now,
            dragging=self.dragging,
            is_angry_locked=self.is_angry_locked,
            is_recovering=self.is_recovering,
            care_lock_active=self.is_under_care(now),
            care_mode=self.care_mode,
            social_mode=self.social_mode,
            flight_mode=self.flight_mode,
            perched_window_hwnd=self.perched_window_hwnd,
            current_purpose=self.current_purpose,
            state=self.state,
            intent_reconsider_after=self.intent_reconsider_after,
            focus_target_name=self.relationship_focus_target_name,
            expression_animation_context=self.expression_animation_context,
            social_target_name=social_target_name,
            care_target_name=care_target_name,
            negative_afterglow_active=negative_afterglow_active,
        )
        sleep_join_intent_active = (
            self.intent_kind in SLEEP_JOIN_INTENT_KINDS and
            bool(self.intent_target_name) and
            snapshot.intent_kind in {
                INTENT_OBSERVE,
                "random_roam",
                "ambient_idle",
            }
        )
        if sleep_join_intent_active:
            return
        observe_lock_active = (
            not negative_afterglow_active and
            self.intent_kind == INTENT_OBSERVE and
            bool(self.intent_target_name) and
            float(self.intent_locked_until or 0.0) > float(now) and
            snapshot.intent_kind in {INTENT_OBSERVE, "random_roam", "ambient_idle"}
        )
        if observe_lock_active:
            self.intent_kind = INTENT_OBSERVE
            self.intent_priority = max(self.intent_priority, snapshot.intent_priority)
            self.intent_source = "ambient"
            self.intent_context = "observe"
            self.intent_reason = "observe_locked"
            return
        observe_pending_clear = (
            not negative_afterglow_active and
            self.intent_kind == INTENT_OBSERVE and
            bool(self.intent_target_name) and
            snapshot.intent_kind in {INTENT_OBSERVE, "random_roam", "ambient_idle"}
        )
        if observe_pending_clear:
            self.intent_kind = INTENT_OBSERVE
            self.intent_priority = max(self.intent_priority, snapshot.intent_priority)
            self.intent_source = "ambient"
            self.intent_context = "observe"
            self.intent_reason = "observe_pending_clear"
            return
        post_observe_interaction_lock_active = (
            not negative_afterglow_active and
            self.intent_kind == INTENT_POST_OBSERVE_INTERACTION and
            bool(self.intent_target_name) and
            float(self.intent_locked_until or 0.0) > float(now) and
            snapshot.intent_kind in {INTENT_OBSERVE, "random_roam", "ambient_idle"}
        )
        if post_observe_interaction_lock_active:
            self.intent_kind = INTENT_POST_OBSERVE_INTERACTION
            self.intent_priority = max(self.intent_priority, snapshot.intent_priority)
            self.intent_source = "ambient"
            self.intent_context = "post_observe_interaction"
            self.intent_reason = "post_observe_interaction_locked"
            return
        post_observe_interaction_pending_clear = (
            not negative_afterglow_active and
            self.intent_kind == INTENT_POST_OBSERVE_INTERACTION and
            bool(self.intent_target_name) and
            snapshot.intent_kind in {INTENT_OBSERVE, "random_roam", "ambient_idle"}
        )
        if post_observe_interaction_pending_clear:
            self.intent_kind = INTENT_POST_OBSERVE_INTERACTION
            self.intent_priority = max(self.intent_priority, snapshot.intent_priority)
            self.intent_source = "ambient"
            self.intent_context = "post_observe_interaction"
            self.intent_reason = "post_observe_interaction_pending_clear"
            return
        self.intent_kind = snapshot.intent_kind
        self.intent_target_name = snapshot.intent_target_name
        self.intent_priority = snapshot.intent_priority
        self.intent_source = snapshot.intent_source
        self.intent_context = snapshot.intent_context
        self.intent_reason = snapshot.intent_reason
        if snapshot.intent_kind != INTENT_OBSERVE:
            self.intent_locked_until = 0.0
        if snapshot.intent_kind not in {"none", "random_roam", "observe", "ambient_idle"}:
            self.intent_reconsider_after = 0.0

    def refresh_behavior_layers(self, all_pets, now=None, force=False):
        profiler = getattr(self, "runtime_profiler", None)
        profiler_started_at = time.perf_counter() if profiler is not None else 0.0
        if now is None:
            now = app_now()
        if getattr(self, "offer_scene_kind", "none") != "none":
            self.apply_offer_behavior_layer_override()
            if profiler is not None:
                profiler.record_section(
                    "pet.layers",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return True
        if not self.should_refresh_behavior_layers(force=force):
            if profiler is not None:
                profiler.record_section(
                    "pet.layers",
                    (time.perf_counter() - profiler_started_at) * 1000.0,
                )
            return False
        self.update_perception_state(all_pets)
        self.update_relationship_state(all_pets, now=now)
        self.update_expression_state(all_pets, now=now)
        self.sync_intent_state(now=now)
        self.apply_offer_behavior_layer_override()
        if profiler is not None:
            profiler.record_section(
                "pet.layers",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )
        return True
