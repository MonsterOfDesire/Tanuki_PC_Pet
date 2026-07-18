from dataclasses import dataclass
import math


ITEM_RAMEN = "ramen"
ITEM_HONEY = "honey"
ITEM_TEA = "tea"
ITEM_BOTTLE = "bottle"
ITEM_LOLLIPOP = "lollipop"
CONTEXT_OFFER_PREVIEW = "offer_preview"
CONTEXT_OFFER_DENIED = "offer_denied"
CONTEXT_HONEY_GUARD_MOVE = "honey_guard_move"
CONTEXT_HONEY_GUARD_TAKE = "honey_guard_take"
CONTEXT_BOTTLE_FEED_HOLD = "bottle_feed_hold"
CONTEXT_BOTTLE_FEED_WATCH = "bottle_feed_watch"
CONTEXT_BOTTLE_FEED_CHILD_APPROACH = "bottle_feed_child_approach"
CONTEXT_BOTTLE_FEED_CHILD_DRINK = "bottle_feed_child_drink"
BASE_CANVAS_SIZE = 600.0
OFFER_PREVIEW_FRAME_PADDING = 108.0
OFFER_HOVER_TIMEOUT_SECONDS = 5.0
OFFER_HOVER_REACTION_COOLDOWN_BUFFER_SECONDS = 3.0
OFFER_HOVER_NEGATIVE_AFTERGLOW_BUFFER_SECONDS = 4.0
OFFER_HOVER_REACTION_STAGE_ONE_SECONDS = 3.0
OFFER_HOVER_REACTION_STAGE_TWO_SECONDS = 3.0
OFFER_HOVER_AVOID_CURSOR_DISTANCE = 220.0
OFFER_HOVER_AVOID_CURSOR_SPEED_SCALE = 1.15
OFFER_HOVER_AVOID_CURSOR_MIN_SPEED = 3.6
GROUND_ITEM_LIFETIME_SECONDS = 60.0
GROUND_ITEM_FALL_GRAVITY = 1.4
GROUND_ITEM_MAX_FALL_SPEED = 18.0
GROUND_ITEM_PICKUP_RADIUS = 55.0
DIRECT_OFFER_ACCEPT_PURPOSE_ORDER = ("move", "idle")
DIRECT_OFFER_STATIONARY_ACCEPT_PURPOSE_ORDER = ("idle", "move")
DIRECT_OFFER_MOBILE_ACCEPT_CHANCE = 0.5
DIRECT_OFFER_MOBILE_MOVE_SPEED_SCALE = 0.75
DIRECT_OFFER_MOBILE_MOVE_TARGET_OFFSET = 96.0


@dataclass(frozen=True)
class OfferItemDefinition:
    kind: str
    label: str
    accent_color: str
    icon_relative_path: str = ""


@dataclass(frozen=True)
class OfferTakeHotspot:
    x: float
    y: float
    radius: float = 10.0


@dataclass(frozen=True)
class OfferGuardianCandidate:
    name: str
    distance: float
    is_visible: bool


@dataclass(frozen=True)
class OfferHotspotMatch:
    matched: bool
    distance: float
    hotspot_global_x: float
    hotspot_global_y: float
    hotspot_radius: float


@dataclass(frozen=True)
class OfferPreviewMatch:
    matched: bool
    distance: float


@dataclass(frozen=True)
class OfferHoverReactionStage:
    purpose: str
    action_type: str
    mood_tag: str
    duration_seconds: float


@dataclass(frozen=True)
class OfferHoverReactionVariant:
    label: str
    avoid_cursor: bool
    stages: tuple[OfferHoverReactionStage, ...]


OFFER_ITEM_DEFINITIONS = (
    OfferItemDefinition(kind=ITEM_RAMEN, label="拉麵", accent_color="#f08a3c", icon_relative_path="items/ramen.png"),
    OfferItemDefinition(kind=ITEM_HONEY, label="蜂蜜", accent_color="#f2be42", icon_relative_path="items/honey.png"),
    OfferItemDefinition(kind=ITEM_TEA, label="茶", accent_color="#90b66f", icon_relative_path="items/tea.png"),
    OfferItemDefinition(kind=ITEM_BOTTLE, label="奶瓶", accent_color="#8ed4ff", icon_relative_path="items/milk.png"),
    OfferItemDefinition(kind=ITEM_LOLLIPOP, label="棒棒糖", accent_color="#ff8fcf", icon_relative_path="items/Lollipop.png"),
)


