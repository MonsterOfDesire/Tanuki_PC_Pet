from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class NearbyPetObservation:
    name: str
    distance: float
    is_adult: bool
    is_visible: bool = True
    is_distressed: bool = False


@dataclass(frozen=True)
class PerceptionSnapshot:
    anchor: str
    support_surface: str
    nearest_visible_pet_name: str = ""
    nearest_visible_pet_distance: float = 0.0
    nearest_distressed_child_name: str = ""
    nearest_distressed_child_distance: float = 0.0
    visible_adult_count: int = 0
    visible_child_count: int = 0
    window_perch_available: bool = False
    window_flight_target_available: bool = False
    situation_tag: str = "stable"


def derive_situation_tag(
    *,
    dragging,
    is_angry_locked,
    care_mode,
    social_mode,
    is_recovering,
    care_lock_active,
    vertical_velocity,
    anchor,
    is_adult,
    has_nearest_visible_pet,
    has_nearest_distressed_child,
):
    if dragging or is_angry_locked:
        return "locked"
    if care_mode != "none" or care_lock_active or is_recovering:
        return "care"
    if social_mode != "none":
        return "social"
    if float(vertical_velocity) != 0.0 or anchor == "air":
        return "hazard"
    if is_adult and has_nearest_distressed_child:
        return "care"
    return "stable"


def summarize_perception(
    observations: Sequence[NearbyPetObservation],
    *,
    anchor,
    support_surface,
    dragging,
    is_angry_locked,
    care_mode,
    social_mode,
    is_recovering,
    care_lock_active,
    vertical_velocity,
    is_adult,
    window_perch_available,
    window_flight_target_available,
):
    visible = [item for item in observations if item.is_visible]
    adults = sum(1 for item in visible if item.is_adult)
    children = sum(1 for item in visible if not item.is_adult)
    nearest_visible = min(visible, key=lambda item: item.distance, default=None)
    distressed_children = [
        item for item in visible
        if not item.is_adult and item.is_distressed
    ]
    nearest_distressed = min(distressed_children, key=lambda item: item.distance, default=None)
    situation_tag = derive_situation_tag(
        dragging=dragging,
        is_angry_locked=is_angry_locked,
        care_mode=care_mode,
        social_mode=social_mode,
        is_recovering=is_recovering,
        care_lock_active=care_lock_active,
        vertical_velocity=vertical_velocity,
        anchor=anchor,
        is_adult=is_adult,
        has_nearest_visible_pet=nearest_visible is not None,
        has_nearest_distressed_child=nearest_distressed is not None,
    )
    return PerceptionSnapshot(
        anchor=anchor,
        support_surface=support_surface,
        nearest_visible_pet_name=nearest_visible.name if nearest_visible else "",
        nearest_visible_pet_distance=nearest_visible.distance if nearest_visible else 0.0,
        nearest_distressed_child_name=nearest_distressed.name if nearest_distressed else "",
        nearest_distressed_child_distance=nearest_distressed.distance if nearest_distressed else 0.0,
        visible_adult_count=adults,
        visible_child_count=children,
        window_perch_available=bool(window_perch_available),
        window_flight_target_available=bool(window_flight_target_available),
        situation_tag=situation_tag,
    )
