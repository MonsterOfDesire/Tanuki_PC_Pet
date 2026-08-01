from dataclasses import dataclass


INTENT_NONE = "none"
INTENT_USER_DRAG = "user_drag"
INTENT_LOCKED = "locked"
INTENT_RECOVER = "recover"
INTENT_CARE_CHILD = "care_child"
INTENT_FOLLOW_LEADER = "follow_leader"
INTENT_MIMIC_PARTNER = "mimic_partner"
INTENT_FLIGHT_TO_WINDOW = "flight_to_window"
INTENT_FLIGHT_TO_TASKBAR = "flight_to_taskbar"
INTENT_PERCH_HOLD = "perch_hold"
INTENT_RANDOM_ROAM = "random_roam"
INTENT_OBSERVE = "observe"
INTENT_POST_OBSERVE_INTERACTION = "post_observe_interaction"
INTENT_SLEEP_OBSERVE = "sleep_observe"
INTENT_SLEEP_JOIN_APPROACH = "sleep_join_approach"
INTENT_AMBIENT_IDLE = "ambient_idle"

SLEEP_JOIN_INTENT_KINDS = frozenset(
    {
        INTENT_SLEEP_OBSERVE,
        INTENT_SLEEP_JOIN_APPROACH,
    }
)

AMBIENT_INTENT_KINDS = {
    INTENT_NONE,
    INTENT_RANDOM_ROAM,
    INTENT_OBSERVE,
    INTENT_AMBIENT_IDLE,
}
RANDOM_PROGRESS_INTENT_KINDS = {
    INTENT_RANDOM_ROAM,
    INTENT_AMBIENT_IDLE,
}
DEFAULT_AMBIENT_RESELECT_INTERVAL = 1.5


@dataclass(frozen=True)
class IntentSnapshot:
    intent_kind: str
    intent_target_name: str = ""
    intent_priority: int = 0
    intent_source: str = "none"
    intent_context: str = "ambient"
    intent_reason: str = ""


@dataclass(frozen=True)
class IntentReselectPlan:
    allow_reselect: bool
    next_reconsider_after: float | None = None
    reason: str = ""


def derive_current_intent(
    *,
    now,
    dragging,
    is_angry_locked,
    is_recovering,
    care_lock_active,
    care_mode,
    social_mode,
    flight_mode,
    perched_window_hwnd,
    current_purpose,
    state,
    intent_reconsider_after,
    focus_target_name,
    expression_animation_context,
    social_target_name,
    care_target_name,
    negative_afterglow_active=False,
):
    if dragging:
        return IntentSnapshot(
            intent_kind=INTENT_USER_DRAG,
            intent_priority=100,
            intent_source="user",
            intent_context="drag",
            intent_reason="dragging",
        )
    if is_angry_locked:
        return IntentSnapshot(
            intent_kind=INTENT_LOCKED,
            intent_priority=95,
            intent_source="interaction",
            intent_context="angry",
            intent_reason="angry_locked",
        )
    if care_mode != "none" or care_lock_active:
        return IntentSnapshot(
            intent_kind=INTENT_CARE_CHILD,
            intent_target_name=care_target_name,
            intent_priority=90,
            intent_source="care",
            intent_context=care_mode if care_mode != "none" else "care_lock",
            intent_reason="care_active",
        )
    if is_recovering:
        return IntentSnapshot(
            intent_kind=INTENT_RECOVER,
            intent_priority=85,
            intent_source="recovery",
            intent_context="recovery",
            intent_reason="recovering",
        )
    if social_mode == "following":
        return IntentSnapshot(
            intent_kind=INTENT_FOLLOW_LEADER,
            intent_target_name=social_target_name,
            intent_priority=75,
            intent_source="social",
            intent_context="social_follow",
            intent_reason="social_following",
        )
    if social_mode == "mimicking":
        return IntentSnapshot(
            intent_kind=INTENT_MIMIC_PARTNER,
            intent_target_name=social_target_name,
            intent_priority=75,
            intent_source="social",
            intent_context="social_mimic",
            intent_reason="social_mimicking",
        )
    if flight_mode == "to_taskbar":
        return IntentSnapshot(
            intent_kind=INTENT_FLIGHT_TO_TASKBAR,
            intent_priority=70,
            intent_source="window",
            intent_context="flight_taskbar",
            intent_reason="flight_to_taskbar",
        )
    if flight_mode != "none":
        return IntentSnapshot(
            intent_kind=INTENT_FLIGHT_TO_WINDOW,
            intent_priority=70,
            intent_source="window",
            intent_context="flight_window",
            intent_reason="flight_active",
        )
    if int(perched_window_hwnd or 0):
        return IntentSnapshot(
            intent_kind=INTENT_PERCH_HOLD,
            intent_priority=65,
            intent_source="window",
            intent_context="perch_hold",
            intent_reason="perched",
        )
    if current_purpose == "move" or state == "move":
        return IntentSnapshot(
            intent_kind=INTENT_RANDOM_ROAM,
            intent_priority=20,
            intent_source="ambient",
            intent_context="random_move",
            intent_reason="ambient_move",
        )
    if (
        not negative_afterglow_active and
        focus_target_name and
        expression_animation_context in {"relation_watch", "relation_close"} and
        float(intent_reconsider_after or 0.0) <= float(now)
    ):
        return IntentSnapshot(
            intent_kind=INTENT_OBSERVE,
            intent_target_name=focus_target_name,
            intent_priority=15,
            intent_source="ambient",
            intent_context="observe",
            intent_reason="focus_visible_pet",
        )
    return IntentSnapshot(
        intent_kind=INTENT_AMBIENT_IDLE,
        intent_priority=10,
        intent_source="ambient",
        intent_context="ambient_idle",
        intent_reason="idle",
    )


def resolve_intent_reselect_gate(
    *,
    now,
    intent_kind,
    intent_reconsider_after,
    dragging,
    is_angry_locked,
    is_recovering,
    care_lock_active,
    care_mode,
    social_mode,
    flight_mode,
    perched_window_hwnd,
):
    if dragging:
        return IntentReselectPlan(allow_reselect=False, reason="dragging")
    if is_angry_locked:
        return IntentReselectPlan(allow_reselect=False, reason="angry_locked")
    if is_recovering:
        return IntentReselectPlan(allow_reselect=False, reason="recovering")
    if care_lock_active or care_mode != "none":
        return IntentReselectPlan(allow_reselect=False, reason="care_active")
    if social_mode != "none":
        return IntentReselectPlan(allow_reselect=False, reason="social_active")
    if flight_mode != "none":
        return IntentReselectPlan(allow_reselect=False, reason="flight_active")
    if int(perched_window_hwnd or 0):
        return IntentReselectPlan(allow_reselect=False, reason="perched")

    if intent_kind not in AMBIENT_INTENT_KINDS:
        return IntentReselectPlan(allow_reselect=False, reason="non_ambient")

    if float(intent_reconsider_after or 0.0) > float(now):
        return IntentReselectPlan(allow_reselect=False, reason="cooldown")

    return IntentReselectPlan(
        allow_reselect=True,
        next_reconsider_after=float(now) + DEFAULT_AMBIENT_RESELECT_INTERVAL,
        reason="ambient_refresh",
    )


def allow_random_behavior_reselect(*, intent_kind, intent_gate_open):
    return bool(intent_gate_open or intent_kind in RANDOM_PROGRESS_INTENT_KINDS)


def pet_has_sleep_join_intent(pet) -> bool:
    return bool(
        pet is not None
        and getattr(pet, "intent_kind", "none")
        in SLEEP_JOIN_INTENT_KINDS
    )