DIRECT_OFFER_ACCEPT_CONTEXT_BY_ITEM = {
    ITEM_RAMEN: "offer_accept_ramen",
    ITEM_HONEY: "offer_accept_honey",
    ITEM_TEA: "offer_accept_tea",
    ITEM_BOTTLE: "offer_accept_milk",
    ITEM_LOLLIPOP: "offer_accept_lollipop",
}


DEFAULT_ITEM_TAKE_HOTSPOTS = {
    ITEM_RAMEN: {
        "Symboli Rudolf": OfferTakeHotspot(26.0, 109.0, 10.0),
        "Tokai Teio": OfferTakeHotspot(60.0, 211.0, 10.0),
    },
    ITEM_HONEY: {
        "Sirius Symboli": OfferTakeHotspot(100.0, 300.0, 10.0),
        "Tokai Teio": OfferTakeHotspot(60.0, 211.0, 10.0),
        "Tsurumaru Tsuyoshi": OfferTakeHotspot(21.0, 176.0, 10.0),
    },
    ITEM_TEA: {
        "Symboli Rudolf": OfferTakeHotspot(26.0, 109.0, 10.0),
        "Air Groove": OfferTakeHotspot(18.0, 247.0, 10.0),
    },
    ITEM_BOTTLE: {
        "Symboli Rudolf": OfferTakeHotspot(26.0, 109.0, 10.0),
        "Sirius Symboli": OfferTakeHotspot(100.0, 300.0, 10.0),
        "Tokai Teio": OfferTakeHotspot(60.0, 211.0, 10.0),
        "Tsurumaru Tsuyoshi": OfferTakeHotspot(21.0, 176.0, 10.0),
        "Air Groove": OfferTakeHotspot(18.0, 247.0, 10.0),
    },
    ITEM_LOLLIPOP: {
        "Symboli Rudolf": OfferTakeHotspot(26.0, 109.0, 10.0),
        "Tokai Teio": OfferTakeHotspot(60.0, 211.0, 10.0),
    },
}


DIRECT_OFFER_PREVIEW_CANDIDATES_BY_NAME = {
    "Symboli Rudolf": ("idle", "get"),
    "Sirius Symboli": ("idle", "stand_hand"),
    "Tokai Teio": ("idle", "side_face_hand"),
    "Tsurumaru Tsuyoshi": ("idle", "get"),
    "Air Groove": ("idle", "get"),
}


DIRECT_OFFER_ACCEPT_CANDIDATES = {
    ITEM_RAMEN: {
        "Symboli Rudolf": (("idle", "side_sit_ramen"),),
        "Tokai Teio": (("idle", "side_sit_ramen"),),
    },
    ITEM_HONEY: {
        "Sirius Symboli": (("idle", "drink"),),
        "Tokai Teio": (("move", "walk_drink"),),
        "Tsurumaru Tsuyoshi": (("idle", "drink"),),
    },
    ITEM_TEA: {
        "Symboli Rudolf": (("idle", "side_drink"),),
        "Air Groove": (("idle", "drink"),),
    },
    ITEM_BOTTLE: {
        "Symboli Rudolf": (("idle", "get"),),
        "Sirius Symboli": (("idle", "stand_hand"),),
        "Tokai Teio": (("idle", "side_face_hand"),),
        "Tsurumaru Tsuyoshi": (("idle", "drink"),),
        "Air Groove": (("idle", "get"),),
    },
    ITEM_LOLLIPOP: {
        "Symboli Rudolf": (("idle", "sit_eat_lollipop"),),
        "Tokai Teio": (("idle", "side_eat_candy"),),
    },
}


