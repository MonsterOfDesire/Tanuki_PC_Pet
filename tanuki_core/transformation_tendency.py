from __future__ import annotations

from dataclasses import dataclass

from .transformation_state import FORM_BASE


TOKAI_TEIO_NAME = "Tokai Teio"
SYMBOLI_RUDOLF_NAME = "Symboli Rudolf"
TSURUMARU_TSUYOSHI_NAME = "Tsurumaru Tsuyoshi"

TENDENCY_TEIO_TSUYOSHI_POSITIVE = "teio_tsuyoshi_positive"
TENDENCY_TEIO_TSUYOSHI_DISTRESS = "teio_tsuyoshi_distress"
TENDENCY_TEIO_RACE_STIMULUS = "teio_race_stimulus"
TENDENCY_TEIO_HIGH_MOOD = "teio_high_mood"
TENDENCY_RUDOLF_HOUSEHOLD_PRESSURE = "rudolf_household_pressure"
TENDENCY_RUDOLF_NEGATIVE_EVENT = "rudolf_negative_household_event"
TENDENCY_RUDOLF_CARE_NEED = "rudolf_care_need"
TENDENCY_RUDOLF_HONEY_NEED = "rudolf_honey_guard_need"
TENDENCY_RUDOLF_RACE_CHALLENGED = "rudolf_race_challenged"

TRANSFORMATION_TENDENCY_MAX_SCORE = 100.0
TRANSFORMATION_TENDENCY_MIN_REMAINING_SECONDS = 30.0


@dataclass(frozen=True)
class TransformationTendencyRule:
    character_name: str
    signal_kind: str
    score: float
    advance_seconds: float


@dataclass(frozen=True)
class TransformationTendencyDecision:
    allowed: bool
    reason: str = ""
    score_delta: float = 0.0
    advance_seconds: float = 0.0


@dataclass(frozen=True)
class TransformationTendencyApplyResult:
    applied: bool
    reason: str = ""
    character_name: str = ""
    signal_kind: str = ""
    score: float = 0.0
    advanced_seconds: float = 0.0
    next_attempt_at: float = 0.0


def _rule(character_name, signal_kind, score, advance_seconds):
    return TransformationTendencyRule(
        character_name,
        signal_kind,
        score,
        advance_seconds,
    )


TRANSFORMATION_TENDENCY_RULES = {
    (TOKAI_TEIO_NAME, TENDENCY_TEIO_TSUYOSHI_POSITIVE): _rule(
        TOKAI_TEIO_NAME, TENDENCY_TEIO_TSUYOSHI_POSITIVE, 12.0, 60.0
    ),
    (TOKAI_TEIO_NAME, TENDENCY_TEIO_TSUYOSHI_DISTRESS): _rule(
        TOKAI_TEIO_NAME, TENDENCY_TEIO_TSUYOSHI_DISTRESS, 24.0, 120.0
    ),
    (TOKAI_TEIO_NAME, TENDENCY_TEIO_RACE_STIMULUS): _rule(
        TOKAI_TEIO_NAME, TENDENCY_TEIO_RACE_STIMULUS, 16.0, 75.0
    ),
    (TOKAI_TEIO_NAME, TENDENCY_TEIO_HIGH_MOOD): _rule(
        TOKAI_TEIO_NAME, TENDENCY_TEIO_HIGH_MOOD, 10.0, 45.0
    ),
    (SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_HOUSEHOLD_PRESSURE): _rule(
        SYMBOLI_RUDOLF_NAME,
        TENDENCY_RUDOLF_HOUSEHOLD_PRESSURE,
        12.0,
        60.0,
    ),
    (SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_NEGATIVE_EVENT): _rule(
        SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_NEGATIVE_EVENT, 18.0, 90.0
    ),
    (SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_CARE_NEED): _rule(
        SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_CARE_NEED, 22.0, 105.0
    ),
    (SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_HONEY_NEED): _rule(
        SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_HONEY_NEED, 22.0, 105.0
    ),
    (SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_RACE_CHALLENGED): _rule(
        SYMBOLI_RUDOLF_NAME, TENDENCY_RUDOLF_RACE_CHALLENGED, 16.0, 75.0
    ),
}


def evaluate_transformation_tendency(
    *,
    character_name: str,
    current_form: str,
    transitioning: bool,
    signal_kind: str,
    strength: float = 1.0,
) -> TransformationTendencyDecision:
    rule = TRANSFORMATION_TENDENCY_RULES.get(
        (str(character_name or ""), str(signal_kind or ""))
    )
    if rule is None:
        return TransformationTendencyDecision(False, "unsupported_signal")
    if str(current_form or FORM_BASE) != FORM_BASE:
        return TransformationTendencyDecision(False, "already_transformed")
    if bool(transitioning):
        return TransformationTendencyDecision(False, "transition_active")
    strength = max(0.25, min(2.0, float(strength or 1.0)))
    return TransformationTendencyDecision(
        True,
        score_delta=rule.score * strength,
        advance_seconds=rule.advance_seconds * strength,
    )


