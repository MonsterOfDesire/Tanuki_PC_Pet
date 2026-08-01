from __future__ import annotations

import os
import random
from dataclasses import dataclass

from .activity_runtime_adapter import pet_has_active_activity
from .asset_manager import AssetManager
from .pet_intent_rules import pet_has_sleep_join_intent
from .transformation_profiles import (
    apply_pet_form_mood_floor,
    get_transformation_profile,
)
from .transformation_rules import (
    AUTO_ACTION_CLEANUP_PREVIEW,
    AUTO_ACTION_END,
    AUTO_ACTION_SCHEDULE,
    AUTO_ACTION_SCHEDULE_MANUAL_END,
    AUTO_ACTION_START,
    TRANSFORMATION_AUTO_END_RETRY_SECONDS,
    TRANSFORMATION_AUTO_START_RETRY_SECONDS,
    TRANSFORMATION_AUTO_WORLD_MODE,
    TRANSFORMATION_AUTO_WORLD_MODES,
    TRANSFORMATION_PHASE_SECONDS,
    TransformationAutoSnapshot,
    TransformationEligibilitySnapshot,
    compute_transformation_whiteness,
    decide_auto_transformation,
    evaluate_transformation_eligibility,
)
from .transformation_state import (
    FORM_BASE,
    FORM_TRANSFORMED,
    TRANSFORMATION_PHASE_REVEALING,
    TRANSFORMATION_PHASE_WHITENING,
)


@dataclass(frozen=True)
class TransformationRuntimeResult:
    handled: bool
    reason: str = ""
    character_name: str = ""
    current_form: str = FORM_BASE
    target_form: str = ""
    started: bool = False
    completed: bool = False
    queued: bool = False
    source: str = ""


