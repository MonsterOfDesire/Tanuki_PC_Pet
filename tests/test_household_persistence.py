import unittest

from tanuki_core.household_event_rules import HouseholdEventScheduleState
from tanuki_core.household_persistence import (
    PERSISTED_HOUSEHOLD_LOG_LIMIT,
    apply_household_persistence_state,
    capture_household_persistence_state,
)
from tanuki_core.household_state import HouseholdEventLog, HouseholdState, record_household_event


class HouseholdPersistenceTests(unittest.TestCase):
    def test_capture_household_persistence_state_serializes_state_log_and_schedule(self):
        household = HouseholdState(living_fund=620, household_pressure=18.5)
        event_log = HouseholdEventLog()
        record_household_event(
            household,
            event_log,
            occurred_at=10.0,
            wall_clock_time=1000.0,
            category="economy",
            event_type="expense",
            summary="帝寶買飲料",
            actor_name="Tokai Teio",
            living_fund_delta=-18,
        )
        record_household_event(
            household,
            event_log,
            occurred_at=12.0,
            wall_clock_time=1002.0,
            category="social",
            event_type="observe_chat",
            summary="魯道夫和帝寶聊起晚餐。",
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            mood_delta=1.0,
            relation_delta={"familiarity": 2.0, "trust": 0.5},
            tags=("observe", "meal"),
        )
        schedule = HouseholdEventScheduleState(
            next_teio_drink_at=130.0,
            next_rudolf_work_at=150.0,
            next_rudolf_collectible_at=160.0,
        )

        payload = capture_household_persistence_state(household, event_log, schedule)

        self.assertEqual(payload["living_fund"], household.living_fund)
        self.assertEqual(payload["event_log_next_sequence"], event_log.next_sequence)
        self.assertEqual(payload["event_log"][0]["summary"], "帝寶買飲料")
        self.assertEqual(payload["event_log"][0]["channel"], "economy")
        self.assertEqual(payload["event_log"][1]["channel"], "social")
        self.assertEqual(payload["event_log"][1]["tags"], ["observe", "meal"])
        self.assertEqual(payload["event_log"][1]["relation_delta"], {"familiarity": 2.0, "trust": 0.5})
        self.assertEqual(payload["relationship_ledger"][0]["actor_name"], "Symboli Rudolf")
        self.assertEqual(payload["relationship_ledger"][0]["target_name"], "Tokai Teio")
        self.assertEqual(payload["relationship_ledger"][0]["trust"], 0.5)
        self.assertEqual(payload["event_schedule"]["next_rudolf_work_at"], 150.0)

    def test_capture_household_persistence_state_limits_log_entries(self):
        household = HouseholdState()
        event_log = HouseholdEventLog()
        schedule = HouseholdEventScheduleState()

        for index in range(PERSISTED_HOUSEHOLD_LOG_LIMIT + 3):
            record_household_event(
                household,
                event_log,
                occurred_at=float(index),
                wall_clock_time=2000.0 + index,
                summary=f"entry-{index}",
                apply_deltas=False,
            )

        payload = capture_household_persistence_state(household, event_log, schedule)

        self.assertEqual(len(payload["event_log"]), PERSISTED_HOUSEHOLD_LOG_LIMIT)
        self.assertEqual(payload["event_log"][0]["summary"], "entry-3")
        self.assertEqual(payload["event_log"][-1]["summary"], f"entry-{PERSISTED_HOUSEHOLD_LOG_LIMIT + 2}")

    def test_apply_household_persistence_state_restores_saved_payload(self):
        household = HouseholdState()
        event_log = HouseholdEventLog()
        schedule = HouseholdEventScheduleState()

        applied = apply_household_persistence_state(
            {
                "living_fund": 777,
                "household_pressure": 23.5,
                "event_log_next_sequence": 12,
                "event_log": [
                    {
                        "sequence": 10,
                        "occurred_at": 88.0,
                        "wall_clock_time": 1888.0,
                        "category": "economy",
                        "event_type": "income",
                        "channel": "economy",
                        "importance": "major",
                        "summary": "魯道夫工作賺錢",
                        "actor_name": "Symboli Rudolf",
                        "target_name": "Tokai Teio",
                        "mood_delta": 1.5,
                        "relation_delta": {"familiarity": 3.0, "attachment": 1.0},
                        "tags": ["work", "family"],
                        "living_fund_delta": 80,
                        "metadata": {"source": "test"},
                    }
                ],
                "relationship_ledger": [
                    {
                        "actor_name": "Symboli Rudolf",
                        "target_name": "Tokai Teio",
                        "familiarity": 7.0,
                        "trust": 4.0,
                        "attachment": 2.0,
                        "tension": 0.5,
                        "updated_at": 77.0,
                        "event_count": 3,
                    }
                ],
                "event_schedule": {
                    "next_teio_drink_at": 91.0,
                    "next_rudolf_work_at": 111.0,
                    "next_rudolf_collectible_at": 121.0,
                },
            },
            household,
            event_log,
            schedule,
        )

        self.assertTrue(applied)
        self.assertEqual(household.living_fund, 777)
        self.assertEqual(household.household_pressure, 23.5)
        self.assertEqual(event_log.entries[0].summary, "魯道夫工作賺錢")
        self.assertEqual(event_log.entries[0].importance, "major")
        self.assertEqual(event_log.entries[0].mood_delta, 1.5)
        self.assertEqual(event_log.entries[0].relation_delta, {"familiarity": 3.0, "attachment": 1.0})
        self.assertEqual(event_log.entries[0].tags, ("work", "family"))
        self.assertEqual(household.relationships.get_entry("Symboli Rudolf", "Tokai Teio").familiarity, 7.0)
        self.assertEqual(event_log.next_sequence, 12)
        self.assertEqual(schedule.next_rudolf_work_at, 111.0)

    def test_apply_household_persistence_state_defaults_extended_log_fields_for_legacy_payload(self):
        household = HouseholdState()
        event_log = HouseholdEventLog()
        schedule = HouseholdEventScheduleState()

        apply_household_persistence_state(
            {
                "event_log": [
                    {
                        "sequence": 1,
                        "occurred_at": 3.0,
                        "category": "player_offer",
                        "event_type": "offer_honey_success",
                        "summary": "帝寶拿到了蜂蜜。",
                    }
                ]
            },
            household,
            event_log,
            schedule,
        )

        entry = event_log.entries[0]

        self.assertEqual(entry.channel, "item")
        self.assertEqual(entry.importance, "normal")
        self.assertEqual(entry.mood_delta, 0.0)
        self.assertEqual(entry.relation_delta, {})
        self.assertEqual(entry.tags, ())


if __name__ == "__main__":
    unittest.main()
