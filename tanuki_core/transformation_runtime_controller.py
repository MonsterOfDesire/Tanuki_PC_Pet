from __future__ import annotations

import time

from .runtime import app_now
from .transformation_executor import (
    TransformationExecutor,
    TransformationRuntimeResult,
)
from .transformation_tendency import TransformationTendencyCoordinator


TRANSFORMATION_EVENT_DISPLAY_NAMES = {
    "Tokai Teio": "帝寶",
    "Symboli Rudolf": "魯道夫",
}


class TransformationRuntimeController:
    """Owns transformation lifecycle without depending on the app façade."""

    def __init__(
        self,
        *,
        executor,
        tendency_coordinator,
        achievement_runtime_coordinator,
        pets,
        pet_registry,
        world_mode_provider,
        household_pressure_provider,
        record_household_event,
        refresh_household_summary=None,
        transition_now_provider=time.perf_counter,
        sim_now_provider=app_now,
    ):
        self.executor = executor
        self.tendency_coordinator = tendency_coordinator
        self.achievement_runtime_coordinator = (
            achievement_runtime_coordinator
        )
        self.pets = pets
        self.pet_registry = pet_registry
        self.world_mode_provider = world_mode_provider
        self.household_pressure_provider = household_pressure_provider
        self.record_household_event = record_household_event
        self.refresh_household_summary = refresh_household_summary
        self.transition_now_provider = transition_now_provider
        self.sim_now_provider = sim_now_provider

    @classmethod
    def create_default(cls, **kwargs):
        return cls(
            executor=TransformationExecutor(),
            tendency_coordinator=TransformationTendencyCoordinator(),
            **kwargs,
        )

    def toggle_preview(self, pet_name, now=None):
        if self.world_mode_provider() != "sandbox":
            return TransformationRuntimeResult(
                False,
                "preview_requires_sandbox",
                character_name=str(pet_name or ""),
            )
        transition_now = (
            self.transition_now_provider()
            if now is None
            else float(now)
        )
        return self.executor.request_manual_toggle(
            self.pet_registry.find_by_name(
                str(pet_name or ""),
                visible_only=False,
            ),
            now=transition_now,
            intent_now=(
                self.sim_now_provider()
                if now is None
                else float(now)
            ),
        )

    def get_preview_state(self, pet_name):
        pet = self.pet_registry.find_by_name(
            str(pet_name or ""),
            visible_only=False,
        )
        state = getattr(pet, "transformation_state", None)
        return {
            "character_name": str(pet_name or ""),
            "available": pet is not None and state is not None,
            "current_form": str(
                getattr(state, "current_form", "base") or "base"
            ),
            "target_form": str(
                getattr(state, "target_form", "") or ""
            ),
            "active": bool(
                state is not None and getattr(state, "active", False)
            ),
            "manual_end_requested": bool(
                state is not None
                and getattr(state, "manual_end_requested", False)
            ),
            "auto_session": bool(
                state is not None
                and getattr(state, "auto_session", False)
            ),
            "auto_world_mode": str(
                getattr(state, "auto_world_mode", "") or ""
            ),
            "source": str(getattr(state, "source", "") or ""),
        }

    def update(self, now=None):
        transition_now = (
            self.transition_now_provider()
            if now is None
            else float(now)
        )
        sim_now = self.sim_now_provider() if now is None else float(now)
        transition_results = self.executor.update(
            self.pets,
            now=transition_now,
        )
        for result in transition_results:
            if not result.completed:
                continue
            if (
                getattr(result, "source", "")
                in {"autonomous_start", "sandbox_autonomous_start"}
                and getattr(result, "current_form", "") == "transformed"
            ):
                self.achievement_runtime_coordinator.complete_transformation(
                    result,
                    occurred_at=sim_now,
                )
            if getattr(result, "source", "") in {
                "autonomous_start",
                "autonomous_end",
            }:
                self.record_event(result, occurred_at=sim_now)
                continue
            if callable(self.refresh_household_summary):
                self.refresh_household_summary()
        auto_results = self.executor.update_auto(
            self.pets,
            world_mode=self.world_mode_provider(),
            sim_now=sim_now,
            transition_now=transition_now,
        )
        for result in tuple(auto_results or ()):
            if (
                bool(getattr(result, "started", False))
                and getattr(result, "target_form", "") == "transformed"
                and getattr(result, "source", "")
                in {"autonomous_start", "sandbox_autonomous_start"}
            ):
                self.achievement_runtime_coordinator.begin_transformation(
                    result,
                    started_at=sim_now,
                )
        self.achievement_runtime_coordinator.cancel_orphaned_transformations(
            self.pets
        )
        if self.tendency_coordinator is not None:
            self.tendency_coordinator.update_context(
                pets=self.pets,
                household_pressure=float(
                    self.household_pressure_provider()
                ),
                executor=self.executor,
                now=sim_now,
            )
        return (*transition_results, *auto_results)

    def observe_race_event(self, event):
        if self.tendency_coordinator is None:
            return ()
        return self.tendency_coordinator.process_race_event(
            event,
            pets=self.pets,
            executor=self.executor,
            now=float(event.occurred_at),
        )

    def record_event(self, result, *, occurred_at):
        entered_transformed = result.current_form == "transformed"
        display_name = TRANSFORMATION_EVENT_DISPLAY_NAMES.get(
            result.character_name,
            result.character_name,
        )
        return self.record_household_event(
            occurred_at=float(occurred_at),
            category="system",
            event_type=(
                "transformation_started"
                if entered_transformed
                else "transformation_ended"
            ),
            channel="story",
            importance="normal" if entered_transformed else "low",
            summary=(
                f"{display_name}完成變身。"
                if entered_transformed
                else f"{display_name}解除變身，回到普通形態。"
            ),
            actor_name=result.character_name,
            tags=(
                "transformation",
                "transformed" if entered_transformed else "base",
            ),
            metadata={
                "form": result.current_form,
                "source": result.source,
            },
            apply_deltas=False,
        )

    def shutdown(self, *, reason="runtime_shutdown"):
        for pet in self.pets:
            if self.executor.is_transition_active(pet):
                self.executor.cancel_pet(pet, reason=reason)
