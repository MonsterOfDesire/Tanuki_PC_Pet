from dataclasses import dataclass, field
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

    def register_timer(self, timer, base_interval_ms, minimum_interval_ms=1):
        if timer is None:
            return
        base_interval_ms = max(1, int(base_interval_ms))
        minimum_interval_ms = max(1, int(minimum_interval_ms))
        self.timer_specs.append((timer, base_interval_ms, minimum_interval_ms))
        self.apply_timer_interval(timer, base_interval_ms, minimum_interval_ms)

    def get_timer_interval(self, base_interval_ms, minimum_interval_ms=1):
        base_interval_ms = max(1, int(base_interval_ms))
        minimum_interval_ms = max(1, int(minimum_interval_ms))
        return max(minimum_interval_ms, int(round(base_interval_ms / self.speed)))

    def get_timer_repeat_count(self, base_interval_ms, minimum_interval_ms=1):
        interval = self.get_timer_interval(base_interval_ms, minimum_interval_ms=minimum_interval_ms)
        return max(1, int(round((self.speed * interval) / max(1, int(base_interval_ms)))))

    def get_timer_step_delta(self, base_interval_ms, actual_interval_ms=None):
        interval = (
            max(1, int(actual_interval_ms))
            if actual_interval_ms is not None
            else self.get_timer_interval(base_interval_ms)
        )
        return (self.speed * interval) / max(1, int(base_interval_ms))

    def apply_timer_interval(self, timer, base_interval_ms, minimum_interval_ms=1):
        interval = self.get_timer_interval(base_interval_ms, minimum_interval_ms=minimum_interval_ms)
        timer.setInterval(interval)

    def apply_registered_timers(self):
        active_specs = []
        for timer, base_interval_ms, minimum_interval_ms in self.timer_specs:
            try:
                self.apply_timer_interval(timer, base_interval_ms, minimum_interval_ms=minimum_interval_ms)
                active_specs.append((timer, base_interval_ms, minimum_interval_ms))
            except RuntimeError:
                continue
        self.timer_specs = active_specs


SIM_CLOCK = SimulationClock()


def resolve_timer_repeat_count(default_repeat_count, repeat_count_provider=None):
    repeat_count = max(1, int(default_repeat_count))
    if callable(repeat_count_provider):
        repeat_count = max(1, int(repeat_count_provider(repeat_count)))
    return repeat_count


def get_timer_callback_step_delta(clock, base_interval_ms, effective_interval_ms, repeat_count=1):
    event_step_delta = clock.get_timer_step_delta(
        base_interval_ms,
        actual_interval_ms=effective_interval_ms,
    )
    return float(event_step_delta) / max(1, int(repeat_count))


def get_enabled_simulation_pets(pets):
    return tuple(
        pet
        for pet in tuple(pets or ())
        if bool(getattr(pet, "user_visible", True))
    )


def get_pet_logic_step_scale(pet):
    return max(1e-6, float(getattr(pet, "logic_step_scale", 1.0) or 1.0))


def get_pet_logic_step_count(pet):
    return max(1, int(round(get_pet_logic_step_scale(pet))))


def run_pet_logic_step(pets):
    active_pets = get_enabled_simulation_pets(pets)
    for pet in active_pets:
        pet.tick(active_pets)
    return len(active_pets)


def run_pet_physics_step(pets):
    active_pets = get_enabled_simulation_pets(pets)
    for pet in active_pets:
        pet.resolve_collision(active_pets)
    return len(active_pets)


@dataclass
class AdaptivePetLogicScheduler:
    high_load_min_speed: float = 8.0
    high_load_pet_threshold: int = 3
    max_pending_step_scale: float = 8.0
    batch_phase: int = 0
    pending_step_scale_by_pet_id: dict[int, float] = field(default_factory=dict)

    def is_high_load(self, pets, speed):
        return (
            float(speed) >= float(self.high_load_min_speed) and
            len(get_enabled_simulation_pets(pets)) >= int(self.high_load_pet_threshold)
        )

    def resolve_repeat_count(self, pets, default_repeat_count, speed):
        if self.is_high_load(pets, speed):
            return 1
        return max(1, int(default_repeat_count))

    def run(self, pets, speed, step_delta=1.0):
        active_pets = get_enabled_simulation_pets(pets)
        if not active_pets:
            self.batch_phase = 0
            self.pending_step_scale_by_pet_id.clear()
            return 0
        event_step_delta = max(1e-6, float(step_delta or 0.0))
        high_load = self.is_high_load(active_pets, speed)
        if not high_load and abs(event_step_delta - 1.0) <= 1e-6:
            self.batch_phase = 0
            self.pending_step_scale_by_pet_id.clear()
            for pet in active_pets:
                pet.tick(active_pets)
            return len(active_pets)
        active_pet_ids = {id(pet) for pet in active_pets}
        for pet_id in tuple(self.pending_step_scale_by_pet_id):
            if pet_id not in active_pet_ids:
                del self.pending_step_scale_by_pet_id[pet_id]
        for pet in active_pets:
            pet_id = id(pet)
            pending = self.pending_step_scale_by_pet_id.get(pet_id, 0.0)
            self.pending_step_scale_by_pet_id[pet_id] = min(
                float(self.max_pending_step_scale),
                pending + event_step_delta,
            )
        if not high_load:
            self.batch_phase = 0
            scheduled_pets = active_pets
        else:
            phase = int(self.batch_phase) % 2
            scheduled_pets = active_pets[phase::2]
            self.batch_phase = 1 - phase
        for pet in scheduled_pets:
            pet_step_scale = self.pending_step_scale_by_pet_id.pop(id(pet), event_step_delta)
            had_step_scale = hasattr(pet, "logic_step_scale")
            previous_step_scale = getattr(pet, "logic_step_scale", 1.0)
            pet.logic_step_scale = float(pet_step_scale)
            try:
                pet.tick(active_pets)
            finally:
                if had_step_scale:
                    pet.logic_step_scale = previous_step_scale
                elif hasattr(pet, "logic_step_scale"):
                    delattr(pet, "logic_step_scale")
        return len(scheduled_pets)


