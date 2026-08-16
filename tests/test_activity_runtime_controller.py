import unittest
from types import SimpleNamespace

from tanuki_core.activity_runtime_controller import ActivityRuntimeController
from tanuki_core.activity_state import PetActivityState
from tanuki_core.race_state import RaceRuntimeResult


class ActivityRuntimeControllerTests(unittest.TestCase):
    def test_race_start_opens_achievement_session_through_coordinator(self):
        achievement = _AchievementCoordinator()
        activity = SimpleNamespace(
            activity_id="race-1",
            source="autonomous",
            started_at=12.0,
            metadata={"execution_mode": "autonomous"},
        )
        activity_coordinator = SimpleNamespace(
            get_activity=lambda activity_id: (
                activity if activity_id == "race-1" else None
            )
        )
        controller = _controller(
            activity_coordinator=activity_coordinator,
            achievement=achievement,
        )
        controller.race_executor = SimpleNamespace(
            update=lambda **kwargs: RaceRuntimeResult(
                True,
                activity_id="race-1",
                started=True,
            )
        )

        result = controller.update_race(now=12.0)

        self.assertTrue(result.started)
        self.assertEqual(
            achievement.started,
            [("race-1", activity_coordinator, "sandbox")],
        )

    def test_world_mode_change_interrupts_every_activity_owner_once(self):
        calls = []
        achievement = _AchievementCoordinator()
        controller = _controller(achievement=achievement)
        controller.work_executor = SimpleNamespace(
            interrupt_active=lambda **kwargs: calls.append(
                ("work", kwargs["reason"])
            )
        )
        controller.sleep_executor = SimpleNamespace(
            interrupt_all=lambda **kwargs: calls.append(
                ("sleep", kwargs["reason"])
            )
        )
        controller.race_executor = SimpleNamespace(
            interrupt_active=lambda **kwargs: calls.append(
                ("race", kwargs["reason"])
            )
        )
        controller.chorus_executor = SimpleNamespace(
            interrupt_all=lambda **kwargs: calls.append(
                ("chorus", kwargs["reason"])
            )
        )

        changed = controller.handle_world_mode_change(
            "golden_legend",
            previous_mode="sandbox",
        )

        self.assertTrue(changed)
        self.assertEqual(
            calls,
            [
                ("work", "world_mode_changed"),
                ("sleep", "world_mode_changed"),
                ("race", "world_mode_changed"),
                ("chorus", "world_mode_changed"),
            ],
        )
        self.assertEqual(achievement.observed_modes, ["golden_legend"])
        self.assertEqual(
            achievement.cancelled_all,
            ["world_mode_changed"],
        )

    def test_user_click_wakes_sleep_without_drag_interrupt(self):
        calls = []
        controller = _controller()
        controller.sleep_executor = SimpleNamespace(
            request_early_wake=lambda pet, **kwargs: (
                calls.append(("wake", kwargs))
                or SimpleNamespace(handled=True)
            ),
            interrupt_pet=lambda pet, **kwargs: (
                calls.append(("interrupt", kwargs))
                or SimpleNamespace(handled=True, activity_id="sleep-1")
            ),
        )

        handled = controller.interrupt_pet_for_user(
            SimpleNamespace(name="Tokai Teio"),
            reason="user_click",
            now=20.0,
        )

        self.assertTrue(handled)
        self.assertEqual(
            calls,
            [("wake", {"now": 20.0, "reason": "user_click"})],
        )

    def test_honey_guard_force_releases_sleep_before_offer_scene(self):
        calls = []
        achievement = _AchievementCoordinator()
        controller = _controller(achievement=achievement)
        controller.sleep_executor = SimpleNamespace(
            interrupt_pet=lambda pet, **kwargs: (
                calls.append((pet, kwargs))
                or SimpleNamespace(handled=True, activity_id="sleep-1")
            ),
        )
        pet = SimpleNamespace(name="Sirius Symboli")

        handled = controller.interrupt_pet_for_user(
            pet,
            reason="honey_guard",
            now=25.0,
        )

        self.assertTrue(handled)
        self.assertEqual(
            calls,
            [
                (
                    pet,
                    {"now": 25.0, "reason": "honey_guard"},
                )
            ],
        )
        self.assertEqual(
            achievement.cancelled,
            [("sleep-1", "honey_guard")],
        )

    def test_active_performer_wakes_sleeping_pet_with_low_band_in_range(self):
        achievement = _AchievementCoordinator()
        performer = _PositionedPet("Sirius Symboli", x=100.0)
        sleeper = _PositionedPet("Air Groove", x=850.0)
        sleeper.activity_state.activity_id = "sleep-1"
        sleeper.activity_state.activity_kind = "sleep"
        sleeper.activity_state.phase = "sleeping"
        wake_calls = []
        controller = _controller(achievement=achievement)
        controller.pets = (performer, sleeper)
        controller.sleep_executor = SimpleNamespace(
            request_early_wake=lambda pet, **kwargs: (
                wake_calls.append((pet.name, kwargs))
                or SimpleNamespace(
                    handled=True,
                    activity_id="sleep-1",
                    participant_name=pet.name,
                )
            )
        )
        participant = SimpleNamespace(
            name=performer.name,
            is_performer=True,
            phase="performing",
        )
        controller.chorus_executor = SimpleNamespace(
            session=SimpleNamespace(
                participants={performer.name: participant}
            ),
            update=lambda **_kwargs: (),
        )

        controller.update_chorus(now=50.0)

        self.assertEqual(len(wake_calls), 1)
        self.assertEqual(wake_calls[0][0], "Air Groove")
        self.assertEqual(wake_calls[0][1]["reason"], "chorus_noise")
        self.assertEqual(
            wake_calls[0][1]["waking_band_override"],
            "low",
        )
        self.assertEqual(wake_calls[0][1]["visual_afterglow_seconds"], 8.0)
        self.assertEqual(
            achievement.sleep_results,
            [("sleep-1", 50.0)],
        )

    def test_audience_does_not_wake_sleeping_pet(self):
        performer = _PositionedPet("Air Groove", x=100.0)
        sleeper = _PositionedPet("Sirius Symboli", x=200.0)
        sleeper.activity_state.activity_id = "sleep-1"
        sleeper.activity_state.activity_kind = "sleep"
        sleeper.activity_state.phase = "sleeping"
        controller = _controller()
        controller.pets = (performer, sleeper)
        participant = SimpleNamespace(
            name=performer.name,
            is_performer=False,
            phase="observing",
        )
        calls = []
        controller.sleep_executor = SimpleNamespace(
            request_early_wake=lambda *_args, **_kwargs: calls.append(True)
        )
        controller.chorus_executor = SimpleNamespace(
            session=SimpleNamespace(
                participants={performer.name: participant}
            ),
            update=lambda **_kwargs: (),
        )

        controller.update_chorus(now=50.0)

        self.assertEqual(calls, [])


