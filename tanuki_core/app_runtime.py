import os
import random
import sys
import time
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from .asset_manager import AssetManager
from .bottle_honey_scene_executor import BottleHoneySceneExecutor
from .config_save_scheduler import ConfigSaveScheduler
from .config_store import ConfigStore
from .dashboard_shell import GlobalMouseListener, SensorZone
from .dashboard_shell_lifecycle import DashboardShellLifecycle
from .dashboard_ui import Dashboard
from .direct_hover_scene_executor import DirectHoverSceneExecutor
from .geometry import DesktopGeometry
from .ground_item_coordinator import GroundItemCoordinator, GroundOfferItem
from .household_event_rules import (
    HouseholdEventScheduleState,
    build_household_event_schedule,
)
from .household_runtime_coordinator import HouseholdRuntimeCoordinator
from .household_state import (
    HouseholdEventLog,
    HouseholdState,
    build_default_household_event_log,
    build_default_household_state,
    seed_default_household_events,
)
from .item_scene_coordinator import (
    ActiveItemScene,
    ItemSceneCoordinator,
)
from .offer_interaction_rules import (
    ITEM_BOTTLE,
    ITEM_HONEY,
    OfferGuardianCandidate,
    can_pet_interact_with_offer_item,
    choose_honey_guardian,
    get_bottle_feed_holder_idle_candidates,
    get_bottle_feed_holder_idle_context,
    get_bottle_feed_holder_idle_preferred_moods,
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
    get_direct_offer_candidates,
    get_direct_offer_mobile_move_speed_scale,
    get_direct_offer_mobile_move_target_offset,
    get_direct_offer_preview_context,
    get_direct_offer_preview_candidates,
    get_direct_offer_preferred_moods,
    get_offer_item_definition,
    resolve_offer_hotspot_match,
    resolve_offer_preview_match,
)
from .pet_widget import TanukiPet
from .runtime import (
    AdaptivePetLogicScheduler,
    SIM_CLOCK,
    RuntimeProfiler,
    app_now,
    get_timer_callback_step_delta,
    resolve_timer_repeat_count,
    run_pet_physics_step,
)
from .settings_provider import RuntimeSettings
from .shared_food_profiles import get_shared_food_profile_for_holder
from .shared_food_scene_executor import SharedFoodSceneExecutor
from .window_tracker import WindowTracker


@dataclass(frozen=True)
class PetSpec:
    folder_name: str
    scale: float
    display_name: str
    initially_visible: bool = True


ActiveOfferScene = ActiveItemScene


ITEM_SCENE_CANCELS_ON_HIDDEN = {
    "direct_accept",
    "hover_timeout_reaction",
    "honey_guard",
    "bottle_feed",
    "deny_only",
}


