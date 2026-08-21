from __future__ import annotations

from dataclasses import asdict, dataclass
import random
import statistics

from .chorus_rules import (
    CHORUS_BASE_DURATION_SECONDS,
    CHORUS_MAX_DURATION_SECONDS,
    get_chorus_schedule_policy,
)
from .pet_logic import clamp_mood_score, compute_mood_update, derive_mood_state
from .sleep_rules import (
    SLEEP_COOLDOWN_MAX_SECONDS,
    SLEEP_COOLDOWN_MIN_SECONDS,
    SLEEP_DURATION_MAX_SECONDS,
    SLEEP_DURATION_MIN_SECONDS,
    SLEEP_INITIAL_DELAY_MAX_SECONDS,
    SLEEP_INITIAL_DELAY_MIN_SECONDS,
    SLEEP_NATURAL_COMPLETION_MOOD_REWARD,
    SLEEP_SETTLING_SECONDS,
    SLEEP_WAKING_SECONDS,
)


MOOD_TICKS_PER_MINUTE = 20


@dataclass(frozen=True)
class MoodCalibrationScenario:
    name: str
    climate_key: str
    is_adult: bool
    nearby_count: int
    has_adult_nearby: bool
    nearest_adult_distance: float | None
    duration_minutes: int = 180
    initial_score: float = 60.0
    paused_fraction: float = 0.0
    periodic_rewards: tuple[tuple[int, float], ...] = ()
    simulate_sleep: bool = False
    simulate_chorus: bool = False
    sleep_mood_ceiling: float | None = None
    chorus_frequency_key: str = "normal"
    chorus_mood_reward: float = 0.0
    chorus_mood_ceiling: float | None = None


@dataclass(frozen=True)
class MoodCalibrationSummary:
    scenario: str
    runs: int
    normal_percent: float
    low_percent: float
    severe_percent: float
    entered_low_by_60_minutes_percent: float
    two_children_entered_low_by_60_minutes_percent: float
    entered_severe_by_60_minutes_percent: float
    median_first_low_minutes: float | None
    median_first_severe_minutes: float | None
    average_final_score: float
    activity_paused_percent: float
    sleep_completions_per_hour: float
    chorus_completions_per_hour: float
    activity_mood_gain_per_hour: float

    def to_dict(self):
        return asdict(self)


DEFAULT_MOOD_CALIBRATION_SCENARIOS = (
    MoodCalibrationScenario(
        name="balanced_child_household",
        climate_key="balanced",
        is_adult=False,
        nearby_count=4,
        has_adult_nearby=True,
        nearest_adult_distance=140.0,
        simulate_sleep=True,
        simulate_chorus=True,
        sleep_mood_ceiling=55.0,
        chorus_frequency_key="frequent",
        chorus_mood_reward=2.0,
        chorus_mood_ceiling=60.0,
    ),
    MoodCalibrationScenario(
        name="balanced_child_household_normal_chorus",
        climate_key="balanced",
        is_adult=False,
        nearby_count=4,
        has_adult_nearby=True,
        nearest_adult_distance=140.0,
        simulate_sleep=True,
        simulate_chorus=True,
        sleep_mood_ceiling=55.0,
        chorus_frequency_key="normal",
        chorus_mood_reward=2.0,
        chorus_mood_ceiling=60.0,
    ),
    MoodCalibrationScenario(
        name="balanced_child_near_adult_no_activities",
        climate_key="balanced",
        is_adult=False,
        nearby_count=1,
        has_adult_nearby=True,
        nearest_adult_distance=140.0,
    ),
    MoodCalibrationScenario(
        name="balanced_child_alone",
        climate_key="balanced",
        is_adult=False,
        nearby_count=0,
        has_adult_nearby=False,
        nearest_adult_distance=None,
    ),
    MoodCalibrationScenario(
        name="balanced_adult_household",
        climate_key="balanced",
        is_adult=True,
        nearby_count=4,
        has_adult_nearby=True,
        nearest_adult_distance=100.0,
        simulate_sleep=True,
        simulate_chorus=True,
        sleep_mood_ceiling=55.0,
        chorus_mood_reward=1.0,
        chorus_mood_ceiling=60.0,
    ),
    MoodCalibrationScenario(
        name="cheerful_child_household",
        climate_key="cheerful",
        is_adult=False,
        nearby_count=4,
        has_adult_nearby=True,
        nearest_adult_distance=140.0,
        simulate_sleep=True,
        simulate_chorus=True,
        sleep_mood_ceiling=55.0,
        chorus_mood_reward=2.0,
        chorus_mood_ceiling=60.0,
    ),
    MoodCalibrationScenario(
        name="expressive_child_alone",
        climate_key="expressive",
        is_adult=False,
        nearby_count=0,
        has_adult_nearby=False,
        nearest_adult_distance=None,
    ),
)

