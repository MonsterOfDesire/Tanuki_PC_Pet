import unittest

from tanuki_core.windows_foreground_watcher import (
    EVENT_SYSTEM_FOREGROUND,
    WindowsForegroundWatcher,
)


class WindowsForegroundWatcherTests(unittest.TestCase):
    def test_non_windows_watcher_never_installs(self):
        watcher = WindowsForegroundWatcher(platform_key="macos")
        self.assertFalse(watcher.start(hook_installer=lambda _callback: 77))
        self.assertFalse(watcher.active)

    def test_windows_watcher_emits_and_unhooks_without_polling(self):
        callbacks = []
        watcher = WindowsForegroundWatcher(platform_key="windows")
        changed = []
        watcher.foreground_changed.connect(changed.append)

        self.assertTrue(
            watcher.start(
                hook_installer=lambda callback: callbacks.append(callback) or 77
            )
        )
        callbacks[0](None, EVENT_SYSTEM_FOREGROUND, 1234, 0, 0, 0, 0)
        self.assertEqual(changed, [1234])
        unhooked = []
        self.assertTrue(watcher.stop(unhook=lambda hook: unhooked.append(hook) or True))
        self.assertEqual(unhooked, [77])
        self.assertFalse(watcher.active)


if __name__ == "__main__":
    unittest.main()
