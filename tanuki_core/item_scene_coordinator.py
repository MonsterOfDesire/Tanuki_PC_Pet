from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from uuid import uuid4


AnimationSignature = tuple[str, str, str]
NormalizedOutcomeWeights = tuple[tuple[str, float], ...]


@dataclass
class SharedFoodSceneState:
    holder_name: str = ""
    partner_name: str = ""
    outcome_key: str = ""
    available_outcomes: tuple[str, ...] = ()
    normalized_outcome_weights: NormalizedOutcomeWeights = ()
    outcome_roll: float = 0.0
    consume_order: tuple[str, ...] = ()
    consumer_names: tuple[str, ...] = ()
    holder_animation: AnimationSignature = ()
    partner_animation: AnimationSignature = ()
    item_hidden: bool = False
    effects_applied: bool = False

    @property
    def outcome_resolved(self) -> bool:
        return bool(self.outcome_key)

    @property
    def first_consumer_name(self) -> str:
        return self.consumer_names[0] if self.consumer_names else ""

    @property
    def second_consumer_name(self) -> str:
        return self.consumer_names[1] if len(self.consumer_names) > 1 else ""

    def store_outcome(
        self,
        *,
        outcome_key: str,
        available_outcomes: tuple[str, ...],
        normalized_outcome_weights: NormalizedOutcomeWeights,
        outcome_roll: float,
        consume_order: tuple[str, ...],
        consumer_names: tuple[str, ...],
    ) -> bool:
        if self.outcome_resolved or not outcome_key:
            return False
        self.outcome_key = str(outcome_key)
        self.available_outcomes = tuple(available_outcomes or ())
        self.normalized_outcome_weights = tuple(normalized_outcome_weights or ())
        self.outcome_roll = float(outcome_roll)
        self.consume_order = tuple(consume_order or ())
        self.consumer_names = tuple(consumer_names or ())
        return True


@dataclass
class ActiveItemScene:
    scene_id: str = ""
    started_at: float = 0.0
    item_kind: str = ""
    scene_kind: str = "none"
    actor_name: str = ""
    target_name: str = ""
    stage: str = "none"
    stage_initialized: bool = False
    stage_started_at: float = 0.0
    stage_ends_at: float = 0.0
    scene_ends_at: float = 0.0
    event_recorded: bool = False
    source: str = "offer_tray"
    profile_key: str = ""
    direct_accept_purpose_order: tuple[str, ...] = ()
    hover_reaction_variant_label: str = ""
    hover_reaction_avoid_cursor: bool = False
    hover_reaction_stage_index: int = 0
    hover_reaction_stages: tuple[object, ...] = ()
    shared_food_state: SharedFoodSceneState = field(default_factory=SharedFoodSceneState)


@dataclass(frozen=True)
class ItemSceneStartResult:
    started: bool
    reason: str = ""
    scene_id: str = ""


@dataclass(frozen=True)
class ItemSceneUpdateResult:
    handled: bool
    scene_finished: bool = False
    emitted_events: tuple[dict, ...] = ()
    released_items: tuple[str, ...] = ()


