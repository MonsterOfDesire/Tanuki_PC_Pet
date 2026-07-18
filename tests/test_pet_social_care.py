import unittest
import sys
import types
from unittest.mock import patch

try:
    import PyQt6  # noqa: F401
    import PyQt6.QtCore  # noqa: F401
    import PyQt6.QtWidgets  # noqa: F401
except ModuleNotFoundError:
    pass


if "PyQt6" not in sys.modules:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtwidgets_module = types.ModuleType("PyQt6.QtWidgets")

    class QObject:
        pass

    class QPoint:
        def __init__(self, x=0, y=0):
            self._x = x
            self._y = y

        def x(self):
            return self._x

        def y(self):
            return self._y

    class QRect:
        def __init__(self, *args, **kwargs):
            pass

        def united(self, other):
            return self

    class QApplication:
        @staticmethod
        def screens():
            return []

        @staticmethod
        def screenAt(*args, **kwargs):
            return None

        @staticmethod
        def primaryScreen():
            return None

    qtcore_module.QObject = QObject
    qtcore_module.QPoint = QPoint
    qtcore_module.QRect = QRect
    qtwidgets_module.QApplication = QApplication
    pyqt6_module.QtCore = qtcore_module
    pyqt6_module.QtWidgets = qtwidgets_module
    sys.modules.setdefault("PyQt6", pyqt6_module)
    sys.modules.setdefault("PyQt6.QtCore", qtcore_module)
    sys.modules.setdefault("PyQt6.QtWidgets", qtwidgets_module)

from tanuki_core.pet_intent_rules import INTENT_OBSERVE, INTENT_POST_OBSERVE_INTERACTION
from tanuki_core.asset_selection_rules import (
    get_mood_band,
    select_contextual_result,
    select_contextual_result_for_purposes,
)
from tanuki_core.pet_social_care import PetSocialCareMixin


class FirstChoiceRng:
    def choice(self, population):
        return population[0]

    def choices(self, population, weights=None, k=1):
        if weights:
            for candidate, weight in zip(population, weights):
                if weight > 0:
                    return [candidate]
        return [population[0]]


class FakeContextualSelectionMixin:
    def get_contextual_result(
        self,
        purpose,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        return select_contextual_result(
            self.asset_records.get(purpose, {}),
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=FirstChoiceRng(),
        )

    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
    ):
        return select_contextual_result_for_purposes(
            self.asset_records,
            purposes,
            context=context,
            preferred_moods=preferred_moods,
            forbidden=forbidden,
            mood_score=mood_score,
            ordered_preferences=ordered_preferences,
            rng=FirstChoiceRng(),
        )


class FakeExpressionAssetManager(FakeContextualSelectionMixin):
    def __init__(self):
        self.specific_calls = []
        self.asset_records = {
            "idle": {
                "photo": {
                    "happy": {
                        "frames": ["photo-happy"],
                        "manifest": {
                            "band": ["normal"],
                            "contexts": ["relation_watch"],
                            "weight": 1.0,
                        },
                    },
                    "sad": {
                        "frames": ["photo-sad"],
                        "manifest": {
                            "band": ["low"],
                            "contexts": ["relation_watch"],
                            "weight": 1.0,
                        },
                    },
                },
                "side_hug": {
                    "happy": {
                        "frames": ["side-hug-happy"],
                        "manifest": {
                            "band": ["normal"],
                            "contexts": ["post_observe"],
                            "weight": 1.0,
                        },
                    },
                },
            },
            "move": {
                "walk_shake": {
                    "happy": {
                        "frames": ["walk-shake-happy"],
                        "manifest": {
                            "band": ["normal"],
                            "contexts": ["post_observe"],
                            "weight": 0.0,
                        },
                    },
                },
            }
        }

    def get_record_weight(self, record):
        return float((record.get("manifest") or {}).get("weight", 1.0))

    def choose_weighted_result(self, results):
        if not results:
            return None
        frames, action_type, mood_tag, _weight = results[0]
        return frames, action_type, mood_tag

    def get_specific_frames(self, purpose, action_type, mood_tag, mood_score=None, context=None):
        self.specific_calls.append((purpose, action_type, mood_tag, mood_score, context))
        record = self.asset_records.get(purpose, {}).get(action_type, {}).get(mood_tag)
        if not record:
            return None
        if not self.is_record_eligible(record, mood_score=mood_score, context=context):
            return None
        return record["frames"]

    def is_record_eligible(self, record, mood_score=None, context=None):
        manifest = record.get("manifest") or {}
        contexts = manifest.get("contexts") or []
        bands = manifest.get("band") or []
        if context and contexts:
            if isinstance(context, (list, tuple, set, frozenset)):
                if not any(item in contexts for item in context if item):
                    return False
            elif context not in contexts:
                return False
        if mood_score is not None and bands and get_mood_band(mood_score) not in bands:
            return False
        return True


