import sys
import types
import unittest
from unittest.mock import patch

try:
    import PyQt6  # noqa: F401
    import PyQt6.QtCore  # noqa: F401
    import PyQt6.QtGui  # noqa: F401
    import PyQt6.QtWidgets  # noqa: F401
except ModuleNotFoundError:
    pass

if "PyQt6" not in sys.modules:
    pyqt6_module = types.ModuleType("PyQt6")
    qtcore_module = types.ModuleType("PyQt6.QtCore")
    qtgui_module = types.ModuleType("PyQt6.QtGui")
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

    class Qt:
        class WindowType:
            FramelessWindowHint = 0
            WindowStaysOnTopHint = 0
            Tool = 0

        class WidgetAttribute:
            WA_TranslucentBackground = 0

    class QPainter:
        RenderHint = types.SimpleNamespace(Antialiasing=0)

    class QPixmap:
        def __init__(self, *args, **kwargs):
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

    class QWidget:
        pass

    qtcore_module.QObject = QObject
    qtcore_module.QPoint = QPoint
    qtcore_module.QRect = QRect
    qtcore_module.QTimer = QTimer
    qtcore_module.QVariantAnimation = QVariantAnimation
    qtcore_module.Qt = Qt
    qtgui_module.QPainter = QPainter
    qtgui_module.QPixmap = QPixmap
    qtwidgets_module.QApplication = QApplication
    qtwidgets_module.QWidget = QWidget
    pyqt6_module.QtCore = qtcore_module
    pyqt6_module.QtGui = qtgui_module
    pyqt6_module.QtWidgets = qtwidgets_module
    sys.modules.setdefault("PyQt6", pyqt6_module)
    sys.modules.setdefault("PyQt6.QtCore", qtcore_module)
    sys.modules.setdefault("PyQt6.QtGui", qtgui_module)
    sys.modules.setdefault("PyQt6.QtWidgets", qtwidgets_module)

pyqt6_module = sys.modules.setdefault("PyQt6", types.ModuleType("PyQt6"))
qtcore_module = sys.modules.setdefault("PyQt6.QtCore", types.ModuleType("PyQt6.QtCore"))
qtgui_module = sys.modules.setdefault("PyQt6.QtGui", types.ModuleType("PyQt6.QtGui"))
qtwidgets_module = sys.modules.setdefault("PyQt6.QtWidgets", types.ModuleType("PyQt6.QtWidgets"))

if not hasattr(qtcore_module, "QTimer"):
    class _QTimer:
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

    qtcore_module.QTimer = _QTimer

if not hasattr(qtcore_module, "QVariantAnimation"):
    class _QVariantAnimation:
        def __init__(self, *args, **kwargs):
            pass

    qtcore_module.QVariantAnimation = _QVariantAnimation

if not hasattr(qtcore_module, "Qt"):
    class _Qt:
        class WindowType:
            FramelessWindowHint = 0
            WindowStaysOnTopHint = 0
            Tool = 0

        class WidgetAttribute:
            WA_TranslucentBackground = 0

    qtcore_module.Qt = _Qt

if not hasattr(qtgui_module, "QPainter"):
    class _QPainter:
        RenderHint = types.SimpleNamespace(Antialiasing=0)

    qtgui_module.QPainter = _QPainter

if not hasattr(qtgui_module, "QPixmap"):
    class _QPixmap:
        def __init__(self, *args, **kwargs):
            pass

    qtgui_module.QPixmap = _QPixmap

if not hasattr(qtwidgets_module, "QWidget"):
    class _QWidget:
        pass

    qtwidgets_module.QWidget = _QWidget

pyqt6_module.QtCore = qtcore_module
pyqt6_module.QtGui = qtgui_module
pyqt6_module.QtWidgets = qtwidgets_module

from tanuki_core.pet_behavior_layers import PetBehaviorLayersMixin
from tanuki_core.pet_intent_rules import INTENT_OBSERVE
from tanuki_core.pet_tick_coordinator import FollowupAiPlan, InitialAiPlan
from tanuki_core.pet_widget import TanukiPet


class FakeCoordinator:
    def __init__(self):
        self.intent_plan_calls = 0

    def resolve_initial_ai_plan(self, **kwargs):
        _ = kwargs
        return InitialAiPlan(
            phase="normal",
            should_move_recovery_walk=False,
            should_finish_recovery=False,
            should_attempt_followup=True,
            should_refresh_and_return=False,
        )

    def resolve_followup_ai_plan(self, **kwargs):
        _ = kwargs
        return FollowupAiPlan(
            phase="random",
            should_run_random=True,
            should_refresh_and_return=False,
        )

    def resolve_intent_reselect_plan(self, **kwargs):
        _ = kwargs
        self.intent_plan_calls += 1
        return types.SimpleNamespace(
            allow_reselect=True,
            next_reconsider_after=15.0,
            reason="test",
        )