class _PositionedPet:
    def __init__(self, name, *, x):
        self.name = name
        self._x = float(x)
        self.activity_state = PetActivityState()

    def x(self):
        return self._x

    def y(self):
        return 0.0

    def width(self):
        return 100.0

    def height(self):
        return 100.0


class _AchievementCoordinator:
    def __init__(self):
        self.started = []
        self.cancelled = []
        self.cancelled_all = []
        self.observed_modes = []
        self.sleep_results = []

    def begin_activity_session(
        self,
        activity_id,
        *,
        activity_coordinator,
        world_mode,
    ):
        self.started.append(
            (activity_id, activity_coordinator, world_mode)
        )
        return True

    def cancel_activity_session(self, activity_id, *, reason):
        self.cancelled.append((activity_id, reason))
        return True

    def cancel_all_activity_sessions(self, *, reason):
        self.cancelled_all.append(reason)

    def observe_world_mode(self, world_mode):
        self.observed_modes.append(world_mode)

    def handle_sleep_result(self, result, *, now):
        self.sleep_results.append((result.activity_id, now))


def _controller(*, activity_coordinator=None, achievement=None):
    activity_coordinator = activity_coordinator or SimpleNamespace(
        get_activity=lambda _activity_id: None,
        get_activity_for_participant=lambda _name: None,
    )
    return ActivityRuntimeController(
        activity_coordinator=activity_coordinator,
        work_settlement_adapter=object(),
        work_executor=SimpleNamespace(),
        sleep_executor=SimpleNamespace(),
        race_executor=SimpleNamespace(),
        race_event_adapter=SimpleNamespace(),
        chorus_executor=SimpleNamespace(),
        chorus_event_adapter=SimpleNamespace(),
        achievement_runtime_coordinator=(
            achievement or _AchievementCoordinator()
        ),
        transformation_runtime_controller=None,
        pets=(),
        pet_registry=SimpleNamespace(
            find_by_name=lambda *_args, **_kwargs: None
        ),
        household=SimpleNamespace(race_statistics=None),
        household_event_schedule=object(),
        world_mode_provider=lambda: "sandbox",
        record_household_event=lambda **_kwargs: None,
        record_resolved_household_event=lambda _event: None,
        apply_race_mood_reward=lambda *_args: None,
        apply_reverse_race_relationship_reward=lambda *_args: None,
        apply_chorus_mood_reward=lambda *_args: None,
        apply_chorus_relationship_reward=lambda *_args: None,
        now_provider=lambda: 10.0,
    )


if __name__ == "__main__":
    unittest.main()
