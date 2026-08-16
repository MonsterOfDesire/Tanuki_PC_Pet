import random

from .item_scene_coordinator import SharedFoodSceneState
from .offer_interaction_rules import (
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
)
from .offer_scene_execution_port import adapt_offer_scene_executor
from .runtime import app_now
from .shared_food_outcome_rules import (
    get_shared_food_consumer_names,
    preflight_shared_food_outcomes,
    resolve_shared_food_outcome,
)
from .shared_food_partner_rules import (
    SharedFoodParticipantState,
    SharedFoodPartnerEligibility,
    calculate_shared_food_approach_timeout,
    evaluate_shared_food_partner_eligibility,
)
from .shared_food_profiles import (
    SHARED_FOOD_CONTEXT_BY_CAPABILITY,
    SHARED_FOOD_OUTCOME_HOLDER_GIVES,
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
    SharedFoodCharacterCapabilities,
    get_shared_food_profile,
    get_shared_food_profile_for_holder,
)
from .transformation_profiles import (
    CAPABILITY_SHARED_FOOD,
    pet_form_allows_capability,
)


SHARED_FOOD_UPDATE_INTERVAL_SECONDS = 0.03
SHARED_FOOD_APPROACH_TIMEOUT_MAX_SECONDS = 8.0
SHARED_FOOD_REQUEST_DECISION_SECONDS = 1.2
SHARED_FOOD_TRANSITION_SECONDS = 0.45
SHARED_FOOD_FINISH_SECONDS = 0.65
SHARED_FOOD_APPROACH_MIN_SPEED = 1.5


