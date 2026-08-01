import unittest
import sys
import types
from unittest.mock import patch

try:
    import PyQt6  # noqa: F401
    import PyQt6.QtCore  # noqa: F401
    import PyQt6.QtGui  # noqa: F401
    import PyQt6.QtWidgets  # noqa: F401
except ModuleNotFoundError:
    pass


pyqt6_module = sys.modules.get("PyQt6") or types.ModuleType("PyQt6")
qtcore_module = sys.modules.get("PyQt6.QtCore") or types.ModuleType("PyQt6.QtCore")
qtgui_module = sys.modules.get("PyQt6.QtGui") or types.ModuleType("PyQt6.QtGui")
qtwidgets_module = sys.modules.get("PyQt6.QtWidgets") or types.ModuleType("PyQt6.QtWidgets")


class QObject:
    pass


class QTimer:
    def __init__(self, *args, **kwargs):
        pass

    def setSingleShot(self, *args, **kwargs):
        pass

    def setTimerType(self, *args, **kwargs):
        pass

    @property
    def timeout(self):
        return types.SimpleNamespace(connect=lambda *args, **kwargs: None)

    def start(self, *args, **kwargs):
        pass

    def stop(self):
        pass


class QVariantAnimation:
    def __init__(self, *args, **kwargs):
        pass


class QRect:
    def __init__(self, *args, **kwargs):
        pass

    def united(self, other):
        _ = other
        return self


class Qt:
    class WindowType:
        FramelessWindowHint = 0
        WindowStaysOnTopHint = 0
        Tool = 0

    class WidgetAttribute:
        WA_TranslucentBackground = 0

    class MouseButton:
        LeftButton = 1

    class CursorShape:
        ForbiddenCursor = 0


class QPainter:
    RenderHint = types.SimpleNamespace(Antialiasing=0)


class QPixmap:
    def __init__(self, *args, **kwargs):
        pass


class QWidget:
    pass


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


if not hasattr(qtcore_module, "QObject"):
    qtcore_module.QObject = QObject
if not hasattr(qtcore_module, "QTimer"):
    qtcore_module.QTimer = QTimer
if not hasattr(qtcore_module, "QVariantAnimation"):
    qtcore_module.QVariantAnimation = QVariantAnimation
if not hasattr(qtcore_module, "QRect"):
    qtcore_module.QRect = QRect
if not hasattr(qtcore_module, "Qt"):
    qtcore_module.Qt = Qt
if not hasattr(qtgui_module, "QPainter"):
    qtgui_module.QPainter = QPainter
if not hasattr(qtgui_module, "QPixmap"):
    qtgui_module.QPixmap = QPixmap
if not hasattr(qtwidgets_module, "QApplication"):
    qtwidgets_module.QApplication = QApplication
if not hasattr(qtwidgets_module, "QWidget"):
    qtwidgets_module.QWidget = QWidget

pyqt6_module.QtCore = qtcore_module
pyqt6_module.QtGui = qtgui_module
pyqt6_module.QtWidgets = qtwidgets_module
sys.modules["PyQt6"] = pyqt6_module
sys.modules["PyQt6.QtCore"] = qtcore_module
sys.modules["PyQt6.QtGui"] = qtgui_module
sys.modules["PyQt6.QtWidgets"] = qtwidgets_module


from tanuki_core.geometry import DesktopGeometry
from tanuki_core.pet_basics import PetBasicsMixin
from tanuki_core.pet_widget import Qt, TanukiPet
from tanuki_core.pet_logic import MoodUpdate


class FakeStarTimer:
    def __init__(self):
        self.stopped = 0

    def stop(self):
        self.stopped += 1


class FakeAnimationTimer:
    def __init__(self, interval_ms):
        self.interval_ms = interval_ms

    def interval(self):
        return self.interval_ms


class FakeControlledTimer:
    def __init__(self):
        self.started_with = []
        self.stop_calls = 0

    def start(self, interval_ms):
        self.started_with.append(interval_ms)

    def stop(self):
        self.stop_calls += 1


