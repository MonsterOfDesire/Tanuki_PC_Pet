import time
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QTimer

from .runtime import (
    SIM_CLOCK,
    get_timer_callback_step_delta,
    resolve_timer_repeat_count,
    run_pet_physics_step,
)


@dataclass
class IdleTimerCadence:
    next_run_at: float = 0.0

    def should_run(
        self,
        *,
        now,
        active,
        base_interval_ms,
        idle_interval_ms,
        speed,
    ):
        if active:
            self.next_run_at = 0.0
            return True
        now = float(now)
        if self.next_run_at > now:
            return False
        effective_idle_ms = max(
            float(base_interval_ms),
            float(idle_interval_ms) / max(1.0, float(speed)),
        )
        self.next_run_at = now + effective_idle_ms / 1000.0
        return True


def register_runtime_timer(
    app,
    interval_ms,
    callback,
    speed_scaled=True,
    minimum_interval_ms=1,
    profiler=None,
    timer_name="",
    repeat_count_provider=None,
    pass_step_delta=False,
    active_provider=None,
    idle_interval_ms=None,
    cadence_time_provider=time.perf_counter,
):
    timer = QTimer(app)
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    last_callback_started_at = 0.0
    idle_cadence = IdleTimerCadence()

    def run_callback():
        nonlocal last_callback_started_at
        callback_started_at = time.perf_counter()
        activity_is_active = None
        if callable(active_provider) and idle_interval_ms is not None:
            activity_is_active = bool(active_provider())
            if not idle_cadence.should_run(
                now=cadence_time_provider(),
                active=activity_is_active,
                base_interval_ms=interval_ms,
                idle_interval_ms=idle_interval_ms,
                speed=SIM_CLOCK.speed,
            ):
                return
        callback_interval_ms = 0.0
        if last_callback_started_at > 0.0:
            callback_interval_ms = (
                callback_started_at - last_callback_started_at
            ) * 1000.0
        last_callback_started_at = callback_started_at
        repeat_count = 1
        if speed_scaled and activity_is_active is not False:
            repeat_count = SIM_CLOCK.get_timer_repeat_count(
                interval_ms,
                minimum_interval_ms=minimum_interval_ms,
            )
        repeat_count = resolve_timer_repeat_count(
            repeat_count,
            repeat_count_provider=repeat_count_provider,
        )
        callback_step_delta = None
        if pass_step_delta:
            callback_step_delta = get_timer_callback_step_delta(
                SIM_CLOCK,
                interval_ms,
                float(timer.interval()),
                repeat_count=repeat_count,
            )
        for _ in range(int(repeat_count)):
            if pass_step_delta:
                callback(callback_step_delta)
            else:
                callback()
        if profiler is not None and timer_name:
            profiler.record_timer(
                timer_name,
                duration_ms=(
                    time.perf_counter() - callback_started_at
                ) * 1000.0,
                now=time.perf_counter(),
                repeat_count=repeat_count,
                interval_ms=callback_interval_ms,
            )

    timer.timeout.connect(run_callback)
    timer.start(interval_ms)
    if speed_scaled:
        SIM_CLOCK.register_timer(
            timer,
            interval_ms,
            minimum_interval_ms=minimum_interval_ms,
        )
    return timer


def start_runtime_timers(runtime):
    timers = {
        "mood": register_runtime_timer(
            runtime.app,
            3000,
            lambda: [
                pet.update_mood(runtime.pets_list)
                for pet in runtime.pets_list
            ],
            speed_scaled=True,
            minimum_interval_ms=250,
            profiler=runtime.profiler,
            timer_name="mood",
        ),
        "physics": register_runtime_timer(
            runtime.app,
            30,
            lambda: run_pet_physics_step(runtime.pets_list),
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="physics",
        ),
        "logic": register_runtime_timer(
            runtime.app,
            30,
            lambda step_delta: runtime.logic_scheduler.run(
                runtime.pets_list,
                speed=SIM_CLOCK.speed,
                step_delta=step_delta,
            ),
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="logic",
            repeat_count_provider=lambda default_repeat_count: (
                runtime.logic_scheduler.resolve_repeat_count(
                    runtime.pets_list,
                    default_repeat_count,
                    speed=SIM_CLOCK.speed,
                )
            ),
            pass_step_delta=True,
        ),
    }
    if getattr(runtime.window_tracker, "available", False):
        timers["windows"] = register_runtime_timer(
            runtime.app,
            150,
            runtime.window_tracker.refresh,
            speed_scaled=False,
            profiler=runtime.profiler,
            timer_name="windows",
        )
    timers.update({
        "offer": register_runtime_timer(
            runtime.app,
            30,
            runtime.update_offer_scene,
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="offer",
            active_provider=(
                runtime.offer_item_scene_runtime_controller.is_active
            ),
            idle_interval_ms=240,
        ),
        "transformation": register_runtime_timer(
            runtime.app,
            30,
            runtime.update_transformations,
            speed_scaled=False,
            profiler=runtime.profiler,
            timer_name="transformation",
            active_provider=(
                runtime.transformation_runtime_controller.is_active
            ),
            idle_interval_ms=240,
        ),
        "race": register_runtime_timer(
            runtime.app,
            30,
            runtime.update_race,
            minimum_interval_ms=8,
            profiler=runtime.profiler,
            timer_name="race",
            active_provider=runtime.race_executor.is_active,
            idle_interval_ms=240,
        ),
        "chorus": register_runtime_timer(
            runtime.app,
            60,
            runtime.update_chorus,
            minimum_interval_ms=12,
            profiler=runtime.profiler,
            timer_name="chorus",
            active_provider=runtime.chorus_executor.is_active,
            idle_interval_ms=480,
        ),
        "household": register_runtime_timer(
            runtime.app,
            1000,
            runtime.update_household_events,
            minimum_interval_ms=250,
            profiler=runtime.profiler,
            timer_name="household",
        ),
    })
    return timers
