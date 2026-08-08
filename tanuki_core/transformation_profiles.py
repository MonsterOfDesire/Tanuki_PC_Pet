from __future__ import annotations

from dataclasses import dataclass

from .transformation_state import FORM_BASE, FORM_TRANSFORMED


TOKAI_TEIO_NAME = "Tokai Teio"
SYMBOLI_RUDOLF_NAME = "Symboli Rudolf"
TSURUMARU_TSUYOSHI_NAME = "Tsurumaru Tsuyoshi"

CAPABILITY_SLEEP = "sleep"
CAPABILITY_WORK = "work"
CAPABILITY_SHARED_FOOD = "shared_food"
CAPABILITY_BOTTLE_FEED_HOLDER = "bottle_feed_holder"
CAPABILITY_HONEY_GUARDIAN = "honey_guardian"
CAPABILITY_CARE_GIVER = "care_giver"
CAPABILITY_COMBINED_CARE = "combined_care"
CAPABILITY_SOCIAL_FOLLOW = "social_follow"
CAPABILITY_SOCIAL_MIMIC = "social_mimic"
CAPABILITY_AUTONOMOUS_FLIGHT = "autonomous_flight"
CAPABILITY_RACE = "race"


@dataclass(frozen=True)
class FormCapabilities:
    sleep: bool = True
    work: bool = True
    shared_food: bool = True
    bottle_feed_holder: bool = True
    honey_guardian: bool = True
    care_giver: bool = False
    combined_care: bool = True
    social_follow: bool = True
    social_mimic: bool = True
    autonomous_flight: bool = True
    race: bool = True
    direct_offer_items: frozenset[str] | None = None
    care_target_names: frozenset[str] | None = None
    minimum_mood_score: float = 0.0


@dataclass(frozen=True)
class TransformationProfile:
    character_name: str
    transformed_subdirectory: str
    transformed_capabilities: FormCapabilities
    auto_base_seconds_min: float = 480.0
    auto_base_seconds_max: float = 900.0
    auto_duration_seconds_min: float = 90.0
    auto_duration_seconds_max: float = 180.0


TRANSFORMATION_PROFILES = {
    TOKAI_TEIO_NAME: TransformationProfile(
        character_name=TOKAI_TEIO_NAME,
        transformed_subdirectory="transformed",
        transformed_capabilities=FormCapabilities(
            sleep=False,
            work=False,
            shared_food=False,
            bottle_feed_holder=True,
            honey_guardian=True,
            care_giver=True,
            combined_care=False,
            social_follow=False,
            social_mimic=False,
            autonomous_flight=True,
            race=False,
            direct_offer_items=frozenset({"bottle"}),
            care_target_names=frozenset({TSURUMARU_TSUYOSHI_NAME}),
            minimum_mood_score=50.0,
        ),
    ),
    SYMBOLI_RUDOLF_NAME: TransformationProfile(
        character_name=SYMBOLI_RUDOLF_NAME,
        transformed_subdirectory="transformed",
        transformed_capabilities=FormCapabilities(
            sleep=False,
            work=False,
            shared_food=False,
            bottle_feed_holder=False,
            honey_guardian=True,
            care_giver=True,
            combined_care=False,
            social_follow=False,
            social_mimic=False,
            autonomous_flight=False,
            race=True,
            direct_offer_items=frozenset(),
            minimum_mood_score=50.0,
        ),
    ),
}


BASE_CAPABILITIES = FormCapabilities()


def get_transformation_profile(character_name: str) -> TransformationProfile | None:
    return TRANSFORMATION_PROFILES.get(str(character_name or ""))


def get_pet_form_key(pet) -> str:
    state = getattr(pet, "transformation_state", None)
    return str(getattr(state, "current_form", FORM_BASE) or FORM_BASE)


def pet_is_transforming(pet) -> bool:
    state = getattr(pet, "transformation_state", None)
    return bool(state is not None and getattr(state, "active", False))


def pet_is_transformed(pet) -> bool:
    return get_pet_form_key(pet) == FORM_TRANSFORMED


def get_pet_form_capabilities(pet) -> FormCapabilities:
    if not pet_is_transformed(pet):
        return BASE_CAPABILITIES
    profile = get_transformation_profile(getattr(pet, "name", ""))
    if profile is None:
        return BASE_CAPABILITIES
    return profile.transformed_capabilities


def pet_form_allows_capability(pet, capability_name: str) -> bool:
    if pet_is_transforming(pet):
        return False
    if not pet_is_transformed(pet):
        if str(capability_name or "") == CAPABILITY_CARE_GIVER:
            return bool(getattr(pet, "is_adult", False))
        return bool(
            str(capability_name or "")
            and hasattr(BASE_CAPABILITIES, str(capability_name or ""))
            and getattr(BASE_CAPABILITIES, str(capability_name or ""))
        )
    capabilities = get_pet_form_capabilities(pet)
    capability_name = str(capability_name or "")
    if not capability_name or not hasattr(capabilities, capability_name):
        return False
    return bool(getattr(capabilities, capability_name))


def pet_form_allows_offer_item(pet, item_kind: str) -> bool:
    if pet_is_transforming(pet):
        return False
    allowed_items = get_pet_form_capabilities(pet).direct_offer_items
    if allowed_items is None:
        return True
    return str(item_kind or "") in allowed_items


def pet_form_allows_care_target(pet, target_name: str) -> bool:
    if not pet_form_allows_capability(pet, CAPABILITY_CARE_GIVER):
        return False
    target_names = get_pet_form_capabilities(pet).care_target_names
    if target_names is None:
        return True
    return str(target_name or "") in target_names


def apply_pet_form_mood_floor(pet, value: float) -> float:
    minimum = float(get_pet_form_capabilities(pet).minimum_mood_score)
    return max(minimum, min(100.0, float(value)))
