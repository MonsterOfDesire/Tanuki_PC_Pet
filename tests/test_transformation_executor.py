import os
import tempfile
import unittest

from tanuki_core.transformation_executor import TransformationExecutor
from tanuki_core.transformation_state import (
    FORM_BASE,
    FORM_TRANSFORMED,
    PetTransformationState,
)
from tanuki_core.transformation_tendency import TENDENCY_TEIO_RACE_STIMULUS


class FakeAssetManager:
    def __init__(self, path, *, result=None, **_kwargs):
        self.character_path = path
        self.result = result
        self.frame_cache = object()
        self.store_cache = object()

    def get_contextual_result_for_any_purpose(self, **_kwargs):
        return self.result


class FixedRandom:
    def uniform(self, lower, _upper):
        return float(lower)


class FakePet:
    def __init__(self, name, base_path, manager):
        self.name = name
        self.base_character_path = base_path
        self.character_path = base_path
        self.asset_manager = manager
        self.transformation_state = PetTransformationState()
        self.user_visible = True
        self.dragging = False
        self.drag_press_pending = False
        self.activity_state = None
        self.intent_kind = "ambient_idle"
        self.offer_scene_kind = "none"
        self.care_mode = "none"
        self.care_partner = None
        self.is_hugging = False
        self.social_mode = "none"
        self.is_recovering = False
        self.is_angry_locked = False
        self.held_item_kind = ""
        self.vy = 0.0
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.state = "idle"
        self.state_timer = 0
        self.current_frames = ["base-frame"]
        self.frame_index = 0
        self.mood_score = 20.0
        self.mood_state = "depressed"
        self.applied = []
        self.update_count = 0

    def isVisible(self):
        return True

    def get_effective_scale(self):
        return 1.0

    def clear_observe_intent(self, **_kwargs):
        self.intent_kind = "ambient_idle"

    def reset_stationary_move_mode(self):
        return None

    def apply_animation_result(self, purpose, result):
        self.applied.append((purpose, result))
        self.current_frames = result[0]
        return True

    def sync_mood_state_with_score(self):
        self.mood_state = "normal" if self.mood_score >= 50.0 else "depressed"

    def refresh_movement_state(self):
        return None

    def update(self):
        self.update_count += 1


