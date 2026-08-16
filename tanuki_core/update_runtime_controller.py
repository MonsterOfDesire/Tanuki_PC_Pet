from __future__ import annotations

from dataclasses import dataclass
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from .app_version import APP_VERSION, GITHUB_RELEASES_URL
from .update_service import GitHubReleaseClient


@dataclass(frozen=True)
class UpdateStatusSnapshot:
    state: str = "idle"
    current_version: str = APP_VERSION
    available_version: str = ""
    release_page_url: str = ""
    error_message: str = ""
    package_manifest_available: bool = False


class UpdateCheckCoordinator(QObject):
    """Run the blocking stdlib release client away from Qt's UI thread."""

    status_changed = pyqtSignal(object)
    _worker_succeeded = pyqtSignal(object)
    _worker_failed = pyqtSignal(str)

    def __init__(self, client=None, parent=None):
        super().__init__(parent)
        self.client = client or GitHubReleaseClient()
        self._status = UpdateStatusSnapshot()
        self._checking = False
        self._worker_succeeded.connect(self._handle_success)
        self._worker_failed.connect(self._handle_failure)

    def snapshot(self):
        return self._status

    def start_check(self):
        if self._checking:
            return False
        self._checking = True
        self._set_status(UpdateStatusSnapshot(state="checking"))
        worker = threading.Thread(
            target=self._run_check,
            name="tanuki-update-check",
            daemon=True,
        )
        worker.start()
        return True

    def _run_check(self):
        try:
            result = self.client.check_for_updates()
        except Exception as exc:
            self._worker_failed.emit(str(exc) or exc.__class__.__name__)
            return
        self._worker_succeeded.emit(result)

    def _handle_success(self, result):
        self._checking = False
        release = result.release
        if not result.update_available or release is None:
            self._set_status(UpdateStatusSnapshot(state="up_to_date"))
            return
        self._set_status(
            UpdateStatusSnapshot(
                state="available",
                available_version=str(release.version),
                release_page_url=(
                    release.page_url or GITHUB_RELEASES_URL
                ),
                package_manifest_available=(
                    release.find_asset("tanuki-update.json") is not None
                ),
            )
        )

    def _handle_failure(self, error_message):
        self._checking = False
        self._set_status(
            UpdateStatusSnapshot(
                state="failed",
                error_message=str(error_message or "unknown error"),
            )
        )

    def _set_status(self, status):
        self._status = status
        self.status_changed.emit(status)