@adapt_offer_scene_executor
class SharedFoodSceneExecutor:
    """Executes shared-food eligibility, scene stages, and outcome settlement."""

    def get_shared_food_capability_contexts(
        self,
        port,
        item_kind,
        pet_name,
        capability_name,
    ):
        contexts = []
        shared_context = SHARED_FOOD_CONTEXT_BY_CAPABILITY.get(capability_name, "")
        if shared_context:
            contexts.append(shared_context)
        if capability_name == "consume":
            direct_context = get_direct_offer_accept_context(item_kind, pet_name)
            if direct_context and direct_context not in contexts:
                contexts.append(direct_context)
        return tuple(contexts)

    def get_shared_food_candidate_result(
        self,
        port,
        pet,
        candidate,
        preferred_moods,
        contexts=(),
    ):
        asset_manager = getattr(pet, "asset_manager", None)
        getter = getattr(asset_manager, "get_frames_for_action_by_preferences", None)
        if not callable(getter):
            return None
        purpose, action_type = candidate
        context_options = tuple(contexts or ()) or (None,)
        for context in context_options:
            result = getter(
                purpose,
                action_type,
                list(preferred_moods or ()),
                mood_score=None,
                context=context,
            )
            if result:
                return result
        return None

    def filter_shared_food_candidates(
        self,
        port,
        pet,
        item_kind,
        capability_name,
        candidates,
        preferred_moods,
    ):
        contexts = port.shared_food.get_capability_contexts(
            item_kind,
            pet.name,
            capability_name,
        )
        return tuple(
            candidate
            for candidate in tuple(candidates or ())
            if port.shared_food.get_candidate_result(
                pet,
                candidate,
                preferred_moods,
                contexts,
            )
        )

    def build_runtime_shared_food_capabilities(
        self,
        port,
        profile,
        pet,
        preferred_moods,
    ):
        configured = profile.capabilities_for(pet.name)
        if configured is None:
            return None
        capability_kwargs = {}
        for capability_name in ("hold", "approach", "consume", "request", "watch", "react"):
            capability_kwargs[f"{capability_name}_candidates"] = port.shared_food.filter_candidates(
                pet,
                profile.item_kind,
                capability_name,
                getattr(configured, f"{capability_name}_candidates"),
                preferred_moods,
            )
        return SharedFoodCharacterCapabilities(**capability_kwargs)

    def apply_shared_food_capability(
        self,
        port,
        pet,
        item_kind,
        capability_name,
        candidates,
        preferred_moods,
        *,
        preserve=False,
    ):
        candidate_list = tuple(candidates or ())
        if not candidate_list:
            return False
        contexts = port.shared_food.get_capability_contexts(
            item_kind,
            pet.name,
            capability_name,
        )
        current_candidate = (
            getattr(pet, "current_purpose", ""),
            getattr(pet, "current_action_tag", ""),
        )
        current_mood = getattr(pet, "current_mood_tag", "")
        if preserve and current_candidate in candidate_list and current_mood in set(preferred_moods or ()):
            current_result = port.shared_food.get_candidate_result(
                pet,
                current_candidate,
                (current_mood,),
                contexts,
            )
            if current_result:
                pet.state = "move" if current_candidate[0] == "move" else "idle"
                return True
        for candidate in candidate_list:
            result = port.shared_food.get_candidate_result(
                pet,
                candidate,
                preferred_moods,
                contexts,
            )
            if result and pet.apply_animation_result(candidate[0], result):
                pet.state = "move" if candidate[0] == "move" else "idle"
                return True
        return False

    def apply_shared_food_role_action(
        self,
        port,
        pet,
        profile,
        capabilities,
        capability_order,
        preferred_moods,
        *,
        preserve=False,
    ):
        for capability_name in capability_order:
            candidates = getattr(capabilities, f"{capability_name}_candidates", ())
            if port.shared_food.apply_capability(
                pet,
                profile.item_kind,
                capability_name,
                candidates,
                preferred_moods,
                preserve=preserve,
            ):
                return True
        return False

    def capture_shared_food_animation(self, port, pet):
        if pet is None:
            return ()
        return (
            str(getattr(pet, "current_purpose", "") or ""),
            str(getattr(pet, "current_action_tag", "") or ""),
            str(getattr(pet, "current_mood_tag", "") or ""),
        )

    def apply_shared_food_scene_lock_state(self, port, pet, focus_name):
        pet.perception_situation_tag = "locked"
        pet.expression_animation_context = "ambient"
        pet.expression_relation_overlay = "none"
        pet.expression_focus_target_name = focus_name
        pet.expression_posture_bias = "neutral"
        pet.expression_spacing_bias = "neutral"
        pet.expression_look_at_target = True
        pet.relationship_focus_target_name = focus_name

    def build_shared_food_participant_state(self, port, pet, now):
        return SharedFoodParticipantState(
            visible=bool(pet is not None and pet.isVisible()),
            busy=bool(
                not pet_form_allows_capability(
                    pet,
                    CAPABILITY_SHARED_FOOD,
                )
                or
                port.pets.is_busy(pet, now)
                or getattr(pet, "is_angry_locked", False)
            ),
            dragging=bool(getattr(pet, "dragging", False)),
            recovering=bool(getattr(pet, "is_recovering", False)),
            social_mode=str(getattr(pet, "social_mode", "none") or "none"),
            perched=bool(getattr(pet, "perched_window_hwnd", 0)),
            offer_scene_kind=str(getattr(pet, "offer_scene_kind", "none") or "none"),
            has_held_item=bool(getattr(pet, "held_item_kind", "")),
        )

    def pet_is_unavailable_during_shared_food(self, port, pet, now):
        return bool(
            pet is None
            or port.pets.is_busy(pet, now)
            or getattr(pet, "is_angry_locked", False)
            or getattr(pet, "dragging", False)
            or getattr(pet, "is_recovering", False)
            or getattr(pet, "social_mode", "none") != "none"
            or getattr(pet, "flight_mode", "none") != "none"
            or getattr(pet, "perched_window_hwnd", 0)
        )

    def evaluate_runtime_shared_food_partner(
        self,
        port,
        profile,
        holder_pet,
        partner_pet,
        now,
    ):
        if profile is None or holder_pet is None or partner_pet is None:
            return SharedFoodPartnerEligibility(False, "missing_participant", float("inf"))
        try:
            distance = float(holder_pet.distance_to(partner_pet))
        except (AttributeError, TypeError, ValueError):
            distance = float("inf")
        return evaluate_shared_food_partner_eligibility(
            holder=port.shared_food.build_participant_state(holder_pet, now),
            partner=port.shared_food.build_participant_state(partner_pet, now),
            distance=distance,
            join_distance=profile.join_distance,
        )

    def get_shared_food_approach_timeout(self, port, profile, holder_pet, partner_pet):
        partner_speed = max(
            SHARED_FOOD_APPROACH_MIN_SPEED,
            float(partner_pet.get_base_speed()),
        )
        return calculate_shared_food_approach_timeout(
            distance=holder_pet.distance_to(partner_pet),
            approach_distance=profile.approach_distance,
            speed_per_tick=partner_speed,
            tick_seconds=SHARED_FOOD_UPDATE_INTERVAL_SECONDS,
            wait_buffer_seconds=profile.partner_wait_seconds,
            maximum_seconds=SHARED_FOOD_APPROACH_TIMEOUT_MAX_SECONDS,
        )

    def find_shared_food_partner(self, port, profile, holder_pet, now=None):
        now = app_now() if now is None else float(now)
        for partner_name in profile.partner_names_for_holder(holder_pet.name):
            partner_pet = port.pets.find_by_name(partner_name, visible_only=False)
            eligibility = port.shared_food.evaluate_partner(
                profile,
                holder_pet,
                partner_pet,
                now,
            )
            if not eligibility.eligible:
                continue
            return partner_pet
        return None

    def start_shared_food_scene(
        self,
        port,
        holder_pet,
        partner_pet=None,
        *,
        profile=None,
        source="offer_tray",
        outcome_roll=None,
        now=None,
        roll_provider=None,
    ):
        if holder_pet is None or port.scene.current is not None:
            return False
        if not pet_form_allows_capability(
            holder_pet,
            CAPABILITY_SHARED_FOOD,
        ):
            return False
        profile = profile or get_shared_food_profile_for_holder(
            getattr(holder_pet, "held_item_kind", ""),
            holder_pet.name,
        )
        if profile is None:
            return False
        if now is None:
            now = app_now()
        partner_pet = partner_pet or port.shared_food.find_partner(profile, holder_pet, now=now)
        if (
            partner_pet is None
            or partner_pet.name not in profile.partner_names_for_holder(holder_pet.name)
        ):
            return False
        eligibility = port.shared_food.evaluate_partner(
            profile,
            holder_pet,
            partner_pet,
            now,
        )
        if not eligibility.eligible:
            return False
        if (
            port.animation.is_window_transitioning(holder_pet)
            or port.animation.is_window_transitioning(partner_pet)
            or port.animation.prepare_window_state(holder_pet)
            or port.animation.prepare_window_state(partner_pet)
        ):
            return False

        holder_capabilities = port.shared_food.build_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = port.shared_food.build_capabilities(
            profile,
            partner_pet,
            profile.partner_preferred_moods,
        )
        available_outcomes = preflight_shared_food_outcomes(
            profile,
            holder_pet.name,
            partner_pet.name,
            holder_capabilities=holder_capabilities,
            partner_capabilities=partner_capabilities,
        )
        if not available_outcomes:
            return False
        held_widget = port.items.ensure_held_item(holder_pet, profile.item_kind, source=source)
        if held_widget is None:
            return False

        port.animation.interrupt_window_motion(holder_pet)
        port.animation.interrupt_window_motion(partner_pet)
        if outcome_roll is None:
            if roll_provider is None:
                roll_provider = random.random
            roll = roll_provider()
        else:
            roll = float(outcome_roll)
        shared_state = SharedFoodSceneState(
            holder_name=holder_pet.name,
            partner_name=partner_pet.name,
            available_outcomes=tuple(available_outcomes),
            outcome_roll=roll,
        )
        approach_end = float(now) + port.shared_food.get_approach_timeout(
            profile,
            holder_pet,
            partner_pet,
        )
        start_result = port.scene.start(
            participant_pets=(holder_pet, partner_pet),
            item_kind=profile.item_kind,
            scene_kind="shared_food",
            actor_name=holder_pet.name,
            target_name=partner_pet.name,
            profile_key=profile.profile_key,
            stage="partner_approach",
            stage_initialized=False,
            stage_started_at=now,
            stage_ends_at=approach_end,
            scene_ends_at=approach_end,
            source=source,
            shared_food_state=shared_state,
        )
        if not start_result.started:
            port.items.clear_held_item(holder_pet)
            return False
        return bool(port.flow.update_shared_food_scene(now))

    def apply_shared_food_outcome_effects(self, port, shared_state):
        if shared_state.effects_applied:
            return False
        reward_by_name = {}
        for consumer_name in shared_state.consumer_names:
            reward_by_name[consumer_name] = max(reward_by_name.get(consumer_name, 0.0), 6.0)
        if shared_state.outcome_key == SHARED_FOOD_OUTCOME_HOLDER_GIVES:
            reward_by_name[shared_state.holder_name] = max(
                reward_by_name.get(shared_state.holder_name, 0.0),
                2.0,
            )
        for pet_name, amount in reward_by_name.items():
            port.events.apply_mood_reward(pet_name, amount=amount)
        shared_state.effects_applied = True
        return True

    def set_shared_food_stage(self, port, stage, now, duration):
        if port.scene.current is None or port.scene.current.scene_kind != "shared_food":
            return False
        stage_end = float(now) + max(0.05, float(duration))
        port.scene.current.stage = stage
        port.scene.current.stage_initialized = False
        port.scene.current.stage_started_at = float(now)
        port.scene.current.stage_ends_at = stage_end
        port.scene.current.scene_ends_at = stage_end
        return True

    def hide_shared_food_item(self, port, holder_pet, shared_state):
        if shared_state.item_hidden:
            return False
        port.items.clear_held_item(holder_pet)
        shared_state.item_hidden = True
        return True

    def fallback_shared_food_to_solo(self, port, holder_pet):
        if port.scene.current is None or port.scene.current.scene_kind != "shared_food":
            return False
        item_kind = port.scene.current.item_kind
        source = port.scene.current.source
        port.scene.clear()
        if (
            holder_pet is None
            or not holder_pet.isVisible()
            or not get_direct_offer_accept_candidates(item_kind, holder_pet.name)
        ):
            return False
        return port.flow.start_direct_offer_scene(item_kind, holder_pet, source=source)

    def resolve_active_shared_food_outcome(
        self,
        port,
        profile,
        holder_pet,
        partner_pet,
    ):
        scene = port.scene.current
        shared_state = scene.shared_food_state
        if shared_state.outcome_resolved:
            return True
        holder_capabilities = port.shared_food.build_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = port.shared_food.build_capabilities(
            profile,
            partner_pet,
            profile.partner_preferred_moods,
        )
        resolution = resolve_shared_food_outcome(
            profile,
            holder_pet.name,
            partner_pet.name,
            roll=shared_state.outcome_roll,
            available_outcomes=shared_state.available_outcomes,
            holder_capabilities=holder_capabilities,
            partner_capabilities=partner_capabilities,
        )
        if not resolution.resolved:
            return False
        consumer_names = get_shared_food_consumer_names(
            resolution.consume_order,
            holder_pet.name,
            partner_pet.name,
        )
        return shared_state.store_outcome(
            outcome_key=resolution.outcome_key,
            available_outcomes=resolution.available_outcomes,
            normalized_outcome_weights=resolution.normalized_weights,
            outcome_roll=resolution.roll,
            consume_order=resolution.consume_order,
            consumer_names=consumer_names,
        )

    def get_shared_food_consume_stage_seconds(self, port, profile, outcome_key):
        shared_seconds = max(2.0, float(profile.shared_duration_seconds))
        if outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
            remaining = shared_seconds - SHARED_FOOD_TRANSITION_SECONDS - SHARED_FOOD_FINISH_SECONDS
            return max(0.75, remaining / 2.0)
        return max(1.0, shared_seconds - SHARED_FOOD_FINISH_SECONDS)

    def apply_shared_food_stage_animations(
        self,
        port,
        profile,
        holder_pet,
        partner_pet,
        holder_capabilities,
        partner_capabilities,
    ):
        scene = port.scene.current
        shared_state = scene.shared_food_state
        preserve = bool(scene.stage_initialized)
        holder_moods = profile.holder_preferred_moods
        partner_moods = profile.partner_preferred_moods
        holder_pet.direction = -1 if partner_pet.x() < holder_pet.x() else 1
        partner_pet.direction = -holder_pet.direction

        if scene.stage == "partner_approach":
            holder_pet.state = "idle"
            port.shared_food.apply_role_action(
                holder_pet,
                profile,
                holder_capabilities,
                ("hold",),
                holder_moods,
                preserve=preserve,
            )
            port.shared_food.apply_role_action(
                partner_pet,
                profile,
                partner_capabilities,
                ("approach",),
                partner_moods,
                preserve=preserve,
            )
            partner_pet.state = "move"
            partner_pet.move_toward_x(
                holder_pet.x(),
                speed_scale=1.0,
                min_speed=max(SHARED_FOOD_APPROACH_MIN_SPEED, partner_pet.get_base_speed()),
            )
            port.items.update_held_item_position(
                getattr(holder_pet, "held_item_widget", None),
                holder_pet,
                profile.item_kind,
                prefer_preview=True,
            )
        else:
            port.animation.reset_pet_motion(holder_pet)
            port.animation.reset_pet_motion(partner_pet)
            if scene.stage == "request_decision":
                port.shared_food.apply_role_action(
                    holder_pet,
                    profile,
                    holder_capabilities,
                    ("watch",),
                    holder_moods,
                    preserve=preserve,
                )
                port.shared_food.apply_role_action(
                    partner_pet,
                    profile,
                    partner_capabilities,
                    ("request",),
                    partner_moods,
                    preserve=preserve,
                )
                port.items.update_held_item_position(
                    getattr(holder_pet, "held_item_widget", None),
                    holder_pet,
                    profile.item_kind,
                    prefer_preview=True,
                )
            elif scene.stage in ("first_consume", "second_consume"):
                consumer_name = (
                    shared_state.first_consumer_name
                    if scene.stage == "first_consume"
                    else shared_state.second_consumer_name
                )
                consumer_pet = holder_pet if consumer_name == holder_pet.name else partner_pet
                consumer_capabilities = (
                    holder_capabilities if consumer_pet is holder_pet else partner_capabilities
                )
                consumer_moods = holder_moods if consumer_pet is holder_pet else partner_moods
                supporter_pet = partner_pet if consumer_pet is holder_pet else holder_pet
                supporter_capabilities = (
                    partner_capabilities if supporter_pet is partner_pet else holder_capabilities
                )
                supporter_moods = partner_moods if supporter_pet is partner_pet else holder_moods
                port.shared_food.apply_role_action(
                    consumer_pet,
                    profile,
                    consumer_capabilities,
                    ("consume",),
                    consumer_moods,
                    preserve=preserve,
                )
                port.shared_food.apply_role_action(
                    supporter_pet,
                    profile,
                    supporter_capabilities,
                    ("react",),
                    supporter_moods,
                    preserve=preserve,
                )

        shared_state.holder_animation = port.shared_food.capture_animation(holder_pet)
        shared_state.partner_animation = port.shared_food.capture_animation(partner_pet)
        port.shared_food.apply_lock_state(holder_pet, partner_pet.name)
        port.shared_food.apply_lock_state(partner_pet, holder_pet.name)
        holder_pet.refresh_movement_state()
        partner_pet.refresh_movement_state()
        scene.stage_initialized = True
        return True

    def update_shared_food_scene(self, port, now):
        scene = port.scene.current
        if scene is None or scene.scene_kind != "shared_food":
            return False
        profile = get_shared_food_profile(scene.profile_key)
        if profile is None or profile.item_kind != scene.item_kind:
            port.scene.clear()
            return False
        shared_state = scene.shared_food_state
        holder_pet = port.pets.find_by_name(
            shared_state.holder_name or scene.actor_name,
            visible_only=False,
        )
        partner_pet = port.pets.find_by_name(
            shared_state.partner_name or scene.target_name,
            visible_only=False,
        )
        if holder_pet is None or not holder_pet.isVisible():
            port.scene.clear()
            return False
        pre_consume = scene.stage in ("partner_approach", "request_decision")
        if partner_pet is None or not partner_pet.isVisible():
            if pre_consume:
                return port.shared_food.fallback_to_solo(holder_pet)
            port.scene.clear()
            return False
        if port.shared_food.pet_is_unavailable(holder_pet, now):
            port.scene.clear()
            return False
        if port.shared_food.pet_is_unavailable(partner_pet, now):
            if pre_consume:
                return port.shared_food.fallback_to_solo(holder_pet)
            port.scene.clear()
            return False

        holder_capabilities = port.shared_food.build_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = port.shared_food.build_capabilities(
            profile,
            partner_pet,
            profile.partner_preferred_moods,
        )
        if holder_capabilities is None or partner_capabilities is None:
            if pre_consume:
                return port.shared_food.fallback_to_solo(holder_pet)
            port.scene.clear()
            return False
        port.scene.refresh_locks(holder_pet, partner_pet)

        if scene.stage == "partner_approach":
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if partner_pet.distance_to(holder_pet) <= float(profile.approach_distance):
                port.shared_food.set_stage(
                    "request_decision",
                    now,
                    SHARED_FOOD_REQUEST_DECISION_SECONDS,
                )
                return port.flow.update_shared_food_scene(now)
            if float(now) >= float(scene.stage_ends_at):
                return port.shared_food.fallback_to_solo(holder_pet)
            return True

        if scene.stage == "request_decision":
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            if not shared_state.outcome_resolved:
                if not port.shared_food.resolve_outcome(profile, holder_pet, partner_pet):
                    return port.shared_food.fallback_to_solo(holder_pet)
                port.shared_food.hide_item(holder_pet, shared_state)
                port.shared_food.set_stage(
                    "first_consume",
                    now,
                    port.shared_food.get_consume_stage_seconds(
                        profile,
                        shared_state.outcome_key,
                    ),
                )
            return port.flow.update_shared_food_scene(now)

        if scene.stage == "first_consume":
            port.shared_food.hide_item(holder_pet, shared_state)
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            if shared_state.outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
                port.shared_food.set_stage(
                    "transition",
                    now,
                    SHARED_FOOD_TRANSITION_SECONDS,
                )
            else:
                port.shared_food.set_stage(
                    "finish",
                    now,
                    SHARED_FOOD_FINISH_SECONDS,
                )
            return port.flow.update_shared_food_scene(now)

        if scene.stage == "transition":
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            port.shared_food.set_stage(
                "second_consume",
                now,
                port.shared_food.get_consume_stage_seconds(
                    profile,
                    shared_state.outcome_key,
                ),
            )
            return port.flow.update_shared_food_scene(now)

        if scene.stage == "second_consume":
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            port.shared_food.set_stage(
                "finish",
                now,
                SHARED_FOOD_FINISH_SECONDS,
            )
            return port.flow.update_shared_food_scene(now)

        if scene.stage == "finish":
            port.shared_food.apply_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            port.events.apply_shared_food_outcome_effects(shared_state)
            if not scene.event_recorded:
                port.events.record_shared_food_event(profile, shared_state, source=scene.source)
                scene.event_recorded = True
            if float(now) < float(scene.stage_ends_at):
                return True
            port.scene.clear()
            return True

        port.scene.clear()
        return False
