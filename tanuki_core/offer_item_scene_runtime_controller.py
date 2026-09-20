from __future__ import annotations

import random
import time
from dataclasses import dataclass

from PyQt6.QtCore import QPoint

from .autonomous_offer_rules import (
    AUTONOMOUS_GROUND_SOURCE,
    AUTONOMOUS_OFFER_COOLDOWN_MAX_SECONDS,
    AUTONOMOUS_OFFER_COOLDOWN_MIN_SECONDS,
    AUTONOMOUS_OFFER_INITIAL_MAX_SECONDS,
    AUTONOMOUS_OFFER_INITIAL_MIN_SECONDS,
    AUTONOMOUS_OFFER_PREVIEW_MAX_SECONDS,
    AUTONOMOUS_OFFER_PREVIEW_MIN_SECONDS,
    AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
    AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
    AUTONOMOUS_OFFER_SOURCE,
    AutonomousOfferOpportunity,
    AutonomousOfferPreviewState,
    AutonomousOfferScheduleState,
    choose_autonomous_offer_opportunity,
)

from .bottle_honey_scene_executor import BottleHoneySceneExecutor
from .direct_hover_scene_executor import DirectHoverSceneExecutor
from .ground_item_coordinator import GroundItemCoordinator
from .item_scene_coordinator import ItemSceneCoordinator
from .offer_interaction_rules import (
    ITEM_BOTTLE,
    ITEM_HONEY,
    ITEM_LOLLIPOP,
    ITEM_RAMEN,
    ITEM_TEA,
    get_direct_offer_accept_candidates,
    get_ground_pickup_pet_names,
)
from .offer_scene_execution_port import OfferSceneExecutionPort
from .runtime import app_now
from .shared_food_profiles import get_shared_food_profile_for_holder
from .shared_food_scene_executor import SharedFoodSceneExecutor


ITEM_SCENE_CANCELS_ON_HIDDEN = {
    "direct_accept",
    "hover_timeout_reaction",
    "honey_guard",
    "bottle_feed",
    "deny_only",
}
BOTTLE_HOLDER_WAIT_TIMEOUT_SECONDS = 2.5


@dataclass
class OfferItemSceneSupport:
    """Narrow callbacks for pet animation and offer-specific selection."""

    apply_offer_hover_miss: object
    pet_is_busy_for_offer_interaction: object
    pet_can_interact_with_offer_item: object
    find_offer_drop_target: object
    find_offer_hover_target: object
    apply_offer_negative_afterglow: object
    apply_offer_hover_timeout_stage: object
    apply_offer_hover_cursor_avoidance: object
    apply_scene_context_with_preferences: object
    apply_scene_contexts_with_preferences: object
    apply_scene_candidates_with_preferences: object
    apply_scene_reaction_with_preferences: object
    order_candidates_by_purpose: object
    update_direct_offer_accept_motion: object
    choose_honey_guardian_for_child: object
    choose_bottle_feed_child_for_holder: object
    interrupt_pet_window_motion_for_offer: object
    pet_is_window_transitioning_for_offer: object
    prepare_pet_window_state_for_offer: object
    reset_offer_scene_pet_motion: object
    update_held_offer_widget_position: object
    apply_held_item_behavior: object
    get_shared_food_capability_contexts: object
    get_shared_food_candidate_result: object
    filter_shared_food_candidates: object
    build_runtime_shared_food_capabilities: object
    apply_shared_food_capability: object
    apply_shared_food_role_action: object
    build_shared_food_achievement_metadata: object
    apply_offer_mood_reward: object
    record_offer_event: object
    record_household_event: object
    start_direct_offer_scene: object
    start_bottle_feed_scene: object
    start_shared_food_scene: object
    start_honey_guard_scene: object
    build_offer_item_widget: object
    drop_ground_offer_item: object
    ensure_pet_held_item: object
    record_shared_food_event: object
    update_shared_food_scene: object