class FakePoint:
    def __init__(self, x=0, y=0):
        self._x = int(x)
        self._y = int(y)

    def __sub__(self, other):
        return FakePoint(self._x - other._x, self._y - other._y)

    def x(self):
        return self._x

    def y(self):
        return self._y


class FakeMouseEvent:
    def __init__(self, x=100, y=120):
        self._point = FakePoint(x, y)

    def button(self):
        return Qt.MouseButton.LeftButton

    def globalPosition(self):
        return types.SimpleNamespace(toPoint=lambda: self._point)


class FakePetForPointerInteraction:
    DRAG_HOLD_THRESHOLD_MS = TanukiPet.DRAG_HOLD_THRESHOLD_MS
    DRAG_HOLD_THRESHOLD_SECONDS = TanukiPet.DRAG_HOLD_THRESHOLD_SECONDS
    DRAG_MOVE_THRESHOLD_PIXELS = TanukiPet.DRAG_MOVE_THRESHOLD_PIXELS

    def __init__(self, activity_locked=False):
        self.transformation_state = types.SimpleNamespace(active=False)
        self.dragging = False
        self.drag_press_pending = False
        self.drag_motion_detected = False
        self.drag_press_global_x = 0
        self.drag_press_global_y = 0
        self.drag_start_time = 0.0
        self.drag_pos = FakePoint()
        self.drag_hold_timer = FakeControlledTimer()
        self.click_reset_timer = FakeControlledTimer()
        self.lock_timer = FakeControlledTimer()
        self.click_count = 0
        self.is_angry_locked = False
        self.care_mode = "none"
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.vy = 3.0
        self.fall_origin_y = 10
        self.mood_score = 60.0
        self.state = "move"
        self.state_timer = 0
        self._activity_locked = bool(activity_locked)
        self.drag_animation_calls = 0
        self.interrupt_reasons = []
        self.reactions = []
        self.heart_calls = 0
        self.refresh_calls = 0
        self.changed_states = []
        self.moved_to = None
        self.activity_user_interrupt_provider = self._interrupt_activity

    def pos(self):
        return FakePoint(10, 20)

    def is_activity_locked(self):
        return self._activity_locked

    def is_under_care(self, now):
        _ = now
        return False

    def is_offer_locked(self, now=None):
        _ = now
        return False

    def _interrupt_activity(self, pet, reason):
        self.interrupt_reasons.append((pet, reason))
        if reason == "user_drag":
            self._activity_locked = False
        return True

    def _cancel_pending_drag_press(self):
        return TanukiPet._cancel_pending_drag_press(self)

    def _begin_drag_after_hold(self):
        return TanukiPet._begin_drag_after_hold(self)

    def _apply_short_click_interaction(self):
        return TanukiPet._apply_short_click_interaction(self)

    def apply_drag_animation(self):
        self.drag_animation_calls += 1
        return True

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def stop_window_flight(self, apply_cooldown=True):
        _ = apply_cooldown
        self.flight_mode = "none"

    def pop_heart(self):
        self.heart_calls += 1

    def apply_reaction(self, preferred_moods, is_negative=False):
        self.reactions.append((tuple(preferred_moods), bool(is_negative)))

    def try_snap_to_window_surface(self):
        return False

    def move(self, x, y):
        self.moved_to = (x, y)

    def change_state(self, purpose, action_type=None):
        self.changed_states.append((purpose, action_type))


class FakePetForHardLandingAnimation(PetBasicsMixin):
    def __init__(self, selection_results):
        self.selection_results = list(selection_results)
        self.context_calls = []
        self.state_timer = 0
        self.stationary_reset_calls = 0

    def change_state_for_context_any_purpose_with_preferences(
        self,
        context,
        **kwargs,
    ):
        self.context_calls.append((context, kwargs))
        return self.selection_results.pop(0)

    def reset_stationary_move_mode(self):
        self.stationary_reset_calls += 1


