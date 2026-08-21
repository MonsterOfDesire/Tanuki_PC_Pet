from .runtime import SIM_CLOCK, app_now


class DashboardActions:
    def __init__(self, sim_clock=None, now_provider=None):
        self.sim_clock = sim_clock or SIM_CLOCK
        self.now_provider = now_provider or app_now

    def apply_time_scale(self, scale):
        self.sim_clock.set_speed(float(scale))

    def apply_display_scale(self, pets_dict, multiplier):
        for info in pets_dict.values():
            pet = info.get("pet")
            if pet:
                pet.apply_display_scale(multiplier)

    def apply_social_cooldowns(self, pets_dict, teio_seconds, tsuyoshi_seconds):
        teio = pets_dict.get("Tokai Teio", {}).get("pet")
        tsuyoshi = pets_dict.get("Tsurumaru Tsuyoshi", {}).get("pet")
        if teio:
            teio.social_cooldown_duration = float(teio_seconds)
        if tsuyoshi:
            tsuyoshi.social_cooldown_duration = float(tsuyoshi_seconds)

    def apply_pet_visibility(self, pet, checked):
        if not checked:
            interrupt_provider = getattr(
                pet,
                "activity_user_interrupt_provider",
                None,
            )
            is_activity_locked = getattr(pet, "is_activity_locked", None)
            if (
                callable(interrupt_provider)
                and callable(is_activity_locked)
                and bool(is_activity_locked())
            ):
                interrupt_provider(pet, reason="user_unsummon")
        pet.user_visible = bool(checked)
        if checked:
            if not (pet.care_lock_mode == "hidden" and pet.is_under_care(self.now_provider())):
                pet.show()
            return
        pet.hide()
