from __future__ import annotations

from dataclasses import dataclass, field

from .offer_interaction_rules import ITEM_HONEY, ITEM_RAMEN, ITEM_TEA


AnimationCandidate = tuple[str, str]
AnimationCandidates = tuple[AnimationCandidate, ...]

SHARED_FOOD_ROLE_HOLDER = "holder"
SHARED_FOOD_ROLE_PARTNER = "partner"

SHARED_FOOD_OUTCOME_SHARE_BOTH = "share_both"
SHARED_FOOD_OUTCOME_HOLDER_KEEPS = "holder_keeps"
SHARED_FOOD_OUTCOME_HOLDER_GIVES = "holder_gives"

SHARED_FOOD_CONTEXT_BY_CAPABILITY = {
    "hold": "shared_food_hold",
    "approach": "shared_food_approach",
    "consume": "shared_food_consume",
    "request": "shared_food_request",
    "watch": "shared_food_watch",
    "react": "shared_food_react",
}


@dataclass(frozen=True)
class SharedFoodOutcomeDefinition:
    outcome_key: str
    consume_order: tuple[str, ...]


SHARED_FOOD_OUTCOME_DEFINITIONS = (
    SharedFoodOutcomeDefinition(
        outcome_key=SHARED_FOOD_OUTCOME_SHARE_BOTH,
        consume_order=(SHARED_FOOD_ROLE_PARTNER, SHARED_FOOD_ROLE_HOLDER),
    ),
    SharedFoodOutcomeDefinition(
        outcome_key=SHARED_FOOD_OUTCOME_HOLDER_KEEPS,
        consume_order=(SHARED_FOOD_ROLE_HOLDER,),
    ),
    SharedFoodOutcomeDefinition(
        outcome_key=SHARED_FOOD_OUTCOME_HOLDER_GIVES,
        consume_order=(SHARED_FOOD_ROLE_PARTNER,),
    ),
)


SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY = {
    outcome.outcome_key: outcome
    for outcome in SHARED_FOOD_OUTCOME_DEFINITIONS
}


SHARED_FOOD_OUTCOME_KEYS = tuple(SHARED_FOOD_OUTCOME_DEFINITIONS_BY_KEY)


@dataclass(frozen=True)
class SharedFoodCharacterCapabilities:
    hold_candidates: AnimationCandidates = ()
    approach_candidates: AnimationCandidates = ()
    consume_candidates: AnimationCandidates = ()
    request_candidates: AnimationCandidates = ()
    watch_candidates: AnimationCandidates = ()
    react_candidates: AnimationCandidates = ()


@dataclass(frozen=True)
class SharedFoodProfile:
    profile_key: str
    item_kind: str
    allowed_holders: tuple[str, ...]
    partner_rules: dict[str, tuple[str, ...]]
    scene_hint: str
    join_distance: float
    approach_distance: float
    shared_duration_seconds: float
    partner_wait_seconds: float
    item_visibility_phase: str
    consume_mode: str
    fallback_mode: str
    outcome_weights_by_key: dict[str, float]
    capabilities_by_name: dict[str, SharedFoodCharacterCapabilities]
    holder_preferred_moods: tuple[str, ...] = ()
    partner_preferred_moods: tuple[str, ...] = ()
    success_event_type: str = ""
    success_summary_by_holder: dict[str, str] = field(default_factory=dict)

    def partner_names_for_holder(self, holder_name: str) -> tuple[str, ...]:
        return self.partner_rules.get(holder_name, ())

    def capabilities_for(self, character_name: str) -> SharedFoodCharacterCapabilities | None:
        return self.capabilities_by_name.get(character_name)