class FakePetForStars:
    def __init__(self):
        self.social_mode = "following"
        self.offer_scene_kind = "direct_accept"
        self.star_opacity = 0.4
        self.star_anim_counter = 0
        self.star_y_offset = 0
        self.star_timer = FakeStarTimer()
        self.updated = 0

    def update(self):
        self.updated += 1


class FakeAssetManagerForIdleOverride:
    def get_specific_frames(self, purpose, action_type, mood, mood_score=None):
        return None

    def get_frames_for_action_by_preferences(self, purpose, action_type, preferred_moods, forbidden=None, mood_score=None):
        return None

    def get_frames_by_score(self, purpose, action_type=None, mood_score=60.0, is_adult=False, context=None):
        return ["frame"], "side_stand", "happy"

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        if action_type == "side_ready":
            return ["ready"], "side_ready", "smile"
        return None


class FakePetForIdleOverride:
    def __init__(self):
        self.name = "Tsurumaru Tsuyoshi"
        self.current_purpose = "idle"
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"
        self.idle_side_stand_armed = False
        self.mood_score = 60.0
        self.is_adult = False
        self.asset_manager = FakeAssetManagerForIdleOverride()
        self.applied = None

    def get_negative_afterglow_preferences(self):
        return (), ()

    def apply_animation_result(self, purpose, result):
        self.applied = (purpose, result)
        return True


class FakeAssetManagerForDirectSideStand:
    def get_specific_frames(self, purpose, action_type, mood, mood_score=None):
        if purpose == "idle" and action_type == "side_ready" and mood == "happy":
            return ["ready"]
        return None

    def get_frames_for_action_by_score(self, purpose, action_type, mood_score=60.0, is_adult=False, context=None):
        if purpose == "idle" and action_type == "side_ready":
            return ["ready"], "side_ready", "smile"
        return None


class FakeAssetManagerForContextExpansion:
    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        if purpose == "idle" and context == "random":
            return ["side_stand", "stand"]
        return []


class FakeAssetManagerForRandomManifest:
    def __init__(self):
        self.context_calls = []

    def get_action_keys_for_context(self, purpose, mood_score=None, context=None):
        self.context_calls.append((purpose, mood_score, context))
        if purpose == "move" and context == "random":
            return ["manifest_walk"]
        if purpose == "idle" and context == "random":
            return ["manifest_stand"]
        return []


class FakePetForDirectSideStand:
    def __init__(self):
        self.name = "Tsurumaru Tsuyoshi"
        self.current_purpose = "idle"
        self.current_action_tag = "stand"
        self.current_mood_tag = "happy"
        self.idle_side_stand_armed = False
        self.mood_score = 60.0
        self.is_adult = False
        self.asset_manager = FakeAssetManagerForDirectSideStand()
        self.current_frames = []
        self.frame_index = 0
        self.animation_step_budget = 1.0


class FakePetForContextExpansion:
    def __init__(self, armed=False):
        self.name = "Tsurumaru Tsuyoshi"
        self.mood_score = 60.0
        self.idle_side_stand_armed = armed
        self.asset_manager = FakeAssetManagerForContextExpansion()