@dataclass
class TanukiAppRuntime:
    app: QApplication
    settings_provider: RuntimeSettings
    config_store: ConfigStore
    save_scheduler: ConfigSaveScheduler
    window_tracker: WindowTracker
    pets_dict: dict
    pets_list: list
    dashboard: Dashboard
    sensor: SensorZone
    monitor: GlobalMouseListener
    shell: DashboardShellLifecycle | None = None
    timers: dict = field(default_factory=dict)
    household: HouseholdState = field(default_factory=build_default_household_state)
    household_event_log: HouseholdEventLog = field(default_factory=build_default_household_event_log)
    household_event_schedule: HouseholdEventScheduleState = field(default_factory=build_household_event_schedule)
    profiler: RuntimeProfiler = field(default_factory=RuntimeProfiler)
    logic_scheduler: AdaptivePetLogicScheduler = field(default_factory=AdaptivePetLogicScheduler)
    offer_scene: ActiveOfferScene | None = None
    item_scene_coordinator: ItemSceneCoordinator = field(init=False, repr=False)
    household_coordinator: HouseholdRuntimeCoordinator = field(init=False, repr=False)
    ground_item_coordinator: GroundItemCoordinator = field(init=False, repr=False)
    direct_hover_scene_executor: DirectHoverSceneExecutor = field(init=False, repr=False)
    bottle_honey_scene_executor: BottleHoneySceneExecutor = field(init=False, repr=False)
    shared_food_scene_executor: SharedFoodSceneExecutor = field(init=False, repr=False)
    offer_hover_item_kind: str = ""
    offer_hover_target_name: str = ""
    offer_hover_global_x: float = 0.0
    offer_hover_global_y: float = 0.0
    offer_hover_started_at: float = 0.0
    ground_offer_items: list = field(default_factory=list)

    def __post_init__(self):
        self.item_scene_coordinator = ItemSceneCoordinator()
        self.household_coordinator = HouseholdRuntimeCoordinator(
            household=self.household,
            event_log=self.household_event_log,
            event_schedule=self.household_event_schedule,
        )
        self.ground_item_coordinator = GroundItemCoordinator(self.ground_offer_items)
        self.direct_hover_scene_executor = DirectHoverSceneExecutor()
        self.bottle_honey_scene_executor = BottleHoneySceneExecutor()
        self.shared_food_scene_executor = SharedFoodSceneExecutor()

    def shutdown(self):
        for timer in self.timers.values():
            if timer.isActive():
                timer.stop()
        self.clear_ground_offer_items()
        for pet in self.pets_list:
            self.clear_pet_held_item(pet)
        if self.shell is not None:
            self.shell.shutdown()

    def record_household_event(
        self,
        *,
        occurred_at: float,
        category: str = "system",
        event_type: str = "info",
        channel: str = "",
        importance: str = "normal",
        summary: str = "",
        actor_name: str = "",
        target_name: str = "",
        mood_delta: float = 0.0,
        relation_delta: dict[str, float] | None = None,
        tags=(),
        living_fund_delta: int = 0,
        household_pressure_delta: float = 0.0,
        metadata: dict[str, object] | None = None,
        apply_deltas: bool = True,
    ):
        return self.household_coordinator.record_event(
            dashboard=self.dashboard,
            pets=self.pets_list,
            occurred_at=occurred_at,
            category=category,
            event_type=event_type,
            channel=channel,
            importance=importance,
            summary=summary,
            actor_name=actor_name,
            target_name=target_name,
            mood_delta=mood_delta,
            relation_delta=relation_delta,
            tags=tags,
            living_fund_delta=living_fund_delta,
            household_pressure_delta=household_pressure_delta,
            metadata=metadata,
            apply_deltas=apply_deltas,
        )

    def refresh_dashboard_views_for_household_entry(self, entry):
        return self.household_coordinator.refresh_dashboard_views_for_entry(
            self.dashboard,
            entry,
        )

    def household_entry_affects_summary(self, entry):
        return self.household_coordinator.household_entry_affects_summary(entry)

    def notify_household_log_icon(self, entry):
        return self.household_coordinator.notify_household_log_icon(
            self.pets_list,
            entry,
        )

    def recent_household_events(self, limit=10):
        return self.household_coordinator.recent_events(limit=limit)

    def query_household_events(self, **filters):
        return self.household_coordinator.query_events(**filters)

    def household_relationship_entries_for(self, actor_name):
        return self.household_coordinator.relationship_entries_for(actor_name)

    def all_household_relationship_entries(self):
        return self.household_coordinator.all_relationship_entries()

    def donate_household_fund(self, amount=100, actor_name="Player"):
        return self.household_coordinator.donate_household_fund(
            world_mode=self.settings_provider.world_mode,
            amount=amount,
            actor_name=actor_name,
        )

    def collect_pending_social_log_events(self, now=None):
        return self.household_coordinator.collect_pending_social_log_events(
            pets=self.pets_list,
            dashboard=self.dashboard,
            now=now,
        )

    def update_household_events(self, now=None):
        return self.household_coordinator.update_events(
            world_mode=self.settings_provider.world_mode,
            pets=self.pets_list,
            dashboard=self.dashboard,
            profiler=self.profiler,
            now=now,
        )

    def capture_household_persistence_state(self):
        return self.household_coordinator.capture_persistence_state()

    def apply_household_persistence_state(self, payload):
        return self.household_coordinator.apply_persistence_state(
            payload,
            dashboard=self.dashboard,
        )

    def handle_world_mode_change(self, world_mode, previous_mode=None):
        return self.household_coordinator.handle_world_mode_change(
            world_mode,
            previous_mode=previous_mode,
            dashboard=self.dashboard,
            clear_offer_scene=self.clear_offer_scene,
            clear_offer_hover=lambda: self.clear_offer_hover(apply_miss=False),
        )

    def find_pet_by_name(self, pet_name, visible_only=False):
        for pet in self.pets_list:
            if pet.name != pet_name:
                continue
            if visible_only and not pet.isVisible():
                continue
            return pet
        return None

    def lock_pet_for_offer_scene(self, pet, scene_kind, until):
        return self.item_scene_coordinator.lock_pet(pet, scene_kind, until)

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
        self.item_scene_coordinator.clear_scene(
            self,
            find_pet_by_name=self.find_pet_by_name,
        )

    def clear_offer_hover(self, apply_miss=True):
        if self.offer_scene is None and self.offer_hover_target_name:
            pet = self.find_pet_by_name(self.offer_hover_target_name, visible_only=False)
            if apply_miss:
                self.apply_offer_hover_miss(pet, self.offer_hover_item_kind)
            if pet is not None and getattr(pet, "offer_scene_kind", "none") == "hover_preview":
                self.unlock_pet_offer_scene(pet, expected_scene_kind="hover_preview")
        self.offer_hover_item_kind = ""
        self.offer_hover_target_name = ""
        self.offer_hover_global_x = 0.0
        self.offer_hover_global_y = 0.0
        self.offer_hover_started_at = 0.0

    def apply_offer_hover_miss(self, pet, item_kind):
        return self.direct_hover_scene_executor.apply_offer_hover_miss(
            self,
            pet,
            item_kind,
            now=app_now(),
        )

    def cancel_offer_scene_if_hidden_participants(self):
        if self.offer_scene is None:
            return False
        if self.offer_scene.scene_kind not in ITEM_SCENE_CANCELS_ON_HIDDEN:
            return False
        participants = []
        has_hidden_participant = False
        for pet_name in {self.offer_scene.actor_name, self.offer_scene.target_name}:
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

    def pet_is_busy_for_offer_interaction(self, pet, now=None):
        if pet is None:
            return True
        if now is None:
            now = app_now()
        is_under_care = getattr(pet, "is_under_care", None)
        care_locked = bool(is_under_care(now)) if callable(is_under_care) else False
        return bool(
            getattr(pet, "flight_mode", "none") != "none" or
            getattr(pet, "care_mode", "none") != "none" or
            getattr(pet, "care_partner", None) is not None or
            getattr(pet, "is_hugging", False) or
            care_locked
        )

    def hover_timeout_scene_accepts_offer_drop(self, item_kind, global_pos):
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

    def start_offer_interaction_for_target(self, item_kind, target_pet, source="offer_tray"):
        if target_pet is None:
            return False
        if not can_pet_interact_with_offer_item(item_kind, target_pet.name):
            return False
        if item_kind == ITEM_HONEY and target_pet.name == "Tsurumaru Tsuyoshi":
            return self.start_honey_guard_scene(target_pet, source=source)
        if item_kind == ITEM_BOTTLE:
            if target_pet.name == "Tsurumaru Tsuyoshi":
                return self.start_direct_offer_scene(item_kind, target_pet, source=source)
            return self.start_bottle_feed_scene(target_pet, source=source)
        shared_profile = get_shared_food_profile_for_holder(item_kind, target_pet.name)
        if shared_profile is not None:
            partner_pet = self.find_shared_food_partner(shared_profile, target_pet)
            if partner_pet is not None and self.start_shared_food_scene(
                target_pet,
                partner_pet,
                profile=shared_profile,
                source=source,
            ):
                return True
        if get_direct_offer_accept_candidates(item_kind, target_pet.name):
            return self.start_direct_offer_scene(item_kind, target_pet, source=source)
        return False

    def clear_ground_offer_items(self):
        return self.ground_item_coordinator.clear_ground_items()

    def clear_pet_held_item(self, pet):
        return self.ground_item_coordinator.clear_held_item(
            pet,
            unlock_offer_scene=self.unlock_pet_offer_scene,
        )

    def build_offer_item_widget(self, item_kind, draggable=False):
        drop_handler = (lambda widget, item_kind, global_pos, runtime=self: runtime.handle_ground_offer_item_drop(
            widget,
            item_kind,
            global_pos,
        )) if draggable else None
        hover_handler = (lambda item_kind, global_pos, runtime=self: runtime.handle_offer_hover(
            item_kind=item_kind,
            global_pos=global_pos,
        )) if draggable else None
        clear_hover_handler = (lambda runtime=self: runtime.clear_offer_hover()) if draggable else None
        return self.ground_item_coordinator.build_widget(
            item_kind,
            draggable=draggable,
            drop_handler=drop_handler,
            hover_handler=hover_handler,
            clear_hover_handler=clear_hover_handler,
        )

    def ensure_pet_held_item(self, pet, item_kind, source="offer_tray"):
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
        now = app_now()
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
            self.offer_hover_target_name != target_pet.name or
            self.offer_hover_item_kind != item_kind
        )
        if self.offer_hover_target_name and hover_target_changed:
            previous_pet = self.find_pet_by_name(self.offer_hover_target_name, visible_only=False)
            if previous_pet is not None and getattr(previous_pet, "offer_scene_kind", "none") == "hover_preview":
                self.unlock_pet_offer_scene(previous_pet, expected_scene_kind="hover_preview")
        self.offer_hover_item_kind = item_kind
        self.offer_hover_target_name = target_pet.name
        self.offer_hover_global_x = float(global_pos.x())
        self.offer_hover_global_y = float(global_pos.y())
        if hover_target_changed or not self.offer_hover_started_at:
            self.offer_hover_started_at = float(now)
        return True

    def handle_offer_drop(self, *, item_kind, global_pos):
        if self.offer_scene is not None:
            if self.hover_timeout_scene_accepts_offer_drop(item_kind, global_pos):
                return True
            return self.drop_ground_offer_item(item_kind, global_pos)
        target_pet = self.find_offer_drop_target(item_kind, global_pos)
        if target_pet is None:
            self.clear_offer_hover(apply_miss=False)
            return self.drop_ground_offer_item(item_kind, global_pos)
        self.clear_offer_hover(apply_miss=False)
        if self.start_offer_interaction_for_target(item_kind, target_pet, source="offer_tray"):
            return True
        return self.drop_ground_offer_item(item_kind, global_pos)

    def handle_ground_offer_item_drop(self, widget, item_kind, global_pos):
        self.clear_offer_hover(apply_miss=False)
        dropped_item = self.find_ground_offer_item_by_widget(widget)
        if dropped_item is None:
            return False
        if self.offer_scene is None:
            target_pet = self.find_offer_drop_target(item_kind, global_pos)
            if target_pet is not None:
                self.remove_ground_offer_item(dropped_item)
                if self.start_offer_interaction_for_target(item_kind, target_pet, source="ground_pickup"):
                    return True
        self.place_ground_offer_item(dropped_item, global_pos)
        return True

    def find_offer_drop_target(self, item_kind, global_pos):
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        matches = []
        for pet in self.pets_list:
            if not pet.isVisible():
                continue
            if self.pet_is_busy_for_offer_interaction(pet):
                continue
            if not can_pet_interact_with_offer_item(item_kind, pet.name):
                continue
            reference_frame = self.get_offer_reference_frame(pet, item_kind, prefer_preview=True)
            frame_width = reference_frame.width() if reference_frame is not None else pet.width()
            frame_height = reference_frame.height() if reference_frame is not None else pet.height()
            match = resolve_offer_hotspot_match(
                item_kind=item_kind,
                pet_name=pet.name,
                widget_left=pet.x(),
                widget_top=pet.y(),
                widget_width=pet.width(),
                widget_height=pet.height(),
                frame_width=frame_width,
                frame_height=frame_height,
                render_scale=pet.get_effective_scale(),
                direction=pet.direction,
                original_face_left=pet.original_face_left,
                offer_global_x=global_x,
                offer_global_y=global_y,
            )
            if match.matched:
                matches.append((match.distance, pet))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def find_offer_hover_target(self, item_kind, global_pos, ignore_reaction_cooldown=False):
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        now = app_now()
        matches = []
        for pet in self.pets_list:
            if not pet.isVisible():
                continue
            if self.pet_is_busy_for_offer_interaction(pet, now):
                continue
            if not can_pet_interact_with_offer_item(item_kind, pet.name):
                continue
            if (
                not ignore_reaction_cooldown and
                float(getattr(pet, "offer_hover_reaction_cooldown_until", 0.0) or 0.0) > float(now)
            ):
                continue
            reference_frame = self.get_offer_reference_frame(pet, item_kind, prefer_preview=True)
            frame_width = reference_frame.width() if reference_frame is not None else pet.width()
            frame_height = reference_frame.height() if reference_frame is not None else pet.height()
            match = resolve_offer_preview_match(
                widget_left=pet.x(),
                widget_top=pet.y(),
                widget_width=pet.width(),
                widget_height=pet.height(),
                frame_width=frame_width,
                frame_height=frame_height,
                offer_global_x=global_x,
                offer_global_y=global_y,
            )
            if match.matched:
                matches.append((match.distance, pet))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def get_offer_reference_frame(self, pet, item_kind, prefer_preview=False):
        if not can_pet_interact_with_offer_item(item_kind, pet.name):
            return None
        context = (
            get_direct_offer_preview_context(item_kind, pet.name)
            if prefer_preview else
            get_direct_offer_accept_context(item_kind, pet.name)
        )
        preferred_moods = get_direct_offer_preferred_moods(item_kind)
        context_candidate = self.get_offer_reference_frame_for_context(
            pet,
            context,
            preferred_moods,
        )
        if context_candidate is not None:
            return context_candidate
        candidates = (
            get_direct_offer_preview_candidates(item_kind, pet.name)
            if prefer_preview else
            get_direct_offer_accept_candidates(item_kind, pet.name)
        )
        if not candidates:
            candidates = get_direct_offer_candidates(item_kind, pet.name)
        current_candidate_keys = set(candidates)
        if (
            getattr(pet, "current_frames", None) and
            (getattr(pet, "current_purpose", ""), getattr(pet, "current_action_tag", "")) in current_candidate_keys
        ):
            return pet.current_frames[0]
        preferred_moods = get_direct_offer_preferred_moods(item_kind)
        for purpose, action_type in candidates:
            preferred_result = pet.asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred_moods,
                mood_score=pet.mood_score,
            )
            if preferred_result and preferred_result[0]:
                return preferred_result[0][0]
            by_score_result = pet.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                pet.mood_score,
                is_adult=pet.is_adult,
            )
            if by_score_result and by_score_result[0]:
                return by_score_result[0][0]
        if getattr(pet, "current_frames", None):
            frame_index = min(int(getattr(pet, "frame_index", 0) or 0), len(pet.current_frames) - 1)
            return pet.current_frames[frame_index]
        return None

    def get_offer_reference_frame_for_context(self, pet, context, preferred_moods):
        if not context:
            return None
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return None
        current_frames = getattr(pet, "current_frames", None)
        current_purpose = getattr(pet, "current_purpose", "")
        current_action = getattr(pet, "current_action_tag", "")
        current_mood = getattr(pet, "current_mood_tag", "")
        get_specific_frames = getattr(asset_manager, "get_specific_frames", None)
        if current_frames and callable(get_specific_frames):
            frames = get_specific_frames(
                current_purpose,
                current_action,
                current_mood,
                mood_score=None,
                context=context,
            )
            if frames:
                frame_index = min(int(getattr(pet, "frame_index", 0) or 0), len(current_frames) - 1)
                return current_frames[frame_index]
        get_contextual_result = getattr(asset_manager, "get_contextual_result", None)
        for purpose in ("idle", "move"):
            if not callable(get_contextual_result):
                continue
            result = get_contextual_result(
                purpose,
                context=context,
                preferred_moods=preferred_moods,
                mood_score=getattr(pet, "mood_score", None),
                ordered_preferences=True,
            )
            if result and result[0]:
                return result[0][0]
        return None

    def get_offer_hotspot_global_position(self, pet, item_kind, prefer_preview=False):
        reference_frame = self.get_offer_reference_frame(pet, item_kind, prefer_preview=prefer_preview)
        frame_width = reference_frame.width() if reference_frame is not None else pet.width()
        frame_height = reference_frame.height() if reference_frame is not None else pet.height()
        match = resolve_offer_hotspot_match(
            item_kind=item_kind,
            pet_name=pet.name,
            widget_left=pet.x(),
            widget_top=pet.y(),
            widget_width=pet.width(),
            widget_height=pet.height(),
            frame_width=frame_width,
            frame_height=frame_height,
            render_scale=pet.get_effective_scale(),
            direction=pet.direction,
            original_face_left=pet.original_face_left,
            offer_global_x=0.0,
            offer_global_y=0.0,
        )
        return match.hotspot_global_x, match.hotspot_global_y

    def update_held_offer_widget_position(self, widget, pet, item_kind, prefer_preview=False):
        if widget is None or pet is None:
            return
        hotspot_x, hotspot_y = self.get_offer_hotspot_global_position(
            pet,
            item_kind,
            prefer_preview=prefer_preview,
        )
        widget.move_to(
            hotspot_x - (widget.width() / 2.0),
            hotspot_y - (widget.height() / 2.0),
        )
        widget.show()
        widget.raise_()

    def apply_offer_negative_afterglow(self, pet, now, amount=30.0, duration=5.0):
        return self.direct_hover_scene_executor.apply_offer_negative_afterglow(
            self,
            pet,
            now,
            amount=amount,
            duration=duration,
        )

    def apply_offer_hover_timeout_stage(self, pet, stage, preserve=False):
        return self.direct_hover_scene_executor.apply_offer_hover_timeout_stage(
            self,
            pet,
            stage,
            preserve=preserve,
        )

    def apply_offer_hover_cursor_avoidance(self, pet):
        return self.direct_hover_scene_executor.apply_offer_hover_cursor_avoidance(self, pet)

    def start_offer_hover_timeout_scene(self, item_kind, target_pet, now=None):
        return self.direct_hover_scene_executor.start_offer_hover_timeout_scene(
            self,
            item_kind,
            target_pet,
            now=now,
            choose_variant=random.choice,
        )

    def choose_honey_guardian_for_child(self, child_pet):
        return choose_honey_guardian(
            [
                OfferGuardianCandidate(
                    name="Symboli Rudolf",
                    distance=self.find_pet_by_name("Symboli Rudolf", visible_only=True).distance_to(child_pet)
                    if self.find_pet_by_name("Symboli Rudolf", visible_only=True) is not None else 999999.0,
                    is_visible=self.find_pet_by_name("Symboli Rudolf", visible_only=True) is not None,
                ),
                OfferGuardianCandidate(
                    name="Sirius Symboli",
                    distance=self.find_pet_by_name("Sirius Symboli", visible_only=True).distance_to(child_pet)
                    if self.find_pet_by_name("Sirius Symboli", visible_only=True) is not None else 999999.0,
                    is_visible=self.find_pet_by_name("Sirius Symboli", visible_only=True) is not None,
                ),
            ]
        )

    def choose_bottle_feed_child_for_holder(self, holder_pet, now=None):
        if holder_pet is None or holder_pet.name == "Tsurumaru Tsuyoshi":
            return None
        now = app_now() if now is None else float(now)
        child_pet = self.find_pet_by_name("Tsurumaru Tsuyoshi", visible_only=True)
        if child_pet is None or child_pet is holder_pet:
            return None
        if (
            child_pet.dragging or
            child_pet.is_offer_locked(now) or
            self.pet_is_busy_for_offer_interaction(child_pet, now)
        ):
            return None
        return child_pet

    def interrupt_pet_window_motion_for_offer(self, pet):
        if pet is None:
            return
        if getattr(pet, "flight_mode", "none") != "none":
            stop_window_flight = getattr(pet, "stop_window_flight", None)
            if callable(stop_window_flight):
                stop_window_flight(apply_cooldown=False)
        if getattr(pet, "perched_window_hwnd", 0):
            detach_from_window_surface = getattr(pet, "detach_from_window_surface", None)
            if callable(detach_from_window_surface):
                detach_from_window_surface()
        pet.vy = 0
        if hasattr(pet, "fall_origin_y"):
            pet.fall_origin_y = None
        pet.state_timer = 0
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        pet.refresh_movement_state()

    def pet_is_window_transitioning_for_offer(self, pet):
        if pet is None:
            return False
        return getattr(pet, "flight_mode", "none") != "none"

    def prepare_pet_window_state_for_offer(self, pet):
        if pet is None:
            return False
        if self.pet_is_window_transitioning_for_offer(pet):
            return True
        if getattr(pet, "perched_window_hwnd", 0):
            detach_from_window_surface = getattr(pet, "detach_from_window_surface", None)
            if callable(detach_from_window_surface):
                detach_from_window_surface()
            pet.vy = 0
            if hasattr(pet, "fall_origin_y"):
                pet.fall_origin_y = None
            pet.state_timer = 0
            refresh_movement_state = getattr(pet, "refresh_movement_state", None)
            if callable(refresh_movement_state):
                refresh_movement_state()
            return True
        return False

    def reset_offer_scene_pet_motion(self, pet):
        pet.state = "idle"
        pet.state_timer = 0
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        pet.refresh_movement_state()

    def scene_animation_matches_preferences(self, pet, candidates, preferred_moods, forbidden=None):
        forbidden = set(forbidden or ())
        if getattr(pet, "current_mood_tag", "") in forbidden:
            return False
        if getattr(pet, "current_mood_tag", "") not in set(preferred_moods or ()):
            return False
        return (getattr(pet, "current_purpose", ""), getattr(pet, "current_action_tag", "")) in set(candidates or ())

    def apply_scene_context_with_preferences(
        self,
        pet,
        purpose,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        if pet is None or not context:
            return False
        changer = getattr(pet, "change_state_for_context_with_preferences", None)
        if not callable(changer):
            return False
        return bool(
            changer(
                purpose,
                context,
                preferred_moods=preferred_moods,
                forbidden=forbidden,
                preserve=preserve,
                ignore_mood_band=ignore_mood_band,
            )
        )

    def apply_scene_contexts_with_preferences(
        self,
        pet,
        purposes,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        for purpose in purposes:
            if self.apply_scene_context_with_preferences(
                pet,
                purpose,
                context,
                preferred_moods=preferred_moods,
                forbidden=forbidden,
                preserve=preserve,
                ignore_mood_band=ignore_mood_band,
            ):
                return True
        return False

    def order_candidates_by_purpose(self, candidates, purpose_order):
        candidate_list = list(candidates or ())
        purpose_order = list(purpose_order or ())
        if not purpose_order:
            return candidate_list
        ordered = []
        seen = set()
        for purpose in purpose_order:
            for candidate in candidate_list:
                if candidate in seen:
                    continue
                if candidate[0] == purpose:
                    ordered.append(candidate)
                    seen.add(candidate)
        for candidate in candidate_list:
            if candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        return ordered

    def current_direct_offer_accept_is_mobile(self, pet, item_kind, accept_context, candidates):
        if pet is None or getattr(pet, "current_purpose", "") != "move":
            return False
        current_action = getattr(pet, "current_action_tag", "")
        if ("move", current_action) in set(candidates or ()):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        get_specific_frames = getattr(asset_manager, "get_specific_frames", None)
        if callable(get_specific_frames):
            frames = get_specific_frames(
                getattr(pet, "current_purpose", ""),
                current_action,
                getattr(pet, "current_mood_tag", ""),
                mood_score=getattr(pet, "mood_score", None),
                context=accept_context,
            )
            if frames:
                return True
        return bool(current_action and current_action == accept_context)

    def update_direct_offer_accept_motion(self, pet, item_kind, accept_context, candidates):
        if not self.current_direct_offer_accept_is_mobile(pet, item_kind, accept_context, candidates):
            self.reset_offer_scene_pet_motion(pet)
            return False
        pet.state = "move"
        pet.state_timer = max(int(getattr(pet, "state_timer", 0) or 0), 1)
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        direction = -1 if getattr(pet, "direction", 1) < 0 else 1
        target_x = pet.x() + (direction * get_direct_offer_mobile_move_target_offset(item_kind, pet.name))
        mover = getattr(pet, "move_toward_x", None)
        if callable(mover):
            mover(
                target_x,
                speed_scale=get_direct_offer_mobile_move_speed_scale(item_kind, pet.name),
                min_speed=1.0,
            )
        else:
            move_logic = getattr(pet, "move_logic", None)
            if callable(move_logic):
                move_logic()
            else:
                pet.refresh_movement_state()
        return True

    def apply_scene_candidates_with_preferences(self, pet, candidates, preferred_moods, forbidden=None, preserve=False):
        candidate_list = list(candidates or ())
        preferred = list(preferred_moods or ())
        forbidden = set(forbidden or ())
        if preserve and self.scene_animation_matches_preferences(
            pet,
            candidate_list,
            preferred,
            forbidden=forbidden,
        ):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return False
        for mood_tag in preferred:
            if mood_tag in forbidden:
                continue
            weighted_matches = []
            for purpose, action_type in candidate_list:
                record = asset_manager.get_record(purpose, action_type, mood_tag)
                frames = record.get("frames") if record else None
                if frames:
                    weighted_matches.append(
                        (
                            frames,
                            purpose,
                            action_type,
                            mood_tag,
                            asset_manager.get_record_weight(record),
                        )
                    )
            if weighted_matches:
                chosen = asset_manager.choose_weighted_result(
                    [(frames, (purpose, action_type), mood_tag, weight) for frames, purpose, action_type, mood_tag, weight in weighted_matches]
                )
                if chosen:
                    frames, purpose_action, chosen_mood = chosen
                    purpose, action_type = purpose_action
                    if pet.apply_animation_result(purpose, (frames, action_type, chosen_mood)):
                        pet.state = purpose if purpose in {"idle", "move"} else "idle"
                        return True
        for purpose, action_type in candidate_list:
            result = asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred,
                forbidden=list(forbidden),
                mood_score=None,
            )
            if pet.apply_animation_result(purpose, result):
                pet.state = purpose if purpose in {"idle", "move"} else "idle"
                return True
        return False

    def apply_scene_reaction_with_preferences(self, pet, preferred_moods, forbidden=None, preserve=False):
        preferred = list(preferred_moods or ())
        forbidden = set(forbidden or ())
        if (
            preserve and
            getattr(pet, "current_purpose", "") == "idle" and
            getattr(pet, "current_mood_tag", "") in preferred and
            getattr(pet, "current_mood_tag", "") not in forbidden
        ):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return False
        result = asset_manager.get_safe_reaction_result(
            "idle",
            preferred,
            forbidden=list(forbidden),
        )
        if pet.apply_animation_result("idle", result):
            pet.state = "idle"
            return True
        return False

    def get_shared_food_capability_contexts(self, item_kind, pet_name, capability_name):
        return self.shared_food_scene_executor.get_shared_food_capability_contexts(
            self,
            item_kind,
            pet_name,
            capability_name,
        )

    def get_shared_food_candidate_result(
        self,
        pet,
        candidate,
        preferred_moods,
        contexts=(),
    ):
        return self.shared_food_scene_executor.get_shared_food_candidate_result(
            self,
            pet,
            candidate,
            preferred_moods,
            contexts,
        )

    def filter_shared_food_candidates(
        self,
        pet,
        item_kind,
        capability_name,
        candidates,
        preferred_moods,
    ):
        return self.shared_food_scene_executor.filter_shared_food_candidates(
            self,
            pet,
            item_kind,
            capability_name,
            candidates,
            preferred_moods,
        )

    def build_runtime_shared_food_capabilities(
        self,
        profile,
        pet,
        preferred_moods,
    ):
        return self.shared_food_scene_executor.build_runtime_shared_food_capabilities(
            self,
            profile,
            pet,
            preferred_moods,
        )

    def apply_shared_food_capability(
        self,
        pet,
        item_kind,
        capability_name,
        candidates,
        preferred_moods,
        *,
        preserve=False,
    ):
        return self.shared_food_scene_executor.apply_shared_food_capability(
            self,
            pet,
            item_kind,
            capability_name,
            candidates,
            preferred_moods,
            preserve=preserve,
        )

    def apply_shared_food_role_action(
        self,
        pet,
        profile,
        capabilities,
        capability_order,
        preferred_moods,
        *,
        preserve=False,
    ):
        return self.shared_food_scene_executor.apply_shared_food_role_action(
            self,
            pet,
            profile,
            capabilities,
            capability_order,
            preferred_moods,
            preserve=preserve,
        )

    def capture_shared_food_animation(self, pet):
        return self.shared_food_scene_executor.capture_shared_food_animation(self, pet)

    def apply_shared_food_scene_lock_state(self, pet, focus_name):
        return self.shared_food_scene_executor.apply_shared_food_scene_lock_state(
            self,
            pet,
            focus_name,
        )

    def apply_held_item_behavior(self, pet, now):
        item_kind = getattr(pet, "held_item_kind", "")
        if not item_kind:
            return False
        preview_candidates = get_direct_offer_preview_candidates(item_kind, pet.name)
        preferred_moods = get_direct_offer_preferred_moods(item_kind)
        manifest_context = get_direct_offer_preview_context(item_kind, pet.name)
        if item_kind == ITEM_BOTTLE and pet.name != "Tsurumaru Tsuyoshi":
            preview_candidates = get_bottle_feed_holder_idle_candidates(pet.name) or preview_candidates
            preferred_moods = get_bottle_feed_holder_idle_preferred_moods() or preferred_moods
            manifest_context = get_bottle_feed_holder_idle_context(pet.name)
        self.lock_pet_for_offer_scene(pet, "held_item", now + 0.2)
        pet.state = "idle"
        if preview_candidates and preferred_moods:
            if not self.apply_scene_context_with_preferences(
                pet,
                "idle",
                manifest_context,
                preferred_moods,
                preserve=True,
            ) and not pet.ensure_candidate_animation_with_preferences(preview_candidates, preferred_moods):
                pet.ensure_candidate_animation(preview_candidates)
        pet.perception_situation_tag = "locked"
        pet.expression_animation_context = "ambient"
        pet.expression_relation_overlay = "none"
        pet.expression_focus_target_name = ""
        pet.expression_posture_bias = "neutral"
        pet.expression_spacing_bias = "neutral"
        pet.expression_look_at_target = False
        pet.relationship_focus_target_name = ""
        pet.refresh_movement_state()
        self.update_held_offer_widget_position(
            pet.held_item_widget,
            pet,
            item_kind,
            prefer_preview=True,
        )
        return True

    def update_pet_held_items(self, now):
        handled = False
        for pet in self.pets_list:
            if not getattr(pet, "held_item_kind", "") or getattr(pet, "held_item_widget", None) is None:
                continue
            if not pet.isVisible():
                self.clear_pet_held_item(pet)
                handled = True
                continue
            if not (
                self.offer_scene is not None and
                self.offer_scene.scene_kind == "honey_guard" and
                self.offer_scene.target_name == pet.name
            ) and not (
                self.offer_scene is not None and
                self.offer_scene.scene_kind == "bottle_feed" and
                self.offer_scene.actor_name == pet.name
            ) and not (
                self.offer_scene is not None and
                self.offer_scene.scene_kind == "shared_food" and
                self.offer_scene.actor_name == pet.name
            ):
                handled = self.apply_held_item_behavior(pet, now) or handled
            if (
                pet.name == "Tsurumaru Tsuyoshi" and
                pet.held_item_kind == ITEM_HONEY and
                self.offer_scene is None
            ):
                guardian_name = self.choose_honey_guardian_for_child(pet)
                if guardian_name:
                    self.start_honey_guard_scene(pet, source=getattr(pet, "held_item_source", "offer_tray"))
                    handled = True
            if (
                pet.name != "Tsurumaru Tsuyoshi" and
                pet.held_item_kind == ITEM_BOTTLE and
                self.offer_scene is None
            ):
                child_pet = self.choose_bottle_feed_child_for_holder(pet, now=now)
                if child_pet is not None:
                    self.start_bottle_feed_scene(pet, source=getattr(pet, "held_item_source", "offer_tray"))
                    handled = True
        return handled

    def start_direct_offer_scene(self, item_kind, target_pet, source="offer_tray"):
        return self.direct_hover_scene_executor.start_direct_offer_scene(
            self,
            item_kind,
            target_pet,
            source=source,
            now=app_now(),
            roll=random.random(),
        )

    def start_bottle_feed_scene(self, holder_pet, source="offer_tray"):
        return self.bottle_honey_scene_executor.start_bottle_feed_scene(
            self,
            holder_pet,
            source=source,
            now=app_now(),
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

    def evaluate_runtime_shared_food_partner(self, profile, holder_pet, partner_pet, now):
        return self.shared_food_scene_executor.evaluate_runtime_shared_food_partner(
            self,
            profile,
            holder_pet,
            partner_pet,
            now,
        )

    def get_shared_food_approach_timeout(self, profile, holder_pet, partner_pet):
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
            now=app_now() if now is None else float(now),
        )

    def start_shared_food_scene(
        self,
        holder_pet,
        partner_pet=None,
        *,
        profile=None,
        source="offer_tray",
        outcome_roll=None,
    ):
        return self.shared_food_scene_executor.start_shared_food_scene(
            self,
            holder_pet,
            partner_pet,
            profile=profile,
            source=source,
            outcome_roll=outcome_roll,
            now=app_now(),
            roll_provider=random.random,
        )

    def start_honey_guard_scene(self, child_pet, source="offer_tray"):
        return self.bottle_honey_scene_executor.start_honey_guard_scene(
            self,
            child_pet,
            source=source,
            now=app_now(),
        )

    def record_offer_event(self, item_kind, actor_name, target_name, scene_kind, source="offer_tray"):
        if item_kind == ITEM_BOTTLE and scene_kind == "direct_accept":
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_bottle_success" if source == "offer_tray" else "ground_bottle_pickup",
                summary=(
                    "鶴寶接過奶瓶，安靜地喝了起來。"
                    if source == "offer_tray"
                    else "鶴寶路過時撿起地上的奶瓶，乖乖地喝了起來。"
                ),
                actor_name="Player" if source == "offer_tray" else target_name,
                target_name=target_name,
                household_pressure_delta=-3.0,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if item_kind == ITEM_BOTTLE and scene_kind == "bottle_feed":
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_bottle_feed" if source == "offer_tray" else "ground_bottle_feed",
                summary=(
                    f"{actor_name} 拿著奶瓶陪在一旁，看著鶴寶乖乖喝了幾口。"
                    if source == "offer_tray"
                    else f"{actor_name} 撿起地上的奶瓶後陪在一旁，讓鶴寶安心喝了幾口。"
                ),
                actor_name=actor_name,
                target_name=target_name,
                household_pressure_delta=-3.0,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "direct_accept":
            if source == "offer_tray":
                summary = (
                    "天狼星接過蜂蜜，神情明顯放鬆了些。"
                    if target_name == "Sirius Symboli"
                    else "帝寶接過蜂蜜，露出心滿意足的表情。"
                )
            else:
                summary = (
                    "天狼星路過時撿起地上的蜂蜜，神情明顯放鬆了些。"
                    if target_name == "Sirius Symboli"
                    else "帝寶路過時撿起地上的蜂蜜，露出心滿意足的表情。"
                )
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_honey_success" if source == "offer_tray" else "ground_honey_pickup",
                summary=summary,
                actor_name="Player" if source == "offer_tray" else target_name,
                target_name=target_name,
                household_pressure_delta=-1.0,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if scene_kind == "direct_accept":
            item_definition = get_offer_item_definition(item_kind)
            item_label = item_definition.label if item_definition is not None else item_kind
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type=(f"offer_{item_kind}_success" if source == "offer_tray" else f"ground_{item_kind}_pickup"),
                summary=(
                    f"{target_name} 接過了{item_label}，看起來相當滿足。"
                    if source == "offer_tray"
                    else f"{target_name} 路過時撿起地上的{item_label}，看起來相當滿足。"
                ),
                actor_name="Player" if source == "offer_tray" else target_name,
                target_name=target_name,
                household_pressure_delta=-1.0,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "honey_guard":
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_honey_guarded",
                summary=f"{actor_name} 趕緊把鶴寶手邊的蜂蜜拿走，免得她誤食。",
                actor_name=actor_name,
                target_name=target_name,
                relation_delta={"trust": -0.05, "attachment": 0.05, "tension": 0.35},
                household_pressure_delta=1.5,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if item_kind == ITEM_HONEY and scene_kind == "deny_only":
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_honey_denied",
                summary="鶴寶眼巴巴地看著蜂蜜，最後還是沒能拿到。",
                actor_name="Player" if source == "offer_tray" else target_name,
                target_name=target_name,
                household_pressure_delta=2.0,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )
            return
        if scene_kind == "hover_timeout_reaction":
            item_definition = get_offer_item_definition(item_kind)
            item_label = item_definition.label if item_definition is not None else item_kind
            self.record_household_event(
                occurred_at=app_now(),
                category="player_offer",
                event_type="offer_hover_timeout",
                summary=f"{target_name} 等了太久都沒拿到{item_label}，明顯鬧起了情緒。",
                actor_name="Player",
                target_name=target_name,
                household_pressure_delta=2.5,
                metadata={"source": source, "item_kind": item_kind, "scene_kind": scene_kind},
            )

    def record_shared_food_event(self, profile, shared_state, source="offer_tray"):
        return self.shared_food_scene_executor.record_shared_food_event(
            self,
            profile,
            shared_state,
            source=source,
            now=app_now(),
        )

    def apply_shared_food_outcome_effects(self, shared_state):
        return self.shared_food_scene_executor.apply_shared_food_outcome_effects(
            self,
            shared_state,
        )

    def apply_offer_mood_reward(self, target_name, amount=10.0):
        pet = self.find_pet_by_name(target_name, visible_only=False)
        if pet is None:
            return False
        clear_negative_afterglow = getattr(pet, "clear_negative_afterglow", None)
        if callable(clear_negative_afterglow):
            clear_negative_afterglow()
        else:
            pet.negative_afterglow_until = 0.0
            pet.negative_afterglow_preferred_moods = ()
            pet.negative_afterglow_forbidden_moods = ()
        pet.offer_hover_reaction_cooldown_until = 0.0
        pet.mood_score = min(100.0, float(pet.mood_score) + float(amount))
        if hasattr(pet, "sync_mood_state_with_score"):
            pet.sync_mood_state_with_score()
        if hasattr(pet, "pop_heart"):
            pet.pop_heart()
        return True

    def drop_ground_offer_item(self, item_kind, global_pos):
        return self.ground_item_coordinator.drop_item(
            item_kind,
            global_pos,
            build_widget=self.build_offer_item_widget,
        )

    def place_ground_offer_item(self, dropped_item, global_pos):
        return self.ground_item_coordinator.place_item(dropped_item, global_pos)

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
        profiler_started_at = time.perf_counter()
        now = app_now() if now is None else float(now)
        held_item_handled = self.update_pet_held_items(now)
        ground_handled = self.update_ground_offer_items(now)
        scene_canceled = self.cancel_offer_scene_if_hidden_participants()
        if self.offer_scene is None and self.offer_hover_target_name:
            result = self.update_offer_hover_preview(now) or scene_canceled or held_item_handled or ground_handled
            self.profiler.record_section(
                "offer.update",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )
            return result
        if self.offer_scene is None:
            result = scene_canceled or held_item_handled or ground_handled
            self.profiler.record_section(
                "offer.update",
                (time.perf_counter() - profiler_started_at) * 1000.0,
            )
            return result
        scene_result = self.item_scene_coordinator.update(
            self,
            now,
            update_handlers={
                "direct_accept": self.update_direct_offer_scene,
                "hover_timeout_reaction": self.update_offer_hover_timeout_reaction_scene,
                "honey_guard": self.update_honey_guard_scene,
                "bottle_feed": self.update_bottle_feed_scene,
                "shared_food": self.update_shared_food_scene,
                "deny_only": self.update_deny_only_offer_scene,
            },
            clear_scene_callback=self.clear_offer_scene,
        )
        result = scene_result.handled or scene_canceled or held_item_handled or ground_handled
        self.profiler.record_section(
            "offer.update",
            (time.perf_counter() - profiler_started_at) * 1000.0,
        )
        return result

    def update_offer_hover_preview(self, now):
        return self.direct_hover_scene_executor.update_offer_hover_preview(self, now)

    def update_offer_hover_timeout_reaction_scene(self, now):
        return self.direct_hover_scene_executor.update_offer_hover_timeout_reaction_scene(self, now)

    def update_direct_offer_scene(self, now):
        return self.direct_hover_scene_executor.update_direct_offer_scene(
            self,
            now,
            roll_provider=random.random,
        )

    def update_deny_only_offer_scene(self, now):
        return self.direct_hover_scene_executor.update_deny_only_offer_scene(self, now)

    def update_bottle_feed_scene(self, now):
        return self.bottle_honey_scene_executor.update_bottle_feed_scene(self, now)

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

    def resolve_active_shared_food_outcome(self, profile, holder_pet, partner_pet):
        return self.shared_food_scene_executor.resolve_active_shared_food_outcome(
            self,
            profile,
            holder_pet,
            partner_pet,
        )

    def get_shared_food_consume_stage_seconds(self, profile, outcome_key):
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

    def update_shared_food_scene(self, now):
        return self.shared_food_scene_executor.update_shared_food_scene(self, now)

    def update_honey_guard_scene(self, now):
        return self.bottle_honey_scene_executor.update_honey_guard_scene(self, now)