SHARED_FOOD_PROFILES = (
    SharedFoodProfile(
        profile_key="shared_meal_ramen",
        item_kind=ITEM_RAMEN,
        allowed_holders=("Symboli Rudolf", "Tokai Teio"),
        partner_rules={
            "Symboli Rudolf": ("Tokai Teio",),
            "Tokai Teio": ("Symboli Rudolf",),
        },
        scene_hint="shared_meal_ramen",
        join_distance=500.0,
        approach_distance=120.0,
        shared_duration_seconds=5.0,
        partner_wait_seconds=2.5,
        item_visibility_phase="until_first_consume",
        consume_mode="weighted_outcome",
        fallback_mode="wait_short_then_solo",
        outcome_weights_by_key={
            SHARED_FOOD_OUTCOME_SHARE_BOTH: 0.60,
            SHARED_FOOD_OUTCOME_HOLDER_KEEPS: 0.20,
            SHARED_FOOD_OUTCOME_HOLDER_GIVES: 0.20,
        },
        capabilities_by_name={
            "Symboli Rudolf": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "get"),),
                approach_candidates=(("move", "walk"),),
                consume_candidates=(("idle", "side_sit_ramen"),),
                request_candidates=(("idle", "observe"), ("idle", "sit_small")),
                watch_candidates=(("idle", "get"), ("idle", "side_face_hand")),
                react_candidates=(("idle", "rest"), ("idle", "sit")),
            ),
            "Tokai Teio": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "side_face_hand"),),
                approach_candidates=(("move", "jog"), ("move", "walk")),
                consume_candidates=(("idle", "side_sit_ramen"),),
                request_candidates=(("idle", "side_rub"), ("idle", "sit"), ("idle", "sway")),
                watch_candidates=(("idle", "side_face_hand"),),
                react_candidates=(("idle", "side_face"), ("idle", "side"), ("idle", "sit")),
            ),
        },
        holder_preferred_moods=("happy", "smile", "confidence", "glance", "think"),
        partner_preferred_moods=("happy", "smile", "confidence", "glance", "think"),
        success_event_type="shared_ramen",
        success_summary_by_holder={
            "Symboli Rudolf": "魯道夫端著拉麵，帝寶也忍不住湊了過去。",
            "Tokai Teio": "帝寶拿著拉麵晃來晃去，魯道夫最後還是陪她一起吃。",
        },
    ),
    SharedFoodProfile(
        profile_key="tea_chat",
        item_kind=ITEM_TEA,
        allowed_holders=("Symboli Rudolf", "Air Groove"),
        partner_rules={
            "Symboli Rudolf": ("Air Groove",),
            "Air Groove": ("Symboli Rudolf",),
        },
        scene_hint="tea_chat",
        join_distance=500.0,
        approach_distance=135.0,
        shared_duration_seconds=5.0,
        partner_wait_seconds=2.0,
        item_visibility_phase="until_first_consume",
        consume_mode="weighted_outcome",
        fallback_mode="solo_consume",
        outcome_weights_by_key={
            SHARED_FOOD_OUTCOME_SHARE_BOTH: 0.45,
            SHARED_FOOD_OUTCOME_HOLDER_KEEPS: 0.35,
            SHARED_FOOD_OUTCOME_HOLDER_GIVES: 0.20,
        },
        capabilities_by_name={
            "Symboli Rudolf": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "get"),),
                approach_candidates=(("move", "walk"),),
                consume_candidates=(("idle", "side_drink"),),
                request_candidates=(("idle", "observe"), ("idle", "sit_small")),
                watch_candidates=(("idle", "get"), ("idle", "side_face_hand")),
                react_candidates=(("idle", "rest"), ("idle", "sit")),
            ),
            "Air Groove": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "get"),),
                approach_candidates=(("move", "walk_hand"), ("move", "walk")),
                consume_candidates=(("idle", "drink"),),
                request_candidates=(("idle", "get"),),
                watch_candidates=(("idle", "get"),),
                react_candidates=(("idle", "side"), ("idle", "sit")),
            ),
        },
        holder_preferred_moods=("relief", "smile", "happy", "think", "calm"),
        partner_preferred_moods=("relief", "smile", "happy", "think", "calm", "awkward"),
        success_event_type="shared_tea_chat",
        success_summary_by_holder={
            "Symboli Rudolf": "魯道夫和氣槽安靜地喝了會兒茶。",
            "Air Groove": "氣槽拿著茶，魯道夫就在旁邊陪她坐了一會兒。",
        },
    ),
    SharedFoodProfile(
        profile_key="shared_honey",
        item_kind=ITEM_HONEY,
        allowed_holders=("Sirius Symboli", "Tokai Teio"),
        partner_rules={
            "Sirius Symboli": ("Tokai Teio",),
            "Tokai Teio": ("Sirius Symboli",),
        },
        scene_hint="shared_honey",
        join_distance=500.0,
        approach_distance=120.0,
        shared_duration_seconds=5.0,
        partner_wait_seconds=2.0,
        item_visibility_phase="until_first_consume",
        consume_mode="weighted_outcome",
        fallback_mode="solo_consume",
        outcome_weights_by_key={
            SHARED_FOOD_OUTCOME_SHARE_BOTH: 0.50,
            SHARED_FOOD_OUTCOME_HOLDER_KEEPS: 0.25,
            SHARED_FOOD_OUTCOME_HOLDER_GIVES: 0.25,
        },
        capabilities_by_name={
            "Sirius Symboli": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "stand_hand"),),
                approach_candidates=(("move", "walk"), ("move", "jog")),
                consume_candidates=(("idle", "drink"),),
                request_candidates=(("idle", "mix_dance_me"),),
                watch_candidates=(("idle", "stand_hand"),),
                react_candidates=(
                    ("idle", "mix_dacne_shiii"),
                    ("idle", "sit_talk"),
                    ("idle", "stand"),
                ),
            ),
            "Tokai Teio": SharedFoodCharacterCapabilities(
                hold_candidates=(("idle", "side_face_hand"),),
                approach_candidates=(("move", "jog"), ("move", "walk")),
                consume_candidates=(("idle", "side_sit_drink"), ("idle", "dance_uma_drink")),
                request_candidates=(("idle", "side_rub"), ("idle", "sit"), ("idle", "sway")),
                watch_candidates=(("idle", "side_face_hand"),),
                react_candidates=(("idle", "side_face"), ("idle", "side"), ("idle", "sit")),
            ),
        },
        holder_preferred_moods=("happy", "smile", "confidence", "cool", "think"),
        partner_preferred_moods=("happy", "smile", "glance", "think"),
        success_event_type="shared_honey",
        success_summary_by_holder={
            "Sirius Symboli": "天狼星拿著蜂蜜時，帝寶也期待地靠了過來。",
            "Tokai Teio": "帝寶拿著蜂蜜，天狼星也走近陪她待了一會兒。",
        },
    ),
)


