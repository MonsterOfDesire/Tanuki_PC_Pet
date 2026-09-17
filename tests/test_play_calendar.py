from datetime import date, datetime, timezone
import unittest

from tanuki_core.play_calendar import normalize_local_date, play_day_number


class PlayCalendarTests(unittest.TestCase):
    def test_starting_local_date_is_day_one(self):
        self.assertEqual(
            play_day_number("2026-09-17", today=date(2026, 9, 17)),
            1,
        )

    def test_elapsed_calendar_days_include_days_when_app_was_closed(self):
        self.assertEqual(
            play_day_number("2026-09-10", today=date(2026, 9, 17)),
            8,
        )

    def test_invalid_and_future_dates_normalize_to_today(self):
        self.assertEqual(
            normalize_local_date("invalid", fallback=date(2026, 9, 17)),
            "2026-09-17",
        )
        self.assertEqual(
            normalize_local_date("2026-10-01", fallback=date(2026, 9, 17)),
            "2026-09-17",
        )

    def test_datetime_uses_its_local_calendar_date(self):
        value = datetime(2026, 9, 16, 16, 30, tzinfo=timezone.utc)
        self.assertEqual(normalize_local_date(value), value.astimezone().date().isoformat())


if __name__ == "__main__":
    unittest.main()