@dataclass
class RuntimeProfileMetric:
    sample_count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0
    last_interval_ms: float = 0.0
    last_repeat_count: int = 1
    window_started_at: float = 0.0
    window_events: int = 0
    window_repeats: int = 0
    events_per_second: float = 0.0
    repeats_per_second: float = 0.0

    @property
    def average_ms(self):
        if self.sample_count <= 0:
            return 0.0
        return self.total_ms / float(self.sample_count)

    @property
    def average_repeat_count(self):
        if self.events_per_second <= 0.0:
            return float(self.last_repeat_count or 1)
        return self.repeats_per_second / max(self.events_per_second, 1e-6)

    def record(self, *, duration_ms, now, repeat_count=1, interval_ms=0.0):
        self.sample_count += 1
        self.total_ms += float(duration_ms)
        self.max_ms = max(self.max_ms, float(duration_ms))
        self.last_ms = float(duration_ms)
        self.last_interval_ms = float(interval_ms)
        self.last_repeat_count = max(1, int(repeat_count))
        if self.window_started_at <= 0.0:
            self.window_started_at = float(now)
        self.window_events += 1
        self.window_repeats += max(1, int(repeat_count))
        elapsed = max(0.0, float(now) - float(self.window_started_at))
        if elapsed >= 1.0:
            self.events_per_second = float(self.window_events) / elapsed
            self.repeats_per_second = float(self.window_repeats) / elapsed
            self.window_started_at = float(now)
            self.window_events = 0
            self.window_repeats = 0


@dataclass
class RuntimeProfiler:
    timer_metrics: dict[str, RuntimeProfileMetric] = field(default_factory=dict)
    section_metrics: dict[str, RuntimeProfileMetric] = field(default_factory=dict)

    def _get_metric(self, bucket, name):
        metric = bucket.get(name)
        if metric is None:
            metric = RuntimeProfileMetric()
            bucket[name] = metric
        return metric

    def record_timer(self, name, *, duration_ms, now=None, repeat_count=1, interval_ms=0.0):
        now = time.perf_counter() if now is None else float(now)
        metric = self._get_metric(self.timer_metrics, str(name))
        metric.record(
            duration_ms=float(duration_ms),
            now=now,
            repeat_count=int(repeat_count),
            interval_ms=float(interval_ms),
        )

    def record_section(self, name, duration_ms, now=None):
        now = time.perf_counter() if now is None else float(now)
        metric = self._get_metric(self.section_metrics, str(name))
        metric.record(duration_ms=float(duration_ms), now=now, repeat_count=1, interval_ms=0.0)

    def build_debug_lines(self, speed=1.0):
        lines = [f"perf speed={float(speed):g}x"]
        timer_order = ("logic", "physics", "offer", "household")
        timer_chunks = []
        for name in timer_order:
            metric = self.timer_metrics.get(name)
            if metric is None or metric.sample_count <= 0:
                continue
            timer_chunks.append(
                f"{name}:{metric.events_per_second:.0f}/s x{metric.average_repeat_count:.1f} {metric.average_ms:.2f}ms"
            )
        if timer_chunks:
            lines.append(" ".join(timer_chunks))
        section_order = ("pet.tick", "pet.layers", "pet.ai", "offer.update", "household.update")
        section_chunks = []
        for name in section_order:
            metric = self.section_metrics.get(name)
            if metric is None or metric.sample_count <= 0:
                continue
            short_name = name.replace("pet.", "").replace(".update", "")
            section_chunks.append(f"{short_name}:{metric.average_ms:.2f}ms")
        if section_chunks:
            lines.append(" ".join(section_chunks))
        return lines


def app_now():
    return SIM_CLOCK.now()
