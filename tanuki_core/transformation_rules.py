from __future__ import annotations

from dataclasses import dataclass

from .transformation_state import (
    FORM_BASE,
    FORM_TRANSFORMED,
    TRANSFORMATION_PHASE_REVEALING,
    TRANSFORMATION_PHASE_WHITENING,
)


TRANSFORMATION_PHASE_SECONDS = 0.45
TRANSFORMATION_AUTO_WORLD_MODE = "golden_legend"
TRANSFORMATION_AUTO_WORLD_MODES = frozenset(
    {"golden_legend", "sandbox"}
)
TRANSFORMATION_AUTO_START_RETRY_SECONDS = 30.0
TRANSFORMATION_AUTO_END_RETRY_SECONDS = 5.0

AUTO_ACTION_NONE = "none"
AUTO_ACTION_SCHEDULE = "schedule"
AUTO_ACTION_SCHEDULE_MANUAL_END = "schedule_manual_end"
AUTO_ACTION_START = "start"
AUTO_ACTION_END = "end"
AUTO_ACTION_CLEANUP_PREVIEW = "cleanup_preview"


@dataclass(frozen=True)
class TransformationEligibilitySnapshot:
    character_name: str
    supported: bool
    current_form: str = FORM_BASE
    transitioning: bool = False
    visible: bool = True
    user_visible: bool = True
    dragging: bool = False
    active_activity: bool = False
    offer_busy: bool = False
    care_busy: bool = False
    social_busy: bool = False
    recovering: bool = False
    angry_locked: bool = False
    held_item: bool = False
    vertical_velocity: float = 0.0
    flight_mode: str = "none"
    perched: bool = False


@dataclass(frozen=True)
class TransformationEligibilityDecision:
    allowed: bool
    reason: str = ""
    target_form: str = ""


@dataclass(frozen=True)
class TransformationAutoSnapshot:
    world_mode: str
    current_form: str
    transitioning: bool
    auto_session: bool
    mood_score: float
    now: float
    next_attempt_at: float = 0.0
    form_expires_at: float = 0.0
    retry_at: float = 0.0


@dataclass(frozen=True)
class TransformationAutoDecision:
    action: str = AUTO_ACTION_NONE
    reason: str = ""


def evaluate_transformation_eligibility(
    snapshot: TransformationEligibilitySnapshot,
) -> TransformationEligibilityDecision:
    target_form = (
        FORM_BASE
        if str(snapshot.current_form or FORM_BASE) == FORM_TRANSFORMED
        else FORM_TRANSFORMED
    )
    if not snapshot.supported:
        return TransformationEligibilityDecision(False, "unsupported_character", target_form)
    if snapshot.transitioning:
        return TransformationEligibilityDecision(False, "transition_active", target_form)
    if not snapshot.user_visible:
        return TransformationEligibilityDecision(False, "participant_disabled", target_form)
    if not snapshot.visible:
        return TransformationEligibilityDecision(False, "participant_hidden", target_form)
    if snapshot.active_activity:
        return TransformationEligibilityDecision(False, "participant_owned", target_form)
    if snapshot.dragging:
        return TransformationEligibilityDecision(False, "participant_dragging", target_form)
    if snapshot.offer_busy or snapshot.held_item:
        return TransformationEligibilityDecision(False, "participant_offer_busy", target_form)
    if snapshot.care_busy:
        return TransformationEligibilityDecision(False, "participant_care_busy", target_form)
    if snapshot.social_busy:
        return TransformationEligibilityDecision(False, "participant_social_busy", target_form)
    if snapshot.recovering or snapshot.angry_locked:
        return TransformationEligibilityDecision(False, "participant_recovering", target_form)
    if (
        abs(float(snapshot.vertical_velocity)) > 1e-6
        or str(snapshot.flight_mode or "none") != "none"
        or snapshot.perched
    ):
        return TransformationEligibilityDecision(False, "airborne", target_form)
    return TransformationEligibilityDecision(True, target_form=target_form)


def decide_auto_transformation(
    snapshot: TransformationAutoSnapshot,
) -> TransformationAutoDecision:
    now = float(snapshot.now)
    if snapshot.transitioning:
        return TransformationAutoDecision(reason="transition_active")
    if now < float(snapshot.retry_at or 0.0):
        return TransformationAutoDecision(reason="retry_wait")

    world_mode = str(snapshot.world_mode or "")
    if world_mode not in TRANSFORMATION_AUTO_WORLD_MODES:
        if snapshot.auto_session and snapshot.current_form == FORM_TRANSFORMED:
            return TransformationAutoDecision(
                action=AUTO_ACTION_END,
                reason="auto_disabled_cleanup",
            )
        return TransformationAutoDecision(reason="auto_disabled")

    if snapshot.current_form == FORM_TRANSFORMED:
        if not snapshot.auto_session:
            if world_mode == TRANSFORMATION_AUTO_WORLD_MODE:
                return TransformationAutoDecision(
                    action=AUTO_ACTION_CLEANUP_PREVIEW,
                    reason="preview_form_in_formal_world",
                )
            if float(snapshot.form_expires_at or 0.0) <= 0.0:
                return TransformationAutoDecision(
                    action=AUTO_ACTION_SCHEDULE_MANUAL_END,
                    reason="manual_duration_missing",
                )
            if now >= float(snapshot.form_expires_at):
                return TransformationAutoDecision(
                    action=AUTO_ACTION_END,
                    reason="manual_duration_complete",
                )
            return TransformationAutoDecision(
                reason="manual_preview_active",
            )
        if now >= float(snapshot.form_expires_at or 0.0):
            return TransformationAutoDecision(
                action=AUTO_ACTION_END,
                reason="duration_complete",
            )
        return TransformationAutoDecision(reason="transformed_active")

    if float(snapshot.next_attempt_at or 0.0) <= 0.0:
        return TransformationAutoDecision(
            action=AUTO_ACTION_SCHEDULE,
            reason="schedule_missing",
        )
    if now < float(snapshot.next_attempt_at):
        return TransformationAutoDecision(reason="base_wait")
    if float(snapshot.mood_score) < 50.0:
        return TransformationAutoDecision(reason="mood_not_normal")
    return TransformationAutoDecision(
        action=AUTO_ACTION_START,
        reason="auto_ready",
    )


def compute_transformation_whiteness(
    phase: str,
    *,
    elapsed_seconds: float,
    phase_seconds: float = TRANSFORMATION_PHASE_SECONDS,
) -> tuple[float, bool]:
    duration = max(1e-6, float(phase_seconds))
    progress = max(0.0, min(1.0, float(elapsed_seconds) / duration))
    if phase == TRANSFORMATION_PHASE_WHITENING:
        return progress, progress >= 1.0
    if phase == TRANSFORMATION_PHASE_REVEALING:
        return 1.0 - progress, progress >= 1.0
    return 0.0, True