def apply_transformation_tendency(
    state,
    decision: TransformationTendencyDecision,
    *,
    character_name: str,
    signal_kind: str,
    now: float,
) -> TransformationTendencyApplyResult:
    if state is None or not decision.allowed:
        return TransformationTendencyApplyResult(
            False,
            decision.reason or "missing_state",
            character_name=str(character_name or ""),
            signal_kind=str(signal_kind or ""),
        )
    current_score = float(
        getattr(state, "auto_tendency_score", 0.0) or 0.0
    )
    state.auto_tendency_score = min(
        TRANSFORMATION_TENDENCY_MAX_SCORE,
        current_score + float(decision.score_delta),
    )
    state.auto_tendency_last_signal = str(signal_kind or "")
    next_attempt_at = float(
        getattr(state, "auto_next_attempt_at", 0.0) or 0.0
    )
    advanced_seconds = 0.0
    if next_attempt_at > 0.0:
        replacement = max(
            float(now) + TRANSFORMATION_TENDENCY_MIN_REMAINING_SECONDS,
            next_attempt_at - float(decision.advance_seconds),
        )
        advanced_seconds = max(0.0, next_attempt_at - replacement)
        state.auto_next_attempt_at = replacement
    else:
        state.auto_pending_tendency_advance_seconds = (
            float(
                getattr(
                    state,
                    "auto_pending_tendency_advance_seconds",
                    0.0,
                )
                or 0.0
            )
            + float(decision.advance_seconds)
        )
    return TransformationTendencyApplyResult(
        True,
        character_name=str(character_name or ""),
        signal_kind=str(signal_kind or ""),
        score=float(state.auto_tendency_score),
        advanced_seconds=advanced_seconds,
        next_attempt_at=float(
            getattr(state, "auto_next_attempt_at", 0.0) or 0.0
        ),
    )


def household_entry_is_negative(entry) -> bool:
    if entry is None:
        return False
    if str(getattr(entry, "event_type", "") or "") == (
        "rudolf_work_completed"
    ):
        return False
    if float(getattr(entry, "household_pressure_delta", 0.0) or 0.0) > 0:
        return True
    if float(getattr(entry, "mood_delta", 0.0) or 0.0) < 0:
        return True
    relation_delta = dict(getattr(entry, "relation_delta", {}) or {})
    if float(relation_delta.get("tension", 0.0) or 0.0) > 0:
        return True
    tags = {str(tag or "") for tag in getattr(entry, "tags", ()) or ()}
    return bool(
        tags.intersection(
            {"negative", "distress", "denied", "failed", "interrupted"}
        )
    )


def entry_is_positive_teio_tsuyoshi_interaction(entry) -> bool:
    if entry is None:
        return False
    participants = {
        str(getattr(entry, "actor_name", "") or ""),
        str(getattr(entry, "target_name", "") or ""),
    }
    if participants != {TOKAI_TEIO_NAME, TSURUMARU_TSUYOSHI_NAME}:
        return False
    relation_delta = dict(getattr(entry, "relation_delta", {}) or {})
    return any(
        float(relation_delta.get(metric, 0.0) or 0.0) > 0
        for metric in ("familiarity", "trust", "attachment")
    )