DIRECT_OFFER_PREFERRED_MOODS = {
    ITEM_RAMEN: ("happy", "smile", "confidence", "glance", "think"),
    ITEM_HONEY: ("happy", "smile", "confidence", "cool", "think"),
    ITEM_TEA: ("smile", "relief", "happy", "think", "cool"),
    ITEM_BOTTLE: ("happy", "smile", "relief", "glance", "think"),
    ITEM_LOLLIPOP: ("happy", "smile", "glance", "confidence", "think"),
}


HONEY_GUARDIAN_MOVE_CANDIDATES = {
    "Symboli Rudolf": (("move", "run_stretch"), ("move", "run")),
    "Sirius Symboli": (("move", "run"), ("move", "jog")),
}


HONEY_GUARDIAN_TAKE_CANDIDATES = {
    "Symboli Rudolf": (("idle", "get"), ("idle", "stand_open"), ("idle", "stand")),
    "Sirius Symboli": (("idle", "stand_hand"), ("idle", "stand")),
}


DENIED_OFFER_REACTION_CANDIDATES = {
    "Tsurumaru Tsuyoshi": (
        ("idle", "side"),
        ("idle", "sit_no"),
        ("idle", "squat"),
        ("idle", "stand"),
        ("idle", "lie"),
    ),
}


DENIED_OFFER_PREFERRED_MOODS = ("hard-cry", "cry", "sad", "scared", "angry")
DENIED_OFFER_FORBIDDEN_MOODS = ("sleep", "exhausted", "relief", "calm", "happy", "smile")


GROUND_PICKUP_PET_NAMES = {
    ITEM_RAMEN: ("Symboli Rudolf", "Tokai Teio"),
    ITEM_HONEY: ("Sirius Symboli", "Tokai Teio", "Tsurumaru Tsuyoshi"),
    ITEM_TEA: ("Symboli Rudolf", "Air Groove"),
    ITEM_BOTTLE: ("Symboli Rudolf", "Sirius Symboli", "Tokai Teio", "Tsurumaru Tsuyoshi", "Air Groove"),
    ITEM_LOLLIPOP: ("Symboli Rudolf", "Tokai Teio"),
}


BOTTLE_FEED_HOLDER_IDLE_CANDIDATES_BY_NAME = {
    "Symboli Rudolf": (("idle", "get"),),
    "Sirius Symboli": (("idle", "stand_hand"),),
    "Tokai Teio": (("idle", "side_face_hand"),),
    "Air Groove": (("idle", "get"),),
}


BOTTLE_FEED_HOLDER_WATCH_CANDIDATES_BY_NAME = {
    "Symboli Rudolf": (("idle", "observe"), ("idle", "sit")),
    "Sirius Symboli": (("idle", "stand_hand"), ("idle", "stand")),
    "Tokai Teio": (("idle", "sit"), ("idle", "sit")),
    "Air Groove": (("idle", "side"), ("idle", "sit")),
}


BOTTLE_FEED_CHILD_APPROACH_CANDIDATES_BY_NAME = {
    "Tsurumaru Tsuyoshi": (("move", "climb"),),
}


BOTTLE_FEED_CHILD_DRINK_CANDIDATES_BY_NAME = {
    "Tsurumaru Tsuyoshi": (("idle", "drink"),),
}


BOTTLE_FEED_HOLDER_IDLE_PREFERRED_MOODS = ("happy", "smile", "glance", "think")
BOTTLE_FEED_HOLDER_WATCH_PREFERRED_MOODS = ("smile", "happy", "sad", "glance")
BOTTLE_FEED_CHILD_APPROACH_PREFERRED_MOODS = ("happy", "smile", "think")
BOTTLE_FEED_CHILD_DRINK_PREFERRED_MOODS = ("happy", "smile", "glance")


OFFER_HOVER_REACTION_TEMPLATE_ITEMS = {
    ITEM_RAMEN: ITEM_BOTTLE,
    ITEM_TEA: ITEM_BOTTLE,
    ITEM_LOLLIPOP: ITEM_BOTTLE,
}


