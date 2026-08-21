from __future__ import annotations

from dataclasses import dataclass
from functools import wraps


def _dynamic(host, method_name):
    return lambda *args, **kwargs: getattr(host, method_name)(
        *args,
        **kwargs,
    )


@dataclass(frozen=True)
class OfferPetExecutionPort:
    find_by_name: object
    is_busy: object
    can_interact_with_item: object
    find_drop_target: object
    find_hover_target: object
    choose_bottle_feed_child: object
    choose_honey_guardian: object


@dataclass(frozen=True)
class OfferAnimationExecutionPort:
    apply_negative_afterglow: object
    apply_hover_timeout_stage: object
    apply_hover_cursor_avoidance: object
    apply_context: object
    apply_contexts: object
    apply_candidates: object
    apply_reaction: object
    order_candidates_by_purpose: object
    update_direct_accept_motion: object
    interrupt_window_motion: object
    is_window_transitioning: object
    prepare_window_state: object
    reset_pet_motion: object


@dataclass(frozen=True)
class OfferItemExecutionPort:
    ensure_held_item: object
    clear_held_item: object
    apply_held_item_behavior: object
    update_held_item_position: object


@dataclass(frozen=True)
class OfferEventExecutionPort:
    apply_mood_reward: object
    record_offer_event: object
    record_shared_food_event: object
    apply_shared_food_outcome_effects: object


@dataclass(frozen=True)
class OfferFlowExecutionPort:
    finalize_hover_timeout_failure: object
    start_hover_timeout_scene: object
    start_interaction_for_target: object
    start_direct_offer_scene: object
    update_hover_timeout_scene: object
    update_bottle_feed_scene: object
    update_honey_guard_scene: object
    update_shared_food_scene: object


@dataclass(frozen=True)
class SharedFoodExecutionPort:
    get_capability_contexts: object
    get_candidate_result: object
    filter_candidates: object
    build_capabilities: object
    apply_capability: object
    apply_role_action: object
    capture_animation: object
    apply_lock_state: object
    build_participant_state: object
    pet_is_unavailable: object
    evaluate_partner: object
    get_approach_timeout: object
    find_partner: object
    set_stage: object
    hide_item: object
    fallback_to_solo: object
    resolve_outcome: object
    get_consume_stage_seconds: object
    apply_stage_animations: object


class OfferSceneStatePort:
    def __init__(self, host):
        self._host = host

    @property
    def current(self):
        return self._host.offer_scene

    @current.setter
    def current(self, value):
        self._host.offer_scene = value

    def start(self, **kwargs):
        return self._host.item_scene_coordinator.start_scene(
            self._host,
            **kwargs,
        )

    def clear(self):
        return self._host.clear_offer_scene()

    def refresh_locks(self, *pets, until=None):
        if until is None:
            return self._host.refresh_offer_scene_locks(*pets)
        return self._host.refresh_offer_scene_locks(*pets, until=until)

    def lock_pet(self, pet, scene_kind, until):
        return self._host.lock_pet_for_offer_scene(
            pet,
            scene_kind,
            until,
        )

    def get_scene_id(self, scene):
        return self._host.item_scene_coordinator.get_scene_id(scene)


class OfferHoverStatePort:
    def __init__(self, host):
        self._host = host

    @property
    def item_kind(self):
        return self._host.offer_hover_item_kind

    @item_kind.setter
    def item_kind(self, value):
        self._host.offer_hover_item_kind = value

    @property
    def target_name(self):
        return self._host.offer_hover_target_name

    @target_name.setter
    def target_name(self, value):
        self._host.offer_hover_target_name = value

    @property
    def global_x(self):
        return self._host.offer_hover_global_x

    @global_x.setter
    def global_x(self, value):
        self._host.offer_hover_global_x = value

    @property
    def global_y(self):
        return self._host.offer_hover_global_y

    @global_y.setter
    def global_y(self, value):
        self._host.offer_hover_global_y = value

    @property
    def started_at(self):
        return self._host.offer_hover_started_at

    @started_at.setter
    def started_at(self, value):
        self._host.offer_hover_started_at = value

    def clear(self, apply_miss=True):
        return self._host.clear_offer_hover(apply_miss=apply_miss)


