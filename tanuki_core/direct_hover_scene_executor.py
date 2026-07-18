import random

from .offer_interaction_rules import (
    OFFER_HOVER_AVOID_CURSOR_DISTANCE,
    OFFER_HOVER_AVOID_CURSOR_MIN_SPEED,
    OFFER_HOVER_AVOID_CURSOR_SPEED_SCALE,
    can_pet_interact_with_offer_item,
    get_denied_offer_context,
    get_denied_offer_forbidden_moods,
    get_denied_offer_preferred_moods,
    get_denied_offer_reaction_candidates,
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
    get_direct_offer_accept_purpose_order,
    get_direct_offer_preferred_moods,
    get_direct_offer_preview_candidates,
    get_direct_offer_preview_context,
    get_offer_hover_negative_afterglow_buffer_seconds,
    get_offer_hover_reaction_cooldown_buffer_seconds,
    get_offer_hover_reaction_variants,
    get_offer_hover_timeout_seconds,
    get_offer_hover_timeout_stage_context,
)
from .pet_ambient_mood_rules import resolve_offer_miss_event
from .runtime import app_now


class DirectHoverSceneExecutor:
    """Executes direct-offer and hover-reaction scenes through the runtime facade."""

    def apply_offer_hover_miss(self, runtime, pet, item_kind, now=None):
        if pet is None or not item_kind:
            return False
        if now is None:
            now = app_now()
        decision = resolve_offer_miss_event(
            now=now,
            hover_started_at=runtime.offer_hover_started_at,
            hover_timeout_seconds=get_offer_hover_timeout_seconds(item_kind),
            cooldown_until=getattr(pet, "offer_miss_event_cooldown_until", 0.0),
        )
        if not decision.should_trigger:
            return False
        pet.offer_miss_event_cooldown_until = float(now) + float(decision.cooldown_seconds)
        pet.mood_score = max(0.0, float(pet.mood_score) - float(decision.mood_delta))
        start_negative_afterglow = getattr(pet, "start_negative_afterglow", None)
        if callable(start_negative_afterglow):
            start_negative_afterglow(
                duration=float(decision.afterglow_duration),
                preferred_moods=list(decision.preferred_moods),
                forbidden_moods=list(decision.forbidden_moods),
                now=now,
            )
        if hasattr(pet, "sync_mood_state_with_score"):
            pet.sync_mood_state_with_score()
        if hasattr(pet, "apply_reaction"):
            pet.apply_reaction(list(decision.preferred_moods), is_negative=True)
        return True

    def hover_timeout_scene_accepts_offer_drop(self, runtime, item_kind, global_pos):
        if runtime.offer_scene is None or runtime.offer_scene.scene_kind != "hover_timeout_reaction":
            return False
        stages = tuple(getattr(runtime.offer_scene, "hover_reaction_stages", ()) or ())
        if not stages:
            return False
        stage_index = int(getattr(runtime.offer_scene, "hover_reaction_stage_index", 0) or 0)
        if stage_index != 0:
            return False
        target_pet = runtime.find_offer_drop_target(item_kind, global_pos)
        if target_pet is None or target_pet.name != runtime.offer_scene.target_name:
            target_pet = runtime.find_offer_hover_target(
                item_kind,
                global_pos,
                ignore_reaction_cooldown=True,
            )
        if target_pet is None or target_pet.name != runtime.offer_scene.target_name:
            return False
        scene_target_name = runtime.offer_scene.target_name
        runtime.clear_offer_scene()
        runtime.clear_offer_hover(apply_miss=False)
        target_pet = runtime.find_pet_by_name(scene_target_name, visible_only=False)
        if target_pet is None or runtime.pet_is_busy_for_offer_interaction(target_pet):
            return False
        return runtime.start_offer_interaction_for_target(item_kind, target_pet, source="offer_tray")

    def finalize_offer_hover_timeout_failure(self, runtime, target_pet, now):
        if runtime.offer_scene is None or runtime.offer_scene.scene_kind != "hover_timeout_reaction":
            return False
        item_kind = runtime.offer_scene.item_kind
        cooldown_duration = get_offer_hover_reaction_cooldown_buffer_seconds(item_kind)
        afterglow_duration = get_offer_hover_negative_afterglow_buffer_seconds(item_kind)
        target_pet.offer_hover_reaction_cooldown_until = float(now) + float(cooldown_duration)
        runtime.apply_offer_negative_afterglow(
            target_pet,
            now,
            amount=30.0,
            duration=afterglow_duration,
        )
        runtime.record_offer_event(
            item_kind,
            target_pet.name,
            target_pet.name,
            "hover_timeout_reaction",
            source="offer_hover",
        )
        runtime.clear_offer_scene()
        return False

    def apply_offer_negative_afterglow(self, runtime, pet, now, amount=30.0, duration=5.0):
        if pet is None:
            return False
        pet.mood_score = max(0.0, float(pet.mood_score) - float(amount))
        start_negative_afterglow = getattr(pet, "start_negative_afterglow", None)
        if callable(start_negative_afterglow):
            start_negative_afterglow(
                duration=duration,
                preferred_moods=["hard-cry", "cry", "sad", "scared", "think"],
                forbidden_moods=["happy", "smile", "relief", "calm", "confidence", "cool", "glance"],
                now=now,
            )
        else:
            pet.negative_afterglow_until = float(now) + float(duration)
            pet.negative_afterglow_preferred_moods = ("hard-cry", "cry", "sad", "scared", "think")
            pet.negative_afterglow_forbidden_moods = (
                "happy",
                "smile",
                "relief",
                "calm",
                "confidence",
                "cool",
                "glance",
            )
        if hasattr(pet, "sync_mood_state_with_score"):
            pet.sync_mood_state_with_score()
        return True

    def apply_offer_hover_timeout_stage(self, runtime, pet, stage, preserve=False):
        if pet is None or stage is None:
            return False
        pet.state = "move" if stage.purpose == "move" else "idle"
        context = ""
        if runtime.offer_scene is not None:
            context = get_offer_hover_timeout_stage_context(
                getattr(runtime.offer_scene, "hover_reaction_variant_label", ""),
                getattr(runtime.offer_scene, "hover_reaction_stage_index", 0),
            )
        if runtime.apply_scene_context_with_preferences(
            pet,
            stage.purpose,
            context,
            [stage.mood_tag],
            preserve=preserve,
            ignore_mood_band=True,
        ):
            return True
        if runtime.apply_scene_candidates_with_preferences(
            pet,
            [(stage.purpose, stage.action_type)],
            [stage.mood_tag],
            preserve=preserve,
        ):
            return True
        return runtime.apply_scene_reaction_with_preferences(
            pet,
            [stage.mood_tag],
            preserve=preserve,
        )

    def apply_offer_hover_cursor_avoidance(self, runtime, pet):
        if pet is None:
            return False
        pet_center_x = pet.x() + (pet.width() / 2.0)
        cursor_x = float(runtime.offer_hover_global_x or pet_center_x)
        direction = 1 if pet_center_x >= cursor_x else -1
        pet.direction = direction
        target_x = pet.x() + (direction * OFFER_HOVER_AVOID_CURSOR_DISTANCE)
        pet.move_toward_x(
            target_x,
            speed_scale=OFFER_HOVER_AVOID_CURSOR_SPEED_SCALE,
            min_speed=OFFER_HOVER_AVOID_CURSOR_MIN_SPEED,
        )
        return True

    def start_offer_hover_timeout_scene(
        self,
        runtime,
        item_kind,
        target_pet,
        now=None,
        choose_variant=None,
    ):
        if target_pet is None:
            return False
        if now is None:
            now = app_now()
        if runtime.pet_is_busy_for_offer_interaction(target_pet, now):
            runtime.clear_offer_hover(apply_miss=False)
            return False
        variants = get_offer_hover_reaction_variants(item_kind, target_pet.name)
        if not variants:
            return False
        if choose_variant is None:
            choose_variant = random.choice
        chosen_variant = choose_variant(list(variants))
        if not chosen_variant.stages:
            return False
        cursor_x = float(runtime.offer_hover_global_x)
        cursor_y = float(runtime.offer_hover_global_y)
        runtime.clear_offer_hover(apply_miss=False)
        runtime.offer_hover_global_x = cursor_x
        runtime.offer_hover_global_y = cursor_y
        first_stage = chosen_variant.stages[0]
        total_duration = sum(float(stage.duration_seconds) for stage in chosen_variant.stages)
        scene_end = float(now) + max(0.2, total_duration)
        start_result = runtime.item_scene_coordinator.start_scene(
            runtime,
            participant_pets=(target_pet,),
            item_kind=item_kind,
            scene_kind="hover_timeout_reaction",
            actor_name=target_pet.name,
            target_name=target_pet.name,
            stage="reaction",
            stage_initialized=False,
            stage_ends_at=float(now) + float(first_stage.duration_seconds),
            scene_ends_at=scene_end,
            source="offer_hover",
            hover_reaction_variant_label=chosen_variant.label,
            hover_reaction_avoid_cursor=chosen_variant.avoid_cursor,
            hover_reaction_stage_index=0,
            hover_reaction_stages=tuple(chosen_variant.stages),
        )
        if not start_result.started:
            return False
        return runtime.update_offer_hover_timeout_reaction_scene(float(now))

    def start_direct_offer_scene(
        self,
        runtime,
        item_kind,
        target_pet,
        source="offer_tray",
        now=None,
        roll=None,
    ):
        if now is None:
            now = app_now()
        if roll is None:
            roll = random.random()
        end_at = now + 1.8
        purpose_order = get_direct_offer_accept_purpose_order(
            item_kind,
            target_pet.name,
            roll=roll,
        )
        start_result = runtime.item_scene_coordinator.start_scene(
            runtime,
            participant_pets=(target_pet,),
            item_kind=item_kind,
            scene_kind="direct_accept",
            actor_name=target_pet.name,
            target_name=target_pet.name,
            stage="accept",
            stage_ends_at=end_at,
            scene_ends_at=end_at,
            source=source,
            direct_accept_purpose_order=tuple(purpose_order),
        )
        if not start_result.started:
            return False
        runtime.apply_offer_mood_reward(target_pet.name)
        runtime.record_offer_event(
            item_kind,
            target_pet.name,
            target_pet.name,
            "direct_accept",
            source=source,
        )
        return True

    def update_offer_hover_preview(self, runtime, now):
        target_pet = runtime.find_pet_by_name(runtime.offer_hover_target_name, visible_only=False)
        if target_pet is None or not target_pet.isVisible():
            runtime.clear_offer_hover(apply_miss=False)
            return False
        if not can_pet_interact_with_offer_item(runtime.offer_hover_item_kind, target_pet.name):
            runtime.clear_offer_hover(apply_miss=False)
            return False
        if runtime.pet_is_busy_for_offer_interaction(target_pet, now):
            runtime.clear_offer_hover(apply_miss=False)
            return False
        if float(getattr(target_pet, "offer_hover_reaction_cooldown_until", 0.0) or 0.0) > float(now):
            runtime.clear_offer_hover(apply_miss=False)
            return False
        preview_candidates = get_direct_offer_preview_candidates(runtime.offer_hover_item_kind, target_pet.name)
        preferred_moods = get_direct_offer_preferred_moods(runtime.offer_hover_item_kind)
        preview_context = get_direct_offer_preview_context(runtime.offer_hover_item_kind, target_pet.name)
        if not preferred_moods or (not preview_candidates and not preview_context):
            runtime.clear_offer_hover(apply_miss=False)
            return False
        if not runtime.offer_hover_started_at:
            runtime.offer_hover_started_at = float(now)
        hover_timeout_seconds = get_offer_hover_timeout_seconds(runtime.offer_hover_item_kind)
        if (
            float(now) - float(runtime.offer_hover_started_at) >= hover_timeout_seconds and
            get_offer_hover_reaction_variants(runtime.offer_hover_item_kind, target_pet.name)
        ):
            return runtime.start_offer_hover_timeout_scene(runtime.offer_hover_item_kind, target_pet, now=now)
        runtime.lock_pet_for_offer_scene(target_pet, "hover_preview", now + 0.2)
        target_pet.state = "idle"
        target_center_x = target_pet.x() + (target_pet.width() / 2.0)
        target_pet.direction = -1 if runtime.offer_hover_global_x < target_center_x else 1
        if not runtime.apply_scene_context_with_preferences(
            target_pet,
            "idle",
            preview_context,
            preferred_moods,
            preserve=True,
        ) and preview_candidates and not target_pet.ensure_candidate_animation_with_preferences(
            preview_candidates,
            preferred_moods,
        ):
            target_pet.ensure_candidate_animation(preview_candidates)
        target_pet.perception_situation_tag = "locked"
        target_pet.expression_animation_context = "ambient"
        target_pet.expression_relation_overlay = "none"
        target_pet.expression_focus_target_name = ""
        target_pet.expression_posture_bias = "neutral"
        target_pet.expression_spacing_bias = "neutral"
        target_pet.expression_look_at_target = False
        target_pet.relationship_focus_target_name = ""
        target_pet.refresh_movement_state()
        return True

    def update_offer_hover_timeout_reaction_scene(self, runtime, now):
        target_pet = runtime.find_pet_by_name(runtime.offer_scene.target_name, visible_only=False)
        if target_pet is None:
            runtime.clear_offer_scene()
            return False
        if runtime.pet_is_busy_for_offer_interaction(target_pet, now):
            runtime.clear_offer_scene()
            return False
        stages = tuple(getattr(runtime.offer_scene, "hover_reaction_stages", ()) or ())
        if not stages:
            runtime.clear_offer_scene()
            return False
        stage_index = int(getattr(runtime.offer_scene, "hover_reaction_stage_index", 0) or 0)
        while stage_index < len(stages) and float(now) >= float(runtime.offer_scene.stage_ends_at):
            stage_index += 1
            runtime.offer_scene.stage_initialized = False
            runtime.offer_scene.hover_reaction_stage_index = stage_index
            if stage_index < len(stages):
                runtime.offer_scene.stage_ends_at = float(now) + float(stages[stage_index].duration_seconds)
        if stage_index >= len(stages) or float(now) >= float(runtime.offer_scene.scene_ends_at):
            return runtime.finalize_offer_hover_timeout_failure(target_pet, now)
        stage = stages[stage_index]
        runtime.refresh_offer_scene_locks(target_pet)
        target_pet.state = "move" if stage.purpose == "move" else "idle"
        pet_center_x = target_pet.x() + (target_pet.width() / 2.0)
        if runtime.offer_scene.hover_reaction_avoid_cursor and stage.purpose == "move":
            target_pet.direction = 1 if pet_center_x >= runtime.offer_hover_global_x else -1
        else:
            target_pet.direction = -1 if runtime.offer_hover_global_x < pet_center_x else 1
        if not runtime.offer_scene.stage_initialized:
            runtime.apply_offer_hover_timeout_stage(target_pet, stage, preserve=False)
            runtime.offer_scene.stage_initialized = True
        else:
            runtime.apply_offer_hover_timeout_stage(target_pet, stage, preserve=True)
        if runtime.offer_scene.hover_reaction_avoid_cursor and stage.purpose == "move":
            runtime.apply_offer_hover_cursor_avoidance(target_pet)
        target_pet.perception_situation_tag = "locked"
        target_pet.expression_animation_context = "ambient"
        target_pet.expression_relation_overlay = "none"
        target_pet.expression_focus_target_name = ""
        target_pet.expression_posture_bias = "neutral"
        target_pet.expression_spacing_bias = "neutral"
        target_pet.expression_look_at_target = False
        target_pet.relationship_focus_target_name = ""
        target_pet.refresh_movement_state()
        return True

    def update_direct_offer_scene(self, runtime, now, roll_provider=None):
        target_pet = runtime.find_pet_by_name(runtime.offer_scene.target_name, visible_only=False)
        if target_pet is None or now >= float(runtime.offer_scene.scene_ends_at):
            runtime.clear_offer_scene()
            return False
        runtime.refresh_offer_scene_locks(target_pet)
        candidates = get_direct_offer_accept_candidates(runtime.offer_scene.item_kind, target_pet.name)
        preferred_moods = get_direct_offer_preferred_moods(runtime.offer_scene.item_kind)
        accept_context = get_direct_offer_accept_context(runtime.offer_scene.item_kind, target_pet.name)
        purpose_order = tuple(getattr(runtime.offer_scene, "direct_accept_purpose_order", ()) or ())
        if not purpose_order:
            if roll_provider is None:
                roll_provider = random.random
            purpose_order = tuple(
                get_direct_offer_accept_purpose_order(
                    runtime.offer_scene.item_kind,
                    target_pet.name,
                    roll=roll_provider(),
                )
            )
            runtime.offer_scene.direct_accept_purpose_order = purpose_order
        ordered_candidates = runtime.order_candidates_by_purpose(candidates, purpose_order)
        if preferred_moods:
            if not runtime.apply_scene_contexts_with_preferences(
                target_pet,
                purpose_order,
                accept_context,
                preferred_moods,
                preserve=True,
            ) and ordered_candidates and not target_pet.ensure_candidate_animation_with_preferences(
                ordered_candidates,
                preferred_moods,
            ):
                target_pet.ensure_candidate_animation(ordered_candidates)
        runtime.update_direct_offer_accept_motion(
            target_pet,
            runtime.offer_scene.item_kind,
            accept_context,
            ordered_candidates,
        )
        target_pet.perception_situation_tag = "locked"
        target_pet.expression_animation_context = "ambient"
        target_pet.expression_relation_overlay = "none"
        target_pet.expression_focus_target_name = ""
        target_pet.expression_posture_bias = "neutral"
        target_pet.expression_spacing_bias = "neutral"
        target_pet.expression_look_at_target = False
        target_pet.relationship_focus_target_name = ""
        return True

    def update_deny_only_offer_scene(self, runtime, now):
        target_pet = runtime.find_pet_by_name(runtime.offer_scene.target_name, visible_only=False)
        if target_pet is None or now >= float(runtime.offer_scene.scene_ends_at):
            runtime.clear_offer_scene()
            return False
        runtime.refresh_offer_scene_locks(target_pet)
        target_pet.state = "idle"
        candidates = get_denied_offer_reaction_candidates(target_pet.name)
        preferred_moods = get_denied_offer_preferred_moods()
        denied_context = get_denied_offer_context(target_pet.name)
        if preferred_moods:
            if not runtime.apply_scene_context_with_preferences(
                target_pet,
                "idle",
                denied_context,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
                preserve=True,
                ignore_mood_band=True,
            ) and not runtime.apply_scene_candidates_with_preferences(
                target_pet,
                candidates,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
            ) and not runtime.apply_scene_reaction_with_preferences(
                target_pet,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
            ):
                target_pet.apply_reaction(preferred_moods, is_negative=True)
        target_pet.refresh_movement_state()
        return True
