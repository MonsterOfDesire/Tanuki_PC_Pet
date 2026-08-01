from dataclasses import dataclass
from typing import Any


CARE_PLAN_COMPANION = "companion"
CARE_PLAN_INTERACTION = "interaction"

SOCIAL_ENTRY_NONE = "none"
SOCIAL_ENTRY_FOLLOWING = "following"
SOCIAL_ENTRY_MIMICKING = "mimicking"
CHEERFUL_MOODS = {"happy", "smile", "confidence", "cool"}
DISTRESS_ANIMATION_MOODS = {"sad", "cry", "hard-cry"}
NON_MIMIC_TARGET_PURPOSES = {"drag"}

CARE_INTERACTION_WEIGHTS = {
    "Symboli Rudolf": 0.65,
    "Sirius Symboli": 0.50,
    "Air Groove": 0.40,
}
CARE_INTERACTION_STATIONARY_CHANCE = 0.50
CARE_INTERACTION_RECOVERY_MOODS = ("happy", "smile", "relief", "calm", "think", "sad", "cry", "hard-cry")


@dataclass(frozen=True)
class CareTargetCandidate:
    pet: Any
    is_self: bool
    is_adult: bool
    is_visible: bool
    care_partner: Any
    is_recovering: bool
    is_distressed: bool
    distance: float
    preferred_adult_name: str | None = None
    care_blocked: bool = False
    activity_busy: bool = False


@dataclass(frozen=True)
class CareAdultCandidate:
    name: str
    is_adult: bool
    is_visible: bool
    is_busy: bool
    distance: float
    same_screen: bool = True


def parse_interaction_action(action_key):
    if action_key.startswith("move_"):
        motion = "move"
        rest = action_key[len("move_"):]
    elif action_key.startswith("idle_"):
        motion = "idle"
        rest = action_key[len("idle_"):]
    else:
        return None
    if "_" not in rest:
        return None
    action_desc, child_token = rest.rsplit("_", 1)
    return motion, action_desc, child_token


def build_distress_mood_candidates(current_mood_tag):
    moods = []
    for mood in [current_mood_tag, "sad", "cry", "hard-cry", "happy"]:
        if mood and mood not in moods:
            moods.append(mood)
    return moods


def build_care_interaction_mood_candidates(current_mood_tag):
    moods = []
    for mood in (current_mood_tag, *CARE_INTERACTION_RECOVERY_MOODS):
        if mood and mood not in moods:
            moods.append(mood)
    return moods


def resolve_care_interaction_motion_order(preferred_motion, roll):
    stationary_first = float(roll or 0.0) < CARE_INTERACTION_STATIONARY_CHANCE
    if stationary_first:
        return ["idle", "move"]
    if preferred_motion == "idle":
        return ["move", "idle"]
    return ["move", "idle"]


def is_distressed_state(
    *,
    mood_state,
    current_mood_tag,
    current_purpose="",
    dragging=False,
    mood_score=None,
    distress_ready_at=0.0,
    now=None,
):
    if dragging or current_purpose == "drag":
        return False
    if (
        mood_score is not None and
        float(mood_score) < 20.0 and
        current_mood_tag in DISTRESS_ANIMATION_MOODS
    ):
        return True
    if mood_state != "depressed":
        return False
    if not current_mood_tag:
        return True
    return current_mood_tag not in CHEERFUL_MOODS


def can_mimic_socially(*, mood_state):
    return mood_state == "normal"


def should_preserve_candidate_animation(current_purpose, current_action_tag, current_mood_tag, candidates, *, frames_available, preferred_moods=None, forbidden=None):
    if not any(current_purpose == purpose and current_action_tag == action for purpose, action in candidates):
        return False
    if not frames_available:
        return False
    if preferred_moods and current_mood_tag in preferred_moods:
        return True
    if forbidden and current_mood_tag in forbidden:
        return False
    return True


def decide_care_plan(name, has_interaction, roll):
    if not has_interaction:
        return CARE_PLAN_COMPANION
    interaction_chance = CARE_INTERACTION_WEIGHTS.get(name, 0.50)
    if roll < interaction_chance:
        return CARE_PLAN_INTERACTION
    return CARE_PLAN_COMPANION


def choose_care_target(adult, adult_name, candidates):
    radius = None if adult_name == "Sirius Symboli" else 1000
    eligible = []
    for candidate in candidates:
        if candidate.is_self or candidate.is_adult or not candidate.is_visible:
            continue
        if candidate.preferred_adult_name not in (None, adult_name):
            continue
        if candidate.care_partner not in (None, adult):
            continue
        if (
            candidate.is_recovering
            or candidate.care_blocked
            or candidate.activity_busy
            or not candidate.is_distressed
        ):
            continue
        if radius is not None and candidate.distance > radius:
            continue
        eligible.append(candidate)
    if not eligible:
        return None
    eligible.sort(key=lambda item: item.distance)
    return eligible[0].pet


def choose_preferred_care_adult_name(candidates):
    eligible = []
    for candidate in candidates:
        if not candidate.is_adult or not candidate.is_visible or candidate.is_busy:
            continue
        if candidate.name != "Sirius Symboli":
            if not candidate.same_screen:
                continue
            if candidate.distance > 1000:
                continue
        eligible.append(candidate)
    if not eligible:
        return None
    eligible.sort(key=lambda item: item.distance)
    return eligible[0].name


def decide_social_entry(distance, social_distance, rudolf_purpose, is_behind, can_strictly_mimic, can_mimic=True):
    if distance >= social_distance:
        return SOCIAL_ENTRY_NONE
    if rudolf_purpose in NON_MIMIC_TARGET_PURPOSES:
        return SOCIAL_ENTRY_NONE
    if rudolf_purpose == "move" and is_behind:
        return SOCIAL_ENTRY_FOLLOWING
    if can_mimic and can_strictly_mimic:
        return SOCIAL_ENTRY_MIMICKING
    return SOCIAL_ENTRY_NONE