DEFAULT_PET_SPECS = (
    PetSpec("Symboli Rudolf", 0.45, "滷豆腐"),
    PetSpec("Tokai Teio", 0.35, "帝寶", initially_visible=False),
    PetSpec("Sirius Symboli", 0.4, "天狼星", initially_visible=False),
    PetSpec("Tsurumaru Tsuyoshi", 0.3, "鶴寶", initially_visible=False),
    PetSpec("Air Groove", 0.4, "氣槽", initially_visible=False),
)


def build_default_pet_specs():
    return DEFAULT_PET_SPECS


def create_pets(assets_dir, pet_specs, settings_provider, window_tracker):
    pets_dict, pets_list = {}, []
    for index, spec in enumerate(pet_specs):
        character_path = os.path.join(assets_dir, spec.folder_name)
        if not os.path.exists(character_path):
            continue

        pet = TanukiPet(
            spec.folder_name,
            character_path,
            spec.scale,
            settings_provider=settings_provider,
            window_tracker=window_tracker,
        )
        pet.move(500 + (index * 100), 600)
        if not spec.initially_visible:
            pet.user_visible = False
            pet.hide()

        pets_dict[spec.folder_name] = {"pet": pet, "name": spec.display_name}
        pets_list.append(pet)
    return pets_dict, pets_list