DEFAULT_SCENARIO_SEED_INDEX = {
    scenario.name: index
    for index, scenario in enumerate(DEFAULT_MOOD_CALIBRATION_SCENARIOS)
}


def _percent(part, whole):
    if not whole:
        return 0.0
    return round((float(part) / float(whole)) * 100.0, 2)


def _median_minutes(ticks):
    if not ticks:
        return None
    return round(statistics.median(ticks) / MOOD_TICKS_PER_MINUTE, 2)


def _seconds_to_ticks(seconds):
    return max(1, int(round(float(seconds) / 3.0)))


def simulate_mood_scenario(scenario, *, runs, seed_offset=0):
    runs = max(1, int(runs))
    total_ticks = max(
        1,
        int(scenario.duration_minutes) * MOOD_TICKS_PER_MINUTE,
    )
    band_counts = {"normal": 0, "unhappy": 0, "depressed": 0}
    first_low_ticks = []
    first_severe_ticks = []
    entered_low_by_hour = 0
    entered_severe_by_hour = 0
    final_scores = []
    total_paused_ticks = 0
    total_sleep_completions = 0
    total_chorus_completions = 0
    total_activity_mood_gain = 0.0

    reward_intervals = tuple(
        (
            max(1, int(minutes) * MOOD_TICKS_PER_MINUTE),
            float(delta),
        )
        for minutes, delta in scenario.periodic_rewards
    )
    chorus_policy = get_chorus_schedule_policy(
        scenario.chorus_frequency_key
    )
    for run_index in range(runs):
        mood_rng = random.Random(int(seed_offset) + run_index)
        timeline_rng = random.Random(
            int(seed_offset) + runs + run_index + 104729
        )
        score = float(scenario.initial_score)
        lonely_timer = 0
        first_low = None
        first_severe = None
        sleep_ends_at = 0
        chorus_ends_at = 0
        next_sleep_at = (
            timeline_rng.randint(
                _seconds_to_ticks(SLEEP_INITIAL_DELAY_MIN_SECONDS),
                _seconds_to_ticks(SLEEP_INITIAL_DELAY_MAX_SECONDS),
            )
            if scenario.simulate_sleep else 0
        )
        next_chorus_at = (
            timeline_rng.randint(
                _seconds_to_ticks(
                    chorus_policy.initial_delay_min_seconds
                ),
                _seconds_to_ticks(
                    chorus_policy.initial_delay_max_seconds
                ),
            )
            if scenario.simulate_chorus else 0
        )
        for tick_index in range(1, total_ticks + 1):
            for interval_ticks, delta in reward_intervals:
                if tick_index % interval_ticks == 0:
                    score = clamp_mood_score(score + delta)
            if sleep_ends_at and tick_index >= sleep_ends_at:
                sleep_reward = SLEEP_NATURAL_COMPLETION_MOOD_REWARD
                sleep_gain = sleep_reward
                if scenario.sleep_mood_ceiling is not None:
                    sleep_gain = min(
                        sleep_gain,
                        max(0.0, scenario.sleep_mood_ceiling - score),
                    )
                score = clamp_mood_score(score + sleep_gain)
                total_activity_mood_gain += sleep_gain
                total_sleep_completions += 1
                sleep_ends_at = 0
                # Runtime cooldown is sampled after waking: 3–8 minutes.
                next_sleep_at = tick_index + timeline_rng.randint(
                    _seconds_to_ticks(SLEEP_COOLDOWN_MIN_SECONDS),
                    _seconds_to_ticks(SLEEP_COOLDOWN_MAX_SECONDS),
                )
            if chorus_ends_at and tick_index >= chorus_ends_at:
                reward = max(0.0, float(scenario.chorus_mood_reward))
                chorus_gain = reward
                if scenario.chorus_mood_ceiling is not None:
                    chorus_gain = min(
                        chorus_gain,
                        max(0.0, scenario.chorus_mood_ceiling - score),
                    )
                score = clamp_mood_score(score + chorus_gain)
                total_activity_mood_gain += chorus_gain
                total_chorus_completions += 1
                chorus_ends_at = 0
                # Runtime cooldown follows the selected frequency policy.
                next_chorus_at = tick_index + timeline_rng.randint(
                    _seconds_to_ticks(chorus_policy.cooldown_min_seconds),
                    _seconds_to_ticks(chorus_policy.cooldown_max_seconds),
                )

            if not sleep_ends_at and not chorus_ends_at:
                due_sleep = bool(next_sleep_at and tick_index >= next_sleep_at)
                due_chorus = bool(
                    next_chorus_at and tick_index >= next_chorus_at
                )
                if due_sleep and (
                    not due_chorus or next_sleep_at <= next_chorus_at
                ):
                    sleep_ends_at = tick_index + timeline_rng.randint(
                        _seconds_to_ticks(
                            SLEEP_DURATION_MIN_SECONDS
                            + SLEEP_SETTLING_SECONDS
                            + SLEEP_WAKING_SECONDS
                        ),
                        _seconds_to_ticks(
                            SLEEP_DURATION_MAX_SECONDS
                            + SLEEP_SETTLING_SECONDS
                            + SLEEP_WAKING_SECONDS
                        ),
                    )
                    next_sleep_at = 0
                elif due_chorus:
                    chorus_ends_at = tick_index + timeline_rng.randint(
                        _seconds_to_ticks(CHORUS_BASE_DURATION_SECONDS),
                        _seconds_to_ticks(CHORUS_MAX_DURATION_SECONDS),
                    )
                    next_chorus_at = 0

            scheduled_activity_paused = bool(sleep_ends_at or chorus_ends_at)
            paused = scheduled_activity_paused or (
                timeline_rng.random()
                < max(0.0, min(1.0, float(scenario.paused_fraction)))
            )
            if paused:
                total_paused_ticks += 1
            if not paused:
                update = compute_mood_update(
                    current_score=score,
                    lonely_timer=lonely_timer,
                    is_adult=scenario.is_adult,
                    nearby_count=scenario.nearby_count,
                    has_adult_nearby=scenario.has_adult_nearby,
                    climate_key=scenario.climate_key,
                    change_roll=mood_rng.random(),
                    direction_roll=mood_rng.random(),
                    magnitude_roll=mood_rng.random(),
                    nearest_adult_distance=(
                        scenario.nearest_adult_distance
                    ),
                )
                score = update.mood_score
                lonely_timer = update.lonely_timer
            state = derive_mood_state(score)
            band_counts[state] += 1
            if state != "normal" and first_low is None:
                first_low = tick_index
            if state == "depressed" and first_severe is None:
                first_severe = tick_index
        if first_low is not None:
            first_low_ticks.append(first_low)
            if first_low <= 60 * MOOD_TICKS_PER_MINUTE:
                entered_low_by_hour += 1
        if first_severe is not None:
            first_severe_ticks.append(first_severe)
            if first_severe <= 60 * MOOD_TICKS_PER_MINUTE:
                entered_severe_by_hour += 1
        final_scores.append(score)

    observed_ticks = total_ticks * runs
    observed_hours = observed_ticks / (MOOD_TICKS_PER_MINUTE * 60.0)
    one_child_probability = entered_low_by_hour / runs
    return MoodCalibrationSummary(
        scenario=scenario.name,
        runs=runs,
        normal_percent=_percent(band_counts["normal"], observed_ticks),
        low_percent=_percent(band_counts["unhappy"], observed_ticks),
        severe_percent=_percent(band_counts["depressed"], observed_ticks),
        entered_low_by_60_minutes_percent=_percent(
            entered_low_by_hour,
            runs,
        ),
        two_children_entered_low_by_60_minutes_percent=round(
            (1.0 - ((1.0 - one_child_probability) ** 2)) * 100.0,
            2,
        ),
        entered_severe_by_60_minutes_percent=_percent(
            entered_severe_by_hour,
            runs,
        ),
        median_first_low_minutes=_median_minutes(first_low_ticks),
        median_first_severe_minutes=_median_minutes(first_severe_ticks),
        average_final_score=round(statistics.mean(final_scores), 2),
        activity_paused_percent=_percent(total_paused_ticks, observed_ticks),
        sleep_completions_per_hour=round(
            total_sleep_completions / observed_hours,
            2,
        ),
        chorus_completions_per_hour=round(
            total_chorus_completions / observed_hours,
            2,
        ),
        activity_mood_gain_per_hour=round(
            total_activity_mood_gain / observed_hours,
            2,
        ),
    )


def run_mood_calibration_suite(
    *,
    runs=2000,
    seed_offset=0,
    scenarios=DEFAULT_MOOD_CALIBRATION_SCENARIOS,
):
    return tuple(
        simulate_mood_scenario(
            scenario,
            runs=runs,
            seed_offset=int(seed_offset) + (
                DEFAULT_SCENARIO_SEED_INDEX.get(scenario.name, index)
                * 1000003
            ),
        )
        for index, scenario in enumerate(scenarios)
    )
