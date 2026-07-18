import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.qt_test_support import QT_BINDINGS_AVAILABLE, QtApplicationTestCase

try:
    from tanuki_core.app_runtime import ActiveOfferScene, TanukiAppRuntime
    from tanuki_core.offer_interaction_rules import ITEM_BOTTLE, ITEM_HONEY, ITEM_RAMEN
except (ImportError, ModuleNotFoundError) as exc:
    TanukiAppRuntime = None
    ActiveOfferScene = None
    ITEM_BOTTLE = "bottle"
    ITEM_HONEY = "honey"
    ITEM_RAMEN = "ramen"
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class FakeFrame:
    def __init__(self, label, width=240, height=240):
        self.label = label
        self._width = width
        self._height = height

    def width(self):
        return self._width

    def height(self):
        return self._height


class FakeOfferItemWidget:
    def __init__(self):
        self._width = 48
        self._height = 48
        self.position = None
        self.visible = False

    def width(self):
        return self._width

    def height(self):
        return self._height

    def move_to(self, x, y):
        self.position = (x, y)

    def show(self):
        self.visible = True

    def raise_(self):
        return None

    def close(self):
        self.visible = False

    def deleteLater(self):
        return None


class FakePet:
    def __init__(self, name, visible=True):
        self.name = name
        self._visible = visible
        self.offer_scene_kind = "none"
        self.offer_locked_until = 0.0
        self.state = "move"
        self.state_timer = 10
        self.mood_score = 50.0
        self.current_frames = []
        self.current_purpose = "move"
        self.current_action_tag = "run"
        self.current_mood_tag = "happy"
        self.vy = 0.0
        self.fall_origin_y = 10.0
        self.refresh_calls = 0
        self.ensure_calls = []
        self.change_calls = []
        self.context_calls = []
        self.context_successes = set()
        self.reset_calls = 0
        self.move_toward_calls = []
        self.synced = 0
        self.hearts = 0
        self.reaction_calls = []
        self.dragging = False
        self.direction = 1
        self._x = 100
        self._y = 100
        self._width = 240
        self._height = 240
        self.original_face_left = True
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.stop_window_flight_calls = []
        self.detach_calls = 0
        self.care_mode = "none"
        self.care_partner = None
        self.is_hugging = False
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0
        self.perception_situation_tag = "stable"
        self.expression_animation_context = "ambient"
        self.expression_relation_overlay = "none"
        self.expression_focus_target_name = ""
        self.expression_posture_bias = "neutral"
        self.expression_spacing_bias = "neutral"
        self.expression_look_at_target = False
        self.relationship_focus_target_name = ""
        self.held_item_kind = ""
        self.held_item_source = "none"
        self.held_item_started_at = 0.0
        self.held_item_widget = None
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_care_block_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()
        self.offer_hover_reaction_cooldown_until = 0.0
        self.offer_miss_event_cooldown_until = 0.0
        self.log_icons = 0
        self.asset_manager = FakeAssetManager()

    def isVisible(self):
        return self._visible

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._width

    def height(self):
        return self._height

    def distance_to(self, other):
        return abs(other.x() - self.x())

    def get_effective_scale(self):
        return 1.0

    def get_surface_snapshot(self):
        return SimpleNamespace(floor_top_y=self._y + self._height)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods):
        self.ensure_calls.append((list(candidates), list(preferred_moods)))
        return True

    def ensure_candidate_animation(self, candidates):
        self.ensure_calls.append((list(candidates), []))
        return True

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        self.change_calls.append((list(candidates), list(preferred_moods), list(forbidden or ())))
        return False

    def change_state_for_context_with_preferences(
        self,
        purpose,
        context,
        preferred_moods=None,
        forbidden=None,
        preserve=False,
        ignore_mood_band=False,
    ):
        self.context_calls.append(
            (
                purpose,
                context,
                tuple(preferred_moods or ()),
                tuple(forbidden or ()),
                bool(preserve),
                bool(ignore_mood_band),
            )
        )
        if (purpose, context) not in self.context_successes:
            return False
        mood_tag = (tuple(preferred_moods or ()) or ("happy",))[0]
        self.current_frames = [f"{purpose}:{context}:{mood_tag}"]
        self.current_purpose = purpose
        self.current_action_tag = context
        self.current_mood_tag = mood_tag
        return True

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def sync_mood_state_with_score(self):
        self.synced += 1

    def pop_heart(self):
        self.hearts += 1

    def pop_log_icon(self):
        self.log_icons += 1

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        self.move_toward_calls.append((target_x, speed_scale, min_speed))
        return True

    def get_base_speed(self):
        return 2.0

    def reset_stationary_move_mode(self):
        self.reset_calls += 1

    def stop_window_flight(self, apply_cooldown=True):
        self.stop_window_flight_calls.append(apply_cooldown)
        self.flight_mode = "none"

    def detach_from_window_surface(self):
        self.detach_calls += 1
        self.perched_window_hwnd = 0

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.current_frames = frames
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True

    def start_negative_afterglow(
        self,
        duration=5.0,
        preferred_moods=None,
        forbidden_moods=None,
        now=0.0,
        block_care=False,
    ):
        self.negative_afterglow_until = float(now) + float(duration)
        if block_care:
            self.negative_afterglow_care_block_until = self.negative_afterglow_until
        self.negative_afterglow_preferred_moods = tuple(preferred_moods or ())
        self.negative_afterglow_forbidden_moods = tuple(forbidden_moods or ())

    def clear_negative_afterglow(self):
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_care_block_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()

    def apply_reaction(self, preferred_moods, is_negative=False):
        self.reaction_calls.append((tuple(preferred_moods), bool(is_negative)))

    def is_under_care(self, now):
        return (
            self.care_partner is not None and
            self.care_lock_mode != "none" and
            float(now) < float(self.care_lock_end_time)
        )

    def is_offer_locked(self, now=None):
        now = 0.0 if now is None else float(now)
        return (
            self.offer_scene_kind != "none" or
            float(self.offer_locked_until or 0.0) > now
        )


