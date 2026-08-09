import unittest

from tanuki_core.information_center_spec import (
    DEFAULT_INFORMATION_CENTER_PAGE,
    INFORMATION_CENTER_PAGE_SPECS,
    PAGE_EVENT_LOG,
    PAGE_FAMILY_STATUS,
    PAGE_RELATION_SUMMON,
    PAGE_STATUS_SETTINGS,
    PAGE_ACHIEVEMENTS,
    get_information_center_page_spec,
)


class InformationCenterSpecTests(unittest.TestCase):
    def test_page_order_matches_navigation_design(self):
        self.assertEqual(
            tuple(page.page_id for page in INFORMATION_CENTER_PAGE_SPECS),
            (
                PAGE_RELATION_SUMMON,
                PAGE_EVENT_LOG,
                PAGE_FAMILY_STATUS,
                PAGE_ACHIEVEMENTS,
                PAGE_STATUS_SETTINGS,
            ),
        )

    def test_family_summary_is_default_page(self):
        self.assertEqual(DEFAULT_INFORMATION_CENTER_PAGE, PAGE_FAMILY_STATUS)
        self.assertEqual(get_information_center_page_spec(None).page_id, PAGE_FAMILY_STATUS)

    def test_unknown_page_is_rejected(self):
        with self.assertRaises(ValueError):
            get_information_center_page_spec("missing")


if __name__ == "__main__":
    unittest.main()
