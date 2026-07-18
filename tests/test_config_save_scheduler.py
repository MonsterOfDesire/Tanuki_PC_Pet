import unittest

from tests.qt_test_support import QT_BINDINGS_AVAILABLE, QtApplicationTestCase


if QT_BINDINGS_AVAILABLE:
    from tanuki_core.config_save_scheduler import ConfigSaveScheduler
else:
    ConfigSaveScheduler = None


class FakeConfigStore:
    def __init__(self):
        self.calls = []

    def save_now(self, force=False):
        self.calls.append(force)


@unittest.skipUnless(QT_BINDINGS_AVAILABLE, "PyQt6 is required for Qt timer tests")
class ConfigSaveSchedulerQtTests(QtApplicationTestCase):
    def setUp(self):
        self.schedulers = []

    def tearDown(self):
        for scheduler in self.schedulers:
            scheduler.save_timer.stop()

    def build_scheduler(self, *args, **kwargs):
        scheduler = ConfigSaveScheduler(*args, **kwargs)
        self.schedulers.append(scheduler)
        return scheduler

    def test_schedule_can_arm_timer_when_autosave_is_enabled(self):
        store = FakeConfigStore()
        scheduler = self.build_scheduler(
            lambda: store,
            delay_ms=900,
            autosave_enabled=True,
        )

        scheduler.schedule()

        self.assertTrue(scheduler.save_timer.isActive())
        self.assertEqual(scheduler.save_timer.interval(), 900)

    def test_save_now_stops_timer_and_delegates(self):
        store = FakeConfigStore()
        scheduler = self.build_scheduler(
            lambda: store,
            delay_ms=900,
            autosave_enabled=True,
        )
        scheduler.schedule()

        scheduler.save_now(force=True)

        self.assertFalse(scheduler.save_timer.isActive())
        self.assertEqual(store.calls, [True])


if __name__ == "__main__":
    unittest.main()
