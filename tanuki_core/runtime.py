import time


class SimulationClock:
    def __init__(self):
        self.speed = 1.0
        self.real_anchor = time.perf_counter()
        self.sim_anchor = time.time()
        self.timer_specs = []

    def now(self):
        elapsed = time.perf_counter() - self.real_anchor
        return self.sim_anchor + (elapsed * self.speed)

    def set_speed(self, speed):
        speed = max(1.0, float(speed))
        self.sim_anchor = self.now()
        self.real_anchor = time.perf_counter()
        self.speed = speed
        self.apply_registered_timers()

    def register_timer(self, timer, base_interval_ms):
        if timer is None:
            return
        base_interval_ms = max(1, int(base_interval_ms))
        self.timer_specs.append((timer, base_interval_ms))
        self.apply_timer_interval(timer, base_interval_ms)

    def apply_timer_interval(self, timer, base_interval_ms):
        interval = max(1, int(round(base_interval_ms / self.speed)))
        timer.setInterval(interval)

    def apply_registered_timers(self):
        active_specs = []
        for timer, base_interval_ms in self.timer_specs:
            try:
                self.apply_timer_interval(timer, base_interval_ms)
                active_specs.append((timer, base_interval_ms))
            except RuntimeError:
                continue
        self.timer_specs = active_specs


SIM_CLOCK = SimulationClock()


def app_now():
    return SIM_CLOCK.now()

