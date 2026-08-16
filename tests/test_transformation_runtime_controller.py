import unittest
from types import SimpleNamespace

from tanuki_core.transformation_runtime_controller import (
    TransformationRuntimeController,
)


class TransformationRuntimeControllerTests(unittest.TestCase):
    def test_non_sandbox_manual_toggle_is_rejected_before_executor(self):
        controller = _controller(world_mode="golden_legend")

        result = controller.toggle_preview("Tokai Teio", now=10.0)

        self.assertFalse(result.handled)
        self.assertEqual(result.reason, "preview_requires_sandbox")

    def test_autonomous_completion_records_event_and_achievement(self):
        completed = SimpleNamespace(
            completed=True,
            character_name="Tokai Teio",
            current_form="transformed",
            target_form="transformed",
            source="autonomous_start",
        )
        executor = _Executor(update_results=(completed,))
        achievement = _AchievementCoordinator()
        recorded = []
        controller = _controller(
            executor=executor,
            achievement=achievement,
            record_event=lambda **kwargs: recorded.append(kwargs),
        )

        results = controller.update(now=30.0)

        self.assertEqual(results, (completed,))
        self.assertEqual(
            achievement.completed,
            [(completed, 30.0)],
        )
        self.assertEqual(recorded[0]["event_type"], "transformation_started")
        self.assertEqual(recorded[0]["actor_name"], "Tokai Teio")

    def test_race_signal_uses_same_executor_and_pet_collection(self):
        calls = []
        pets = (SimpleNamespace(name="Tokai Teio"),)
        executor = _Executor()
        tendency = SimpleNamespace(
            process_race_event=lambda event, **kwargs: (
                calls.append((event, kwargs)) or ("applied",)
            )
        )
        controller = _controller(
            executor=executor,
            tendency=tendency,
            pets=pets,
        )
        event = SimpleNamespace(occurred_at=45.0)

        result = controller.observe_race_event(event)

        self.assertEqual(result, ("applied",))
        self.assertIs(calls[0][1]["executor"], executor)
        self.assertIs(calls[0][1]["pets"], pets)
        self.assertEqual(calls[0][1]["now"], 45.0)


class _Executor:
    def __init__(self, *, update_results=(), auto_results=()):
        self.update_results = update_results
        self.auto_results = auto_results

    def update(self, _pets, *, now):
        return self.update_results

    def update_auto(self, _pets, **_kwargs):
        return self.auto_results


class _AchievementCoordinator:
    def __init__(self):
        self.completed = []

    def complete_transformation(self, result, *, occurred_at):
        self.completed.append((result, occurred_at))

    def begin_transformation(self, _result, *, started_at):
        return started_at

    def cancel_orphaned_transformations(self, _pets):
        return None


def _controller(
    *,
    world_mode="sandbox",
    executor=None,
    tendency=None,
    achievement=None,
    pets=(),
    record_event=None,
):
    return TransformationRuntimeController(
        executor=executor or _Executor(),
        tendency_coordinator=tendency,
        achievement_runtime_coordinator=(
            achievement or _AchievementCoordinator()
        ),
        pets=pets,
        pet_registry=SimpleNamespace(
            find_by_name=lambda *_args, **_kwargs: None
        ),
        world_mode_provider=lambda: world_mode,
        household_pressure_provider=lambda: 0.0,
        record_household_event=(record_event or (lambda **_kwargs: None)),
        transition_now_provider=lambda: 10.0,
        sim_now_provider=lambda: 10.0,
    )


if __name__ == "__main__":
    unittest.main()
