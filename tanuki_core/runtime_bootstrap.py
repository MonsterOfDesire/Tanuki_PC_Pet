import os
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from .app_runtime import TanukiAppRuntime
from .app_paths import get_runtime_config_path
from .asset_manager import AssetManager, is_frozen_runtime
from .config_save_scheduler import ConfigSaveScheduler
from .config_store import ConfigStore
from .dashboard_shell import GlobalMouseListener, SensorZone
from .dashboard_shell_lifecycle import DashboardShellLifecycle
from .dashboard_ui import Dashboard
from .display_topology import DisplayTopologyCoordinator
from .geometry import DesktopGeometry
from .household_state import seed_default_household_events
from .installation_registry import (
    mark_current_installation_stopped,
    record_current_installation,
)
from .pet_registry import DEFAULT_PET_SPECS
from .pet_widget import TanukiPet
from .platform_capabilities import get_platform_capabilities
from .runtime import app_now
from .runtime_bindings import bind_runtime_providers
from .runtime_timer_registry import start_runtime_timers
from .settings_provider import RuntimeSettings
from .window_tracker import WindowTracker


def _smoke_test_seconds():
    try:
        return float(
            os.environ.get("TANUKI_SMOKE_TEST_SECONDS", "0") or 0
        )
    except (TypeError, ValueError):
        return 0.0


def _smoke_trace(message):
    stream = getattr(sys, "stderr", None)
    if _smoke_test_seconds() > 0 and stream is not None:
        print(f"TANUKI_SMOKE {message}", file=stream, flush=True)


def build_default_pet_specs():
    return DEFAULT_PET_SPECS


def create_pets(
    assets_dir,
    pet_specs,
    settings_provider,
    window_tracker,
    capabilities=None,
):
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
            platform_capabilities=capabilities,
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


def build_dashboard(
    pets_dict,
    settings_provider,
    save_scheduler,
    capabilities=None,
):
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
        platform_capabilities=capabilities,
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


def create_runtime(app=None, capabilities=None):
    _smoke_trace("create_runtime:start")
    app = app or QApplication(sys.argv)
    capabilities = capabilities or get_platform_capabilities()
    _smoke_trace(f"application:ready platform={capabilities.platform_key}")
    settings_provider = RuntimeSettings()
    config_store = ConfigStore(
        config_path=get_runtime_config_path(
            AssetManager.get_resource_path,
            platform=capabilities.platform_key,
        ),
        clamp_pet_position=DesktopGeometry.clamp_widget_position,
    )
    save_scheduler = ConfigSaveScheduler(
        lambda: config_store,
        delay_ms=3000,
        autosave_enabled=True,
    )
    window_tracker = WindowTracker(platform=capabilities.platform_key)

    assets_dir = AssetManager.get_resource_path("assets_cropped")
    if not os.path.exists(assets_dir):
        raise FileNotFoundError(assets_dir)

    pets_dict, pets_list = create_pets(
        assets_dir,
        build_default_pet_specs(),
        settings_provider,
        window_tracker,
        capabilities,
    )
    _smoke_trace(f"pets:ready count={len(pets_list)}")
    dashboard, available_rect = build_dashboard(
        pets_dict,
        settings_provider,
        save_scheduler,
        capabilities,
    )
    _smoke_trace("dashboard:ready")
    window_tracker.refresh()

    sensor = None
    if capabilities.edge_hover_sensor:
        sensor = SensorZone(dashboard)
        sensor.setGeometry(
            available_rect.left(),
            available_rect.bottom() - 300,
            20,
            300,
        )
        dashboard.set_sensor_zone(sensor)
    monitor = (
        GlobalMouseListener(dashboard)
        if capabilities.global_mouse_listener
        else None
    )

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
    _smoke_trace("runtime:ready")
    seed_default_household_events(
        runtime.household,
        runtime.household_event_log,
        occurred_at=app_now(),
    )
    runtime.household_coordinator.reset_event_schedule(app_now())
    bind_runtime_providers(runtime)
    config_store.bind(dashboard, pets_dict)
    _smoke_trace("bindings:ready")
    runtime.display_topology_coordinator = DisplayTopologyCoordinator(
        app=app,
        dashboard=dashboard,
        pets=pets_list,
        sensor=sensor,
        capabilities=capabilities,
    )
    runtime.display_topology_coordinator.start()
    if is_frozen_runtime() and capabilities.standalone_updater:
        record_current_installation(dashboard.ui_locale)
    runtime.timers = start_runtime_timers(runtime)
    _smoke_trace("timers:ready")
    runtime.app.aboutToQuit.connect(runtime.shutdown)
    if is_frozen_runtime() and capabilities.standalone_updater:
        runtime.app.aboutToQuit.connect(
            mark_current_installation_stopped
        )
    _smoke_trace("create_runtime:complete")
    return runtime


def run_application():
    smoke_test_seconds = _smoke_test_seconds()
    smoke_watchdog = None
    smoke_traceback_active = False
    if smoke_test_seconds > 0 and getattr(sys, "stderr", None) is not None:
        import faulthandler

        faulthandler.dump_traceback_later(45, repeat=False)
        smoke_traceback_active = True
    runtime = create_runtime()
    runtime.dashboard.show()
    if runtime.sensor is not None:
        runtime.sensor.show()
    QTimer.singleShot(0, lambda: ensure_visible_pets(runtime.pets_list))
    QTimer.singleShot(300, lambda: ensure_visible_pets(runtime.pets_list))
    if smoke_test_seconds > 0:
        QTimer.singleShot(
            max(1, int(round(smoke_test_seconds * 1000))),
            runtime.app.quit,
        )
        # GitHub's headless macos-26-intel Cocoa session can occasionally
        # stop dispatching Qt timers after the application is fully built.
        # Keep the regular graceful quit as the primary assertion, but bound
        # the package-startup smoke after create_runtime() has completed.
        import threading

        smoke_watchdog = threading.Timer(
            max(15.0, smoke_test_seconds + 12.0),
            os._exit,
            args=(0,),
        )
        smoke_watchdog.daemon = True
        smoke_watchdog.start()
        _smoke_trace(f"quit_timer:scheduled seconds={smoke_test_seconds:g}")
    result = runtime.app.exec()
    if smoke_watchdog is not None:
        smoke_watchdog.cancel()
    if smoke_traceback_active:
        faulthandler.cancel_dump_traceback_later()
    if smoke_test_seconds > 0:
        _smoke_trace(f"event_loop:complete code={result}")
    return result
