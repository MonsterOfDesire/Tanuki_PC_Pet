from __future__ import annotations

import random
import time

from .achievement_memory_capture import capture_pet_scene_image
from .bounded_key_set import BoundedKeySet
from .runtime_debug_log import log_suppressed_exception


RANDOM_MEMORY_MIN_SECONDS = 8 * 60
RANDOM_MEMORY_MAX_SECONDS = 15 * 60
EVENT_PHASES = {
    ("race", "running"): "race",
    ("chorus", "performing"): "chorus",
    ("sleep", "sleeping"): "sleep",
    ("sleep", "waking"): "sleep",
    ("rudolf_work", "working"): "work",
}


class MemoryCaptureRuntime:
    """Detects one representative frame per live scene without owning gameplay."""

    def __init__(
        self,
        *,
        achievement_service,
        album_service,
        album_settings_provider,
        album_changed=None,
        image_provider=None,
        now_provider=None,
        rng=None,
    ):
        self.achievement_service = achievement_service
        self.album_service = album_service
        self.album_settings_provider = album_settings_provider
        self.album_changed = album_changed or (lambda: None)
        self.image_provider = image_provider or capture_pet_scene_image
        self.now_provider = now_provider or time.monotonic
        self.rng = rng or random.Random()
        self._seen_scene_keys = BoundedKeySet(max_entries=4096)
        self._previous_forms = None
        self._next_random_at = self._sample_next_random(self.now_provider())
        self._capture_suspended_for_speed = False

    def reset_random_schedule(self):
        self._next_random_at = self._sample_next_random(self.now_provider())
        return self._next_random_at

    def observe_time_scale(self, time_scale, pets=()):
        """Synchronize capture eligibility with the simulation speed."""
        now = float(self.now_provider())
        if not _is_one_x(time_scale):
            visible_pets = self._visible_pets(pets)
            for _kind, scene_key, _participants, _metadata in self._event_scenes(
                visible_pets
            ):
                self._seen_scene_keys.add(scene_key)
            if not self._capture_suspended_for_speed:
                discard = getattr(
                    self.achievement_service,
                    "discard_performing_candidates",
                    None,
                )
                if callable(discard):
                    discard()
            self._capture_suspended_for_speed = True
            return False
        if self._capture_suspended_for_speed:
            self._capture_suspended_for_speed = False
            self._next_random_at = self._sample_next_random(now)
        return True

    def tick(self, pets):
        pets = self._visible_pets(pets)
        settings = dict(self.album_settings_provider() or {})
        if not self.observe_time_scale(
            settings.get("time_scale", 1.0),
            pets,
        ):
            return ()
        if not pets:
            return ()
        mode = str(settings.get("mode", "off") or "off")
        capacity = int(settings.get("capacity", 20) or 20)
        achievement_enabled = bool(settings.get("achievement_enabled", False))
        if mode == "off" and not achievement_enabled:
            self._previous_forms = {
                str(getattr(pet, "name", "") or ""): str(
                    getattr(
                        getattr(pet, "transformation_state", None),
                        "current_form",
                        "base",
                    )
                    or "base"
                )
                for pet in pets
            }
            return ()
        saved = []

        for kind, scene_key, participants, scene_metadata in self._event_scenes(
            pets
        ):
            if scene_key in self._seen_scene_keys:
                continue
            album_wants_event = (
                mode in {"events", "random"}
                and bool(scene_metadata.get("album_eligible", True))
            )
            if album_wants_event:
                album_wants_event = not self.album_service.snapshot(
                    mode=mode,
                    capacity=capacity,
                ).full
            if not achievement_enabled and not album_wants_event:
                continue
            self._seen_scene_keys.add(scene_key)
            image = self._capture(participants)
            if image is None:
                continue
            metadata = {
                "kind": kind,
                "scene_key": scene_key,
                "participants": [
                    str(getattr(pet, "name", "") or "")
                    for pet in participants
                ],
                "captured_at": float(self.now_provider()),
            }
            metadata.update(scene_metadata)
            if achievement_enabled:
                self.achievement_service.stage_performing_candidate(
                    kind,
                    image,
                    metadata=metadata,
                )
            if album_wants_event:
                path = self.album_service.capture(
                    image,
                    mode=mode,
                    capacity=capacity,
                    kind=kind,
                    participants=metadata["participants"],
                )
                if path is not None:
                    saved.append(path)

        now = float(self.now_provider())
        if mode == "random" and now >= self._next_random_at:
            if not self.album_service.snapshot(
                mode=mode,
                capacity=capacity,
            ).full:
                group = self._random_group(pets)
                image = self._capture(group)
                if image is not None:
                    path = self.album_service.capture(
                        image,
                        mode=mode,
                        capacity=capacity,
                        kind="daily",
                        participants=[
                            str(getattr(pet, "name", "") or "") for pet in group
                        ],
                    )
                    if path is not None:
                        saved.append(path)
            self._next_random_at = self._sample_next_random(now)
        elif mode != "random":
            self._next_random_at = self._sample_next_random(now)

        if saved:
            self.album_changed()
        return tuple(saved)

    def _event_scenes(self, pets):
        grouped = {}
        for pet in pets:
            state = getattr(pet, "activity_state", None)
            key = (
                str(getattr(state, "activity_kind", "") or ""),
                str(getattr(state, "phase", "") or ""),
            )
            kind = EVENT_PHASES.get(key)
            activity_id = str(getattr(state, "activity_id", "") or "")
            if kind and activity_id:
                grouped.setdefault((kind, activity_id, key[1]), []).append(pet)
        for (kind, activity_id, phase), participants in grouped.items():
            yield (
                kind,
                f"activity:{kind}:{activity_id}:{phase}",
                tuple(participants),
                {
                    "activity_id": activity_id,
                    "phase": phase,
                    "album_eligible": not (
                        kind == "sleep" and phase == "waking"
                    ),
                },
            )

        for pet in pets:
            name = str(getattr(pet, "name", "") or "")
            offer_kind = str(getattr(pet, "offer_scene_kind", "none") or "none")
            purpose = str(getattr(pet, "current_purpose", "") or "")
            if offer_kind != "none" and purpose not in {"", "move"}:
                participants = [pet]
                for other in pets:
                    if other is pet:
                        continue
                    if str(getattr(other, "offer_scene_kind", "none") or "none") == offer_kind:
                        participants.append(other)
                kind = "honey_guard" if offer_kind == "honey_guard" else "food"
                scene_key = "offer:{}:{}:{:.3f}".format(
                    offer_kind,
                    min(id(item) for item in participants),
                    max(
                        float(getattr(item, "held_item_started_at", 0.0) or 0.0)
                        for item in participants
                    ),
                )
                yield (
                    kind,
                    scene_key,
                    tuple(participants),
                    {"phase": purpose},
                )
            care_mode = str(getattr(pet, "care_mode", "none") or "none")
            if care_mode in {"interaction", "care_interaction", "sit"}:
                target = getattr(pet, "care_target", None)
                participants = (pet, target) if target is not None else (pet,)
                yield (
                    "care",
                    "care:{}:{}:{}:{:.3f}".format(
                        name,
                        id(target),
                        care_mode,
                        float(getattr(pet, "care_end_time", 0.0) or 0.0),
                    ),
                    participants,
                    {"phase": care_mode},
                )
            social_mode = str(getattr(pet, "social_mode", "none") or "none")
            if social_mode in {"interaction", "moving_interaction", "post_observe"}:
                target = getattr(pet, "social_target", None)
                participants = (pet, target) if target is not None else (pet,)
                yield (
                    "social",
                    "social:{}:{}:{}:{:.3f}".format(
                        name,
                        id(target),
                        social_mode,
                        float(getattr(pet, "social_started_at", 0.0) or 0.0),
                    ),
                    participants,
                    {"phase": social_mode},
                )

        forms = {
            str(getattr(pet, "name", "") or ""): str(
                getattr(getattr(pet, "transformation_state", None), "current_form", "base")
                or "base"
            )
            for pet in pets
        }
        if self._previous_forms is None:
            self._previous_forms = forms
        else:
            for pet in pets:
                name = str(getattr(pet, "name", "") or "")
                state = getattr(pet, "transformation_state", None)
                form = forms[name]
                if (
                    self._previous_forms.get(name) != form
                    and str(getattr(state, "phase", "idle") or "idle") == "idle"
                    and float(getattr(state, "whiteness", 0.0) or 0.0) <= 0.0
                ):
                    yield (
                        "transformation",
                        f"transformation:{name}:{form}:{self.now_provider():.6f}",
                        (pet,),
                        {
                            "phase": "completed",
                            "character_name": name,
                        },
                    )
            self._previous_forms = forms

    def _capture(self, pets):
        try:
            return self.image_provider(tuple(pet for pet in pets if pet is not None))
        except Exception as error:
            log_suppressed_exception("memory_capture.image_provider", error)
            return None

    @staticmethod
    def _visible_pets(pets):
        return tuple(
            pet for pet in (pets or ())
            if pet is not None and bool(getattr(pet, "user_visible", True))
        )

    def _random_group(self, pets):
        seed = self.rng.choice(tuple(pets))
        center = float(seed.x()) + float(seed.width()) / 2.0
        nearby = tuple(
            pet for pet in pets
            if abs(float(pet.x()) + float(pet.width()) / 2.0 - center) <= 600.0
        )
        return nearby or (seed,)

    def _sample_next_random(self, now):
        return float(now) + self.rng.uniform(
            RANDOM_MEMORY_MIN_SECONDS,
            RANDOM_MEMORY_MAX_SECONDS,
        )


def _is_one_x(time_scale):
    try:
        return abs(float(time_scale) - 1.0) <= 1e-6
    except (TypeError, ValueError):
        return False