def build_dashboard(pets_dict, settings_provider, save_scheduler):
    left_screen = min(QApplication.screens(), key=lambda screen: screen.geometry().x())
    available_rect = left_screen.availableGeometry()
    dashboard = Dashboard(
        available_rect,
        pets_dict,
        AssetManager.get_resource_path,
        settings_provider=settings_provider,
        save_scheduler=save_scheduler,
    )
    return dashboard, available_rect


def register_runtime_timer(
    app,
    interval_ms,
    callback,
    speed_scaled=True,
    minimum_interval_ms=1,
    profiler=None,
    timer_name="",
    repeat_count_provider=None,
    pass_step_delta=False,
):
    timer = QTimer(app)
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    last_callback_started_at = 0.0

    def run_callback():
        nonlocal last_callback_started_at
        callback_started_at = time.perf_counter()
        callback_interval_ms = 0.0
        if last_callback_started_at > 0.0:
            callback_interval_ms = (callback_started_at - last_callback_started_at) * 1000.0
        last_callback_started_at = callback_started_at
        repeat_count = 1
        if speed_scaled:
            repeat_count = SIM_CLOCK.get_timer_repeat_count(
                interval_ms,
                minimum_interval_ms=minimum_interval_ms,
            )
        repeat_count = resolve_timer_repeat_count(
            repeat_count,
            repeat_count_provider=repeat_count_provider,
        )
        callback_step_delta = None
        if pass_step_delta:
            callback_step_delta = get_timer_callback_step_delta(
                SIM_CLOCK,
                interval_ms,
                float(timer.interval()),
                repeat_count=repeat_count,
            )
        for _ in range(int(repeat_count)):
            if pass_step_delta:
                callback(callback_step_delta)
            else:
                callback()
        if profiler is not None and timer_name:
            profiler.record_timer(
                timer_name,
                duration_ms=(time.perf_counter() - callback_started_at) * 1000.0,
                now=time.perf_counter(),
                repeat_count=repeat_count,
                interval_ms=callback_interval_ms,
            )

    timer.timeout.connect(run_callback)
    timer.start(interval_ms)
    if speed_scaled:
        SIM_CLOCK.register_timer(
            timer,
            interval_ms,
            minimum_interval_ms=minimum_interval_ms,
        )
    return timer


