import unittest

from tanuki_core.activity_coordinator import ActivityCoordinator
from tanuki_core.activity_runtime_adapter import ActivityRuntimeAdapter
from tanuki_core.activity_state import PetActivityState
from tanuki_core.chorus_executor import ChorusExecutor
from tanuki_core.chorus_rules import CHORUS_APPROACH_PHASE
from tanuki_core.chorus_state import (
    CHORUS_REACTION_AUDIENCE,
    CHORUS_REACTION_PERFORM,
    ChorusScheduleState,
    ChorusParticipantState,
    ChorusSessionState,
)
from tanuki_core.transformation_state import PetTransformationState


class FakeAssetManager:
    def __init__(self, missing=()):
        self.missing = set(missing)
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
        if context in self.missing:
            return None
        purpose = "move" if context == "activity_chorus_approach" else "idle"
        return ([f"{context}-frame"], purpose, "manifest-action", "happy")


class FakePet:
    def __init__(self, name, *, x=100.0, mood_score=60.0):
        self.name = name
        self.mood_score = mood_score
        self.is_adult = name not in {"Tokai Teio", "Tsurumaru Tsuyoshi"}
        self.asset_manager = FakeAssetManager()
        self.activity_state = PetActivityState()
        self.transformation_state = PetTransformationState()
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
        self.visible = True
        self.state = "idle"
        self.state_timer = 0
        self.fall_origin_y = None
        self.direction = 1
        self._x = float(x)
        self.apply_calls = []
        self.distressed = False
        self.change_state_calls = []
        self.context_state_calls = []
        self.move_calls = []
        self.widget_width = 100

    def isVisible(self):
        return self.visible

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now):
        return self.offer_scene_kind != "none"

    def is_distressed(self):
        return self.distressed

    def is_care_feature_enabled(self):
        return True

    def apply_animation_result(self, purpose, result):
        self.apply_calls.append((purpose, result))
        return True

    def refresh_movement_state(self):
        return None

    def change_state(self, state):
        self.change_state_calls.append(state)
        self.state = state

    def change_state_for_context_with_preferences(self, purpose, context):
        self.context_state_calls.append((purpose, context))
        self.state = purpose
        return True

    def x(self):
        return self._x

    def width(self):
        return self.widget_width

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        self.move_calls.append((float(target_x), speed_scale, min_speed))
        self._x = float(target_x)
        return True

    def clamp_x_to_virtual_geometry(self, x, width, padding=0):
        return float(x)


def build_executor(random_values=(0.0, 0.0, 0.0, 0.0)):
    sequence = iter(range(1, 100))
    rolls = iter(random_values)
    coordinator = ActivityCoordinator(
        activity_id_factory=lambda: f"chorus-{next(sequence)}",
        event_id_factory=lambda: f"event-{next(sequence)}",
    )
    executor = ChorusExecutor(
        coordinator=coordinator,
        runtime_adapter=ActivityRuntimeAdapter(),
        uniform=lambda minimum, maximum: minimum,
        random_value=lambda: next(rolls, 0.0),
        session_id_factory=lambda: "session-1",
    )
    executor.schedule = ChorusScheduleState(next_proposal_at=10.0)
    return executor, coordinator


class ChorusExecutorTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.coordinator = build_executor()
        self.tsuyoshi = FakePet("Tsurumaru Tsuyoshi", x=100.0)
        self.air_groove = FakePet("Air Groove", x=260.0)
        self.pets = (self.tsuyoshi, self.air_groove)
        self.events = []

    def update(self, now, pets=None):
        return self.executor.update(
            now=now,
            world_mode="sandbox",
            pets=self.pets if pets is None else pets,
            record_chorus_event=self.events.append,
        )

    def test_joiner_selects_perform_animation_once_and_holds_it(self):
        started = self.update(10.0)[0]
        self.assertTrue(started.started)
        self.assertEqual(len(self.executor.session.participants), 2)

        self.update(10.1)
        participant = self.executor.session.participants["Air Groove"]
        self.assertEqual(participant.reaction, CHORUS_REACTION_PERFORM)
        perform_applies = [
            call
            for call in self.air_groove.apply_calls
            if call[1][0] == ["activity_chorus_perform-frame"]
        ]
        self.assertEqual(len(perform_applies), 1)

        self.update(11.0)
        perform_applies = [
            call
            for call in self.air_groove.apply_calls
            if call[1][0] == ["activity_chorus_perform-frame"]
        ]
        self.assertEqual(len(perform_applies), 1)

    def test_dragging_first_performer_only_removes_that_character(self):
        self.update(10.0)
        self.update(10.1)

        removed = self.executor.remove_pet(
            self.tsuyoshi,
            now=11.0,
            reason="user_drag",
            pets=self.pets,
        )

        self.assertTrue(removed.removed)
        self.assertIsNotNone(self.executor.session)
        self.assertNotIn("Tsurumaru Tsuyoshi", self.executor.session.participants)
        self.assertIn("Air Groove", self.executor.session.participants)
        self.assertFalse(self.tsuyoshi.activity_state.active)
        self.assertTrue(self.air_groove.activity_state.active)
        self.assertEqual(
            self.tsuyoshi.context_state_calls,
            [("idle", "random")],
        )
        self.assertEqual(self.tsuyoshi.change_state_calls, [])

    def test_removed_character_is_not_reconsidered_in_same_session(self):
        self.update(10.0)
        self.update(10.1)
        self.executor.remove_pet(
            self.tsuyoshi,
            now=11.0,
            reason="user_drag",
            pets=self.pets,
        )

        self.update(12.0)

        self.assertNotIn("Tsurumaru Tsuyoshi", self.executor.session.participants)
        self.assertIn("Tsurumaru Tsuyoshi", self.executor.session.considered_names)

    def test_tsuyoshi_distress_releases_whole_session_for_care(self):
        self.update(10.0)
        self.update(10.1)
        self.tsuyoshi.distressed = True

        result = self.update(11.0)[0]

        self.assertTrue(result.interrupted)
        self.assertEqual(result.reason, "child_care_needed")
        self.assertIsNone(self.executor.session)
        self.assertFalse(self.tsuyoshi.activity_state.active)
        self.assertFalse(self.air_groove.activity_state.active)
        self.assertEqual(self.events[-1].event_type, "chorus_interrupted")

    def test_teio_distress_releases_whole_session_for_care(self):
        self.update(10.0)
        self.update(10.1)
        teio = FakePet("Tokai Teio", x=520.0)
        teio.distressed = True

        result = self.update(11.0, pets=(*self.pets, teio))[0]

        self.assertTrue(result.interrupted)
        self.assertEqual(result.reason, "child_care_needed")
        self.assertIsNone(self.executor.session)
        self.assertFalse(self.tsuyoshi.activity_state.active)
        self.assertFalse(self.air_groove.activity_state.active)
        self.assertEqual(self.events[-1].reason, "child_care_needed")

    def test_recovering_distressed_child_does_not_interrupt_chorus(self):
        self.update(10.0)
        self.update(10.1)
        teio = FakePet("Tokai Teio", x=520.0)
        teio.distressed = True
        teio.is_recovering = True

        results = self.update(11.0, pets=(*self.pets, teio))

        self.assertFalse(any(result.interrupted for result in results))
        self.assertIsNotNone(self.executor.session)

    def test_busy_character_does_not_enter_notice_reaction(self):
        self.air_groove.care_mode = "approach"

        self.update(10.0)

        self.assertEqual(
            tuple(self.executor.session.participants),
            ("Tsurumaru Tsuyoshi",),
        )
        self.assertNotIn(
            "Air Groove",
            self.executor.session.considered_names,
        )

        self.air_groove.care_mode = "none"
        self.update(11.0)

        self.assertIn("Air Groove", self.executor.session.participants)

    def test_social_character_is_considered_after_social_activity_ends(self):
        self.air_groove.social_mode = "mimic"
        self.update(10.0)

        self.assertNotIn(
            "Air Groove",
            self.executor.session.considered_names,
        )

        self.air_groove.social_mode = "none"
        self.update(11.0)

        self.assertIn("Air Groove", self.executor.session.participants)

    def test_initially_hidden_character_can_be_considered_after_summon(self):
        self.air_groove.visible = False
        self.update(10.0)

        self.assertNotIn(
            "Air Groove",
            self.executor.session.considered_names,
        )

        self.air_groove.visible = True
        self.update(11.0)

        self.assertIn("Air Groove", self.executor.session.participants)

    def test_notice_includes_candidate_within_fifteen_hundred_pixels(self):
        listener = FakePet("Air Groove", x=1550.0)

        self.update(10.0, pets=(self.tsuyoshi, listener))

        self.assertIn("Air Groove", self.executor.session.participants)

    def test_notice_excludes_candidate_beyond_fifteen_hundred_pixels(self):
        listener = FakePet("Air Groove", x=1701.0)

        self.update(10.0, pets=(self.tsuyoshi, listener))

        self.assertNotIn("Air Groove", self.executor.session.participants)

        listener._x = 1550.0
        self.update(11.0, pets=(self.tsuyoshi, listener))

        self.assertIn("Air Groove", self.executor.session.participants)

    def test_joined_performer_extends_session_toward_three_minute_cap(self):
        teio = FakePet("Tokai Teio", x=400.0)
        pets = (self.tsuyoshi, self.air_groove, teio)
        self.update(10.0, pets=pets)

        self.assertEqual(self.executor.session.ends_at, 100.0)

        self.update(10.1, pets=pets)

        self.assertEqual(self.executor.session.ends_at, 130.0)

    def test_approach_uses_four_pixel_speed_floor(self):
        self.update(10.0)
        self.update(10.1)

        self.assertTrue(self.air_groove.move_calls)
        _target_x, speed_scale, min_speed = self.air_groove.move_calls[-1]
        self.assertEqual(speed_scale, 1.0)
        self.assertEqual(min_speed, 4.0)

    def test_stage_spacing_uses_character_footprint_not_transparent_window(self):
        pet = FakePet("Air Groove")
        pet.widget_width = 600
        pet.radius = 100.0

        self.assertEqual(self.executor._stage_footprint_width(pet), 200.0)

    def test_later_arrivals_receive_monotonically_outer_slots(self):
        session = ChorusSessionState(
            session_id="slots",
            source="test",
            world_mode="sandbox",
            started_at=0.0,
            ends_at=60.0,
            center_x=100.0,
        )

        slots = tuple(
            self.executor._allocate_next_slot(
                session,
                CHORUS_REACTION_PERFORM,
            )
            for _ in range(6)
        )

        self.assertEqual(slots, (1, -1, 2, -2, 3, -3))

    def test_audience_uses_independent_outer_slots(self):
        session = ChorusSessionState(
            session_id="chorus-slots",
            source="autonomous",
            world_mode="sandbox",
            started_at=0.0,
            ends_at=60.0,
            center_x=100.0,
        )

        first_audience = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_AUDIENCE,
        )
        performer_slots = tuple(
            self.executor._allocate_next_slot(
                session,
                CHORUS_REACTION_PERFORM,
            )
            for _ in range(4)
        )
        second_audience = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_AUDIENCE,
        )

        self.assertEqual(performer_slots, (1, -1, 2, -2))
        self.assertEqual((first_audience, second_audience), (3, -3))

    def test_audience_prefers_nearest_outer_slot_on_its_starting_side(self):
        session = ChorusSessionState(
            session_id="audience-side",
            source="autonomous",
            world_mode="sandbox",
            started_at=0.0,
            ends_at=60.0,
            center_x=500.0,
        )
        left_audience = FakePet("Air Groove", x=100.0)
        right_audience = FakePet("Symboli Rudolf", x=900.0)

        left_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_AUDIENCE,
            preferred_side=self.executor._preferred_slot_side(
                left_audience,
                session,
            ),
        )
        session.participants[left_audience.name] = ChorusParticipantState(
            name=left_audience.name,
            reaction=CHORUS_REACTION_AUDIENCE,
            activity_id="left",
            phase=CHORUS_APPROACH_PHASE,
            slot=left_slot,
            joined_at=0.0,
        )
        second_left_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_AUDIENCE,
            preferred_side=-1,
        )
        right_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_AUDIENCE,
            preferred_side=self.executor._preferred_slot_side(
                right_audience,
                session,
            ),
        )

        self.assertEqual((left_slot, second_left_slot, right_slot), (-3, -4, 3))

    def test_performer_prefers_nearest_inner_slot_on_its_starting_side(self):
        session = ChorusSessionState(
            session_id="performer-side",
            source="autonomous",
            world_mode="sandbox",
            started_at=0.0,
            ends_at=60.0,
            center_x=500.0,
        )
        left_performer = FakePet("Air Groove", x=100.0)
        right_performer = FakePet("Symboli Rudolf", x=900.0)

        first_left_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_PERFORM,
            preferred_side=self.executor._preferred_slot_side(
                left_performer,
                session,
            ),
        )
        session.participants[left_performer.name] = ChorusParticipantState(
            name=left_performer.name,
            reaction=CHORUS_REACTION_PERFORM,
            activity_id="left",
            phase=CHORUS_APPROACH_PHASE,
            slot=first_left_slot,
            joined_at=0.0,
        )
        second_left_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_PERFORM,
            preferred_side=-1,
        )
        right_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_PERFORM,
            preferred_side=self.executor._preferred_slot_side(
                right_performer,
                session,
            ),
        )

        self.assertEqual(
            (first_left_slot, second_left_slot, right_slot),
            (-1, -2, 1),
        )

    def test_late_performer_keeps_audiences_outside_without_slot_collision(self):
        session = ChorusSessionState(
            session_id="performer-after-audience",
            source="autonomous",
            world_mode="sandbox",
            started_at=0.0,
            ends_at=60.0,
            center_x=500.0,
        )
        session.participants["audience-one"] = ChorusParticipantState(
            name="audience-one",
            reaction=CHORUS_REACTION_AUDIENCE,
            activity_id="audience-one",
            phase=CHORUS_APPROACH_PHASE,
            slot=3,
            joined_at=0.0,
        )
        session.participants["audience-two"] = ChorusParticipantState(
            name="audience-two",
            reaction=CHORUS_REACTION_AUDIENCE,
            activity_id="audience-two",
            phase=CHORUS_APPROACH_PHASE,
            slot=4,
            joined_at=0.0,
        )
        for slot in (1, 2):
            session.participants[f"performer-{slot}"] = ChorusParticipantState(
                name=f"performer-{slot}",
                reaction=CHORUS_REACTION_PERFORM,
                activity_id=f"performer-{slot}",
                phase=CHORUS_APPROACH_PHASE,
                slot=slot,
                joined_at=0.0,
            )

        performer_slot = self.executor._allocate_next_slot(
            session,
            CHORUS_REACTION_PERFORM,
            preferred_side=1,
        )

        audience_slots = tuple(
            participant.slot
            for participant in session.participants.values()
            if not participant.is_performer
        )
        self.assertEqual(performer_slot, 3)
        self.assertEqual(audience_slots, (4, 5))
        self.assertNotIn(performer_slot, audience_slots)

    def test_frequency_change_restarts_wait_with_new_policy(self):
        selected = ["frequent"]
        self.executor.frequency_provider = lambda: selected[0]
        self.executor.schedule = ChorusScheduleState(
            next_proposal_at=100.0,
            world_mode="sandbox",
            frequency_key="normal",
        )

        results = self.executor.update(
            now=20.0,
            world_mode="sandbox",
            pets=(),
        )

        self.assertEqual(results, ())
        self.assertEqual(self.executor.schedule.frequency_key, "frequent")
        self.assertEqual(self.executor.schedule.next_proposal_at, 80.0)

    def test_transformed_teio_can_autonomously_start(self):
        executor, _coordinator = build_executor()
        teio = FakePet("Tokai Teio")
        teio.transformation_state.current_form = "transformed"

        result = executor.update(
            now=10.0,
            world_mode="sandbox",
            pets=(teio,),
        )[0]

        self.assertTrue(result.started)
        self.assertEqual(tuple(executor.session.participants), ("Tokai Teio",))

    def test_sandbox_preview_starts_immediately_with_normal_reactions(self):
        executor, _coordinator = build_executor()

        result = executor.start_preview(
            now=5.0,
            world_mode="sandbox",
            pets=self.pets,
        )

        self.assertTrue(result.started)
        self.assertTrue(executor.is_preview_active())
        self.assertEqual(executor.session.source, "settings_preview")
        self.assertEqual(len(executor.session.participants), 2)

    def test_preview_is_sandbox_only_and_does_not_replace_active_chorus(self):
        executor, _coordinator = build_executor()
        rejected = executor.start_preview(
            now=5.0,
            world_mode="golden_legend",
            pets=self.pets,
        )
        started = executor.start_preview(
            now=5.0,
            world_mode="sandbox",
            pets=self.pets,
        )
        duplicate = executor.start_preview(
            now=6.0,
            world_mode="sandbox",
            pets=self.pets,
        )

        self.assertEqual(rejected.reason, "preview_requires_sandbox")
        self.assertTrue(started.started)
        self.assertEqual(duplicate.reason, "chorus_already_active")
        self.assertEqual(executor.session.session_id, started.session_id)


if __name__ == "__main__":
    unittest.main()
