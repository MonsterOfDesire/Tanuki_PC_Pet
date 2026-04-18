from dataclasses import dataclass
from typing import Optional


WINDOW_PERCH_DECISION_NONE = "none"
WINDOW_PERCH_DECISION_CONTINUE = "continue"
WINDOW_PERCH_DECISION_DETACH = "detach"
WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR = "detach_to_taskbar"

WINDOW_FLIGHT_DECISION_NONE = "none"
WINDOW_FLIGHT_DECISION_STOP = "stop"
WINDOW_FLIGHT_DECISION_TASKBAR_TICK = "taskbar_tick"
WINDOW_FLIGHT_DECISION_WINDOW_TICK = "window_tick"
WINDOW_FLIGHT_DECISION_ATTACH = "attach"


@dataclass(frozen=True)
class WindowPerchDecision:
    action: str
    handled: bool = False
    target_x: Optional[int] = None


@dataclass(frozen=True)
class WindowPerchContext:
    is_perched: bool
    dragging: bool
    care_mode: str
    social_mode: str
    is_recovering: bool
    has_window_tracker: bool
    has_surface: bool
    can_perch_on_surface: bool
    is_child_distressed: bool
    adult_should_leave_for_care: bool
    auto_perch_expired: bool
    current_x: int
    fallback_target_x: Optional[int] = None


@dataclass(frozen=True)
class WindowFlightDecision:
    action: str
    handled: bool = False


@dataclass(frozen=True)
class WindowFlightContext:
    mode: str
    dragging: bool
    care_mode: str
    social_mode: str
    is_recovering: bool
    has_window_tracker: bool
    has_surface: bool
    can_perch_on_surface: bool
    has_anchor_center: bool
    distance_to_target: Optional[float]


class WindowingCoordinator:
    def decide_window_perch(self, context: WindowPerchContext):
        if not context.is_perched:
            return WindowPerchDecision(action=WINDOW_PERCH_DECISION_NONE)
        if (
            context.dragging or
            context.care_mode != "none" or
            context.social_mode != "none" or
            context.is_recovering or
            not context.has_window_tracker or
            not context.has_surface
        ):
            return WindowPerchDecision(action=WINDOW_PERCH_DECISION_DETACH)
        if not context.can_perch_on_surface:
            return WindowPerchDecision(
                action=WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
                target_x=context.current_x,
            )
        if context.is_child_distressed:
            return WindowPerchDecision(
                action=WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
                target_x=context.current_x,
            )
        if context.adult_should_leave_for_care:
            return WindowPerchDecision(
                action=WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
                target_x=context.fallback_target_x if context.fallback_target_x is not None else context.current_x,
            )
        if context.auto_perch_expired:
            return WindowPerchDecision(
                action=WINDOW_PERCH_DECISION_DETACH_TO_TASKBAR,
                target_x=context.fallback_target_x if context.fallback_target_x is not None else context.current_x,
            )
        return WindowPerchDecision(action=WINDOW_PERCH_DECISION_CONTINUE, handled=True)

    def decide_window_flight(self, context: WindowFlightContext):
        if context.mode == "none":
            return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_NONE)
        if (
            context.dragging or
            context.care_mode != "none" or
            context.social_mode != "none" or
            context.is_recovering or
            not context.has_window_tracker
        ):
            return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_STOP)
        if context.mode == "to_taskbar":
            return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_TASKBAR_TICK, handled=True)
        if not context.has_surface or not context.can_perch_on_surface or not context.has_anchor_center:
            return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_STOP)
        if context.distance_to_target is not None and context.distance_to_target <= 14:
            return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_ATTACH, handled=True)
        return WindowFlightDecision(action=WINDOW_FLIGHT_DECISION_WINDOW_TICK, handled=True)

WINDOWING_COORDINATOR = WindowingCoordinator()
