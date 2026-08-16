from .activity_runtime_adapter import pet_has_active_activity
from .offer_interaction_rules import (
    ITEM_BOTTLE,
    ITEM_HONEY,
    get_bottle_feed_child_approach_candidates,
    get_bottle_feed_child_approach_context,
    get_bottle_feed_child_approach_preferred_moods,
    get_bottle_feed_child_drink_candidates,
    get_bottle_feed_child_drink_context,
    get_bottle_feed_child_drink_preferred_moods,
    get_bottle_feed_holder_idle_candidates,
    get_bottle_feed_holder_idle_context,
    get_bottle_feed_holder_idle_preferred_moods,
    get_bottle_feed_holder_watch_candidates,
    get_bottle_feed_holder_watch_context,
    get_bottle_feed_holder_watch_preferred_moods,
    get_denied_offer_context,
    get_denied_offer_forbidden_moods,
    get_denied_offer_preferred_moods,
    get_denied_offer_reaction_candidates,
    get_direct_offer_preferred_moods,
    get_direct_offer_preview_candidates,
    get_direct_offer_preview_context,
    get_honey_guardian_move_candidates,
    get_honey_guardian_move_context,
    get_honey_guardian_take_candidates,
    get_honey_guardian_take_context,
)
from .offer_scene_execution_port import adapt_offer_scene_executor
from .runtime import app_now
from .transformation_profiles import (
    CAPABILITY_BOTTLE_FEED_HOLDER,
    pet_form_allows_capability,
)


HONEY_GUARD_APPROACH_SPEED_SCALE = 1.6
HONEY_GUARD_APPROACH_MIN_SPEED_SCALE = 1.0
HONEY_GUARD_APPROACH_MIN_SPEED_FLOOR = 0.0
HONEY_GUARD_RESCUE_MIN_SPEED_FLOOR = 5.0
HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS = 5.0
HONEY_GUARD_TAKE_PREFERRED_MOODS = ("sad", "think")
HONEY_GUARD_TAKE_FORBIDDEN_MOODS = (
    "cool",
    "confidence",
    "serious",
    "angry",
    "scold",
    "happy",
    "smile",
    "glance",
    "relief",
)
BOTTLE_FEED_DRINK_SECONDS = 5.0
BOTTLE_FEED_APPROACH_MIN_SPEED = 2.0


def prepare_honey_guardian_activity(guardian_pet) -> bool:
    """Release a sleeping guardian before offer-scene ownership is acquired."""
    if guardian_pet is None:
        return False
    if not pet_has_active_activity(guardian_pet):
        return True
    activity_state = getattr(guardian_pet, "activity_state", None)
    if str(getattr(activity_state, "activity_kind", "none") or "none") != "sleep":
        return False
    interrupt_provider = getattr(
        guardian_pet,
        "activity_user_interrupt_provider",
        None,
    )
    if not callable(interrupt_provider):
        return False
    if not bool(interrupt_provider(guardian_pet, reason="honey_guard")):
        return False
    return not pet_has_active_activity(guardian_pet)


