from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping

from .achievement_catalog import (
    ACHIEVEMENT_WORLD_MODES,
    AchievementCatalog,
    AchievementDefinition,
)
from .achievement_eligibility import (
    ACHIEVEMENT_ELIGIBLE_SOURCE_KINDS,
    AchievementEligibilityDecision,
)
from .achievement_state import AchievementProgress, AchievementState


@dataclass(frozen=True)
class AchievementGameplayEvent:
    event_id: str
    event_name: str
    world_mode: str
    source_kind: str
    occurred_at: float
    started_at: float = 0.0
    payload: Mapping[str, object] = field(default_factory=dict)
    participants: tuple[Mapping[str, object], ...] = ()
    eligible: bool = True
    ineligible_reason: str = ""

    @classmethod
    def from_eligibility_decision(
        cls,
        decision: AchievementEligibilityDecision,
        *,
        event_name: str,
        payload: Mapping[str, object] | None = None,
        participants=(),
    ) -> "AchievementGameplayEvent":
        return cls(
            event_id=decision.event_id,
            event_name=str(event_name or "").strip(),
            world_mode=decision.world_mode,
            source_kind=decision.source_kind,
            occurred_at=float(decision.ended_at),
            started_at=float(decision.started_at),
            payload=dict(payload or {}),
            participants=tuple(
                participant
                for participant in participants
                if isinstance(participant, Mapping)
            ),
            eligible=bool(decision.eligible),
            ineligible_reason=str(decision.reason or ""),
        )


@dataclass(frozen=True)
class AchievementUpdate:
    achievement_id: str
    world_mode: str
    progress_current: int
    progress_target: int
    unlocked: bool
    unlocked_now: bool
    unlocked_at: float | None


@dataclass(frozen=True)
class AchievementConsumeResult:
    accepted: bool
    reason: str = ""
    updates: tuple[AchievementUpdate, ...] = ()

    @property
    def unlocked_achievement_ids(self) -> tuple[str, ...]:
        return tuple(
            update.achievement_id
            for update in self.updates
            if update.unlocked_now
        )


