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


class BottleHoneySceneExecutor:
    """Executes bottle handoff and honey-guard scenes through runtime facades."""

    def start_bottle_feed_scene(
        self,
        runtime,
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
        runtime.ensure_pet_held_item(holder_pet, ITEM_BOTTLE, source=source)
        child_pet = runtime.choose_bottle_feed_child_for_holder(holder_pet, now=now)
        if child_pet is None:
            return runtime.apply_held_item_behavior(holder_pet, now)
        if (
            runtime.pet_is_window_transitioning_for_offer(holder_pet) or
            runtime.pet_is_window_transitioning_for_offer(child_pet) or
            runtime.prepare_pet_window_state_for_offer(holder_pet) or
            runtime.prepare_pet_window_state_for_offer(child_pet)
        ):
            return runtime.apply_held_item_behavior(holder_pet, now)
        runtime.interrupt_pet_window_motion_for_offer(holder_pet)
        runtime.interrupt_pet_window_motion_for_offer(child_pet)
        approach_end = now + 3600.0
        start_result = runtime.item_scene_coordinator.start_scene(
            runtime,
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
        runtime.apply_held_item_behavior(holder_pet, now)
        runtime.refresh_offer_scene_locks(holder_pet, child_pet)
        return True

    def update_bottle_feed_scene(self, runtime, now):
        holder_pet = runtime.find_pet_by_name(runtime.offer_scene.actor_name, visible_only=False)
        child_pet = runtime.find_pet_by_name(runtime.offer_scene.target_name, visible_only=False)
        if holder_pet is None:
            runtime.clear_offer_scene()
            return False
        if child_pet is None or not child_pet.isVisible():
            runtime.clear_offer_scene()
            return runtime.apply_held_item_behavior(holder_pet, now)
        if (
            runtime.pet_is_window_transitioning_for_offer(holder_pet) or
            runtime.pet_is_window_transitioning_for_offer(child_pet) or
            runtime.prepare_pet_window_state_for_offer(holder_pet) or
            runtime.prepare_pet_window_state_for_offer(child_pet)
        ):
            runtime.clear_offer_scene()
            return runtime.apply_held_item_behavior(holder_pet, now)

        runtime.refresh_offer_scene_locks(holder_pet, child_pet)

        if runtime.offer_scene.stage == "approach":
            holder_pet.state = "idle"
            holder_candidates = get_bottle_feed_holder_idle_candidates(holder_pet.name)
            holder_moods = get_bottle_feed_holder_idle_preferred_moods()
            holder_context = get_bottle_feed_holder_idle_context(holder_pet.name)
            if holder_moods:
                if not runtime.apply_scene_context_with_preferences(
                    holder_pet,
                    "idle",
                    holder_context,
                    holder_moods,
                    preserve=True,
                ) and not runtime.apply_scene_candidates_with_preferences(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                    preserve=True,
                ):
                    holder_pet.ensure_candidate_animation_with_preferences(holder_candidates, holder_moods)
            runtime.update_held_offer_widget_position(
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
                if not runtime.apply_scene_context_with_preferences(
                    child_pet,
                    "move",
                    child_context,
                    child_moods,
                    preserve=True,
                ) and not runtime.apply_scene_candidates_with_preferences(
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
                runtime.offer_scene.stage = "drink"
                runtime.offer_scene.stage_initialized = False
                runtime.offer_scene.scene_ends_at = float(now) + BOTTLE_FEED_DRINK_SECONDS
                runtime.offer_scene.stage_ends_at = float(runtime.offer_scene.scene_ends_at)
                return runtime.update_bottle_feed_scene(now)
            return True

        if now >= float(runtime.offer_scene.scene_ends_at):
            if not runtime.offer_scene.event_recorded:
                runtime.apply_offer_mood_reward(child_pet.name)
                runtime.record_offer_event(
                    ITEM_BOTTLE,
                    holder_pet.name,
                    child_pet.name,
                    "bottle_feed",
                    source=runtime.offer_scene.source,
                )
                runtime.offer_scene.event_recorded = True
            runtime.clear_offer_scene()
            return True

        runtime.reset_offer_scene_pet_motion(holder_pet)
        runtime.reset_offer_scene_pet_motion(child_pet)
        holder_pet.direction = -1 if child_pet.x() < holder_pet.x() else 1
        child_pet.direction = -holder_pet.direction

        holder_candidates = get_bottle_feed_holder_watch_candidates(holder_pet.name)
        holder_moods = get_bottle_feed_holder_watch_preferred_moods()
        child_candidates = get_bottle_feed_child_drink_candidates(child_pet.name)
        child_moods = get_bottle_feed_child_drink_preferred_moods()
        holder_context = get_bottle_feed_holder_watch_context(holder_pet.name)
        child_context = get_bottle_feed_child_drink_context(child_pet.name)

        if not runtime.offer_scene.stage_initialized:
            runtime.clear_pet_held_item(holder_pet)
            if holder_moods and not runtime.apply_scene_context_with_preferences(
                holder_pet,
                "idle",
                holder_context,
                holder_moods,
            ):
                runtime.apply_scene_candidates_with_preferences(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                )
            if child_moods and not runtime.apply_scene_context_with_preferences(
                child_pet,
                "idle",
                child_context,
                child_moods,
            ):
                runtime.apply_scene_candidates_with_preferences(
                    child_pet,
                    child_candidates,
                    child_moods,
                )
            runtime.offer_scene.stage_initialized = True
        else:
            if holder_moods and not runtime.apply_scene_context_with_preferences(
                holder_pet,
                "idle",
                holder_context,
                holder_moods,
                preserve=True,
            ):
                runtime.apply_scene_candidates_with_preferences(
                    holder_pet,
                    holder_candidates,
                    holder_moods,
                    preserve=True,
                )
            if child_moods and not runtime.apply_scene_context_with_preferences(
                child_pet,
                "idle",
                child_context,
                child_moods,
                preserve=True,
            ):
                runtime.apply_scene_candidates_with_preferences(
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
        runtime,
        child_pet,
        source="offer_tray",
        now=None,
    ):
        runtime.ensure_pet_held_item(child_pet, ITEM_HONEY, source=source)
        guardian_name = runtime.choose_honey_guardian_for_child(child_pet)
        if now is None:
            now = app_now()
        if not guardian_name:
            return runtime.apply_held_item_behavior(child_pet, now)

        guardian_pet = runtime.find_pet_by_name(guardian_name, visible_only=False)
        if (
            runtime.pet_is_window_transitioning_for_offer(child_pet) or
            runtime.prepare_pet_window_state_for_offer(guardian_pet)
        ):
            return runtime.apply_held_item_behavior(child_pet, now)
        runtime.interrupt_pet_window_motion_for_offer(child_pet)
        runtime.interrupt_pet_window_motion_for_offer(guardian_pet)
        approach_end = now + 3600.0
        start_result = runtime.item_scene_coordinator.start_scene(
            runtime,
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
        runtime.apply_held_item_behavior(child_pet, now)
        runtime.refresh_offer_scene_locks(guardian_pet, child_pet)
        return True

    def update_honey_guard_scene(self, runtime, now):
        guardian_pet = runtime.find_pet_by_name(runtime.offer_scene.actor_name, visible_only=False)
        child_pet = runtime.find_pet_by_name(runtime.offer_scene.target_name, visible_only=False)
        if guardian_pet is None or child_pet is None:
            runtime.clear_offer_scene()
            return False
        if (
            runtime.pet_is_window_transitioning_for_offer(child_pet) or
            runtime.prepare_pet_window_state_for_offer(guardian_pet)
        ):
            runtime.clear_offer_scene()
            return runtime.apply_held_item_behavior(child_pet, now)
        runtime.refresh_offer_scene_locks(guardian_pet, child_pet)
        child_pet.state = "idle"
        child_candidates = get_direct_offer_preview_candidates(ITEM_HONEY, child_pet.name)
        child_moods = get_direct_offer_preferred_moods(ITEM_HONEY)
        child_preview_context = get_direct_offer_preview_context(ITEM_HONEY, child_pet.name)
        if runtime.offer_scene.stage == "approach":
            if child_moods and not runtime.apply_scene_context_with_preferences(
                child_pet,
                "idle",
                child_preview_context,
                child_moods,
                preserve=True,
            ) and child_candidates:
                child_pet.ensure_candidate_animation_with_preferences(child_candidates, child_moods)
            runtime.update_held_offer_widget_position(
                getattr(child_pet, "held_item_widget", None),
                child_pet,
                ITEM_HONEY,
                prefer_preview=True,
            )
            guardian_pet.state = "move"
            move_candidates = get_honey_guardian_move_candidates(guardian_pet.name)
            move_context = get_honey_guardian_move_context(guardian_pet.name)
            move_moods = ["angry", "scold", "cool", "hurry", "effort", "serious", "sad"]
            if not runtime.apply_scene_context_with_preferences(
                guardian_pet,
                "move",
                move_context,
                move_moods,
                preserve=True,
                ignore_mood_band=True,
            ) and move_candidates:
                if not runtime.apply_scene_candidates_with_preferences(
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
                runtime.offer_scene.stage = "snatch"
                runtime.offer_scene.stage_initialized = False
                runtime.offer_scene.scene_ends_at = float(now) + 1.2
                runtime.offer_scene.stage_ends_at = float(runtime.offer_scene.scene_ends_at)
                runtime.clear_pet_held_item(child_pet)
                if not runtime.offer_scene.event_recorded:
                    runtime.record_offer_event(
                        ITEM_HONEY,
                        guardian_pet.name,
                        child_pet.name,
                        "honey_guard",
                        source=runtime.offer_scene.source,
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
                    runtime.offer_scene.event_recorded = True
                return runtime.update_honey_guard_scene(now)
            return True

        runtime.reset_offer_scene_pet_motion(guardian_pet)
        runtime.reset_offer_scene_pet_motion(child_pet)
        guardian_pet.direction = -1 if child_pet.x() < guardian_pet.x() else 1
        child_pet.direction = -guardian_pet.direction
        guardian_candidates = get_honey_guardian_take_candidates(guardian_pet.name)
        denied_candidates = get_denied_offer_reaction_candidates(child_pet.name)
        denied_moods = get_denied_offer_preferred_moods()
        denied_forbidden = get_denied_offer_forbidden_moods()
        guardian_take_context = get_honey_guardian_take_context(guardian_pet.name)
        denied_context = get_denied_offer_context(child_pet.name)

        if not runtime.offer_scene.stage_initialized:
            guardian_changed = runtime.apply_scene_context_with_preferences(
                guardian_pet,
                "idle",
                guardian_take_context,
                HONEY_GUARD_TAKE_PREFERRED_MOODS,
                forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                ignore_mood_band=True,
            )
            if not guardian_changed and guardian_candidates:
                guardian_changed = runtime.apply_scene_candidates_with_preferences(
                    guardian_pet,
                    guardian_candidates,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                )
            if not guardian_changed:
                runtime.apply_scene_reaction_with_preferences(
                    guardian_pet,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                )
            child_changed = runtime.apply_scene_context_with_preferences(
                child_pet,
                "idle",
                denied_context,
                denied_moods,
                forbidden=denied_forbidden,
                ignore_mood_band=True,
            )
            if not child_changed and denied_candidates:
                child_changed = runtime.apply_scene_candidates_with_preferences(
                    child_pet,
                    denied_candidates,
                    denied_moods,
                    forbidden=denied_forbidden,
                )
            if not child_changed:
                runtime.apply_scene_reaction_with_preferences(
                    child_pet,
                    denied_moods,
                    forbidden=denied_forbidden,
                )
            runtime.offer_scene.stage_initialized = True
        else:
            guardian_changed = runtime.apply_scene_context_with_preferences(
                guardian_pet,
                "idle",
                guardian_take_context,
                HONEY_GUARD_TAKE_PREFERRED_MOODS,
                forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                preserve=True,
                ignore_mood_band=True,
            )
            if not guardian_changed and guardian_candidates:
                guardian_changed = runtime.apply_scene_candidates_with_preferences(
                    guardian_pet,
                    guardian_candidates,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                    preserve=True,
                )
            if not guardian_changed:
                runtime.apply_scene_reaction_with_preferences(
                    guardian_pet,
                    HONEY_GUARD_TAKE_PREFERRED_MOODS,
                    forbidden=HONEY_GUARD_TAKE_FORBIDDEN_MOODS,
                    preserve=True,
                )
            child_changed = runtime.apply_scene_context_with_preferences(
                child_pet,
                "idle",
                denied_context,
                denied_moods,
                forbidden=denied_forbidden,
                preserve=True,
                ignore_mood_band=True,
            )
            if not child_changed and denied_candidates:
                child_changed = runtime.apply_scene_candidates_with_preferences(
                    child_pet,
                    denied_candidates,
                    denied_moods,
                    forbidden=denied_forbidden,
                    preserve=True,
                )
            if not child_changed:
                runtime.apply_scene_reaction_with_preferences(
                    child_pet,
                    denied_moods,
                    forbidden=denied_forbidden,
                    preserve=True,
                )
        guardian_pet.refresh_movement_state()
        child_pet.refresh_movement_state()
        if now >= float(runtime.offer_scene.scene_ends_at):
            runtime.clear_offer_scene()
            return False
        return True
