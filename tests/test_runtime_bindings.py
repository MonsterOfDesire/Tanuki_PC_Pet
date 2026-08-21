import unittest
from types import SimpleNamespace

from tanuki_core.runtime_bindings import bind_runtime_providers


class FakeDashboard:
    def __init__(self):
        self.bound = {}

    def _capture(self, group, values):
        self.bound[group] = values

    def set_household_data_providers(self, **providers):
        self._capture("household_data", providers)

    def set_achievement_data_provider(self, **providers):
        self._capture("achievement", providers)

    def set_household_action_providers(self, **providers):
        self._capture("household_actions", providers)

    def set_activity_action_providers(self, **providers):
        self._capture("activity_actions", providers)

    def set_household_persistence_providers(self, **providers):
        self._capture("persistence", providers)

    def set_offer_interaction_provider(self, **providers):
        self._capture("offer", providers)


class FakePet:
    pass


class RuntimeBindingsTests(unittest.TestCase):
    def build_runtime(self):
        calls = []
        dashboard = FakeDashboard()
        pet = FakePet()
        runtime = SimpleNamespace(
            dashboard=dashboard,
            pets_list=[pet],
            profiler=object(),
            household=object(),
            achievement_state=object(),
            achievement_runtime_service=SimpleNamespace(catalog=()),
            achievement_eligibility_guard=SimpleNamespace(
                observe_time_scale=lambda value: calls.append(
                    ("time_scale", value)
                )
            ),
            achievement_runtime_coordinator=SimpleNamespace(
                build_cabinet_snapshot=lambda: "achievements",
                observe_time_scale=lambda value: calls.append(
                    ("time_scale", value)
                ),
                handle_ambient_animation_context=(
                    lambda pet, context, now: calls.append(
                        ("ambient_animation", pet, context, now)
                    )
                ),
            ),
            interrupt_pet_activity_for_user=(
                lambda target, reason="": calls.append(
                    ("interrupt", target, reason)
                )
            ),
            update_sleep_join_behavior=(
                lambda target, pets, now: calls.append(
                    ("sleep_join", target, pets, now)
                )
            ),
            handle_care_activity_event=(
                lambda stage, caregiver, target, **kwargs: calls.append(
                    ("care", stage, caregiver, target, kwargs)
                )
            ),
            recent_household_events=lambda limit=24: ("events", limit),
            get_activity_rhythm_snapshot=lambda: "rhythm",
            donate_household_fund=(
                lambda amount=100: calls.append(("donate", amount))
            ),
            preview_rudolf_work=lambda: "work",
            is_rudolf_work_preview_active=lambda: False,
            preview_rudolf_teio_race=lambda: "race",
            is_race_preview_active=lambda: False,
            preview_chorus=lambda: "chorus",
            is_chorus_preview_active=lambda: False,
            toggle_transformation_preview=lambda name: ("transform", name),
            get_transformation_preview_state=lambda name: ("form", name),
            toggle_sleep_control=lambda name: ("sleep", name),
            get_sleep_control_state=lambda name: ("sleep_state", name),
            capture_household_persistence_state=lambda: {"saved": True},
            apply_household_persistence_state=lambda payload: payload,
            handle_world_mode_change=(
                lambda mode, previous_mode=None: (mode, previous_mode)
            ),
            handle_offer_drop=lambda **kwargs: ("drop", kwargs),
            handle_offer_hover=lambda **kwargs: ("hover", kwargs),
            clear_offer_hover=lambda: "clear",
        )
        return runtime, dashboard, pet, calls

    def test_bindings_assign_pet_and_dashboard_providers(self):
        runtime, dashboard, pet, calls = self.build_runtime()

        bind_runtime_providers(runtime)

        self.assertIs(pet.runtime_profiler, runtime.profiler)
        self.assertEqual(
            set(dashboard.bound),
            {
                "household_data",
                "achievement",
                "household_actions",
                "activity_actions",
                "persistence",
                "offer",
            },
        )
        self.assertEqual(
            dashboard.bound["household_data"]["activity_rhythm_provider"](),
            "rhythm",
        )
        self.assertEqual(
            dashboard.bound["achievement"][
                "achievement_snapshot_provider"
            ](),
            "achievements",
        )
        self.assertEqual(
            dashboard.bound["activity_actions"]["race_preview_provider"](),
            "race",
        )
        self.assertEqual(
            dashboard.bound["offer"]["offer_drop_provider"](
                "honey",
                (10, 20),
            ),
            (
                "drop",
                {"item_kind": "honey", "global_pos": (10, 20)},
            ),
        )

        pet.activity_user_interrupt_provider(pet, reason="user_drag")
        self.assertIn(("interrupt", pet, "user_drag"), calls)
        pet.ambient_animation_event_provider(
            pet,
            "side_ready_followup",
            now=42.0,
        )
        self.assertIn(
            (
                "ambient_animation",
                pet,
                "side_ready_followup",
                42.0,
            ),
            calls,
        )


if __name__ == "__main__":
    unittest.main()
