from dataclasses import dataclass


PET_STATE_PROXY_FIELDS = {
    "behavior_state": (
        "mood_score",
        "mood_state",
        "lonely_timer",
        "distress_ready_at",
        "state",
        "state_timer",
        "current_purpose",
        "current_action_tag",
        "current_mood_tag",
    ),
    "interaction_state": (
        "dragging",
        "drag_start_time",
        "click_count",
        "is_angry_locked",
        "user_visible",
    ),
    "motion_state": (
        "direction",
        "last_x",
        "stuck_count",
        "vy",
        "fall_origin_y",
        "gravity",
        "bounce",
        "radius",
        "mass",
    ),
    "social_state": (
        "social_mode",
        "social_target",
        "social_started_at",
        "social_timer_frames",
        "social_cooldown_end",
        "social_distance",
        "social_cooldown_duration",
    ),
    "care_state": (
        "is_recovering",
        "recovery_end_time",
        "recovery_motion_mode",
        "stationary_move_mode",
        "stationary_move_key",
        "is_hugging",
        "care_mode",
        "care_target",
        "care_end_time",
        "care_cooldown_end",
        "care_move_direction",
        "care_plan",
        "care_partner",
        "care_lock_mode",
        "care_lock_end_time",
    ),
    "windowing_state": (
        "perched_window_hwnd",
        "window_perch_offset_x",
        "window_perch_mode",
        "window_perch_origin",
        "window_perch_end_time",
        "flight_mode",
        "flight_target_hwnd",
        "flight_target_x",
        "flight_target_y",
        "flight_cooldown_end",
        "movement_state",
    ),
}


@dataclass
class PetBehaviorState:
    mood_score: float = 60.0
    mood_state: str = "normal"
    lonely_timer: int = 0
    distress_ready_at: float = 0.0
    state: str = "idle"
    state_timer: int = 0
    current_purpose: str = ""
    current_action_tag: str = "stand"
    current_mood_tag: str = "happy"


@dataclass
class PetInteractionState:
    dragging: bool = False
    drag_start_time: float = 0.0
    click_count: int = 0
    is_angry_locked: bool = False
    user_visible: bool = True


@dataclass
class PetMotionState:
    direction: int = 1
    last_x: int = 0
    stuck_count: int = 0
    vy: float = 0.0
    fall_origin_y: int | None = None
    gravity: float = 1.2
    bounce: float = -0.3
    radius: float = 0.0
    mass: float = 1.0


@dataclass
class PetSocialState:
    social_mode: str = "none"
    social_target: object | None = None
    social_started_at: float = 0.0
    social_timer_frames: int = 0
    social_cooldown_end: float = 0.0
    social_distance: int = 600
    social_cooldown_duration: float = 5.0


@dataclass
class PetCareState:
    is_recovering: bool = False
    recovery_end_time: float = 0.0
    recovery_motion_mode: str = "stay"
    stationary_move_mode: bool = False
    stationary_move_key: str = ""
    is_hugging: bool = False
    care_mode: str = "none"
    care_target: object | None = None
    care_end_time: float = 0.0
    care_cooldown_end: float = 0.0
    care_move_direction: int = 0
    care_plan: str = "auto"
    care_partner: object | None = None
    care_lock_mode: str = "none"
    care_lock_end_time: float = 0.0


@dataclass
class PetWindowingState:
    perched_window_hwnd: int = 0
    window_perch_offset_x: int = 0
    window_perch_mode: str = "idle"
    window_perch_origin: str = "manual"
    window_perch_end_time: float = 0.0
    flight_mode: str = "none"
    flight_target_hwnd: int = 0
    flight_target_x: int = 0
    flight_target_y: int = 0
    flight_cooldown_end: float = 0.0
    movement_state: object | None = None


@dataclass
class PetRuntimeStateBundle:
    behavior: PetBehaviorState
    interaction: PetInteractionState
    motion: PetMotionState
    social: PetSocialState
    care: PetCareState
    windowing: PetWindowingState


def build_pet_runtime_state(name):
    social_state = PetSocialState()
    if name == "Tokai Teio":
        social_state.social_distance = 600
        social_state.social_cooldown_duration = 10.0
    elif name == "Tsurumaru Tsuyoshi":
        social_state.social_distance = 350
        social_state.social_cooldown_duration = 10.0

    return PetRuntimeStateBundle(
        behavior=PetBehaviorState(),
        interaction=PetInteractionState(),
        motion=PetMotionState(),
        social=social_state,
        care=PetCareState(),
        windowing=PetWindowingState(),
    )
