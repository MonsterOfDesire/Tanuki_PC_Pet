import unittest

from tanuki_core.household_event_rules import (
    COLLECTIBLE_LIVING_FUND_THRESHOLD,
    COLLECTIBLE_PRESSURE_MAX,
    RUDOLF_WORK_INTERVAL_SECONDS,
    TEIO_DRINK_INTERVAL_SECONDS,
    WORK_LIVING_FUND_THRESHOLD,
    WORK_PRESSURE_THRESHOLD,
    HouseholdEventScheduleState,
    build_household_event_schedule,
    consume_rudolf_work_schedule_if_due,
    refresh_household_summary_if_needed,
    resolve_household_events,
)
from tanuki_core.household_state import HouseholdState


class HouseholdEventRulesTests(unittest.TestCase):
    def test_refresh_household_summary_if_needed_calls_dashboard_when_events_exist(self):
        class FakeDashboard:
            def __init__(self):
                self.refresh_calls = 0
                self.social_refresh_calls = 0
                self.relationship_refresh_calls = 0

            def refresh_household_summary_if_open(self):
                self.refresh_calls += 1

            def refresh_social_log_if_open(self):
                self.social_refresh_calls += 1

            def refresh_relationship_table_if_open(self):
                self.relationship_refresh_calls += 1

        dashboard = FakeDashboard()

        refreshed = refresh_household_summary_if_needed(dashboard, [object()])

        self.assertTrue(refreshed)
        self.assertEqual(dashboard.refresh_calls, 1)
        self.assertEqual(dashboard.social_refresh_calls, 1)
        self.assertEqual(dashboard.relationship_refresh_calls, 1)

    def test_refresh_household_summary_if_needed_skips_when_no_events_exist(self):
        class FakeDashboard:
            def __init__(self):
                self.refresh_calls = 0
                self.social_refresh_calls = 0
                self.relationship_refresh_calls = 0

            def refresh_household_summary_if_open(self):
                self.refresh_calls += 1

            def refresh_social_log_if_open(self):
                self.social_refresh_calls += 1

            def refresh_relationship_table_if_open(self):
                self.relationship_refresh_calls += 1

        dashboard = FakeDashboard()

        refreshed = refresh_household_summary_if_needed(dashboard, [])

        self.assertFalse(refreshed)
        self.assertEqual(dashboard.refresh_calls, 0)
        self.assertEqual(dashboard.social_refresh_calls, 0)
        self.assertEqual(dashboard.relationship_refresh_calls, 0)

    def test_build_household_event_schedule_starts_with_future_due_times(self):
        schedule = build_household_event_schedule(now=100.0)

        self.assertEqual(schedule.next_teio_drink_at, 100.0 + TEIO_DRINK_INTERVAL_SECONDS)
        self.assertEqual(schedule.next_rudolf_work_at, 100.0 + RUDOLF_WORK_INTERVAL_SECONDS)

    def test_resolve_household_events_emits_teio_drink_when_due(self):
        household = HouseholdState()
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=10.0,
            next_rudolf_work_at=999.0,
            next_rudolf_collectible_at=999.0,
        )

        events = resolve_household_events(household, schedule, now=10.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "teio_drink_expense")
        self.assertEqual(events[0].living_fund_delta, -18)
        self.assertEqual(events[0].household_pressure_delta, 4.0)
        self.assertEqual(schedule.next_teio_drink_at, 10.0 + TEIO_DRINK_INTERVAL_SECONDS)

    def test_work_schedule_is_consumed_by_activity_runtime_when_due(self):
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=999.0,
            next_rudolf_work_at=30.0,
            next_rudolf_collectible_at=999.0,
        )

        consumed = consume_rudolf_work_schedule_if_due(
            schedule,
            now=30.0,
        )

        self.assertTrue(consumed)
        self.assertEqual(
            schedule.next_rudolf_work_at,
            30.0 + RUDOLF_WORK_INTERVAL_SECONDS,
        )

    def test_work_schedule_is_not_consumed_before_due(self):
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=999.0,
            next_rudolf_work_at=30.0,
            next_rudolf_collectible_at=999.0,
        )

        consumed = consume_rudolf_work_schedule_if_due(
            schedule,
            now=29.0,
        )

        self.assertFalse(consumed)
        self.assertEqual(schedule.next_rudolf_work_at, 30.0)

    def test_periodic_resolver_leaves_work_schedule_to_activity_runtime(self):
        household = HouseholdState(
            living_fund=WORK_LIVING_FUND_THRESHOLD,
            household_pressure=WORK_PRESSURE_THRESHOLD,
        )
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=999.0,
            next_rudolf_work_at=40.0,
            next_rudolf_collectible_at=999.0,
        )

        events = resolve_household_events(household, schedule, now=40.0)

        self.assertEqual(events, [])
        self.assertEqual(schedule.next_rudolf_work_at, 40.0)

    def test_resolve_household_events_emits_collectible_when_fund_is_high_and_pressure_low(self):
        household = HouseholdState(
            living_fund=COLLECTIBLE_LIVING_FUND_THRESHOLD,
            household_pressure=COLLECTIBLE_PRESSURE_MAX,
        )
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=999.0,
            next_rudolf_work_at=999.0,
            next_rudolf_collectible_at=50.0,
        )

        events = resolve_household_events(household, schedule, now=50.0)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "rudolf_collectible_expense")
        self.assertEqual(events[0].living_fund_delta, -35)
        self.assertEqual(events[0].household_pressure_delta, 3.0)

    def test_resolve_household_events_can_emit_multiple_due_events_in_one_tick(self):
        household = HouseholdState(living_fund=700, household_pressure=32.0)
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=60.0,
            next_rudolf_work_at=60.0,
            next_rudolf_collectible_at=999.0,
        )

        events = resolve_household_events(household, schedule, now=60.0)

        self.assertEqual(
            [event.event_type for event in events],
            ["teio_drink_expense"],
        )


if __name__ == "__main__":
    unittest.main()
