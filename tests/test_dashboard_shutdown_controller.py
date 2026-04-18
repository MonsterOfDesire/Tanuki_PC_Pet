import unittest

from tanuki_core.shutdown_controller import DashboardShutdownController


class FakeConfigStore:
    def __init__(self):
        self.save_calls = []

    def save_now(self, force=False):
        self.save_calls.append(force)


class ShutdownControllerTests(unittest.TestCase):
    def test_execute_forces_save_before_quit(self):
        events = []
        store = FakeConfigStore()

        controller = DashboardShutdownController(
            save_before_quit=lambda: store.save_now(force=True),
            quit_app=lambda: events.append("quit"),
        )

        controller.execute()

        self.assertEqual(store.save_calls, [True])
        self.assertEqual(events, ["quit"])

    def test_execute_quits_even_without_store(self):
        events = []
        controller = DashboardShutdownController(
            save_before_quit=lambda: None,
            quit_app=lambda: events.append("quit"),
        )

        controller.execute()

        self.assertEqual(events, ["quit"])


if __name__ == "__main__":
    unittest.main()
