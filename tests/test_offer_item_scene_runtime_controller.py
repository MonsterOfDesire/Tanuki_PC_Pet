import unittest
from dataclasses import fields
from types import SimpleNamespace

from tanuki_core.item_scene_coordinator import ItemSceneUpdateResult
from tanuki_core.offer_item_scene_runtime_controller import (
    OfferItemSceneRuntimeController,
    OfferItemSceneSupport,
)


class OfferItemSceneRuntimeControllerTests(unittest.TestCase):
    def test_executor_receives_controller_as_scene_host(self):
        calls = []
        direct_executor = SimpleNamespace(
            start_direct_offer_scene=lambda runtime, *args, **kwargs: (
                calls.append((runtime, args, kwargs)) or True
            )
        )
        controller = _controller(
            direct_hover_scene_executor=direct_executor,
        )

        started = controller._start_direct_offer_scene(
            "honey",
            SimpleNamespace(name="Tokai Teio"),
            source="offer_tray",
        )

        self.assertTrue(started)
        self.assertIs(calls[0][0], controller)
        self.assertNotIn("app_runtime", type(calls[0][0]).__module__)

    def test_update_dispatches_scene_through_single_controller_state(self):
        calls = []
        scene_coordinator = SimpleNamespace(
            update=lambda runtime, now, **kwargs: (
                calls.append((runtime, now, kwargs))
                or ItemSceneUpdateResult(True)
            )
        )
        controller = _controller(
            item_scene_coordinator=scene_coordinator,
        )
        controller.offer_scene = SimpleNamespace(scene_kind="direct_accept")
        controller.update_pet_held_items = lambda _now: False
        controller.update_ground_offer_items = lambda _now: False
        controller.cancel_offer_scene_if_hidden_participants = lambda: False

        handled = controller.update_offer_scene(now=25.0)

        self.assertTrue(handled)
        self.assertIs(calls[0][0], controller)
        self.assertEqual(calls[0][1], 25.0)
        self.assertIn("shared_food", calls[0][2]["update_handlers"])

    def test_honey_guard_priority_skips_shared_food_lookup(self):
        calls = []
        profile_calls = []
        support = _support(
            pet_can_interact_with_offer_item=lambda *_args: True,
            start_honey_guard_scene=lambda pet, **kwargs: (
                calls.append((pet, kwargs)) or True
            ),
        )
        controller = _controller(
            support=support,
            shared_food_profile_provider=lambda *args: profile_calls.append(
                args
            ),
        )
        child = SimpleNamespace(name="Tsurumaru Tsuyoshi")

        handled = controller.start_offer_interaction_for_target(
            "honey",
            child,
        )

        self.assertTrue(handled)
        self.assertEqual(calls, [(child, {"source": "offer_tray"})])
        self.assertEqual(profile_calls, [])

    def test_hover_state_is_owned_and_cleared_by_controller(self):
        controller = _controller()
        controller.offer_hover_item_kind = "bottle"
        controller.offer_hover_target_name = "missing"
        controller.offer_hover_global_x = 100.0
        controller.offer_hover_global_y = 200.0
        controller.offer_hover_started_at = 10.0

        controller.clear_offer_hover(apply_miss=False)

        self.assertEqual(controller.offer_hover_item_kind, "")
        self.assertEqual(controller.offer_hover_target_name, "")
        self.assertEqual(controller.offer_hover_global_x, 0.0)
        self.assertEqual(controller.offer_hover_global_y, 0.0)
        self.assertEqual(controller.offer_hover_started_at, 0.0)


def _support(**overrides):
    callbacks = {
        field.name: (lambda *args, **kwargs: False)
        for field in fields(OfferItemSceneSupport)
    }
    callbacks.update(overrides)
    return OfferItemSceneSupport(**callbacks)


def _controller(
    *,
    support=None,
    item_scene_coordinator=None,
    direct_hover_scene_executor=None,
    shared_food_profile_provider=lambda *_args: None,
):
    return OfferItemSceneRuntimeController(
        pets=(),
        pet_registry=SimpleNamespace(
            find_by_name=lambda *_args, **_kwargs: None
        ),
        achievement_runtime_coordinator=SimpleNamespace(),
        profiler=SimpleNamespace(record_section=lambda *_args: None),
        support=support or _support(),
        item_scene_coordinator=item_scene_coordinator,
        direct_hover_scene_executor=direct_hover_scene_executor,
        shared_food_profile_provider=shared_food_profile_provider,
        now_provider=lambda: 10.0,
        performance_now_provider=lambda: 1.0,
    )


if __name__ == "__main__":
    unittest.main()
