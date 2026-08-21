import io
import json
import unittest

from tanuki_core.app_version import AppVersion
from tanuki_core.update_service import (
    GitHubReleaseClient,
    ReleaseInfo,
    get_release_update_bundle_assets,
    select_newest_release,
)


def release_payload(tag, *, prerelease=False, draft=False, assets=()):
    return {
        "tag_name": tag,
        "name": tag,
        "html_url": f"https://example.test/{tag}",
        "body": "notes",
        "prerelease": prerelease,
        "draft": draft,
        "published_at": "2026-08-16T00:00:00Z",
        "assets": list(assets),
    }


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class UpdateServiceTests(unittest.TestCase):
    def test_stable_channel_ignores_prereleases(self):
        selected = select_newest_release(
            (
                release_payload("v0.8.0"),
                release_payload("v0.9.0-beta", prerelease=True),
            ),
            current_version="0.7.0",
        )
        self.assertEqual(str(selected.version), "0.8.0")

    def test_beta_channel_includes_prereleases(self):
        selected = select_newest_release(
            (
                release_payload("v0.8.0"),
                release_payload("v0.9.0-beta", prerelease=True),
            ),
            current_version="0.7.0-beta",
        )
        self.assertEqual(str(selected.version), "0.9.0-beta")

    def test_invalid_and_draft_releases_are_skipped(self):
        selected = select_newest_release(
            (
                release_payload("latest"),
                release_payload("v9.0.0", draft=True),
                release_payload("v0.8.0"),
            ),
            current_version="0.7.0",
        )
        self.assertEqual(str(selected.version), "0.8.0")

    def test_client_builds_update_result_without_network(self):
        payload = json.dumps(
            [release_payload("v0.8.0-beta", prerelease=True)]
        ).encode("utf-8")
        calls = []

        def opener(request, timeout):
            calls.append((request.full_url, timeout, dict(request.headers)))
            return FakeResponse(payload)

        client = GitHubReleaseClient(
            releases_url="https://api.example.test/releases",
            opener=opener,
            timeout_seconds=3,
        )
        result = client.check_for_updates(current_version="0.7.0-beta")

        self.assertTrue(result.update_available)
        self.assertEqual(result.checked_release_count, 1)
        self.assertIn("per_page=20", calls[0][0])

    def test_release_finds_named_manifest_asset(self):
        release = ReleaseInfo.from_github_payload(
            release_payload(
                "v0.8.0",
                assets=(
                    {
                        "name": "tanuki-update.json",
                        "browser_download_url": "https://example.test/manifest",
                        "size": 200,
                        "digest": "sha256:abc",
                    },
                ),
            )
        )
        self.assertEqual(
            release.find_asset("tanuki-update.json").size,
            200,
        )

    def test_manifest_package_must_match_asset_on_same_release(self):
        package_name = "TanukiPet-0.8.0-beta-windows-x64.zip"
        manifest_payload = {
            "schema_version": 1,
            "version": "0.8.0-beta",
            "executable_name": "TanukiPet.exe",
            "package": {
                "name": package_name,
                "url": "https://example.test/package",
                "sha256": "a" * 64,
                "size": 123,
            },
        }
        release = ReleaseInfo.from_github_payload(
            release_payload(
                "v0.8.0-beta",
                prerelease=True,
                assets=(
                    {
                        "name": "tanuki-update.json",
                        "browser_download_url": "https://example.test/manifest",
                    },
                    {
                        "name": package_name,
                        "browser_download_url": "https://example.test/package",
                        "size": 123,
                    },
                ),
            )
        )
        responses = iter(
            (
                FakeResponse(json.dumps(manifest_payload).encode("utf-8")),
            )
        )
        client = GitHubReleaseClient(
            opener=lambda *_args, **_kwargs: next(responses)
        )

        manifest = client.fetch_update_manifest(release)

        self.assertEqual(manifest.package_name, package_name)
        mismatched = dict(manifest_payload)
        mismatched["package"] = dict(manifest_payload["package"])
        mismatched["package"]["url"] = "https://example.test/other"
        client = GitHubReleaseClient(
            opener=lambda *_args, **_kwargs: FakeResponse(
                json.dumps(mismatched).encode("utf-8")
            )
        )
        with self.assertRaisesRegex(ValueError, "URL does not match"):
            client.fetch_update_manifest(release)

    def test_update_bundle_requires_updater_manifest_and_matching_zip(self):
        release = ReleaseInfo.from_github_payload(
            release_payload(
                "v0.8.0-beta",
                prerelease=True,
                assets=(
                    {
                        "name": "TanukiUpdater.exe",
                        "browser_download_url": "https://example.test/updater",
                    },
                    {
                        "name": "tanuki-update.json",
                        "browser_download_url": "https://example.test/manifest",
                    },
                    {
                        "name": "TanukiPet-0.8.0-beta-windows-x64.zip",
                        "browser_download_url": "https://example.test/package",
                    },
                ),
            )
        )

        assets = get_release_update_bundle_assets(release)

        self.assertIsNotNone(assets)
        self.assertEqual(assets[0].name, "TanukiUpdater.exe")
        incomplete = ReleaseInfo.from_github_payload(
            release_payload(
                "v0.8.0-beta",
                prerelease=True,
                assets=(
                    {
                        "name": "TanukiUpdater.exe",
                        "browser_download_url": "https://example.test/updater",
                    },
                    {
                        "name": "tanuki-update.json",
                        "browser_download_url": "https://example.test/manifest",
                    },
                ),
            )
        )
        self.assertIsNone(get_release_update_bundle_assets(incomplete))


if __name__ == "__main__":
    unittest.main()
