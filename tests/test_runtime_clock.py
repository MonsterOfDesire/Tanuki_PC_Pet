import unittest

from tanuki_core.runtime import (
    AdaptivePetLogicScheduler,
    RuntimeProfiler,
    SimulationClock,
    get_enabled_simulation_pets,
    get_pet_logic_step_count,
    get_pet_logic_step_scale,
    get_timer_callback_step_delta,
    resolve_timer_repeat_count,
    run_pet_logic_step,
    run_pet_physics_step,
)


class RuntimeTests(unittest.TestCase):
    def test_fast_logic_timers_scale_to_dense_real_time_updates(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(30, minimum_interval_ms=8), 8)
        self.assertEqual(clock.get_timer_repeat_count(30, minimum_interval_ms=8), 2)

    def test_animation_timer_matches_legacy_speed_scaled_refresh(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(80), 10)
        self.assertEqual(clock.get_timer_repeat_count(80), 1)
        self.assertAlmostEqual(clock.get_timer_step_delta(80), 1.0)

    def test_animation_timer_can_cap_repaint_and_advance_multiple_frames(self):
        clock = SimulationClock()
        clock.speed = 8.0

        interval = clock.get_timer_interval(80, minimum_interval_ms=17)

        self.assertEqual(interval, 17)
        self.assertAlmostEqual(
            clock.get_timer_step_delta(80, actual_interval_ms=interval),
            1.7,
        )

    def test_medium_timers_still_scale_cleanly(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertEqual(clock.get_timer_interval(150), 19)
        self.assertEqual(clock.get_timer_repeat_count(150), 1)
        self.assertAlmostEqual(clock.get_timer_step_delta(150), 1.0133333333)

    def test_register_and_speed_change_reapply_timer_interval(self):
        clock = SimulationClock()
        timer = FakeTimer()

        clock.register_timer(timer, 30)
        clock.set_speed(4.0)

        self.assertEqual(timer.intervals[0], 30)
        self.assertEqual(timer.intervals[-1], 8)

    def test_custom_minimum_interval_can_be_provided_for_specific_timers(self):
        clock = SimulationClock()
        timer = FakeTimer()

        clock.register_timer(timer, 30, minimum_interval_ms=8)
        clock.set_speed(8.0)

        self.assertEqual(timer.intervals[-1], 8)

    def test_runtime_profiler_tracks_timer_repeat_rate(self):
        profiler = RuntimeProfiler()

        profiler.record_timer("logic", duration_ms=0.5, now=0.5, repeat_count=2, interval_ms=8.0)
        profiler.record_timer("logic", duration_ms=0.7, now=1.7, repeat_count=2, interval_ms=8.0)

        metric = profiler.timer_metrics["logic"]
        self.assertGreater(metric.events_per_second, 0.0)
        self.assertGreater(metric.repeats_per_second, metric.events_per_second)
        self.assertEqual(metric.last_repeat_count, 2)

    def test_runtime_timer_repeat_provider_can_reduce_a_dense_callback_batch(self):
        observed_defaults = []

        repeat_count = resolve_timer_repeat_count(
            2,
            repeat_count_provider=lambda default: observed_defaults.append(default) or 1,
        )

        self.assertEqual(observed_defaults, [2])
        self.assertEqual(repeat_count, 1)

    def test_timer_callback_step_delta_splits_elapsed_time_across_repeats(self):
        clock = SimulationClock()
        clock.speed = 8.0

        self.assertAlmostEqual(
            get_timer_callback_step_delta(
                clock,
                base_interval_ms=30,
                effective_interval_ms=8,
                repeat_count=2,
            ),
            1.0666666667,
        )
        self.assertAlmostEqual(
            get_timer_callback_step_delta(
                clock,
                base_interval_ms=30,
                effective_interval_ms=8,
                repeat_count=1,
            ),
            2.1333333333,
        )

    def test_timer_callback_step_delta_is_stable_at_1x_nominal_interval(self):
        clock = SimulationClock()
        clock.speed = 1.0

        self.assertEqual(
            get_timer_callback_step_delta(
                clock,
                base_interval_ms=30,
                effective_interval_ms=30,
                repeat_count=1,
            ),
            1.0,
        )

    def test_runtime_profiler_builds_debug_lines(self):
        profiler = RuntimeProfiler()
        profiler.record_timer("logic", duration_ms=0.6, now=0.5, repeat_count=2, interval_ms=8.0)
        profiler.record_timer("logic", duration_ms=0.8, now=1.8, repeat_count=2, interval_ms=8.0)
        profiler.record_section("pet.tick", 0.9, now=1.2)

        lines = profiler.build_debug_lines(speed=8.0)

        self.assertTrue(any("perf speed=8x" in line for line in lines))
        self.assertTrue(any("logic:" in line for line in lines))
        self.assertTrue(any("tick:" in line for line in lines))

    def test_simulation_steps_skip_only_user_disabled_pets(self):
        enabled = FakeSimulationPet(user_visible=True, widget_visible=True)
        temporarily_hidden = FakeSimulationPet(user_visible=True, widget_visible=False)
        disabled = FakeSimulationPet(user_visible=False, widget_visible=False)
        pets = [enabled, temporarily_hidden, disabled]

        self.assertEqual(
            get_enabled_simulation_pets(pets),
            (enabled, temporarily_hidden),
        )
        self.assertEqual(run_pet_logic_step(pets), 2)
        self.assertEqual(run_pet_physics_step(pets), 2)

        active_pets = (enabled, temporarily_hidden)
        self.assertEqual(enabled.logic_groups, [active_pets])
        self.assertEqual(temporarily_hidden.logic_groups, [active_pets])
        self.assertEqual(disabled.logic_groups, [])
        self.assertEqual(enabled.physics_groups, [active_pets])
        self.assertEqual(temporarily_hidden.physics_groups, [active_pets])
        self.assertEqual(disabled.physics_groups, [])

    def test_simulation_steps_keep_legacy_pets_without_visibility_flag(self):
        pet = FakeSimulationPet()
        del pet.user_visible

        self.assertEqual(run_pet_logic_step([pet]), 1)
        self.assertEqual(pet.logic_groups, [(pet,)])

    def test_adaptive_logic_scheduler_batches_three_or_more_pets_at_8x(self):
        scheduler = AdaptivePetLogicScheduler()
        pets = [FakeSimulationPet() for _ in range(5)]

        first_count = scheduler.run(pets, speed=8.0, step_delta=2.0)
        second_count = scheduler.run(pets, speed=8.0, step_delta=2.0)

        self.assertEqual(first_count, 3)
        self.assertEqual(second_count, 2)
        self.assertEqual([len(pet.logic_groups) for pet in pets], [1, 1, 1, 1, 1])
        self.assertTrue(all(pet.logic_groups == [tuple(pets)] for pet in pets))
        self.assertEqual([pet.logic_step_scales for pet in pets], [[2.0], [4.0], [2.0], [4.0], [2.0]])
        self.assertTrue(all(not hasattr(pet, "logic_step_scale") for pet in pets))

    def test_adaptive_scheduler_preserves_elapsed_time_across_pet_counts(self):
        clock = SimulationClock()
        clock.speed = 8.0
        event_step_delta = clock.get_timer_step_delta(30, actual_interval_ms=8)
        low_load_repeat_count = clock.get_timer_repeat_count(30, minimum_interval_ms=8)
        low_load_step_delta = event_step_delta / low_load_repeat_count
        low_load_scheduler = AdaptivePetLogicScheduler()
        high_load_scheduler = AdaptivePetLogicScheduler()
        two_pets = [FakeSimulationPet() for _ in range(2)]
        five_pets = [FakeSimulationPet() for _ in range(5)]

        event_count = 120
        for _ in range(event_count):
            for _repeat in range(low_load_repeat_count):
                low_load_scheduler.run(two_pets, speed=8.0, step_delta=low_load_step_delta)
            high_load_scheduler.run(five_pets, speed=8.0, step_delta=event_step_delta)

        expected_elapsed_steps = event_count * event_step_delta
        for pet in two_pets:
            self.assertAlmostEqual(sum(pet.logic_step_scales), expected_elapsed_steps)
        for pet in five_pets:
            self.assertLessEqual(
                abs(sum(pet.logic_step_scales) - expected_elapsed_steps),
                event_step_delta + 1e-6,
            )

    def test_adaptive_scheduler_handles_two_to_three_pet_transition_without_spike(self):
        scheduler = AdaptivePetLogicScheduler()
        pets = [FakeSimulationPet() for _ in range(2)]
        scheduler.run(pets, speed=8.0, step_delta=1.0)
        third_pet = FakeSimulationPet()
        pets.append(third_pet)

        scheduler.run(pets, speed=8.0, step_delta=2.0)
        scheduler.run(pets, speed=8.0, step_delta=2.0)

        transition_scales = [scale for pet in pets for scale in pet.logic_step_scales[1:]]
        transition_scales.extend(third_pet.logic_step_scales)
        self.assertTrue(transition_scales)
        self.assertLessEqual(max(transition_scales), 4.0)

    def test_adaptive_scheduler_discards_disabled_pet_backlog_before_reenable(self):
        scheduler = AdaptivePetLogicScheduler()
        pets = [FakeSimulationPet() for _ in range(5)]
        target = pets[1]
        scheduler.run(pets, speed=8.0, step_delta=2.0)
        target.user_visible = False
        for _ in range(4):
            scheduler.run(pets, speed=8.0, step_delta=2.0)
        target.user_visible = True
        for _ in range(2):
            scheduler.run(pets, speed=8.0, step_delta=2.0)

        self.assertEqual(len(target.logic_step_scales), 1)
        self.assertLessEqual(target.logic_step_scales[0], 4.0)

    def test_adaptive_scheduler_caps_large_elapsed_backlog(self):
        scheduler = AdaptivePetLogicScheduler(max_pending_step_scale=8.0)
        pets = [FakeSimulationPet() for _ in range(5)]

        scheduler.run(pets, speed=8.0, step_delta=100.0)
        scheduler.run(pets, speed=8.0, step_delta=1.0)

        self.assertTrue(all(max(pet.logic_step_scales) <= 8.0 for pet in pets))

    def test_adaptive_logic_scheduler_disables_timer_repeat_in_high_load_mode(self):
        scheduler = AdaptivePetLogicScheduler()
        five_pets = [FakeSimulationPet() for _ in range(5)]
        two_pets = [FakeSimulationPet() for _ in range(2)]

        self.assertEqual(
            scheduler.resolve_repeat_count(five_pets, default_repeat_count=2, speed=8.0),
            1,
        )
        self.assertEqual(
            scheduler.resolve_repeat_count(two_pets, default_repeat_count=2, speed=8.0),
            2,
        )
        self.assertEqual(
            scheduler.resolve_repeat_count(five_pets, default_repeat_count=1, speed=4.0),
            1,
        )

    def test_adaptive_logic_scheduler_counts_only_user_enabled_pets(self):
        scheduler = AdaptivePetLogicScheduler()
        pets = [FakeSimulationPet() for _ in range(2)]
        pets.extend(FakeSimulationPet(user_visible=False) for _ in range(3))

        self.assertFalse(scheduler.is_high_load(pets, speed=8.0))
        self.assertEqual(scheduler.run(pets, speed=8.0), 2)
        self.assertEqual([len(pet.logic_groups) for pet in pets], [1, 1, 0, 0, 0])
        self.assertEqual([pet.logic_step_scales for pet in pets[:2]], [[1.0], [1.0]])

    def test_adaptive_scheduler_uses_legacy_fast_path_for_unit_step(self):
        scheduler = AdaptivePetLogicScheduler()
        pets = [FakeSimulationPet() for _ in range(5)]

        self.assertEqual(scheduler.run(pets, speed=1.0, step_delta=1.0), 5)

        self.assertTrue(all(pet.logic_step_attribute_present == [False] for pet in pets))
        self.assertEqual(scheduler.pending_step_scale_by_pet_id, {})

    def test_logic_step_count_normalizes_scheduler_scale(self):
        pet = FakeSimulationPet()

        self.assertEqual(get_pet_logic_step_count(pet), 1)
        pet.logic_step_scale = 4.0
        self.assertEqual(get_pet_logic_step_count(pet), 4)
        self.assertEqual(get_pet_logic_step_scale(pet), 4.0)
        pet.logic_step_scale = 2.25
        self.assertEqual(get_pet_logic_step_count(pet), 2)
        self.assertEqual(get_pet_logic_step_scale(pet), 2.25)


class FakeTimer:
    def __init__(self):
        self.intervals = []

    def setInterval(self, interval):
        self.intervals.append(interval)


class FakeSimulationPet:
    def __init__(self, user_visible=True, widget_visible=True):
        self.user_visible = user_visible
        self.widget_visible = widget_visible
        self.logic_groups = []
        self.logic_step_scales = []
        self.logic_step_attribute_present = []
        self.physics_groups = []

    def isVisible(self):
        return self.widget_visible

    def tick(self, pets):
        self.logic_groups.append(pets)
        self.logic_step_attribute_present.append(hasattr(self, "logic_step_scale"))
        self.logic_step_scales.append(float(getattr(self, "logic_step_scale", 1.0)))

    def resolve_collision(self, pets):
        self.physics_groups.append(pets)


if __name__ == "__main__":
    unittest.main()
