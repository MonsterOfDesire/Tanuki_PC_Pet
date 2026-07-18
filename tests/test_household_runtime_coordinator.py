import unittest

from tanuki_core.household_event_rules import HouseholdEventScheduleState
from tanuki_core.household_runtime_coordinator import HouseholdRuntimeCoordinator
from tanuki_core.household_state import HouseholdEventLog, HouseholdState


class FakeDashboard:
    def __init__(self):
        self.summary_refreshes = 0
        self.social_refreshes = 0
        self.relationship_refreshes = 0

    def refresh_household_summary_if_open(self):
        self.summary_refreshes += 1

    def refresh_social_log_if_open(self):
        self.social_refreshes += 1

    def refresh_relationship_table_if_open(self):
        self.relationship_refreshes += 1


class FakePet:
    def __init__(self, name, visible=True):
        self.name = name
        self.visible = visible
        self.pending_social_log_event = {}
        self.log_icons = 0

    def isVisible(self):
        return self.visible

    def pop_log_icon(self):
        self.log_icons += 1


class FakeProfiler:
    def __init__(self):
        self.calls = []

    def record_section(self, section_name, duration_ms):
        self.calls.append((section_name, duration_ms))


class HouseholdRuntimeCoordinatorTests(unittest.TestCase):
    def build_coordinator(self, schedule=None):
        return HouseholdRuntimeCoordinator(
            household=HouseholdState(),
            event_log=HouseholdEventLog(),
            event_schedule=schedule or HouseholdEventScheduleState(),
        )

    def test_record_event_updates_views_and_notifies_visible_target_for_player_event(self):
        coordinator = self.build_coordinator()
        dashboard = FakeDashboard()
        target = FakePet("Tsurumaru Tsuyoshi")

        entry = coordinator.record_event(
            dashboard=dashboard,
            pets=[target],
            occurred_at=10.0,
            category="player_offer",
            event_type="offer_honey_success",
            actor_name="Player",
            target_name=target.name,
            relation_delta={"trust": 0.2},
        )

        self.assertEqual(target.log_icons, 1)
        self.assertEqual(dashboard.summary_refreshes, 1)
        self.assertEqual(dashboard.social_refreshes, 1)
        self.assertEqual(dashboard.relationship_refreshes, 1)
        self.assertEqual(entry.relation_delta, {"trust": 0.2})

    def test_social_entry_does_not_directly_refresh_household_summary(self):
        coordinator = self.build_coordinator()
        dashboard = FakeDashboard()

        coordinator.record_event(
            dashboard=dashboard,
            occurred_at=12.0,
            category="social",
            channel="social",
            actor_name="Symboli Rudolf",
            target_name="Tokai Teio",
            relation_delta={"familiarity": 0.1},
        )

        self.assertEqual(dashboard.summary_refreshes, 0)
        self.assertEqual(dashboard.social_refreshes, 1)
        self.assertEqual(dashboard.relationship_refreshes, 1)

    def test_collect_pending_social_log_events_clears_payload_and_records_entry(self):
        coordinator = self.build_coordinator()
        dashboard = FakeDashboard()
        actor = FakePet("Symboli Rudolf")
        actor.pending_social_log_event = {
            "actor_name": actor.name,
            "target_name": "Tokai Teio",
            "summary": "魯道夫看了帝寶一會兒。",
            "relation_delta": {"familiarity": 0.2},
        }

        entries = coordinator.collect_pending_social_log_events(
            pets=[actor],
            dashboard=dashboard,
            now=20.0,
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].channel, "social")
        self.assertEqual(actor.pending_social_log_event, {})

    def test_update_events_profiles_sandbox_social_collection(self):
        coordinator = self.build_coordinator()
        dashboard = FakeDashboard()
        profiler = FakeProfiler()
        actor = FakePet("Symboli Rudolf")
        actor.pending_social_log_event = {
            "actor_name": actor.name,
            "target_name": "Tokai Teio",
            "summary": "魯道夫向帝寶點了點頭。",
        }

        events = coordinator.update_events(
            world_mode="sandbox",
            pets=[actor],
            dashboard=dashboard,
            profiler=profiler,
            now=30.0,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(profiler.calls[0][0], "household.update")

    def test_world_mode_change_resets_same_schedule_and_clears_item_interactions(self):
        schedule = HouseholdEventScheduleState(1.0, 2.0, 3.0)
        coordinator = self.build_coordinator(schedule=schedule)
        dashboard = FakeDashboard()
        calls = []

        changed = coordinator.handle_world_mode_change(
            "golden_legend",
            previous_mode="sandbox",
            dashboard=dashboard,
            clear_offer_scene=lambda: calls.append("scene"),
            clear_offer_hover=lambda: calls.append("hover"),
            now=100.0,
        )

        self.assertTrue(changed)
        self.assertIs(coordinator.event_schedule, schedule)
        self.assertEqual(schedule.next_teio_drink_at, 130.0)
        self.assertEqual(calls, ["scene", "hover"])
        self.assertEqual(dashboard.summary_refreshes, 1)


if __name__ == "__main__":
    unittest.main()