def start_runtime_timers(runtime):
    return {
        "mood": register_runtime_timer(
            runtime.app,
            3000,
            lambda: [pet.update_mood(runtime.pets_list) for pet in runtime.pets_list],
            speed_scaled=False,
            profiler=runtime.profiler,
            timer_name="mood",
        ),
        "physics": register_runtime_timer(
            runtime.app,
            30,
            lambda: run_pet_physics_step(runtime.pets_list),
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="physics",
        ),
        "logic": register_runtime_timer(
            runtime.app,
            30,
            lambda step_delta: runtime.logic_scheduler.run(
                runtime.pets_list,
                speed=SIM_CLOCK.speed,
                step_delta=step_delta,
            ),
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="logic",
            repeat_count_provider=lambda default_repeat_count: (
                runtime.logic_scheduler.resolve_repeat_count(
                    runtime.pets_list,
                    default_repeat_count,
                    speed=SIM_CLOCK.speed,
                )
            ),
            pass_step_delta=True,
        ),
        "windows": register_runtime_timer(
            runtime.app,
            150,
            runtime.window_tracker.refresh,
            speed_scaled=False,
            profiler=runtime.profiler,
            timer_name="windows",
        ),
        "offer": register_runtime_timer(
            runtime.app,
            30,
            runtime.update_offer_scene,
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="offer",
        ),
        "household": register_runtime_timer(
            runtime.app,
            1000,
            runtime.update_household_events,
            minimum_interval_ms=250,
            profiler=runtime.profiler,
            timer_name="household",
        ),
    }


