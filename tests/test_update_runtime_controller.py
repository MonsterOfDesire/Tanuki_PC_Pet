import unittest

from tanuki_core.app_version import AppVersion
from tanuki_core.update_runtime_controller import UpdateCheckCoordinator
from tanuki_core.update_service import (
    ReleaseInfo,
    UpdateCheckResult,
)


def build_release(*, include_package=True):
    assets = [
        {
            "name": "TanukiUpdater.exe",
            "browser_download_url": "https://example.test/TanukiUpdater.exe",
        },
        {
            "name": "tanuki-update.json",
            "browser_download_url": "https://example.test/manifest",
        },
    ]
    if include_package:
        assets.append(
            {
                "name": "TanukiPet-0.8.0-beta-windows-x64.zip",
                "browser_download_url": "https://example.test/package",
            }
        )
    return ReleaseInfo.from_github_payload(
        {
            "tag_name": "v0.8.0-beta",
            "name": "v0.8.0-beta",
            "html_url": "https://example.test/release",
            "body": "notes",
            "prerelease": True,
            "draft": False,
            "published_at": "2026-08-18T00:00:00Z",
            "assets": assets,
        }
    )


class UpdateRuntimeControllerTests(unittest.TestCase):
    def result(self, release):
        return UpdateCheckResult(
            current_version=AppVersion.parse("0.7.0-beta"),
            release=release,
            checked_release_count=1,
        )

    def test_complete_bundle_exposes_direct_updater_download(self):
        coordinator = UpdateCheckCoordinator()
        release = build_release()

        coordinator._handle_success(self.result(release))
        snapshot = coordinator.snapshot()

        self.assertEqual(snapshot.state, "available")
        self.assertTrue(snapshot.update_bundle_available)
        self.assertEqual(
            snapshot.updater_download_url,
            "https://example.test/TanukiUpdater.exe",
        )

    def test_incomplete_bundle_does_not_offer_download(self):
        coordinator = UpdateCheckCoordinator()
        release = build_release(include_package=False)

        coordinator._handle_success(self.result(release))
        snapshot = coordinator.snapshot()

        self.assertFalse(snapshot.update_bundle_available)
        self.assertEqual(snapshot.updater_download_url, "")


if __name__ == "__main__":
    unittest.main()
