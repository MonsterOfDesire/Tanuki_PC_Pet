import unittest
from types import SimpleNamespace

from tanuki_core.app_runtime import TanukiAppRuntime
from tanuki_core.activity_runtime_controller import ActivityRuntimeController
from tanuki_core.achievement_gameplay_bridge import AchievementGameplayBridge
from tanuki_core.achievement_runtime_coordinator import (
    AchievementRuntimeCoordinator,
)
from tanuki_core.chorus_executor import ChorusRuntimeResult
from tanuki_core.item_scene_coordinator import (
    ActiveItemScene,
    ItemSceneCoordinator,
    SharedFoodSceneState,
)
from tanuki_core.race_state import RaceRuntimeResult
from tanuki_core.rudolf_work_executor import RudolfWorkRuntimeResult
from tanuki_core.sleep_executor import SleepRuntimeResult
from tanuki_core.transformation_executor import TransformationRuntimeResult


class FakeAchievementRuntimeService:
    def __init__(self):
        self.started = []
        self.cancelled = []
        self.consumed = []
        self.snapshots = []

    def begin_activity_session(self, **kwargs):
        self.started.append(kwargs)
        return True

    def cancel_activity_session(self, activity_id, *, reason):
        self.cancelled.append((activity_id, reason))
        return True

    def consume_activity_metadata(self, metadata):
        self.consumed.append(dict(metadata))
        return True

    def consume_instantaneous_activity_metadata(self, metadata):
        self.consumed.append(dict(metadata))
        return True

    def activity_session_is_eligible(self, activity_id, *, world_mode):
        return any(
            item["activity_id"] == activity_id
            and item["world_mode"] == world_mode
            for item in self.started
        )

    def consume_state_snapshot(self, **kwargs):
        self.snapshots.append(kwargs)
        return True