# 每位角色保留 2 條 hover timeout 路線：
# 1. 三段反應，且會刻意迴避滑鼠
# 2. 兩段反應，不額外躲滑鼠
# stage tuple 格式：("purpose", "action_type", "mood_tag", duration_seconds)
# cooldown / afterglow 由 runtime 以「總演出長度 + buffer」動態推算。
OFFER_HOVER_TIMEOUT_REACTION_STAGES = {
    ITEM_HONEY: {
        "Symboli Rudolf": (
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side_stretch", "angry", 0.75),
                ("move", "walk", "sad", 0.95),
            ),
            (
                ("idle", "get", "hurry", 0.55),
                ("idle", "sit_small", "think", 0.90),
            ),
        ),
        "Sirius Symboli": (
            (
                ("idle", "stand_hand", "sad", 0.55),
                ("idle", "side", "angry", 0.75),
                ("move", "walk", "angry", 0.95),
            ),
            (
                ("idle", "stand_hand", "glance", 0.55),
                ("idle", "side", "scold", 0.90),
            ),
        ),
        "Tokai Teio": (
            (
                ("idle", "side_face_hand", "angry", 0.55),
                ("idle", "side_stretch", "angry", 0.75),
                ("move", "jog", "angry", 0.95),
            ),
            (
                ("idle", "side_face_hand", "sad", 0.55),
                ("idle", "lie", "cry", 0.90),
            ),
        ),
        "Tsurumaru Tsuyoshi": (
            (
                ("idle", "get", "angry", 0.55),
                ("idle", "side_shake", "angry", 0.75),
                ("move", "climb", "angry", 0.95),
            ),
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side_stretch", "cry", 0.90),
            ),
        ),
        "Air Groove": (
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side", "sad", 0.75),
                ("move", "walk", "awkward", 0.95),
            ),
            (
                ("idle", "get", "angry", 0.55),
                ("idle", "side", "scold", 0.90),
            ),
        ),
    },
    ITEM_BOTTLE: {
        "Symboli Rudolf": (
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side_stretch", "angry", 0.75),
                ("move", "walk", "sad", 0.95),
            ),
            (
                ("idle", "get", "hurry", 0.55),
                ("idle", "sit_small", "think", 0.90),
            ),
        ),
        "Sirius Symboli": (
            (
                ("idle", "stand_hand", "sad", 0.55),
                ("idle", "side", "angry", 0.75),
                ("move", "walk", "angry", 0.95),
            ),
            (
                ("idle", "stand_hand", "glance", 0.55),
                ("idle", "side", "scold", 0.90),
            ),
        ),
        "Tokai Teio": (
            (
                ("idle", "side_face_hand", "angry", 0.55),
                ("idle", "side_stretch", "angry", 0.75),
                ("move", "jog", "angry", 0.95),
            ),
            (
                ("idle", "side_face_hand", "sad", 0.55),
                ("idle", "lie", "cry", 0.90),
            ),
        ),
        "Tsurumaru Tsuyoshi": (
            (
                ("idle", "get", "angry", 0.55),
                ("idle", "side_shake", "angry", 0.75),
                ("move", "climb", "angry", 0.95),
            ),
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side_stretch", "cry", 0.90),
            ),
        ),
        "Air Groove": (
            (
                ("idle", "get", "sad", 0.55),
                ("idle", "side", "sad", 0.75),
                ("move", "walk", "awkward", 0.95),
            ),
            (
                ("idle", "get", "angry", 0.55),
                ("idle", "side", "scold", 0.90),
            ),
        ),
    },
}


OFFER_HOVER_TIMEOUT_REACTION_AVOID_CURSOR = {
    ITEM_HONEY: {
        "Symboli Rudolf": (True, False),
        "Sirius Symboli": (True, False),
        "Tokai Teio": (True, False),
        "Tsurumaru Tsuyoshi": (True, False),
        "Air Groove": (True, False),
    },
    ITEM_BOTTLE: {
        "Symboli Rudolf": (True, False),
        "Sirius Symboli": (True, False),
        "Tokai Teio": (True, False),
        "Tsurumaru Tsuyoshi": (True, False),
        "Air Groove": (True, False),
    },
}


def get_offer_item_definitions():
    return list(OFFER_ITEM_DEFINITIONS)


def get_offer_item_definition(item_kind):
    for item_definition in OFFER_ITEM_DEFINITIONS:
        if item_definition.kind == item_kind:
            return item_definition
    return None