class FakePetForRandomManifest:
    def __init__(self):
        self.name = "Tokai Teio"
        self.state = "move"
        self.state_timer = 80
        self.mood_score = 60.0
        self.current_purpose = ""
        self.current_action_tag = ""
        self.current_mood_tag = ""
        self.direction = 1
        self.stationary_move_mode = False
        self.stuck_count = 0
        self.last_x = 10
        self.expression_animation_context = "ambient"
        self.asset_manager = FakeAssetManagerForRandomManifest()
        self.changed_candidates = []
        self.moved = 0
        self.stationary_configured = []

    def x(self):
        return 15

    def get_base_speed(self):
        return 2.0

    def get_random_animation_context(self):
        return "random"

    def get_random_manifest_candidates(self, purpose, context="random"):
        return TanukiPet.get_random_manifest_candidates(self, purpose, context=context)

    def expand_candidates_with_context(self, purpose, candidates, context=None):
        return TanukiPet.expand_candidates_with_context(self, purpose, candidates, context=context)

    def get_randomized_candidates(self, candidates):
        return list(candidates)

    def change_state_candidates(self, candidates, context=None):
        self.changed_candidates.append((list(candidates), context))
        if not candidates:
            return False
        purpose, action_type = candidates[0]
        self.current_purpose = purpose
        self.current_action_tag = action_type
        self.current_mood_tag = "happy"
        return True

    def try_start_window_flight(self, now):
        _ = now
        return False

    def move_logic(self):
        self.moved += 1

    def configure_stationary_move_mode(self, context="random", force=False):
        self.stationary_configured.append((context, force, self.current_action_tag))

    def should_apply_negative_afterglow_to_candidates(self, candidates):
        _ = candidates
        return False

    def get_move_candidates(self):
        raise AssertionError("random should not use pet_social_catalog move candidates")

    def get_idle_candidates(self):
        raise AssertionError("random should not use pet_social_catalog idle candidates")


class FakePetForBehaviorProbeLabel:
    def __init__(self, intent_kind="random_roam", intent_context="random_move", expression_context="ambient"):
        self.intent_kind = intent_kind
        self.intent_context = intent_context
        self.expression_animation_context = expression_context


class FakePetForAnimationTiming:
    ANIMATION_BASE_INTERVAL_MS = 80
    STAR_BASE_INTERVAL_MS = 30

    def __init__(self):
        self.current_frames = ["a", "b", "c", "d", "e"]
        self.frame_index = 0
        self.updated = 0
        self.social_mode = "following"
        self.offer_scene_kind = "none"
        self.star_opacity = 0.0
        self.star_anim_counter = 0
        self.star_y_offset = 0
        self.star_timer = FakeStarTimer()

    def update(self):
        self.updated += 1

    def next_frame(self, steps=1):
        TanukiPet.next_frame(self, steps=steps)

    def update_star_animation(self):
        TanukiPet.update_star_animation(self)


class FakeScaledMotionSurface:
    left_bound = 0
    right_bound = 500

    def clamp_x(self, x):
        return max(self.left_bound, min(self.right_bound, int(x)))


class FakePetForScaledMotion:
    def __init__(self, step_scale=4.0):
        self._x = 10
        self._y = 20
        self.direction = 1
        self.logic_step_scale = step_scale
        self.movement_refreshes = 0

    def x(self):
        return self._x

    def y(self):
        return self._y

    def move(self, x, y):
        self._x = int(x)
        self._y = int(y)

    def get_base_speed(self):
        return 2.9

    def get_surface_snapshot(self):
        return FakeScaledMotionSurface()

    def refresh_movement_state(self):
        self.movement_refreshes += 1


class FakePetForMoodAnimationGuard:
    def __init__(self):
        self.mood_score = 60.0
        self.mood_state = "normal"
        self.lonely_timer = 0
        self.distress_ready_at = 1.0
        self.is_adult = False
        self.state = "idle"
        self.current_purpose = "interaction"
        self.current_action_tag = "scene_action"
        self.offer_scene_kind = "none"
        self.offer_locked_until = 0.0
        self.care_mode = "none"
        self.care_partner = None
        self.care_lock_mode = "none"
        self.care_lock_end_time = 0.0
        self.change_calls = []

    def geometry(self):
        return types.SimpleNamespace(center=lambda: object())

    def isVisible(self):
        return True

    def is_offer_locked(self, now=None):
        return TanukiPet.is_offer_locked(self, now)

    def is_under_care(self, now):
        return (
            self.care_partner is not None and
            self.care_lock_mode != "none" and
            float(now) < float(self.care_lock_end_time)
        )

    def is_scene_animation_locked(self, now=None):
        return TanukiPet.is_scene_animation_locked(self, now)

    def refresh_animation_for_mood_change(self, now=None):
        return TanukiPet.refresh_animation_for_mood_change(self, now)

    def change_state(self, purpose, action_type=None):
        self.change_calls.append((purpose, action_type))


