import os
import sys
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication

from .asset_manager import AssetManager
from .config_save_scheduler import ConfigSaveScheduler
from .config_store import ConfigStore
from .dashboard_shell import GlobalMouseListener, SensorZone
from .dashboard_shell_lifecycle import DashboardShellLifecycle
from .dashboard_ui import Dashboard
from .geometry import DesktopGeometry
from .pet_widget import TanukiPet
from .runtime import SIM_CLOCK, app_now
from .settings_provider import RuntimeSettings
from .window_tracker import WindowTracker


@dataclass(frozen=True)
class PetSpec:
    folder_name: str
    scale: float
    display_name: str
    initially_visible: bool = True


@dataclass
class TanukiAppRuntime:
    app: QApplication
    settings_provider: RuntimeSettings
    config_store: ConfigStore
    save_scheduler: ConfigSaveScheduler
    window_tracker: WindowTracker
    pets_dict: dict
    pets_list: list
    dashboard: Dashboard
    sensor: SensorZone
    monitor: GlobalMouseListener
    shell: DashboardShellLifecycle | None = None
    timers: dict = field(default_factory=dict)

    def shutdown(self):
        for timer in self.timers.values():
            if timer.isActive():
                timer.stop()
        if self.shell is not None:
            self.shell.shutdown()


DEFAULT_PET_SPECS = (
    PetSpec("Symboli Rudolf", 0.45, "滷豆腐"),
    PetSpec("Tokai Teio", 0.35, "帝寶", initially_visible=False),
    PetSpec("Sirius Symboli", 0.4, "天狼星", initially_visible=False),
    PetSpec("Tsurumaru Tsuyoshi", 0.3, "鶴寶", initially_visible=False),
    PetSpec("Air Groove", 0.4, "氣槽", initially_visible=False),
)


def build_default_pet_specs():
    return DEFAULT_PET_SPECS


def create_pets(assets_dir, pet_specs, settings_provider, window_tracker):
    pets_dict, pets_list = {}, []
    for index, spec in enumerate(pet_specs):
        character_path = os.path.join(assets_dir, spec.folder_name)
        if not os.path.exists(character_path):
            continue

        pet = TanukiPet(
            spec.folder_name,
            character_path,
            spec.scale,
            settings_provider=settings_provider,
            window_tracker=window_tracker,
        )
        pet.move(500 + (index * 100), 600)
        if not spec.initially_visible:
            pet.user_visible = False
            pet.hide()

        pets_dict[spec.folder_name] = {"pet": pet, "name": spec.display_name}
        pets_list.append(pet)
    return pets_dict, pets_list


def build_dashboard(pets_dict, settings_provider, save_scheduler):
    left_screen = min(QApplication.screens(), key=lambda screen: screen.geometry().x())
    available_rect = left_screen.availableGeometry()
    dashboard = Dashboard(
        available_rect,
        pets_dict,
        AssetManager.get_resource_path,
        settings_provider=settings_provider,
        save_scheduler=save_scheduler,
    )
    return dashboard, available_rect


def register_runtime_timer(app, interval_ms, callback, speed_scaled=True, minimum_interval_ms=1):
    timer = QTimer(app)
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    repeat_count = 1

    def run_callback():
        nonlocal repeat_count
        if not speed_scaled:
            callback()
            return
        repeat_count = SIM_CLOCK.get_timer_repeat_count(interval_ms, minimum_interval_ms=minimum_interval_ms)
        for _ in range(repeat_count):
            callback()

    timer.timeout.connect(run_callback)
    timer.start(interval_ms)
    if speed_scaled:
        SIM_CLOCK.register_timer(timer, interval_ms, minimum_interval_ms=minimum_interval_ms)
    return timer


def start_runtime_timers(runtime):
    return {
        "mood": register_runtime_timer(
            runtime.app,
            3000,
            lambda: [pet.update_mood(runtime.pets_list) for pet in runtime.pets_list],
            speed_scaled=False,
        ),
        "physics": register_runtime_timer(
            runtime.app,
            30,
            lambda: [pet.resolve_collision(runtime.pets_list) for pet in runtime.pets_list],
            minimum_interval_ms=8,
        ),
        "logic": register_runtime_timer(
            runtime.app,
            30,
            lambda: [pet.tick(runtime.pets_list) for pet in runtime.pets_list],
            minimum_interval_ms=8,
        ),
        "windows": register_runtime_timer(
            runtime.app,
            150,
            runtime.window_tracker.refresh,
            speed_scaled=False,
        ),
    }


def ensure_visible_pets(pets_list):
    for pet in pets_list:
        if not getattr(pet, "user_visible", True):
            continue
        if pet.care_lock_mode == "hidden" and pet.is_under_care(app_now()):
            continue
        clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(pet, pet.x(), pet.y())
        if (clamped_x, clamped_y) != (pet.x(), pet.y()):
            pet.move(clamped_x, clamped_y)
        pet.show()
        pet.raise_()
        pet.update()


def create_runtime(app=None):
    app = app or QApplication(sys.argv)
    settings_provider = RuntimeSettings()
    config_store = ConfigStore(
        config_path=AssetManager.get_resource_path("config.json"),
        clamp_pet_position=DesktopGeometry.clamp_widget_position,
    )
    save_scheduler = ConfigSaveScheduler(lambda: config_store)
    window_tracker = WindowTracker()

    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir):
        raise FileNotFoundError(assets_dir)

    pets_dict, pets_list = create_pets(
        assets_dir,
        build_default_pet_specs(),
        settings_provider,
        window_tracker,
    )
    dashboard, available_rect = build_dashboard(pets_dict, settings_provider, save_scheduler)

    config_store.bind(dashboard, pets_dict)
    window_tracker.refresh()

    sensor = SensorZone(dashboard)
    sensor.setGeometry(available_rect.left(), available_rect.bottom() - 300, 20, 300)
    monitor = GlobalMouseListener(dashboard)

    runtime = TanukiAppRuntime(
        app=app,
        settings_provider=settings_provider,
        config_store=config_store,
        save_scheduler=save_scheduler,
        window_tracker=window_tracker,
        pets_dict=pets_dict,
        pets_list=pets_list,
        dashboard=dashboard,
        sensor=sensor,
        monitor=monitor,
        shell=DashboardShellLifecycle(sensor=sensor, monitor=monitor),
    )
    runtime.timers = start_runtime_timers(runtime)
    runtime.app.aboutToQuit.connect(runtime.shutdown)
    return runtime


def run_application():
    runtime = create_runtime()
    runtime.dashboard.show()
    runtime.sensor.show()
    QTimer.singleShot(0, lambda: ensure_visible_pets(runtime.pets_list))
    QTimer.singleShot(300, lambda: ensure_visible_pets(runtime.pets_list))
    return runtime.app.exec()