def ensure_visible_pets(pets_list):
    for pet in pets_list:
        if not getattr(pet, "user_visible", True):
            continue
        if pet.care_lock_mode == "hidden" and pet.is_under_care(app_now()):
            continue
        clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(pet, pet.x(), pet.y())
        if (clamped_x, clamped_y) != (pet.x(), pet.y()):
            pet.move(clamped_x, clamped_y)
        pet.show()
        pet.raise_()
        pet.update()


def create_runtime(app=None):
    app = app or QApplication(sys.argv)
    settings_provider = RuntimeSettings()
    config_store = ConfigStore(
        config_path=AssetManager.get_resource_path("config.json"),
        clamp_pet_position=DesktopGeometry.clamp_widget_position,
    )
    save_scheduler = ConfigSaveScheduler(lambda: config_store)
    window_tracker = WindowTracker()

    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir):
        raise FileNotFoundError(assets_dir)

    pets_dict, pets_list = create_pets(
        assets_dir,
        build_default_pet_specs(),
        settings_provider,
        window_tracker,
    )
    dashboard, available_rect = build_dashboard(pets_dict, settings_provider, save_scheduler)
    window_tracker.refresh()

    sensor = SensorZone(dashboard)
    sensor.setGeometry(available_rect.left(), available_rect.bottom() - 300, 20, 300)
    dashboard.set_sensor_zone(sensor)
    monitor = GlobalMouseListener(dashboard)

    runtime = TanukiAppRuntime(
        app=app,
        settings_provider=settings_provider,
        config_store=config_store,
        save_scheduler=save_scheduler,
        window_tracker=window_tracker,
        pets_dict=pets_dict,
        pets_list=pets_list,
        dashboard=dashboard,
        sensor=sensor,
        monitor=monitor,
        shell=DashboardShellLifecycle(sensor=sensor, monitor=monitor),
    )
    for pet in pets_list:
        pet.runtime_profiler = runtime.profiler
    seed_default_household_events(runtime.household, runtime.household_event_log, occurred_at=app_now())
    runtime.household_coordinator.reset_event_schedule(app_now())
    dashboard.set_household_data_providers(
        household_state_provider=lambda runtime=runtime: runtime.household,
        household_events_provider=lambda limit=24, runtime=runtime: runtime.recent_household_events(limit=limit),
    )
    dashboard.set_household_action_providers(
        household_donate_provider=lambda amount=100, runtime=runtime: runtime.donate_household_fund(amount=amount),
    )
    dashboard.set_household_persistence_providers(
        household_capture_provider=lambda runtime=runtime: runtime.capture_household_persistence_state(),
        household_load_provider=lambda payload, runtime=runtime: runtime.apply_household_persistence_state(payload),
        world_mode_change_provider=lambda mode, previous_mode=None, runtime=runtime: runtime.handle_world_mode_change(
            mode,
            previous_mode=previous_mode,
        ),
    )
    dashboard.set_offer_interaction_provider(
        offer_drop_provider=lambda item_kind, global_pos, runtime=runtime: runtime.handle_offer_drop(
            item_kind=item_kind,
            global_pos=global_pos,
        ),
        offer_hover_provider=lambda item_kind, global_pos, runtime=runtime: runtime.handle_offer_hover(
            item_kind=item_kind,
            global_pos=global_pos,
        ),
        offer_hover_clear_provider=lambda runtime=runtime: runtime.clear_offer_hover(),
    )
    config_store.bind(dashboard, pets_dict)
    runtime.timers = start_runtime_timers(runtime)
    runtime.app.aboutToQuit.connect(runtime.shutdown)
    return runtime


def run_application():
    runtime = create_runtime()
    runtime.dashboard.show()
    runtime.sensor.show()
    QTimer.singleShot(0, lambda: ensure_visible_pets(runtime.pets_list))
    QTimer.singleShot(300, lambda: ensure_visible_pets(runtime.pets_list))
    return runtime.app.exec()
