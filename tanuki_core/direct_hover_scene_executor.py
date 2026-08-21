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
from .offer_scene_execution_port import adapt_offer_scene_executor


@adapt_offer_scene_executor
class DirectHoverSceneExecutor:
    @staticmethod
    def pet_can_interact_with_offer_item(port, pet, item_kind):
        try:
            return bool(port.pets.can_interact_with_item(pet, item_kind))
        except AttributeError:
            pass
        return bool(
            pet is not None
            and can_pet_interact_with_offer_item(item_kind, pet.name)
        )

    """Executes direct-offer and hover-reaction scenes through a narrow port."""

    def apply_offer_hover_miss(self, port, pet, item_kind, now=None):
        if pet is None or not item_kind:
            return False
        if now is None:
            now = app_now()
        decision = resolve_offer_miss_event(
            now=now,
            hover_started_at=port.hover.started_at,
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

    def hover_timeout_scene_accepts_offer_drop(self, port, item_kind, global_pos):
        if port.scene.current is None or port.scene.current.scene_kind != "hover_timeout_reaction":
            return False
        stages = tuple(getattr(port.scene.current, "hover_reaction_stages", ()) or ())
        if not stages:
            return False
        stage_index = int(getattr(port.scene.current, "hover_reaction_stage_index", 0) or 0)
        if stage_index != 0:
            return False
        target_pet = port.pets.find_drop_target(item_kind, global_pos)
        if target_pet is None or target_pet.name != port.scene.current.target_name:
            target_pet = port.pets.find_hover_target(
                item_kind,
                global_pos,
                ignore_reaction_cooldown=True,
            )
        if target_pet is None or target_pet.name != port.scene.current.target_name:
            return False
        scene_target_name = port.scene.current.target_name
        port.scene.clear()
        port.hover.clear(apply_miss=False)
        target_pet = port.pets.find_by_name(scene_target_name, visible_only=False)
        if target_pet is None or port.pets.is_busy(target_pet):
            return False
        return port.flow.start_interaction_for_target(item_kind, target_pet, source="offer_tray")

    def finalize_offer_hover_timeout_failure(self, port, target_pet, now):
        if port.scene.current is None or port.scene.current.scene_kind != "hover_timeout_reaction":
            return False
        item_kind = port.scene.current.item_kind
        cooldown_duration = get_offer_hover_reaction_cooldown_buffer_seconds(item_kind)
        afterglow_duration = get_offer_hover_negative_afterglow_buffer_seconds(item_kind)
        target_pet.offer_hover_reaction_cooldown_until = float(now) + float(cooldown_duration)
        port.animation.apply_negative_afterglow(
            target_pet,
            now,
            amount=30.0,
            duration=afterglow_duration,
        )
        port.events.record_offer_event(
            item_kind,
            target_pet.name,
            target_pet.name,
            "hover_timeout_reaction",
            source="offer_hover",
        )
        port.scene.clear()
        return False

    def apply_offer_negative_afterglow(self, port, pet, now, amount=30.0, duration=5.0):
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

    def apply_offer_hover_timeout_stage(self, port, pet, stage, preserve=False):
        if pet is None or stage is None:
            return False
        pet.state = "move" if stage.purpose == "move" else "idle"
        context = ""
        if port.scene.current is not None:
            context = get_offer_hover_timeout_stage_context(
                getattr(port.scene.current, "hover_reaction_variant_label", ""),
                getattr(port.scene.current, "hover_reaction_stage_index", 0),
            )
        if port.animation.apply_context(
            pet,
            stage.purpose,
            context,
            [stage.mood_tag],
            preserve=preserve,
            ignore_mood_band=True,
        ):
            return True
        if port.animation.apply_candidates(
            pet,
            [(stage.purpose, stage.action_type)],
            [stage.mood_tag],
            preserve=preserve,
        ):
            return True
        return port.animation.apply_reaction(
            pet,
            [stage.mood_tag],
            preserve=preserve,
        )

    def apply_offer_hover_cursor_avoidance(self, port, pet):
        if pet is None:
            return False
        pet_center_x = pet.x() + (pet.width() / 2.0)
        cursor_x = float(port.hover.global_x or pet_center_x)
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
        port,
        item_kind,
        target_pet,
        now=None,
        choose_variant=None,
    ):
        if target_pet is None:
            return False
        if now is None:
            now = app_now()
        if port.pets.is_busy(target_pet, now):
            port.hover.clear(apply_miss=False)
            return False
        variants = get_offer_hover_reaction_variants(item_kind, target_pet.name)
        if not variants:
            return False
        if choose_variant is None:
            choose_variant = random.choice
        chosen_variant = choose_variant(list(variants))
        if not chosen_variant.stages:
            return False
        cursor_x = float(port.hover.global_x)
        cursor_y = float(port.hover.global_y)
        port.hover.clear(apply_miss=False)
        port.hover.global_x = cursor_x
        port.hover.global_y = cursor_y
        first_stage = chosen_variant.stages[0]
        total_duration = sum(float(stage.duration_seconds) for stage in chosen_variant.stages)
        scene_end = float(now) + max(0.2, total_duration)
        start_result = port.scene.start(
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
        return port.flow.update_hover_timeout_scene(float(now))

    def start_direct_offer_scene(
        self,
        port,
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
        start_result = port.scene.start(
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
        port.events.apply_mood_reward(target_pet.name)
        port.events.record_offer_event(
            item_kind,
            target_pet.name,
            target_pet.name,
            "direct_accept",
            source=source,
        )
        return True

    def update_offer_hover_preview(self, port, now):
        target_pet = port.pets.find_by_name(port.hover.target_name, visible_only=False)
        if target_pet is None or not target_pet.isVisible():
            port.hover.clear(apply_miss=False)
            return False
        if not self.pet_can_interact_with_offer_item(
            port,
            target_pet,
            port.hover.item_kind,
        ):
            port.hover.clear(apply_miss=False)
            return False
        if port.pets.is_busy(target_pet, now):
            port.hover.clear(apply_miss=False)
            return False
        if float(getattr(target_pet, "offer_hover_reaction_cooldown_until", 0.0) or 0.0) > float(now):
            port.hover.clear(apply_miss=False)
            return False
        preview_candidates = get_direct_offer_preview_candidates(port.hover.item_kind, target_pet.name)
        preferred_moods = get_direct_offer_preferred_moods(port.hover.item_kind)
        preview_context = get_direct_offer_preview_context(port.hover.item_kind, target_pet.name)
        if not preferred_moods or (not preview_candidates and not preview_context):
            port.hover.clear(apply_miss=False)
            return False
        if not port.hover.started_at:
            port.hover.started_at = float(now)
        hover_timeout_seconds = get_offer_hover_timeout_seconds(port.hover.item_kind)
        if (
            float(now) - float(port.hover.started_at) >= hover_timeout_seconds and
            get_offer_hover_reaction_variants(port.hover.item_kind, target_pet.name)
        ):
            return port.flow.start_hover_timeout_scene(port.hover.item_kind, target_pet, now=now)
        port.scene.lock_pet(target_pet, "hover_preview", now + 0.2)
        target_pet.state = "idle"
        target_center_x = target_pet.x() + (target_pet.width() / 2.0)
        target_pet.direction = -1 if port.hover.global_x < target_center_x else 1
        if not port.animation.apply_context(
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

    def update_offer_hover_timeout_reaction_scene(self, port, now):
        target_pet = port.pets.find_by_name(port.scene.current.target_name, visible_only=False)
        if target_pet is None:
            port.scene.clear()
            return False
        if port.pets.is_busy(target_pet, now):
            port.scene.clear()
            return False
        stages = tuple(getattr(port.scene.current, "hover_reaction_stages", ()) or ())
        if not stages:
            port.scene.clear()
            return False
        stage_index = int(getattr(port.scene.current, "hover_reaction_stage_index", 0) or 0)
        while stage_index < len(stages) and float(now) >= float(port.scene.current.stage_ends_at):
            stage_index += 1
            port.scene.current.stage_initialized = False
            port.scene.current.hover_reaction_stage_index = stage_index
            if stage_index < len(stages):
                port.scene.current.stage_ends_at = float(now) + float(stages[stage_index].duration_seconds)
        if stage_index >= len(stages) or float(now) >= float(port.scene.current.scene_ends_at):
            return port.flow.finalize_hover_timeout_failure(target_pet, now)
        stage = stages[stage_index]
        port.scene.refresh_locks(target_pet)
        target_pet.state = "move" if stage.purpose == "move" else "idle"
        pet_center_x = target_pet.x() + (target_pet.width() / 2.0)
        if port.scene.current.hover_reaction_avoid_cursor and stage.purpose == "move":
            target_pet.direction = 1 if pet_center_x >= port.hover.global_x else -1
        else:
            target_pet.direction = -1 if port.hover.global_x < pet_center_x else 1
        if not port.scene.current.stage_initialized:
            port.animation.apply_hover_timeout_stage(target_pet, stage, preserve=False)
            port.scene.current.stage_initialized = True
        else:
            port.animation.apply_hover_timeout_stage(target_pet, stage, preserve=True)
        if port.scene.current.hover_reaction_avoid_cursor and stage.purpose == "move":
            port.animation.apply_hover_cursor_avoidance(target_pet)
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

    def update_direct_offer_scene(self, port, now, roll_provider=None):
        target_pet = port.pets.find_by_name(port.scene.current.target_name, visible_only=False)
        if target_pet is None or now >= float(port.scene.current.scene_ends_at):
            port.scene.clear()
            return False
        port.scene.refresh_locks(target_pet)
        candidates = get_direct_offer_accept_candidates(port.scene.current.item_kind, target_pet.name)
        preferred_moods = get_direct_offer_preferred_moods(port.scene.current.item_kind)
        accept_context = get_direct_offer_accept_context(port.scene.current.item_kind, target_pet.name)
        purpose_order = tuple(getattr(port.scene.current, "direct_accept_purpose_order", ()) or ())
        if not purpose_order:
            if roll_provider is None:
                roll_provider = random.random
            purpose_order = tuple(
                get_direct_offer_accept_purpose_order(
                    port.scene.current.item_kind,
                    target_pet.name,
                    roll=roll_provider(),
                )
            )
            port.scene.current.direct_accept_purpose_order = purpose_order
        ordered_candidates = port.animation.order_candidates_by_purpose(candidates, purpose_order)
        if preferred_moods:
            if not port.animation.apply_contexts(
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
        port.animation.update_direct_accept_motion(
            target_pet,
            port.scene.current.item_kind,
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

    def update_deny_only_offer_scene(self, port, now):
        target_pet = port.pets.find_by_name(port.scene.current.target_name, visible_only=False)
        if target_pet is None or now >= float(port.scene.current.scene_ends_at):
            port.scene.clear()
            return False
        port.scene.refresh_locks(target_pet)
        target_pet.state = "idle"
        candidates = get_denied_offer_reaction_candidates(target_pet.name)
        preferred_moods = get_denied_offer_preferred_moods()
        denied_context = get_denied_offer_context(target_pet.name)
        if preferred_moods:
            if not port.animation.apply_context(
                target_pet,
                "idle",
                denied_context,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
                preserve=True,
                ignore_mood_band=True,
                ordered_preferences=True,
            ) and not port.animation.apply_candidates(
                target_pet,
                candidates,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
            ) and not port.animation.apply_reaction(
                target_pet,
                preferred_moods,
                forbidden=get_denied_offer_forbidden_moods(),
            ):
                target_pet.apply_reaction(preferred_moods, is_negative=True)
        target_pet.refresh_movement_state()
        return True