@dataclass(frozen=True)
class OfferSceneExecutionPort:
    scene: OfferSceneStatePort
    hover: OfferHoverStatePort
    pets: OfferPetExecutionPort
    animation: OfferAnimationExecutionPort
    items: OfferItemExecutionPort
    events: OfferEventExecutionPort
    flow: OfferFlowExecutionPort
    shared_food: SharedFoodExecutionPort

    @classmethod
    def from_host(cls, host):
        return cls(
            scene=OfferSceneStatePort(host),
            hover=OfferHoverStatePort(host),
            pets=OfferPetExecutionPort(
                find_by_name=_dynamic(host, "find_pet_by_name"),
                is_busy=_dynamic(host, "pet_is_busy_for_offer_interaction"),
                can_interact_with_item=_dynamic(
                    host,
                    "pet_can_interact_with_offer_item",
                ),
                find_drop_target=_dynamic(host, "find_offer_drop_target"),
                find_hover_target=_dynamic(host, "find_offer_hover_target"),
                choose_bottle_feed_child=_dynamic(
                    host,
                    "choose_bottle_feed_child_for_holder",
                ),
                choose_honey_guardian=_dynamic(
                    host,
                    "choose_honey_guardian_for_child",
                ),
            ),
            animation=OfferAnimationExecutionPort(
                apply_negative_afterglow=_dynamic(
                    host,
                    "apply_offer_negative_afterglow",
                ),
                apply_hover_timeout_stage=_dynamic(
                    host,
                    "apply_offer_hover_timeout_stage",
                ),
                apply_hover_cursor_avoidance=_dynamic(
                    host,
                    "apply_offer_hover_cursor_avoidance",
                ),
                apply_context=_dynamic(
                    host,
                    "apply_scene_context_with_preferences",
                ),
                apply_contexts=_dynamic(
                    host,
                    "apply_scene_contexts_with_preferences",
                ),
                apply_candidates=_dynamic(
                    host,
                    "apply_scene_candidates_with_preferences",
                ),
                apply_reaction=_dynamic(
                    host,
                    "apply_scene_reaction_with_preferences",
                ),
                order_candidates_by_purpose=_dynamic(
                    host,
                    "order_candidates_by_purpose",
                ),
                update_direct_accept_motion=_dynamic(
                    host,
                    "update_direct_offer_accept_motion",
                ),
                interrupt_window_motion=_dynamic(
                    host,
                    "interrupt_pet_window_motion_for_offer",
                ),
                is_window_transitioning=_dynamic(
                    host,
                    "pet_is_window_transitioning_for_offer",
                ),
                prepare_window_state=_dynamic(
                    host,
                    "prepare_pet_window_state_for_offer",
                ),
                reset_pet_motion=_dynamic(
                    host,
                    "reset_offer_scene_pet_motion",
                ),
            ),
            items=OfferItemExecutionPort(
                ensure_held_item=_dynamic(host, "ensure_pet_held_item"),
                clear_held_item=_dynamic(host, "clear_pet_held_item"),
                apply_held_item_behavior=_dynamic(
                    host,
                    "apply_held_item_behavior",
                ),
                update_held_item_position=_dynamic(
                    host,
                    "update_held_offer_widget_position",
                ),
            ),
            events=OfferEventExecutionPort(
                apply_mood_reward=_dynamic(host, "apply_offer_mood_reward"),
                record_offer_event=_dynamic(host, "record_offer_event"),
                record_shared_food_event=_dynamic(
                    host,
                    "record_shared_food_event",
                ),
                apply_shared_food_outcome_effects=_dynamic(
                    host,
                    "apply_shared_food_outcome_effects",
                ),
            ),
            flow=OfferFlowExecutionPort(
                finalize_hover_timeout_failure=_dynamic(
                    host,
                    "finalize_offer_hover_timeout_failure",
                ),
                start_hover_timeout_scene=_dynamic(
                    host,
                    "start_offer_hover_timeout_scene",
                ),
                start_interaction_for_target=_dynamic(
                    host,
                    "start_offer_interaction_for_target",
                ),
                start_direct_offer_scene=_dynamic(
                    host,
                    "start_direct_offer_scene",
                ),
                update_hover_timeout_scene=_dynamic(
                    host,
                    "update_offer_hover_timeout_reaction_scene",
                ),
                update_bottle_feed_scene=_dynamic(
                    host,
                    "update_bottle_feed_scene",
                ),
                update_honey_guard_scene=_dynamic(
                    host,
                    "update_honey_guard_scene",
                ),
                update_shared_food_scene=_dynamic(
                    host,
                    "update_shared_food_scene",
                ),
            ),
            shared_food=SharedFoodExecutionPort(
                get_capability_contexts=_dynamic(
                    host,
                    "get_shared_food_capability_contexts",
                ),
                get_candidate_result=_dynamic(
                    host,
                    "get_shared_food_candidate_result",
                ),
                filter_candidates=_dynamic(
                    host,
                    "filter_shared_food_candidates",
                ),
                build_capabilities=_dynamic(
                    host,
                    "build_runtime_shared_food_capabilities",
                ),
                apply_capability=_dynamic(
                    host,
                    "apply_shared_food_capability",
                ),
                apply_role_action=_dynamic(
                    host,
                    "apply_shared_food_role_action",
                ),
                capture_animation=_dynamic(
                    host,
                    "capture_shared_food_animation",
                ),
                apply_lock_state=_dynamic(
                    host,
                    "apply_shared_food_scene_lock_state",
                ),
                build_participant_state=_dynamic(
                    host,
                    "build_shared_food_participant_state",
                ),
                pet_is_unavailable=_dynamic(
                    host,
                    "pet_is_unavailable_during_shared_food",
                ),
                evaluate_partner=_dynamic(
                    host,
                    "evaluate_runtime_shared_food_partner",
                ),
                get_approach_timeout=_dynamic(
                    host,
                    "get_shared_food_approach_timeout",
                ),
                find_partner=_dynamic(host, "find_shared_food_partner"),
                set_stage=_dynamic(host, "set_shared_food_stage"),
                hide_item=_dynamic(host, "hide_shared_food_item"),
                fallback_to_solo=_dynamic(
                    host,
                    "fallback_shared_food_to_solo",
                ),
                resolve_outcome=_dynamic(
                    host,
                    "resolve_active_shared_food_outcome",
                ),
                get_consume_stage_seconds=_dynamic(
                    host,
                    "get_shared_food_consume_stage_seconds",
                ),
                apply_stage_animations=_dynamic(
                    host,
                    "apply_shared_food_stage_animations",
                ),
            ),
        )


