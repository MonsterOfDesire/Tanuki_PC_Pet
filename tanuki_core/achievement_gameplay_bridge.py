from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from uuid import uuid4

from .activity_event_contract import (
    AMBIENT_EVENT_TSUYOSHI_SIDE_READY_FOLLOWUP,
    ACTIVITY_EVENT_SLEEP_COMPLETED,
    ACTIVITY_EVENT_SLEEP_GROUP_JOINED,
    ACTIVITY_EVENT_TRANSFORMATION_COMPLETED,
    INTERACTION_EVENT_CARE_COMPLETED,
    INTERACTION_EVENT_FOOD_SHARE_COMPLETED,
    INTERACTION_EVENT_HONEY_GUARD_COMPLETED,
    build_activity_event_metadata,
)
from .achievement_runtime_service import AchievementRuntimeService
from .pet_random_rules import SIDE_READY_FOLLOWUP_CONTEXT
from .sleep_rules import (
    SLEEP_ACTIVITY_KIND,
    SLEEP_TRIGGER_SANDBOX_CONTROL,
    SLEEPING_PHASE,
)


class AchievementGameplayBridge:
    """Translates live gameplay lifecycles into achievement events."""

    def __init__(
        self,
        *,
        service: AchievementRuntimeService,
        world_mode_provider: Callable[[], str],
    ):
        self.service = service
        self.world_mode_provider = world_mode_provider
        self.transformation_sessions: dict[str, dict[str, object]] = {}
        self.care_sessions: dict[str, dict[str, object]] = {}
        self.recent_care_wakes: dict[str, dict[str, object]] = {}
        self.sleep_join_sessions: dict[str, dict[str, object]] = {}
        self.sleep_snapshot_signature: tuple[tuple[str, str], ...] = ()

    def handle_sleep_result(self, result, *, now: float):
        activity_id = str(getattr(result, "activity_id", "") or "")
        if not activity_id:
            return None
        participant_name = str(
            getattr(result, "participant_name", "") or ""
        )
        metadata = dict(getattr(result, "metadata", {}) or {})
        trigger_kind = str(metadata.get("sleep_trigger", "") or "")
        if bool(getattr(result, "started", False)):
            if trigger_kind == SLEEP_TRIGGER_SANDBOX_CONTROL:
                return None
            return self.begin_sleep_session(
                activity_id,
                metadata=metadata,
            )
        if bool(getattr(result, "interrupted", False)):
            return self.service.cancel_activity_session(
                activity_id,
                reason=str(
                    getattr(result, "reason", "") or "sleep_interrupted"
                ),
            )
        if not bool(getattr(result, "finished", False)):
            return None
        early_wake_reason = str(
            metadata.get("early_wake_reason", "") or ""
        )
        if early_wake_reason:
            if early_wake_reason == "child_distress":
                self.recent_care_wakes[participant_name] = {
                    "target_name": str(
                        metadata.get("care_wake_target_name", "") or ""
                    ),
                    "occurred_at": float(now),
                }
            return self.service.cancel_activity_session(
                activity_id,
                reason=early_wake_reason,
            )
        if trigger_kind == SLEEP_TRIGGER_SANDBOX_CONTROL:
            return None
        world_mode = self._metadata_world_mode(metadata)
        event_metadata = build_activity_event_metadata(
            event_name=ACTIVITY_EVENT_SLEEP_COMPLETED,
            event_id=f"{activity_id}:completed",
            activity_id=activity_id,
            activity_kind="sleep",
            participants=((participant_name, "sleeper"),),
            source=str(
                metadata.get("source", "sleep_schedule")
                or "sleep_schedule"
            ),
            execution_mode="autonomous",
            world_mode=world_mode,
            phase="waking",
            started_at=float(metadata.get("started_at", now) or now),
            ended_at=float(now),
            outcome="completed",
            extra={
                "character_name": participant_name,
                "sleep_trigger": trigger_kind,
                "sleep_group_id": str(
                    metadata.get("sleep_group_id", "") or ""
                ),
                "sleep_anchor_name": str(
                    metadata.get("sleep_anchor_name", "") or ""
                ),
                "natural_completion": True,
            },
        )
        return self.service.consume_activity_metadata(event_metadata)

    def begin_sleep_session(self, activity_id: str, *, metadata: Mapping):
        return self.service.begin_activity_session(
            activity_id=str(activity_id or ""),
            world_mode=self._metadata_world_mode(metadata),
            source=str(
                metadata.get("source", "sleep_schedule")
                or "sleep_schedule"
            ),
            execution_mode="autonomous",
            started_at=float(metadata.get("started_at", 0.0) or 0.0),
        )

    def sync_sleep_join_sessions(self, attempts: Mapping, *, now: float):
        attempts = dict(attempts or {})
        for participant_name in tuple(self.sleep_join_sessions):
            if participant_name in attempts:
                continue
            session = self.sleep_join_sessions.pop(participant_name)
            self.service.cancel_activity_session(
                str(session["activity_id"]),
                reason="sleep_join_attempt_ended",
            )
        for participant_name, attempt in attempts.items():
            if participant_name in self.sleep_join_sessions:
                continue
            activity_id = f"sleep_join:{uuid4().hex}"
            world_mode = self._world_mode()
            self.sleep_join_sessions[str(participant_name)] = {
                "activity_id": activity_id,
                "started_at": float(now),
                "world_mode": world_mode,
                "anchor_name": str(
                    getattr(attempt, "anchor_name", "")
                    or getattr(attempt, "target_name", "")
                    or ""
                ),
            }
            self.service.begin_activity_session(
                activity_id=activity_id,
                world_mode=world_mode,
                source="sleep_observed_join",
                execution_mode="autonomous",
                started_at=float(now),
            )

    def complete_sleep_group_join(
        self,
        participant_name: str,
        *,
        activity,
        now: float,
    ):
        session = self.sleep_join_sessions.pop(
            str(participant_name or ""),
            None,
        )
        if not session:
            return None
        join_activity_id = str(session["activity_id"])
        event_metadata = build_activity_event_metadata(
            event_name=ACTIVITY_EVENT_SLEEP_GROUP_JOINED,
            event_id=f"{join_activity_id}:joined",
            activity_id=join_activity_id,
            activity_kind="sleep_join",
            participants=(
                (participant_name, "joiner"),
                (
                    str(
                        activity.metadata.get("sleep_anchor_name", "")
                        or ""
                    ),
                    "anchor",
                ),
            ),
            source="sleep_observed_join",
            execution_mode="autonomous",
            world_mode=str(session["world_mode"]),
            phase="joined",
            started_at=float(session["started_at"]),
            ended_at=float(now),
            outcome="joined",
            extra={
                "character_name": str(participant_name or ""),
                "sleep_activity_id": str(activity.activity_id or ""),
                "sleep_group_id": str(
                    activity.metadata.get("sleep_group_id", "") or ""
                ),
                "sleep_anchor_name": str(
                    activity.metadata.get("sleep_anchor_name", "") or ""
                ),
            },
        )
        return self.service.consume_activity_metadata(event_metadata)

    def update_sleep_snapshot(
        self,
        activities: Iterable,
        *,
        now: float,
    ):
        sleepers = []
        for activity in tuple(activities or ()):
            if (
                activity.spec.kind != SLEEP_ACTIVITY_KIND
                or activity.phase.name != SLEEPING_PHASE
                or str(activity.metadata.get("sleep_trigger", "") or "")
                == SLEEP_TRIGGER_SANDBOX_CONTROL
                or not activity.participants
            ):
                continue
            sleepers.append(
                (activity.participants[0].name, activity.activity_id)
            )
        signature = tuple(sorted(sleepers))
        if signature == self.sleep_snapshot_signature:
            return None
        self.sleep_snapshot_signature = signature
        if not signature:
            return None
        world_mode = self._world_mode()
        eligible = all(
            self.service.activity_session_is_eligible(
                activity_id,
                world_mode=world_mode,
            )
            for _name, activity_id in signature
        )
        return self.service.consume_state_snapshot(
            snapshot_id=f"sleep_snapshot:{uuid4().hex}",
            world_mode=world_mode,
            source="sleep_schedule",
            execution_mode="autonomous",
            occurred_at=float(now),
            state_payload={
                "naturally_sleeping_character_names": [
                    name for name, _activity_id in signature
                ]
            },
            eligible=eligible,
            ineligible_reason=(
                "sleep_session_ineligible" if not eligible else ""
            ),
        )

    def begin_transformation(self, result, *, started_at: float):
        character_name = str(result.character_name or "")
        if not character_name:
            return False
        previous = self.transformation_sessions.pop(character_name, None)
        if previous:
            self.service.cancel_activity_session(
                str(previous["activity_id"]),
                reason="transformation_session_replaced",
            )
        activity_id = f"transformation:{uuid4().hex}"
        session = {
            "activity_id": activity_id,
            "world_mode": self._world_mode(),
            "source": str(result.source or ""),
            "started_at": float(started_at),
        }
        self.transformation_sessions[character_name] = session
        return self.service.begin_activity_session(
            activity_id=activity_id,
            world_mode=str(session["world_mode"]),
            source=str(session["source"]),
            execution_mode="autonomous",
            started_at=float(started_at),
        )

    def complete_transformation(self, result, *, occurred_at: float):
        character_name = str(result.character_name or "")
        session = self.transformation_sessions.pop(character_name, None)
        if not session:
            return None
        activity_id = str(session["activity_id"])
        metadata = build_activity_event_metadata(
            event_name=ACTIVITY_EVENT_TRANSFORMATION_COMPLETED,
            event_id=f"{activity_id}:completed",
            activity_id=activity_id,
            activity_kind="transformation",
            participants=((character_name, "subject"),),
            source=str(session["source"]),
            execution_mode="autonomous",
            world_mode=str(session["world_mode"]),
            phase="revealing",
            started_at=float(session["started_at"]),
            ended_at=float(occurred_at),
            outcome="completed",
            extra={
                "character_name": character_name,
                "source": str(session["source"]),
                "target_form": str(result.current_form or ""),
            },
        )
        return self.service.consume_activity_metadata(metadata)

    def handle_ambient_animation_context(
        self,
        *,
        character_name: str,
        context: str,
        now: float,
    ):
        character_name = str(character_name or "")
        context = str(context or "")
        if (
            character_name != "Tsurumaru Tsuyoshi"
            or context != SIDE_READY_FOLLOWUP_CONTEXT
        ):
            return None
        event_id = f"ambient_tsuyoshi_stand:{uuid4().hex}"
        metadata = build_activity_event_metadata(
            event_name=AMBIENT_EVENT_TSUYOSHI_SIDE_READY_FOLLOWUP,
            event_id=event_id,
            activity_id="",
            activity_kind="ambient_animation",
            participants=((character_name, "subject"),),
            source="ambient_random",
            execution_mode="autonomous",
            world_mode=self._world_mode(),
            phase=context,
            started_at=float(now),
            ended_at=float(now),
            outcome="observed",
            extra={
                "character_name": character_name,
                "animation_context": context,
            },
        )
        return self.service.consume_instantaneous_activity_metadata(
            metadata
        )

    def cancel_orphaned_transformations(
        self,
        active_character_names: Iterable[str],
    ):
        active_names = {str(name or "") for name in active_character_names}
        for character_name, session in tuple(
            self.transformation_sessions.items()
        ):
            if character_name in active_names:
                continue
            self.transformation_sessions.pop(character_name, None)
            self.service.cancel_activity_session(
                str(session["activity_id"]),
                reason="transformation_transition_cancelled",
            )

    def handle_care_event(
        self,
        stage: str,
        *,
        caregiver_name: str,
        target_name: str,
        caregiver_form: str,
        now: float,
        success=None,
        care_mode: str = "",
    ):
        caregiver_name = str(caregiver_name or "")
        target_name = str(target_name or "")
        stage = str(stage or "")
        if not caregiver_name or not target_name:
            return None
        if stage == "started":
            previous = self.care_sessions.pop(caregiver_name, None)
            if previous:
                self.service.cancel_activity_session(
                    str(previous["activity_id"]),
                    reason="care_session_replaced",
                )
            wake = self.recent_care_wakes.pop(caregiver_name, None)
            woke_from_sleep = bool(
                wake
                and wake.get("target_name") == target_name
                and float(now) - float(wake.get("occurred_at", 0.0))
                <= 30.0
            )
            activity_id = f"care:{uuid4().hex}"
            session = {
                "activity_id": activity_id,
                "world_mode": self._world_mode(),
                "started_at": float(now),
                "target_name": target_name,
                "caregiver_form": str(caregiver_form or "base"),
                "caregiver_woke_from_sleep": woke_from_sleep,
            }
            self.care_sessions[caregiver_name] = session
            return self.service.begin_activity_session(
                activity_id=activity_id,
                world_mode=str(session["world_mode"]),
                source="care_autonomous",
                execution_mode="autonomous",
                started_at=float(now),
            )
        session = self.care_sessions.pop(caregiver_name, None)
        if not session:
            return None
        activity_id = str(session["activity_id"])
        if stage != "completed" or not bool(success):
            return self.service.cancel_activity_session(
                activity_id,
                reason="care_interrupted",
            )
        metadata = build_activity_event_metadata(
            event_name=INTERACTION_EVENT_CARE_COMPLETED,
            event_id=f"{activity_id}:completed",
            activity_id=activity_id,
            activity_kind="care",
            participants=(
                (caregiver_name, "caregiver"),
                (target_name, "recipient"),
            ),
            source="care_autonomous",
            execution_mode="autonomous",
            world_mode=str(session["world_mode"]),
            phase=str(care_mode or "finish"),
            started_at=float(session["started_at"]),
            ended_at=float(now),
            outcome="completed",
            extra={
                "caregiver_name": caregiver_name,
                "target_name": target_name,
                "caregiver_form": str(session["caregiver_form"]),
                "caregiver_woke_from_sleep": bool(
                    session["caregiver_woke_from_sleep"]
                ),
            },
        )
        return self.service.consume_activity_metadata(metadata)

    def begin_offer_session(
        self,
        *,
        scene_id: str,
        source: str,
        started_at: float,
    ) -> bool:
        return self.service.begin_activity_session(
            activity_id=str(scene_id or ""),
            world_mode=self._world_mode(),
            source=str(source or "offer_tray"),
            execution_mode="player_gameplay",
            started_at=float(started_at),
        )

    def cancel_offer_session(self, scene_id: str, *, reason: str) -> bool:
        return self.service.cancel_activity_session(
            str(scene_id or ""),
            reason=str(reason or "offer_scene_cancelled"),
        )

    def build_honey_guard_metadata(
        self,
        *,
        scene_id: str,
        source: str,
        started_at: float,
        occurred_at: float,
        guardian_name: str,
        target_name: str,
        item_kind: str,
    ) -> dict[str, object]:
        return build_activity_event_metadata(
            event_name=INTERACTION_EVENT_HONEY_GUARD_COMPLETED,
            event_id=f"{scene_id}:completed",
            activity_id=scene_id,
            activity_kind="honey_guard",
            participants=(
                (guardian_name, "guardian"),
                (target_name, "child"),
            ),
            source=str(source or "offer_tray"),
            execution_mode="player_gameplay",
            world_mode=self._world_mode(),
            phase="snatch",
            started_at=float(started_at),
            ended_at=float(occurred_at),
            outcome="guarded",
            extra={
                "guardian_name": guardian_name,
                "target_name": target_name,
                "item_kind": item_kind,
                "scene_kind": "honey_guard",
            },
        )

    def build_shared_food_metadata(
        self,
        *,
        scene_id: str,
        source: str,
        started_at: float,
        occurred_at: float,
        holder_name: str,
        partner_name: str,
        consumer_names: Iterable[str],
        item_kind: str,
        profile_key: str,
        outcome: str,
    ) -> dict[str, object]:
        return build_activity_event_metadata(
            event_name=INTERACTION_EVENT_FOOD_SHARE_COMPLETED,
            event_id=f"{scene_id}:completed",
            activity_id=scene_id,
            activity_kind="food_share",
            participants=(
                (holder_name, "holder"),
                (partner_name, "partner"),
            ),
            source=str(source or "offer_tray"),
            execution_mode="player_gameplay",
            world_mode=self._world_mode(),
            phase="finish",
            started_at=float(started_at),
            ended_at=float(occurred_at),
            outcome=str(outcome or ""),
            extra={
                "holder_name": holder_name,
                "partner_name": partner_name,
                "consumer_names": list(consumer_names or ()),
                "item_kind": item_kind,
                "profile_key": profile_key,
                "scene_kind": "shared_food",
            },
        )

    def _metadata_world_mode(self, metadata: Mapping) -> str:
        return str(
            metadata.get("start_world_mode", self._world_mode())
            or self._world_mode()
        )

    def _world_mode(self) -> str:
        return str(self.world_mode_provider() or "")