class AchievementAppRuntimeWiringTests(unittest.TestCase):
    def test_state_change_saves_and_forwards_only_new_unlock_ids(self):
        runtime = object.__new__(TanukiAppRuntime)
        calls = []
        runtime.achievement_runtime_coordinator = _achievement_coordinator(
            "sandbox",
            save_callback=lambda: calls.append("save"),
            unlock_callback=(
                lambda achievement_ids: calls.append(tuple(achievement_ids))
            ),
        )
        result = SimpleNamespace(
            unlocked_achievement_ids=("race.first_natural_finish",)
        )

        runtime._handle_achievement_state_changed(result)

        self.assertEqual(
            calls,
            ["save", ("race.first_natural_finish",)],
        )

    def test_tsuyoshi_side_ready_followup_emits_instantaneous_event(self):
        service = FakeAchievementRuntimeService()
        bridge = AchievementGameplayBridge(
            service=service,
            world_mode_provider=lambda: "sandbox",
        )

        result = bridge.handle_ambient_animation_context(
            character_name="Tsurumaru Tsuyoshi",
            context="side_ready_followup",
            now=42.0,
        )

        self.assertTrue(result)
        self.assertEqual(len(service.consumed), 1)
        metadata = service.consumed[0]
        self.assertEqual(
            metadata["activity_event_name"],
            "ambient.tsuyoshi.side_ready_followup",
        )
        self.assertEqual(metadata["activity_world_mode"], "sandbox")
        self.assertEqual(metadata["activity_source"], "ambient_random")
        self.assertEqual(
            metadata["animation_context"],
            "side_ready_followup",
        )

    def test_progress_only_state_change_saves_without_refreshing_ui(self):
        runtime = object.__new__(TanukiAppRuntime)
        calls = []
        runtime.achievement_runtime_coordinator = _achievement_coordinator(
            "sandbox",
            save_callback=lambda: calls.append("save"),
            unlock_callback=(
                lambda achievement_ids: calls.append(tuple(achievement_ids))
            ),
        )

        runtime._handle_achievement_state_changed(
            SimpleNamespace(unlocked_achievement_ids=())
        )

        self.assertEqual(calls, ["save"])

    def test_race_start_creates_eligibility_session(self):
        runtime = _runtime_shell("sandbox")
        activity = _activity("race-1", source="autonomous")
        runtime.activity_coordinator = SimpleNamespace(
            get_activity=lambda activity_id: (
                activity if activity_id == "race-1" else None
            )
        )
        runtime.activity_runtime_controller.activity_coordinator = (
            runtime.activity_coordinator
        )
        runtime.activity_runtime_controller.race_executor = SimpleNamespace(
            update=lambda **_kwargs: RaceRuntimeResult(
                True,
                activity_id="race-1",
                started=True,
            )
        )

        result = runtime.update_race(now=10.0)

        self.assertTrue(result.started)
        self.assertEqual(
            runtime.achievement_runtime_service.started,
            [
                {
                    "activity_id": "race-1",
                    "world_mode": "sandbox",
                    "source": "autonomous",
                    "execution_mode": "autonomous",
                    "started_at": 10.0,
                }
            ],
        )

    def test_work_start_uses_current_golden_world_mode(self):
        runtime = _runtime_shell("golden_legend")
        activity = _activity(
            "work-1",
            source="household_schedule",
            execution_mode="normal",
            world_mode="",
        )
        runtime.activity_coordinator = SimpleNamespace(
            get_activity=lambda activity_id: (
                activity if activity_id == "work-1" else None
            )
        )
        runtime.activity_runtime_controller.activity_coordinator = (
            runtime.activity_coordinator
        )
        runtime.activity_runtime_controller.work_executor = SimpleNamespace(
            update=lambda **_kwargs: RudolfWorkRuntimeResult(
                True,
                activity_id="work-1",
                started=True,
            )
        )

        result = runtime.update_rudolf_work(now=30.0)

        self.assertTrue(result.started)
        self.assertEqual(
            runtime.achievement_runtime_service.started[0]["world_mode"],
            "golden_legend",
        )
        self.assertEqual(
            runtime.achievement_runtime_service.started[0]["source"],
            "household_schedule",
        )

    def test_chorus_session_id_is_the_achievement_session_id(self):
        runtime = _runtime_shell("sandbox")
        runtime.activity_runtime_controller.chorus_executor = SimpleNamespace(
            session=SimpleNamespace(
                session_id="chorus-1",
                world_mode="sandbox",
                source="autonomous",
                started_at=40.0,
            ),
            update=lambda **_kwargs: (
                ChorusRuntimeResult(
                    True,
                    session_id="chorus-1",
                    started=True,
                ),
            ),
        )

        results = runtime.update_chorus(now=40.0)

        self.assertTrue(results[0].started)
        self.assertEqual(
            runtime.achievement_runtime_service.started,
            [
                {
                    "activity_id": "chorus-1",
                    "world_mode": "sandbox",
                    "source": "autonomous",
                    "execution_mode": "autonomous",
                    "started_at": 40.0,
                }
            ],
        )

    def test_interrupted_race_releases_eligibility_session(self):
        runtime = _runtime_shell("sandbox")
        runtime.activity_runtime_controller.race_executor = SimpleNamespace(
            update=lambda **_kwargs: RaceRuntimeResult(
                True,
                reason="participant_hidden",
                activity_id="race-2",
                interrupted=True,
            )
        )

        runtime.update_race(now=50.0)

        self.assertEqual(
            runtime.achievement_runtime_service.cancelled,
            [("race-2", "participant_hidden")],
        )

    def test_natural_sleep_starts_and_completes_one_session(self):
        runtime = _runtime_shell("sandbox")
        runtime.achievement_runtime_coordinator.handle_sleep_result(
            SleepRuntimeResult(
                True,
                activity_id="sleep-1",
                participant_name="Tokai Teio",
                started=True,
                metadata={
                    "source": "sleep_schedule",
                    "started_at": 10.0,
                    "start_world_mode": "sandbox",
                    "sleep_trigger": "autonomous",
                },
            ),
            now=10.0,
        )
        runtime.achievement_runtime_coordinator.handle_sleep_result(
            SleepRuntimeResult(
                True,
                activity_id="sleep-1",
                participant_name="Tokai Teio",
                finished=True,
                metadata={
                    "source": "sleep_schedule",
                    "started_at": 10.0,
                    "start_world_mode": "sandbox",
                    "sleep_trigger": "autonomous",
                },
            ),
            now=80.0,
        )

        self.assertEqual(
            runtime.achievement_runtime_service.started[0]["activity_id"],
            "sleep-1",
        )
        self.assertEqual(
            runtime.achievement_runtime_service.consumed[0][
                "activity_event_name"
            ],
            "activity.sleep.completed",
        )
        self.assertEqual(
            runtime.achievement_runtime_service.consumed[0][
                "character_name"
            ],
            "Tokai Teio",
        )

    def test_sandbox_sleep_control_never_starts_achievement_session(self):
        runtime = _runtime_shell("sandbox")
        runtime.achievement_runtime_coordinator.handle_sleep_result(
            SleepRuntimeResult(
                True,
                activity_id="sleep-test",
                participant_name="Tokai Teio",
                started=True,
                metadata={
                    "source": "sleep_sandbox_control",
                    "started_at": 10.0,
                    "start_world_mode": "sandbox",
                    "sleep_trigger": "sandbox_control",
                },
            ),
            now=10.0,
        )

        self.assertEqual(runtime.achievement_runtime_service.started, [])

    def test_autonomous_transformation_uses_one_session(self):
        runtime = _runtime_shell("sandbox")
        started = TransformationRuntimeResult(
            True,
            character_name="Tokai Teio",
            target_form="transformed",
            started=True,
            source="sandbox_autonomous_start",
        )
        completed = TransformationRuntimeResult(
            True,
            character_name="Tokai Teio",
            current_form="transformed",
            target_form="transformed",
            completed=True,
            source="sandbox_autonomous_start",
        )

        runtime.achievement_runtime_coordinator.begin_transformation(
            started,
            started_at=20.0,
        )
        runtime.achievement_runtime_coordinator.complete_transformation(
            completed,
            occurred_at=22.0,
        )

        payload = runtime.achievement_runtime_service.consumed[0]
        self.assertEqual(
            payload["activity_event_name"],
            "activity.transformation.completed",
        )
        self.assertEqual(payload["target_form"], "transformed")

    def test_care_completion_carries_shallow_sleep_rescue_flag(self):
        runtime = _runtime_shell("sandbox")
        runtime.achievement_gameplay_bridge.recent_care_wakes = {
            "Sirius Symboli": {
                "target_name": "Tsurumaru Tsuyoshi",
                "occurred_at": 29.0,
            }
        }
        caregiver = SimpleNamespace(name="Sirius Symboli")
        target = SimpleNamespace(name="Tsurumaru Tsuyoshi")

        runtime.handle_care_activity_event(
            "started",
            caregiver,
            target,
            now=30.0,
            care_mode="approach",
        )
        runtime.handle_care_activity_event(
            "completed",
            caregiver,
            target,
            now=35.0,
            success=True,
            care_mode="sit",
        )

        payload = runtime.achievement_runtime_service.consumed[0]
        self.assertTrue(payload["caregiver_woke_from_sleep"])
        self.assertEqual(payload["caregiver_name"], "Sirius Symboli")

    def test_honey_guard_household_event_uses_canonical_metadata(self):
        runtime = _runtime_shell("sandbox")
        runtime.item_scene_coordinator = ItemSceneCoordinator(
            scene_id_factory=lambda: "unused"
        )
        runtime.offer_scene = ActiveItemScene(
            scene_id="honey-1",
            started_at=10.0,
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            source="offer_tray",
        )
        calls = []
        runtime.record_household_event = lambda **kwargs: calls.append(kwargs)

        runtime.record_offer_event(
            "honey",
            "Sirius Symboli",
            "Tsurumaru Tsuyoshi",
            "honey_guard",
        )

        metadata = calls[0]["metadata"]
        self.assertEqual(
            metadata["activity_event_name"],
            "interaction.honey_guard.completed",
        )
        self.assertEqual(metadata["activity_id"], "honey-1")

    def test_shared_food_metadata_is_canonical(self):
        runtime = _runtime_shell("sandbox")
        runtime.item_scene_coordinator = ItemSceneCoordinator(
            scene_id_factory=lambda: "unused"
        )
        runtime.offer_scene = ActiveItemScene(
            scene_id="food-1",
            started_at=12.0,
            item_kind="ramen",
            scene_kind="shared_food",
        )
        profile = SimpleNamespace(item_kind="ramen", profile_key="ramen-share")
        state = SharedFoodSceneState(
            holder_name="Tokai Teio",
            partner_name="Symboli Rudolf",
            outcome_key="share_both",
            consumer_names=("Tokai Teio", "Symboli Rudolf"),
        )

        metadata = runtime.build_shared_food_achievement_metadata(
            profile,
            state,
            source="offer_tray",
            now=20.0,
        )

        self.assertEqual(
            metadata["activity_event_name"],
            "interaction.food_share.completed",
        )
        self.assertEqual(metadata["activity_id"], "food-1")


