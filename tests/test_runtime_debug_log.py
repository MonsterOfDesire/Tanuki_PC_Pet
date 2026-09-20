from pathlib import Path
import tempfile
import unittest

from tanuki_core.runtime_debug_log import (
    RUNTIME_DEBUG_LOG_NAME,
    RuntimeDebugLog,
)


class RuntimeDebugLogTests(unittest.TestCase):
    def test_records_scope_and_exception_without_raising(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            debug_log = RuntimeDebugLog(temporary_directory)
            try:
                try:
                    raise RuntimeError("camera unavailable")
                except RuntimeError as error:
                    debug_log.exception("manual_camera.capture", error)
            finally:
                debug_log.close()

            text = (
                Path(temporary_directory) / RUNTIME_DEBUG_LOG_NAME
            ).read_text(encoding="utf-8")
            self.assertIn("manual_camera.capture", text)
            self.assertIn("camera unavailable", text)

    def test_rotates_instead_of_growing_without_limit(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            debug_log = RuntimeDebugLog(
                temporary_directory,
                max_bytes=320,
                backup_count=2,
            )
            try:
                for index in range(40):
                    try:
                        raise ValueError(f"failure-{index}-" + ("x" * 80))
                    except ValueError as error:
                        debug_log.exception("rotation.test", error)
            finally:
                debug_log.close()

            paths = tuple(Path(temporary_directory).glob(
                f"{RUNTIME_DEBUG_LOG_NAME}*"
            ))
            self.assertGreater(len(paths), 1)
            self.assertLessEqual(len(paths), 3)


if __name__ == "__main__":
    unittest.main()
