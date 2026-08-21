import argparse
import json

from tanuki_core.mood_calibration import (
    DEFAULT_MOOD_CALIBRATION_SCENARIOS,
    run_mood_calibration_suite,
)


def main():
    parser = argparse.ArgumentParser(
        description="Run deterministic Monte Carlo checks for mood climates.",
    )
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument(
        "--scenario",
        action="append",
        default=[],
        help="Run only the named scenario; repeat to select multiple.",
    )
    arguments = parser.parse_args()
    selected_names = set(arguments.scenario)
    scenarios = tuple(
        scenario
        for scenario in DEFAULT_MOOD_CALIBRATION_SCENARIOS
        if not selected_names or scenario.name in selected_names
    )
    if selected_names and len(scenarios) != len(selected_names):
        known_names = {scenario.name for scenario in scenarios}
        unknown_names = sorted(selected_names - known_names)
        parser.error(f"unknown scenario(s): {', '.join(unknown_names)}")
    summaries = run_mood_calibration_suite(
        runs=arguments.runs,
        seed_offset=arguments.seed_offset,
        scenarios=scenarios,
    )
    print(
        json.dumps(
            [summary.to_dict() for summary in summaries],
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
