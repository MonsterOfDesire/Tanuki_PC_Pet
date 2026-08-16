import io
import json
import unittest

from tanuki_core.app_version import AppVersion
from tanuki_core.update_service import (
    GitHubReleaseClient,
    ReleaseInfo,
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


if __name__ == "__main__":
    unittest.main()