def get_take_hotspot(item_kind, pet_name):
    return DEFAULT_ITEM_TAKE_HOTSPOTS.get(item_kind, {}).get(pet_name)


def can_pet_interact_with_offer_item(item_kind, pet_name):
    return get_take_hotspot(item_kind, pet_name) is not None


def get_direct_offer_preview_context(item_kind=None, pet_name=None):
    return CONTEXT_OFFER_PREVIEW


def get_direct_offer_accept_context(item_kind, pet_name=None):
    return DIRECT_OFFER_ACCEPT_CONTEXT_BY_ITEM.get(item_kind, "")


def get_denied_offer_context(pet_name=None):
    return CONTEXT_OFFER_DENIED


def get_honey_guardian_move_context(pet_name=None):
    return CONTEXT_HONEY_GUARD_MOVE


def get_honey_guardian_take_context(pet_name=None):
    return CONTEXT_HONEY_GUARD_TAKE


def get_bottle_feed_holder_idle_context(pet_name=None):
    return CONTEXT_BOTTLE_FEED_HOLD


def get_bottle_feed_holder_watch_context(pet_name=None):
    return CONTEXT_BOTTLE_FEED_WATCH


def get_bottle_feed_child_approach_context(pet_name=None):
    return CONTEXT_BOTTLE_FEED_CHILD_APPROACH


def get_bottle_feed_child_drink_context(pet_name=None):
    return CONTEXT_BOTTLE_FEED_CHILD_DRINK


def get_offer_hover_timeout_stage_context(variant_label, stage_index):
    variant = str(variant_label or "")
    route = ""
    if variant.endswith("variant_1"):
        route = "route_a"
    elif variant.endswith("variant_2"):
        route = "route_b"
    if not route:
        return ""
    step_number = int(stage_index or 0) + 1
    return f"offer_timeout_{route}_step{step_number}"


def get_direct_offer_candidates(item_kind, pet_name):
    accept_candidates = list(DIRECT_OFFER_ACCEPT_CANDIDATES.get(item_kind, {}).get(pet_name, ()))
    if not accept_candidates:
        return []
    preview_candidate = DIRECT_OFFER_PREVIEW_CANDIDATES_BY_NAME.get(pet_name)
    if preview_candidate and preview_candidate not in accept_candidates:
        accept_candidates.append(preview_candidate)
    return accept_candidates


def get_direct_offer_preview_candidates(item_kind, pet_name):
    preview_candidate = DIRECT_OFFER_PREVIEW_CANDIDATES_BY_NAME.get(pet_name)
    if preview_candidate:
        return [preview_candidate]
    candidates = get_direct_offer_accept_candidates(item_kind, pet_name)
    if candidates:
        return [candidates[0]]
    return []


def get_direct_offer_accept_candidates(item_kind, pet_name):
    return list(DIRECT_OFFER_ACCEPT_CANDIDATES.get(item_kind, {}).get(pet_name, ()))


def get_direct_offer_accept_purpose_order(item_kind, pet_name, roll=None):
    if roll is not None and float(roll) >= DIRECT_OFFER_MOBILE_ACCEPT_CHANCE:
        return list(DIRECT_OFFER_STATIONARY_ACCEPT_PURPOSE_ORDER)
    return list(DIRECT_OFFER_ACCEPT_PURPOSE_ORDER)


def get_direct_offer_mobile_move_speed_scale(item_kind, pet_name):
    return float(DIRECT_OFFER_MOBILE_MOVE_SPEED_SCALE)


def get_direct_offer_mobile_move_target_offset(item_kind, pet_name):
    return float(DIRECT_OFFER_MOBILE_MOVE_TARGET_OFFSET)


def get_direct_offer_preferred_moods(item_kind):
    return list(DIRECT_OFFER_PREFERRED_MOODS.get(item_kind, ()))


def get_honey_guardian_move_candidates(pet_name):
    return list(HONEY_GUARDIAN_MOVE_CANDIDATES.get(pet_name, ()))


def get_honey_guardian_take_candidates(pet_name):
    return list(HONEY_GUARDIAN_TAKE_CANDIDATES.get(pet_name, ()))


