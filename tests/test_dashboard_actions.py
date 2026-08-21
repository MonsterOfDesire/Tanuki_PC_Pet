import unittest

from tanuki_core.dashboard_actions import DashboardActions


class FakeClock:
    def __init__(self):
        self.speeds = []

    def set_speed(self, speed):
        self.speeds.append(speed)


class FakePet:
    def __init__(self, *, under_care=False, care_lock_mode="none"):
        self.under_care = under_care
        self.care_lock_mode = care_lock_mode
        self.user_visible = True
        self.apply_display_scale_calls = []
        self.social_cooldown_duration = None
        self.show_calls = 0
        self.hide_calls = 0
        self.activity_locked = False
        self.activity_interrupt_calls = []
        self.activity_user_interrupt_provider = (
            lambda pet, reason: self.activity_interrupt_calls.append(reason)
        )

    def apply_display_scale(self, multiplier):
        self.apply_display_scale_calls.append(multiplier)

    def is_under_care(self, now_value):
        return self.under_care

    def show(self):
        self.show_calls += 1

    def hide(self):
        self.hide_calls += 1

    def is_activity_locked(self):
        return self.activity_locked


class DashboardActionsTests(unittest.TestCase):
    def test_apply_time_scale_delegates_to_clock(self):
        clock = FakeClock()
        actions = DashboardActions(sim_clock=clock, now_provider=lambda: 0.0)

        actions.apply_time_scale(4.0)

        self.assertEqual(clock.speeds, [4.0])

    def test_apply_display_scale_updates_all_pets(self):
        teio = FakePet()
        rudolf = FakePet()
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 0.0)

        actions.apply_display_scale(
            {
                "Tokai Teio": {"pet": teio},
                "Symboli Rudolf": {"pet": rudolf},
            },
            1.5,
        )

        self.assertEqual(teio.apply_display_scale_calls, [1.5])
        self.assertEqual(rudolf.apply_display_scale_calls, [1.5])

    def test_apply_social_cooldowns_targets_teio_and_tsuyoshi(self):
        teio = FakePet()
        tsuyoshi = FakePet()
        rudolf = FakePet()
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 0.0)

        actions.apply_social_cooldowns(
            {
                "Tokai Teio": {"pet": teio},
                "Tsurumaru Tsuyoshi": {"pet": tsuyoshi},
                "Symboli Rudolf": {"pet": rudolf},
            },
            5.0,
            40.0,
        )

        self.assertEqual(teio.social_cooldown_duration, 5.0)
        self.assertEqual(tsuyoshi.social_cooldown_duration, 40.0)
        self.assertIsNone(rudolf.social_cooldown_duration)

    def test_apply_pet_visibility_shows_pet_when_allowed(self):
        pet = FakePet()
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 123.0)

        actions.apply_pet_visibility(pet, True)

        self.assertTrue(pet.user_visible)
        self.assertEqual(pet.show_calls, 1)
        self.assertEqual(pet.hide_calls, 0)

    def test_apply_pet_visibility_keeps_hidden_care_pet_hidden(self):
        pet = FakePet(under_care=True, care_lock_mode="hidden")
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 123.0)

        actions.apply_pet_visibility(pet, True)

        self.assertTrue(pet.user_visible)
        self.assertEqual(pet.show_calls, 0)
        self.assertEqual(pet.hide_calls, 0)

    def test_apply_pet_visibility_hides_pet_when_unchecked(self):
        pet = FakePet()
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 0.0)

        actions.apply_pet_visibility(pet, False)

        self.assertFalse(pet.user_visible)
        self.assertEqual(pet.hide_calls, 1)

    def test_unsummon_interrupts_active_activity_before_hiding(self):
        pet = FakePet()
        pet.activity_locked = True
        actions = DashboardActions(sim_clock=FakeClock(), now_provider=lambda: 0.0)

        actions.apply_pet_visibility(pet, False)

        self.assertEqual(pet.activity_interrupt_calls, ["user_unsummon"])
        self.assertEqual(pet.hide_calls, 1)


if __name__ == "__main__":
    unittest.main()