class OfferItemSceneRuntimeController:
    """Owns offer, held-item and ground-item scene lifecycle."""

    def __init__(
        self,
        *,
        pets,
        pet_registry,
        achievement_runtime_coordinator,
        profiler,
        support: OfferItemSceneSupport,
        item_scene_coordinator=None,
        ground_item_coordinator=None,
        direct_hover_scene_executor=None,
        bottle_honey_scene_executor=None,
        shared_food_scene_executor=None,
        ground_items=None,
        now_provider=app_now,
        performance_now_provider=time.perf_counter,
        random_provider=random.random,
        random_choice_provider=random.choice,
        uniform_provider=random.uniform,
        shared_food_profile_provider=get_shared_food_profile_for_holder,
    ):
        self.pets_list = pets
        self.pet_registry = pet_registry
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.profiler = profiler
        self.support = support
        self.item_scene_coordinator = (
            item_scene_coordinator or ItemSceneCoordinator()
        )
        self.ground_offer_items = (
            ground_items if ground_items is not None else []
        )
        self.ground_item_coordinator = (
            ground_item_coordinator
            or GroundItemCoordinator(self.ground_offer_items)
        )
        self.direct_hover_scene_executor = (
            direct_hover_scene_executor or DirectHoverSceneExecutor()
        )
        self.bottle_honey_scene_executor = (
            bottle_honey_scene_executor or BottleHoneySceneExecutor()
        )
        self.shared_food_scene_executor = (
            shared_food_scene_executor or SharedFoodSceneExecutor()
        )
        self.now_provider = now_provider
        self.performance_now_provider = performance_now_provider
        self.random_provider = random_provider
        self.random_choice_provider = random_choice_provider
        self.uniform_provider = uniform_provider
        self.shared_food_profile_provider = shared_food_profile_provider
        self.offer_scene = None
        self.offer_hover_item_kind = ""
        self.offer_hover_target_name = ""
        self.offer_hover_global_x = 0.0
        self.offer_hover_global_y = 0.0
        self.offer_hover_started_at = 0.0
        self.autonomous_offer_schedule = AutonomousOfferScheduleState()
        self.autonomous_offer_preview = None
        self.offer_scene_execution_port = OfferSceneExecutionPort.from_host(
            self
        )

    def find_pet_by_name(self, pet_name, visible_only=False):
        return self.pet_registry.find_by_name(
            pet_name,
            visible_only=visible_only,
        )

    def lock_pet_for_offer_scene(self, pet, scene_kind, until):
        return self.item_scene_coordinator.lock_pet(
            pet,
            scene_kind,
            until,
        )

    def unlock_pet_offer_scene(self, pet, expected_scene_kind=None):
        return self.item_scene_coordinator.unlock_pet(
            pet,
            expected_scene_kind=expected_scene_kind,
        )

    def refresh_offer_scene_locks(self, *pets, until=None):
        return self.item_scene_coordinator.lock_scene_participants(
            self,
            pets,
            until=until,
        )

    def clear_offer_scene(self):
        scene = self.offer_scene
        if scene is not None and scene.scene_kind in {
            "honey_guard",
            "shared_food",
        }:
            self.achievement_runtime_coordinator.cancel_activity_session(
                self.item_scene_coordinator.get_scene_id(scene),
                reason="offer_scene_cleared",
            )
        if scene is not None and scene.scene_kind == "shared_food":
            shared_state = scene.shared_food_state
            if not shared_state.item_hidden:
                holder_pet = self.find_pet_by_name(
                    shared_state.holder_name or scene.actor_name,
                    visible_only=False,
                )
                if holder_pet is not None:
                    self.clear_pet_held_item(holder_pet)
                shared_state.item_hidden = True
        return self.item_scene_coordinator.clear_scene(
            self,
            find_pet_by_name=self.find_pet_by_name,
        )

    def clear_offer_hover(self, apply_miss=True):
        if self.offer_scene is None and self.offer_hover_target_name:
            pet = self.find_pet_by_name(
                self.offer_hover_target_name,
                visible_only=False,
            )
            if apply_miss:
                self.apply_offer_hover_miss(
                    pet,
                    self.offer_hover_item_kind,
                )
            if (
                pet is not None
                and getattr(pet, "offer_scene_kind", "none")
                == "hover_preview"
            ):
                self.unlock_pet_offer_scene(
                    pet,
                    expected_scene_kind="hover_preview",
                )
        self.offer_hover_item_kind = ""
        self.offer_hover_target_name = ""
        self.offer_hover_global_x = 0.0
        self.offer_hover_global_y = 0.0
        self.offer_hover_started_at = 0.0

    def cancel_offer_scene_if_hidden_participants(self):
        if self.offer_scene is None:
            return False
        if self.offer_scene.scene_kind not in ITEM_SCENE_CANCELS_ON_HIDDEN:
            return False
        participants = []
        has_hidden_participant = False
        for pet_name in {
            self.offer_scene.actor_name,
            self.offer_scene.target_name,
        }:
            if not pet_name:
                continue
            pet = self.find_pet_by_name(pet_name, visible_only=False)
            if pet is None:
                continue
            participants.append(pet)
            if not pet.isVisible():
                has_hidden_participant = True
        if not has_hidden_participant:
            return False
        for pet in participants:
            if getattr(pet, "held_item_kind", ""):
                self.clear_pet_held_item(pet)
        self.clear_offer_hover(apply_miss=False)
        self.clear_offer_scene()
        return True

    def start_offer_interaction_for_target(
        self,
        item_kind,
        target_pet,
        source="offer_tray",
    ):
        if target_pet is None:
            return False
        if not self.pet_can_interact_with_offer_item(
            target_pet,
            item_kind,
        ):
            return False
        if (
            item_kind == ITEM_HONEY
            and target_pet.name == "Tsurumaru Tsuyoshi"
        ):
            return self.start_honey_guard_scene(target_pet, source=source)
        if item_kind == ITEM_BOTTLE:
            if target_pet.name == "Tsurumaru Tsuyoshi":
                return self.start_direct_offer_scene(
                    item_kind,
                    target_pet,
                    source=source,
                )
            return self.start_bottle_feed_scene(target_pet, source=source)
        shared_profile = self.shared_food_profile_provider(
            item_kind,
            target_pet.name,
        )
        if shared_profile is not None:
            partner_pet = self.find_shared_food_partner(
                shared_profile,
                target_pet,
            )
            if partner_pet is not None and self.start_shared_food_scene(
                target_pet,
                partner_pet,
                profile=shared_profile,
                source=source,
            ):
                return True
        if get_direct_offer_accept_candidates(
            item_kind,
            target_pet.name,
        ):
            return self.start_direct_offer_scene(
                item_kind,
                target_pet,
                source=source,
            )
        return False

    def clear_ground_offer_items(self):
        return self.ground_item_coordinator.clear_ground_items()

    def clear_pet_held_item(self, pet):
        return self.ground_item_coordinator.clear_held_item(
            pet,
            unlock_offer_scene=self.unlock_pet_offer_scene,
        )

    def build_offer_item_widget(self, *args, **kwargs):
        return self.support.build_offer_item_widget(*args, **kwargs)

    def _build_offer_item_widget(self, item_kind, draggable=False):
        drop_handler = (
            lambda widget, kind, global_pos: (
                self.handle_ground_offer_item_drop(
                    widget,
                    kind,
                    global_pos,
                )
            )
            if draggable
            else None
        )
        hover_handler = (
            lambda kind, global_pos: self.handle_offer_hover(
                item_kind=kind,
                global_pos=global_pos,
            )
            if draggable
            else None
        )
        clear_hover_handler = (
            (lambda: self.clear_offer_hover()) if draggable else None
        )
        return self.ground_item_coordinator.build_widget(
            item_kind,
            draggable=draggable,
            drop_handler=drop_handler,
            hover_handler=hover_handler,
            clear_hover_handler=clear_hover_handler,
        )

    def ensure_pet_held_item(self, *args, **kwargs):
        return self.support.ensure_pet_held_item(*args, **kwargs)

    def _ensure_pet_held_item(
        self,
        pet,
        item_kind,
        source="offer_tray",
    ):
        return self.ground_item_coordinator.ensure_held_item(
            pet,
            item_kind,
            source=source,
            clear_held_item=self.clear_pet_held_item,
            build_widget=self.build_offer_item_widget,
        )

    def find_ground_offer_item_by_widget(self, widget):
        return self.ground_item_coordinator.find_by_widget(widget)

    def handle_offer_hover(self, *, item_kind, global_pos):
        now = self.now_provider()
        if self.offer_scene is not None:
            if self.offer_scene.scene_kind == "hover_timeout_reaction":
                self.offer_hover_global_x = float(global_pos.x())
                self.offer_hover_global_y = float(global_pos.y())
                return True
            return False
        target_pet = self.find_offer_hover_target(item_kind, global_pos)
        if target_pet is None:
            self.clear_offer_hover()
            return False
        hover_target_changed = (
            self.offer_hover_target_name != target_pet.name
            or self.offer_hover_item_kind != item_kind
        )
        if self.offer_hover_target_name and hover_target_changed:
            previous_pet = self.find_pet_by_name(
                self.offer_hover_target_name,
                visible_only=False,
            )
            if (
                previous_pet is not None
                and getattr(previous_pet, "offer_scene_kind", "none")
                == "hover_preview"
            ):
                self.unlock_pet_offer_scene(
                    previous_pet,
                    expected_scene_kind="hover_preview",
                )
        self.offer_hover_item_kind = item_kind
        self.offer_hover_target_name = target_pet.name
        self.offer_hover_global_x = float(global_pos.x())
        self.offer_hover_global_y = float(global_pos.y())
        if hover_target_changed or not self.offer_hover_started_at:
            self.offer_hover_started_at = float(now)
        return True

    def handle_offer_drop(self, *, item_kind, global_pos):
        if self.offer_scene is not None:
            if self.hover_timeout_scene_accepts_offer_drop(
                item_kind,
                global_pos,
            ):
                return True
            return self.drop_ground_offer_item(item_kind, global_pos)
        target_pet = self.find_offer_drop_target(item_kind, global_pos)
        if target_pet is None:
            self.clear_offer_hover(apply_miss=False)
            return self.drop_ground_offer_item(item_kind, global_pos)
        self.clear_offer_hover(apply_miss=False)
        if self.start_offer_interaction_for_target(
            item_kind,
            target_pet,
            source="offer_tray",
        ):
            return True
        return self.drop_ground_offer_item(item_kind, global_pos)

    def handle_ground_offer_item_drop(
        self,
        widget,
        item_kind,
        global_pos,
    ):
        self.clear_offer_hover(apply_miss=False)
        dropped_item = self.find_ground_offer_item_by_widget(widget)
        if dropped_item is None:
            return False
        if self.offer_scene is None:
            target_pet = self.find_offer_drop_target(
                item_kind,
                global_pos,
            )
            if target_pet is not None:
                self.remove_ground_offer_item(dropped_item)
                if self.start_offer_interaction_for_target(
                    item_kind,
                    target_pet,
                    source="ground_pickup",
                ):
                    return True
        self.place_ground_offer_item(dropped_item, global_pos)
        return True

    def update_pet_held_items(self, now):
        handled = False
        for pet in self.pets_list:
            if (
                not getattr(pet, "held_item_kind", "")
                or getattr(pet, "held_item_widget", None) is None
            ):
                continue
            if not pet.isVisible():
                self.clear_pet_held_item(pet)
                handled = True
                continue
            if self._is_autonomous_offer_preview_holder(pet):
                handled = self.apply_held_item_behavior(pet, now) or handled
                continue
            if (
                pet.held_item_kind == ITEM_BOTTLE
                and float(
                    getattr(pet, "held_item_started_at", 0.0) or 0.0
                )
                <= 0.0
            ):
                pet.held_item_started_at = float(now)
            if (
                pet.name != "Tsurumaru Tsuyoshi"
                and pet.held_item_kind == ITEM_BOTTLE
                and not (
                    self.offer_scene is not None
                    and self.offer_scene.scene_kind == "bottle_feed"
                    and self.offer_scene.actor_name == pet.name
                )
                and self.choose_bottle_feed_child_for_holder(
                    pet,
                    now=now,
                )
                is None
                and float(now) - float(pet.held_item_started_at)
                >= BOTTLE_HOLDER_WAIT_TIMEOUT_SECONDS
            ):
                self.clear_pet_held_item(pet)
                handled = True
                continue
            active_holder = bool(
                self.offer_scene is not None
                and (
                    (
                        self.offer_scene.scene_kind == "honey_guard"
                        and self.offer_scene.target_name == pet.name
                    )
                    or (
                        self.offer_scene.scene_kind == "bottle_feed"
                        and self.offer_scene.actor_name == pet.name
                    )
                    or (
                        self.offer_scene.scene_kind == "shared_food"
                        and self.offer_scene.actor_name == pet.name
                    )
                )
            )
            if not active_holder:
                handled = self.apply_held_item_behavior(pet, now) or handled
            if (
                pet.name == "Tsurumaru Tsuyoshi"
                and pet.held_item_kind == ITEM_HONEY
                and self.offer_scene is None
            ):
                guardian_name = self.choose_honey_guardian_for_child(pet)
                if guardian_name:
                    self.start_honey_guard_scene(
                        pet,
                        source=getattr(
                            pet,
                            "held_item_source",
                            "offer_tray",
                        ),
                    )
                    handled = True
            if (
                pet.name != "Tsurumaru Tsuyoshi"
                and pet.held_item_kind == ITEM_BOTTLE
                and self.offer_scene is None
            ):
                child_pet = self.choose_bottle_feed_child_for_holder(
                    pet,
                    now=now,
                )
                if child_pet is not None:
                    self.start_bottle_feed_scene(
                        pet,
                        source=getattr(
                            pet,
                            "held_item_source",
                            "offer_tray",
                        ),
                    )
                    handled = True
        return handled

    def start_direct_offer_scene(self, *args, **kwargs):
        return self.support.start_direct_offer_scene(*args, **kwargs)

    def _start_direct_offer_scene(
        self,
        item_kind,
        target_pet,
        source="offer_tray",
    ):
        return self.direct_hover_scene_executor.start_direct_offer_scene(
            self,
            item_kind,
            target_pet,
            source=source,
            now=self.now_provider(),
            roll=self.random_provider(),
        )

    def start_bottle_feed_scene(self, *args, **kwargs):
        return self.support.start_bottle_feed_scene(*args, **kwargs)

    def _start_bottle_feed_scene(
        self,
        holder_pet,
        source="offer_tray",
    ):
        return self.bottle_honey_scene_executor.start_bottle_feed_scene(
            self,
            holder_pet,
            source=source,
            now=self.now_provider(),
        )

    def start_shared_food_scene(self, *args, **kwargs):
        return self.support.start_shared_food_scene(*args, **kwargs)

    def _start_shared_food_scene(
        self,
        holder_pet,
        partner_pet=None,
        *,
        profile=None,
        source="offer_tray",
        outcome_roll=None,
    ):
        started = self.shared_food_scene_executor.start_shared_food_scene(
            self,
            holder_pet,
            partner_pet,
            profile=profile,
            source=source,
            outcome_roll=outcome_roll,
            now=self.now_provider(),
            roll_provider=self.random_provider,
        )
        if (
            started
            and self.offer_scene is not None
            and self.offer_scene.scene_kind == "shared_food"
        ):
            self._begin_offer_achievement_session(self.offer_scene)
        return started

    def start_honey_guard_scene(self, *args, **kwargs):
        return self.support.start_honey_guard_scene(*args, **kwargs)

    def _start_honey_guard_scene(
        self,
        child_pet,
        source="offer_tray",
    ):
        started = self.bottle_honey_scene_executor.start_honey_guard_scene(
            self,
            child_pet,
            source=source,
            now=self.now_provider(),
        )
        if (
            started
            and self.offer_scene is not None
            and self.offer_scene.scene_kind == "honey_guard"
        ):
            self._begin_offer_achievement_session(self.offer_scene)
        return started

    def _begin_offer_achievement_session(self, scene):
        if scene is None:
            return False
        return self.achievement_runtime_coordinator.begin_offer_session(
            scene_id=self.item_scene_coordinator.get_scene_id(scene),
            source=str(scene.source or "offer_tray"),
            started_at=float(scene.started_at or self.now_provider()),
        )

    def drop_ground_offer_item(self, *args, **kwargs):
        return self.support.drop_ground_offer_item(*args, **kwargs)

    def _drop_ground_offer_item(self, item_kind, global_pos):
        return self.ground_item_coordinator.drop_item(
            item_kind,
            global_pos,
            build_widget=self.build_offer_item_widget,
        )

    def place_ground_offer_item(self, dropped_item, global_pos):
        return self.ground_item_coordinator.place_item(
            dropped_item,
            global_pos,
        )

    def remove_ground_offer_item(self, dropped_item):
        return self.ground_item_coordinator.remove_item(dropped_item)

    def update_ground_offer_items(self, now):
        return self.ground_item_coordinator.update_items(
            now,
            offer_scene_active=lambda: self.offer_scene is not None,
            try_pickup=self.try_pickup_ground_offer_item,
        )

    def try_pickup_ground_offer_item(self, dropped_item):
        return self.ground_item_coordinator.try_pickup_item(
            dropped_item,
            find_pet_by_name=self.find_pet_by_name,
            pet_is_busy=self.pet_is_busy_for_offer_interaction,
            start_interaction=self.start_offer_interaction_for_target,
        )

    def update_offer_scene(self, now=None):
        profiler_started_at = self.performance_now_provider()
        now = self.now_provider() if now is None else float(now)
        held_item_handled = self.update_pet_held_items(now)
        ground_handled = self.update_ground_offer_items(now)
        scene_canceled = self.cancel_offer_scene_if_hidden_participants()
        autonomous_handled = self.update_autonomous_offer_proposal(now)
        if self.offer_scene is None and self.offer_hover_target_name:
            result = bool(
                self.update_offer_hover_preview(now)
                or scene_canceled
                or held_item_handled
                or ground_handled
                or autonomous_handled
            )
            self._record_update_duration(profiler_started_at)
            return result
        if self.offer_scene is None:
            result = bool(
                scene_canceled or held_item_handled or ground_handled
                or autonomous_handled
            )
            self._record_update_duration(profiler_started_at)
            return result
        scene_result = self.item_scene_coordinator.update(
            self,
            now,
            update_handlers={
                "direct_accept": self.update_direct_offer_scene,
                "hover_timeout_reaction": (
                    self.update_offer_hover_timeout_reaction_scene
                ),
                "honey_guard": self.update_honey_guard_scene,
                "bottle_feed": self.update_bottle_feed_scene,
                "shared_food": self.update_shared_food_scene,
                "deny_only": self.update_deny_only_offer_scene,
            },
            clear_scene_callback=self.clear_offer_scene,
        )
        result = bool(
            scene_result.handled
            or scene_canceled
            or held_item_handled
            or ground_handled
            or autonomous_handled
        )
        self._record_update_duration(profiler_started_at)
        return result

    def is_active(self):
        return bool(
            self.offer_scene is not None
            or self.offer_hover_target_name
            or self.autonomous_offer_preview is not None
            or self.ground_offer_items
            or any(
                getattr(pet, "held_item_kind", "")
                for pet in self.pets_list
            )
        )

    def update_autonomous_offer_proposal(self, now):
        now = float(now)
        if self.autonomous_offer_preview is not None:
            return self._update_autonomous_offer_preview(now)
        schedule = self.autonomous_offer_schedule
        if schedule.next_proposal_at <= 0.0:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_INITIAL_MIN_SECONDS,
                AUTONOMOUS_OFFER_INITIAL_MAX_SECONDS,
            )
            return False
        if now < schedule.next_proposal_at:
            return False
        if (
            self.offer_scene is not None
            or bool(self.offer_hover_target_name)
            or bool(self.ground_offer_items)
            or any(
                getattr(pet, "held_item_kind", "")
                for pet in self.pets_list
            )
        ):
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
                AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
            )
            return False

        opportunities = self._autonomous_offer_opportunities(now)
        selected = choose_autonomous_offer_opportunity(
            opportunities,
            roll=self.random_provider(),
        )
        if selected is None:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
                AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
            )
            return False
        actor = self.find_pet_by_name(
            selected.actor_name,
            visible_only=True,
        )
        if selected.delivery_kind == "ground":
            started = self._drop_autonomous_honey_for_child(actor)
        else:
            return bool(self._start_autonomous_offer_preview(
                selected,
                actor,
                now,
            ))
        if started:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_COOLDOWN_MIN_SECONDS,
                AUTONOMOUS_OFFER_COOLDOWN_MAX_SECONDS,
            )
        else:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
                AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
            )
        return bool(started)

    def _start_autonomous_offer_preview(self, selected, actor, now):
        if actor is None:
            return False
        widget = self._ensure_pet_held_item(
            actor,
            selected.item_kind,
            source=AUTONOMOUS_OFFER_SOURCE,
        )
        if widget is None:
            return False
        duration = self.uniform_provider(
            AUTONOMOUS_OFFER_PREVIEW_MIN_SECONDS,
            AUTONOMOUS_OFFER_PREVIEW_MAX_SECONDS,
        )
        self.autonomous_offer_preview = AutonomousOfferPreviewState(
            item_kind=selected.item_kind,
            actor_name=selected.actor_name,
            started_at=float(now),
            ends_at=float(now) + float(duration),
        )
        self.apply_held_item_behavior(actor, now)
        return True

    def _update_autonomous_offer_preview(self, now):
        preview = self.autonomous_offer_preview
        if preview is None:
            return False
        actor = self.find_pet_by_name(
            preview.actor_name,
            visible_only=False,
        )
        preview_is_valid = bool(
            actor is not None
            and actor.isVisible()
            and not bool(getattr(actor, "dragging", False))
            and getattr(actor, "held_item_kind", "") == preview.item_kind
            and getattr(actor, "held_item_widget", None) is not None
            and self.offer_scene is None
        )
        if not preview_is_valid:
            if actor is not None and getattr(actor, "held_item_kind", ""):
                self.clear_pet_held_item(actor)
            self.autonomous_offer_preview = None
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
                AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
            )
            return False
        if now < preview.ends_at:
            return bool(self.apply_held_item_behavior(actor, now))

        self.autonomous_offer_preview = None
        self.clear_pet_held_item(actor)
        started = self.start_offer_interaction_for_target(
            preview.item_kind,
            actor,
            source=AUTONOMOUS_OFFER_SOURCE,
        )
        if started:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_COOLDOWN_MIN_SECONDS,
                AUTONOMOUS_OFFER_COOLDOWN_MAX_SECONDS,
            )
        else:
            self._schedule_autonomous_offer(
                now,
                AUTONOMOUS_OFFER_RETRY_MIN_SECONDS,
                AUTONOMOUS_OFFER_RETRY_MAX_SECONDS,
            )
        return bool(started)

    def _is_autonomous_offer_preview_holder(self, pet):
        preview = self.autonomous_offer_preview
        return bool(
            preview is not None
            and pet is not None
            and getattr(pet, "name", "") == preview.actor_name
        )

    def _autonomous_offer_opportunities(self, now):
        opportunities = []
        item_weights = {
            ITEM_RAMEN: 1.0,
            ITEM_TEA: 1.0,
            ITEM_LOLLIPOP: 0.9,
            ITEM_HONEY: 0.8,
            ITEM_BOTTLE: 0.9,
        }
        for item_kind in (
            ITEM_RAMEN,
            ITEM_TEA,
            ITEM_LOLLIPOP,
            ITEM_HONEY,
            ITEM_BOTTLE,
        ):
            for pet_name in get_ground_pickup_pet_names(item_kind):
                if (
                    pet_name == "Tsurumaru Tsuyoshi"
                    and item_kind in {ITEM_HONEY, ITEM_BOTTLE}
                ):
                    continue
                pet = self.find_pet_by_name(pet_name, visible_only=True)
                if not self._pet_allows_autonomous_offer(
                    pet,
                    item_kind,
                    now,
                ):
                    continue
                if (
                    item_kind == ITEM_BOTTLE
                    and self.choose_bottle_feed_child_for_holder(
                        pet,
                        now=now,
                    )
                    is None
                ):
                    continue
                opportunities.append(
                    AutonomousOfferOpportunity(
                        item_kind=item_kind,
                        actor_name=pet_name,
                        weight=item_weights[item_kind],
                    )
                )

        child = self.find_pet_by_name(
            "Tsurumaru Tsuyoshi",
            visible_only=True,
        )
        if (
            self._pet_allows_autonomous_offer(child, ITEM_HONEY, now)
            and self.choose_honey_guardian_for_child(child)
        ):
            opportunities.append(
                AutonomousOfferOpportunity(
                    item_kind=ITEM_HONEY,
                    actor_name="Tsurumaru Tsuyoshi",
                    delivery_kind="ground",
                    weight=0.8,
                )
            )
        return tuple(opportunities)

    def _pet_allows_autonomous_offer(self, pet, item_kind, now):
        if pet is None or not pet.isVisible():
            return False
        if self.pet_is_busy_for_offer_interaction(pet, now):
            return False
        is_offer_locked = getattr(pet, "is_offer_locked", None)
        if callable(is_offer_locked) and is_offer_locked(now):
            return False
        return self.pet_can_interact_with_offer_item(pet, item_kind)

    def _drop_autonomous_honey_for_child(self, child):
        if child is None:
            return False
        center_x = float(child.x()) + (float(child.width()) / 2.0)
        bottom_y = float(child.y()) + float(child.height())
        return self.ground_item_coordinator.drop_item(
            ITEM_HONEY,
            QPoint(int(round(center_x)), int(round(bottom_y))),
            build_widget=self.build_offer_item_widget,
            source=AUTONOMOUS_GROUND_SOURCE,
            preferred_pickup_name="Tsurumaru Tsuyoshi",
        )

    def _schedule_autonomous_offer(self, now, minimum, maximum):
        self.autonomous_offer_schedule.next_proposal_at = float(now) + float(
            self.uniform_provider(float(minimum), float(maximum))
        )

    def _record_update_duration(self, started_at):
        self.profiler.record_section(
            "offer.update",
            (self.performance_now_provider() - started_at) * 1000.0,
        )

    def update_offer_hover_preview(self, now):
        return self.direct_hover_scene_executor.update_offer_hover_preview(
            self,
            now,
        )

    def update_offer_hover_timeout_reaction_scene(self, now):
        return self.direct_hover_scene_executor.update_offer_hover_timeout_reaction_scene(
            self,
            now,
        )

    def update_direct_offer_scene(self, now):
        return self.direct_hover_scene_executor.update_direct_offer_scene(
            self,
            now,
            roll_provider=self.random_provider,
        )

    def update_deny_only_offer_scene(self, now):
        return self.direct_hover_scene_executor.update_deny_only_offer_scene(
            self,
            now,
        )

    def update_bottle_feed_scene(self, now):
        return self.bottle_honey_scene_executor.update_bottle_feed_scene(
            self,
            now,
        )

    def update_honey_guard_scene(self, now):
        return self.bottle_honey_scene_executor.update_honey_guard_scene(
            self,
            now,
        )

    def build_shared_food_participant_state(self, pet, now):
        return self.shared_food_scene_executor.build_shared_food_participant_state(
            self,
            pet,
            now,
        )

    def pet_is_unavailable_during_shared_food(self, pet, now):
        return self.shared_food_scene_executor.pet_is_unavailable_during_shared_food(
            self,
            pet,
            now,
        )

    def evaluate_runtime_shared_food_partner(
        self,
        profile,
        holder_pet,
        partner_pet,
        now,
    ):
        return self.shared_food_scene_executor.evaluate_runtime_shared_food_partner(
            self,
            profile,
            holder_pet,
            partner_pet,
            now,
        )

    def get_shared_food_approach_timeout(
        self,
        profile,
        holder_pet,
        partner_pet,
    ):
        return self.shared_food_scene_executor.get_shared_food_approach_timeout(
            self,
            profile,
            holder_pet,
            partner_pet,
        )

    def find_shared_food_partner(self, profile, holder_pet, now=None):
        return self.shared_food_scene_executor.find_shared_food_partner(
            self,
            profile,
            holder_pet,
            now=self.now_provider() if now is None else float(now),
        )

    def set_shared_food_stage(self, stage, now, duration):
        return self.shared_food_scene_executor.set_shared_food_stage(
            self,
            stage,
            now,
            duration,
        )

    def hide_shared_food_item(self, holder_pet, shared_state):
        return self.shared_food_scene_executor.hide_shared_food_item(
            self,
            holder_pet,
            shared_state,
        )

    def fallback_shared_food_to_solo(self, holder_pet):
        return self.shared_food_scene_executor.fallback_shared_food_to_solo(
            self,
            holder_pet,
        )

    def resolve_active_shared_food_outcome(
        self,
        profile,
        holder_pet,
        partner_pet,
    ):
        return self.shared_food_scene_executor.resolve_active_shared_food_outcome(
            self,
            profile,
            holder_pet,
            partner_pet,
        )

    def get_shared_food_consume_stage_seconds(
        self,
        profile,
        outcome_key,
    ):
        return self.shared_food_scene_executor.get_shared_food_consume_stage_seconds(
            self,
            profile,
            outcome_key,
        )

    def apply_shared_food_stage_animations(
        self,
        profile,
        holder_pet,
        partner_pet,
        holder_capabilities,
        partner_capabilities,
    ):
        return self.shared_food_scene_executor.apply_shared_food_stage_animations(
            self,
            profile,
            holder_pet,
            partner_pet,
            holder_capabilities,
            partner_capabilities,
        )

    def update_shared_food_scene(self, *args, **kwargs):
        return self.support.update_shared_food_scene(*args, **kwargs)

    def _update_shared_food_scene(self, now):
        return self.shared_food_scene_executor.update_shared_food_scene(
            self,
            now,
        )

    def capture_shared_food_animation(self, pet):
        return self.shared_food_scene_executor.capture_shared_food_animation(
            self,
            pet,
        )

    def apply_shared_food_scene_lock_state(self, pet, focus_name):
        return self.shared_food_scene_executor.apply_shared_food_scene_lock_state(
            self,
            pet,
            focus_name,
        )

    def record_shared_food_event(self, *args, **kwargs):
        return self.support.record_shared_food_event(*args, **kwargs)

    def _record_shared_food_event(
        self,
        profile,
        shared_state,
        source="offer_tray",
    ):
        return self.support.record_shared_food_event(
            profile,
            shared_state,
            source=source,
        )

    def apply_shared_food_outcome_effects(self, shared_state):
        return self.shared_food_scene_executor.apply_shared_food_outcome_effects(
            self,
            shared_state,
        )

    def hover_timeout_scene_accepts_offer_drop(
        self,
        item_kind,
        global_pos,
    ):
        return self.direct_hover_scene_executor.hover_timeout_scene_accepts_offer_drop(
            self,
            item_kind,
            global_pos,
        )

    def finalize_offer_hover_timeout_failure(self, target_pet, now):
        return self.direct_hover_scene_executor.finalize_offer_hover_timeout_failure(
            self,
            target_pet,
            now,
        )

    def start_offer_hover_timeout_scene(
        self,
        item_kind,
        target_pet,
        now=None,
    ):
        return self.direct_hover_scene_executor.start_offer_hover_timeout_scene(
            self,
            item_kind,
            target_pet,
            now=self.now_provider() if now is None else float(now),
            choose_variant=self.random_choice_provider,
        )

    def shutdown(self):
        self.clear_offer_hover(apply_miss=False)
        self.autonomous_offer_preview = None
        self.clear_offer_scene()
        self.clear_ground_offer_items()
        for pet in self.pets_list:
            self.clear_pet_held_item(pet)
        self.autonomous_offer_schedule = AutonomousOfferScheduleState()

    # Explicit support port forwarded to app-owned animation/selection helpers.
    def apply_offer_hover_miss(self, pet, item_kind):
        return self.support.apply_offer_hover_miss(pet, item_kind)

    def pet_is_busy_for_offer_interaction(self, pet, now=None):
        return self.support.pet_is_busy_for_offer_interaction(pet, now)

    def pet_can_interact_with_offer_item(self, pet, item_kind):
        return self.support.pet_can_interact_with_offer_item(pet, item_kind)

    def find_offer_drop_target(self, item_kind, global_pos):
        return self.support.find_offer_drop_target(item_kind, global_pos)

    def find_offer_hover_target(
        self,
        item_kind,
        global_pos,
        ignore_reaction_cooldown=False,
    ):
        return self.support.find_offer_hover_target(
            item_kind,
            global_pos,
            ignore_reaction_cooldown,
        )

    def apply_offer_negative_afterglow(self, *args, **kwargs):
        return self.support.apply_offer_negative_afterglow(*args, **kwargs)

    def apply_offer_hover_timeout_stage(self, *args, **kwargs):
        return self.support.apply_offer_hover_timeout_stage(*args, **kwargs)

    def apply_offer_hover_cursor_avoidance(self, *args, **kwargs):
        return self.support.apply_offer_hover_cursor_avoidance(*args, **kwargs)

    def apply_scene_context_with_preferences(self, *args, **kwargs):
        return self.support.apply_scene_context_with_preferences(*args, **kwargs)

    def apply_scene_contexts_with_preferences(self, *args, **kwargs):
        return self.support.apply_scene_contexts_with_preferences(*args, **kwargs)

    def apply_scene_candidates_with_preferences(self, *args, **kwargs):
        return self.support.apply_scene_candidates_with_preferences(*args, **kwargs)

    def apply_scene_reaction_with_preferences(self, *args, **kwargs):
        return self.support.apply_scene_reaction_with_preferences(*args, **kwargs)

    def order_candidates_by_purpose(self, *args, **kwargs):
        return self.support.order_candidates_by_purpose(*args, **kwargs)

    def update_direct_offer_accept_motion(self, *args, **kwargs):
        return self.support.update_direct_offer_accept_motion(*args, **kwargs)

    def choose_honey_guardian_for_child(self, *args, **kwargs):
        return self.support.choose_honey_guardian_for_child(*args, **kwargs)

    def choose_bottle_feed_child_for_holder(self, *args, **kwargs):
        return self.support.choose_bottle_feed_child_for_holder(*args, **kwargs)

    def interrupt_pet_window_motion_for_offer(self, *args, **kwargs):
        return self.support.interrupt_pet_window_motion_for_offer(*args, **kwargs)

    def pet_is_window_transitioning_for_offer(self, *args, **kwargs):
        return self.support.pet_is_window_transitioning_for_offer(*args, **kwargs)

    def prepare_pet_window_state_for_offer(self, *args, **kwargs):
        return self.support.prepare_pet_window_state_for_offer(*args, **kwargs)

    def reset_offer_scene_pet_motion(self, *args, **kwargs):
        return self.support.reset_offer_scene_pet_motion(*args, **kwargs)

    def update_held_offer_widget_position(self, *args, **kwargs):
        return self.support.update_held_offer_widget_position(*args, **kwargs)

    def apply_held_item_behavior(self, *args, **kwargs):
        return self.support.apply_held_item_behavior(*args, **kwargs)

    def get_shared_food_capability_contexts(self, *args, **kwargs):
        return self.support.get_shared_food_capability_contexts(*args, **kwargs)

    def get_shared_food_candidate_result(self, *args, **kwargs):
        return self.support.get_shared_food_candidate_result(*args, **kwargs)

    def filter_shared_food_candidates(self, *args, **kwargs):
        return self.support.filter_shared_food_candidates(*args, **kwargs)

    def build_runtime_shared_food_capabilities(self, *args, **kwargs):
        return self.support.build_runtime_shared_food_capabilities(*args, **kwargs)

    def apply_shared_food_capability(self, *args, **kwargs):
        return self.support.apply_shared_food_capability(*args, **kwargs)

    def apply_shared_food_role_action(self, *args, **kwargs):
        return self.support.apply_shared_food_role_action(*args, **kwargs)

    def build_shared_food_achievement_metadata(self, *args, **kwargs):
        return self.support.build_shared_food_achievement_metadata(*args, **kwargs)

    def apply_offer_mood_reward(self, *args, **kwargs):
        return self.support.apply_offer_mood_reward(*args, **kwargs)

    def record_offer_event(self, *args, **kwargs):
        return self.support.record_offer_event(*args, **kwargs)

    def record_household_event(self, **kwargs):
        return self.support.record_household_event(**kwargs)