class PetWidgetRuntimeTests(unittest.TestCase):
    def test_short_click_never_enters_drag_animation(self):
        pet = FakePetForPointerInteraction()
        event = FakeMouseEvent()

        with patch("tanuki_core.pet_widget.time.time", return_value=100.0):
            TanukiPet.mousePressEvent(pet, event)

        self.assertTrue(pet.drag_press_pending)
        self.assertFalse(pet.dragging)
        self.assertEqual(pet.drag_animation_calls, 0)
        self.assertEqual(
            pet.drag_hold_timer.started_with,
            [TanukiPet.DRAG_HOLD_THRESHOLD_MS],
        )

        with patch("tanuki_core.pet_widget.time.time", return_value=100.1):
            TanukiPet.mouseReleaseEvent(pet, event)

        self.assertFalse(pet.drag_press_pending)
        self.assertFalse(pet.dragging)
        self.assertEqual(pet.drag_animation_calls, 0)
        self.assertEqual(pet.heart_calls, 1)
        self.assertEqual(pet.reactions, [(('happy', 'smile'), False)])

    def test_sleeping_short_click_requests_waking_without_drag(self):
        pet = FakePetForPointerInteraction(activity_locked=True)
        event = FakeMouseEvent()

        with patch("tanuki_core.pet_widget.time.time", return_value=200.0):
            TanukiPet.mousePressEvent(pet, event)
        with patch("tanuki_core.pet_widget.time.time", return_value=200.1):
            TanukiPet.mouseReleaseEvent(pet, event)

        self.assertEqual(
            pet.interrupt_reasons,
            [(pet, "user_click")],
        )
        self.assertEqual(pet.drag_animation_calls, 0)
        self.assertEqual(pet.heart_calls, 0)

    def test_stationary_hold_is_still_a_click_without_drag(self):
        pet = FakePetForPointerInteraction()
        event = FakeMouseEvent()

        with patch("tanuki_core.pet_widget.time.time", return_value=250.0):
            TanukiPet.mousePressEvent(pet, event)
        with patch("tanuki_core.pet_widget.time.time", return_value=250.3):
            TanukiPet.mouseReleaseEvent(pet, event)

        self.assertFalse(pet.dragging)
        self.assertEqual(pet.drag_animation_calls, 0)
        self.assertEqual(pet.heart_calls, 1)

    def test_pointer_motion_starts_drag_after_short_threshold(self):
        pet = FakePetForPointerInteraction()
        press_event = FakeMouseEvent(100, 120)
        move_event = FakeMouseEvent(104, 120)

        with patch("tanuki_core.pet_widget.time.time", return_value=275.0):
            TanukiPet.mousePressEvent(pet, press_event)
        with patch(
            "tanuki_core.pet_widget.time.time",
            return_value=275.051,
        ), patch.object(
            DesktopGeometry,
            "clamp_drag_position",
            return_value=(14, 20),
        ):
            TanukiPet.mouseMoveEvent(pet, move_event)

        self.assertTrue(pet.dragging)
        self.assertEqual(pet.drag_animation_calls, 1)
        self.assertEqual(pet.moved_to, (14, 20))

    def test_hold_threshold_starts_drag_and_uses_drag_interrupt(self):
        pet = FakePetForPointerInteraction(activity_locked=True)
        event = FakeMouseEvent()

        with patch("tanuki_core.pet_widget.time.time", return_value=300.0):
            TanukiPet.mousePressEvent(pet, event)
        pet.drag_motion_detected = True
        with patch("tanuki_core.pet_widget.time.time", return_value=300.21):
            started = TanukiPet._begin_drag_after_hold(pet)

        self.assertTrue(started)
        self.assertFalse(pet.drag_press_pending)
        self.assertTrue(pet.dragging)
        self.assertEqual(
            pet.interrupt_reasons,
            [(pet, "user_drag")],
        )
        self.assertEqual(pet.drag_animation_calls, 1)

    def test_hard_landing_prefers_current_band_with_strict_context(self):
        pet = FakePetForHardLandingAnimation([True])

        applied = pet.apply_hard_landing_animation()

        self.assertTrue(applied)
        self.assertEqual(pet.context_calls, [("hard_landing", {})])
        self.assertEqual(pet.state_timer, 80)
        self.assertEqual(pet.stationary_reset_calls, 1)

    def test_hard_landing_relaxes_only_band_not_context(self):
        pet = FakePetForHardLandingAnimation([False, True])

        applied = pet.apply_hard_landing_animation()

        self.assertTrue(applied)
        self.assertEqual(
            pet.context_calls,
            [
                ("hard_landing", {}),
                ("hard_landing", {"ignore_mood_band": True}),
            ],
        )

    def test_scene_animation_lock_keeps_offer_scene_protected_after_deadline_until_cleared(self):
        pet = FakePetForMoodAnimationGuard()
        pet.offer_scene_kind = "bottle_feed"
        pet.offer_locked_until = 5.0

        self.assertTrue(TanukiPet.is_offer_locked(pet, now=6.0))
        self.assertTrue(TanukiPet.is_scene_animation_locked(pet, now=6.0))

        pet.offer_scene_kind = "none"
        self.assertFalse(TanukiPet.is_scene_animation_locked(pet, now=6.0))

    def test_sync_mood_updates_state_without_replacing_offer_scene_animation(self):
        pet = FakePetForMoodAnimationGuard()
        pet.offer_scene_kind = "bottle_feed"
        pet.mood_score = 10.0

        TanukiPet.sync_mood_state_with_score(pet)

        self.assertEqual(pet.mood_state, "depressed")
        self.assertEqual(pet.change_calls, [])

    def test_sync_mood_updates_state_without_replacing_care_animation(self):
        pet = FakePetForMoodAnimationGuard()
        pet.care_mode = "interaction"
        pet.mood_score = 10.0

        TanukiPet.sync_mood_state_with_score(pet)

        self.assertEqual(pet.mood_state, "depressed")
        self.assertEqual(pet.change_calls, [])

    def test_sync_mood_refreshes_animation_outside_scripted_scene(self):
        pet = FakePetForMoodAnimationGuard()
        pet.mood_score = 10.0

        TanukiPet.sync_mood_state_with_score(pet)

        self.assertEqual(pet.change_calls, [("interaction", "scene_action")])

    def test_mood_timer_update_preserves_scripted_scene_animation(self):
        pet = FakePetForMoodAnimationGuard()
        pet.offer_scene_kind = "direct_accept"
        mood_update = MoodUpdate(mood_score=10.0, mood_state="depressed", lonely_timer=3)

        with patch("tanuki_core.pet_widget.compute_mood_update", return_value=mood_update):
            TanukiPet.update_mood(pet, [pet])

        self.assertEqual(pet.mood_score, 10.0)
        self.assertEqual(pet.mood_state, "depressed")
        self.assertEqual(pet.lonely_timer, 3)
        self.assertEqual(pet.change_calls, [])

    def test_update_star_animation_hides_social_stars_during_offer_scene(self):
        pet = FakePetForStars()

        for _ in range(5):
            TanukiPet.update_star_animation(pet)

        self.assertEqual(pet.star_opacity, 0.0)
        self.assertGreaterEqual(pet.star_timer.stopped, 1)

    def test_change_state_for_tsuyoshi_routes_side_stand_through_side_ready_first(self):
        pet = FakePetForIdleOverride()

        TanukiPet.change_state(pet, "idle")

        self.assertEqual(pet.applied, ("idle", (["ready"], "side_ready", "smile")))

    def test_apply_animation_result_for_tsuyoshi_routes_direct_side_stand_through_side_ready(self):
        pet = FakePetForDirectSideStand()

        applied = TanukiPet.apply_animation_result(pet, "idle", (["stand"], "side_stand", "happy"))

        self.assertTrue(applied)
        self.assertEqual(pet.current_action_tag, "side_ready")
        self.assertEqual(pet.current_mood_tag, "happy")
        self.assertEqual(pet.current_frames, ["ready"])
        self.assertTrue(pet.idle_side_stand_armed)

    def test_apply_animation_result_for_tsuyoshi_consumes_side_ready_arm_on_immediate_side_stand(self):
        pet = FakePetForDirectSideStand()
        pet.current_action_tag = "side_ready"
        pet.idle_side_stand_armed = True

        applied = TanukiPet.apply_animation_result(pet, "idle", (["stand"], "side_stand", "happy"))

        self.assertTrue(applied)
        self.assertEqual(pet.current_action_tag, "side_stand")
        self.assertFalse(pet.idle_side_stand_armed)

    def test_expand_candidates_with_context_blocks_tsuyoshi_side_stand_when_not_armed(self):
        pet = FakePetForContextExpansion(armed=False)

        candidates = TanukiPet.expand_candidates_with_context(pet, "idle", [("idle", "side")], context="random")

        self.assertEqual(candidates, [("idle", "side"), ("idle", "stand")])

    def test_expand_candidates_with_context_allows_tsuyoshi_side_stand_when_armed(self):
        pet = FakePetForContextExpansion(armed=True)

        candidates = TanukiPet.expand_candidates_with_context(pet, "idle", [("idle", "side")], context="random")

        self.assertEqual(candidates, [("idle", "side"), ("idle", "side_stand"), ("idle", "stand")])

    def test_random_behavior_uses_manifest_random_context_without_catalog_candidates(self):
        pet = FakePetForRandomManifest()

        TanukiPet.update_random_behavior(pet)

        self.assertEqual(pet.changed_candidates, [([("move", "manifest_walk")], "random")])
        self.assertEqual(pet.asset_manager.context_calls, [("move", 60.0, "random")])
        self.assertEqual(pet.stationary_configured, [("random", True, "manifest_walk")])
        self.assertEqual(pet.moved, 1)

    def test_behavior_probe_label_shows_goal_and_expression_layers(self):
        self.assertEqual(
            TanukiPet.get_behavior_probe_label(FakePetForBehaviorProbeLabel()),
            "random",
        )
        self.assertEqual(
            TanukiPet.get_behavior_probe_label(
                FakePetForBehaviorProbeLabel(expression_context="relation_watch")
            ),
            "random / relation_watch",
        )
        self.assertEqual(
            TanukiPet.get_behavior_probe_label(
                FakePetForBehaviorProbeLabel(expression_context="relation_close")
            ),
            "random / relation_close",
        )
        self.assertEqual(
            TanukiPet.get_behavior_probe_label(
                FakePetForBehaviorProbeLabel(
                    intent_kind="observe",
                    intent_context="observe",
                    expression_context="relation_watch",
                )
            ),
            "observe / relation_watch",
        )
        self.assertEqual(
            TanukiPet.get_behavior_probe_label(
                FakePetForBehaviorProbeLabel(
                    intent_kind="post_observe_interaction",
                    intent_context="post_observe_interaction",
                    expression_context="relation_close",
                )
            ),
            "post_observe / relation_close",
        )

    def test_behavior_probe_overlay_setting_defaults_off_and_can_enable(self):
        pet = type(
            "ProbePet",
            (),
            {
                "settings_provider": type(
                    "Settings",
                    (),
                    {"social_status_enabled": False},
                )(),
            },
        )()

        self.assertFalse(TanukiPet.is_social_status_enabled(pet))

        pet.settings_provider.social_status_enabled = True

        self.assertTrue(TanukiPet.is_social_status_enabled(pet))

    def test_advance_animation_timer_advances_one_frame_per_callback(self):
        pet = FakePetForAnimationTiming()
        pet.animation_frame_accumulator = 0.75

        with patch("tanuki_core.pet_widget.SIM_CLOCK.speed", 1.0), patch(
            "tanuki_core.pet_widget.SIM_CLOCK.get_timer_step_delta"
        ) as get_step_delta:
            TanukiPet.advance_animation_timer(pet)

        self.assertEqual(pet.frame_index, 1)
        self.assertEqual(pet.updated, 1)
        self.assertEqual(pet.animation_frame_accumulator, 0.0)
        get_step_delta.assert_not_called()

    def test_advance_animation_timer_loops_frames_normally(self):
        pet = FakePetForAnimationTiming()
        pet.frame_index = 4

        TanukiPet.advance_animation_timer(pet)

        self.assertEqual(pet.frame_index, 0)
        self.assertEqual(pet.updated, 1)

    def test_advance_animation_timer_avoids_even_frame_phase_lock_at_8x(self):
        pet = FakePetForAnimationTiming()
        pet.current_frames = ["a", "b", "c", "d"]
        pet.anim_timer = FakeAnimationTimer(17)
        pet.animation_frame_accumulator = 0.0
        pet.isVisible = lambda: True
        visited_frames = []

        with patch("tanuki_core.pet_widget.SIM_CLOCK.speed", 8.0), patch(
            "tanuki_core.pet_widget.SIM_CLOCK.get_timer_step_delta",
            return_value=1.7,
        ) as get_step_delta:
            for _ in range(5):
                TanukiPet.advance_animation_timer(pet)
                visited_frames.append(pet.frame_index)

        self.assertEqual(get_step_delta.call_count, 5)
        get_step_delta.assert_called_with(80, actual_interval_ms=17)
        self.assertEqual(set(visited_frames), {0, 1, 2, 3})
        self.assertEqual(pet.updated, 5)

    def test_advance_animation_timer_accumulates_fractional_frames(self):
        pet = FakePetForAnimationTiming()
        pet.anim_timer = FakeAnimationTimer(30)
        pet.animation_frame_accumulator = 0.0
        pet.isVisible = lambda: True

        with patch("tanuki_core.pet_widget.SIM_CLOCK.speed", 4.0), patch(
            "tanuki_core.pet_widget.SIM_CLOCK.get_timer_step_delta",
            return_value=1.5,
        ):
            TanukiPet.advance_animation_timer(pet)
            TanukiPet.advance_animation_timer(pet)

        self.assertEqual(pet.frame_index, 3)
        self.assertEqual(pet.updated, 2)
        self.assertEqual(pet.animation_frame_accumulator, 0.0)

    def test_advance_animation_timer_skips_hidden_widget_work(self):
        pet = FakePetForAnimationTiming()
        pet.anim_timer = FakeAnimationTimer(20)
        pet.animation_frame_accumulator = 0.0
        pet.isVisible = lambda: False

        with patch(
            "tanuki_core.pet_widget.SIM_CLOCK.get_timer_step_delta",
        ) as get_step_delta:
            TanukiPet.advance_animation_timer(pet)

        get_step_delta.assert_not_called()
        self.assertEqual(pet.frame_index, 0)
        self.assertEqual(pet.updated, 0)

    def test_advance_star_animation_advances_once_per_callback(self):
        pet = FakePetForAnimationTiming()

        TanukiPet.advance_star_animation(pet)
        TanukiPet.advance_star_animation(pet)

        self.assertEqual(pet.star_anim_counter, 2)
        self.assertGreater(pet.star_opacity, 0.0)

    def test_move_logic_applies_high_load_step_scale(self):
        pet = FakePetForScaledMotion(step_scale=4.0)

        TanukiPet.move_logic(pet)

        self.assertEqual(pet.x(), 18)
        self.assertEqual(pet.movement_refreshes, 1)

    def test_move_toward_x_applies_step_scale_without_overshooting_target(self):
        pet = FakePetForScaledMotion(step_scale=4.0)

        arrived = TanukiPet.move_toward_x(pet, 15)

        self.assertTrue(arrived)
        self.assertEqual(pet.x(), 15)


if __name__ == "__main__":
    unittest.main()
