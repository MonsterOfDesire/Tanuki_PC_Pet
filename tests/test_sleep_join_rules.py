import unittest

from tanuki_core.sleep_join_rules import (
    build_sleep_group_join_plan,
    resolve_sleep_join_target_x,
)


class SleepJoinRuleTests(unittest.TestCase):
    def test_first_joiner_creates_group_and_second_uses_other_slot(self):
        first = build_sleep_group_join_plan(
            target_activity_id="activity-1",
            target_name="Symboli Rudolf",
            occupied_slots=(0,),
        )
        second = build_sleep_group_join_plan(
            target_activity_id="activity-1",
            target_name="Symboli Rudolf",
            existing_group_id=first.group_id,
            existing_anchor_name=first.anchor_name,
            occupied_slots=(0, 1),
        )
        third = build_sleep_group_join_plan(
            target_activity_id="activity-1",
            target_name="Symboli Rudolf",
            existing_group_id=first.group_id,
            existing_anchor_name=first.anchor_name,
            occupied_slots=(0, 1, -1),
        )

        self.assertTrue(first.allowed)
        self.assertEqual(first.group_id, "sleep-group:activity-1")
        self.assertEqual(first.anchor_name, "Symboli Rudolf")
        self.assertEqual(first.slot, 1)
        self.assertEqual(second.slot, -1)
        self.assertEqual(third.slot, 2)

    def test_join_target_is_positioned_beside_anchor(self):
        right = resolve_sleep_join_target_x(
            anchor_x=100.0,
            anchor_width=100.0,
            joiner_width=80.0,
            slot=1,
        )
        left = resolve_sleep_join_target_x(
            anchor_x=100.0,
            anchor_width=100.0,
            joiner_width=80.0,
            slot=-1,
        )

        self.assertGreater(right, 100.0)
        self.assertLess(left, 100.0)

        farther_right = resolve_sleep_join_target_x(
            anchor_x=100.0,
            anchor_width=100.0,
            joiner_width=80.0,
            slot=2,
        )
        self.assertGreater(farther_right, right)


if __name__ == "__main__":
    unittest.main()