class FakeAssetManager:
    def __init__(self):
        self.contextual_calls = []
        self.contextual_results = {}

    def get_record(self, purpose, action_type, mood_tag):
        if (purpose, action_type, mood_tag) in {
            ("move", "run", "angry"),
            ("move", "run", "scold"),
            ("move", "run_stretch", "hurry"),
            ("move", "jog", "cry"),
            ("move", "climb", "happy"),
            ("move", "climb", "smile"),
            ("move", "climb", "think"),
            ("idle", "stand_hand", "sad"),
            ("idle", "stand_hand", "angry"),
            ("idle", "stand_hand", "smile"),
            ("idle", "stand_hand", "think"),
            ("idle", "stand", "sad"),
            ("idle", "stand", "think"),
            ("idle", "stand", "smile"),
            ("idle", "lie", "sad"),
            ("idle", "lie", "cry"),
            ("idle", "lie", "hard-cry"),
            ("idle", "get", "happy"),
            ("idle", "get", "smile"),
            ("idle", "get", "angry"),
            ("idle", "get", "think"),
            ("idle", "drink", "happy"),
            ("idle", "drink", "smile"),
            ("idle", "drink", "relief"),
            ("idle", "stand_open", "think"),
            ("idle", "stand_open", "relief"),
            ("idle", "side_face_hand", "happy"),
            ("idle", "side_face_hand", "smile"),
            ("idle", "side_face_hand", "think"),
            ("idle", "sit_no", "sad"),
            ("idle", "sit_no", "cry"),
            ("idle", "sit_no", "hard-cry"),
            ("idle", "side", "sad"),
            ("idle", "side", "cry"),
            ("idle", "side", "hard-cry"),
            ("idle", "squat", "sad"),
            ("idle", "squat", "cry"),
            ("idle", "squat", "hard-cry"),
        }:
            return {"frames": [FakeFrame(f"{purpose}:{action_type}:{mood_tag}")]}
        return None

    def get_record_weight(self, record):
        return 1.0

    def choose_weighted_result(self, results):
        return results[0][:3] if results else None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None):
        forbidden = set(forbidden or ())
        for mood_tag in preferred_moods:
            if mood_tag in forbidden:
                continue
            record = self.get_record(purpose, action_type, mood_tag)
            if record:
                return record["frames"], action_type, mood_tag
        return None

    def get_safe_reaction_result(self, purpose, preferred_moods, forbidden=None):
        forbidden = set(forbidden or ())
        for action_type in ("side", "sit_no", "lie", "squat", "stand"):
            for mood_tag in preferred_moods:
                if mood_tag in forbidden:
                    continue
                record = self.get_record(purpose, action_type, mood_tag)
                if record:
                    return record["frames"], action_type, mood_tag
        return None

    def get_contextual_result(
        self,
        purpose,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        self.contextual_calls.append(
            (
                purpose,
                context,
                tuple(preferred_moods or ()),
                tuple(forbidden or ()),
                mood_score,
                ordered_preferences,
            )
        )
        return self.contextual_results.get((purpose, context))


@unittest.skipIf(
    TanukiAppRuntime is None or not QT_BINDINGS_AVAILABLE,
    f"PyQt6 unavailable: {IMPORT_ERROR}",
)
class OfferInteractionRuntimeTests(QtApplicationTestCase):
    def build_runtime(self, pets, dashboard=None):
        dashboard = dashboard or SimpleNamespace(refresh_household_summary_if_open=lambda: None)
        runtime = TanukiAppRuntime(
            app=None,
            settings_provider=SimpleNamespace(world_mode="sandbox"),
            config_store=None,
            save_scheduler=None,
            window_tracker=None,
            pets_dict={},
            pets_list=pets,
            dashboard=dashboard,
            sensor=None,
            monitor=None,
        )
        runtime.build_offer_item_widget = lambda *_args, **_kwargs: FakeOfferItemWidget()
        return runtime

    def test_offer_context_reference_frame_uses_asset_manager_without_applying_state(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        pet.current_frames = []
        pet.asset_manager.contextual_results[("move", "bottle_feed_child_drink")] = (
            ["drink-reference"],
            "crawl_drink",
            "happy",
        )
        runtime = self.build_runtime([pet])

        frame = runtime.get_offer_reference_frame_for_context(
            pet,
            "bottle_feed_child_drink",
            ["happy", "smile"],
        )

        self.assertEqual(frame, "drink-reference")
        self.assertEqual(
            pet.asset_manager.contextual_calls,
            [
                ("idle", "bottle_feed_child_drink", ("happy", "smile"), (), 50.0, True),
                ("move", "bottle_feed_child_drink", ("happy", "smile"), (), 50.0, True),
            ],
        )
        self.assertEqual(pet.current_action_tag, "run")
        self.assertEqual(pet.current_frames, [])

    def test_update_offer_hover_preview_uses_preview_candidates(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = "bottle"
        runtime.offer_hover_target_name = "Tsurumaru Tsuyoshi"
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_started_at = 10.0

        handled = runtime.update_offer_hover_preview(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.offer_scene_kind, "hover_preview")
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.ensure_calls[0][0], [("idle", "get")])
        self.assertEqual(pet.direction, -1)
        self.assertEqual(pet.perception_situation_tag, "locked")
        self.assertEqual(pet.refresh_calls, 1)

    def test_update_offer_hover_preview_prefers_manifest_context(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        pet.context_successes.add(("idle", "offer_preview"))
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = "bottle"
        runtime.offer_hover_target_name = "Tsurumaru Tsuyoshi"
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_started_at = 10.0

        handled = runtime.update_offer_hover_preview(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.context_calls[0][1], "offer_preview")
        self.assertEqual(pet.ensure_calls, [])

    def test_find_offer_hover_target_ignores_unsupported_item_even_with_preview_context(self):
        pet = FakePet("Air Groove")
        pet.context_successes.add(("idle", "offer_preview"))
        runtime = self.build_runtime([pet])

        target = runtime.find_offer_hover_target(
            ITEM_RAMEN,
            SimpleNamespace(x=lambda: pet.x() + 20, y=lambda: pet.y() + 20),
        )

        self.assertIsNone(target)
        self.assertEqual(pet.context_calls, [])

    def test_update_offer_hover_preview_clears_unsupported_target(self):
        pet = FakePet("Air Groove")
        pet.context_successes.add(("idle", "offer_preview"))
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = ITEM_RAMEN
        runtime.offer_hover_target_name = "Air Groove"
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_started_at = 10.0

        handled = runtime.update_offer_hover_preview(10.0)

        self.assertFalse(handled)
        self.assertEqual(runtime.offer_hover_item_kind, "")
        self.assertEqual(pet.context_calls, [])

    def test_update_offer_hover_preview_can_start_hover_timeout_reaction_scene(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = "bottle"
        runtime.offer_hover_target_name = "Tsurumaru Tsuyoshi"
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_global_y = 120.0
        runtime.offer_hover_started_at = 10.0

        with patch("tanuki_core.app_runtime.random.choice", side_effect=lambda seq: seq[0]):
            handled = runtime.update_offer_hover_preview(15.1)

        self.assertTrue(handled)
        self.assertIsNotNone(runtime.offer_scene)
        self.assertEqual(runtime.offer_scene.scene_kind, "hover_timeout_reaction")
        self.assertEqual(runtime.offer_scene.hover_reaction_stage_index, 0)
        self.assertTrue(runtime.offer_scene.hover_reaction_avoid_cursor)
        self.assertEqual(pet.mood_score, 50.0)
        self.assertAlmostEqual(pet.negative_afterglow_until, 0.0)
        self.assertAlmostEqual(pet.offer_hover_reaction_cooldown_until, 0.0)
        self.assertEqual(pet.direction, -1)

    def test_update_offer_hover_preview_clears_when_target_enters_care(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        pet.care_mode = "approach"
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = "bottle"
        runtime.offer_hover_target_name = "Tsurumaru Tsuyoshi"
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_global_y = 120.0
        runtime.offer_hover_started_at = 10.0

        handled = runtime.update_offer_hover_preview(10.2)

        self.assertFalse(handled)
        self.assertEqual(runtime.offer_hover_item_kind, "")
        self.assertEqual(runtime.offer_hover_target_name, "")
        self.assertEqual(pet.offer_scene_kind, "none")

    def test_pet_is_busy_for_offer_interaction_includes_flight(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        pet.flight_mode = "window_flight"
        runtime = self.build_runtime([pet])

        self.assertTrue(runtime.pet_is_busy_for_offer_interaction(pet, 10.0))

    def test_collect_pending_social_log_events_records_sandbox_social_entry(self):
        pet = FakePet("Symboli Rudolf")
        pet.pending_social_log_event = {
            "occurred_at": 22.0,
            "event_type": "observe_social_log",
            "summary": "魯道夫注意到帝寶正在做自己的事。",
            "actor_name": "Symboli Rudolf",
            "target_name": "Tokai Teio",
            "relation_delta": {"familiarity": 0.12},
            "tags": ("observe", "ambient_social"),
            "metadata": {"source": "observe"},
        }
        runtime = self.build_runtime([pet])

        entries = runtime.collect_pending_social_log_events(now=22.0)

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].channel, "social")
        self.assertEqual(entries[0].category, "social")
        self.assertEqual(entries[0].event_type, "observe_social_log")
        self.assertEqual(entries[0].relation_delta, {"familiarity": 0.12})
        self.assertEqual(entries[0].tags, ("observe", "ambient_social"))
        self.assertEqual(pet.pending_social_log_event, {})
        self.assertEqual(pet.log_icons, 1)
        relation = runtime.household.relationships.get_entry("Symboli Rudolf", "Tokai Teio")
        self.assertIsNotNone(relation)
        self.assertEqual(relation.familiarity, 0.12)

    def test_record_household_event_uses_target_icon_when_actor_is_player(self):
        pet = FakePet("Tokai Teio")
        runtime = self.build_runtime([pet])

        runtime.record_household_event(
            occurred_at=30.0,
            category="player_offer",
            event_type="offer_honey_success",
            summary="帝寶接過蜂蜜。",
            actor_name="Player",
            target_name="Tokai Teio",
        )

        self.assertEqual(pet.log_icons, 1)

    def test_record_household_event_refreshes_open_social_and_relationship_views(self):
        class FakeDashboard:
            def __init__(self):
                self.summary_refreshes = 0
                self.social_refreshes = 0
                self.relationship_refreshes = 0

            def refresh_household_summary_if_open(self):
                self.summary_refreshes += 1

            def refresh_social_log_if_open(self):
                self.social_refreshes += 1

            def refresh_relationship_table_if_open(self):
                self.relationship_refreshes += 1

        dashboard = FakeDashboard()
        runtime = self.build_runtime([], dashboard=dashboard)

        runtime.record_household_event(
            occurred_at=30.0,
            category="social",
            event_type="post_observe_social_log",
            summary="魯道夫和帝寶小小拌了幾句嘴。",
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            relation_delta={"tension": 0.2},
        )

        self.assertEqual(dashboard.summary_refreshes, 0)
        self.assertEqual(dashboard.social_refreshes, 1)
        self.assertEqual(dashboard.relationship_refreshes, 1)

    def test_record_offer_honey_guard_adds_visible_negative_relationship_delta(self):
        guardian = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([guardian, child])

        runtime.record_offer_event(
            ITEM_HONEY,
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            scene_kind="honey_guard",
            source="offer_tray",
        )

        entry = runtime.household_event_log.entries[-1]
        relation = runtime.household.relationships.get_entry("Symboli Rudolf", "Tsurumaru Tsuyoshi")
        self.assertEqual(entry.relation_delta, {"trust": -0.05, "attachment": 0.05, "tension": 0.35})
        self.assertIsNotNone(relation)
        self.assertEqual(relation.trust, 0.0)
        self.assertEqual(relation.attachment, 0.05)
        self.assertEqual(relation.tension, 0.35)

    def test_handle_offer_drop_can_accept_during_nonfinal_hover_timeout_stage(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="hover_timeout_reaction",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="reaction",
            stage_initialized=True,
            stage_ends_at=20.0,
            scene_ends_at=24.0,
            source="offer_hover",
            hover_reaction_variant_label="test",
            hover_reaction_avoid_cursor=True,
            hover_reaction_stage_index=0,
            hover_reaction_stages=(
                SimpleNamespace(purpose="idle", action_type="get", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="idle", action_type="side_shake", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="move", action_type="climb", mood_tag="angry", duration_seconds=0.95),
            ),
        )

        with patch.object(runtime, "find_offer_drop_target", return_value=pet), \
             patch.object(runtime, "start_direct_offer_scene", return_value=True) as mocked_start:
            handled = runtime.handle_offer_drop(item_kind="bottle", global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_start.assert_called_once_with("bottle", pet, source="offer_tray")

    def test_handle_offer_drop_can_accept_during_first_hover_timeout_stage_by_preview_range(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="hover_timeout_reaction",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="reaction",
            stage_initialized=True,
            stage_ends_at=20.0,
            scene_ends_at=24.0,
            source="offer_hover",
            hover_reaction_variant_label="test",
            hover_reaction_avoid_cursor=True,
            hover_reaction_stage_index=0,
            hover_reaction_stages=(
                SimpleNamespace(purpose="idle", action_type="get", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="idle", action_type="side_shake", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="move", action_type="climb", mood_tag="angry", duration_seconds=0.95),
            ),
        )

        with patch.object(runtime, "find_offer_drop_target", return_value=None), \
             patch.object(runtime, "find_offer_hover_target", return_value=pet), \
             patch.object(runtime, "start_direct_offer_scene", return_value=True) as mocked_start:
            handled = runtime.handle_offer_drop(item_kind="bottle", global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_start.assert_called_once_with("bottle", pet, source="offer_tray")

    def test_handle_offer_drop_falls_to_ground_on_later_hover_timeout_stage(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="hover_timeout_reaction",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="reaction",
            stage_initialized=True,
            stage_ends_at=20.0,
            scene_ends_at=24.0,
            source="offer_hover",
            hover_reaction_variant_label="test",
            hover_reaction_avoid_cursor=True,
            hover_reaction_stage_index=1,
            hover_reaction_stages=(
                SimpleNamespace(purpose="idle", action_type="get", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="idle", action_type="side_shake", mood_tag="angry", duration_seconds=3.0),
                SimpleNamespace(purpose="move", action_type="climb", mood_tag="angry", duration_seconds=0.95),
            ),
        )

        with patch.object(runtime, "drop_ground_offer_item", return_value=True) as mocked_drop, \
             patch.object(runtime, "start_direct_offer_scene", return_value=True) as mocked_start:
            handled = runtime.handle_offer_drop(item_kind="bottle", global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_drop.assert_called_once()
        mocked_start.assert_not_called()

    def test_hover_timeout_reaction_failure_applies_penalty_on_scene_end(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="hover_timeout_reaction",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="reaction",
            stage_initialized=True,
            stage_ends_at=10.0,
            scene_ends_at=10.0,
            source="offer_hover",
            hover_reaction_variant_label="test",
            hover_reaction_avoid_cursor=False,
            hover_reaction_stage_index=0,
            hover_reaction_stages=(
                SimpleNamespace(purpose="idle", action_type="get", mood_tag="sad", duration_seconds=3.0),
            ),
        )

        handled = runtime.update_offer_hover_timeout_reaction_scene(10.1)

        self.assertFalse(handled)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(pet.mood_score, 20.0)
        self.assertAlmostEqual(pet.offer_hover_reaction_cooldown_until, 13.1)
        self.assertAlmostEqual(pet.negative_afterglow_until, 14.1)

    def test_hover_timeout_reaction_avoid_variant_faces_and_moves_away_from_cursor(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="hover_timeout_reaction",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="reaction",
            stage_initialized=False,
            stage_ends_at=10.95,
            scene_ends_at=12.25,
            source="offer_hover",
            hover_reaction_variant_label="test",
            hover_reaction_avoid_cursor=True,
            hover_reaction_stage_index=2,
            hover_reaction_stages=(
                None,
                None,
                SimpleNamespace(purpose="move", action_type="jog", mood_tag="cry", duration_seconds=0.95),
            ),
        )
        runtime.offer_hover_global_x = 50.0
        runtime.offer_hover_global_y = 120.0

        handled = runtime.update_offer_hover_timeout_reaction_scene(10.1)

        self.assertTrue(handled)
        self.assertEqual(pet.direction, 1)
        self.assertEqual(pet.move_toward_calls[0][1], 1.15)

    def test_update_direct_offer_scene_uses_accept_candidates(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="direct_accept",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="accept",
            stage_ends_at=20.0,
            scene_ends_at=20.0,
        )

        handled = runtime.update_direct_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.ensure_calls[0][0], [("idle", "drink")])
        self.assertEqual(pet.perception_situation_tag, "locked")

    def test_update_direct_offer_scene_prefers_manifest_accept_context(self):
        pet = FakePet("Tsurumaru Tsuyoshi")
        pet.context_successes.add(("idle", "offer_accept_milk"))
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="direct_accept",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="accept",
            stage_ends_at=20.0,
            scene_ends_at=20.0,
        )

        handled = runtime.update_direct_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.context_calls[0][1], "offer_accept_milk")
        self.assertEqual(pet.ensure_calls, [])

    def test_update_direct_offer_scene_allows_mobile_accept_when_move_context_exists(self):
        pet = FakePet("Tokai Teio")
        pet.context_successes.add(("move", "offer_accept_honey"))
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_HONEY,
            scene_kind="direct_accept",
            actor_name="Tokai Teio",
            target_name="Tokai Teio",
            stage="accept",
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            direct_accept_purpose_order=("move", "idle"),
        )

        handled = runtime.update_direct_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.context_calls[0][0], "move")
        self.assertEqual(pet.current_purpose, "move")
        self.assertEqual(pet.state, "move")
        self.assertEqual(len(pet.move_toward_calls), 1)
        self.assertEqual(pet.ensure_calls, [])

    def test_update_direct_offer_scene_can_choose_stationary_accept_even_when_move_context_exists(self):
        pet = FakePet("Tokai Teio")
        pet.context_successes.add(("move", "offer_accept_honey"))
        pet.context_successes.add(("idle", "offer_accept_honey"))
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_HONEY,
            scene_kind="direct_accept",
            actor_name="Tokai Teio",
            target_name="Tokai Teio",
            stage="accept",
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            direct_accept_purpose_order=("idle", "move"),
        )

        handled = runtime.update_direct_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(pet.context_calls[0][0], "idle")
        self.assertEqual(pet.current_purpose, "idle")
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.move_toward_calls, [])

    def test_update_offer_scene_cancels_direct_accept_when_target_hidden(self):
        pet = FakePet("Tsurumaru Tsuyoshi", visible=False)
        runtime = self.build_runtime([pet])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="bottle",
            scene_kind="direct_accept",
            actor_name="Tsurumaru Tsuyoshi",
            target_name="Tsurumaru Tsuyoshi",
            stage="accept",
            stage_ends_at=20.0,
            scene_ends_at=20.0,
        )

        handled = runtime.update_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertIsNone(runtime.offer_scene)

    def test_handle_offer_drop_uses_generic_direct_accept_for_new_item(self):
        pet = FakePet("Symboli Rudolf")
        runtime = self.build_runtime([pet])

        with patch.object(runtime, "find_offer_drop_target", return_value=pet), \
             patch.object(runtime, "start_direct_offer_scene", return_value=True) as mocked_start:
            handled = runtime.handle_offer_drop(item_kind=ITEM_RAMEN, global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_start.assert_called_once_with(ITEM_RAMEN, pet, source="offer_tray")

    def test_handle_offer_drop_routes_bottle_for_adult_into_bottle_feed(self):
        holder = FakePet("Symboli Rudolf")
        runtime = self.build_runtime([holder])

        with patch.object(runtime, "find_offer_drop_target", return_value=holder), \
             patch.object(runtime, "start_bottle_feed_scene", return_value=True) as mocked_start:
            handled = runtime.handle_offer_drop(item_kind=ITEM_BOTTLE, global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_start.assert_called_once_with(holder, source="offer_tray")

    def test_apply_offer_mood_reward_increases_mood_and_triggers_heart(self):
        pet = FakePet("Tokai Teio")
        pet.negative_afterglow_until = 20.0
        pet.negative_afterglow_preferred_moods = ("sad",)
        pet.negative_afterglow_forbidden_moods = ("happy",)
        pet.offer_hover_reaction_cooldown_until = 30.0
        runtime = self.build_runtime([pet])

        applied = runtime.apply_offer_mood_reward("Tokai Teio", amount=10.0)

        self.assertTrue(applied)
        self.assertEqual(pet.mood_score, 60.0)
        self.assertEqual(pet.negative_afterglow_until, 0.0)
        self.assertEqual(pet.negative_afterglow_preferred_moods, ())
        self.assertEqual(pet.negative_afterglow_forbidden_moods, ())
        self.assertEqual(pet.offer_hover_reaction_cooldown_until, 0.0)
        self.assertEqual(pet.synced, 1)
        self.assertEqual(pet.hearts, 1)

    def test_clear_offer_hover_applies_offer_miss_penalty_only_for_failed_hover(self):
        pet = FakePet("Tokai Teio")
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = ITEM_RAMEN
        runtime.offer_hover_target_name = "Tokai Teio"
        runtime.offer_hover_started_at = 10.0

        with patch("tanuki_core.app_runtime.app_now", return_value=12.5):
            runtime.clear_offer_hover()

        self.assertEqual(runtime.offer_hover_item_kind, "")
        self.assertEqual(runtime.offer_hover_target_name, "")
        self.assertEqual(pet.mood_score, 46.0)
        self.assertAlmostEqual(pet.offer_miss_event_cooldown_until, 24.5)
        self.assertAlmostEqual(pet.negative_afterglow_until, 15.5)
        self.assertEqual(pet.reaction_calls, [(("sad", "think"), True)])

    def test_handle_offer_drop_success_does_not_apply_offer_miss_penalty(self):
        pet = FakePet("Tokai Teio")
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = ITEM_RAMEN
        runtime.offer_hover_target_name = "Tokai Teio"
        runtime.offer_hover_started_at = 10.0

        with patch("tanuki_core.app_runtime.app_now", return_value=12.5), \
             patch.object(runtime, "find_offer_drop_target", return_value=pet), \
             patch.object(runtime, "start_direct_offer_scene", return_value=True):
            handled = runtime.handle_offer_drop(item_kind=ITEM_RAMEN, global_pos=SimpleNamespace())

        self.assertTrue(handled)
        self.assertEqual(pet.mood_score, 50.0)
        self.assertAlmostEqual(pet.offer_miss_event_cooldown_until, 0.0)
        self.assertAlmostEqual(pet.negative_afterglow_until, 0.0)
        self.assertEqual(pet.reaction_calls, [])

    def test_handle_offer_drop_to_ground_does_not_apply_offer_miss_penalty(self):
        pet = FakePet("Tokai Teio")
        runtime = self.build_runtime([pet])
        runtime.offer_hover_item_kind = ITEM_RAMEN
        runtime.offer_hover_target_name = pet.name
        runtime.offer_hover_started_at = 10.0

        with (
            patch("tanuki_core.app_runtime.app_now", return_value=12.5),
            patch.object(runtime, "find_offer_drop_target", return_value=None),
            patch.object(runtime, "drop_ground_offer_item", return_value=True) as mocked_drop,
        ):
            handled = runtime.handle_offer_drop(item_kind=ITEM_RAMEN, global_pos=SimpleNamespace())

        self.assertTrue(handled)
        mocked_drop.assert_called_once()
        self.assertEqual(runtime.offer_hover_item_kind, "")
        self.assertEqual(runtime.offer_hover_target_name, "")
        self.assertEqual(pet.mood_score, 50.0)
        self.assertAlmostEqual(pet.offer_miss_event_cooldown_until, 0.0)
        self.assertAlmostEqual(pet.negative_afterglow_until, 0.0)
        self.assertEqual(pet.reaction_calls, [])

    def test_start_bottle_feed_scene_holds_bottle_when_child_available(self):
        holder = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        holder._x = 100
        child._x = 260
        runtime = self.build_runtime([holder, child])

        def ensure_held_item(pet, item_kind, source="offer_tray"):
            pet.held_item_kind = item_kind
            pet.held_item_source = source
            pet.held_item_widget = object()
            return pet.held_item_widget

        with (
            patch.object(runtime, "ensure_pet_held_item", side_effect=ensure_held_item),
            patch.object(runtime, "update_held_offer_widget_position") as mocked_position,
        ):
            started = runtime.start_bottle_feed_scene(holder, source="offer_tray")

        self.assertTrue(started)
        self.assertIsNotNone(runtime.offer_scene)
        self.assertEqual(runtime.offer_scene.scene_kind, "bottle_feed")
        self.assertEqual(runtime.offer_scene.actor_name, "Symboli Rudolf")
        self.assertEqual(runtime.offer_scene.target_name, "Tsurumaru Tsuyoshi")
        self.assertEqual(holder.held_item_kind, ITEM_BOTTLE)
        self.assertEqual(holder.offer_scene_kind, "bottle_feed")
        self.assertEqual(child.offer_scene_kind, "bottle_feed")
        mocked_position.assert_called_once_with(
            holder.held_item_widget,
            holder,
            ITEM_BOTTLE,
            prefer_preview=True,
        )

    def test_all_non_child_bottle_holders_execute_real_held_behavior(self):
        for holder_name in ("Sirius Symboli", "Tokai Teio", "Air Groove"):
            with self.subTest(holder_name=holder_name):
                holder = FakePet(holder_name)
                child = FakePet("Tsurumaru Tsuyoshi")
                holder._x = 100
                child._x = 260
                runtime = self.build_runtime([holder, child])

                def ensure_held_item(pet, item_kind, source="offer_tray"):
                    pet.held_item_kind = item_kind
                    pet.held_item_source = source
                    pet.held_item_widget = object()
                    return pet.held_item_widget

                with (
                    patch.object(runtime, "ensure_pet_held_item", side_effect=ensure_held_item),
                    patch.object(runtime, "update_held_offer_widget_position"),
                ):
                    started = runtime.start_bottle_feed_scene(holder, source="offer_tray")

                self.assertTrue(started)
                self.assertEqual(holder.held_item_kind, ITEM_BOTTLE)
                self.assertEqual(holder.offer_scene_kind, "bottle_feed")
                self.assertEqual(child.offer_scene_kind, "bottle_feed")

    def test_update_bottle_feed_scene_approach_keeps_bottle_on_holder_and_moves_child(self):
        holder = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        holder._x = 100
        child._x = 360
        runtime = self.build_runtime([holder, child])
        runtime.ensure_pet_held_item(holder, ITEM_BOTTLE, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_BOTTLE,
            scene_kind="bottle_feed",
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
        )

        handled = runtime.update_bottle_feed_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(holder.held_item_kind, ITEM_BOTTLE)
        self.assertEqual(holder.state, "idle")
        self.assertEqual(child.state, "move")
        self.assertEqual(child.current_action_tag, "climb")
        self.assertEqual(child.move_toward_calls[0][2], 2.0)

    def test_update_bottle_feed_scene_approach_prefers_manifest_contexts(self):
        holder = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        holder.context_successes.add(("idle", "bottle_feed_hold"))
        child.context_successes.add(("move", "bottle_feed_child_approach"))
        holder._x = 100
        child._x = 360
        runtime = self.build_runtime([holder, child])
        runtime.ensure_pet_held_item(holder, ITEM_BOTTLE, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_BOTTLE,
            scene_kind="bottle_feed",
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
        )

        handled = runtime.update_bottle_feed_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(holder.context_calls[0][1], "bottle_feed_hold")
        self.assertEqual(child.context_calls[0][1], "bottle_feed_child_approach")
        self.assertEqual(holder.ensure_calls, [])
        self.assertEqual(child.ensure_calls, [])

    def test_update_bottle_feed_scene_drink_stage_removes_holder_item_and_rewards_child(self):
        holder = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        holder._x = 100
        child._x = 180
        runtime = self.build_runtime([holder, child])
        runtime.ensure_pet_held_item(holder, ITEM_BOTTLE, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_BOTTLE,
            scene_kind="bottle_feed",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="drink",
            stage_initialized=False,
            stage_ends_at=12.0,
            scene_ends_at=12.0,
            source="offer_tray",
            event_recorded=False,
        )

        first_handled = runtime.update_bottle_feed_scene(10.0)
        second_handled = runtime.update_bottle_feed_scene(12.1)

        self.assertTrue(first_handled)
        self.assertTrue(second_handled)
        self.assertEqual(holder.held_item_kind, "")
        self.assertEqual(child.current_action_tag, "drink")
        self.assertEqual(child.mood_score, 60.0)
        self.assertIsNone(runtime.offer_scene)

    def test_update_offer_scene_cancels_bottle_feed_and_clears_hidden_holder_item(self):
        holder = FakePet("Sirius Symboli", visible=False)
        child = FakePet("Tsurumaru Tsuyoshi")
        runtime = self.build_runtime([holder, child])
        runtime.ensure_pet_held_item(holder, ITEM_BOTTLE, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind=ITEM_BOTTLE,
            scene_kind="bottle_feed",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            source="offer_tray",
        )

        handled = runtime.update_offer_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(holder.held_item_kind, "")
        self.assertIsNone(holder.held_item_widget)
        self.assertIsNone(runtime.offer_scene)

    def test_honey_guard_snatch_changes_once_then_preserves_animation(self):
        guardian = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian._x = 80
        child._x = 130
        runtime = self.build_runtime([guardian, child])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            stage="snatch",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        first_handled = runtime.update_honey_guard_scene(10.0)
        first_guardian_mood = guardian.current_mood_tag
        first_child_mood = child.current_mood_tag
        second_handled = runtime.update_honey_guard_scene(10.2)

        self.assertTrue(first_handled)
        self.assertTrue(second_handled)
        self.assertIn(first_guardian_mood, {"sad", "think"})
        self.assertIn(first_child_mood, {"sad", "cry", "hard-cry"})
        self.assertEqual(guardian.current_mood_tag, first_guardian_mood)
        self.assertEqual(child.current_mood_tag, first_child_mood)
        self.assertEqual(len(guardian.change_calls), 0)
        self.assertEqual(len(child.change_calls), 0)
        self.assertEqual(len(guardian.ensure_calls), 0)
        self.assertEqual(len(child.ensure_calls), 0)
        self.assertTrue(runtime.offer_scene.stage_initialized)
        self.assertGreaterEqual(guardian.reset_calls, 2)
        self.assertGreaterEqual(child.reset_calls, 2)

    def test_honey_guard_approach_prefers_rescue_move_moods(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian._x = 50
        child._x = 400
        runtime = self.build_runtime([guardian, child])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(guardian.current_purpose, "move")
        self.assertEqual(guardian.current_action_tag, "run")
        self.assertEqual(guardian.current_mood_tag, "angry")

    def test_honey_guard_approach_prefers_manifest_contexts(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.context_successes.add(("move", "honey_guard_move"))
        child.context_successes.add(("idle", "offer_preview"))
        guardian._x = 50
        child._x = 400
        runtime = self.build_runtime([guardian, child])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(child.context_calls[0][1], "offer_preview")
        self.assertEqual(guardian.context_calls[0][1], "honey_guard_move")
        self.assertEqual(guardian.ensure_calls, [])

    def test_honey_guard_approach_prefers_rudolf_run_for_first_available_mood(self):
        guardian = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian._x = 50
        child._x = 400
        runtime = self.build_runtime([guardian, child])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(guardian.current_purpose, "move")
        self.assertEqual(guardian.current_action_tag, "run")
        self.assertEqual(guardian.current_mood_tag, "angry")
        self.assertEqual(guardian.move_toward_calls[0][1], 1.6)
        self.assertEqual(guardian.move_toward_calls[0][2], 5.0)

    def test_start_honey_guard_scene_defers_while_guardian_flying(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.flight_mode = "to_window"
        child.perched_window_hwnd = 123
        guardian.vy = 2.0
        child.vy = 1.0
        runtime = self.build_runtime([guardian, child])

        started = runtime.start_honey_guard_scene(child, source="offer_tray")

        self.assertTrue(started)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(guardian.stop_window_flight_calls, [])
        self.assertEqual(child.detach_calls, 0)
        self.assertEqual(guardian.flight_mode, "to_window")
        self.assertEqual(child.perched_window_hwnd, 123)
        self.assertEqual(child.offer_scene_kind, "held_item")

    def test_start_honey_guard_scene_locks_guardian_and_child(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian._x = 100
        child._x = 260
        runtime = self.build_runtime([guardian, child])

        def ensure_held_item(pet, item_kind, source="offer_tray"):
            pet.held_item_kind = item_kind
            pet.held_item_source = source
            pet.held_item_widget = object()
            return pet.held_item_widget

        with (
            patch.object(runtime, "ensure_pet_held_item", side_effect=ensure_held_item),
            patch.object(runtime, "apply_held_item_behavior", return_value=True),
        ):
            started = runtime.start_honey_guard_scene(child, source="offer_tray")

        self.assertTrue(started)
        self.assertIsNotNone(runtime.offer_scene)
        self.assertEqual(runtime.offer_scene.scene_kind, "honey_guard")
        self.assertEqual(guardian.offer_scene_kind, "honey_guard")
        self.assertEqual(child.offer_scene_kind, "honey_guard")

    def test_start_honey_guard_scene_detaches_perched_guardian_before_deferring(self):
        guardian = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.perched_window_hwnd = 456
        runtime = self.build_runtime([guardian, child])

        started = runtime.start_honey_guard_scene(child, source="offer_tray")

        self.assertTrue(started)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(guardian.detach_calls, 1)
        self.assertEqual(guardian.perched_window_hwnd, 0)
        self.assertEqual(child.offer_scene_kind, "held_item")

    def test_update_honey_guard_scene_aborts_when_window_transition_resumes(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.flight_mode = "to_window"
        child.perched_window_hwnd = 123
        runtime = self.build_runtime([guardian, child])
        runtime.ensure_pet_held_item(child, ITEM_HONEY, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(child.offer_scene_kind, "held_item")

    def test_update_honey_guard_scene_detaches_perched_guardian_then_defers(self):
        guardian = FakePet("Symboli Rudolf")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.perched_window_hwnd = 456
        runtime = self.build_runtime([guardian, child])
        runtime.ensure_pet_held_item(child, ITEM_HONEY, source="offer_tray")
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Symboli Rudolf",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=True,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(guardian.detach_calls, 1)
        self.assertEqual(guardian.perched_window_hwnd, 0)
        self.assertEqual(child.offer_scene_kind, "held_item")

    def test_honey_guard_snatch_starts_negative_afterglow(self):
        guardian = FakePet("Sirius Symboli")
        child = FakePet("Tsurumaru Tsuyoshi")
        guardian.context_successes.add(("idle", "honey_guard_take"))
        child.context_successes.add(("idle", "offer_denied"))
        guardian._x = 100
        child._x = 160
        runtime = self.build_runtime([guardian, child])
        runtime.offer_scene = ActiveOfferScene(
            item_kind="honey",
            scene_kind="honey_guard",
            actor_name="Sirius Symboli",
            target_name="Tsurumaru Tsuyoshi",
            stage="approach",
            stage_initialized=False,
            stage_ends_at=20.0,
            scene_ends_at=20.0,
            event_recorded=False,
        )

        handled = runtime.update_honey_guard_scene(10.0)

        self.assertTrue(handled)
        self.assertEqual(child.mood_score, 20.0)
        self.assertEqual(runtime.offer_scene.scene_ends_at, 11.2)
        self.assertEqual(guardian.negative_afterglow_until, 15.0)
        self.assertEqual(guardian.negative_afterglow_preferred_moods, ("sad", "think"))
        self.assertIn("happy", guardian.negative_afterglow_forbidden_moods)
        self.assertEqual(guardian.current_action_tag, "honey_guard_take")
        self.assertEqual(child.negative_afterglow_until, 15.0)
        self.assertEqual(child.negative_afterglow_care_block_until, 15.0)
        self.assertIn("cry", child.negative_afterglow_preferred_moods)
        self.assertIn("happy", child.negative_afterglow_forbidden_moods)

        self.assertTrue(runtime.update_honey_guard_scene(11.1))
        self.assertIsNotNone(runtime.offer_scene)
        self.assertEqual(guardian.current_action_tag, "honey_guard_take")
        self.assertFalse(runtime.update_honey_guard_scene(11.2))
        self.assertIsNone(runtime.offer_scene)
        self.assertEqual(guardian.offer_scene_kind, "none")
        self.assertEqual(child.offer_scene_kind, "none")
        self.assertEqual(guardian.negative_afterglow_until, 15.0)
        self.assertEqual(child.negative_afterglow_until, 15.0)


if __name__ == "__main__":
    unittest.main()
