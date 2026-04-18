try:
    from PyQt6.QtCore import QObject, QTimer
except ModuleNotFoundError:
    class _FallbackSignal:
        def __init__(self):
            self._callback = None

        def connect(self, callback):
            self._callback = callback

        def emit(self):
            if self._callback:
                self._callback()

    class QObject:
        def __init__(self, *args, **kwargs):
            pass

    class QTimer:
        def __init__(self, parent=None):
            self._active = False
            self._interval = 0
            self._single_shot = False
            self.timeout = _FallbackSignal()

        def setSingleShot(self, enabled):
            self._single_shot = bool(enabled)

        def start(self, interval):
            self._interval = interval
            self._active = True

        def stop(self):
            self._active = False

        def isActive(self):
            return self._active

        def interval(self):
            return self._interval


class ConfigSaveScheduler(QObject):
    def __init__(self, config_store_provider, delay_ms=750, autosave_enabled=False):
        super().__init__()
        self.config_store_provider = config_store_provider
        self.delay_ms = int(delay_ms)
        self.autosave_enabled = bool(autosave_enabled)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_pending)

    def _get_config_store(self):
        return self.config_store_provider() if self.config_store_provider else None

    def schedule(self):
        if not self.autosave_enabled:
            return
        config_store = self._get_config_store()
        if not config_store:
            return
        self.save_timer.start(self.delay_ms)

    def save_now(self, force=False):
        if self.save_timer.isActive():
            self.save_timer.stop()
        config_store = self._get_config_store()
        if config_store:
            config_store.save_now(force=force)

    def _save_pending(self):
        self.save_now(force=False)
