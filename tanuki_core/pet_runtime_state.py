from dataclasses import dataclass, field

from .activity_state import PetActivityState
from .transformation_state import PetTransformationState


PET_STATE_PROXY_FIELDS = {
    "behavior_state": (
        "mood_score",
        "mood_state",
        "lonely_timer",
        "distress_ready_at",
        "last_company_seen_at",
        "solitude_event_cooldown_until",
        "crowding_event_cooldown_until",
        "offer_miss_event_cooldown_until",
        "idle_side_stand_armed",
        "state",
        "state_timer",
        "current_purpose",
        "current_action_tag",
        "current_mood_tag",
        "ambient_low_mood_tag",
        "ambient_low_mood_streak",
        "behavior_layer_refresh_skip_counter",
        "behavior_layer_refresh_divisor",
        "high_level_ai_refresh_skip_counter",
        "high_level_ai_refresh_divisor",
    ),
    "interaction_state": (
        "dragging",
        "drag_press_pending",
        "drag_motion_detected",
        "drag_press_global_x",
        "drag_press_global_y",
        "drag_start_time",
        "click_count",
        "is_angry_locked",
        "user_visible",
        "offer_locked_until",
        "offer_scene_kind",
        "held_item_kind",
        "held_item_source",
        "held_item_started_at",
        "held_item_widget",
        "negative_afterglow_until",
        "negative_afterglow_care_block_until",
        "negative_afterglow_preferred_moods",
        "negative_afterglow_forbidden_moods",
        "offer_hover_reaction_cooldown_until",
    ),
    "motion_state": (
        "direction",
        "last_x",
        "stuck_count",
        "vy",
        "collision_displaced_until",
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
    "perception_state": (
        "perception_anchor",
        "perception_support_surface",
        "perception_nearest_visible_pet_name",
        "perception_nearest_visible_pet_distance",
        "perception_nearest_distressed_child_name",
        "perception_nearest_distressed_child_distance",
        "perception_visible_adult_count",
        "perception_visible_child_count",
        "perception_window_perch_available",
        "perception_window_flight_target_available",
        "perception_situation_tag",
    ),
    "intent_state": (
        "intent_kind",
        "intent_target_name",
        "intent_target_form",
        "intent_locked_until",
        "intent_reconsider_after",
        "observe_blocked_target_name",
        "observe_blocked_until",
        "observe_streak_target_name",
        "observe_streak_count",
        "observe_notice_cooldown_until",
        "pending_social_log_event",
        "social_log_event_cooldown_until",
        "intent_priority",
        "intent_source",
        "intent_context",
        "intent_reason",
    ),
    "relationship_state": (
        "relationship_entries",
        "relationship_focus_target_name",
        "relationship_focus_familiarity",
        "relationship_focus_trust",
        "relationship_focus_attachment",
        "relationship_focus_tension",
    ),
    "expression_state": (
        "expression_animation_context",
        "expression_relation_overlay",
        "expression_focus_target_name",
        "expression_posture_bias",
        "expression_spacing_bias",
        "expression_look_at_target",
    ),
}


@dataclass
class PetBehaviorState:
    mood_score: float = 60.0
    mood_state: str = "normal"
    lonely_timer: int = 0
    distress_ready_at: float = 0.0
    last_company_seen_at: float = 0.0
    solitude_event_cooldown_until: float = 0.0
    crowding_event_cooldown_until: float = 0.0
    offer_miss_event_cooldown_until: float = 0.0
    idle_side_stand_armed: bool = False
    state: str = "idle"
    state_timer: int = 0
    current_purpose: str = ""
    current_action_tag: str = "stand"
    current_mood_tag: str = "happy"
    ambient_low_mood_tag: str = ""
    ambient_low_mood_streak: int = 0
    behavior_layer_refresh_skip_counter: float = 0.0
    behavior_layer_refresh_divisor: int = 1
    high_level_ai_refresh_skip_counter: float = 0.0
    high_level_ai_refresh_divisor: int = 1


@dataclass
class PetInteractionState:
    dragging: bool = False
    drag_press_pending: bool = False
    drag_motion_detected: bool = False
    drag_press_global_x: int = 0
    drag_press_global_y: int = 0
    drag_start_time: float = 0.0
    click_count: int = 0
    is_angry_locked: bool = False
    user_visible: bool = True
    offer_locked_until: float = 0.0
    offer_scene_kind: str = "none"
    held_item_kind: str = ""
    held_item_source: str = "none"
    held_item_started_at: float = 0.0
    held_item_widget: object | None = None
    negative_afterglow_until: float = 0.0
    negative_afterglow_care_block_until: float = 0.0
    negative_afterglow_preferred_moods: tuple[str, ...] = ()
    negative_afterglow_forbidden_moods: tuple[str, ...] = ()
    offer_hover_reaction_cooldown_until: float = 0.0


@dataclass
class PetMotionState:
    direction: int = 1
    last_x: int = 0
    stuck_count: int = 0
    vy: float = 0.0
    collision_displaced_until: float = 0.0
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
class PetPerceptionState:
    perception_anchor: str = "floor"
    perception_support_surface: str = "desktop_floor"
    perception_nearest_visible_pet_name: str = ""
    perception_nearest_visible_pet_distance: float = 0.0
    perception_nearest_distressed_child_name: str = ""
    perception_nearest_distressed_child_distance: float = 0.0
    perception_visible_adult_count: int = 0
    perception_visible_child_count: int = 0
    perception_window_perch_available: bool = False
    perception_window_flight_target_available: bool = False
    perception_situation_tag: str = "stable"


@dataclass
class PetIntentState:
    intent_kind: str = "none"
    intent_target_name: str = ""
    intent_target_form: str = ""
    intent_locked_until: float = 0.0
    intent_reconsider_after: float = 0.0
    observe_blocked_target_name: str = ""
    observe_blocked_until: float = 0.0
    observe_streak_target_name: str = ""
    observe_streak_count: int = 0
    observe_notice_cooldown_until: float = 0.0
    pending_social_log_event: dict[str, object] = field(default_factory=dict)
    social_log_event_cooldown_until: float = 0.0
    intent_priority: int = 0
    intent_source: str = "none"
    intent_context: str = "ambient"
    intent_reason: str = ""


@dataclass
class RelationshipEntry:
    familiarity: float = 0.0
    trust: float = 0.0
    attachment: float = 0.0
    tension: float = 0.0
    last_seen_at: float = 0.0
    last_interaction_at: float = 0.0


@dataclass
class PetRelationshipState:
    relationship_entries: dict[str, RelationshipEntry] = field(default_factory=dict)
    relationship_focus_target_name: str = ""
    relationship_focus_familiarity: float = 0.0
    relationship_focus_trust: float = 0.0
    relationship_focus_attachment: float = 0.0
    relationship_focus_tension: float = 0.0


@dataclass
class PetExpressionState:
    expression_animation_context: str = "ambient"
    expression_relation_overlay: str = "none"
    expression_focus_target_name: str = ""
    expression_posture_bias: str = "neutral"
    expression_spacing_bias: str = "neutral"
    expression_look_at_target: bool = False


@dataclass
class PetRuntimeStateBundle:
    behavior: PetBehaviorState
    interaction: PetInteractionState
    motion: PetMotionState
    social: PetSocialState
    care: PetCareState
    windowing: PetWindowingState
    perception: PetPerceptionState
    intent: PetIntentState
    relationship: PetRelationshipState
    expression: PetExpressionState
    activity: PetActivityState
    transformation: PetTransformationState


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
        perception=PetPerceptionState(),
        intent=PetIntentState(),
        relationship=PetRelationshipState(),
        expression=PetExpressionState(),
        activity=PetActivityState(),
        transformation=PetTransformationState(),
    )