def get_denied_offer_reaction_candidates(pet_name):
    return list(DENIED_OFFER_REACTION_CANDIDATES.get(pet_name, ()))


def get_denied_offer_preferred_moods():
    return list(DENIED_OFFER_PREFERRED_MOODS)


def get_denied_offer_forbidden_moods():
    return list(DENIED_OFFER_FORBIDDEN_MOODS)


def get_ground_pickup_pet_names(item_kind):
    return list(GROUND_PICKUP_PET_NAMES.get(item_kind, ()))


def get_bottle_feed_holder_idle_candidates(pet_name):
    return list(BOTTLE_FEED_HOLDER_IDLE_CANDIDATES_BY_NAME.get(pet_name, ()))


def get_bottle_feed_holder_watch_candidates(pet_name):
    return list(BOTTLE_FEED_HOLDER_WATCH_CANDIDATES_BY_NAME.get(pet_name, ()))


def get_bottle_feed_child_approach_candidates(pet_name):
    return list(BOTTLE_FEED_CHILD_APPROACH_CANDIDATES_BY_NAME.get(pet_name, ()))


def get_bottle_feed_child_drink_candidates(pet_name):
    return list(BOTTLE_FEED_CHILD_DRINK_CANDIDATES_BY_NAME.get(pet_name, ()))


def get_bottle_feed_holder_idle_preferred_moods():
    return list(BOTTLE_FEED_HOLDER_IDLE_PREFERRED_MOODS)


def get_bottle_feed_holder_watch_preferred_moods():
    return list(BOTTLE_FEED_HOLDER_WATCH_PREFERRED_MOODS)


def get_bottle_feed_child_approach_preferred_moods():
    return list(BOTTLE_FEED_CHILD_APPROACH_PREFERRED_MOODS)


def get_bottle_feed_child_drink_preferred_moods():
    return list(BOTTLE_FEED_CHILD_DRINK_PREFERRED_MOODS)


def get_offer_hover_timeout_seconds(item_kind):
    return float(OFFER_HOVER_TIMEOUT_SECONDS)


def get_offer_hover_reaction_cooldown_buffer_seconds(item_kind):
    return float(OFFER_HOVER_REACTION_COOLDOWN_BUFFER_SECONDS)


def get_offer_hover_negative_afterglow_buffer_seconds(item_kind):
    return float(OFFER_HOVER_NEGATIVE_AFTERGLOW_BUFFER_SECONDS)


def get_offer_hover_reaction_variants(item_kind, pet_name):
    raw_variants = OFFER_HOVER_TIMEOUT_REACTION_STAGES.get(item_kind, {}).get(pet_name, ())
    avoid_flags = OFFER_HOVER_TIMEOUT_REACTION_AVOID_CURSOR.get(item_kind, {}).get(pet_name, ())
    if not raw_variants:
        template_item_kind = OFFER_HOVER_REACTION_TEMPLATE_ITEMS.get(item_kind, "")
        if template_item_kind:
            raw_variants = OFFER_HOVER_TIMEOUT_REACTION_STAGES.get(template_item_kind, {}).get(pet_name, ())
            avoid_flags = OFFER_HOVER_TIMEOUT_REACTION_AVOID_CURSOR.get(template_item_kind, {}).get(pet_name, ())
    variants = []
    for index, raw_variant in enumerate(raw_variants):
        if not raw_variant:
            continue
        stages = []
        for stage_index, raw_stage in enumerate(raw_variant):
            if not raw_stage or len(raw_stage) != 4:
                continue
            purpose, action_type, mood_tag, duration_seconds = raw_stage
            if stage_index == 0:
                duration_seconds = OFFER_HOVER_REACTION_STAGE_ONE_SECONDS
            elif stage_index == 1:
                duration_seconds = OFFER_HOVER_REACTION_STAGE_TWO_SECONDS
            stages.append(
                OfferHoverReactionStage(
                    purpose=str(purpose),
                    action_type=str(action_type),
                    mood_tag=str(mood_tag),
                    duration_seconds=max(0.1, float(duration_seconds)),
                )
            )
        if not stages:
            continue
        variants.append(
            OfferHoverReactionVariant(
                label=f"{pet_name}:{item_kind}:variant_{index + 1}",
                avoid_cursor=bool(avoid_flags[index]) if index < len(avoid_flags) else False,
                stages=tuple(stages),
            )
        )
    return variants


