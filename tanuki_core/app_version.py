from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
import re


APP_NAME = "Tanuki PC Pet"
APP_VERSION = "0.7.0-beta"
GITHUB_REPOSITORY = "MonsterOfDesire/Tanuki_PC_Pet"
GITHUB_RELEASES_URL = (
    f"https://github.com/{GITHUB_REPOSITORY}/releases"
)
GITHUB_RELEASES_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases"
)
UPDATE_MANIFEST_ASSET_NAME = "tanuki-update.json"


_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:[-.]?(?P<label>alpha|beta|rc)(?:[.-]?(?P<number>\d+))?)?$",
    re.IGNORECASE,
)
_PRERELEASE_ORDER = {"alpha": 0, "beta": 1, "rc": 2, "": 3}


@total_ordering
@dataclass(frozen=True)
class AppVersion:
    major: int
    minor: int
    patch: int
    prerelease_label: str = ""
    prerelease_number: int = 0

    @classmethod
    def parse(cls, value):
        match = _VERSION_PATTERN.fullmatch(str(value or "").strip())
        if not match:
            raise ValueError(f"invalid application version: {value!r}")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease_label=str(match.group("label") or "").lower(),
            prerelease_number=int(match.group("number") or 0),
        )

    @property
    def is_prerelease(self):
        return bool(self.prerelease_label)

    def _comparison_key(self):
        return (
            self.major,
            self.minor,
            self.patch,
            _PRERELEASE_ORDER[self.prerelease_label],
            self.prerelease_number,
        )

    def __lt__(self, other):
        if not isinstance(other, AppVersion):
            return NotImplemented
        return self._comparison_key() < other._comparison_key()

    def __str__(self):
        base = f"{self.major}.{self.minor}.{self.patch}"
        if not self.prerelease_label:
            return base
        suffix = self.prerelease_label
        if self.prerelease_number:
            suffix += f".{self.prerelease_number}"
        return f"{base}-{suffix}"


CURRENT_APP_VERSION = AppVersion.parse(APP_VERSION)
