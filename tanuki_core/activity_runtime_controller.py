from __future__ import annotations

import math

from .activity_interaction_rules import (
    CHORUS_SLEEP_WAKE_AFTERGLOW_SECONDS,
    CHORUS_SLEEP_WAKE_BAND,
    should_chorus_wake_sleeping_pet,
)

from .chorus_event_adapter import ChorusEventAdapter
from .chorus_executor import ChorusExecutor
from .race_event_adapter import RaceEventAdapter
from .race_executor import RaceExecutor
from .rudolf_work_executor import RudolfWorkExecutor
from .rudolf_work_rules import RUDOLF_NAME
from .rudolf_work_settlement import RudolfWorkSettlementAdapter
from .runtime import app_now
from .sleep_executor import SleepExecutor
from .sleep_rules import (
    SLEEP_ACTIVITY_KIND,
    SLEEP_TRIGGER_OBSERVED_JOIN,
    SLEEPING_PHASE,
)
from .transformation_profiles import (
    CAPABILITY_SLEEP,
    pet_form_allows_capability,
)


class ActivityRuntimeController:
    """Application boundary for work, sleep, race and chorus lifecycle."""

    def __init__(
        self,
        *,
        activity_coordinator,
        work_settlement_adapter,
        work_executor,
        sleep_executor,
        race_executor,
        race_event_adapter,
        chorus_executor,
        chorus_event_adapter,
        achievement_runtime_coordinator,
        transformation_runtime_controller,
        pets,
        pet_registry,
        household,
        household_event_schedule,
        world_mode_provider,
        record_household_event,
        record_resolved_household_event,
        apply_race_mood_reward,
        apply_reverse_race_relationship_reward,
        apply_chorus_mood_reward,
        apply_chorus_relationship_reward,
        refresh_relationship_table=None,
        now_provider=app_now,
    ):
        self.activity_coordinator = activity_coordinator
        self.work_settlement_adapter = work_settlement_adapter
        self.work_executor = work_executor
        self.sleep_executor = sleep_executor
        self.race_executor = race_executor
        self.race_event_adapter = race_event_adapter
        self.chorus_executor = chorus_executor
        self.chorus_event_adapter = chorus_event_adapter
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.transformation_runtime_controller = (
            transformation_runtime_controller
        )
        self.pets = pets
        self.pet_registry = pet_registry
        self.household = household
        self.household_event_schedule = household_event_schedule
        self.world_mode_provider = world_mode_provider
        self.record_household_event = record_household_event
        self.record_resolved_household_event = (
            record_resolved_household_event
        )
        self.apply_race_mood_reward = apply_race_mood_reward
        self.apply_reverse_race_relationship_reward = (
            apply_reverse_race_relationship_reward
        )
        self.apply_chorus_mood_reward = apply_chorus_mood_reward
        self.apply_chorus_relationship_reward = (
            apply_chorus_relationship_reward
        )
        self.refresh_relationship_table = refresh_relationship_table
        self.now_provider = now_provider

    @classmethod
    def create_default(
        cls,
        *,
        activity_coordinator,
        runtime_adapter,
        race_frequency_provider,
        chorus_frequency_provider,
        **kwargs,
    ):
        work_settlement_adapter = RudolfWorkSettlementAdapter()
        return cls(
            activity_coordinator=activity_coordinator,
            work_settlement_adapter=work_settlement_adapter,
            work_executor=RudolfWorkExecutor(
                coordinator=activity_coordinator,
                runtime_adapter=runtime_adapter,
                settlement_adapter=work_settlement_adapter,
            ),
            sleep_executor=SleepExecutor(
                coordinator=activity_coordinator,
                runtime_adapter=runtime_adapter,
            ),
            race_executor=RaceExecutor(
                coordinator=activity_coordinator,
                runtime_adapter=runtime_adapter,
                frequency_provider=race_frequency_provider,
            ),
            race_event_adapter=RaceEventAdapter(),
            chorus_executor=ChorusExecutor(
                coordinator=activity_coordinator,
                runtime_adapter=runtime_adapter,
                frequency_provider=chorus_frequency_provider,
            ),
            chorus_event_adapter=ChorusEventAdapter(),
            **kwargs,
        )

    def _now(self, now):
        return self.now_provider() if now is None else float(now)

    def _world_mode(self):
        return str(self.world_mode_provider() or "")

    def _begin_activity_session(self, activity_id):
        return self.achievement_runtime_coordinator.begin_activity_session(
            activity_id,
            activity_coordinator=self.activity_coordinator,
            world_mode=self._world_mode(),
        )

    def _cancel_activity_session(self, activity_id, *, reason):
        return self.achievement_runtime_coordinator.cancel_activity_session(
            activity_id,
            reason=reason,
        )

    def update_work(self, now=None):
        now = self._now(now)
        result = self.work_executor.update(
            now=now,
            world_mode=self._world_mode(),
            household=self.household,
            event_schedule=self.household_event_schedule,
            rudolf_pet=self.pet_registry.find_by_name(
                RUDOLF_NAME,
                visible_only=False,
            ),
            record_household_event=self.record_resolved_household_event,
        )
        if result.started:
            self._begin_activity_session(result.activity_id)
        if result.interrupted or result.finished:
            self._cancel_activity_session(
                result.activity_id,
                reason=result.reason,
            )
        return result

    def preview_work(self, now=None):
        return self.work_executor.start_preview(
            now=self._now(now),
            world_mode=self._world_mode(),
            rudolf_pet=self.pet_registry.find_by_name(
                RUDOLF_NAME,
                visible_only=False,
            ),
        )

    def is_work_preview_active(self):
        return self.work_executor.is_preview_active()

    def update_race(self, now=None):
        result = self.race_executor.update(
            now=self._now(now),
            world_mode=self._world_mode(),
            pets=self.pets,
            record_race_event=self.record_race_event,
        )
        if result.started:
            self._begin_activity_session(result.activity_id)
        if result.interrupted or result.finished:
            self._cancel_activity_session(
                result.activity_id,
                reason=result.reason,
            )
        return result

    def preview_race(self, now=None):
        return self.race_executor.start_preview(
            now=self._now(now),
            world_mode=self._world_mode(),
            rudolf_pet=self.pet_registry.find_by_name(
                "Symboli Rudolf",
                visible_only=False,
            ),
            teio_pet=self.pet_registry.find_by_name(
                "Tokai Teio",
                visible_only=False,
            ),
        )

    def is_race_preview_active(self):
        return self.race_executor.is_preview_active()

    def record_race_event(self, event):
        entry = self.race_event_adapter.apply(
            event,
            record_household_event=self.record_household_event,
            race_statistics=self.household.race_statistics,
            apply_winner_mood_reward=self.apply_race_mood_reward,
            apply_reverse_relationship_reward=(
                self.apply_reverse_race_relationship_reward
            ),
        )
        if self.transformation_runtime_controller is not None:
            self.transformation_runtime_controller.observe_race_event(event)
        if (
            entry is not None
            and event.event_type == "race_completed"
            and callable(self.refresh_relationship_table)
        ):
            self.refresh_relationship_table()
        return entry

    def update_chorus(self, now=None):
        now = self._now(now)
        results = self.chorus_executor.update(
            now=now,
            world_mode=self._world_mode(),
            pets=self.pets,
            record_chorus_event=self.record_chorus_event,
        )
        for result in tuple(results or ()):
            if result.started:
                session = self.chorus_executor.session
                if session is not None:
                    self.achievement_runtime_coordinator.begin_explicit_activity_session(
                        activity_id=session.session_id,
                        world_mode=session.world_mode,
                        source=session.source,
                        execution_mode="autonomous",
                        started_at=session.started_at,
                    )
            if result.interrupted or result.finished:
                self._cancel_activity_session(
                    result.session_id,
                    reason=result.reason,
                )
        self._wake_sleepers_near_chorus(now=now)
        return results

    def _wake_sleepers_near_chorus(self, *, now):
        session = getattr(self.chorus_executor, "session", None)
        if session is None:
            return ()
        session_participants = getattr(session, "participants", {}) or {}
        if not hasattr(session_participants, "values"):
            return ()
        pets_by_name = {
            str(getattr(pet, "name", "") or ""): pet
            for pet in self.pets
        }
        performers = []
        for participant in tuple(session_participants.values()):
            if not bool(getattr(participant, "is_performer", False)):
                continue
            if str(getattr(participant, "phase", "") or "") != "performing":
                continue
            performer = pets_by_name.get(
                str(getattr(participant, "name", "") or "")
            )
            if performer is not None:
                performers.append(performer)
        if not performers:
            return ()

        wake_results = []
        for sleeper in self.pets:
            state = getattr(sleeper, "activity_state", None)
            if (
                str(getattr(state, "activity_kind", "") or "")
                != SLEEP_ACTIVITY_KIND
                or str(getattr(state, "phase", "") or "")
                != SLEEPING_PHASE
            ):
                continue
            nearest_distance = min(
                self._pet_center_distance(sleeper, performer)
                for performer in performers
            )
            if not should_chorus_wake_sleeping_pet(
                distance=nearest_distance,
                performer_phase="performing",
                sleeper_phase=SLEEPING_PHASE,
            ):
                continue
            result = self.sleep_executor.request_early_wake(
                sleeper,
                now=now,
                reason="chorus_noise",
                waking_band_override=CHORUS_SLEEP_WAKE_BAND,
                visual_afterglow_seconds=(
                    CHORUS_SLEEP_WAKE_AFTERGLOW_SECONDS
                ),
            )
            if result.handled:
                wake_results.append(result)
                self.achievement_runtime_coordinator.handle_sleep_result(
                    result,
                    now=now,
                )
        return tuple(wake_results)

    @staticmethod
    def _pet_center_distance(first, second):
        def center(pet):
            geometry_getter = getattr(pet, "geometry", None)
            if callable(geometry_getter):
                geometry = geometry_getter()
                center_getter = getattr(geometry, "center", None)
                if callable(center_getter):
                    point = center_getter()
                    return float(point.x()), float(point.y())
            x_getter = getattr(pet, "x", None)
            y_getter = getattr(pet, "y", None)
            width_getter = getattr(pet, "width", None)
            height_getter = getattr(pet, "height", None)
            x = float(x_getter()) if callable(x_getter) else 0.0
            y = float(y_getter()) if callable(y_getter) else 0.0
            width = (
                float(width_getter())
                if callable(width_getter)
                else 0.0
            )
            height = (
                float(height_getter())
                if callable(height_getter)
                else 0.0
            )
            return x + width / 2.0, y + height / 2.0

        first_x, first_y = center(first)
        second_x, second_y = center(second)
        return math.hypot(first_x - second_x, first_y - second_y)

    def preview_chorus(self, now=None):
        return self.chorus_executor.start_preview(
            now=self._now(now),
            world_mode=self._world_mode(),
            pets=self.pets,
        )

    def is_chorus_preview_active(self):
        return self.chorus_executor.is_preview_active()

    def record_chorus_event(self, event):
        entry = self.chorus_event_adapter.apply(
            event,
            record_household_event=self.record_household_event,
            apply_mood_reward=self.apply_chorus_mood_reward,
            apply_relationship_reward=self.apply_chorus_relationship_reward,
        )
        if (
            entry is not None
            and event.event_type == "chorus_completed"
            and callable(self.refresh_relationship_table)
        ):
            self.refresh_relationship_table()
        return entry

    def update_sleep(self, now=None):
        now = self._now(now)
        results = self.sleep_executor.update(
            now=now,
            pets=self.pets,
            world_mode=self._world_mode(),
        )
        for result in tuple(results or ()):
            self.achievement_runtime_coordinator.handle_sleep_result(
                result,
                now=now,
            )
        self._sync_sleep_achievements(now=now)
        return results

    def toggle_sleep_control(self, pet_name, now=None):
        now = self._now(now)
        result = self.sleep_executor.request_sandbox_toggle(
            self.pet_registry.find_by_name(
                str(pet_name or ""),
                visible_only=False,
            ),
            now=now,
            world_mode=self._world_mode(),
            pets=self.pets,
        )
        self.achievement_runtime_coordinator.handle_sleep_result(
            result,
            now=now,
        )
        self._update_sleep_snapshot(now=now)
        return result

    def get_sleep_control_state(self, pet_name):
        pet_name = str(pet_name or "")
        pet = self.pet_registry.find_by_name(
            pet_name,
            visible_only=False,
        )
        activity = (
            self.activity_coordinator.get_activity_for_participant(pet_name)
            if pet is not None
            else None
        )
        sleep_activity = (
            activity
            if activity is not None
            and activity.spec.kind == SLEEP_ACTIVITY_KIND
            else None
        )
        visible = bool(
            pet is not None
            and getattr(pet, "user_visible", True)
            and getattr(pet, "isVisible", lambda: False)()
        )
        return {
            "character_name": pet_name,
            "available": pet is not None,
            "visible": visible,
            "active": sleep_activity is not None,
            "phase": str(
                getattr(
                    getattr(sleep_activity, "phase", None),
                    "name",
                    "",
                )
                or ""
            ),
            "form_allows_sleep": bool(
                pet is not None
                and pet_form_allows_capability(pet, CAPABILITY_SLEEP)
            ),
            "world_mode": self._world_mode(),
        }

    def update_sleep_join_behavior(self, pet, all_pets, now=None):
        now = self._now(now)
        participant_name = str(getattr(pet, "name", "") or "")
        before_activity = self.activity_coordinator.get_activity_for_participant(
            participant_name
        )
        handled = self.sleep_executor.update_join_behavior(
            pet,
            all_pets,
            now=now,
            world_mode=self._world_mode(),
        )
        after_activity = self.activity_coordinator.get_activity_for_participant(
            participant_name
        )
        if (
            before_activity is None
            and after_activity is not None
            and after_activity.spec.kind == SLEEP_ACTIVITY_KIND
            and str(after_activity.metadata.get("sleep_trigger", "") or "")
            == SLEEP_TRIGGER_OBSERVED_JOIN
        ):
            metadata = dict(after_activity.metadata)
            metadata.update(
                {
                    "source": str(after_activity.source or ""),
                    "started_at": float(after_activity.started_at),
                }
            )
            self.achievement_runtime_coordinator.complete_sleep_group_join(
                participant_name,
                activity=after_activity,
                now=now,
            )
            self.achievement_runtime_coordinator.begin_sleep_session(
                after_activity.activity_id,
                metadata=metadata,
            )
        self._sync_sleep_achievements(now=now)
        return handled

    def _sync_sleep_achievements(self, *, now):
        self.achievement_runtime_coordinator.sync_sleep_join_sessions(
            getattr(self.sleep_executor, "join_attempts", {}),
            now=now,
        )
        self._update_sleep_snapshot(now=now)

    def _update_sleep_snapshot(self, *, now):
        return self.achievement_runtime_coordinator.update_sleep_snapshot(
            self.activity_coordinator.get_active_activities(),
            now=now,
        )

    def interrupt_pet_for_user(
        self,
        pet,
        *,
        reason="user_drag",
        now=None,
    ):
        now = self._now(now)
        activity = self.activity_coordinator.get_activity_for_participant(
            str(getattr(pet, "name", "") or "")
        )
        if activity is not None and activity.spec.kind == "race":
            if str(reason or "") == "user_click":
                return False
            result = self.race_executor.interrupt_pet(
                pet,
                now=now,
                reason=reason,
                pets=self.pets,
            )
            if result.handled:
                self._cancel_activity_session(
                    getattr(activity, "activity_id", ""),
                    reason=reason,
                )
            return result.handled
        if activity is not None and activity.spec.kind == "chorus":
            if str(reason or "") == "user_click":
                return False
            result = self.chorus_executor.remove_pet(
                pet,
                now=now,
                reason=reason,
                pets=self.pets,
            )
            if result.handled and self.chorus_executor.session is None:
                self._cancel_activity_session(
                    result.session_id,
                    reason=reason,
                )
            return result.handled
        if str(reason or "") == "user_click":
            return self.sleep_executor.request_early_wake(
                pet,
                now=now,
                reason=reason,
            ).handled
        result = self.sleep_executor.interrupt_pet(
            pet,
            now=now,
            reason=reason,
        )
        if result.handled and result.activity_id:
            self._cancel_activity_session(
                result.activity_id,
                reason=reason,
            )
        return result.handled

    def interrupt_all(self, *, reason, now=None):
        now = self._now(now)
        self.work_executor.interrupt_active(
            now=now,
            reason=reason,
            rudolf_pet=self.pet_registry.find_by_name(
                RUDOLF_NAME,
                visible_only=False,
            ),
        )
        self.sleep_executor.interrupt_all(
            now=now,
            pets=self.pets,
            reason=reason,
        )
        self.race_executor.interrupt_active(
            now=now,
            pets=self.pets,
            reason=reason,
        )
        self.chorus_executor.interrupt_all(
            now=now,
            pets=self.pets,
            reason=reason,
        )
        self.achievement_runtime_coordinator.cancel_all_activity_sessions(
            reason=reason
        )

    def handle_world_mode_change(self, world_mode, previous_mode=None):
        if str(world_mode or "") == str(previous_mode or ""):
            return False
        self.achievement_runtime_coordinator.observe_world_mode(world_mode)
        self.interrupt_all(reason="world_mode_changed")
        return True

    def shutdown(self):
        self.interrupt_all(reason="runtime_shutdown")