class ItemSceneCoordinator:
    SUPPORTED_SCENE_KINDS = frozenset(
        {
            "direct_accept",
            "hover_preview",
            "hover_timeout_reaction",
            "deny_only",
            "honey_guard",
            "bottle_feed",
            "shared_food",
        }
    )

    def __init__(self, *, scene_id_factory: Callable[[], str] | None = None):
        self._scene_id_factory = scene_id_factory or (lambda: uuid4().hex)

    def build_scene(
        self,
        *,
        scene_id: str = "",
        scene_kind: str,
        item_kind: str,
        actor_name: str,
        target_name: str = "",
        source: str = "offer_tray",
        profile_key: str = "",
        direct_accept_purpose_order: tuple[str, ...] = (),
        stage: str = "none",
        stage_initialized: bool = False,
        stage_started_at: float = 0.0,
        stage_ends_at: float = 0.0,
        scene_ends_at: float = 0.0,
        event_recorded: bool = False,
        hover_reaction_variant_label: str = "",
        hover_reaction_avoid_cursor: bool = False,
        hover_reaction_stage_index: int = 0,
        hover_reaction_stages: tuple[object, ...] = (),
        shared_food_state: SharedFoodSceneState | None = None,
    ) -> ActiveItemScene:
        if shared_food_state is None:
            shared_food_state = SharedFoodSceneState(
                holder_name=actor_name if scene_kind == "shared_food" else "",
                partner_name=target_name if scene_kind == "shared_food" else "",
            )
        return ActiveItemScene(
            scene_id=str(scene_id or ""),
            started_at=float(stage_started_at),
            item_kind=item_kind,
            scene_kind=scene_kind,
            actor_name=actor_name,
            target_name=target_name,
            stage=stage,
            stage_initialized=stage_initialized,
            stage_started_at=float(stage_started_at),
            stage_ends_at=float(stage_ends_at),
            scene_ends_at=float(scene_ends_at),
            event_recorded=bool(event_recorded),
            source=source,
            profile_key=profile_key,
            direct_accept_purpose_order=tuple(direct_accept_purpose_order or ()),
            hover_reaction_variant_label=hover_reaction_variant_label,
            hover_reaction_avoid_cursor=bool(hover_reaction_avoid_cursor),
            hover_reaction_stage_index=int(hover_reaction_stage_index),
            hover_reaction_stages=tuple(hover_reaction_stages or ()),
            shared_food_state=shared_food_state,
        )

    def lock_pet(self, pet, scene_kind: str, until: float) -> bool:
        if pet is None:
            return False
        normalized_scene_kind = str(scene_kind or "none")
        if normalized_scene_kind == "none":
            return False
        pet.offer_scene_kind = normalized_scene_kind
        pet.offer_locked_until = max(
            float(getattr(pet, "offer_locked_until", 0.0) or 0.0),
            float(until),
        )
        return True

    def unlock_pet(self, pet, *, expected_scene_kind: str | None = None) -> bool:
        if pet is None:
            return False
        current_scene_kind = str(getattr(pet, "offer_scene_kind", "none") or "none")
        if expected_scene_kind is not None and current_scene_kind != str(expected_scene_kind):
            return False
        pet.offer_scene_kind = "none"
        pet.offer_locked_until = 0.0
        return True

    def lock_scene_participants(self, runtime, pets, *, until: float | None = None) -> int:
        scene = getattr(runtime, "offer_scene", None)
        if scene is None:
            return 0
        lock_until = float(scene.scene_ends_at if until is None else until)
        locked_count = 0
        seen_pet_ids = set()
        for pet in pets or ():
            if pet is None or id(pet) in seen_pet_ids:
                continue
            seen_pet_ids.add(id(pet))
            if self.lock_pet(pet, scene.scene_kind, lock_until):
                locked_count += 1
        return locked_count

    def start_scene(self, runtime, *, participant_pets=(), **scene_kwargs) -> ItemSceneStartResult:
        scene_kind = str(scene_kwargs.get("scene_kind", "") or "")
        if scene_kind not in self.SUPPORTED_SCENE_KINDS:
            return ItemSceneStartResult(
                started=False,
                reason="unsupported_scene_kind",
            )
        scene_id = str(self._scene_id_factory() or "").strip()
        if not scene_id:
            return ItemSceneStartResult(
                started=False,
                reason="empty_scene_id",
            )
        scene = self.build_scene(scene_id=scene_id, **scene_kwargs)
        runtime.offer_scene = scene
        self.lock_scene_participants(runtime, participant_pets)
        return ItemSceneStartResult(
            started=True,
            scene_id=self.get_scene_id(scene),
        )

    def get_scene_id(self, scene: ActiveItemScene | None) -> str:
        if scene is None:
            return ""
        if str(scene.scene_id or "").strip():
            return str(scene.scene_id)
        actor = scene.actor_name or "none"
        target = scene.target_name or "none"
        item = scene.item_kind or "none"
        return f"{scene.scene_kind}:{item}:{actor}:{target}"

    def get_participants(self, scene: ActiveItemScene | None) -> tuple[str, ...]:
        if scene is None:
            return ()
        participants = []
        if scene.actor_name:
            participants.append(scene.actor_name)
        if scene.target_name and scene.target_name != scene.actor_name:
            participants.append(scene.target_name)
        return tuple(participants)

    def clear_scene(
        self,
        runtime,
        *,
        find_pet_by_name: Callable[[str, bool], object | None],
    ) -> bool:
        scene = getattr(runtime, "offer_scene", None)
        if scene is None:
            return False
        for pet_name in self.get_participants(scene):
            pet = find_pet_by_name(pet_name, False)
            if pet is not None:
                self.unlock_pet(pet, expected_scene_kind=scene.scene_kind)
        runtime.offer_scene = None
        return True

    def cancel_scene(
        self,
        runtime,
        *,
        reason: str = "manual",
        find_pet_by_name: Callable[[str, bool], object | None],
    ) -> bool:
        _ = reason
        return self.clear_scene(
            runtime,
            find_pet_by_name=find_pet_by_name,
        )

    def cancel_scenes_for_pet(
        self,
        runtime,
        *,
        pet_name: str,
        reason: str = "pet_hidden",
        find_pet_by_name: Callable[[str, bool], object | None],
    ) -> bool:
        _ = reason
        scene = getattr(runtime, "offer_scene", None)
        if scene is None:
            return False
        if pet_name not in self.get_participants(scene):
            return False
        return self.clear_scene(
            runtime,
            find_pet_by_name=find_pet_by_name,
        )

    def update(
        self,
        runtime,
        now: float,
        *,
        update_handlers: dict[str, Callable[[float], bool]],
        clear_scene_callback: Callable[[], None],
    ) -> ItemSceneUpdateResult:
        scene = getattr(runtime, "offer_scene", None)
        if scene is None:
            return ItemSceneUpdateResult(handled=False, scene_finished=False)
        handler = update_handlers.get(scene.scene_kind)
        if handler is None:
            clear_scene_callback()
            return ItemSceneUpdateResult(handled=True, scene_finished=True)
        handled = bool(handler(float(now)))
        scene_finished = getattr(runtime, "offer_scene", None) is None
        return ItemSceneUpdateResult(
            handled=handled,
            scene_finished=scene_finished,
        )
