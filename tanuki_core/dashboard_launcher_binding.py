from dataclasses import dataclass

from .information_center_spec import PAGE_STATUS_SETTINGS
from .ui_localization import translate_ui


@dataclass(frozen=True)
class DashboardLauncherSnapshot:
    world_mode_key: str
    world_mode_label: str
    time_scale_label: str
    care_enabled: bool
    care_label: str
    shutdown_text: str = "關閉系統"
    shutdown_enabled: bool = True
    status_text: str = ""
    show_status: bool = False
    information_center_open: bool = False
    offer_tray_open: bool = False
    manual_camera_available: bool = False
    manual_camera_active: bool = False
    manual_camera_reason: str = ""
    play_day_number: int | None = None
    play_started_on: str = ""


class DashboardLauncherBinding:
    """Narrow launcher adapter that reuses existing Dashboard entry points."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def snapshot(self):
        world_mode = str(getattr(self.dashboard, "world_mode", "") or "")
        time_scale = float(self.dashboard.get_time_scale())
        care_enabled = bool(
            getattr(self.dashboard, "care_feature_enabled", False)
        )
        play_day_number = self._normalize_play_day(
            getattr(self.dashboard, "launcher_play_day_number", None)
        )
        availability_provider = getattr(
            self.dashboard,
            "get_manual_camera_availability",
            None,
        )
        if callable(availability_provider):
            manual_camera_available, manual_camera_reason = (
                availability_provider()
            )
        else:
            manual_camera_available = callable(
                getattr(self.dashboard, "toggle_manual_camera", None)
            )
            manual_camera_reason = "" if manual_camera_available else "unavailable"
        return DashboardLauncherSnapshot(
            world_mode_key=world_mode,
            world_mode_label=translate_ui(
                f"launcher.world_{world_mode}",
                default=world_mode or "未設定",
            ),
            time_scale_label=f"{time_scale:g}x",
            care_enabled=care_enabled,
            care_label=translate_ui(
                "launcher.care_on" if care_enabled else "launcher.care_off",
                default="照護中" if care_enabled else "照護關閉",
            ),
            shutdown_text=(
                translate_ui("launcher.shutdown", default="關閉系統")
                if str(
                    getattr(
                        self.dashboard,
                        "launcher_shutdown_text",
                        "關閉系統",
                    )
                ) == "關閉系統"
                else str(self.dashboard.launcher_shutdown_text)
            ),
            shutdown_enabled=bool(
                getattr(
                    self.dashboard,
                    "launcher_shutdown_enabled",
                    True,
                )
            ),
            status_text=str(
                getattr(
                    self.dashboard,
                    "launcher_status_text",
                    "",
                )
            ),
            show_status=bool(
                getattr(
                    self.dashboard,
                    "launcher_show_status",
                    False,
                )
            ),
            information_center_open=self._window_is_visible(
                "information_center_window"
            ),
            offer_tray_open=self._window_is_visible("offer_tray_window"),
            manual_camera_available=bool(manual_camera_available),
            manual_camera_active=bool(
                getattr(self.dashboard, "manual_camera_active", False)
            ),
            manual_camera_reason=str(manual_camera_reason or ""),
            play_day_number=play_day_number,
            play_started_on=str(
                getattr(self.dashboard, "launcher_play_started_on", "") or ""
            ),
        )

    @staticmethod
    def _normalize_play_day(value):
        try:
            day_number = int(value)
        except (TypeError, ValueError):
            return None
        return day_number if day_number >= 1 else None

    def _window_is_visible(self, attribute_name):
        window = getattr(self.dashboard, attribute_name, None)
        is_visible = getattr(window, "isVisible", None)
        return bool(callable(is_visible) and is_visible())

    def open_information_center(self):
        if self._close_visible_window("information_center_window"):
            return
        self.dashboard.open_information_center()

    def open_offer_tray(self):
        if self._close_visible_window("offer_tray_window"):
            return
        self.dashboard.open_offer_tray()

    def toggle_manual_camera(self):
        toggler = getattr(self.dashboard, "toggle_manual_camera", None)
        if not callable(toggler):
            return False
        return toggler()

    def _close_visible_window(self, attribute_name):
        if not self._window_is_visible(attribute_name):
            return False
        window = getattr(self.dashboard, attribute_name, None)
        close = getattr(window, "close", None)
        if callable(close):
            close()
        refresh = getattr(self.dashboard, "refresh_launcher_panel", None)
        if callable(refresh):
            refresh()
        return True

    def open_status_settings(self):
        self.dashboard.open_information_center(
            page_id=PAGE_STATUS_SETTINGS,
        )

    def begin_shutdown(self):
        self.dashboard.begin_shutdown()
