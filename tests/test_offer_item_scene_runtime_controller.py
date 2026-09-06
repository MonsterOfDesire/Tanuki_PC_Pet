import unittest
from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import Mock

from tanuki_core.item_scene_coordinator import ItemSceneUpdateResult
from tanuki_core.offer_item_scene_runtime_controller import (
    OfferItemSceneRuntimeController,
    OfferItemSceneSupport,
)
from tanuki_core.autonomous_offer_rules import (
    AUTONOMOUS_GROUND_SOURCE,
    AUTONOMOUS_OFFER_SOURCE,
    AutonomousOfferPreviewState,
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

    def test_autonomous_proposal_reuses_direct_offer_scene_flow(self):
        calls = []
        pet = _available_pet("Symboli Rudolf")
        widget = _HeldWidget()
        support = _support(
            pet_can_interact_with_offer_item=lambda *_args: True,
            pet_is_busy_for_offer_interaction=lambda *_args: False,
            choose_bottle_feed_child_for_holder=lambda *_args, **_kwargs: None,
            choose_honey_guardian_for_child=lambda *_args: "",
            build_offer_item_widget=lambda *_args, **_kwargs: widget,
            apply_held_item_behavior=lambda *_args: True,
            start_direct_offer_scene=lambda item_kind, target, **kwargs: (
                calls.append((item_kind, target.name, kwargs["source"]))
                or True
            ),
        )
        controller = _controller(
            pets=(pet,),
            support=support,
            random_provider=lambda: 0.0,
            uniform_provider=lambda minimum, maximum: minimum,
        )
        controller.autonomous_offer_schedule.next_proposal_at = 10.0

        handled = controller.update_autonomous_offer_proposal(10.0)

        self.assertTrue(handled)
        self.assertEqual(calls, [])
        self.assertEqual(pet.held_item_kind, "ramen")
        self.assertEqual(controller.autonomous_offer_preview.ends_at, 14.0)

        handled = controller.update_autonomous_offer_proposal(14.0)

        self.assertTrue(handled)
        self.assertEqual(
            calls,
            [("ramen", "Symboli Rudolf", AUTONOMOUS_OFFER_SOURCE)],
        )
        self.assertEqual(pet.held_item_kind, "")
        self.assertIsNone(controller.autonomous_offer_preview)
        self.assertEqual(
            controller.autonomous_offer_schedule.next_proposal_at,
            194.0,
        )

    def test_autonomous_preview_blocks_held_bottle_auto_start(self):
        pet = _available_pet("Symboli Rudolf")
        pet.held_item_kind = "bottle"
        pet.held_item_widget = _HeldWidget()
        controller = _controller(
            pets=(pet,),
            support=_support(
                apply_held_item_behavior=lambda *_args: True,
                choose_bottle_feed_child_for_holder=lambda *_args, **_kwargs: (
                    SimpleNamespace(name="Tsurumaru Tsuyoshi")
                ),
                start_bottle_feed_scene=Mock(return_value=True),
            ),
        )
        controller.autonomous_offer_preview = AutonomousOfferPreviewState(
            item_kind="bottle",
            actor_name=pet.name,
            started_at=10.0,
            ends_at=18.0,
        )

        self.assertTrue(controller.update_pet_held_items(11.0))

        controller.support.start_bottle_feed_scene.assert_not_called()

    def test_autonomous_tsuyoshi_honey_is_spawned_as_reserved_ground_item(self):
        child = _available_pet("Tsurumaru Tsuyoshi")
        ground_coordinator = SimpleNamespace(drop_item=Mock(return_value=True))
        support = _support(
            pet_can_interact_with_offer_item=lambda *_args: True,
            pet_is_busy_for_offer_interaction=lambda *_args: False,
            choose_honey_guardian_for_child=lambda *_args: "Sirius Symboli",
            build_offer_item_widget=lambda *_args, **_kwargs: object(),
        )
        controller = _controller(
            pets=(child,),
            support=support,
            ground_item_coordinator=ground_coordinator,
            random_provider=lambda: 0.0,
        )
        controller.autonomous_offer_schedule.next_proposal_at = 10.0

        self.assertTrue(controller.update_autonomous_offer_proposal(10.0))

        call = ground_coordinator.drop_item.call_args
        self.assertEqual(call.args[0], "honey")
        self.assertEqual(call.kwargs["source"], AUTONOMOUS_GROUND_SOURCE)
        self.assertEqual(
            call.kwargs["preferred_pickup_name"],
            "Tsurumaru Tsuyoshi",
        )


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
    pets=(),
    pet_registry=None,
    ground_item_coordinator=None,
    random_provider=lambda: 0.0,
    uniform_provider=lambda minimum, maximum: minimum,
):
    if pet_registry is None:
        by_name = {pet.name: pet for pet in pets}
        pet_registry = SimpleNamespace(
            find_by_name=lambda name, visible_only=False: by_name.get(name)
        )
    return OfferItemSceneRuntimeController(
        pets=pets,
        pet_registry=pet_registry,
        achievement_runtime_coordinator=SimpleNamespace(),
        profiler=SimpleNamespace(record_section=lambda *_args: None),
        support=support or _support(),
        item_scene_coordinator=item_scene_coordinator,
        direct_hover_scene_executor=direct_hover_scene_executor,
        ground_item_coordinator=ground_item_coordinator,
        shared_food_profile_provider=shared_food_profile_provider,
        random_provider=random_provider,
        uniform_provider=uniform_provider,
        now_provider=lambda: 10.0,
        performance_now_provider=lambda: 1.0,
    )


def _available_pet(name):
    return SimpleNamespace(
        name=name,
        held_item_kind="",
        held_item_source="none",
        held_item_started_at=0.0,
        held_item_widget=None,
        isVisible=lambda: True,
        is_offer_locked=lambda _now: False,
        x=lambda: 100,
        y=lambda: 500,
        width=lambda: 100,
        height=lambda: 100,
    )


class _HeldWidget:
    def close(self):
        pass

    def deleteLater(self):
        pass


if __name__ == "__main__":
    unittest.main()