@adapt_offer_scene_executor
class BottleHoneySceneExecutor:
    """Executes bottle handoff and honey-guard scenes through a narrow port."""

    def start_bottle_feed_scene(
        self,
        port,
        holder_pet,
        source="offer_tray",
        now=None,
    ):
        if now is None:
            now = app_now()
        if not pet_form_allows_capability(
            holder_pet,
            CAPABILITY_BOTTLE_FEED_HOLDER,
        ):
            return False
        port.items.ensure_held_item(holder_pet, ITEM_BOTTLE, source=source)
        child_pet = port.pets.choose_bottle_feed_child(holder_pet, now=now)
        if child_pet is None:
            return port.items.apply_held_item_behavior(holder_pet, now)
        if (
            port.animation.is_window_transitioning(holder_pet) or
            port.animation.is_window_transitioning(child_pet) or
            port.animation.prepare_window_state(holder_pet) or
            port.animation.prepare_window_state(child_pet)
        ):
            return port.items.apply_held_item_behavior(holder_pet, now)
        port.animation.interrupt_window_motion(holder_pet)
        port.animation.interrupt_window_motion(child_pet)
        approach_end = now + 3600.0
        start_result = port.scene.start(
            participant_pets=(holder_pet, child_pet),
            item_kind=ITEM_BOTTLE,
            scene_kind="bottle_feed",
            actor_name=holder_pet.name,
            target_name=child_pet.name,
            stage="approach",
            stage_initialized=False,
            stage_ends_at=approach_end,
            scene_ends_at=approach_end,
            source=source,
        )
        if not start_result.started:
            return False
        port.items.apply_held_item_behavior(holder_pet, now)
        port.scene.refresh_locks(holder_pet, child_pet)
        return True

    def update_bottle_feed_scene(self, port, now):
        holder_pet = port.pets.find_by_name(port.scene.current.actor_name, visible_only=False)
        child_pet = port.pets.find_by_name(port.scene.current.target_name, visible_only=False)
        if holder_pet is None:
            port.scene.clear()
            return False
        if child_pet is None or not child_pet.isVisible():
            port.scene.clear()
            return port.items.apply_held_item_behavior(holder_pet, now)
        if (
            port.animation.is_window_transitioning(holder_pet) or
            port.animation.is_window_transitioning(child_pet) or
            port.animation.prepare_window_state(holder_pet) or
            port.animation.prepare_window_state(child_pet)
        ):
            port.scene.clear()
            return port.items.apply_held_item_behavior(holder_pet, now)

        port.scene.refresh_locks(holder_pet, child_pet)

        if port.scene.current.stage == "approach":
            holder_pet.state = "idle"
            holder_candidates = get_bottle_feed_holder_idle_candidates(holder_pet.name)
            holder_moods = get_bottle_feed_holder_idle_preferred_moods()
            holder_context = get_bottle_feed_holder_idle_context(holder_pet.name)
            if holder_moods:
                if not port.animation.apply_context(
                    holder_pet,
                    "idle",
                    holder_context,
                    holder_moods,
                    preserve=True,
                ) and not port.animation.apply_candidates(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                    preserve=True,
                ):
                    holder_pet.ensure_candidate_animation_with_preferences(holder_candidates, holder_moods)
            port.items.update_held_item_position(
                getattr(holder_pet, "held_item_widget", None),
                holder_pet,
                ITEM_BOTTLE,
                prefer_preview=True,
            )

            child_pet.state = "move"
            child_pet.direction = -1 if holder_pet.x() < child_pet.x() else 1
            holder_pet.direction = -child_pet.direction
            child_candidates = get_bottle_feed_child_approach_candidates(child_pet.name)
            child_moods = get_bottle_feed_child_approach_preferred_moods()
            child_context = get_bottle_feed_child_approach_context(child_pet.name)
            if child_moods:
                if not port.animation.apply_context(
                    child_pet,
                    "move",
                    child_context,
                    child_moods,
                    preserve=True,
                ) and not port.animation.apply_candidates(
                    child_pet,
                    child_candidates,
                    child_moods,
                    preserve=True,
                ):
                    child_pet.ensure_candidate_animation_with_preferences(child_candidates, child_moods)
            child_pet.move_toward_x(
                holder_pet.x(),
                speed_scale=1.0,
                min_speed=max(BOTTLE_FEED_APPROACH_MIN_SPEED, child_pet.get_base_speed()),
            )
            holder_pet.refresh_movement_state()
            child_pet.refresh_movement_state()
            if child_pet.distance_to(holder_pet) <= 140:
                port.scene.current.stage = "drink"
                port.scene.current.stage_initialized = False
                port.scene.current.scene_ends_at = float(now) + BOTTLE_FEED_DRINK_SECONDS
                port.scene.current.stage_ends_at = float(port.scene.current.scene_ends_at)
                return port.flow.update_bottle_feed_scene(now)
            return True

        if now >= float(port.scene.current.scene_ends_at):
            if not port.scene.current.event_recorded:
                port.events.apply_mood_reward(child_pet.name)
                port.events.record_offer_event(
                    ITEM_BOTTLE,
                    holder_pet.name,
                    child_pet.name,
                    "bottle_feed",
                    source=port.scene.current.source,
                )
                port.scene.current.event_recorded = True
            port.scene.clear()
            return True

        port.animation.reset_pet_motion(holder_pet)
        port.animation.reset_pet_motion(child_pet)
        holder_pet.direction = -1 if child_pet.x() < holder_pet.x() else 1
        child_pet.direction = -holder_pet.direction

        holder_candidates = get_bottle_feed_holder_watch_candidates(holder_pet.name)
        holder_moods = get_bottle_feed_holder_watch_preferred_moods()
        child_candidates = get_bottle_feed_child_drink_candidates(child_pet.name)
        child_moods = get_bottle_feed_child_drink_preferred_moods()
        holder_context = get_bottle_feed_holder_watch_context(holder_pet.name)
        child_context = get_bottle_feed_child_drink_context(child_pet.name)

        if not port.scene.current.stage_initialized:
            port.items.clear_held_item(holder_pet)
            if holder_moods and not port.animation.apply_context(
                holder_pet,
                "idle",
                holder_context,
                holder_moods,
            ):
                port.animation.apply_candidates(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                )
            if child_moods and not port.animation.apply_context(
                child_pet,
                "idle",
                child_context,
                child_moods,
            ):
                port.animation.apply_candidates(
                    child_pet,
                    child_candidates,
                    child_moods,
                )
            port.scene.current.stage_initialized = True
        else:
            if holder_moods and not port.animation.apply_context(
                holder_pet,
                "idle",
                holder_context,
                holder_moods,
                preserve=True,
            ):
                port.animation.apply_candidates(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                    preserve=True,
                )
            if child_moods and not port.animation.apply_context(
                child_pet,
                "idle",
                child_context,
                child_moods,
                preserve=True,
            ):
                port.animation.apply_candidates(
                    child_pet,
                    child_candidates,
                    child_moods,
                    preserve=True,
                )
        holder_pet.refresh_movement_state()
        child_pet.refresh_movement_state()
        return True

    def start_honey_guard_scene(
        self,
        port,
        child_pet,
        source="offer_tray",
        now=None,
    ):
        port.items.ensure_held_item(child_pet, ITEM_HONEY, source=source)
        guardian_name = port.pets.choose_honey_guardian(child_pet)
        if now is None:
            now = app_now()
        if not guardian_name:
            return port.items.apply_held_item_behavior(child_pet, now)

        guardian_pet = port.pets.find_by_name(guardian_name, visible_only=False)
        if not prepare_honey_guardian_activity(guardian_pet):
            return port.items.apply_held_item_behavior(child_pet, now)
        if (
            port.animation.is_window_transitioning(child_pet) or
            port.animation.prepare_window_state(guardian_pet)
        ):
            return port.items.apply_held_item_behavior(child_pet, now)
        port.animation.interrupt_window_motion(child_pet)
        port.animation.interrupt_window_motion(guardian_pet)
        approach_end = now + 3600.0
        start_result = port.scene.start(
            participant_pets=(guardian_pet, child_pet),
            item_kind=ITEM_HONEY,
            scene_kind="honey_guard",
            actor_name=guardian_name,
            target_name=child_pet.name,
            stage="approach",
            stage_initialized=False,
            stage_started_at=now,
            stage_ends_at=approach_end,
            scene_ends_at=approach_end,
            source=source,
        )
        if not start_result.started:
            return False
        port.items.apply_held_item_behavior(child_pet, now)
        port.scene.refresh_locks(guardian_pet, child_pet)
        return True

    def update_honey_guard_scene(self, port, now):
        guardian_pet = port.pets.find_by_name(port.scene.current.actor_name, visible_only=False)
        child_pet = port.pets.find_by_name(port.scene.current.target_name, visible_only=False)
        if guardian_pet is None or child_pet is None:
            port.scene.clear()
            return False
        if (
            port.animation.is_window_transitioning(child_pet) or
            port.animation.prepare_window_state(guardian_pet)
        ):
            port.scene.clear()
            return port.items.apply_held_item_behavior(child_pet, now)
        port.scene.refresh_locks(guardian_pet, child_pet)
        child_pet.state = "idle"
        child_candidates = get_direct_offer_preview_candidates(ITEM_HONEY, child_pet.name)
        child_moods = get_direct_offer_preferred_moods(ITEM_HONEY)
        child_preview_context = get_direct_offer_preview_context(ITEM_HONEY, child_pet.name)
        if port.scene.current.stage == "approach":
            if child_moods and not port.animation.apply_context(
                child_pet,
                "idle",
                child_preview_context,
                child_moods,
                preserve=True,
            ) and child_candidates:
                child_pet.ensure_candidate_animation_with_preferences(child_candidates, child_moods)
            port.items.update_held_item_position(
                getattr(child_pet, "held_item_widget", None),
                child_pet,
                ITEM_HONEY,
                prefer_preview=True,
            )
            guardian_pet.state = "move"
            move_candidates = get_honey_guardian_move_candidates(guardian_pet.name)
            move_context = get_honey_guardian_move_context(guardian_pet.name)
            move_moods = ["angry", "scold", "cool", "hurry", "effort", "serious", "sad"]
            if not port.animation.apply_context(
                guardian_pet,
                "move",
                move_context,
                move_moods,
                preserve=True,
                ignore_mood_band=True,
            ) and move_candidates:
                if not port.animation.apply_candidates(
                    guardian_pet,
                    move_candidates,
                    move_moods,
                    preserve=True,
                ):
                    guardian_pet.ensure_candidate_animation(move_candidates)
            guardian_pet.move_toward_x(
                child_pet.x(),
                speed_scale=HONEY_GUARD_APPROACH_SPEED_SCALE,
                min_speed=max(
                    HONEY_GUARD_APPROACH_MIN_SPEED_FLOOR,
                    guardian_pet.get_base_speed() * HONEY_GUARD_APPROACH_MIN_SPEED_SCALE,
                    HONEY_GUARD_RESCUE_MIN_SPEED_FLOOR,
                ),
            )
            guardian_pet.refresh_movement_state()
            child_pet.refresh_movement_state()
            if guardian_pet.distance_to(child_pet) <= 150:
                port.scene.current.stage = "snatch"
                port.scene.current.stage_initialized = False
                port.scene.current.scene_ends_at = float(now) + 1.2
                port.scene.current.stage_ends_at = float(port.scene.current.scene_ends_at)
                port.items.clear_held_item(child_pet)
                if not port.scene.current.event_recorded:
                    port.events.record_offer_event(
                        ITEM_HONEY,
                        guardian_pet.name,
                        child_pet.name,
                        "honey_guard",
                        source=port.scene.current.source,
                    )
                    child_pet.mood_score = max(0.0, float(child_pet.mood_score) - 30.0)
                    guardian_afterglow = getattr(guardian_pet, "start_negative_afterglow", None)
                    if callable(guardian_afterglow):
                        guardian_afterglow(
                            duration=HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS,
                            preferred_moods=HONEY_GUARD_TAKE_PREFERRED_MOODS,
                            forbidden_moods=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                            now=now,
                        )
                    else:
                        guardian_pet.negative_afterglow_until = (
                            float(now) + HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS
                        )
                        guardian_pet.negative_afterglow_preferred_moods = HONEY_GUARD_TAKE_PREFERRED_MOODS
                        guardian_pet.negative_afterglow_forbidden_moods = HONEY_GUARD_TAKE_FORBIDDEN_MOODS
                    start_negative_afterglow = getattr(child_pet, "start_negative_afterglow", None)
                    if callable(start_negative_afterglow):
                        start_negative_afterglow(
                            duration=HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS,
                            preferred_moods=["hard-cry", "cry", "sad", "scared", "think"],
                            forbidden_moods=["happy", "smile", "relief", "calm", "confidence", "cool", "glance"],
                            now=now,
                            block_care=True,
                        )
                    else:
                        child_pet.negative_afterglow_until = float(now) + HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS
                        child_pet.negative_afterglow_care_block_until = (
                            float(now) + HONEY_GUARD_NEGATIVE_AFTERGLOW_SECONDS
                        )
                        child_pet.negative_afterglow_preferred_moods = (
                            "hard-cry",
                            "cry",
                            "sad",
                            "scared",
                            "think",
                        )
                        child_pet.negative_afterglow_forbidden_moods = (
                            "happy",
                            "smile",
                            "relief",
                            "calm",
                            "confidence",
                            "cool",
                            "glance",
                        )
                    if hasattr(child_pet, "sync_mood_state_with_score"):
                        child_pet.sync_mood_state_with_score()
                    port.scene.current.event_recorded = True
                return port.flow.update_honey_guard_scene(now)
            return True

        port.animation.reset_pet_motion(guardian_pet)
        port.animation.reset_pet_motion(child_pet)
        guardian_pet.direction = -1 if child_pet.x() < guardian_pet.x() else 1
        child_pet.direction = -guardian_pet.direction
        guardian_candidates = get_honey_guardian_take_candidates(guardian_pet.name)
        denied_candidates = get_denied_offer_reaction_candidates(child_pet.name)
        denied_moods = get_denied_offer_preferred_moods()
        denied_forbidden = get_denied_offer_forbidden_moods()
        guardian_take_context = get_honey_guardian_take_context(guardian_pet.name)
        denied_context = get_denied_offer_context(child_pet.name)

        if not port.scene.current.stage_initialized:
            guardian_changed = port.animation.apply_context(
                guardian_pet,
                "idle",
                guardian_take_context,
                HONEY_GUARD_TAKE_PREFERRED_MOODS,
                forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                ignore_mood_band=True,
            )
            if not guardian_changed and guardian_candidates:
                guardian_changed = port.animation.apply_candidates(
                    guardian_pet,
                    guardian_candidates,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                )
            if not guardian_changed:
                port.animation.apply_reaction(
                    guardian_pet,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                )
            child_changed = port.animation.apply_context(
                child_pet,
                "idle",
                denied_context,
                denied_moods,
                forbidden=denied_forbidden,
                ignore_mood_band=True,
            )
            if not child_changed and denied_candidates:
                child_changed = port.animation.apply_candidates(
                    child_pet,
                    denied_candidates,
                    denied_moods,
                    forbidden=denied_forbidden,
                )
            if not child_changed:
                port.animation.apply_reaction(
                    child_pet,
                    denied_moods,
                    forbidden=denied_forbidden,
                )
            port.scene.current.stage_initialized = True
        else:
            guardian_changed = port.animation.apply_context(
                guardian_pet,
                "idle",
                guardian_take_context,
                HONEY_GUARD_TAKE_PREFERRED_MOODS,
                forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                preserve=True,
                ignore_mood_band=True,
            )
            if not guardian_changed and guardian_candidates:
                guardian_changed = port.animation.apply_candidates(
                    guardian_pet,
                    guardian_candidates,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                    preserve=True,
                )
            if not guardian_changed:
                port.animation.apply_reaction(
                    guardian_pet,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                    preserve=True,
                )
            child_changed = port.animation.apply_context(
                child_pet,
                "idle",
                denied_context,
                denied_moods,
                forbidden=denied_forbidden,
                preserve=True,
                ignore_mood_band=True,
            )
            if not child_changed and denied_candidates:
                child_changed = port.animation.apply_candidates(
                    child_pet,
                    denied_candidates,
                    denied_moods,
                    forbidden=denied_forbidden,
                    preserve=True,
                )
            if not child_changed:
                port.animation.apply_reaction(
                    child_pet,
                    denied_moods,
                    forbidden=denied_forbidden,
                    preserve=True,
                )
        guardian_pet.refresh_movement_state()
        child_pet.refresh_movement_state()
        if now >= float(port.scene.current.scene_ends_at):
            port.scene.clear()
            return False
        return True