class FakeExpressionPet(PetSocialCareMixin):
    def __init__(self):
        self.name = "Symboli Rudolf"
        self.state = "idle"
        self.expression_animation_context = "relation_watch"
        self.current_purpose = "idle"
        self.current_action_tag = "photo"
        self.current_mood_tag = "happy"
        self.mood_score = 60.0
        self.social_mode = "none"
        self.care_mode = "none"
        self.offer_scene_kind = "none"
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()
        self.asset_manager = FakeExpressionAssetManager()
        self.calls = []
        self.applied = []

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.applied.append((purpose, action_type, mood_tag, tuple(frames)))
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True

    def get_randomized_candidates(self, candidates):
        return list(candidates)

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        self.calls.append(("expand", purpose, list(candidates), context))
        return list(candidates)

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        self.calls.append(("ensure", list(candidates), list(preferred_moods), context))
        return True

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None, ignore_mood_band=False):
        self.calls.append(("change", list(candidates), list(preferred_moods), context, ignore_mood_band))
        return True

    def is_under_care(self, now):
        return False


class FakeSocialAfterglowPet(PetSocialCareMixin):
    CHILD_NAMES = {"Tokai Teio", "Tsurumaru Tsuyoshi"}

    def __init__(self):
        self.name = "Tsurumaru Tsuyoshi"
        self.dragging = False
        self.social_mode = "following"
        self.social_target = object()
        self.negative_afterglow_until = 20.0
        self.negative_afterglow_preferred_moods = ("sad",)
        self.negative_afterglow_forbidden_moods = ("happy",)
        self.stop_calls = []

    def stop_social_mode(self, now, apply_cooldown=True):
        self.stop_calls.append((now, apply_cooldown))
        self.social_mode = "none"


class FakePreserveAfterglowAssetManager:
    def __init__(self):
        self.calls = []

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        self.calls.append((purpose, action_type, mood, mood_score, context))
        if mood_score is None:
            return ["frame"]
        return None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None, context=None):
        return None


class FakePreserveAfterglowPet(PetSocialCareMixin):
    def __init__(self):
        self.current_purpose = "idle"
        self.current_action_tag = "side_hug"
        self.current_mood_tag = "sad"
        self.mood_score = 85.0
        self.social_mode = "none"
        self.care_mode = "none"
        self.offer_scene_kind = "none"
        self.negative_afterglow_until = 20.0
        self.negative_afterglow_preferred_moods = ("hard-cry", "cry", "sad", "scared", "think")
        self.negative_afterglow_forbidden_moods = ("happy", "smile")
        self.asset_manager = FakePreserveAfterglowAssetManager()
        self.change_calls = []

    def change_state_candidates(self, candidates, context=None):
        self.change_calls.append(("change", list(candidates), context))
        return False

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None, ignore_mood_band=False):
        self.change_calls.append(("change_pref", list(candidates), list(preferred_moods), context, ignore_mood_band))
        return False

    def is_under_care(self, now):
        return False


class FakeContextAssetManager(FakeContextualSelectionMixin):
    def __init__(self):
        self.asset_records = {
            "idle": {
                "get": {
                    "happy": {
                        "frames": ["get-happy"],
                        "manifest": {
                            "band": ["normal"],
                            "contexts": ["offer_preview"],
                            "weight": 1.0,
                        },
                    },
                    "sad": {
                        "frames": ["get-sad"],
                        "manifest": {
                            "band": ["low"],
                            "contexts": ["offer_preview"],
                            "weight": 1.0,
                        },
                    },
                },
                "side": {
                    "cry": {
                        "frames": ["side-cry"],
                        "manifest": {
                            "band": ["severe"],
                            "contexts": ["offer_denied"],
                            "weight": 1.0,
                        },
                    },
                },
            }
        }

    def get_record_weight(self, record):
        return float((record.get("manifest") or {}).get("weight", 1.0))

    def choose_weighted_result(self, results):
        if not results:
            return None
        frames, action_type, mood_tag, _weight = results[0]
        return frames, action_type, mood_tag

    def get_specific_frames(self, purpose, action_type, mood_tag, mood_score=None, context=None):
        record = self.asset_records.get(purpose, {}).get(action_type, {}).get(mood_tag)
        if not record:
            return None
        if not self.is_record_eligible(record, mood_score=mood_score, context=context):
            return None
        return record["frames"]

    def is_record_eligible(self, record, mood_score=None, context=None):
        manifest = record.get("manifest") or {}
        contexts = manifest.get("contexts") or []
        bands = manifest.get("band") or []
        if context and contexts and context not in contexts:
            return False
        if mood_score is not None and bands and get_mood_band(mood_score) not in bands:
            return False
        return True