def _validate_shared_food_profiles() -> None:
    known_outcomes = set(SHARED_FOOD_OUTCOME_KEYS)
    seen_profile_keys: set[str] = set()
    seen_item_kinds: set[str] = set()
    for profile in SHARED_FOOD_PROFILES:
        if profile.profile_key in seen_profile_keys:
            raise ValueError(f"duplicate shared-food profile key: {profile.profile_key}")
        if profile.item_kind in seen_item_kinds:
            raise ValueError(f"duplicate shared-food item profile: {profile.item_kind}")
        seen_profile_keys.add(profile.profile_key)
        seen_item_kinds.add(profile.item_kind)
        if set(profile.outcome_weights_by_key) != known_outcomes:
            raise ValueError(f"{profile.profile_key}: outcome weights must define all shared-food outcomes")
        if any(weight <= 0.0 for weight in profile.outcome_weights_by_key.values()):
            raise ValueError(f"{profile.profile_key}: outcome weights must be positive")
        if abs(sum(profile.outcome_weights_by_key.values()) - 1.0) > 1e-9:
            raise ValueError(f"{profile.profile_key}: outcome weights must total 1.0")
        if profile.join_distance <= profile.approach_distance:
            raise ValueError(
                f"{profile.profile_key}: join distance must exceed approach distance"
            )
        if set(profile.partner_rules) != set(profile.allowed_holders):
            raise ValueError(f"{profile.profile_key}: every allowed holder must define partner rules")
        for holder_name in profile.allowed_holders:
            capabilities = profile.capabilities_for(holder_name)
            if capabilities is None:
                raise ValueError(f"{profile.profile_key}: missing holder capabilities for {holder_name}")
            for capability_name in (
                "hold",
                "approach",
                "consume",
                "request",
                "watch",
                "react",
            ):
                if not getattr(capabilities, f"{capability_name}_candidates"):
                    raise ValueError(
                        f"{profile.profile_key}: {holder_name} has no {capability_name} candidates"
                    )
            partner_names = profile.partner_names_for_holder(holder_name)
            if not partner_names:
                raise ValueError(f"{profile.profile_key}: {holder_name} has no shared-food partner")
            for partner_name in partner_names:
                if partner_name not in profile.capabilities_by_name:
                    raise ValueError(f"{profile.profile_key}: missing partner capabilities for {partner_name}")
                if holder_name not in profile.partner_names_for_holder(partner_name):
                    raise ValueError(
                        f"{profile.profile_key}: pairing must be bidirectional for "
                        f"{holder_name} and {partner_name}"
                    )


_validate_shared_food_profiles()


SHARED_FOOD_PROFILES_BY_KEY = {
    profile.profile_key: profile
    for profile in SHARED_FOOD_PROFILES
}


SHARED_FOOD_PROFILE_KEY_BY_ITEM_KIND = {
    profile.item_kind: profile.profile_key
    for profile in SHARED_FOOD_PROFILES
}


def get_shared_food_profile(profile_key: str) -> SharedFoodProfile | None:
    return SHARED_FOOD_PROFILES_BY_KEY.get(profile_key)


def get_shared_food_profile_for_item(item_kind: str) -> SharedFoodProfile | None:
    profile_key = SHARED_FOOD_PROFILE_KEY_BY_ITEM_KIND.get(item_kind)
    if not profile_key:
        return None
    return SHARED_FOOD_PROFILES_BY_KEY.get(profile_key)


def get_shared_food_profile_for_holder(
    item_kind: str,
    holder_name: str,
) -> SharedFoodProfile | None:
    profile = get_shared_food_profile_for_item(item_kind)
    if profile is None or holder_name not in profile.allowed_holders:
        return None
    return profile


def get_shared_food_partner_names(item_kind: str, holder_name: str) -> tuple[str, ...]:
    profile = get_shared_food_profile_for_holder(item_kind, holder_name)
    if profile is None:
        return ()
    return profile.partner_names_for_holder(holder_name)
