from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardStatusPresentation:
    status_text: str
    show_status: bool
    exit_enabled: bool
    exit_text: str
    force_expanded: bool


@dataclass(frozen=True)
class DashboardDialogPresentation:
    title: str
    message: str
    severity: str


@dataclass(frozen=True)
class DashboardButtonPresentation:
    text: str


class DashboardPresenter:
    def build_shutdown_status(self):
        return DashboardStatusPresentation(
            status_text="正在儲存設定...",
            show_status=True,
            exit_enabled=False,
            exit_text="正在關閉...",
            force_expanded=True,
        )

    def build_debug_button(self, enabled):
        return DashboardButtonPresentation(text=f"Debug: {'開啟' if enabled else '關閉'}")

    def build_validation_dialog(self, result):
        title = "檢查結果（有警告）" if result.has_warnings else "檢查結果（正常）"
        return DashboardDialogPresentation(
            title=title,
            message=result.report,
            severity="warning" if result.has_warnings else "information",
        )