class AchievementTracker:
    def __init__(
        self,
        catalog: AchievementCatalog,
        state: AchievementState | None = None,
    ):
        self.catalog = catalog
        self.state = state or AchievementState()

    def consume_event(
        self,
        event: AchievementGameplayEvent,
    ) -> AchievementConsumeResult:
        rejection = self._event_rejection_reason(event)
        if rejection:
            return AchievementConsumeResult(False, rejection)

        self.state.mark_event_processed(event.world_mode, event.event_id)
        updates = []
        for definition in self.catalog.definitions_for_mode(
            event.world_mode
        ):
            if definition.rule.get("type") in {
                "all_of_achievements",
                "simultaneous_state_threshold",
            }:
                continue
            update = self._apply_event_rule(definition, event)
            if update is not None:
                updates.append(update)

        updates.extend(
            self._resolve_meta_achievements(
                event.world_mode,
                event.occurred_at,
            )
        )
        return AchievementConsumeResult(
            True,
            updates=tuple(_deduplicate_updates(updates)),
        )

    def consume_state_snapshot(
        self,
        *,
        snapshot_id: str,
        world_mode: str,
        source_kind: str,
        occurred_at: float,
        state_payload: Mapping[str, object],
        eligible: bool = True,
        ineligible_reason: str = "",
    ) -> AchievementConsumeResult:
        event = AchievementGameplayEvent(
            event_id=str(snapshot_id or "").strip(),
            event_name="state.snapshot",
            world_mode=str(world_mode or "").strip(),
            source_kind=str(source_kind or "").strip(),
            occurred_at=float(occurred_at),
            payload=dict(state_payload or {}),
            eligible=bool(eligible),
            ineligible_reason=str(ineligible_reason or ""),
        )
        rejection = self._event_rejection_reason(event)
        if rejection:
            return AchievementConsumeResult(False, rejection)

        self.state.mark_event_processed(event.world_mode, event.event_id)
        updates = []
        for definition in self.catalog.definitions_for_mode(
            event.world_mode
        ):
            if definition.rule.get("type") != "simultaneous_state_threshold":
                continue
            update = self._apply_snapshot_rule(definition, event)
            if update is not None:
                updates.append(update)
        updates.extend(
            self._resolve_meta_achievements(
                event.world_mode,
                event.occurred_at,
            )
        )
        return AchievementConsumeResult(
            True,
            updates=tuple(_deduplicate_updates(updates)),
        )

    def _event_rejection_reason(
        self,
        event: AchievementGameplayEvent,
    ) -> str:
        if not event.eligible:
            return str(event.ineligible_reason or "ineligible_event")
        if event.source_kind not in ACHIEVEMENT_ELIGIBLE_SOURCE_KINDS:
            return "ineligible_source_kind"
        if event.world_mode not in ACHIEVEMENT_WORLD_MODES:
            return "unsupported_world_mode"
        if not str(event.event_id or "").strip():
            return "missing_event_id"
        if not str(event.event_name or "").strip():
            return "missing_event_name"
        if self.state.has_processed_event(event.world_mode, event.event_id):
            return "duplicate_event"
        return ""

    def _apply_event_rule(
        self,
        definition: AchievementDefinition,
        event: AchievementGameplayEvent,
    ) -> AchievementUpdate | None:
        progress = self.state.progress_for(
            definition.world_mode,
            definition.achievement_id,
        )
        if progress.unlocked:
            return None
        rule = definition.rule
        rule_type = str(rule.get("type", "") or "")
        if not _rule_accepts_event(rule, event.event_name):
            return None
        if not _matches_filters(rule.get("filters", {}), event):
            return None

        changed = False
        if rule_type == "event_count":
            progress.count += 1
            changed = True
        elif rule_type == "distinct_values":
            value = _event_value(event, str(rule.get("payload_key", "")))
            changed = _add_allowed_observed_key(
                progress,
                value,
                rule.get("required_values"),
            )
        elif rule_type == "single_event_threshold":
            value = _safe_int(
                _event_value(event, str(rule.get("payload_key", ""))),
                0,
            )
            previous = progress.count
            progress.count = max(previous, value)
            changed = progress.count != previous
        elif rule_type == "distinct_participants_by_role":
            role = str(rule.get("participant_role", "") or "")
            required_values = rule.get("required_values")
            for participant in _event_participants(event):
                if str(participant.get("role", "") or "") != role:
                    continue
                changed = (
                    _add_allowed_observed_key(
                        progress,
                        participant.get("name"),
                        required_values,
                    )
                    or changed
                )
        elif rule_type == "all_of":
            expected_names = _normalized_string_set(
                rule.get("event_names", ())
            )
            if event.event_name in expected_names:
                previous = len(progress.observed_event_names)
                progress.observed_event_names.add(event.event_name)
                changed = len(progress.observed_event_names) != previous
        elif rule_type == "distinct_composite_values":
            value = tuple(
                _event_value(event, str(payload_key or ""))
                for payload_key in rule.get("payload_keys", ())
            )
            if all(item is not None for item in value):
                changed = _add_allowed_observed_key(
                    progress,
                    value,
                    rule.get("required_values"),
                )

        if not changed:
            return None
        progress.updated_at = float(event.occurred_at)
        return self._build_update(
            definition,
            progress,
            occurred_at=event.occurred_at,
        )

    def _apply_snapshot_rule(
        self,
        definition: AchievementDefinition,
        event: AchievementGameplayEvent,
    ) -> AchievementUpdate | None:
        progress = self.state.progress_for(
            definition.world_mode,
            definition.achievement_id,
        )
        if progress.unlocked:
            return None
        rule = definition.rule
        state_value = event.payload.get(str(rule.get("state_key", "")))
        if isinstance(state_value, (list, tuple, set, frozenset)):
            value = len(state_value)
        else:
            value = _safe_int(state_value, 0)
        previous = progress.count
        progress.count = max(previous, value)
        if progress.count == previous:
            return None
        progress.updated_at = float(event.occurred_at)
        return self._build_update(
            definition,
            progress,
            occurred_at=event.occurred_at,
        )

    def _resolve_meta_achievements(
        self,
        world_mode: str,
        occurred_at: float,
    ) -> list[AchievementUpdate]:
        updates = []
        changed = True
        while changed:
            changed = False
            for definition in self.catalog.definitions_for_mode(world_mode):
                if definition.rule.get("type") != "all_of_achievements":
                    continue
                progress = self.state.progress_for(
                    world_mode,
                    definition.achievement_id,
                )
                if progress.unlocked:
                    continue
                dependency_ids = tuple(
                    str(value or "").strip()
                    for value in definition.rule.get(
                        "achievement_ids",
                        (),
                    )
                )
                completed = sum(
                    self.state.is_unlocked(world_mode, dependency_id)
                    for dependency_id in dependency_ids
                )
                progress_changed = progress.count != completed
                progress.count = completed
                if progress_changed:
                    progress.updated_at = float(occurred_at)
                if completed < len(dependency_ids):
                    if progress_changed:
                        updates.append(
                            self._build_update(
                                definition,
                                progress,
                                occurred_at=occurred_at,
                            )
                        )
                    continue
                unlocked_now = progress.unlock(occurred_at)
                if unlocked_now:
                    changed = True
                    updates.append(
                        self._build_update(
                            definition,
                            progress,
                            occurred_at=occurred_at,
                            already_resolved_unlock=True,
                            unlocked_now=True,
                        )
                    )
        return updates

    def _build_update(
        self,
        definition: AchievementDefinition,
        progress: AchievementProgress,
        *,
        occurred_at: float,
        already_resolved_unlock: bool = False,
        unlocked_now: bool = False,
    ) -> AchievementUpdate:
        target = _rule_target(definition.rule)
        current = _progress_current(definition.rule, progress)
        if not already_resolved_unlock and current >= target:
            unlocked_now = progress.unlock(occurred_at)
        return AchievementUpdate(
            achievement_id=definition.achievement_id,
            world_mode=definition.world_mode,
            progress_current=min(current, target),
            progress_target=target,
            unlocked=progress.unlocked,
            unlocked_now=bool(unlocked_now),
            unlocked_at=progress.unlocked_at,
        )