def ensure_offer_scene_execution_port(port_or_host):
    if isinstance(port_or_host, OfferSceneExecutionPort):
        return port_or_host
    existing = getattr(port_or_host, "offer_scene_execution_port", None)
    if isinstance(existing, OfferSceneExecutionPort):
        return existing
    return OfferSceneExecutionPort.from_host(port_or_host)


def adapt_offer_scene_executor(cls):
    """Coerce legacy test hosts at executor boundaries into the narrow port."""

    for method_name, descriptor in tuple(vars(cls).items()):
        if method_name.startswith("__"):
            continue
        if isinstance(descriptor, staticmethod):
            function = descriptor.__func__

            @wraps(function)
            def static_wrapper(port_or_host, *args, __fn=function, **kwargs):
                return __fn(
                    ensure_offer_scene_execution_port(port_or_host),
                    *args,
                    **kwargs,
                )

            setattr(cls, method_name, staticmethod(static_wrapper))
            continue
        if not callable(descriptor):
            continue
        function = descriptor

        @wraps(function)
        def method_wrapper(
            self,
            port_or_host,
            *args,
            __fn=function,
            **kwargs,
        ):
            return __fn(
                self,
                ensure_offer_scene_execution_port(port_or_host),
                *args,
                **kwargs,
            )

        setattr(cls, method_name, method_wrapper)
    return cls