class TransformationExecutor:
    def __init__(
        self,
        *,
        phase_seconds: float = TRANSFORMATION_PHASE_SECONDS,
        asset_manager_factory=AssetManager,
        random_source=random,
    ):
        self.phase_seconds = max(0.05, float(phase_seconds))
        self.asset_manager_factory = asset_manager_factory
        self.random_source = random_source
        self._pending_assets: dict[str, tuple[object, tuple]] = {}

    def toggle(
        self,
        pet,
        *,
        now: float,
        source: str = "settings_preview",
        intent_now: float | None = None,
    ) -> TransformationRuntimeResult:
        if pet is None:
            return TransformationRuntimeResult(False, "participant_unavailable")
        name = str(getattr(pet, "name", "") or "")
        profile = get_transformation_profile(name)
        state = getattr(pet, "transformation_state", None)
        if state is None:
            return TransformationRuntimeResult(False, "missing_transformation_state", character_name=name)
        decision = evaluate_transformation_eligibility(
            TransformationEligibilitySnapshot(
                character_name=name,
                supported=profile is not None,
                current_form=state.current_form,
                transitioning=state.active,
                visible=bool(pet.isVisible()),
                user_visible=bool(getattr(pet, "user_visible", True)),
                dragging=bool(
                    getattr(pet, "dragging", False)
                    or getattr(pet, "drag_press_pending", False)
                ),
                active_activity=bool(pet_has_active_activity(pet) or pet_has_sleep_join_intent(pet)),
                offer_busy=bool(getattr(pet, "offer_scene_kind", "none") != "none"),
                care_busy=bool(
                    getattr(pet, "care_mode", "none") != "none"
                    or getattr(pet, "care_partner", None) is not None
                    or getattr(pet, "is_hugging", False)
                ),
                social_busy=bool(getattr(pet, "social_mode", "none") != "none"),
                recovering=bool(getattr(pet, "is_recovering", False)),
                angry_locked=bool(getattr(pet, "is_angry_locked", False)),
                held_item=bool(getattr(pet, "held_item_kind", "")),
                vertical_velocity=float(getattr(pet, "vy", 0.0) or 0.0),
                flight_mode=str(getattr(pet, "flight_mode", "none") or "none"),
                perched=bool(getattr(pet, "perched_window_hwnd", 0)),
            )
        )
        if not decision.allowed:
            return TransformationRuntimeResult(
                False,
                decision.reason,
                character_name=name,
                current_form=state.current_form,
                target_form=decision.target_form,
            )

        target_path = self._target_path(pet, profile, decision.target_form)
        if not os.path.isdir(target_path):
            return TransformationRuntimeResult(
                False,
                "asset_directory_missing",
                character_name=name,
                current_form=state.current_form,
                target_form=decision.target_form,
            )
        try:
            manager = self._build_asset_manager(pet, target_path)
            initial_result = manager.get_contextual_result_for_any_purpose(
                context="random",
                mood_score=max(50.0, float(getattr(pet, "mood_score", 60.0))),
                ordered_preferences=True,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return TransformationRuntimeResult(
                False,
                f"asset_load_failed:{exc}",
                character_name=name,
                current_form=state.current_form,
                target_form=decision.target_form,
            )
        if not initial_result:
            return TransformationRuntimeResult(
                False,
                "capability_unavailable:random",
                character_name=name,
                current_form=state.current_form,
                target_form=decision.target_form,
            )

        clear_observe = getattr(pet, "clear_observe_intent", None)
        if callable(clear_observe):
            clear_observe(
                now=float(now if intent_now is None else intent_now),
                allow_social_log_event=False,
            )
        pet.state = "idle"
        pet.state_timer = 0
        reset_stationary = getattr(pet, "reset_stationary_move_mode", None)
        if callable(reset_stationary):
            reset_stationary()
        state.begin(
            target_form=decision.target_form,
            now=float(now),
            source=source,
        )
        self._pending_assets[name] = (manager, initial_result)
        pet.update()
        return TransformationRuntimeResult(
            True,
            character_name=name,
            current_form=state.current_form,
            target_form=decision.target_form,
            started=True,
            source=source,
        )

    def update_auto(
        self,
        pets,
        *,
        world_mode: str,
        sim_now: float,
        transition_now: float,
    ) -> tuple[TransformationRuntimeResult, ...]:
        results = []
        for pet in tuple(pets or ()):
            profile = get_transformation_profile(
                getattr(pet, "name", "")
            )
            state = getattr(pet, "transformation_state", None)
            if profile is None or state is None:
                continue
            manual_result = self._update_manual_end_request(
                pet,
                state=state,
                sim_now=float(sim_now),
                transition_now=float(transition_now),
            )
            if manual_result is not None:
                if manual_result.handled:
                    results.append(manual_result)
                continue
            decision = decide_auto_transformation(
                TransformationAutoSnapshot(
                    world_mode=str(world_mode or ""),
                    current_form=state.current_form,
                    transitioning=state.active,
                    auto_session=state.auto_session,
                    mood_score=float(
                        getattr(pet, "mood_score", 0.0) or 0.0
                    ),
                    now=float(sim_now),
                    next_attempt_at=state.auto_next_attempt_at,
                    form_expires_at=state.auto_form_expires_at,
                    retry_at=state.auto_retry_at,
                )
            )
            if decision.action == AUTO_ACTION_SCHEDULE:
                state.auto_next_attempt_at = float(sim_now) + self._uniform(
                    profile.auto_base_seconds_min,
                    profile.auto_base_seconds_max,
                )
                state.auto_retry_at = 0.0
                continue
            if decision.action == AUTO_ACTION_SCHEDULE_MANUAL_END:
                state.auto_form_expires_at = (
                    float(sim_now)
                    + self._uniform(
                        profile.auto_duration_seconds_min,
                        profile.auto_duration_seconds_max,
                    )
                )
                state.auto_retry_at = 0.0
                continue
            if decision.action == AUTO_ACTION_START:
                auto_source = (
                    "autonomous_start"
                    if str(world_mode or "")
                    == TRANSFORMATION_AUTO_WORLD_MODE
                    else "sandbox_autonomous_start"
                )
                result = self.toggle(
                    pet,
                    now=float(transition_now),
                    intent_now=float(sim_now),
                    source=auto_source,
                )
                if result.started:
                    state.auto_session = True
                    state.auto_world_mode = str(world_mode or "")
                    state.auto_next_attempt_at = 0.0
                    state.auto_retry_at = 0.0
                    state.auto_form_expires_at = (
                        float(sim_now)
                        + self._uniform(
                            profile.auto_duration_seconds_min,
                            profile.auto_duration_seconds_max,
                        )
                    )
                else:
                    state.auto_retry_at = (
                        float(sim_now)
                        + TRANSFORMATION_AUTO_START_RETRY_SECONDS
                    )
                results.append(result)
                continue
            if decision.action in {
                AUTO_ACTION_END,
                AUTO_ACTION_CLEANUP_PREVIEW,
            }:
                source = (
                    "settings_preview_timeout"
                    if decision.reason == "manual_duration_complete"
                    else "autonomous_end"
                    if (
                        state.auto_session
                        and state.auto_world_mode
                        == TRANSFORMATION_AUTO_WORLD_MODE
                    )
                    else "sandbox_autonomous_end"
                    if state.auto_session
                    else "world_mode_cleanup"
                )
                result = self.toggle(
                    pet,
                    now=float(transition_now),
                    intent_now=float(sim_now),
                    source=source,
                )
                if result.started:
                    state.auto_session = False
                    state.auto_world_mode = ""
                    state.auto_form_expires_at = 0.0
                    state.auto_retry_at = 0.0
                    state.auto_next_attempt_at = 0.0
                else:
                    state.auto_retry_at = (
                        float(sim_now)
                        + TRANSFORMATION_AUTO_END_RETRY_SECONDS
                    )
                results.append(result)
                continue
            if decision.reason == "mood_not_normal":
                state.auto_retry_at = (
                    float(sim_now)
                    + TRANSFORMATION_AUTO_START_RETRY_SECONDS
                )
            elif decision.reason == "auto_disabled" and (
                state.current_form == FORM_BASE
            ):
                state.auto_next_attempt_at = 0.0
                state.auto_retry_at = 0.0
        return tuple(results)

    def request_manual_toggle(
        self,
        pet,
        *,
        now: float,
        intent_now: float,
    ) -> TransformationRuntimeResult:
        state = getattr(pet, "transformation_state", None)
        if state is None:
            return self.toggle(
                pet,
                now=float(now),
                intent_now=float(intent_now),
                source="settings_preview",
            )
        ending_auto_source = (
            "autonomous_end"
            if (
                state.current_form == FORM_TRANSFORMED
                and state.auto_session
                and state.auto_world_mode
                == TRANSFORMATION_AUTO_WORLD_MODE
            )
            else "settings_preview"
        )
        result = self.toggle(
            pet,
            now=float(now),
            intent_now=float(intent_now),
            source=ending_auto_source,
        )
        if result.started:
            self._release_auto_session_for_manual_toggle(
                state,
            )
            if result.target_form == FORM_TRANSFORMED:
                profile = get_transformation_profile(
                    getattr(pet, "name", "")
                )
                if profile is not None:
                    state.auto_form_expires_at = (
                        float(intent_now)
                        + self._uniform(
                            profile.auto_duration_seconds_min,
                            profile.auto_duration_seconds_max,
                        )
                    )
            return result
        if (
            state.current_form == FORM_TRANSFORMED
            and result.reason in {
                "participant_owned",
                "participant_dragging",
                "participant_offer_busy",
                "participant_care_busy",
                "participant_social_busy",
                "participant_recovering",
                "airborne",
            }
        ):
            state.manual_end_requested = True
            state.auto_retry_at = (
                float(intent_now)
                + TRANSFORMATION_AUTO_END_RETRY_SECONDS
            )
            return TransformationRuntimeResult(
                True,
                reason="manual_end_queued",
                character_name=result.character_name,
                current_form=result.current_form,
                target_form=FORM_BASE,
                queued=True,
                source=ending_auto_source,
            )
        return result

    def update(self, pets, *, now: float) -> tuple[TransformationRuntimeResult, ...]:
        results = []
        for pet in tuple(pets or ()):
            result = self.update_pet(pet, now=now)
            if result.handled:
                results.append(result)
        return tuple(results)

    def update_pet(self, pet, *, now: float) -> TransformationRuntimeResult:
        state = getattr(pet, "transformation_state", None)
        if state is None or not state.active:
            return TransformationRuntimeResult(False, "transition_inactive")
        name = str(getattr(pet, "name", "") or "")
        elapsed = max(0.0, float(now) - float(state.phase_started_at))
        whiteness, phase_complete = compute_transformation_whiteness(
            state.phase,
            elapsed_seconds=elapsed,
            phase_seconds=self.phase_seconds,
        )
        state.whiteness = whiteness
        pet.update()
        if not phase_complete:
            return TransformationRuntimeResult(
                True,
                character_name=name,
                current_form=state.current_form,
                target_form=state.target_form,
                source=state.source,
            )

        if state.phase == TRANSFORMATION_PHASE_WHITENING:
            if not self._swap_form_assets(pet):
                self.cancel_pet(pet, reason="asset_swap_failed")
                return TransformationRuntimeResult(
                    False,
                    "asset_swap_failed",
                    character_name=name,
                    current_form=state.current_form,
                )
            state.begin_reveal(now=float(now))
            pet.update()
            return TransformationRuntimeResult(
                True,
                character_name=name,
                current_form=state.current_form,
                target_form=state.target_form,
                source=state.source,
            )

        if state.phase == TRANSFORMATION_PHASE_REVEALING:
            current_form = state.current_form
            target_form = state.target_form
            source = state.source
            state.finish()
            pet.update()
            return TransformationRuntimeResult(
                True,
                character_name=name,
                current_form=current_form,
                target_form=target_form,
                completed=True,
                source=source,
            )
        return TransformationRuntimeResult(False, "unknown_transition_phase")

    def cancel_pet(self, pet, *, reason: str = "canceled") -> TransformationRuntimeResult:
        if pet is None:
            return TransformationRuntimeResult(False, reason)
        name = str(getattr(pet, "name", "") or "")
        self._pending_assets.pop(name, None)
        state = getattr(pet, "transformation_state", None)
        if state is not None:
            state.finish()
        pet.update()
        return TransformationRuntimeResult(
            True,
            reason,
            character_name=name,
            current_form=str(getattr(state, "current_form", FORM_BASE) or FORM_BASE),
        )

    def is_transition_active(self, pet) -> bool:
        state = getattr(pet, "transformation_state", None)
        return bool(state is not None and state.active)

    def _uniform(self, lower: float, upper: float) -> float:
        return float(self.random_source.uniform(float(lower), float(upper)))

    def _update_manual_end_request(
        self,
        pet,
        *,
        state,
        sim_now: float,
        transition_now: float,
    ) -> TransformationRuntimeResult | None:
        if not state.manual_end_requested:
            return None
        if state.current_form != FORM_TRANSFORMED:
            state.manual_end_requested = False
            return None
        if state.active or float(sim_now) < float(
            state.auto_retry_at or 0.0
        ):
            return TransformationRuntimeResult(
                False,
                reason="manual_end_wait",
                character_name=str(getattr(pet, "name", "") or ""),
                current_form=state.current_form,
                target_form=FORM_BASE,
                queued=True,
            )
        source = (
            "autonomous_end"
            if (
                state.auto_session
                and state.auto_world_mode
                == TRANSFORMATION_AUTO_WORLD_MODE
            )
            else "settings_preview_queued"
        )
        result = self.toggle(
            pet,
            now=float(transition_now),
            intent_now=float(sim_now),
            source=source,
        )
        if result.started:
            self._release_auto_session_for_manual_toggle(state)
        else:
            state.auto_retry_at = (
                float(sim_now)
                + TRANSFORMATION_AUTO_END_RETRY_SECONDS
            )
        return result

    @staticmethod
    def _release_auto_session_for_manual_toggle(state) -> None:
        state.manual_end_requested = False
        state.auto_session = False
        state.auto_world_mode = ""
        state.auto_next_attempt_at = 0.0
        state.auto_form_expires_at = 0.0
        state.auto_retry_at = 0.0

    def _target_path(self, pet, profile, target_form: str) -> str:
        base_path = str(
            getattr(pet, "base_character_path", "")
            or getattr(pet, "character_path", "")
        )
        if target_form == FORM_TRANSFORMED:
            return os.path.join(base_path, profile.transformed_subdirectory)
        return base_path

    def _build_asset_manager(self, pet, target_path: str):
        current = getattr(pet, "asset_manager", None)
        return self.asset_manager_factory(
            target_path,
            scale_factor=float(pet.get_effective_scale()),
            frame_cache=getattr(current, "frame_cache", None),
            store_cache=getattr(current, "store_cache", None),
        )

    def _swap_form_assets(self, pet) -> bool:
        name = str(getattr(pet, "name", "") or "")
        pending = self._pending_assets.pop(name, None)
        state = getattr(pet, "transformation_state", None)
        if pending is None or state is None or not state.target_form:
            return False
        manager, initial_result = pending
        pet.asset_manager = manager
        state.current_form = state.target_form
        pet.current_frames = []
        pet.frame_index = 0
        pet.mood_score = apply_pet_form_mood_floor(
            pet,
            float(getattr(pet, "mood_score", 60.0)),
        )
        sync_mood = getattr(pet, "sync_mood_state_with_score", None)
        if callable(sync_mood):
            sync_mood()
        frames, purpose, action_type, mood_tag = initial_result
        if not pet.apply_animation_result(
            purpose,
            (frames, action_type, mood_tag),
        ):
            return False
        pet.state = "move" if purpose == "move" else "idle"
        pet.state_timer = 0
        refresh = getattr(pet, "refresh_movement_state", None)
        if callable(refresh):
            refresh()
        return True
