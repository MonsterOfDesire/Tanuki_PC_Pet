import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tanuki_core.offer_event_adapter import OfferEventAdapter
from tanuki_core.shared_food_profiles import (
    SHARED_FOOD_OUTCOME_SHARE_BOTH,
)


class OfferEventAdapterTests(unittest.TestCase):
    def build_adapter(self, *, pet=None, scene=None):
        achievement = Mock()
        recorder = Mock()
        registry = SimpleNamespace(find_by_name=Mock(return_value=pet))
        adapter = OfferEventAdapter(
            achievement_runtime_coordinator=achievement,
            pet_registry=registry,
            record_household_event=recorder,
            scene_provider=lambda: scene,
            scene_id_provider=lambda active_scene: "offer-scene-1",
            now_provider=lambda: 25.0,
        )
        return adapter, achievement, recorder

    def test_bottle_feed_event_keeps_existing_payload(self):
        adapter, _, recorder = self.build_adapter()

        adapter.record_offer_event(
            "bottle",
            "Tokai Teio",
            "Tsurumaru Tsuyoshi",
            "bottle_feed",
        )

        payload = recorder.call_args.kwargs
        self.assertEqual(payload["event_type"], "offer_bottle_feed")
        self.assertEqual(payload["household_pressure_delta"], -3.0)
        self.assertEqual(
            payload["metadata"],
            {
                "source": "offer_tray",
                "item_kind": "bottle",
                "scene_kind": "bottle_feed",
            },
        )

    def test_honey_guard_builds_canonical_achievement_metadata(self):
        scene = SimpleNamespace(started_at=20.0)
        adapter, achievement, recorder = self.build_adapter(scene=scene)
        achievement.build_honey_guard_metadata.return_value = {
            "activity_id": "offer-scene-1"
        }

        adapter.record_offer_event(
            "honey",
            "Sirius Symboli",
            "Tsurumaru Tsuyoshi",
            "honey_guard",
        )

        achievement.build_honey_guard_metadata.assert_called_once_with(
            scene_id="offer-scene-1",
            source="offer_tray",
            started_at=20.0,
            occurred_at=25.0,
            guardian_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            item_kind="honey",
        )
        self.assertEqual(
            recorder.call_args.kwargs["metadata"],
            {"activity_id": "offer-scene-1"},
        )

    def test_shared_food_summary_and_metadata_are_owned_by_adapter(self):
        scene = SimpleNamespace(started_at=20.0)
        adapter, achievement, recorder = self.build_adapter(scene=scene)
        achievement.build_shared_food_metadata.return_value = {
            "activity_id": "offer-scene-1"
        }
        profile = SimpleNamespace(
            item_kind="carrot",
            profile_key="teio_carrot",
            success_event_type="offer_carrot_shared",
            success_summary_by_holder={
                "Tokai Teio": "帝寶和鶴寶分享了紅蘿蔔。"
            },
        )
        state = SimpleNamespace(
            holder_name="Tokai Teio",
            partner_name="Tsurumaru Tsuyoshi",
            consumer_names=("Tokai Teio", "Tsurumaru Tsuyoshi"),
            outcome_key=SHARED_FOOD_OUTCOME_SHARE_BOTH,
        )

        adapter.record_shared_food_event(profile, state)

        self.assertEqual(
            recorder.call_args.kwargs["summary"],
            "帝寶和鶴寶分享了紅蘿蔔。",
        )
        self.assertEqual(
            recorder.call_args.kwargs["metadata"],
            {"activity_id": "offer-scene-1"},
        )

    def test_mood_reward_clears_afterglow_and_caps_score(self):
        pet = SimpleNamespace(
            mood_score=98.0,
            offer_hover_reaction_cooldown_until=9.0,
            clear_negative_afterglow=Mock(),
            sync_mood_state_with_score=Mock(),
            pop_heart=Mock(),
        )
        adapter, _, _ = self.build_adapter(pet=pet)

        self.assertTrue(adapter.apply_offer_mood_reward("Tokai Teio", 6.0))

        self.assertEqual(pet.mood_score, 100.0)
        self.assertEqual(pet.offer_hover_reaction_cooldown_until, 0.0)
        pet.clear_negative_afterglow.assert_called_once_with()
        pet.pop_heart.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