class TransformationExecutorTests(unittest.TestCase):
    def test_pending_drag_hold_blocks_transformation_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            manager = FakeAssetManager(
                temp_dir,
                result=(["frame"], "idle", "stand", "happy"),
            )
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.drag_press_pending = True
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
            )

            result = executor.toggle(pet, now=1.0)

            self.assertFalse(result.started)
            self.assertEqual(result.reason, "participant_dragging")

    def test_toggle_swaps_at_full_white_then_reveals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            transformed_dir = os.path.join(temp_dir, "transformed")
            os.mkdir(transformed_dir)
            result = (["transformed-frame"], "move", "fly", "happy")
            base_manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, base_manager)
            executor = TransformationExecutor(
                phase_seconds=0.5,
                asset_manager_factory=(
                    lambda path, **kwargs: FakeAssetManager(
                        path,
                        result=result,
                        **kwargs,
                    )
                ),
            )

            started = executor.toggle(pet, now=10.0)
            halfway = executor.update_pet(pet, now=10.25)
            swapped = executor.update_pet(pet, now=10.5)
            completed = executor.update_pet(pet, now=11.0)

            self.assertTrue(started.started)
            self.assertTrue(halfway.handled)
            self.assertEqual(pet.transformation_state.current_form, FORM_TRANSFORMED)
            self.assertTrue(swapped.handled)
            self.assertTrue(completed.completed)
            self.assertFalse(pet.transformation_state.active)
            self.assertEqual(pet.mood_score, 50.0)
            self.assertEqual(pet.asset_manager.character_path, transformed_dir)
            self.assertEqual(pet.applied[-1][0], "move")

    def test_airborne_pet_cannot_start(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            manager = FakeAssetManager(
                temp_dir,
                result=(["frame"], "idle", "stand", "happy"),
            )
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.vy = 1.0
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
            )

            result = executor.toggle(pet, now=1.0)

            self.assertFalse(result.started)
            self.assertEqual(result.reason, "airborne")
            self.assertEqual(pet.transformation_state.current_form, FORM_BASE)

    def test_auto_update_schedules_and_starts_in_golden_world(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.mood_score = 60.0
            executor = TransformationExecutor(
                asset_manager_factory=(
                    lambda path, **kwargs: FakeAssetManager(
                        path,
                        result=result,
                        **kwargs,
                    )
                ),
                random_source=FixedRandom(),
            )

            executor.update_auto(
                [pet],
                world_mode="golden_legend",
                sim_now=10.0,
                transition_now=100.0,
            )
            started = executor.update_auto(
                [pet],
                world_mode="golden_legend",
                sim_now=490.0,
                transition_now=101.0,
            )

            self.assertEqual(pet.transformation_state.auto_next_attempt_at, 0.0)
            self.assertTrue(pet.transformation_state.auto_session)
            self.assertEqual(pet.transformation_state.auto_form_expires_at, 580.0)
            self.assertTrue(started[0].started)
            self.assertEqual(started[0].source, "autonomous_start")

    def test_auto_update_schedules_and_starts_without_formal_source_in_sandbox(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Symboli Rudolf", temp_dir, manager)
            pet.mood_score = 60.0
            executor = TransformationExecutor(
                asset_manager_factory=(
                    lambda path, **kwargs: FakeAssetManager(
                        path,
                        result=result,
                        **kwargs,
                    )
                ),
                random_source=FixedRandom(),
            )

            executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=10.0,
                transition_now=100.0,
            )
            started = executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=490.0,
                transition_now=101.0,
            )

            self.assertTrue(started[0].started)
            self.assertEqual(
                started[0].source,
                "sandbox_autonomous_start",
            )
            self.assertEqual(
                pet.transformation_state.auto_world_mode,
                "sandbox",
            )

    def test_pending_tendency_shortens_new_auto_schedule(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FakeAssetManager(temp_dir)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.mood_score = 60.0
            executor = TransformationExecutor(random_source=FixedRandom())

            tendency = executor.apply_tendency_signal(
                pet,
                signal_kind=TENDENCY_TEIO_RACE_STIMULUS,
                sim_now=5.0,
            )
            executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=10.0,
                transition_now=100.0,
            )

            self.assertTrue(tendency.applied)
            self.assertEqual(
                pet.transformation_state.auto_next_attempt_at,
                415.0,
            )
            self.assertEqual(
                pet.transformation_state.auto_pending_tendency_advance_seconds,
                0.0,
            )
            self.assertEqual(pet.transformation_state.auto_attempt_serial, 1)

    def test_expired_auto_form_retries_end_while_airborne(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.transformation_state.current_form = FORM_TRANSFORMED
            pet.transformation_state.auto_session = True
            pet.transformation_state.auto_world_mode = "golden_legend"
            pet.transformation_state.auto_form_expires_at = 10.0
            pet.vy = 1.0
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
                random_source=FixedRandom(),
            )

            results = executor.update_auto(
                [pet],
                world_mode="golden_legend",
                sim_now=20.0,
                transition_now=100.0,
            )

            self.assertFalse(results[0].started)
            self.assertEqual(results[0].reason, "airborne")
            self.assertTrue(pet.transformation_state.auto_session)
            self.assertEqual(pet.transformation_state.auto_retry_at, 25.0)

    def test_manual_end_waits_until_transformed_pet_is_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.transformation_state.current_form = FORM_TRANSFORMED
            pet.transformation_state.auto_session = True
            pet.transformation_state.auto_world_mode = "sandbox"
            pet.care_mode = "interaction"
            executor = TransformationExecutor(
                asset_manager_factory=(
                    lambda path, **kwargs: FakeAssetManager(
                        path,
                        result=result,
                        **kwargs,
                    )
                ),
                random_source=FixedRandom(),
            )

            queued = executor.request_manual_toggle(
                pet,
                now=100.0,
                intent_now=20.0,
            )
            pet.care_mode = "none"
            waiting = executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=24.0,
                transition_now=101.0,
            )
            started = executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=25.0,
                transition_now=102.0,
            )

            self.assertTrue(queued.queued)
            self.assertEqual(queued.reason, "manual_end_queued")
            self.assertEqual(waiting, ())
            self.assertTrue(started[0].started)
            self.assertEqual(
                started[0].source,
                "settings_preview_queued",
            )
            self.assertFalse(
                pet.transformation_state.manual_end_requested
            )
            self.assertFalse(pet.transformation_state.auto_session)

    def test_manual_start_uses_auto_duration_without_becoming_auto_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
                random_source=FixedRandom(),
            )

            started = executor.request_manual_toggle(
                pet,
                now=100.0,
                intent_now=20.0,
            )

            self.assertTrue(started.started)
            self.assertEqual(started.source, "settings_preview")
            self.assertFalse(pet.transformation_state.auto_session)
            self.assertEqual(
                pet.transformation_state.auto_form_expires_at,
                110.0,
            )

    def test_manual_duration_ends_with_distinct_source_when_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.transformation_state.current_form = FORM_TRANSFORMED
            pet.transformation_state.auto_form_expires_at = 10.0
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
                random_source=FixedRandom(),
            )

            results = executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=20.0,
                transition_now=100.0,
            )

            self.assertTrue(results[0].started)
            self.assertEqual(
                results[0].source,
                "settings_preview_timeout",
            )
            self.assertFalse(pet.transformation_state.auto_session)
            self.assertEqual(
                pet.transformation_state.auto_form_expires_at,
                0.0,
            )
            self.assertEqual(
                pet.transformation_state.auto_next_attempt_at,
                0.0,
            )

    def test_expired_manual_form_retries_safe_end_while_airborne(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.transformation_state.current_form = FORM_TRANSFORMED
            pet.transformation_state.auto_form_expires_at = 10.0
            pet.vy = 1.0
            executor = TransformationExecutor(
                asset_manager_factory=lambda path, **kwargs: manager,
                random_source=FixedRandom(),
            )

            results = executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=20.0,
                transition_now=100.0,
            )

            self.assertFalse(results[0].started)
            self.assertEqual(results[0].reason, "airborne")
            self.assertFalse(pet.transformation_state.auto_session)
            self.assertEqual(
                pet.transformation_state.auto_form_expires_at,
                10.0,
            )
            self.assertEqual(pet.transformation_state.auto_retry_at, 25.0)

    def test_manual_end_schedules_shared_cooldown_after_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.mkdir(os.path.join(temp_dir, "transformed"))
            result = (["frame"], "idle", "stand", "happy")
            manager = FakeAssetManager(temp_dir, result=result)
            pet = FakePet("Tokai Teio", temp_dir, manager)
            pet.transformation_state.current_form = FORM_TRANSFORMED
            pet.transformation_state.auto_form_expires_at = 100.0
            executor = TransformationExecutor(
                phase_seconds=0.5,
                asset_manager_factory=lambda path, **kwargs: manager,
                random_source=FixedRandom(),
            )

            started = executor.request_manual_toggle(
                pet,
                now=100.0,
                intent_now=20.0,
            )
            executor.update_pet(pet, now=100.5)
            completed = executor.update_pet(pet, now=101.0)
            executor.update_auto(
                [pet],
                world_mode="sandbox",
                sim_now=22.0,
                transition_now=102.0,
            )

            self.assertTrue(started.started)
            self.assertTrue(completed.completed)
            self.assertEqual(
                pet.transformation_state.auto_next_attempt_at,
                502.0,
            )


if __name__ == "__main__":
    unittest.main()
