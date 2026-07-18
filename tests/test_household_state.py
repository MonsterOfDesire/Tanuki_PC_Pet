import unittest

from tanuki_core.household_state import (
    DEFAULT_HOUSEHOLD_EVENT_LOG_CAPACITY,
    DEFAULT_HOUSEHOLD_PRESSURE,
    DEFAULT_LIVING_FUND,
    HouseholdEventLog,
    HouseholdState,
    build_default_household_event_log,
    build_default_household_state,
    clamp_household_pressure,
    record_player_donate_household_fund,
    record_household_event,
    seed_default_household_events,
)


class HouseholdStateTests(unittest.TestCase):
    def test_default_builders_initialize_household_state_and_log(self):
        household = build_default_household_state()
        event_log = build_default_household_event_log()

        self.assertEqual(household.living_fund, DEFAULT_LIVING_FUND)
        self.assertEqual(household.household_pressure, DEFAULT_HOUSEHOLD_PRESSURE)
        self.assertEqual(event_log.max_entries, DEFAULT_HOUSEHOLD_EVENT_LOG_CAPACITY)
        self.assertEqual(event_log.entries, [])
        self.assertEqual(event_log.next_sequence, 1)

    def test_household_delta_clamps_fund_and_pressure(self):
        household = HouseholdState(living_fund=12, household_pressure=95.0)

        household.apply_delta(
            living_fund_delta=-40,
            household_pressure_delta=12.0,
        )

        self.assertEqual(household.living_fund, 0)
        self.assertEqual(household.household_pressure, 100.0)
        self.assertEqual(clamp_household_pressure(-5.0), 0.0)

    def test_event_log_append_behaves_like_ring_buffer(self):
        event_log = HouseholdEventLog(max_entries=2)

        first = event_log.append(event_log.create_entry(occurred_at=1.0, summary="a"))
        second = event_log.append(event_log.create_entry(occurred_at=2.0, summary="b"))
        third = event_log.append(event_log.create_entry(occurred_at=3.0, summary="c"))

        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(third.sequence, 3)
        self.assertEqual([entry.summary for entry in event_log.entries], ["b", "c"])
        self.assertEqual(event_log.next_sequence, 4)
        self.assertEqual([entry.summary for entry in event_log.recent_entries(limit=1)], ["c"])

    def test_record_household_event_updates_state_and_stores_metadata(self):
        household = HouseholdState(living_fund=100, household_pressure=10.0)
        event_log = HouseholdEventLog()

        entry = record_household_event(
            household,
            event_log,
            occurred_at=12.5,
            wall_clock_time=1234.0,
            category="economy",
            event_type="expense",
            summary="帝寶偷喝飲料",
            actor_name="Tokai Teio",
            living_fund_delta=-35,
            household_pressure_delta=8.5,
            metadata={"reason": "soft_drink"},
        )

        self.assertEqual(entry.sequence, 1)
        self.assertEqual(entry.category, "economy")
        self.assertEqual(entry.event_type, "expense")
        self.assertEqual(entry.channel, "economy")
        self.assertEqual(entry.importance, "normal")
        self.assertEqual(entry.summary, "帝寶偷喝飲料")
        self.assertEqual(entry.wall_clock_time, 1234.0)
        self.assertEqual(entry.tags, ())
        self.assertEqual(entry.mood_delta, 0.0)
        self.assertEqual(entry.relation_delta, {})
        self.assertEqual(entry.metadata["reason"], "soft_drink")
        self.assertEqual(household.living_fund, 65)
        self.assertEqual(household.household_pressure, 18.5)
        self.assertEqual(event_log.next_sequence, 2)
        self.assertEqual(event_log.entries[0], entry)

    def test_record_social_event_stores_extended_fields_and_updates_relationship_ledger(self):
        household = HouseholdState()
        event_log = HouseholdEventLog()

        entry = record_household_event(
            household,
            event_log,
            occurred_at=42.0,
            category="social",
            event_type="observe_chat",
            summary="氣槽問帝寶晚餐想吃什麼。",
            actor_name="Air Groove",
            target_name="Tokai Teio",
            mood_delta=2.5,
            relation_delta={"familiarity": 1.5, "attachment": 0.5, "bad": "ignored"},
            tags=("observe", "meal", "observe"),
            apply_deltas=True,
        )

        relation = household.relationships.get_entry("Air Groove", "Tokai Teio")

        self.assertEqual(entry.channel, "social")
        self.assertEqual(entry.importance, "normal")
        self.assertEqual(entry.mood_delta, 2.5)
        self.assertEqual(entry.relation_delta, {"familiarity": 1.5, "attachment": 0.5})
        self.assertEqual(entry.tags, ("observe", "meal"))
        self.assertIsNotNone(relation)
        self.assertEqual(relation.familiarity, 1.5)
        self.assertEqual(relation.attachment, 0.5)
        self.assertEqual(relation.event_count, 1)

    def test_event_log_query_entries_filters_by_channel_participant_and_tags(self):
        event_log = HouseholdEventLog()
        social_entry = event_log.append(
            event_log.create_entry(
                occurred_at=1.0,
                category="social",
                actor_name="Symboli Rudolf",
                target_name="Tokai Teio",
                tags=("observe",),
                summary="魯道夫看著帝寶整理點心。",
            )
        )
        event_log.append(
            event_log.create_entry(
                occurred_at=2.0,
                category="economy",
                actor_name="Tokai Teio",
                tags=("expense",),
                summary="帝寶買飲料。",
            )
        )

        results = event_log.query_entries(
            channel="social",
            participant_name="Tokai Teio",
            tags=("observe",),
        )

        self.assertEqual(results, [social_entry])

    def test_record_household_event_can_skip_state_mutation_for_read_only_log(self):
        household = HouseholdState(living_fund=80, household_pressure=5.0)
        event_log = HouseholdEventLog()

        entry = record_household_event(
            household,
            event_log,
            occurred_at=20.0,
            category="log",
            event_type="note",
            summary="鶴寶今天特別安靜",
            actor_name="Tsurumaru Tsuyoshi",
            household_pressure_delta=10.0,
            apply_deltas=False,
        )

        self.assertEqual(entry.sequence, 1)
        self.assertEqual(household.living_fund, 80)
        self.assertEqual(household.household_pressure, 5.0)
        self.assertEqual(event_log.entries[0].summary, "鶴寶今天特別安靜")

    def test_seed_default_household_events_adds_bootstrap_notes_without_mutation(self):
        household = HouseholdState(living_fund=300, household_pressure=12.0)
        event_log = HouseholdEventLog()

        entries = seed_default_household_events(household, event_log, occurred_at=0.0)

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].event_type, "opening_note")
        self.assertEqual(entries[1].summary, "目前生活費為 300 元。")
        self.assertEqual(entries[2].summary, "家庭壓力目前為 12%。")
        self.assertEqual(household.living_fund, 300)
        self.assertEqual(household.household_pressure, 12.0)
        self.assertEqual(len(event_log.entries), 3)

    def test_record_player_donate_household_fund_updates_fund_and_relieves_pressure(self):
        household = HouseholdState(living_fund=200, household_pressure=10.0)
        event_log = HouseholdEventLog()

        entry = record_player_donate_household_fund(
            household,
            event_log,
            occurred_at=30.0,
            wall_clock_time=2234.0,
            amount=120,
        )

        self.assertEqual(entry.event_type, "player_donate_fund")
        self.assertEqual(entry.wall_clock_time, 2234.0)
        self.assertEqual(entry.living_fund_delta, 120)
        self.assertEqual(entry.household_pressure_delta, -4.0)
        self.assertEqual(household.living_fund, 320)
        self.assertEqual(household.household_pressure, 6.0)


if __name__ == "__main__":
    unittest.main()
