from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from urllib.request import Request, urlopen
import zipfile

from .app_version import AppVersion


UPDATE_PACKAGE_SCHEMA_VERSION = 1
DEFAULT_EXECUTABLE_NAME = "TanukiPet.exe"
UPDATE_PACKAGE_PLATFORM_SUFFIX = "windows-x64.zip"


def get_update_package_asset_name(version):
    return (
        f"TanukiPet-{AppVersion.parse(version)}-"
        f"{UPDATE_PACKAGE_PLATFORM_SUFFIX}"
    )


@dataclass(frozen=True)
class UpdatePackageManifest:
    version: AppVersion
    package_name: str
    package_url: str
    sha256: str
    size: int
    executable_name: str = DEFAULT_EXECUTABLE_NAME
    schema_version: int = UPDATE_PACKAGE_SCHEMA_VERSION

    @classmethod
    def from_payload(cls, payload):
        if not isinstance(payload, dict):
            raise ValueError("update manifest root must be an object")
        schema_version = int(payload.get("schema_version") or 0)
        if schema_version != UPDATE_PACKAGE_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported update manifest schema: {schema_version}"
            )
        package = payload.get("package")
        if not isinstance(package, dict):
            raise ValueError("update manifest package must be an object")
        sha256 = str(package.get("sha256") or "").lower()
        if len(sha256) != 64 or any(
            character not in "0123456789abcdef" for character in sha256
        ):
            raise ValueError("update package sha256 is invalid")
        package_name = str(package.get("name") or "")
        package_url = str(package.get("url") or "")
        if not package_name.endswith(".zip"):
            raise ValueError("update package must be a zip archive")
        if not package_url.startswith("https://"):
            raise ValueError("update package URL must use HTTPS")
        return cls(
            version=AppVersion.parse(payload.get("version")),
            package_name=package_name,
            package_url=package_url,
            sha256=sha256,
            size=max(1, int(package.get("size") or 0)),
            executable_name=str(
                payload.get("executable_name") or DEFAULT_EXECUTABLE_NAME
            ),
            schema_version=schema_version,
        )

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as stream:
            return cls.from_payload(json.load(stream))

    def to_payload(self):
        return {
            "schema_version": self.schema_version,
            "version": str(self.version),
            "executable_name": self.executable_name,
            "package": {
                "name": self.package_name,
                "url": self.package_url,
                "sha256": self.sha256,
                "size": self.size,
            },
        }


def calculate_sha256(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_update_package(path, manifest):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"update package does not exist: {path}")
    if path.stat().st_size != manifest.size:
        raise ValueError("update package size does not match manifest")
    digest = calculate_sha256(path)
    if digest.lower() != manifest.sha256.lower():
        raise ValueError("update package sha256 does not match manifest")
    return True


def download_update_package(
    manifest,
    destination_dir,
    *,
    opener=urlopen,
    timeout_seconds=30.0,
    progress_callback=None,
):
    destination_dir = Path(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    partial_path = destination_dir / f"{manifest.package_name}.partial"
    final_path = destination_dir / manifest.package_name
    request = Request(
        manifest.package_url,
        headers={"User-Agent": "Tanuki-PC-Pet-Updater"},
    )
    try:
        with opener(request, timeout=float(timeout_seconds)) as response:
            with open(partial_path, "wb") as output:
                downloaded = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    if callable(progress_callback):
                        progress_callback(downloaded, manifest.size)
        verify_update_package(partial_path, manifest)
        os.replace(partial_path, final_path)
    finally:
        if partial_path.exists():
            partial_path.unlink()
    return final_path


def _validated_archive_member(member):
    normalized = str(member.filename or "").replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe update archive path: {member.filename!r}")
    if path.parts and ":" in path.parts[0]:
        raise ValueError(f"unsafe update archive drive path: {member.filename!r}")
    unix_mode = (member.external_attr >> 16) & 0o170000
    if unix_mode == 0o120000:
        raise ValueError(f"symbolic links are not allowed: {member.filename!r}")
    return path


def extract_update_package(package_path, destination_dir, manifest=None):
    package_path = Path(package_path)
    destination_dir = Path(destination_dir)
    if manifest is not None:
        verify_update_package(package_path, manifest)
    if destination_dir.exists() and any(destination_dir.iterdir()):
        raise ValueError("update staging directory must be empty")
    destination_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "r") as archive:
        members = tuple(archive.infolist())
        validated = tuple(
            (member, _validated_archive_member(member))
            for member in members
        )
        for member, relative_path in validated:
            target = destination_dir.joinpath(*relative_path.parts)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member, "r") as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    if manifest is not None:
        executable_path = destination_dir / manifest.executable_name
        if not executable_path.is_file():
            raise ValueError(
                f"staged update is missing {manifest.executable_name}"
            )
    return destination_dir
