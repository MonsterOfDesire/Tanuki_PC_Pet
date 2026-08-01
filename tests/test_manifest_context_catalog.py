import re
import unittest
from pathlib import Path

from tanuki_core.manifest_xlsx_converter import KNOWN_CONTEXTS


CATALOG_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "MANIFEST_CONTEXT_CATALOG.md"
)
CATALOG_ENTRY_PATTERN = re.compile(
    r"^- \[x\] `([^`]+)` — \*\*情境\*\*：.+；"
    r"\*\*對象\*\*：.+；\*\*效果\*\*：.+；\*\*狀態\*\*：.+$",
    re.MULTILINE,
)


class ManifestContextCatalogTests(unittest.TestCase):
    def test_catalog_lists_every_known_context_once_with_required_details(self):
        text = CATALOG_PATH.read_text(encoding="utf-8")
        listed = CATALOG_ENTRY_PATTERN.findall(text)

        self.assertEqual(len(listed), len(set(listed)), "catalog contains duplicate contexts")
        self.assertEqual(set(listed), set(KNOWN_CONTEXTS))


if __name__ == "__main__":
    unittest.main()