class FakeContextPet(PetSocialCareMixin):
    def __init__(self):
        self.name = "Tsurumaru Tsuyoshi"
        self.current_purpose = "idle"
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"
        self.mood_score = 60.0
        self.asset_manager = FakeContextAssetManager()
        self.applied = []

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.applied.append((purpose, action_type, mood_tag, tuple(frames)))
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True


class FakeObserveTarget:
    def __init__(self, name="Tokai Teio", x=170, collision_displaced_until=0.0):
        self.name = name
        self._x = x
        self.collision_displaced_until = collision_displaced_until
        self.dragging = False
        self.is_angry_locked = False
        self.is_recovering = False
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.social_mode = "none"
        self.care_mode = "none"
        self.offer_scene_kind = "none"
        self.intent_kind = "ambient_idle"
        self.intent_reconsider_after = 0.0
        self.observe_notice_cooldown_until = 0.0
        self.state = "move"
        self.state_timer = 0
        self.current_purpose = "move"
        self.relationship_focus_target_name = ""
        self.expression_animation_context = "ambient"
        self.expression_focus_target_name = ""
        self.expression_look_at_target = False
        self.direction = 1
        self.expression_calls = []

    def x(self):
        return self._x

    def isVisible(self):
        return True

    def is_under_care(self, now):
        _ = now
        return False

    def get_random_animation_context(self):
        return ["relation_watch", "random"]

    def apply_expression_idle_behavior(self, random_context):
        self.expression_calls.append(random_context)
        return True


class FakeObservePet(PetSocialCareMixin):
    def __init__(self, target):
        self.name = "Symboli Rudolf"
        self._x = 100
        self._target = target
        self.state = "idle"
        self.state_timer = 25
        self.current_purpose = "idle"
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"
        self.mood_score = 60.0
        self.direction = 1
        self.intent_kind = INTENT_OBSERVE
        self.intent_target_name = target.name
        self.intent_locked_until = 12.0
        self.intent_reconsider_after = 0.0
        self.observe_blocked_target_name = ""
        self.observe_blocked_until = 0.0
        self.observe_streak_target_name = ""
        self.observe_streak_count = 0
        self.observe_notice_cooldown_until = 0.0
        self.pending_social_log_event = {}
        self.social_log_event_cooldown_until = 0.0
        self.perception_visible_adult_count = 0
        self.perception_visible_child_count = 0
        self.intent_priority = 15
        self.intent_source = "ambient"
        self.intent_context = "observe"
        self.intent_reason = "observe_hold"
        self.relationship_focus_target_name = target.name
        self.relationship_focus_familiarity = 8.0
        self.relationship_focus_trust = 1.0
        self.relationship_focus_attachment = 0.0
        self.relationship_focus_tension = 0.0
        self.expression_animation_context = "relation_watch"
        self.expression_relation_overlay = "none"
        self.expression_focus_target_name = target.name
        self.expression_posture_bias = "curious"
        self.expression_spacing_bias = "neutral"
        self.expression_look_at_target = True
        self.negative_afterglow_until = 0.0
        self.negative_afterglow_preferred_moods = ()
        self.negative_afterglow_forbidden_moods = ()
        self.collision_displaced_until = 0.0
        self.asset_manager = FakeExpressionAssetManager()
        self.calls = []
        self.applied = []

    def x(self):
        return self._x

    def distance_to(self, other):
        return abs(other.x() - self.x())

    def get_visible_behavior_target(self, all_pets, target_name):
        if target_name == self._target.name:
            return self._target
        return None

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.applied.append((purpose, action_type, mood_tag, tuple(frames)))
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True

    def get_random_animation_context(self):
        return ["relation_watch", "random"]

    def apply_expression_idle_behavior(self, random_context):
        self.calls.append(("expr", random_context))
        return True

    def ensure_candidate_animation(self, candidates, context=None):
        self.calls.append(("ensure", list(candidates), context))
        return True

    def ensure_candidate_animation_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None):
        self.calls.append(("ensure_pref", list(candidates), list(preferred_moods), context))
        return True

    def change_state_candidates_with_preferences(self, candidates, preferred_moods, forbidden=None, context=None, ignore_mood_band=False):
        self.calls.append(("change", list(candidates), list(preferred_moods), context, ignore_mood_band))
        return True

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        self.calls.append(("expand", purpose, list(candidates), context))
        return list(candidates)

    def get_idle_candidates(self):
        return [("idle", "stand")]

    def get_move_candidates(self):
        return [("move", "walk")]

    def move_toward_x(self, target_x, speed_scale=1.0, min_speed=None):
        self.calls.append(("move_toward", target_x, speed_scale, min_speed))
        return True

    def reset_stationary_move_mode(self):
        self.calls.append(("reset_stationary",))


