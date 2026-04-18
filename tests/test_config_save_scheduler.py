import unittest

from tanuki_core.config_save_scheduler import ConfigSaveScheduler


class FakeConfigStore:
    def __init__(self):
        self.calls = []

    def save_now(self, force=False):
        self.calls.append(force)


class ConfigSaveSchedulerTests(unittest.TestCase):
    def test_schedule_is_disabled_by_default(self):
        store = FakeConfigStore()
        scheduler = ConfigSaveScheduler(lambda: store, delay_ms=900)

        scheduler.schedule()

        self.assertFalse(scheduler.save_timer.isActive())

    def test_schedule_can_arm_timer_when_autosave_is_enabled(self):
        store = FakeConfigStore()
        scheduler = ConfigSaveScheduler(lambda: store, delay_ms=900, autosave_enabled=True)

        scheduler.schedule()

        self.assertTrue(scheduler.save_timer.isActive())
        self.assertEqual(scheduler.save_timer.interval(), 900)

    def test_save_now_stops_timer_and_delegates(self):
        store = FakeConfigStore()
        scheduler = ConfigSaveScheduler(lambda: store, delay_ms=900)
        scheduler.schedule()

        scheduler.save_now(force=True)

        self.assertFalse(scheduler.save_timer.isActive())
        self.assertEqual(store.calls, [True])


if __name__ == "__main__":
    unittest.main()
