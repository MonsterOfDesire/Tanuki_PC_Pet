import random

from .item_scene_coordinator import SharedFoodSceneState
from .offer_interaction_rules import (
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
    get_offer_item_definition,
)
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
    SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
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


class SharedFoodSceneExecutor:
    """Executes shared-food eligibility, scene stages, and outcome settlement."""

    def get_shared_food_capability_contexts(
        self,
        runtime,
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
        runtime,
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
        runtime,
        pet,
        item_kind,
        capability_name,
        candidates,
        preferred_moods,
    ):
        contexts = runtime.get_shared_food_capability_contexts(
            item_kind,
            pet.name,
            capability_name,
        )
        return tuple(
            candidate
            for candidate in tuple(candidates or ())
            if runtime.get_shared_food_candidate_result(
                pet,
                candidate,
                preferred_moods,
                contexts,
            )
        )

    def build_runtime_shared_food_capabilities(
        self,
        runtime,
        profile,
        pet,
        preferred_moods,
    ):
        configured = profile.capabilities_for(pet.name)
        if configured is None:
            return None
        capability_kwargs = {}
        for capability_name in ("hold", "approach", "consume", "request", "watch", "react"):
            capability_kwargs[f"{capability_name}_candidates"] = runtime.filter_shared_food_candidates(
                pet,
                profile.item_kind,
                capability_name,
                getattr(configured, f"{capability_name}_candidates"),
                preferred_moods,
            )
        return SharedFoodCharacterCapabilities(**capability_kwargs)

    def apply_shared_food_capability(
        self,
        runtime,
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
        contexts = runtime.get_shared_food_capability_contexts(
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
            current_result = runtime.get_shared_food_candidate_result(
                pet,
                current_candidate,
                (current_mood,),
                contexts,
            )
            if current_result:
                pet.state = "move" if current_candidate[0] == "move" else "idle"
                return True
        for candidate in candidate_list:
            result = runtime.get_shared_food_candidate_result(
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
        runtime,
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
            if runtime.apply_shared_food_capability(
                pet,
                profile.item_kind,
                capability_name,
                candidates,
                preferred_moods,
                preserve=preserve,
            ):
                return True
        return False

    def capture_shared_food_animation(self, runtime, pet):
        if pet is None:
            return ()
        return (
            str(getattr(pet, "current_purpose", "") or ""),
            str(getattr(pet, "current_action_tag", "") or ""),
            str(getattr(pet, "current_mood_tag", "") or ""),
        )

    def apply_shared_food_scene_lock_state(self, runtime, pet, focus_name):
        pet.perception_situation_tag = "locked"
        pet.expression_animation_context = "ambient"
        pet.expression_relation_overlay = "none"
        pet.expression_focus_target_name = focus_name
        pet.expression_posture_bias = "neutral"
        pet.expression_spacing_bias = "neutral"
        pet.expression_look_at_target = True
        pet.relationship_focus_target_name = focus_name

    def build_shared_food_participant_state(self, runtime, pet, now):
        return SharedFoodParticipantState(
            visible=bool(pet is not None and pet.isVisible()),
            busy=bool(
                not pet_form_allows_capability(
                    pet,
                    CAPABILITY_SHARED_FOOD,
                )
                or
                runtime.pet_is_busy_for_offer_interaction(pet, now)
                or getattr(pet, "is_angry_locked", False)
            ),
            dragging=bool(getattr(pet, "dragging", False)),
            recovering=bool(getattr(pet, "is_recovering", False)),
            social_mode=str(getattr(pet, "social_mode", "none") or "none"),
            perched=bool(getattr(pet, "perched_window_hwnd", 0)),
            offer_scene_kind=str(getattr(pet, "offer_scene_kind", "none") or "none"),
            has_held_item=bool(getattr(pet, "held_item_kind", "")),
        )

    def pet_is_unavailable_during_shared_food(self, runtime, pet, now):
        return bool(
            pet is None
            or runtime.pet_is_busy_for_offer_interaction(pet, now)
            or getattr(pet, "is_angry_locked", False)
            or getattr(pet, "dragging", False)
            or getattr(pet, "is_recovering", False)
            or getattr(pet, "social_mode", "none") != "none"
            or getattr(pet, "flight_mode", "none") != "none"
            or getattr(pet, "perched_window_hwnd", 0)
        )

    def evaluate_runtime_shared_food_partner(
        self,
        runtime,
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
            holder=runtime.build_shared_food_participant_state(holder_pet, now),
            partner=runtime.build_shared_food_participant_state(partner_pet, now),
            distance=distance,
            join_distance=profile.join_distance,
        )

    def get_shared_food_approach_timeout(self, runtime, profile, holder_pet, partner_pet):
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

    def find_shared_food_partner(self, runtime, profile, holder_pet, now=None):
        now = app_now() if now is None else float(now)
        for partner_name in profile.partner_names_for_holder(holder_pet.name):
            partner_pet = runtime.find_pet_by_name(partner_name, visible_only=False)
            eligibility = runtime.evaluate_runtime_shared_food_partner(
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
        runtime,
        holder_pet,
        partner_pet=None,
        *,
        profile=None,
        source="offer_tray",
        outcome_roll=None,
        now=None,
        roll_provider=None,
    ):
        if holder_pet is None or runtime.offer_scene is not None:
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
        partner_pet = partner_pet or runtime.find_shared_food_partner(profile, holder_pet, now=now)
        if (
            partner_pet is None
            or partner_pet.name not in profile.partner_names_for_holder(holder_pet.name)
        ):
            return False
        eligibility = runtime.evaluate_runtime_shared_food_partner(
            profile,
            holder_pet,
            partner_pet,
            now,
        )
        if not eligibility.eligible:
            return False
        if (
            runtime.pet_is_window_transitioning_for_offer(holder_pet)
            or runtime.pet_is_window_transitioning_for_offer(partner_pet)
            or runtime.prepare_pet_window_state_for_offer(holder_pet)
            or runtime.prepare_pet_window_state_for_offer(partner_pet)
        ):
            return False

        holder_capabilities = runtime.build_runtime_shared_food_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = runtime.build_runtime_shared_food_capabilities(
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
        held_widget = runtime.ensure_pet_held_item(holder_pet, profile.item_kind, source=source)
        if held_widget is None:
            return False

        runtime.interrupt_pet_window_motion_for_offer(holder_pet)
        runtime.interrupt_pet_window_motion_for_offer(partner_pet)
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
        approach_end = float(now) + runtime.get_shared_food_approach_timeout(
            profile,
            holder_pet,
            partner_pet,
        )
        start_result = runtime.item_scene_coordinator.start_scene(
            runtime,
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
            runtime.clear_pet_held_item(holder_pet)
            return False
        return bool(runtime.update_shared_food_scene(now))

    def record_shared_food_event(
        self,
        runtime,
        profile,
        shared_state,
        source="offer_tray",
        now=None,
    ):
        item_definition = get_offer_item_definition(profile.item_kind)
        item_label = item_definition.label if item_definition is not None else profile.item_kind
        if shared_state.outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
            summary = profile.success_summary_by_holder.get(
                shared_state.holder_name,
                f"{shared_state.holder_name} 和 {shared_state.partner_name} 分享了{item_label}。",
            )
        elif shared_state.outcome_key == SHARED_FOOD_OUTCOME_HOLDER_KEEPS:
            summary = (
                f"{shared_state.partner_name} 靠過來看了看，"
                f"{shared_state.holder_name} 最後還是自己享用了{item_label}。"
            )
        else:
            summary = (
                f"{shared_state.holder_name} 把{item_label}讓給了"
                f"{shared_state.partner_name}。"
            )
        metadata_builder = getattr(
            runtime,
            "build_shared_food_achievement_metadata",
            None,
        )
        metadata = (
            metadata_builder(
                profile,
                shared_state,
                source=source,
                now=app_now() if now is None else float(now),
            )
            if callable(metadata_builder)
            else {
                "source": source,
                "item_kind": profile.item_kind,
                "scene_kind": "shared_food",
                "profile_key": profile.profile_key,
                "outcome": shared_state.outcome_key,
            }
        )
        runtime.record_household_event(
            occurred_at=app_now() if now is None else float(now),
            category="player_offer",
            event_type=profile.success_event_type,
            summary=summary,
            actor_name=shared_state.holder_name,
            target_name=shared_state.partner_name,
            household_pressure_delta=-1.0,
            metadata=metadata,
        )

    def apply_shared_food_outcome_effects(self, runtime, shared_state):
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
            runtime.apply_offer_mood_reward(pet_name, amount=amount)
        shared_state.effects_applied = True
        return True

    def set_shared_food_stage(self, runtime, stage, now, duration):
        if runtime.offer_scene is None or runtime.offer_scene.scene_kind != "shared_food":
            return False
        stage_end = float(now) + max(0.05, float(duration))
        runtime.offer_scene.stage = stage
        runtime.offer_scene.stage_initialized = False
        runtime.offer_scene.stage_started_at = float(now)
        runtime.offer_scene.stage_ends_at = stage_end
        runtime.offer_scene.scene_ends_at = stage_end
        return True

    def hide_shared_food_item(self, runtime, holder_pet, shared_state):
        if shared_state.item_hidden:
            return False
        runtime.clear_pet_held_item(holder_pet)
        shared_state.item_hidden = True
        return True

    def fallback_shared_food_to_solo(self, runtime, holder_pet):
        if runtime.offer_scene is None or runtime.offer_scene.scene_kind != "shared_food":
            return False
        item_kind = runtime.offer_scene.item_kind
        source = runtime.offer_scene.source
        runtime.clear_offer_scene()
        if (
            holder_pet is None
            or not holder_pet.isVisible()
            or not get_direct_offer_accept_candidates(item_kind, holder_pet.name)
        ):
            return False
        return runtime.start_direct_offer_scene(item_kind, holder_pet, source=source)

    def resolve_active_shared_food_outcome(
        self,
        runtime,
        profile,
        holder_pet,
        partner_pet,
    ):
        scene = runtime.offer_scene
        shared_state = scene.shared_food_state
        if shared_state.outcome_resolved:
            return True
        holder_capabilities = runtime.build_runtime_shared_food_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = runtime.build_runtime_shared_food_capabilities(
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

    def get_shared_food_consume_stage_seconds(self, runtime, profile, outcome_key):
        shared_seconds = max(2.0, float(profile.shared_duration_seconds))
        if outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
            remaining = shared_seconds - SHARED_FOOD_TRANSITION_SECONDS - SHARED_FOOD_FINISH_SECONDS
            return max(0.75, remaining / 2.0)
        return max(1.0, shared_seconds - SHARED_FOOD_FINISH_SECONDS)

    def apply_shared_food_stage_animations(
        self,
        runtime,
        profile,
        holder_pet,
        partner_pet,
        holder_capabilities,
        partner_capabilities,
    ):
        scene = runtime.offer_scene
        shared_state = scene.shared_food_state
        preserve = bool(scene.stage_initialized)
        holder_moods = profile.holder_preferred_moods
        partner_moods = profile.partner_preferred_moods
        holder_pet.direction = -1 if partner_pet.x() < holder_pet.x() else 1
        partner_pet.direction = -holder_pet.direction

        if scene.stage == "partner_approach":
            holder_pet.state = "idle"
            runtime.apply_shared_food_role_action(
                holder_pet,
                profile,
                holder_capabilities,
                ("hold",),
                holder_moods,
                preserve=preserve,
            )
            runtime.apply_shared_food_role_action(
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
            runtime.update_held_offer_widget_position(
                getattr(holder_pet, "held_item_widget", None),
                holder_pet,
                profile.item_kind,
                prefer_preview=True,
            )
        else:
            runtime.reset_offer_scene_pet_motion(holder_pet)
            runtime.reset_offer_scene_pet_motion(partner_pet)
            if scene.stage == "request_decision":
                runtime.apply_shared_food_role_action(
                    holder_pet,
                    profile,
                    holder_capabilities,
                    ("watch",),
                    holder_moods,
                    preserve=preserve,
                )
                runtime.apply_shared_food_role_action(
                    partner_pet,
                    profile,
                    partner_capabilities,
                    ("request",),
                    partner_moods,
                    preserve=preserve,
                )
                runtime.update_held_offer_widget_position(
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
                runtime.apply_shared_food_role_action(
                    consumer_pet,
                    profile,
                    consumer_capabilities,
                    ("consume",),
                    consumer_moods,
                    preserve=preserve,
                )
                runtime.apply_shared_food_role_action(
                    supporter_pet,
                    profile,
                    supporter_capabilities,
                    ("react",),
                    supporter_moods,
                    preserve=preserve,
                )

        shared_state.holder_animation = runtime.capture_shared_food_animation(holder_pet)
        shared_state.partner_animation = runtime.capture_shared_food_animation(partner_pet)
        runtime.apply_shared_food_scene_lock_state(holder_pet, partner_pet.name)
        runtime.apply_shared_food_scene_lock_state(partner_pet, holder_pet.name)
        holder_pet.refresh_movement_state()
        partner_pet.refresh_movement_state()
        scene.stage_initialized = True
        return True

    def update_shared_food_scene(self, runtime, now):
        scene = runtime.offer_scene
        if scene is None or scene.scene_kind != "shared_food":
            return False
        profile = get_shared_food_profile(scene.profile_key)
        if profile is None or profile.item_kind != scene.item_kind:
            runtime.clear_offer_scene()
            return False
        shared_state = scene.shared_food_state
        holder_pet = runtime.find_pet_by_name(
            shared_state.holder_name or scene.actor_name,
            visible_only=False,
        )
        partner_pet = runtime.find_pet_by_name(
            shared_state.partner_name or scene.target_name,
            visible_only=False,
        )
        if holder_pet is None or not holder_pet.isVisible():
            runtime.clear_offer_scene()
            return False
        pre_consume = scene.stage in ("partner_approach", "request_decision")
        if partner_pet is None or not partner_pet.isVisible():
            if pre_consume:
                return runtime.fallback_shared_food_to_solo(holder_pet)
            runtime.clear_offer_scene()
            return False
        if runtime.pet_is_unavailable_during_shared_food(holder_pet, now):
            runtime.clear_offer_scene()
            return False
        if runtime.pet_is_unavailable_during_shared_food(partner_pet, now):
            if pre_consume:
                return runtime.fallback_shared_food_to_solo(holder_pet)
            runtime.clear_offer_scene()
            return False

        holder_capabilities = runtime.build_runtime_shared_food_capabilities(
            profile,
            holder_pet,
            profile.holder_preferred_moods,
        )
        partner_capabilities = runtime.build_runtime_shared_food_capabilities(
            profile,
            partner_pet,
            profile.partner_preferred_moods,
        )
        if holder_capabilities is None or partner_capabilities is None:
            if pre_consume:
                return runtime.fallback_shared_food_to_solo(holder_pet)
            runtime.clear_offer_scene()
            return False
        runtime.refresh_offer_scene_locks(holder_pet, partner_pet)

        if scene.stage == "partner_approach":
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if partner_pet.distance_to(holder_pet) <= float(profile.approach_distance):
                runtime.set_shared_food_stage(
                    "request_decision",
                    now,
                    SHARED_FOOD_REQUEST_DECISION_SECONDS,
                )
                return runtime.update_shared_food_scene(now)
            if float(now) >= float(scene.stage_ends_at):
                return runtime.fallback_shared_food_to_solo(holder_pet)
            return True

        if scene.stage == "request_decision":
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            if not shared_state.outcome_resolved:
                if not runtime.resolve_active_shared_food_outcome(profile, holder_pet, partner_pet):
                    return runtime.fallback_shared_food_to_solo(holder_pet)
                runtime.hide_shared_food_item(holder_pet, shared_state)
                runtime.set_shared_food_stage(
                    "first_consume",
                    now,
                    runtime.get_shared_food_consume_stage_seconds(
                        profile,
                        shared_state.outcome_key,
                    ),
                )
            return runtime.update_shared_food_scene(now)

        if scene.stage == "first_consume":
            runtime.hide_shared_food_item(holder_pet, shared_state)
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            if shared_state.outcome_key == SHARED_FOOD_OUTCOME_SHARE_BOTH:
                runtime.set_shared_food_stage(
                    "transition",
                    now,
                    SHARED_FOOD_TRANSITION_SECONDS,
                )
            else:
                runtime.set_shared_food_stage(
                    "finish",
                    now,
                    SHARED_FOOD_FINISH_SECONDS,
                )
            return runtime.update_shared_food_scene(now)

        if scene.stage == "transition":
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            runtime.set_shared_food_stage(
                "second_consume",
                now,
                runtime.get_shared_food_consume_stage_seconds(
                    profile,
                    shared_state.outcome_key,
                ),
            )
            return runtime.update_shared_food_scene(now)

        if scene.stage == "second_consume":
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            if float(now) < float(scene.stage_ends_at):
                return True
            runtime.set_shared_food_stage(
                "finish",
                now,
                SHARED_FOOD_FINISH_SECONDS,
            )
            return runtime.update_shared_food_scene(now)

        if scene.stage == "finish":
            runtime.apply_shared_food_stage_animations(
                profile,
                holder_pet,
                partner_pet,
                holder_capabilities,
                partner_capabilities,
            )
            runtime.apply_shared_food_outcome_effects(shared_state)
            if not scene.event_recorded:
                runtime.record_shared_food_event(profile, shared_state, source=scene.source)
                scene.event_recorded = True
            if float(now) < float(scene.stage_ends_at):
                return True
            runtime.clear_offer_scene()
            return True

        runtime.clear_offer_scene()
        return False