class FakeCollisionPet(PetSocialCareMixin):
    def __init__(self):
        self.dragging = False
        self.vy = 0
        self._visible = True
        self.flight_mode = "none"
        self.is_hugging = False
        self.care_mode = "none"
        self.care_partner = None
        self.offer_locked_until = 5.0

    def isVisible(self):
        return self._visible

    def is_under_care(self, now):
        return False

    def is_offer_locked(self, now=None):
        if now is None:
            now = 0.0
        return float(self.offer_locked_until or 0.0) > float(now)


class FakeCareInteractionAssetManager:
    def __init__(self):
        self.calls = []
        self.records = {
            ("interaction", "idle_hug_Teio", "happy"): {
                "frames": ["idle-hug-happy"],
                "contexts": {"care_interaction_teio"},
            },
            ("interaction", "move_walk_Teio", "happy"): {
                "frames": ["move-walk-happy"],
                "contexts": {"moving_care_interaction_teio"},
            },
        }

    def get_action_keys(self, purpose):
        if purpose == "interaction":
            return ["idle_hug_Teio", "move_walk_Teio"]
        return []

    def get_specific_frames(self, purpose, action_type, mood, mood_score=None, context=None):
        self.calls.append((purpose, action_type, mood, mood_score, context))
        record = self.records.get((purpose, action_type, mood))
        if not record:
            return None
        contexts = set(context or ())
        if record["contexts"] & contexts:
            return record["frames"]
        return None


class FakeCareInteractionPet(PetSocialCareMixin):
    def __init__(self):
        self.name = "Symboli Rudolf"
        self.state = "move"
        self.asset_manager = FakeCareInteractionAssetManager()


class FakeCareInteractionChild:
    current_mood_tag = "cry"
    mood_score = 10.0

    def get_child_tokens(self):
        return ["Teio"]


class FakeCareApproachAssetManager(FakeContextualSelectionMixin):
    def __init__(self):
        self.asset_records = {
            "move": {
                "run_stretch": {
                    "hurry": {
                        "frames": ["care-approach-hurry"],
                        "manifest": {
                            "band": ["normal"],
                            "contexts": ["care_approach_teio"],
                            "weight": 1.0,
                        },
                    },
                },
            },
        }

    def get_record_weight(self, record):
        return float((record.get("manifest") or {}).get("weight", 1.0))

    def choose_weighted_result(self, results):
        if not results:
            return None
        frames, action_type, mood_tag, _weight = results[0]
        return frames, action_type, mood_tag

    def get_specific_frames(self, purpose, action_type, mood_tag, mood_score=None, context=None):
        record = self.asset_records.get(purpose, {}).get(action_type, {}).get(mood_tag)
        if not record:
            return None
        if not self.is_record_eligible(record, mood_score=mood_score, context=context):
            return None
        return record["frames"]

    def is_record_eligible(self, record, mood_score=None, context=None):
        manifest = record.get("manifest") or {}
        contexts = manifest.get("contexts") or []
        bands = manifest.get("band") or []
        if context and contexts:
            if isinstance(context, (list, tuple, set, frozenset)):
                if not any(item in contexts for item in context if item):
                    return False
            elif context not in contexts:
                return False
        if mood_score is not None and bands and get_mood_band(mood_score) not in bands:
            return False
        return True


class FakeCareApproachPet(PetSocialCareMixin):
    def __init__(self):
        self.name = "Symboli Rudolf"
        self.current_purpose = "move"
        self.current_action_tag = "walk"
        self.current_mood_tag = "happy"
        self.mood_score = 60.0
        self.asset_manager = FakeCareApproachAssetManager()
        self.applied = []

    def apply_animation_result(self, purpose, result):
        if not result:
            return False
        frames, action_type, mood_tag = result
        self.applied.append((purpose, action_type, mood_tag, tuple(frames)))
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = mood_tag
        return True


