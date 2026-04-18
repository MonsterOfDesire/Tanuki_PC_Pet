class DashboardShellLifecycle:
    def __init__(self, sensor, monitor):
        self.sensor = sensor
        self.monitor = monitor
        self._shutdown = False

    def shutdown(self):
        if self._shutdown:
            return
        self._shutdown = True
        if self.monitor is not None:
            self.monitor.shutdown()
        if self.sensor is not None:
            self.sensor.shutdown()


def shutdown_listener(listener):
    if listener is None:
        return
    try:
        listener.stop()
    finally:
        join = getattr(listener, "join", None)
        if join is None:
            return
        try:
            join(0.2)
        except TypeError:
            join()
