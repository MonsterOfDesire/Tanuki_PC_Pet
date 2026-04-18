import unittest

from tanuki_core.dashboard_shell_lifecycle import DashboardShellLifecycle, shutdown_listener


class FakeListener:
    def __init__(self):
        self.stop_calls = 0
        self.join_calls = []

    def stop(self):
        self.stop_calls += 1

    def join(self, timeout=None):
        self.join_calls.append(timeout)


class FakeShellPart:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


class DashboardShellLifecycleTests(unittest.TestCase):
    def test_shutdown_listener_stops_and_joins_once(self):
        listener = FakeListener()

        shutdown_listener(listener)

        self.assertEqual(listener.stop_calls, 1)
        self.assertEqual(listener.join_calls, [0.2])

    def test_dashboard_shell_lifecycle_shutdown_is_idempotent(self):
        sensor = FakeShellPart()
        monitor = FakeShellPart()
        lifecycle = DashboardShellLifecycle(sensor=sensor, monitor=monitor)

        lifecycle.shutdown()
        lifecycle.shutdown()

        self.assertEqual(sensor.shutdown_calls, 1)
        self.assertEqual(monitor.shutdown_calls, 1)


if __name__ == "__main__":
    unittest.main()
