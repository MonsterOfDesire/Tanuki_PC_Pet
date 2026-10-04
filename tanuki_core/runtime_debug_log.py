from __future__ import annotations

from logging import Formatter, Logger, WARNING
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading

from .app_paths import get_user_data_directory


RUNTIME_DEBUG_LOG_NAME = "tanuki-debug.log"
RUNTIME_DEBUG_LOG_MAX_BYTES = 512 * 1024
RUNTIME_DEBUG_LOG_BACKUP_COUNT = 3


class RuntimeDebugLog:
    def __init__(
        self,
        root=None,
        *,
        max_bytes=RUNTIME_DEBUG_LOG_MAX_BYTES,
        backup_count=RUNTIME_DEBUG_LOG_BACKUP_COUNT,
    ):
        self.path = Path(
            root if root is not None else get_user_data_directory()
        ) / RUNTIME_DEBUG_LOG_NAME
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._logger = Logger(
            f"tanuki.runtime.{id(self)}",
            level=WARNING,
        )
        self._logger.propagate = False
        self._handler = RotatingFileHandler(
            self.path,
            maxBytes=max(1, int(max_bytes)),
            backupCount=max(0, int(backup_count)),
            encoding="utf-8",
        )
        self._handler.setFormatter(Formatter(
            "%(asctime)s %(levelname)s %(message)s"
        ))
        self._logger.addHandler(self._handler)

    def exception(self, scope, error):
        self._logger.warning(
            "suppressed exception in %s: %s",
            str(scope or "runtime"),
            error,
            exc_info=(type(error), error, error.__traceback__),
        )

    def close(self):
        self._logger.removeHandler(self._handler)
        self._handler.close()


_runtime_log = None
_runtime_log_lock = threading.Lock()


def log_suppressed_exception(scope, error):
    """Best-effort diagnostics that must never replace the original fallback."""
    global _runtime_log
    try:
        if _runtime_log is None:
            with _runtime_log_lock:
                if _runtime_log is None:
                    _runtime_log = RuntimeDebugLog()
        _runtime_log.exception(scope, error)
    except Exception:
        # Logging is intentionally secondary to the runtime recovery path.
        return False
    return True
