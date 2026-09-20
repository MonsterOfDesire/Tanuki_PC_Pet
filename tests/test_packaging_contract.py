from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OPTIONAL_QT_MODULES = (
    "PyQt6.QtPdf",
    "PyQt6.QtNetwork",
    "PyQt6.QtSvg",
)


class PackagingContractTests(unittest.TestCase):
    def test_windows_and_macos_exclude_unused_optional_qt_modules(self):
        windows_script = (
            REPOSITORY_ROOT / "build_lab_2.ps1"
        ).read_text(encoding="utf-8-sig")
        macos_spec = (
            REPOSITORY_ROOT / "TanukiPet-macOS.spec"
        ).read_text(encoding="utf-8")

        for module_name in OPTIONAL_QT_MODULES:
            self.assertIn(f"--exclude-module {module_name}", windows_script)
            self.assertIn(module_name, macos_spec)
        for binary_name in (
            "Qt6Pdf.dll",
            "Qt6Network.dll",
            "Qt6Svg.dll",
            "qtuiotouchplugin.dll",
            "qsvgicon.dll",
            "qpdf.dll",
            "qsvg.dll",
        ):
            self.assertIn(binary_name, windows_script)
        self.assertIn("unused_qt_binary_markers", macos_spec)

    def test_opengl_software_fallback_is_not_excluded(self):
        combined = "\n".join(
            (
                (REPOSITORY_ROOT / "build_lab_2.ps1").read_text(
                    encoding="utf-8-sig"
                ),
                (REPOSITORY_ROOT / "TanukiPet-macOS.spec").read_text(
                    encoding="utf-8"
                ),
            )
        ).lower()
        self.assertNotIn("exclude-module opengl32sw", combined)


if __name__ == "__main__":
    unittest.main()
