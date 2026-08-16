from __future__ import annotations

from .activity_runtime_adapter import pet_has_active_activity
from .offer_interaction_rules import (
    ITEM_BOTTLE,
    OfferGuardianCandidate,
    can_pet_interact_with_offer_item,
    choose_honey_guardian,
    get_bottle_feed_holder_idle_candidates,
    get_bottle_feed_holder_idle_context,
    get_bottle_feed_holder_idle_preferred_moods,
    get_direct_offer_accept_candidates,
    get_direct_offer_accept_context,
    get_direct_offer_candidates,
    get_direct_offer_mobile_move_speed_scale,
    get_direct_offer_mobile_move_target_offset,
    get_direct_offer_preview_candidates,
    get_direct_offer_preview_context,
    get_direct_offer_preferred_moods,
    resolve_offer_hotspot_match,
    resolve_offer_preview_match,
)
from .pet_intent_rules import pet_has_sleep_join_intent
from .runtime import app_now
from .transformation_profiles import (
    CAPABILITY_HONEY_GUARDIAN,
    get_pet_form_key,
    pet_form_allows_capability,
    pet_form_allows_offer_item,
    pet_is_transformed,
    pet_is_transforming,
)


class OfferAnimationSupport:
    """Offer-specific manifest selection, hotspot and pet animation operations."""

    def __init__(
        self,
        *,
        pets,
        pet_registry,
        lock_pet_for_offer_scene,
        held_item_position_updater=None,
        now_provider=app_now,
    ):
        self.pets_list = pets
        self.pet_registry = pet_registry
        self.lock_pet_for_offer_scene = lock_pet_for_offer_scene
        self.held_item_position_updater = held_item_position_updater
        self.now_provider = now_provider

    def find_pet_by_name(self, pet_name, visible_only=False):
        return self.pet_registry.find_by_name(
            pet_name,
            visible_only=visible_only,
        )

    def pet_is_busy_for_offer_interaction(self, pet, now=None):
        if pet is None:
            return True
        if now is None:
            now = self.now_provider()
        is_under_care = getattr(pet, "is_under_care", None)
        care_locked = bool(is_under_care(now)) if callable(is_under_care) else False
        return bool(
            pet_is_transforming(pet)
            or pet_has_active_activity(pet)
            or pet_has_sleep_join_intent(pet)
            or getattr(pet, "dragging", False)
            or getattr(pet, "drag_press_pending", False)
            or getattr(pet, "flight_mode", "none") != "none"
            or getattr(pet, "care_mode", "none") != "none"
            or getattr(pet, "care_partner", None) is not None
            or getattr(pet, "is_hugging", False)
            or care_locked
        )

    def pet_can_interact_with_offer_item(self, pet, item_kind):
        return bool(
            pet is not None
            and pet_form_allows_offer_item(pet, item_kind)
            and can_pet_interact_with_offer_item(item_kind, pet.name)
        )

    def find_offer_drop_target(self, item_kind, global_pos):
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        matches = []
        for pet in self.pets_list:
            if not pet.isVisible():
                continue
            if self.pet_is_busy_for_offer_interaction(pet):
                continue
            if not self.pet_can_interact_with_offer_item(pet, item_kind):
                continue
            reference_frame = self.get_offer_reference_frame(
                pet,
                item_kind,
                prefer_preview=True,
            )
            frame_width = (
                reference_frame.width()
                if reference_frame is not None
                else pet.width()
            )
            frame_height = (
                reference_frame.height()
                if reference_frame is not None
                else pet.height()
            )
            match = resolve_offer_hotspot_match(
                item_kind=item_kind,
                pet_name=pet.name,
                widget_left=pet.x(),
                widget_top=pet.y(),
                widget_width=pet.width(),
                widget_height=pet.height(),
                frame_width=frame_width,
                frame_height=frame_height,
                render_scale=pet.get_effective_scale(),
                direction=pet.direction,
                original_face_left=pet.original_face_left,
                offer_global_x=global_x,
                offer_global_y=global_y,
            )
            if match.matched:
                matches.append((match.distance, pet))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def find_offer_hover_target(
        self,
        item_kind,
        global_pos,
        ignore_reaction_cooldown=False,
    ):
        global_x = float(global_pos.x())
        global_y = float(global_pos.y())
        now = self.now_provider()
        matches = []
        for pet in self.pets_list:
            if not pet.isVisible():
                continue
            if self.pet_is_busy_for_offer_interaction(pet, now):
                continue
            if not self.pet_can_interact_with_offer_item(pet, item_kind):
                continue
            if (
                not ignore_reaction_cooldown
                and float(
                    getattr(
                        pet,
                        "offer_hover_reaction_cooldown_until",
                        0.0,
                    )
                    or 0.0
                )
                > float(now)
            ):
                continue
            reference_frame = self.get_offer_reference_frame(
                pet,
                item_kind,
                prefer_preview=True,
            )
            frame_width = (
                reference_frame.width()
                if reference_frame is not None
                else pet.width()
            )
            frame_height = (
                reference_frame.height()
                if reference_frame is not None
                else pet.height()
            )
            match = resolve_offer_preview_match(
                widget_left=pet.x(),
                widget_top=pet.y(),
                widget_width=pet.width(),
                widget_height=pet.height(),
                frame_width=frame_width,
                frame_height=frame_height,
                offer_global_x=global_x,
                offer_global_y=global_y,
            )
            if match.matched:
                matches.append((match.distance, pet))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def get_offer_reference_frame(self, pet, item_kind, prefer_preview=False):
        if not self.pet_can_interact_with_offer_item(pet, item_kind):
            return None
        context = (
            get_direct_offer_preview_context(item_kind, pet.name)
            if prefer_preview
            else get_direct_offer_accept_context(item_kind, pet.name)
        )
        preferred_moods = get_direct_offer_preferred_moods(item_kind)
        context_candidate = self.get_offer_reference_frame_for_context(
            pet,
            context,
            preferred_moods,
        )
        if context_candidate is not None:
            return context_candidate
        candidates = (
            get_direct_offer_preview_candidates(item_kind, pet.name)
            if prefer_preview
            else get_direct_offer_accept_candidates(item_kind, pet.name)
        )
        if not candidates:
            candidates = get_direct_offer_candidates(item_kind, pet.name)
        current_candidate_keys = set(candidates)
        if (
            getattr(pet, "current_frames", None)
            and (
                getattr(pet, "current_purpose", ""),
                getattr(pet, "current_action_tag", ""),
            )
            in current_candidate_keys
        ):
            return pet.current_frames[0]
        for purpose, action_type in candidates:
            preferred_result = (
                pet.asset_manager.get_frames_for_action_by_preferences(
                    purpose,
                    action_type,
                    preferred_moods,
                    mood_score=pet.mood_score,
                )
            )
            if preferred_result and preferred_result[0]:
                return preferred_result[0][0]
            by_score_result = pet.asset_manager.get_frames_for_action_by_score(
                purpose,
                action_type,
                pet.mood_score,
                is_adult=pet.is_adult,
            )
            if by_score_result and by_score_result[0]:
                return by_score_result[0][0]
        if getattr(pet, "current_frames", None):
            frame_index = min(
                int(getattr(pet, "frame_index", 0) or 0),
                len(pet.current_frames) - 1,
            )
            return pet.current_frames[frame_index]
        return None

    def get_offer_reference_frame_for_context(
        self,
        pet,
        context,
        preferred_moods,
    ):
        if not context:
            return None
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return None
        current_frames = getattr(pet, "current_frames", None)
        current_purpose = getattr(pet, "current_purpose", "")
        current_action = getattr(pet, "current_action_tag", "")
        current_mood = getattr(pet, "current_mood_tag", "")
        get_specific_frames = getattr(asset_manager, "get_specific_frames", None)
        if current_frames and callable(get_specific_frames):
            frames = get_specific_frames(
                current_purpose,
                current_action,
                current_mood,
                mood_score=None,
                context=context,
            )
            if frames:
                frame_index = min(
                    int(getattr(pet, "frame_index", 0) or 0),
                    len(current_frames) - 1,
                )
                return current_frames[frame_index]
        get_contextual_result = getattr(
            asset_manager,
            "get_contextual_result",
            None,
        )
        for purpose in ("idle", "move"):
            if not callable(get_contextual_result):
                continue
            result = get_contextual_result(
                purpose,
                context=context,
                preferred_moods=preferred_moods,
                mood_score=getattr(pet, "mood_score", None),
                ordered_preferences=True,
            )
            if result and result[0]:
                return result[0][0]
        return None

    def get_offer_hotspot_global_position(
        self,
        pet,
        item_kind,
        prefer_preview=False,
    ):
        reference_frame = self.get_offer_reference_frame(
            pet,
            item_kind,
            prefer_preview=prefer_preview,
        )
        frame_width = (
            reference_frame.width()
            if reference_frame is not None
            else pet.width()
        )
        frame_height = (
            reference_frame.height()
            if reference_frame is not None
            else pet.height()
        )
        match = resolve_offer_hotspot_match(
            item_kind=item_kind,
            pet_name=pet.name,
            widget_left=pet.x(),
            widget_top=pet.y(),
            widget_width=pet.width(),
            widget_height=pet.height(),
            frame_width=frame_width,
            frame_height=frame_height,
            render_scale=pet.get_effective_scale(),
            direction=pet.direction,
            original_face_left=pet.original_face_left,
            offer_global_x=0.0,
            offer_global_y=0.0,
            form_key=get_pet_form_key(pet),
        )
        return match.hotspot_global_x, match.hotspot_global_y

    def update_held_offer_widget_position(
        self,
        widget,
        pet,
        item_kind,
        prefer_preview=False,
    ):
        if widget is None or pet is None:
            return
        hotspot_x, hotspot_y = self.get_offer_hotspot_global_position(
            pet,
            item_kind,
            prefer_preview=prefer_preview,
        )
        widget.move_to(
            hotspot_x - (widget.width() / 2.0),
            hotspot_y - (widget.height() / 2.0),
        )
        widget.show()
        widget.raise_()

    def choose_honey_guardian_for_child(self, child_pet):
        candidate_names = ["Symboli Rudolf", "Sirius Symboli"]
        transformed_teio = self.find_pet_by_name(
            "Tokai Teio",
            visible_only=True,
        )
        if (
            getattr(child_pet, "name", "") == "Tsurumaru Tsuyoshi"
            and transformed_teio is not None
            and pet_is_transformed(transformed_teio)
        ):
            candidate_names.append("Tokai Teio")
        candidates = []
        for candidate_name in candidate_names:
            guardian = self.find_pet_by_name(
                candidate_name,
                visible_only=True,
            )
            allowed = bool(
                guardian is not None
                and guardian is not child_pet
                and pet_form_allows_capability(
                    guardian,
                    CAPABILITY_HONEY_GUARDIAN,
                )
            )
            candidates.append(
                OfferGuardianCandidate(
                    name=candidate_name,
                    distance=(
                        guardian.distance_to(child_pet)
                        if allowed
                        else 999999.0
                    ),
                    is_visible=allowed,
                )
            )
        return choose_honey_guardian(candidates)

    def choose_bottle_feed_child_for_holder(self, holder_pet, now=None):
        if holder_pet is None or holder_pet.name == "Tsurumaru Tsuyoshi":
            return None
        now = self.now_provider() if now is None else float(now)
        child_pet = self.find_pet_by_name(
            "Tsurumaru Tsuyoshi",
            visible_only=True,
        )
        if child_pet is None or child_pet is holder_pet:
            return None
        if (
            child_pet.dragging
            or child_pet.is_offer_locked(now)
            or self.pet_is_busy_for_offer_interaction(child_pet, now)
        ):
            return None
        return child_pet

    def interrupt_pet_window_motion_for_offer(self, pet):
        if pet is None:
            return
        if getattr(pet, "flight_mode", "none") != "none":
            stop_window_flight = getattr(pet, "stop_window_flight", None)
            if callable(stop_window_flight):
                stop_window_flight(apply_cooldown=False)
        if getattr(pet, "perched_window_hwnd", 0):
            detach = getattr(pet, "detach_from_window_surface", None)
            if callable(detach):
                detach()
        pet.vy = 0
        if hasattr(pet, "fall_origin_y"):
            pet.fall_origin_y = None
        pet.state_timer = 0
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        pet.refresh_movement_state()

    def pet_is_window_transitioning_for_offer(self, pet):
        if pet is None:
            return False
        return getattr(pet, "flight_mode", "none") != "none"

    def prepare_pet_window_state_for_offer(self, pet):
        if pet is None:
            return False
        if self.pet_is_window_transitioning_for_offer(pet):
            return True
        if getattr(pet, "perched_window_hwnd", 0):
            detach = getattr(pet, "detach_from_window_surface", None)
            if callable(detach):
                detach()
            pet.vy = 0
            if hasattr(pet, "fall_origin_y"):
                pet.fall_origin_y = None
            pet.state_timer = 0
            refresh = getattr(pet, "refresh_movement_state", None)
            if callable(refresh):
                refresh()
            return True
        return False

    def reset_offer_scene_pet_motion(self, pet):
        pet.state = "idle"
        pet.state_timer = 0
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        pet.refresh_movement_state()

    def scene_animation_matches_preferences(
        self,
        pet,
        candidates,
        preferred_moods,
        forbidden=None,
    ):
        forbidden = set(forbidden or ())
        if getattr(pet, "current_mood_tag", "") in forbidden:
            return False
        if getattr(pet, "current_mood_tag", "") not in set(
            preferred_moods or ()
        ):
            return False
        return (
            getattr(pet, "current_purpose", ""),
            getattr(pet, "current_action_tag", ""),
        ) in set(candidates or ())

    def apply_scene_context_with_preferences(
        self,
        pet,
        purpose,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        if pet is None or not context:
            return False
        changer = getattr(
            pet,
            "change_state_for_context_with_preferences",
            None,
        )
        if not callable(changer):
            return False
        return bool(
            changer(
                purpose,
                context,
                preferred_moods=preferred_moods,
                forbidden=forbidden,
                preserve=preserve,
                ignore_mood_band=ignore_mood_band,
            )
        )

    def apply_scene_contexts_with_preferences(
        self,
        pet,
        purposes,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        for purpose in purposes:
            if self.apply_scene_context_with_preferences(
                pet,
                purpose,
                context,
                preferred_moods=preferred_moods,
                forbidden=forbidden,
                preserve=preserve,
                ignore_mood_band=ignore_mood_band,
            ):
                return True
        return False

    def order_candidates_by_purpose(self, candidates, purpose_order):
        candidate_list = list(candidates or ())
        purpose_order = list(purpose_order or ())
        if not purpose_order:
            return candidate_list
        ordered = []
        seen = set()
        for purpose in purpose_order:
            for candidate in candidate_list:
                if candidate in seen:
                    continue
                if candidate[0] == purpose:
                    ordered.append(candidate)
                    seen.add(candidate)
        for candidate in candidate_list:
            if candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        return ordered

    def current_direct_offer_accept_is_mobile(
        self,
        pet,
        item_kind,
        accept_context,
        candidates,
    ):
        if pet is None or getattr(pet, "current_purpose", "") != "move":
            return False
        current_action = getattr(pet, "current_action_tag", "")
        if ("move", current_action) in set(candidates or ()):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        get_specific_frames = getattr(asset_manager, "get_specific_frames", None)
        if callable(get_specific_frames):
            frames = get_specific_frames(
                getattr(pet, "current_purpose", ""),
                current_action,
                getattr(pet, "current_mood_tag", ""),
                mood_score=getattr(pet, "mood_score", None),
                context=accept_context,
            )
            if frames:
                return True
        return bool(current_action and current_action == accept_context)

    def update_direct_offer_accept_motion(
        self,
        pet,
        item_kind,
        accept_context,
        candidates,
    ):
        if not self.current_direct_offer_accept_is_mobile(
            pet,
            item_kind,
            accept_context,
            candidates,
        ):
            self.reset_offer_scene_pet_motion(pet)
            return False
        pet.state = "move"
        pet.state_timer = max(
            int(getattr(pet, "state_timer", 0) or 0),
            1,
        )
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        direction = -1 if getattr(pet, "direction", 1) < 0 else 1
        target_x = pet.x() + (
            direction
            * get_direct_offer_mobile_move_target_offset(item_kind, pet.name)
        )
        mover = getattr(pet, "move_toward_x", None)
        if callable(mover):
            mover(
                target_x,
                speed_scale=get_direct_offer_mobile_move_speed_scale(
                    item_kind,
                    pet.name,
                ),
                min_speed=1.0,
            )
        else:
            move_logic = getattr(pet, "move_logic", None)
            if callable(move_logic):
                move_logic()
            else:
                pet.refresh_movement_state()
        return True

    def apply_scene_candidates_with_preferences(
        self,
        pet,
        candidates,
        preferred_moods,
        forbidden=None,
        preserve=False,
    ):
        candidate_list = list(candidates or ())
        preferred = list(preferred_moods or ())
        forbidden = set(forbidden or ())
        if preserve and self.scene_animation_matches_preferences(
            pet,
            candidate_list,
            preferred,
            forbidden=forbidden,
        ):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return False
        for mood_tag in preferred:
            if mood_tag in forbidden:
                continue
            weighted_matches = []
            for purpose, action_type in candidate_list:
                record = asset_manager.get_record(
                    purpose,
                    action_type,
                    mood_tag,
                )
                frames = record.get("frames") if record else None
                if frames:
                    weighted_matches.append(
                        (
                            frames,
                            purpose,
                            action_type,
                            mood_tag,
                            asset_manager.get_record_weight(record),
                        )
                    )
            if weighted_matches:
                chosen = asset_manager.choose_weighted_result(
                    [
                        (frames, (purpose, action_type), mood_tag, weight)
                        for frames, purpose, action_type, mood_tag, weight
                        in weighted_matches
                    ]
                )
                if chosen:
                    frames, purpose_action, chosen_mood = chosen
                    purpose, action_type = purpose_action
                    if pet.apply_animation_result(
                        purpose,
                        (frames, action_type, chosen_mood),
                    ):
                        pet.state = (
                            purpose if purpose in {"idle", "move"} else "idle"
                        )
                        return True
        for purpose, action_type in candidate_list:
            result = asset_manager.get_frames_for_action_by_preferences(
                purpose,
                action_type,
                preferred,
                forbidden=list(forbidden),
                mood_score=None,
            )
            if pet.apply_animation_result(purpose, result):
                pet.state = purpose if purpose in {"idle", "move"} else "idle"
                return True
        return False

    def apply_scene_reaction_with_preferences(
        self,
        pet,
        preferred_moods,
        forbidden=None,
        preserve=False,
    ):
        preferred = list(preferred_moods or ())
        forbidden = set(forbidden or ())
        if (
            preserve
            and getattr(pet, "current_purpose", "") == "idle"
            and getattr(pet, "current_mood_tag", "") in preferred
            and getattr(pet, "current_mood_tag", "") not in forbidden
        ):
            return True
        asset_manager = getattr(pet, "asset_manager", None)
        if asset_manager is None:
            return False
        result = asset_manager.get_safe_reaction_result(
            "idle",
            preferred,
            forbidden=list(forbidden),
        )
        if pet.apply_animation_result("idle", result):
            pet.state = "idle"
            return True
        return False

    def apply_held_item_behavior(self, pet, now):
        item_kind = getattr(pet, "held_item_kind", "")
        if not item_kind:
            return False
        preview_candidates = get_direct_offer_preview_candidates(
            item_kind,
            pet.name,
        )
        preferred_moods = get_direct_offer_preferred_moods(item_kind)
        manifest_context = get_direct_offer_preview_context(
            item_kind,
            pet.name,
        )
        if item_kind == ITEM_BOTTLE and pet.name != "Tsurumaru Tsuyoshi":
            preview_candidates = (
                get_bottle_feed_holder_idle_candidates(pet.name)
                or preview_candidates
            )
            preferred_moods = (
                get_bottle_feed_holder_idle_preferred_moods()
                or preferred_moods
            )
            manifest_context = get_bottle_feed_holder_idle_context(pet.name)
        self.lock_pet_for_offer_scene(pet, "held_item", now + 0.2)
        pet.state = "idle"
        if preview_candidates and preferred_moods:
            if not self.apply_scene_context_with_preferences(
                pet,
                "idle",
                manifest_context,
                preferred_moods,
                preserve=True,
            ) and not pet.ensure_candidate_animation_with_preferences(
                preview_candidates,
                preferred_moods,
            ):
                pet.ensure_candidate_animation(preview_candidates)
        pet.perception_situation_tag = "locked"
        pet.expression_animation_context = "ambient"
        pet.expression_relation_overlay = "none"
        pet.expression_focus_target_name = ""
        pet.expression_posture_bias = "neutral"
        pet.expression_spacing_bias = "neutral"
        pet.expression_look_at_target = False
        pet.relationship_focus_target_name = ""
        pet.refresh_movement_state()
        if self.held_item_position_updater is not None:
            self.held_item_position_updater(
                pet.held_item_widget,
                pet,
                item_kind,
                prefer_preview=True,
            )
        else:
            self.update_held_offer_widget_position(
                pet.held_item_widget,
                pet,
                item_kind,
                prefer_preview=True,
            )
        return True
