from __future__ import annotations

from dataclasses import dataclass
import threading

from PyQt6.QtCore import QObject, pyqtSignal

from .app_version import APP_VERSION, GITHUB_RELEASES_URL
from .update_service import (
    GitHubReleaseClient,
    get_release_update_bundle_assets,
)
from .platform_capabilities import get_platform_capabilities


@dataclass(frozen=True)
class UpdateStatusSnapshot:
    state: str = "idle"
    current_version: str = APP_VERSION
    available_version: str = ""
    release_page_url: str = ""
    updater_download_url: str = ""
    error_message: str = ""
    update_bundle_available: bool = False
    update_method: str = "standalone_updater"


class UpdateCheckCoordinator(QObject):
    """Run the blocking stdlib release client away from Qt's UI thread."""

    status_changed = pyqtSignal(object)
    _worker_succeeded = pyqtSignal(object)
    _worker_failed = pyqtSignal(str)

    def __init__(
        self,
        client=None,
        parent=None,
        *,
        platform=None,
        capabilities=None,
    ):
        super().__init__(parent)
        self.client = client or GitHubReleaseClient()
        self.capabilities = (
            capabilities or get_platform_capabilities(platform)
        )
        self._status = UpdateStatusSnapshot(
            update_method=self.capabilities.update_method,
        )
        self._checking = False
        self._worker_succeeded.connect(self._handle_success)
        self._worker_failed.connect(self._handle_failure)

    def snapshot(self):
        return self._status

    def start_check(self):
        if self._checking:
            return False
        self._checking = True
        self._set_status(self._status_for(state="checking"))
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
            self._set_status(self._status_for(state="up_to_date"))
            return
        bundle_assets = get_release_update_bundle_assets(
            release,
            platform=self.capabilities.platform_key,
        )
        updater_asset = bundle_assets[0] if bundle_assets else None
        bundle_available = bundle_assets is not None
        self._set_status(
            self._status_for(
                state="available",
                available_version=str(release.version),
                release_page_url=(
                    release.page_url or GITHUB_RELEASES_URL
                ),
                updater_download_url=(
                    updater_asset.download_url
                    if bundle_available and updater_asset is not None
                    else ""
                ),
                update_bundle_available=bundle_available,
            )
        )

    def _handle_failure(self, error_message):
        self._checking = False
        self._set_status(
            self._status_for(
                state="failed",
                error_message=str(error_message or "unknown error"),
            )
        )

    def _set_status(self, status):
        self._status = status
        self.status_changed.emit(status)

    def _status_for(self, **values):
        return UpdateStatusSnapshot(
            update_method=self.capabilities.update_method,
            **values,
        )