class FakeAiSchedulerPet(PetBehaviorLayersMixin):
    def __init__(self):
        self.runtime_profiler = None
        self.tick_coordinator = FakeCoordinator()
        self.is_angry_locked = False
        self.is_recovering = False
        self.recovery_end_time = 0.0
        self.recovery_motion_mode = "stay"
        self.current_purpose = "idle"
        self.intent_kind = "ambient_idle"
        self.intent_target_name = ""
        self.intent_locked_until = 0.0
        self.intent_reconsider_after = 0.0
        self.intent_priority = 0
        self.intent_source = "ambient"
        self.intent_context = "ambient"
        self.intent_reason = ""
        self.dragging = False
        self.care_mode = "none"
        self.social_mode = "none"
        self.flight_mode = "none"
        self.perched_window_hwnd = 0
        self.offer_scene_kind = "none"
        self.behavior_layer_refresh_skip_counter = 0
        self.behavior_layer_refresh_divisor = 1
        self.high_level_ai_refresh_skip_counter = 0
        self.high_level_ai_refresh_divisor = 1
        self.care_calls = 0
        self.social_calls = 0
        self.post_observe_calls = 0
        self.observe_calls = 0
        self.ambient_calls = 0
        self.random_calls = 0
        self.random_allow_reselect = []
        self.refresh_calls = 0

    def maintain_care_lock(self, now):
        _ = now
        return False

    def update_care_behavior(self, now, all_pets):
        _ = (now, all_pets)
        self.care_calls += 1
        return False

    def update_social_behavior(self, now, all_pets):
        _ = (now, all_pets)
        self.social_calls += 1
        return False

    def update_post_observe_interaction_behavior(self, now, all_pets):
        _ = (now, all_pets)
        self.post_observe_calls += 1
        return False

    def update_observe_behavior(self, now, all_pets):
        _ = (now, all_pets)
        self.observe_calls += 1
        return False

    def update_ambient_mood_events(self, now):
        _ = now
        self.ambient_calls += 1
        return False

    def update_random_behavior(self, allow_reselect=False):
        self.random_calls += 1
        self.random_allow_reselect.append(bool(allow_reselect))

    def refresh_movement_state(self):
        self.refresh_calls += 1

    def change_state(self, purpose, action_type=None):
        _ = (purpose, action_type)

    def move_logic(self):
        return None

    def reset_stationary_move_mode(self):
        return None


class PetAiSchedulerTests(unittest.TestCase):
    def test_update_ai_behavior_throttles_high_level_followups_but_keeps_random_reselect_each_tick(self):
        pet = FakeAiSchedulerPet()

        with patch("tanuki_core.pet_widget.app_now", return_value=10.0), patch(
            "tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 4.0
        ):
            TanukiPet.update_ai_behavior(pet, [])
            TanukiPet.update_ai_behavior(pet, [])

        self.assertEqual(pet.post_observe_calls, 1)
        self.assertEqual(pet.observe_calls, 1)
        self.assertEqual(pet.ambient_calls, 1)
        self.assertEqual(pet.tick_coordinator.intent_plan_calls, 2)
        self.assertEqual(pet.random_calls, 2)
        self.assertEqual(pet.random_allow_reselect, [True, True])

    def test_update_ai_behavior_keeps_active_observe_running_each_tick(self):
        pet = FakeAiSchedulerPet()
        pet.intent_kind = INTENT_OBSERVE
        pet.intent_target_name = "Air Groove"
        pet.intent_locked_until = 25.0

        def active_observe(now, all_pets):
            _ = (now, all_pets)
            pet.observe_calls += 1
            return True

        pet.update_observe_behavior = active_observe

        with patch("tanuki_core.pet_widget.app_now", return_value=10.0), patch(
            "tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0
        ):
            TanukiPet.update_ai_behavior(pet, [])
            TanukiPet.update_ai_behavior(pet, [])

        self.assertEqual(pet.observe_calls, 2)
        self.assertEqual(pet.tick_coordinator.intent_plan_calls, 0)
        self.assertEqual(pet.random_calls, 0)

    def test_update_ai_behavior_runs_expired_observe_once_for_clear_or_post_observe(self):
        pet = FakeAiSchedulerPet()
        pet.intent_kind = INTENT_OBSERVE
        pet.intent_target_name = "Air Groove"
        pet.intent_locked_until = 9.5

        def expired_observe(now, all_pets):
            _ = (now, all_pets)
            pet.observe_calls += 1
            return True

        pet.update_observe_behavior = expired_observe

        with patch("tanuki_core.pet_widget.app_now", return_value=10.0), patch(
            "tanuki_core.pet_behavior_layers.SIM_CLOCK.speed", 8.0
        ):
            TanukiPet.update_ai_behavior(pet, [])

        self.assertEqual(pet.observe_calls, 1)
        self.assertEqual(pet.tick_coordinator.intent_plan_calls, 0)
        self.assertEqual(pet.random_calls, 0)


if __name__ == "__main__":
    unittest.main()