def _runtime_shell(world_mode):
    runtime = object.__new__(TanukiAppRuntime)
    runtime.settings_provider = SimpleNamespace(world_mode=world_mode)
    runtime.pets_list = []
    runtime.achievement_runtime_service = FakeAchievementRuntimeService()
    runtime.achievement_gameplay_bridge = AchievementGameplayBridge(
        service=runtime.achievement_runtime_service,
        world_mode_provider=lambda: world_mode,
    )
    runtime.achievement_runtime_coordinator = _achievement_coordinator(
        world_mode,
        service=runtime.achievement_runtime_service,
        gameplay_bridge=runtime.achievement_gameplay_bridge,
    )
    runtime.find_pet_by_name = lambda *_args, **_kwargs: None
    runtime.activity_coordinator = SimpleNamespace(
        get_activity=lambda _activity_id: None,
        get_activity_for_participant=lambda _name: None,
        get_active_activities=lambda: (),
    )
    runtime.household = SimpleNamespace(race_statistics=None)
    runtime.household_event_schedule = object()
    runtime.activity_runtime_controller = ActivityRuntimeController(
        activity_coordinator=runtime.activity_coordinator,
        work_settlement_adapter=object(),
        work_executor=SimpleNamespace(),
        sleep_executor=SimpleNamespace(),
        race_executor=SimpleNamespace(),
        race_event_adapter=SimpleNamespace(),
        chorus_executor=SimpleNamespace(),
        chorus_event_adapter=SimpleNamespace(),
        achievement_runtime_coordinator=(
            runtime.achievement_runtime_coordinator
        ),
        transformation_runtime_controller=None,
        pets=runtime.pets_list,
        pet_registry=SimpleNamespace(
            find_by_name=lambda *_args, **_kwargs: None
        ),
        household=runtime.household,
        household_event_schedule=runtime.household_event_schedule,
        world_mode_provider=lambda: world_mode,
        record_household_event=lambda **_kwargs: None,
        record_resolved_household_event=lambda _event: None,
        apply_race_mood_reward=lambda *_args: None,
        apply_reverse_race_relationship_reward=lambda *_args: None,
        apply_chorus_mood_reward=lambda *_args: None,
        apply_chorus_relationship_reward=lambda *_args: None,
    )
    return runtime


def _achievement_coordinator(
    world_mode,
    *,
    service=None,
    gameplay_bridge=None,
    save_callback=None,
    unlock_callback=None,
):
    service = service or FakeAchievementRuntimeService()
    gameplay_bridge = gameplay_bridge or AchievementGameplayBridge(
        service=service,
        world_mode_provider=lambda: world_mode,
    )
    return AchievementRuntimeCoordinator(
        state=None,
        eligibility_guard=SimpleNamespace(),
        time_scale_provider=lambda: 1.0,
        world_mode_provider=lambda: world_mode,
        service=service,
        gameplay_bridge=gameplay_bridge,
        save_callback=save_callback,
        unlock_callback=unlock_callback,
    )


def _activity(
    activity_id,
    *,
    source,
    execution_mode="autonomous",
    world_mode="sandbox",
):
    metadata = {"execution_mode": execution_mode}
    if world_mode:
        metadata["world_mode"] = world_mode
    return SimpleNamespace(
        activity_id=activity_id,
        source=source,
        started_at=10.0 if activity_id == "race-1" else 30.0,
        metadata=metadata,
    )


if __name__ == "__main__":
    unittest.main()
