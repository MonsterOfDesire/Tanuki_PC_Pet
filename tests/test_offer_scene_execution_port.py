import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tanuki_core.offer_scene_execution_port import (
    OfferSceneExecutionPort,
    adapt_offer_scene_executor,
    ensure_offer_scene_execution_port,
)


class OfferSceneExecutionPortTests(unittest.TestCase):
    def build_host(self):
        coordinator = SimpleNamespace(
            start_scene=Mock(return_value="started"),
            get_scene_id=Mock(return_value="scene-1"),
        )
        host = SimpleNamespace(
            offer_scene=SimpleNamespace(scene_kind="direct_accept"),
            offer_hover_item_kind="bottle",
            offer_hover_target_name="Tokai Teio",
            offer_hover_global_x=10.0,
            offer_hover_global_y=20.0,
            offer_hover_started_at=30.0,
            item_scene_coordinator=coordinator,
            clear_offer_scene=Mock(),
            refresh_offer_scene_locks=Mock(),
            lock_pet_for_offer_scene=Mock(),
            clear_offer_hover=Mock(),
        )
        return host, coordinator

    def test_scene_state_port_owns_start_and_hover_access(self):
        host, coordinator = self.build_host()
        port = OfferSceneExecutionPort.from_host(host)

        self.assertEqual(
            port.scene.start(scene_kind="direct_accept"),
            "started",
        )
        coordinator.start_scene.assert_called_once_with(
            host,
            scene_kind="direct_accept",
        )
        port.hover.target_name = "Tsurumaru Tsuyoshi"
        port.hover.global_x = 44.0
        self.assertEqual(host.offer_hover_target_name, "Tsurumaru Tsuyoshi")
        self.assertEqual(host.offer_hover_global_x, 44.0)

    def test_callbacks_remain_dynamic_after_port_creation(self):
        host, _ = self.build_host()
        first = Mock()
        second = Mock()
        host.record_offer_event = first
        port = OfferSceneExecutionPort.from_host(host)

        host.record_offer_event = second
        port.events.record_offer_event("bottle", "a", "b", "direct_accept")

        first.assert_not_called()
        second.assert_called_once_with(
            "bottle",
            "a",
            "b",
            "direct_accept",
        )

    def test_executor_adapter_coerces_legacy_host_and_reuses_cached_port(self):
        @adapt_offer_scene_executor
        class ExampleExecutor:
            def current_scene(self, port):
                return port.scene.current

        host, _ = self.build_host()
        cached = OfferSceneExecutionPort.from_host(host)
        host.offer_scene_execution_port = cached

        self.assertIs(ensure_offer_scene_execution_port(host), cached)
        self.assertIs(ExampleExecutor().current_scene(host), host.offer_scene)


if __name__ == "__main__":
    unittest.main()
