# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
import plistlib
import re


repo_root = Path(os.environ.get("TANUKI_REPO_ROOT", Path.cwd())).resolve()
icon_path = Path(os.environ["TANUKI_MACOS_ICON"]).resolve()
version_text = os.environ.get("TANUKI_APP_VERSION", "0.0.0")
version_match = re.match(r"\d+\.\d+\.\d+", version_text)
numeric_version = version_match.group(0) if version_match else "0.0.0"
with (repo_root / "packaging" / "macos" / "Info.plist").open(
    "rb"
) as plist_stream:
    info_plist_values = plistlib.load(plist_stream)
for managed_key in (
    "CFBundleExecutable",
    "CFBundleIdentifier",
    "CFBundleName",
    "CFBundlePackageType",
):
    info_plist_values.pop(managed_key, None)
info_plist_values.update({
    "CFBundleShortVersionString": numeric_version,
    "CFBundleVersion": numeric_version,
})

datas = [
    (str(repo_root / "assets_cropped"), "assets_cropped"),
    (str(repo_root / "items"), "items"),
    (str(repo_root / "UI" / "diet.png"), "UI"),
    (str(repo_root / "UI" / "diet_char.gif"), "UI"),
    (str(repo_root / "UI" / "relation_summon.gif"), "UI"),
    (str(repo_root / "UI" / "relation_summon_char.gif"), "UI"),
    (str(repo_root / "UI" / "event_note.jpg"), "UI"),
    (str(repo_root / "UI" / "event_note_char.gif"), "UI"),
    (str(repo_root / "UI" / "family_status_abstract.png"), "UI"),
    (str(repo_root / "UI" / "family_status_abstract_char.gif"), "UI"),
    (str(repo_root / "UI" / "status_setting.png"), "UI"),
    (str(repo_root / "UI" / "status_setting_char.gif"), "UI"),
    (str(repo_root / "UI" / "achievement.png"), "UI"),
    (str(repo_root / "UI" / "achievement_char.gif"), "UI"),
    (str(repo_root / "UI" / "trophies"), "UI/trophies"),
    (str(repo_root / "UI" / "locales"), "UI/locales"),
    (str(repo_root / "UI" / "side.png"), "UI"),
    (str(repo_root / "UI" / "family_icon"), "UI/family_icon"),
    (str(repo_root / "UI" / "pet_overlays"), "UI/pet_overlays"),
]

a = Analysis(
    [str(repo_root / "lab_2.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pynput", "pynput.mouse", "pynput.keyboard"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TanukiPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TanukiPet",
)
app = BUNDLE(
    coll,
    name="TanukiPet.app",
    icon=str(icon_path),
    bundle_identifier="io.github.monsterofdesire.tanukipet",
    info_plist=info_plist_values,
)
