import unittest

from tanuki_core.app_version import AppVersion


class AppVersionTests(unittest.TestCase):
    def test_parses_release_and_prerelease_versions(self):
        self.assertEqual(str(AppVersion.parse("v0.8.0-beta")), "0.8.0-beta")
        self.assertEqual(str(AppVersion.parse("1.2.3-rc.2")), "1.2.3-rc.2")
        self.assertFalse(AppVersion.parse("1.0.0").is_prerelease)

    def test_semver_precedence_matches_release_channels(self):
        versions = tuple(
            AppVersion.parse(value)
            for value in (
                "1.0.0-alpha",
                "1.0.0-beta",
                "1.0.0-rc.1",
                "1.0.0",
                "1.1.0-beta",
            )
        )
        self.assertEqual(tuple(sorted(versions)), versions)

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            AppVersion.parse("latest")


if __name__ == "__main__":
    unittest.main()
