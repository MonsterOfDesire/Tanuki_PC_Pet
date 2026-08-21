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
        )

    def open_information_center(self):
        self.dashboard.open_information_center()

    def open_offer_tray(self):
        self.dashboard.open_offer_tray()

    def open_status_settings(self):
        self.dashboard.open_information_center(
            page_id=PAGE_STATUS_SETTINGS,
        )

    def begin_shutdown(self):
        self.dashboard.begin_shutdown()
