import unittest
from types import SimpleNamespace

from tanuki_core.transformation_state import PetTransformationState
from tanuki_core.transformation_tendency import (
    TENDENCY_RUDOLF_RACE_CHALLENGED,
    TENDENCY_TEIO_HIGH_MOOD,
    TENDENCY_TEIO_RACE_STIMULUS,
    TransformationTendencyCoordinator,
    apply_transformation_tendency,
    evaluate_transformation_tendency,
    household_entry_is_negative,
)


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def apply_tendency_signal(
        self,
        pet,
        *,
        signal_kind,
        strength=1.0,
        sim_now,
    ):
        self.calls.append((pet.name, signal_kind, strength, sim_now))
        decision = evaluate_transformation_tendency(
            character_name=pet.name,
            current_form=pet.transformation_state.current_form,
            transitioning=pet.transformation_state.active,
            signal_kind=signal_kind,
            strength=strength,
        )
        return apply_transformation_tendency(
            pet.transformation_state,
            decision,
            character_name=pet.name,
            signal_kind=signal_kind,
            now=sim_now,
        )


def make_pet(name, *, mood_score=60.0, attempt_serial=1):
    return SimpleNamespace(
        name=name,
        mood_score=mood_score,
        transformation_state=PetTransformationState(
            auto_attempt_serial=attempt_serial,
            auto_next_attempt_at=600.0,
        ),
        is_distressed=lambda: False,
        held_item_kind="",
    )


class TransformationTendencyTests(unittest.TestCase):
    def test_completed_work_is_not_misclassified_as_negative_family_event(self):
        entry = SimpleNamespace(
            event_type="rudolf_work_completed",
            mood_delta=-6.0,
            household_pressure_delta=-6.0,
            relation_delta={},
            tags=("activity", "work", "completed"),
        )

        self.assertFalse(household_entry_is_negative(entry))

    def test_signal_advances_attempt_without_crossing_safety_window(self):
        state = PetTransformationState(auto_next_attempt_at=120.0)
        decision = evaluate_transformation_tendency(
            character_name="Tokai Teio",
            current_form="base",
            transitioning=False,
            signal_kind=TENDENCY_TEIO_RACE_STIMULUS,
        )

        result = apply_transformation_tendency(
            state,
            decision,
            character_name="Tokai Teio",
            signal_kind=TENDENCY_TEIO_RACE_STIMULUS,
            now=100.0,
        )

        self.assertTrue(result.applied)
        self.assertEqual(state.auto_next_attempt_at, 130.0)
        self.assertEqual(state.auto_tendency_score, 16.0)

    def test_high_mood_applies_once_per_transformation_attempt(self):
        teio = make_pet("Tokai Teio", mood_score=90.0)
        rudolf = make_pet("Symboli Rudolf")
        executor = FakeExecutor()
        coordinator = TransformationTendencyCoordinator()

        coordinator.update_context(
            pets=(teio, rudolf),
            household_pressure=0.0,
            executor=executor,
            now=100.0,
        )
        coordinator.update_context(
            pets=(teio, rudolf),
            household_pressure=0.0,
            executor=executor,
            now=101.0,
        )

        signals = [call[1] for call in executor.calls]
        self.assertEqual(signals.count(TENDENCY_TEIO_HIGH_MOOD), 1)

    def test_race_signals_teio_and_challenged_rudolf_independently(self):
        teio = make_pet("Tokai Teio")
        rudolf = make_pet("Symboli Rudolf")
        executor = FakeExecutor()
        event = SimpleNamespace(
            event_type="race_completed",
            challenger_name="Tokai Teio",
            opponent_name="Symboli Rudolf",
        )

        results = TransformationTendencyCoordinator().process_race_event(
            event,
            pets=(teio, rudolf),
            executor=executor,
            now=200.0,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            {call[1] for call in executor.calls},
            {
                TENDENCY_TEIO_RACE_STIMULUS,
                TENDENCY_RUDOLF_RACE_CHALLENGED,
            },
        )


if __name__ == "__main__":
    unittest.main()