def choose_honey_guardian(candidates):
    visible = [candidate for candidate in candidates if candidate.is_visible]
    if not visible:
        return ""
    visible.sort(key=lambda candidate: (candidate.distance, candidate.name))
    return visible[0].name


def resolve_offer_preview_match(
    *,
    widget_left,
    widget_top,
    widget_width,
    widget_height,
    frame_width=None,
    frame_height=None,
    offer_global_x,
    offer_global_y,
):
    widget_width = float(widget_width)
    widget_height = float(widget_height)
    frame_width = float(widget_width if frame_width is None else frame_width)
    frame_height = float(widget_height if frame_height is None else frame_height)
    draw_x = max(0.0, (widget_width - frame_width) / 2.0)
    draw_y = max(0.0, widget_height - frame_height)
    frame_left = float(widget_left) + draw_x
    frame_top = float(widget_top) + draw_y
    expanded_left = frame_left - OFFER_PREVIEW_FRAME_PADDING
    expanded_top = frame_top - OFFER_PREVIEW_FRAME_PADDING
    expanded_right = frame_left + frame_width + OFFER_PREVIEW_FRAME_PADDING
    expanded_bottom = frame_top + frame_height + OFFER_PREVIEW_FRAME_PADDING
    frame_center_x = frame_left + (frame_width / 2.0)
    frame_center_y = frame_top + (frame_height / 2.0)
    distance = math.hypot(float(offer_global_x) - frame_center_x, float(offer_global_y) - frame_center_y)
    return OfferPreviewMatch(
        matched=(
            expanded_left <= float(offer_global_x) <= expanded_right and
            expanded_top <= float(offer_global_y) <= expanded_bottom
        ),
        distance=distance,
    )


def resolve_offer_hotspot_match(
    *,
    item_kind,
    pet_name,
    widget_left,
    widget_top,
    widget_width,
    widget_height,
    frame_width=None,
    frame_height=None,
    render_scale=None,
    direction,
    original_face_left,
    offer_global_x,
    offer_global_y,
):
    hotspot = get_take_hotspot(item_kind, pet_name)
    if hotspot is None:
        return OfferHotspotMatch(
            matched=False,
            distance=math.inf,
            hotspot_global_x=0.0,
            hotspot_global_y=0.0,
            hotspot_radius=0.0,
        )

    widget_width = float(widget_width)
    widget_height = float(widget_height)
    frame_width = float(widget_width if frame_width is None else frame_width)
    frame_height = float(widget_height if frame_height is None else frame_height)
    if render_scale is None:
        scale_x = frame_width / BASE_CANVAS_SIZE
        scale_y = frame_height / BASE_CANVAS_SIZE
        render_scale = (scale_x + scale_y) / 2.0
    else:
        render_scale = float(render_scale)

    draw_x = max(0.0, (widget_width - frame_width) / 2.0)
    draw_y = max(0.0, widget_height - frame_height)
    local_x = float(hotspot.x) * render_scale
    local_y = float(hotspot.y) * render_scale
    hotspot_radius = float(hotspot.radius)
    should_flip = (int(direction) == 1) if bool(original_face_left) else (int(direction) == -1)
    if should_flip:
        local_x = frame_width - local_x

    frame_left = float(widget_left) + draw_x
    frame_top = float(widget_top) + draw_y
    hotspot_global_x = float(widget_left) + draw_x + local_x
    hotspot_global_y = float(widget_top) + draw_y + local_y
    distance = math.hypot(float(offer_global_x) - hotspot_global_x, float(offer_global_y) - hotspot_global_y)
    return OfferHotspotMatch(
        matched=(distance <= hotspot_radius),
        distance=distance,
        hotspot_global_x=hotspot_global_x,
        hotspot_global_y=hotspot_global_y,
        hotspot_radius=hotspot_radius,
    )
