#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_root="${1:-${TANUKI_BUILD_ROOT:-$repo_root}}"
python_exe="${TANUKI_PYTHON:-python3}"
mkdir -p "$output_root"
output_root="$(cd "$output_root" && pwd -P)"
if [[ "$output_root" == "/" ]]; then
  echo "Refusing to use the filesystem root as the output directory." >&2
  exit 2
fi
build_root="$output_root/build/macos"
dist_root="$output_root/dist"
iconset_path="$build_root/TanukiPet.iconset"
icon_path="$build_root/TanukiPet.icns"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build_macos.sh must run on macOS." >&2
  exit 2
fi

export TANUKI_REPO_ROOT="$repo_root"
export TANUKI_MACOS_ICON="$icon_path"
export TANUKI_APP_VERSION
TANUKI_APP_VERSION="$($python_exe -c 'from tanuki_core.app_version import APP_VERSION; print(APP_VERSION)')"

case "$(uname -m)" in
  arm64) architecture="arm64" ;;
  x86_64) architecture="x64" ;;
  *)
    echo "Unsupported macOS architecture: $(uname -m)" >&2
    exit 2
    ;;
esac

required_paths=(
  "$repo_root/lab_2.py"
  "$repo_root/luna.ico"
  "$repo_root/assets_cropped"
  "$repo_root/items"
  "$repo_root/UI/locales"
  "$repo_root/UI/trophies"
  "$repo_root/UI/family_icon"
  "$repo_root/UI/pet_overlays"
  "$repo_root/packaging/macos/Info.plist"
)
for required_path in "${required_paths[@]}"; do
  if [[ ! -e "$required_path" ]]; then
    echo "Missing build input: $required_path" >&2
    exit 2
  fi
done

rm -rf "$build_root" "$dist_root/TanukiPet" "$dist_root/TanukiPet.app"
mkdir -p "$build_root" "$dist_root"

"$python_exe" "$repo_root/tools/create_macos_iconset.py" \
  "$repo_root/luna.ico" "$iconset_path"
iconutil --convert icns --output "$icon_path" "$iconset_path"

"$python_exe" -m PyInstaller \
  --noconfirm \
  --clean \
  --workpath "$build_root/pyinstaller" \
  --distpath "$dist_root" \
  "$repo_root/TanukiPet-macOS.spec"

app_path="$dist_root/TanukiPet.app"
plist_path="$app_path/Contents/Info.plist"
if [[ ! -d "$app_path" || ! -f "$plist_path" ]]; then
  echo "PyInstaller did not produce TanukiPet.app." >&2
  exit 3
fi

plutil -lint "$plist_path"
codesign --force --deep --sign - "$app_path"
codesign --verify --deep --strict --verbose=2 "$app_path"

package_name="TanukiPet-${TANUKI_APP_VERSION}-macos-${architecture}.zip"
package_path="$dist_root/$package_name"
rm -f "$package_path"
ditto -c -k --sequesterRsrc --keepParent "$app_path" "$package_path"

echo "macOS limited build complete."
echo "Application: $app_path"
echo "Package: $package_path"
