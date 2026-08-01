from __future__ import annotations

from dataclasses import fields

from .activity_coordinator import ActivityCoordinator
from .activity_profiles import ActivityAnimationBinding
from .activity_state import (
    ActivityParticipant,
    ActivityParticipantSnapshot,
    ActivityStateProjection,
    PetActivityState,
)
from .manifest_animation_resolver import (
    ManifestAnimationApplyResult,
    ManifestAnimationResolver,
)
from .pet_intent_rules import (
    INTENT_OBSERVE,
    INTENT_POST_OBSERVE_INTERACTION,
    SLEEP_JOIN_INTENT_KINDS,
)


PET_ACTIVITY_FIELD_NAMES = tuple(
    field_info.name
    for field_info in fields(PetActivityState)
)


def pet_has_active_activity(pet) -> bool:
    state = getattr(pet, "activity_state", None)
    return bool(state is not None and getattr(state, "active", False))


class ActivityRuntimeAdapter:
    def __init__(
        self,
        *,
        animation_resolver: ManifestAnimationResolver | None = None,
    ):
        self.animation_resolver = (
            animation_resolver or ManifestAnimationResolver()
        )

    def build_participant_snapshot(
        self,
        pet,
        *,
        role: str,
        now: float,
        capability_ready: bool = True,
        capability_reason: str = "",
    ) -> ActivityParticipantSnapshot:
        now = float(now)
        busy_reasons = []
        if bool(
            getattr(pet, "dragging", False)
            or getattr(pet, "drag_press_pending", False)
        ):
            busy_reasons.append("drag")
        if bool(getattr(pet, "is_angry_locked", False)):
            busy_reasons.append("angry")
        if bool(getattr(pet, "is_recovering", False)):
            busy_reasons.append("recovery")
        if getattr(pet, "care_mode", "none") != "none":
            busy_reasons.append("care")
        if getattr(pet, "care_partner", None) is not None:
            busy_reasons.append("care_partner")
        is_under_care = getattr(pet, "is_under_care", None)
        if callable(is_under_care) and bool(is_under_care(now)):
            busy_reasons.append("care_lock")
        if getattr(pet, "social_mode", "none") != "none":
            busy_reasons.append("social")
        if getattr(pet, "intent_kind", "none") in {
            INTENT_OBSERVE,
            INTENT_POST_OBSERVE_INTERACTION,
        }:
            busy_reasons.append("observe")
        if getattr(pet, "intent_kind", "none") in SLEEP_JOIN_INTENT_KINDS:
            busy_reasons.append("sleep_join")
        if getattr(pet, "flight_mode", "none") != "none":
            busy_reasons.append("flight")
        if bool(getattr(pet, "perched_window_hwnd", 0)):
            busy_reasons.append("window_perch")
        if float(getattr(pet, "vy", 0.0) or 0.0) != 0.0:
            busy_reasons.append("airborne")
        is_offer_locked = getattr(pet, "is_offer_locked", None)
        if (
            bool(is_offer_locked(now))
            if callable(is_offer_locked)
            else getattr(pet, "offer_scene_kind", "none") != "none"
        ):
            busy_reasons.append("offer")
        if str(getattr(pet, "held_item_kind", "") or ""):
            busy_reasons.append("held_item")

        state = getattr(pet, "activity_state", None)
        active_activity_id = (
            str(getattr(state, "activity_id", "") or "")
            if state is not None and getattr(state, "active", False)
            else ""
        )
        is_visible = getattr(pet, "isVisible", None)
        visible = bool(is_visible()) if callable(is_visible) else True
        enabled = bool(getattr(pet, "user_visible", True))
        return ActivityParticipantSnapshot(
            participant=ActivityParticipant(
                str(getattr(pet, "name", "") or ""),
                role,
            ),
            visible=visible,
            enabled=enabled,
            active_activity_id=active_activity_id,
            busy_reasons=tuple(busy_reasons),
            capability_ready=bool(capability_ready),
            capability_reason=capability_reason,
        )

    def apply_projections(
        self,
        pets_by_name: dict[str, object],
        projections: tuple[ActivityStateProjection, ...],
    ) -> int:
        applied_count = 0
        for projection in projections or ():
            pet = pets_by_name.get(projection.participant_name)
            if pet is None:
                continue
            target_state = getattr(pet, "activity_state", None)
            if target_state is None:
                target_state = PetActivityState()
                pet.activity_state = target_state
            for field_name in PET_ACTIVITY_FIELD_NAMES:
                setattr(
                    target_state,
                    field_name,
                    getattr(projection.state, field_name),
                )
            applied_count += 1
        return applied_count

    def clear_released_participants(
        self,
        pets_by_name: dict[str, object],
        participant_names: tuple[str, ...],
        *,
        expected_activity_id: str,
    ) -> int:
        cleared_count = 0
        for participant_name in participant_names or ():
            pet = pets_by_name.get(participant_name)
            state = getattr(pet, "activity_state", None) if pet else None
            if state is not None and state.clear(
                expected_activity_id=expected_activity_id
            ):
                cleared_count += 1
        return cleared_count

    def apply_phase_animation(
        self,
        pet,
        binding: ActivityAnimationBinding,
    ) -> ManifestAnimationApplyResult:
        result = self.animation_resolver.apply(
            pet,
            binding.build_request(
                float(getattr(pet, "mood_score", 60.0))
            ),
        )
        if result.applied and result.selection is not None:
            pet.state = (
                result.selection.purpose
                if result.selection.purpose in {"idle", "move"}
                else "idle"
            )
            pet.state_timer = 0
            if result.selection.purpose == "idle":
                pet.vy = 0.0
                pet.fall_origin_y = None
            refresh_movement_state = getattr(
                pet,
                "refresh_movement_state",
                None,
            )
            if callable(refresh_movement_state):
                refresh_movement_state()
        return result

    def apply_mood_delta(self, pet, mood_delta: float) -> bool:
        if pet is None:
            return False
        pet.mood_score = max(
            0.0,
            min(
                100.0,
                float(getattr(pet, "mood_score", 60.0))
                + float(mood_delta),
            ),
        )
        sync_mood_state = getattr(
            pet,
            "sync_mood_state_with_score",
            None,
        )
        if callable(sync_mood_state):
            sync_mood_state()
        return True

    def interrupt_participant(
        self,
        coordinator: ActivityCoordinator,
        pet,
        *,
        now: float,
        reason: str,
    ):
        activity = coordinator.get_activity_for_participant(
            str(getattr(pet, "name", "") or "")
        )
        if activity is None:
            return None
        return coordinator.interrupt(
            activity.activity_id,
            now=float(now),
            reason=reason,
            force=True,
        )
