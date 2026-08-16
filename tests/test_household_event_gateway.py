import unittest
from types import SimpleNamespace

from tanuki_core.household_event_gateway import HouseholdEventGateway


class FakeHouseholdCoordinator:
    def __init__(self):
        self.calls = []

    def record_event(self, **fields):
        self.calls.append(("record", fields))
        return SimpleNamespace(metadata={"activity_event_name": "race.done"})

    def record_resolved_event(self, event, **fields):
        self.calls.append(("resolved", event, fields))
        return SimpleNamespace(metadata={})


class HouseholdEventGatewayTests(unittest.TestCase):
    def build_gateway(self):
        household = FakeHouseholdCoordinator()
        tendency_calls = []
        achievement_calls = []
        tendency = SimpleNamespace(
            process_household_entry=lambda entry, **fields: tendency_calls.append(
                (entry, fields)
            )
        )
        achievements = SimpleNamespace(
            consume_entry=lambda entry: achievement_calls.append(entry)
        )
        gateway = HouseholdEventGateway(
            household_coordinator=household,
            dashboard="dashboard",
            pets=("pet",),
            transformation_tendency_coordinator=tendency,
            transformation_executor="executor",
            achievement_runtime_coordinator=achievements,
            now_provider=lambda: 99.0,
        )
        return gateway, household, tendency_calls, achievement_calls

    def test_record_event_notifies_tendency_and_achievement_once(self):
        gateway, household, tendency_calls, achievement_calls = (
            self.build_gateway()
        )

        entry = gateway.record_event(
            occurred_at=25.0,
            category="social",
            event_type="race_completed",
        )

        self.assertIs(achievement_calls[0], entry)
        self.assertEqual(len(achievement_calls), 1)
        self.assertEqual(len(tendency_calls), 1)
        self.assertEqual(tendency_calls[0][1]["pets"], ("pet",))
        self.assertEqual(tendency_calls[0][1]["executor"], "executor")
        self.assertEqual(tendency_calls[0][1]["now"], 25.0)
        self.assertEqual(household.calls[0][1]["dashboard"], "dashboard")

    def test_scheduled_entries_use_one_shared_observation_time(self):
        gateway, _household, tendency_calls, achievement_calls = (
            self.build_gateway()
        )
        entries = (SimpleNamespace(metadata={}), SimpleNamespace(metadata={}))

        returned = gateway.process_entries(entries, occurred_at=40.0)

        self.assertIs(returned, entries)
        self.assertEqual(len(tendency_calls), 2)
        self.assertEqual(len(achievement_calls), 2)
        self.assertEqual(
            [fields["now"] for _entry, fields in tendency_calls],
            [40.0, 40.0],
        )


if __name__ == "__main__":
    unittest.main()
