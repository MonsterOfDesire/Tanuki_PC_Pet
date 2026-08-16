from .achievement_catalog import load_achievement_catalog
from .achievement_gameplay_bridge import AchievementGameplayBridge
from .achievement_presenter import build_achievement_cabinet_snapshot
from .achievement_runtime_service import AchievementRuntimeService
from .achievement_state import (
    apply_achievement_persistence_state,
    capture_achievement_persistence_state,
)
from .transformation_profiles import get_pet_form_key


class AchievementRuntimeCoordinator:
    """Application boundary for achievement lifecycle and persistence."""

    def __init__(
        self,
        *,
        state,
        eligibility_guard,
        time_scale_provider,
        world_mode_provider,
        catalog=None,
        service=None,
        gameplay_bridge=None,
        save_callback=None,
        unlock_callback=None,
    ):
        self.state = state
        self.eligibility_guard = eligibility_guard
        self.time_scale_provider = time_scale_provider
        self.world_mode_provider = world_mode_provider
        self.save_callback = save_callback
        self.unlock_callback = unlock_callback
        if service is None:
            if catalog is None:
                raise ValueError("achievement catalog is required")
            service = AchievementRuntimeService(
                catalog=catalog,
                state=state,
                eligibility_guard=eligibility_guard,
                time_scale_provider=time_scale_provider,
                state_changed_callback=self.handle_state_changed,
            )
        self.service = service
        self.gameplay_bridge = gameplay_bridge or AchievementGameplayBridge(
            service=self.service,
            world_mode_provider=world_mode_provider,
        )

    @classmethod
    def create_default(
        cls,
        *,
        resource_resolver,
        state,
        eligibility_guard,
        time_scale_provider,
        world_mode_provider,
        save_callback=None,
        unlock_callback=None,
    ):
        catalog = load_achievement_catalog(
            resource_resolver("UI/trophies/achievement_catalog_draft.json")
        )
        return cls(
            state=state,
            eligibility_guard=eligibility_guard,
            time_scale_provider=time_scale_provider,
            world_mode_provider=world_mode_provider,
            catalog=catalog,
            save_callback=save_callback,
            unlock_callback=unlock_callback,
        )

    def handle_state_changed(self, result):
        if callable(self.save_callback):
            self.save_callback()
        unlocked_ids = tuple(
            getattr(result, "unlocked_achievement_ids", ()) or ()
        )
        if unlocked_ids and callable(self.unlock_callback):
            self.unlock_callback(unlocked_ids)

    def build_cabinet_snapshot(self):
        return build_achievement_cabinet_snapshot(
            self.service.catalog,
            self.state,
        )

    def consume_entry(self, entry):
        return self.consume_payload(getattr(entry, "metadata", None))

    def consume_payload(self, metadata, *, instantaneous=False):
        if not isinstance(metadata, dict):
            return None
        if not str(metadata.get("activity_event_name", "") or ""):
            return None
        if instantaneous:
            return self.service.consume_instantaneous_activity_metadata(
                metadata
            )
        return self.service.consume_activity_metadata(metadata)

    def begin_activity_session(
        self,
        activity_id,
        *,
        activity_coordinator,
        world_mode,
    ):
        activity = activity_coordinator.get_activity(str(activity_id or ""))
        if activity is None:
            return False
        return self.begin_explicit_activity_session(
            activity_id=activity.activity_id,
            world_mode=str(
                activity.metadata.get("world_mode", world_mode) or world_mode
            ),
            source=activity.source,
            execution_mode=str(
                activity.metadata.get("execution_mode", "") or ""
            ),
            started_at=float(activity.started_at),
        )

    def begin_explicit_activity_session(
        self,
        *,
        activity_id,
        world_mode,
        source,
        execution_mode,
        started_at,
    ):
        return self.service.begin_activity_session(
            activity_id=str(activity_id or ""),
            world_mode=str(world_mode or ""),
            source=str(source or ""),
            execution_mode=str(execution_mode or ""),
            started_at=float(started_at),
        )

    def cancel_activity_session(self, activity_id, *, reason):
        return self.service.cancel_activity_session(
            str(activity_id or ""),
            reason=str(reason or "activity_cancelled"),
        )

    def begin_transformation(self, result, *, started_at):
        return self.gameplay_bridge.begin_transformation(
            result,
            started_at=float(started_at),
        )

    def complete_transformation(self, result, *, occurred_at):
        return self.gameplay_bridge.complete_transformation(
            result,
            occurred_at=float(occurred_at),
        )

    def handle_ambient_animation_context(
        self,
        pet,
        context,
        *,
        now,
    ):
        return self.gameplay_bridge.handle_ambient_animation_context(
            character_name=str(getattr(pet, "name", "") or ""),
            context=str(context or ""),
            now=float(now),
        )

    def cancel_orphaned_transformations(self, pets):
        active_names = []
        for pet in pets:
            state = getattr(pet, "transformation_state", None)
            if state is not None and bool(getattr(state, "active", False)):
                active_names.append(str(getattr(pet, "name", "") or ""))
        self.gameplay_bridge.cancel_orphaned_transformations(active_names)

    def handle_sleep_result(self, result, *, now):
        return self.gameplay_bridge.handle_sleep_result(
            result,
            now=float(now),
        )

    def begin_sleep_session(self, activity_id, *, metadata):
        return self.gameplay_bridge.begin_sleep_session(
            str(activity_id or ""),
            metadata=metadata,
        )

    def sync_sleep_join_sessions(self, join_attempts, *, now):
        self.gameplay_bridge.sync_sleep_join_sessions(
            join_attempts,
            now=float(now),
        )

    def complete_sleep_group_join(
        self,
        participant_name,
        *,
        activity,
        now,
    ):
        return self.gameplay_bridge.complete_sleep_group_join(
            str(participant_name or ""),
            activity=activity,
            now=float(now),
        )

    def update_sleep_snapshot(self, activities, *, now):
        return self.gameplay_bridge.update_sleep_snapshot(
            activities,
            now=float(now),
        )

    def handle_care_event(
        self,
        stage,
        caregiver,
        target,
        *,
        now,
        success=None,
        care_mode="",
    ):
        return self.gameplay_bridge.handle_care_event(
            str(stage or ""),
            caregiver_name=str(getattr(caregiver, "name", "") or ""),
            target_name=str(getattr(target, "name", "") or ""),
            caregiver_form=get_pet_form_key(caregiver),
            now=float(now),
            success=success,
            care_mode=str(care_mode or ""),
        )

    def begin_offer_session(self, *, scene_id, source, started_at):
        return self.gameplay_bridge.begin_offer_session(
            scene_id=str(scene_id or ""),
            source=str(source or "offer_tray"),
            started_at=float(started_at),
        )

    def build_honey_guard_metadata(self, **fields):
        return self.gameplay_bridge.build_honey_guard_metadata(**fields)

    def build_shared_food_metadata(self, **fields):
        return self.gameplay_bridge.build_shared_food_metadata(**fields)

    def capture_persistence_state(self):
        return capture_achievement_persistence_state(self.state)

    def apply_persistence_state(self, payload):
        return apply_achievement_persistence_state(payload, self.state)

    def observe_world_mode(self, world_mode):
        return self.eligibility_guard.observe_world_mode(str(world_mode or ""))

    def observe_time_scale(self, time_scale):
        return self.eligibility_guard.observe_time_scale(time_scale)

    def cancel_all_activity_sessions(self, *, reason):
        return self.service.cancel_all_activity_sessions(reason=reason)
