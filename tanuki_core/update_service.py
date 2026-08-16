from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.request import Request, urlopen

from .app_version import (
    APP_NAME,
    APP_VERSION,
    CURRENT_APP_VERSION,
    GITHUB_RELEASES_API_URL,
    UPDATE_MANIFEST_ASSET_NAME,
    AppVersion,
)
from .update_package import UpdatePackageManifest


GITHUB_API_VERSION = "2022-11-28"


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int
    digest: str = ""

    @classmethod
    def from_github_payload(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("release asset must be an object")
        return cls(
            name=str(payload.get("name") or ""),
            download_url=str(payload.get("browser_download_url") or ""),
            size=max(0, int(payload.get("size") or 0)),
            digest=str(payload.get("digest") or ""),
        )


@dataclass(frozen=True)
class ReleaseInfo:
    version: AppVersion
    tag_name: str
    title: str
    page_url: str
    body: str
    prerelease: bool
    published_at: str
    assets: tuple[ReleaseAsset, ...]

    @classmethod
    def from_github_payload(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("release payload must be an object")
        if bool(payload.get("draft", False)):
            raise ValueError("draft releases are not update candidates")
        tag_name = str(payload.get("tag_name") or "")
        return cls(
            version=AppVersion.parse(tag_name),
            tag_name=tag_name,
            title=str(payload.get("name") or tag_name),
            page_url=str(payload.get("html_url") or ""),
            body=str(payload.get("body") or ""),
            prerelease=bool(payload.get("prerelease", False)),
            published_at=str(payload.get("published_at") or ""),
            assets=tuple(
                ReleaseAsset.from_github_payload(asset)
                for asset in payload.get("assets", ())
                if isinstance(asset, dict)
            ),
        )

    def find_asset(self, name):
        expected = str(name or "")
        return next(
            (asset for asset in self.assets if asset.name == expected),
            None,
        )


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: AppVersion
    release: ReleaseInfo | None
    checked_release_count: int

    @property
    def update_available(self):
        return bool(
            self.release is not None
            and self.release.version > self.current_version
        )


def select_newest_release(
    releases,
    *,
    current_version=CURRENT_APP_VERSION,
    include_prereleases=None,
):
    current_version = (
        current_version
        if isinstance(current_version, AppVersion)
        else AppVersion.parse(current_version)
    )
    if include_prereleases is None:
        include_prereleases = current_version.is_prerelease
    candidates = []
    for release in releases:
        try:
            candidate = (
                release
                if isinstance(release, ReleaseInfo)
                else ReleaseInfo.from_github_payload(release)
            )
        except (TypeError, ValueError):
            continue
        if candidate.prerelease and not include_prereleases:
            continue
        candidates.append(candidate)
    return max(candidates, key=lambda release: release.version, default=None)


class GitHubReleaseClient:
    """Small stdlib client so update checks stay outside Qt and the UI thread."""

    def __init__(
        self,
        releases_url=GITHUB_RELEASES_API_URL,
        opener=urlopen,
        timeout_seconds=8.0,
    ):
        self.releases_url = str(releases_url)
        self.opener = opener
        self.timeout_seconds = float(timeout_seconds)

    @staticmethod
    def _headers(accept="application/vnd.github+json"):
        return {
            "Accept": accept,
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
        }

    def fetch_releases(self, limit=20):
        separator = "&" if "?" in self.releases_url else "?"
        url = f"{self.releases_url}{separator}per_page={max(1, int(limit))}"
        request = Request(url, headers=self._headers())
        with self.opener(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("GitHub releases response must be an array")
        return tuple(payload)

    def check_for_updates(
        self,
        *,
        current_version=CURRENT_APP_VERSION,
        include_prereleases=None,
    ):
        payloads = self.fetch_releases()
        release = select_newest_release(
            payloads,
            current_version=current_version,
            include_prereleases=include_prereleases,
        )
        current = (
            current_version
            if isinstance(current_version, AppVersion)
            else AppVersion.parse(current_version)
        )
        return UpdateCheckResult(
            current_version=current,
            release=release,
            checked_release_count=len(payloads),
        )

    def fetch_update_manifest(self, release):
        asset = release.find_asset(UPDATE_MANIFEST_ASSET_NAME)
        if asset is None or not asset.download_url:
            raise ValueError(
                f"release {release.tag_name} has no {UPDATE_MANIFEST_ASSET_NAME}"
            )
        request = Request(asset.download_url, headers=self._headers())
        with self.opener(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        manifest = UpdatePackageManifest.from_payload(payload)
        if manifest.version != release.version:
            raise ValueError(
                "update manifest version does not match release tag"
            )
        return manifest