def _rule_accepts_event(rule, event_name: str) -> bool:
    rule_type = str(rule.get("type", "") or "")
    if rule_type == "all_of":
        return event_name in _normalized_string_set(
            rule.get("event_names", ())
        )
    return str(rule.get("event_name", "") or "") == event_name


def _matches_filters(raw_filters, event: AchievementGameplayEvent) -> bool:
    if not isinstance(raw_filters, Mapping):
        return True
    return all(
        _event_value(event, str(key or "")) == expected
        for key, expected in raw_filters.items()
    )


def _event_value(event: AchievementGameplayEvent, key: str):
    if key == "source_kind":
        return event.source_kind
    if key == "world_mode":
        return event.world_mode
    if key in event.payload:
        return event.payload.get(key)
    if key == "winner_form":
        winner_name = event.payload.get("winner_name")
        if winner_name == event.payload.get("challenger_name"):
            return event.payload.get("challenger_form")
        if winner_name == event.payload.get("opponent_name"):
            return event.payload.get("opponent_form")
    return None


def _event_participants(
    event: AchievementGameplayEvent,
) -> tuple[Mapping[str, object], ...]:
    if event.participants:
        return event.participants
    raw_participants = event.payload.get("activity_participants", ())
    if not isinstance(raw_participants, list):
        return ()
    return tuple(
        participant
        for participant in raw_participants
        if isinstance(participant, Mapping)
    )


def _add_allowed_observed_key(
    progress: AchievementProgress,
    value,
    raw_required_values,
) -> bool:
    if value is None:
        return False
    encoded = _encode_observed_key(value)
    required_keys = _encoded_required_values(raw_required_values)
    if required_keys is not None and encoded not in required_keys:
        return False
    previous = len(progress.observed_keys)
    progress.observed_keys.add(encoded)
    return len(progress.observed_keys) != previous


def _encoded_required_values(raw_required_values) -> set[str] | None:
    if not isinstance(raw_required_values, list):
        return None
    return {
        _encode_observed_key(value) for value in raw_required_values
    }


def _encode_observed_key(value) -> str:
    if isinstance(value, tuple):
        value = list(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _rule_target(rule) -> int:
    rule_type = str(rule.get("type", "") or "")
    if rule_type in {"event_count", "distinct_composite_values"}:
        if isinstance(rule.get("required_values"), list):
            return max(1, len(rule["required_values"]))
        return max(1, _safe_int(rule.get("target"), 1))
    if rule_type == "distinct_values":
        if isinstance(rule.get("required_values"), list):
            return max(1, len(rule["required_values"]))
        return max(1, _safe_int(rule.get("target"), 1))
    if rule_type in {
        "single_event_threshold",
        "simultaneous_state_threshold",
    }:
        return max(1, _safe_int(rule.get("minimum"), 1))
    if rule_type == "distinct_participants_by_role":
        return max(1, len(rule.get("required_values", ())))
    if rule_type == "all_of":
        return max(1, len(rule.get("event_names", ())))
    if rule_type == "all_of_achievements":
        return max(1, len(rule.get("achievement_ids", ())))
    return 1


def _progress_current(rule, progress: AchievementProgress) -> int:
    rule_type = str(rule.get("type", "") or "")
    if rule_type in {
        "distinct_values",
        "distinct_participants_by_role",
        "distinct_composite_values",
    }:
        return len(progress.observed_keys)
    if rule_type == "all_of":
        return len(progress.observed_event_names)
    return max(0, int(progress.count))


def _normalized_string_set(value) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        normalized
        for normalized in (str(item or "").strip() for item in value)
        if normalized
    }


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _deduplicate_updates(updates) -> list[AchievementUpdate]:
    latest_by_id = {}
    order = []
    for update in updates:
        if update.achievement_id not in latest_by_id:
            order.append(update.achievement_id)
        previous = latest_by_id.get(update.achievement_id)
        if previous is not None and previous.unlocked_now and not update.unlocked_now:
            update = AchievementUpdate(
                achievement_id=update.achievement_id,
                world_mode=update.world_mode,
                progress_current=update.progress_current,
                progress_target=update.progress_target,
                unlocked=update.unlocked,
                unlocked_now=True,
                unlocked_at=update.unlocked_at,
            )
        latest_by_id[update.achievement_id] = update
    return [latest_by_id[achievement_id] for achievement_id in order]
