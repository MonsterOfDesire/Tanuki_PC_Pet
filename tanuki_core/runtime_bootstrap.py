import os
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .app_runtime import TanukiAppRuntime
from .asset_manager import AssetManager, is_frozen_runtime
from .config_save_scheduler import ConfigSaveScheduler
from .config_store import ConfigStore
from .dashboard_shell import GlobalMouseListener, SensorZone
from .dashboard_shell_lifecycle import DashboardShellLifecycle
from .dashboard_ui import Dashboard
from .geometry import DesktopGeometry
from .household_state import seed_default_household_events
from .installation_registry import (
    mark_current_installation_stopped,
    record_current_installation,
)
from .pet_registry import DEFAULT_PET_SPECS
from .pet_widget import TanukiPet
from .runtime import app_now
from .runtime_bindings import bind_runtime_providers
from .runtime_timer_registry import start_runtime_timers
from .settings_provider import RuntimeSettings
from .window_tracker import WindowTracker


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

        pets_dict[spec.folder_name] = {
            "pet": pet,
            "name": spec.display_name,
        }
        pets_list.append(pet)
    return pets_dict, pets_list


def build_dashboard(pets_dict, settings_provider, save_scheduler):
    left_screen = min(
        QApplication.screens(),
        key=lambda screen: screen.geometry().x(),
    )
    available_rect = left_screen.availableGeometry()
    dashboard = Dashboard(
        available_rect,
        pets_dict,
        AssetManager.get_resource_path,
        settings_provider=settings_provider,
        save_scheduler=save_scheduler,
    )
    return dashboard, available_rect


def ensure_visible_pets(pets_list):
    for pet in pets_list:
        if not getattr(pet, "user_visible", True):
            continue
        if pet.care_lock_mode == "hidden" and pet.is_under_care(app_now()):
            continue
        clamped_x, clamped_y = DesktopGeometry.clamp_widget_position(
            pet,
            pet.x(),
            pet.y(),
        )
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
    dashboard, available_rect = build_dashboard(
        pets_dict,
        settings_provider,
        save_scheduler,
    )
    window_tracker.refresh()

    sensor = SensorZone(dashboard)
    sensor.setGeometry(
        available_rect.left(),
        available_rect.bottom() - 300,
        20,
        300,
    )
    dashboard.set_sensor_zone(sensor)
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
    seed_default_household_events(
        runtime.household,
        runtime.household_event_log,
        occurred_at=app_now(),
    )
    runtime.household_coordinator.reset_event_schedule(app_now())
    bind_runtime_providers(runtime)
    config_store.bind(dashboard, pets_dict)
    if is_frozen_runtime():
        record_current_installation(dashboard.ui_locale)
    runtime.timers = start_runtime_timers(runtime)
    runtime.app.aboutToQuit.connect(runtime.shutdown)
    if is_frozen_runtime():
        runtime.app.aboutToQuit.connect(
            mark_current_installation_stopped
        )
    return runtime


def run_application():
    runtime = create_runtime()
    runtime.dashboard.show()
    runtime.sensor.show()
    QTimer.singleShot(0, lambda: ensure_visible_pets(runtime.pets_list))
    QTimer.singleShot(300, lambda: ensure_visible_pets(runtime.pets_list))
    return runtime.app.exec()
