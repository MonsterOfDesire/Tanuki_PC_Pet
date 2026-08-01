import unittest

from tanuki_core.activity_runtime_adapter import (
    ActivityRuntimeAdapter,
    pet_has_active_activity,
)
from tanuki_core.activity_profiles import ActivityAnimationBinding
from tanuki_core.activity_state import (
    ActivityStateProjection,
    PetActivityState,
)
from tanuki_core.manifest_animation_resolver import BAND_POLICY_IGNORE


class FakeAssetManager:
    def __init__(self):
        self.calls = []

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.calls.append((context, mood_score))
        if context == "activity_work_rest":
            return (["rest-frame"], "idle", "rest", "exhausted")
        return None


class FakePet:
    def __init__(self):
        self.name = "Symboli Rudolf"
        self.activity_state = PetActivityState()
        self.asset_manager = FakeAssetManager()
        self.mood_score = 90.0
        self.dragging = False
        self.drag_press_pending = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.care_mode = "none"
        self.care_partner = None
        self.social_mode = "none"
        self.intent_kind = "none"
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.vy = 0.0
        self.offer_scene_kind = "none"
        self.held_item_kind = ""
        self.user_visible = True
        self.state = "move"
        self.state_timer = 99
        self.fall_origin_y = 20
        self.apply_calls = []
        self.refresh_calls = 0
        self.mood_sync_calls = 0

    def isVisible(self):
        return True

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now):
        return False

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return True

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def sync_mood_state_with_score(self):
        self.mood_sync_calls += 1


class ActivityRuntimeAdapterTests(unittest.TestCase):
    def test_snapshot_reports_runtime_conflicts(self):
        pet = FakePet()
        pet.dragging = True
        pet.social_mode = "following"

        snapshot = ActivityRuntimeAdapter().build_participant_snapshot(
            pet,
            role="worker",
            now=10.0,
        )

        self.assertEqual(snapshot.participant.name, "Symboli Rudolf")
        self.assertEqual(snapshot.participant.role, "worker")
        self.assertEqual(snapshot.busy_reasons, ("drag", "social"))

    def test_snapshot_treats_sleep_join_intent_as_busy(self):
        pet = FakePet()
        pet.intent_kind = "sleep_join_approach"

        snapshot = ActivityRuntimeAdapter().build_participant_snapshot(
            pet,
            role="worker",
            now=10.0,
        )

        self.assertEqual(snapshot.busy_reasons, ("sleep_join",))

    def test_snapshot_treats_pending_drag_hold_as_busy(self):
        pet = FakePet()
        pet.drag_press_pending = True

        snapshot = ActivityRuntimeAdapter().build_participant_snapshot(
            pet,
            role="worker",
            now=10.0,
        )

        self.assertEqual(snapshot.busy_reasons, ("drag",))

    def test_projection_and_expected_release_update_pet_activity_state(self):
        pet = FakePet()
        adapter = ActivityRuntimeAdapter()
        projection = ActivityStateProjection(
            participant_name=pet.name,
            state=PetActivityState(
                activity_id="work-1",
                activity_kind="rudolf_work",
                phase="working",
            ),
        )

        applied = adapter.apply_projections(
            {pet.name: pet},
            (projection,),
        )

        self.assertEqual(applied, 1)
        self.assertTrue(pet_has_active_activity(pet))
        self.assertEqual(pet.activity_state.phase, "working")
        self.assertEqual(
            adapter.clear_released_participants(
                {pet.name: pet},
                (pet.name,),
                expected_activity_id="other",
            ),
            0,
        )
        self.assertTrue(pet_has_active_activity(pet))
        self.assertEqual(
            adapter.clear_released_participants(
                {pet.name: pet},
                (pet.name,),
                expected_activity_id="work-1",
            ),
            1,
        )
        self.assertFalse(pet_has_active_activity(pet))

    def test_ignore_band_animation_uses_context_without_mood_filter(self):
        pet = FakePet()
        adapter = ActivityRuntimeAdapter()

        result = adapter.apply_phase_animation(
            pet,
            ActivityAnimationBinding(
                contexts=("activity_work_rest",),
                band_policy=BAND_POLICY_IGNORE,
            ),
        )

        self.assertTrue(result.applied)
        self.assertEqual(
            pet.asset_manager.calls,
            [("activity_work_rest", None)],
        )
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.state_timer, 0)
        self.assertEqual(pet.vy, 0.0)
        self.assertIsNone(pet.fall_origin_y)
        self.assertEqual(pet.refresh_calls, 1)

    def test_mood_delta_is_clamped_and_synchronized(self):
        pet = FakePet()
        pet.mood_score = 4.0

        applied = ActivityRuntimeAdapter().apply_mood_delta(
            pet,
            -6.0,
        )

        self.assertTrue(applied)
        self.assertEqual(pet.mood_score, 0.0)
        self.assertEqual(pet.mood_sync_calls, 1)


if __name__ == "__main__":
    unittest.main()