class TransformationTendencyCoordinator:
    def __init__(self):
        self._processed_entry_sequences: set[int] = set()
        self._ambient_attempt_serials: dict[str, int] = {}
        self._live_signal_attempt_serials: dict[
            tuple[str, str], int
        ] = {}

    def process_household_entry(
        self, entry, *, pets, executor, now: float
    ) -> tuple[TransformationTendencyApplyResult, ...]:
        sequence = int(getattr(entry, "sequence", 0) or 0)
        if sequence and sequence in self._processed_entry_sequences:
            return ()
        if sequence:
            self._processed_entry_sequences.add(sequence)
        results = []
        if entry_is_positive_teio_tsuyoshi_interaction(entry):
            results.append(
                self._apply(
                    TOKAI_TEIO_NAME,
                    TENDENCY_TEIO_TSUYOSHI_POSITIVE,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        if household_entry_is_negative(entry):
            results.append(
                self._apply(
                    SYMBOLI_RUDOLF_NAME,
                    TENDENCY_RUDOLF_NEGATIVE_EVENT,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        return tuple(result for result in results if result.applied)

    def process_race_event(
        self, event, *, pets, executor, now: float
    ) -> tuple[TransformationTendencyApplyResult, ...]:
        participants = {
            str(getattr(event, "challenger_name", "") or ""),
            str(getattr(event, "opponent_name", "") or ""),
        }
        results = []
        if (
            TOKAI_TEIO_NAME in participants
            and str(getattr(event, "event_type", "") or "")
            == "race_completed"
        ):
            results.append(
                self._apply(
                    TOKAI_TEIO_NAME,
                    TENDENCY_TEIO_RACE_STIMULUS,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        if (
            str(getattr(event, "opponent_name", "") or "")
            == SYMBOLI_RUDOLF_NAME
        ):
            results.append(
                self._apply(
                    SYMBOLI_RUDOLF_NAME,
                    TENDENCY_RUDOLF_RACE_CHALLENGED,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        return tuple(result for result in results if result.applied)

    def update_context(
        self,
        *,
        pets,
        household_pressure: float,
        executor,
        now: float,
    ) -> tuple[TransformationTendencyApplyResult, ...]:
        pets = tuple(pets or ())
        pets_by_name = {
            str(getattr(pet, "name", "") or ""): pet for pet in pets
        }
        results = []
        for name in (TOKAI_TEIO_NAME, SYMBOLI_RUDOLF_NAME):
            pet = pets_by_name.get(name)
            state = getattr(pet, "transformation_state", None)
            serial = int(getattr(state, "auto_attempt_serial", 0) or 0)
            if pet is None or state is None or serial <= 0:
                continue
            if self._ambient_attempt_serials.get(name) == serial:
                continue
            if (
                name == TOKAI_TEIO_NAME
                and float(getattr(pet, "mood_score", 0.0) or 0.0) >= 80.0
            ):
                results.append(
                    self._apply(
                        name,
                        TENDENCY_TEIO_HIGH_MOOD,
                        pets=pets,
                        executor=executor,
                        now=now,
                    )
                )
            if name == SYMBOLI_RUDOLF_NAME and household_pressure >= 35.0:
                strength = min(
                    2.0,
                    max(0.5, (float(household_pressure) - 20.0) / 40.0),
                )
                results.append(
                    self._apply(
                        name,
                        TENDENCY_RUDOLF_HOUSEHOLD_PRESSURE,
                        pets=pets,
                        executor=executor,
                        now=now,
                        strength=strength,
                    )
                )
            self._ambient_attempt_serials[name] = serial

        tsuyoshi = pets_by_name.get(TSURUMARU_TSUYOSHI_NAME)
        distress = False
        if tsuyoshi is not None:
            is_distressed = getattr(tsuyoshi, "is_distressed", None)
            distress = bool(callable(is_distressed) and is_distressed())
        if distress:
            results.extend(
                self._apply_live_once_per_attempt(
                    TOKAI_TEIO_NAME,
                    TENDENCY_TEIO_TSUYOSHI_DISTRESS,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
            results.extend(
                self._apply_live_once_per_attempt(
                    SYMBOLI_RUDOLF_NAME,
                    TENDENCY_RUDOLF_CARE_NEED,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        if (
            tsuyoshi is not None
            and str(getattr(tsuyoshi, "held_item_kind", "") or "")
            == "honey"
        ):
            results.extend(
                self._apply_live_once_per_attempt(
                    SYMBOLI_RUDOLF_NAME,
                    TENDENCY_RUDOLF_HONEY_NEED,
                    pets=pets,
                    executor=executor,
                    now=now,
                )
            )
        return tuple(result for result in results if result.applied)

    def _apply_live_once_per_attempt(
        self,
        character_name: str,
        signal_kind: str,
        *,
        pets,
        executor,
        now: float,
    ) -> tuple[TransformationTendencyApplyResult, ...]:
        pet = self._pet_by_name(pets, character_name)
        state = getattr(pet, "transformation_state", None)
        serial = int(getattr(state, "auto_attempt_serial", 0) or 0)
        key = (character_name, signal_kind)
        if serial <= 0 or self._live_signal_attempt_serials.get(key) == serial:
            return ()
        result = self._apply(
            character_name,
            signal_kind,
            pets=pets,
            executor=executor,
            now=now,
        )
        if result.applied:
            self._live_signal_attempt_serials[key] = serial
            return (result,)
        return ()

    @staticmethod
    def _pet_by_name(pets, name):
        return next(
            (
                pet
                for pet in tuple(pets or ())
                if str(getattr(pet, "name", "") or "") == name
            ),
            None,
        )

    def _apply(
        self,
        character_name: str,
        signal_kind: str,
        *,
        pets,
        executor,
        now: float,
        strength: float = 1.0,
    ) -> TransformationTendencyApplyResult:
        pet = self._pet_by_name(pets, character_name)
        if pet is None:
            return TransformationTendencyApplyResult(
                False,
                "participant_unavailable",
                character_name=character_name,
                signal_kind=signal_kind,
            )
        return executor.apply_tendency_signal(
            pet,
            signal_kind=signal_kind,
            strength=strength,
            sim_now=float(now),
        )
