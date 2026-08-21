import plistlib
from pathlib import Path
import tempfile
import unittest

from tools.create_macos_iconset import ICON_OUTPUTS, build_iconset


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class MacOSBuildContractTests(unittest.TestCase):
    def test_committed_plist_declares_limited_background_app(self):
        with (REPOSITORY_ROOT / "packaging" / "macos" / "Info.plist").open(
            "rb"
        ) as handle:
            values = plistlib.load(handle)

        self.assertEqual(
            values["CFBundleIdentifier"],
            "io.github.monsterofdesire.tanukipet",
        )
        self.assertEqual(values["LSMinimumSystemVersion"], "13.0")
        self.assertTrue(values["LSUIElement"])
        self.assertTrue(values["NSHighResolutionCapable"])

    def test_iconset_generator_produces_all_apple_icon_slots(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            outputs = build_iconset(
                REPOSITORY_ROOT / "luna.ico",
                Path(temporary_directory) / "TanukiPet.iconset",
            )

            self.assertEqual(len(outputs), len(ICON_OUTPUTS))
            self.assertTrue(all(output.is_file() for output in outputs))

    def test_macos_package_excludes_windows_updater(self):
        spec_text = (
            REPOSITORY_ROOT / "TanukiPet-macOS.spec"
        ).read_text(encoding="utf-8")
        script_text = (
            REPOSITORY_ROOT / "build_macos.sh"
        ).read_text(encoding="utf-8")

        self.assertNotIn("TanukiUpdater", spec_text)
        self.assertNotIn("TanukiUpdater", script_text)
        self.assertIn('"packaging" / "macos" / "Info.plist"', spec_text)
        self.assertIn("macos-${architecture}.zip", script_text)


if __name__ == "__main__":
    unittest.main()
