from dataclasses import dataclass, replace

from .pet_runtime_state import RelationshipEntry

RELATIONAL_SOCIAL_DISTANCE = 220.0
RELATION_FOCUS_START_DISTANCE = 220.0
RELATION_FOCUS_KEEP_DISTANCE = 260.0


@dataclass(frozen=True)
class RelationshipObservation:
    name: str
    distance: float
    same_anchor: bool
    is_visible: bool = True
    social_active: bool = False
    care_active: bool = False


@dataclass(frozen=True)
class RelationshipFocus:
    target_name: str = ""
    familiarity: float = 0.0
    trust: float = 0.0
    attachment: float = 0.0
    tension: float = 0.0


@dataclass(frozen=True)
class ExpressionSnapshot:
    animation_context: str
    relation_overlay: str
    focus_target_name: str
    posture_bias: str
    spacing_bias: str
    look_at_target: bool


def clamp_relationship_value(value):
    return max(0.0, min(100.0, float(value)))


def advance_relationship_entry(entry, *, distance, same_anchor, social_active, care_active, now):
    familiarity = clamp_relationship_value(entry.familiarity)
    trust = clamp_relationship_value(entry.trust)
    attachment = clamp_relationship_value(entry.attachment)
    tension = clamp_relationship_value(entry.tension)

    if float(distance) <= 260.0:
        familiarity += 0.01
        if same_anchor:
            familiarity += 0.01
    if social_active:
        familiarity += 0.02
        attachment += 0.03
        tension -= 0.01
    if care_active:
        trust += 0.04
        attachment += 0.02
        tension -= 0.02
    if same_anchor and not social_active and not care_active:
        tension -= 0.005

    return replace(
        entry,
        familiarity=clamp_relationship_value(familiarity),
        trust=clamp_relationship_value(trust),
        attachment=clamp_relationship_value(attachment),
        tension=clamp_relationship_value(tension),
        last_seen_at=float(now),
        last_interaction_at=(float(now) if social_active or care_active else entry.last_interaction_at),
    )


def choose_relationship_focus(
    *,
    entries,
    social_target_name="",
    care_target_name="",
    observe_target_name="",
    observe_target_distance=0.0,
    observe_target_visible=False,
    nearest_visible_pet_name="",
    nearest_visible_pet_distance=0.0,
    blocked_target_name="",
):
    target_name = care_target_name or social_target_name
    if (
        not target_name and
        observe_target_name and
        observe_target_visible and
        observe_target_name != blocked_target_name and
        0.0 < float(observe_target_distance) <= RELATION_FOCUS_KEEP_DISTANCE
    ):
        target_name = observe_target_name
    if (
        not target_name and
        nearest_visible_pet_name and
        nearest_visible_pet_name != blocked_target_name and
        0.0 < float(nearest_visible_pet_distance) <= RELATION_FOCUS_START_DISTANCE
    ):
        target_name = nearest_visible_pet_name
    if not target_name:
        return RelationshipFocus()
    entry = entries.get(target_name, RelationshipEntry())
    return RelationshipFocus(
        target_name=target_name,
        familiarity=entry.familiarity,
        trust=entry.trust,
        attachment=entry.attachment,
        tension=entry.tension,
    )


def derive_relational_situation_tag(current_situation_tag, *, focus, focus_distance):
    if current_situation_tag != "stable":
        return current_situation_tag
    if not focus.target_name:
        return current_situation_tag
    if float(focus_distance) <= 0.0 or float(focus_distance) > RELATIONAL_SOCIAL_DISTANCE:
        return current_situation_tag
    if focus.attachment >= 15.0 or focus.familiarity >= 6.0:
        return "social"
    return current_situation_tag


def derive_expression_state(*, situation_tag, social_mode, care_mode, care_lock_active, focus):
    if care_mode != "none" or care_lock_active:
        return ExpressionSnapshot(
            animation_context="care",
            relation_overlay="heart",
            focus_target_name=focus.target_name,
            posture_bias="protective",
            spacing_bias="close",
            look_at_target=bool(focus.target_name),
        )
    if social_mode == "following":
        return ExpressionSnapshot(
            animation_context="social_follow",
            relation_overlay="star",
            focus_target_name=focus.target_name,
            posture_bias="engaged",
            spacing_bias="close",
            look_at_target=bool(focus.target_name),
        )
    if social_mode == "mimicking":
        return ExpressionSnapshot(
            animation_context="social_mimic",
            relation_overlay="star",
            focus_target_name=focus.target_name,
            posture_bias="mirroring",
            spacing_bias="close",
            look_at_target=bool(focus.target_name),
        )
    if situation_tag == "hazard":
        return ExpressionSnapshot(
            animation_context="hazard",
            relation_overlay="none",
            focus_target_name="",
            posture_bias="alert",
            spacing_bias="neutral",
            look_at_target=False,
        )
    if focus.target_name and focus.attachment >= 15.0 and focus.familiarity >= 6.0:
        return ExpressionSnapshot(
            animation_context="relation_close",
            relation_overlay="soft_star",
            focus_target_name=focus.target_name,
            posture_bias="warm",
            spacing_bias="comfortable",
            look_at_target=True,
        )
    if focus.target_name and focus.familiarity >= 6.0:
        return ExpressionSnapshot(
            animation_context="relation_watch",
            relation_overlay="none",
            focus_target_name=focus.target_name,
            posture_bias="curious",
            spacing_bias="neutral",
            look_at_target=True,
        )
    return ExpressionSnapshot(
        animation_context="ambient",
        relation_overlay="none",
        focus_target_name="",
        posture_bias="neutral",
        spacing_bias="neutral",
        look_at_target=False,
    )
