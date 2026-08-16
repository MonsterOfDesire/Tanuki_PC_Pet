from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tanuki_core.app_version import AppVersion, UPDATE_MANIFEST_ASSET_NAME
from tanuki_core.update_package import (
    DEFAULT_EXECUTABLE_NAME,
    UpdatePackageManifest,
    calculate_sha256,
)


def build_zip(source_dir, output_path):
    source_dir = Path(source_dir).resolve()
    output_path = Path(output_path).resolve()
    if not source_dir.is_dir():
        raise ValueError(f"build directory does not exist: {source_dir}")
    if not (source_dir / DEFAULT_EXECUTABLE_NAME).is_file():
        raise ValueError(
            f"build directory is missing {DEFAULT_EXECUTABLE_NAME}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(source_dir).as_posix()
                if relative_path == "config.json":
                    continue
                archive.write(path, relative_path)
    return output_path


def build_manifest(version, package_path, package_url):
    package_path = Path(package_path)
    return UpdatePackageManifest(
        version=AppVersion.parse(version),
        package_name=package_path.name,
        package_url=str(package_url),
        sha256=calculate_sha256(package_path),
        size=package_path.stat().st_size,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a verified Tanuki PC Pet portable update package.",
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--package-url",
        required=True,
        help="Final HTTPS GitHub Release asset URL.",
    )
    args = parser.parse_args(argv)

    version = AppVersion.parse(args.version)
    output_dir = Path(args.output_dir).resolve()
    package_name = f"TanukiPet-{version}-windows-x64.zip"
    package_path = build_zip(
        args.source_dir,
        output_dir / package_name,
    )
    manifest = build_manifest(version, package_path, args.package_url)
    manifest_path = output_dir / UPDATE_MANIFEST_ASSET_NAME
    manifest_path.write_text(
        json.dumps(
            manifest.to_payload(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(package_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