class PetSocialCareMixinTests(unittest.TestCase):
    def test_expression_idle_behavior_preserves_matching_relation_context_animation(self):
        pet = FakeExpressionPet()

        handled = pet.apply_expression_idle_behavior(["relation_watch", "random"])

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [])
        self.assertEqual(pet.asset_manager.specific_calls[0][4], "relation_watch")
        self.assertEqual(pet.calls, [])

    def test_expression_idle_behavior_skips_non_idle_state(self):
        pet = FakeExpressionPet()
        pet.state = "move"

        handled = pet.apply_expression_idle_behavior(["relation_watch", "random"])

        self.assertFalse(handled)
        self.assertEqual(pet.calls, [])

    @patch("tanuki_core.pet_social_care.app_now", return_value=10.0)
    def test_expression_preferred_moods_switch_to_negative_afterglow(self, _mock_now):
        pet = FakeExpressionPet()
        pet.start_negative_afterglow(duration=5.0, now=10.0)

        moods = pet.get_expression_preferred_moods()

        self.assertEqual(moods, ["hard-cry", "cry", "sad", "scared", "think"])

    def test_regular_negative_afterglow_does_not_block_care(self):
        pet = FakeExpressionPet()

        pet.start_negative_afterglow(duration=5.0, now=10.0)

        self.assertFalse(pet.is_care_blocked_by_negative_afterglow(now=10.0))
        self.assertTrue(
            pet.should_apply_negative_afterglow_to_candidates(
                [("move", "crawl")],
                now=10.0,
            )
        )

    def test_care_blocking_negative_afterglow_expires_with_its_duration(self):
        pet = FakeExpressionPet()

        pet.start_negative_afterglow(duration=5.0, now=10.0, block_care=True)

        self.assertTrue(pet.is_care_blocked_by_negative_afterglow(now=14.9))
        self.assertFalse(pet.is_care_blocked_by_negative_afterglow(now=15.0))

    @patch("tanuki_core.pet_social_care.app_now", return_value=10.0)
    def test_relation_expression_afterglow_ignores_high_mood_band_and_forbids_happy(self, _mock_now):
        pet = FakeExpressionPet()
        pet.mood_score = 85.0
        pet.start_negative_afterglow(
            duration=5.0,
            preferred_moods=["sad"],
            forbidden_moods=["happy", "smile"],
            now=10.0,
        )

        handled = pet.apply_expression_idle_behavior(["relation_watch", "random"])

        self.assertTrue(handled)
        self.assertEqual(pet.current_mood_tag, "sad")
        self.assertEqual(pet.applied, [("idle", "photo", "sad", ("photo-sad",))])

    @patch("tanuki_core.pet_social_care.app_now", return_value=10.0)
    def test_expression_preferred_moods_keep_negative_afterglow_while_social_stops(self, _mock_now):
        pet = FakeExpressionPet()
        pet.social_mode = "following"
        pet.start_negative_afterglow(duration=5.0, now=10.0)

        moods = pet.get_expression_preferred_moods()

        self.assertEqual(moods, ["hard-cry", "cry", "sad", "scared", "think"])

    @patch("tanuki_core.pet_social_care.app_now", return_value=10.0)
    def test_negative_afterglow_does_not_override_candidates_while_social_active(self, _mock_now):
        pet = FakeExpressionPet()
        pet.social_mode = "following"
        pet.start_negative_afterglow(duration=5.0, now=10.0)

        should_apply = pet.should_apply_negative_afterglow_to_candidates([("idle", "stand")], now=10.0)

        self.assertFalse(should_apply)

    def test_update_social_behavior_stops_active_social_when_negative_afterglow_active(self):
        pet = FakeSocialAfterglowPet()

        handled = pet.update_social_behavior(10.0, [])

        self.assertFalse(handled)
        self.assertEqual(pet.social_mode, "none")
        self.assertEqual(pet.stop_calls, [(10.0, False)])

    def test_update_observe_behavior_clears_active_observe_during_negative_afterglow(self):
        target = FakeObserveTarget()
        pet = FakeObservePet(target)
        pet.start_negative_afterglow(duration=5.0, now=10.0)

        handled = pet.update_observe_behavior(10.0, [target])

        self.assertFalse(handled)
        self.assertEqual(pet.intent_kind, "ambient_idle")
        self.assertEqual(pet.intent_target_name, "")
        self.assertEqual(pet.calls, [])

    def test_update_post_observe_behavior_clears_active_interaction_during_negative_afterglow(self):
        target = FakeObserveTarget()
        pet = FakeObservePet(target)
        pet.intent_kind = INTENT_POST_OBSERVE_INTERACTION
        pet.intent_context = "post_observe_interaction"
        pet.start_negative_afterglow(duration=5.0, now=10.0)

        handled = pet.update_post_observe_interaction_behavior(10.0, [target])

        self.assertFalse(handled)
        self.assertEqual(pet.intent_kind, "ambient_idle")
        self.assertEqual(pet.intent_target_name, "")
        self.assertEqual(pet.calls, [])

    @patch("tanuki_core.pet_social_care.app_now", return_value=10.0)
    def test_ensure_candidate_animation_with_preferences_preserves_afterglow_pose_ignoring_band(self, _mock_now):
        pet = FakePreserveAfterglowPet()

        handled = pet.ensure_candidate_animation_with_preferences(
            [("idle", "side_hug")],
            ["hard-cry", "cry", "sad", "scared", "think"],
            forbidden=["happy", "smile"],
            context=["relation_watch", "random"],
        )

        self.assertTrue(handled)
        self.assertEqual(pet.asset_manager.calls[0][3], None)
        self.assertEqual(pet.change_calls, [])

    def test_change_state_for_context_filters_by_current_mood_band_before_preferences(self):
        pet = FakeContextPet()
        pet.mood_score = 60.0

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_preview",
            preferred_moods=["sad", "happy"],
        )

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [("idle", "get", "happy", ("get-happy",))])

    def test_change_state_for_context_can_fall_back_to_band_matching_nonpreferred_mood(self):
        pet = FakeContextPet()
        pet.mood_score = 35.0

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_preview",
            preferred_moods=["happy"],
        )

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [("idle", "get", "sad", ("get-sad",))])

    def test_change_state_for_context_can_ignore_mood_band_for_forced_scenes(self):
        pet = FakeContextPet()
        pet.mood_score = 60.0

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_preview",
            preferred_moods=["sad", "happy"],
            ignore_mood_band=True,
        )

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [("idle", "get", "sad", ("get-sad",))])

    def test_change_state_for_context_preserves_matching_current_animation(self):
        pet = FakeContextPet()
        pet.current_purpose = "idle"
        pet.current_action_tag = "get"
        pet.current_mood_tag = "happy"

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_preview",
            preferred_moods=["happy"],
            preserve=True,
        )

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [])

    def test_change_state_for_context_preserves_band_matching_fallback_mood(self):
        pet = FakeContextPet()
        pet.mood_score = 35.0
        pet.current_purpose = "idle"
        pet.current_action_tag = "get"
        pet.current_mood_tag = "sad"

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_preview",
            preferred_moods=["happy"],
            preserve=True,
        )

        self.assertTrue(handled)
        self.assertEqual(pet.applied, [])

    def test_change_state_for_context_respects_forbidden_moods(self):
        pet = FakeContextPet()

        handled = pet.change_state_for_context_with_preferences(
            "idle",
            "offer_denied",
            preferred_moods=["cry"],
            forbidden=["cry"],
        )

        self.assertFalse(handled)
        self.assertEqual(pet.applied, [])

    def test_care_approach_animation_uses_manifest_context(self):
        pet = FakeCareApproachPet()
        child = FakeCareInteractionChild()

        handled = pet.apply_care_approach_animation(child)

        self.assertTrue(handled)
        self.assertEqual(
            pet.applied,
            [("move", "run_stretch", "hurry", ("care-approach-hurry",))],
        )
        self.assertEqual(pet.get_care_approach_speed_scale(), 1.6)
        self.assertEqual(pet.get_care_approach_speed(), 5.0)

    def test_select_interaction_animation_can_prefer_stationary_care_context(self):
        pet = FakeCareInteractionPet()
        child = FakeCareInteractionChild()

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.1), \
             patch("tanuki_core.pet_social_care.random.shuffle", side_effect=lambda seq: None), \
             patch("tanuki_core.pet_social_care.random.choice", side_effect=lambda seq: seq[0]):
            result = pet.select_interaction_animation(child)

        self.assertEqual(result, ("idle_hug_Teio", "happy", ["idle-hug-happy"]))
        self.assertEqual(pet.asset_manager.calls[0][3], None)
        self.assertEqual(pet.asset_manager.calls[0][4], ["care_interaction_teio", "care_interaction"])

    def test_select_interaction_animation_can_prefer_moving_care_context(self):
        pet = FakeCareInteractionPet()
        child = FakeCareInteractionChild()

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.9), \
             patch("tanuki_core.pet_social_care.random.shuffle", side_effect=lambda seq: None), \
             patch("tanuki_core.pet_social_care.random.choice", side_effect=lambda seq: seq[0]):
            result = pet.select_interaction_animation(child)

        self.assertEqual(result, ("move_walk_Teio", "happy", ["move-walk-happy"]))
        self.assertEqual(pet.asset_manager.calls[0][3], None)
        self.assertEqual(
            pet.asset_manager.calls[0][4],
            ["moving_care_interaction_teio", "moving_care_interaction"],
        )

    @patch("tanuki_core.pet_social_care.app_now", return_value=1.0)
    def test_should_ignore_collision_while_offer_locked(self, _mock_now):
        pet = FakeCollisionPet()

        ignored = pet.should_ignore_collision()

        self.assertTrue(ignored)

    def test_post_observe_interaction_idle_behavior_uses_manifest_context(self):
        pet = FakeExpressionPet()
        pet.expression_animation_context = "relation_close"

        handled = pet.apply_post_observe_interaction_idle_behavior()

        self.assertTrue(handled)
        self.assertEqual(
            pet.applied,
            [("idle", "side_hug", "happy", ("side-hug-happy",))],
        )
        self.assertEqual(pet.calls, [])

    def test_post_observe_can_use_move_context_animation_without_moving_state(self):
        pet = FakeExpressionPet()
        pet.asset_manager.asset_records["idle"]["side_hug"]["happy"]["manifest"]["weight"] = 0.0
        pet.asset_manager.asset_records["move"]["walk_shake"]["happy"]["manifest"]["weight"] = 1.0

        handled = pet.apply_post_observe_interaction_idle_behavior(preserve=False)

        self.assertTrue(handled)
        self.assertEqual(pet.state, "idle")
        self.assertEqual(
            pet.applied,
            [("move", "walk_shake", "happy", ("walk-shake-happy",))],
        )

    def test_clear_observe_intent_resets_to_ambient_and_forces_random_refresh(self):
        pet = FakeObservePet(FakeObserveTarget())

        pet.clear_observe_intent(now=10.0, escape_roll=1.0)

        self.assertEqual(pet.intent_kind, "ambient_idle")
        self.assertEqual(pet.intent_target_name, "")
        self.assertEqual(pet.intent_context, "ambient_idle")
        self.assertEqual(pet.state_timer, 0)
        self.assertEqual(pet.current_purpose, "")
        self.assertGreater(pet.intent_reconsider_after, 10.0)
        self.assertEqual(pet.observe_blocked_target_name, "Tokai Teio")
        self.assertGreater(pet.observe_blocked_until, 10.0)
        self.assertEqual(pet.observe_streak_target_name, "Tokai Teio")
        self.assertEqual(pet.observe_streak_count, 1)
        self.assertEqual(pet.relationship_focus_target_name, "")
        self.assertEqual(pet.expression_animation_context, "ambient")
        self.assertEqual(pet.expression_focus_target_name, "")

    def test_clear_observe_intent_increases_same_target_cooldown_for_repeat_observe(self):
        pet = FakeObservePet(FakeObserveTarget())

        pet.clear_observe_intent(now=10.0, escape_roll=1.0)
        first_blocked_until = pet.observe_blocked_until

        pet.intent_kind = INTENT_OBSERVE
        pet.intent_target_name = "Tokai Teio"
        pet.relationship_focus_target_name = "Tokai Teio"
        pet.expression_animation_context = "relation_watch"
        pet.expression_focus_target_name = "Tokai Teio"
        pet.clear_observe_intent(now=20.0, escape_roll=1.0)

        self.assertEqual(pet.observe_streak_target_name, "Tokai Teio")
        self.assertEqual(pet.observe_streak_count, 2)
        self.assertGreater(pet.observe_blocked_until - 20.0, first_blocked_until - 10.0)

    def test_clear_observe_intent_can_start_post_observe_escape_roam(self):
        pet = FakeObservePet(FakeObserveTarget(x=180))
        pet.perception_visible_adult_count = 3

        pet.clear_observe_intent(now=10.0, blocked_target_dx=80.0, escape_roll=0.0)

        self.assertEqual(pet.intent_kind, "random_roam")
        self.assertEqual(pet.intent_context, "post_observe_escape")
        self.assertEqual(pet.intent_reason, "post_observe_escape")
        self.assertEqual(pet.state, "move")
        self.assertEqual(pet.direction, -1)
        self.assertGreaterEqual(pet.state_timer, 140)

    def test_clear_observe_intent_can_enqueue_social_log_event_candidate(self):
        pet = FakeObservePet(FakeObserveTarget())

        queued = pet.enqueue_social_log_event_from_observe(
            now=10.0,
            target_name="Tokai Teio",
            source_context="observe",
            roll=0.0,
            template_index=0,
        )

        self.assertTrue(queued)
        self.assertEqual(pet.pending_social_log_event["event_type"], "observe_social_log")
        self.assertEqual(pet.pending_social_log_event["actor_name"], "Symboli Rudolf")
        self.assertEqual(pet.pending_social_log_event["target_name"], "Tokai Teio")
        self.assertEqual(pet.pending_social_log_event["relation_delta"], {"familiarity": 0.12})
        self.assertGreater(pet.social_log_event_cooldown_until, 10.0)

    def test_observe_backoff_pauses_when_target_was_recently_pushed(self):
        target = FakeObserveTarget(collision_displaced_until=10.4, x=165)
        pet = FakeObservePet(target)

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.0):
            handled = pet.update_observe_behavior(10.0, [target])

        self.assertTrue(handled)
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.intent_reason, "observe_hold_collision_settle")
        self.assertEqual([call[0] for call in pet.calls], ["expr"])

    def test_observe_start_can_be_skipped_to_leave_room_for_pass_through(self):
        target = FakeObserveTarget(x=180)
        pet = FakeObservePet(target)
        pet.intent_kind = "ambient_idle"
        pet.intent_target_name = ""
        pet.intent_locked_until = 0.0

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.99):
            handled = pet.update_observe_behavior(10.0, [target])

        self.assertFalse(handled)
        self.assertEqual(pet.intent_kind, "ambient_idle")
        self.assertEqual(pet.intent_reason, "observe_start_skipped")
        self.assertGreater(pet.intent_reconsider_after, 10.0)

    def test_observe_start_can_briefly_notify_idle_target_without_forcing_interaction(self):
        target = FakeObserveTarget(x=250)
        pet = FakeObservePet(target)
        pet.intent_kind = "ambient_idle"
        pet.intent_target_name = ""
        pet.intent_locked_until = 0.0
        pet.intent_reconsider_after = 0.0

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.0):
            handled = pet.update_observe_behavior(10.0, [target])

        self.assertTrue(handled)
        self.assertEqual(pet.intent_kind, INTENT_OBSERVE)
        self.assertEqual(target.state, "idle")
        self.assertEqual(target.relationship_focus_target_name, "Symboli Rudolf")
        self.assertEqual(target.expression_animation_context, "relation_watch")
        self.assertGreater(target.observe_notice_cooldown_until, 10.0)
        self.assertEqual(target.expression_calls, [["relation_watch", "random"]])

    def test_observe_target_notice_does_not_interrupt_busy_target(self):
        target = FakeObserveTarget(x=250)
        target.social_mode = "following"
        pet = FakeObservePet(target)
        pet.intent_kind = "ambient_idle"
        pet.intent_target_name = ""
        pet.intent_locked_until = 0.0
        pet.intent_reconsider_after = 0.0

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.0):
            handled = pet.update_observe_behavior(10.0, [target])

        self.assertTrue(handled)
        self.assertEqual(target.state, "move")
        self.assertEqual(target.relationship_focus_target_name, "")
        self.assertEqual(target.expression_calls, [])

    def test_observe_clear_lock_can_promote_to_post_observe_interaction(self):
        target = FakeObserveTarget(x=250)
        pet = FakeObservePet(target)
        pet.intent_locked_until = 9.5
        pet.intent_reconsider_after = 10.5
        pet.expression_animation_context = "relation_close"

        with patch("tanuki_core.pet_social_care.random.random", return_value=0.0):
            handled = pet.update_observe_behavior(10.0, [target])

        self.assertTrue(handled)
        self.assertEqual(pet.intent_kind, INTENT_POST_OBSERVE_INTERACTION)
        self.assertEqual(pet.intent_context, "post_observe_interaction")
        self.assertEqual(pet.expression_animation_context, "relation_close")

    def test_post_observe_interaction_behavior_holds_idle_until_lock_expires(self):
        target = FakeObserveTarget(x=180)
        pet = FakeObservePet(target)
        pet.intent_kind = INTENT_POST_OBSERVE_INTERACTION
        pet.intent_target_name = target.name
        pet.intent_locked_until = 12.0
        pet.expression_animation_context = "relation_close"

        handled = pet.update_post_observe_interaction_behavior(10.0, [target])

        self.assertTrue(handled)
        self.assertEqual(pet.state, "idle")
        self.assertEqual(pet.direction, 1)
        self.assertEqual(
            pet.applied,
            [("idle", "side_hug", "happy", ("side-hug-happy",))],
        )
        self.assertEqual(pet.calls, [])

    def test_start_post_observe_interaction_immediately_switches_to_interaction_animation(self):
        target = FakeObserveTarget(x=180)
        pet = FakeObservePet(target)

        started = pet.start_post_observe_interaction(target, 10.0, "relation_close", 2.0)

        self.assertTrue(started)
        self.assertEqual(pet.intent_kind, INTENT_POST_OBSERVE_INTERACTION)
        self.assertEqual(
            pet.applied,
            [("idle", "side_hug", "happy", ("side-hug-happy",))],
        )


if __name__ == "__main__":
    unittest.main()
