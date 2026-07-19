import unittest
from unittest.mock import patch

from tools import manifest_xlsx_to_json


class ManifestXlsxToolTests(unittest.TestCase):
    def test_wrapper_delegates_arguments_and_exit_code(self):
        arguments = ["--assets-dir", "assets", "--character", "Tokai Teio", "--write"]

        with patch(
            "tanuki_core.manifest_xlsx_converter.main",
            return_value=7,
        ) as run_converter:
            result = manifest_xlsx_to_json.main(arguments)

        self.assertEqual(result, 7)
        run_converter.assert_called_once_with(arguments)


if __name__ == "__main__":
    unittest.main()
