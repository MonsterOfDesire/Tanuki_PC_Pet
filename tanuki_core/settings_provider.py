from dataclasses import dataclass

from .ui_localization import DEFAULT_UI_LOCALE, SUPPORTED_UI_LOCALES


@dataclass
class RuntimeSettings:
    world_mode: str = "golden_legend"
    care_feature_enabled: bool = True
    debug_enabled: bool = False
    social_status_enabled: bool = False
    teio_dur_idx: int = 3
    tsuyoshi_dur_idx: int = 2
    time_scale_idx: int = 0
    display_scale_idx: int = 0
    race_frequency: str = "normal"
    chorus_frequency: str = "normal"
    mood_climate: str = "cheerful"
    ui_locale: str = DEFAULT_UI_LOCALE

    WORLD_MODE_OPTIONS = ("golden_legend", "sandbox")
    TIME_SCALE_OPTIONS = (1, 2, 4, 8)
    DISPLAY_SCALE_OPTIONS = (1.0, 1.5, 2.0, 3.0)
    TEIO_DURATIONS = (2, 5, 10, 20, 30)
    TSUYOSHI_DURATIONS = (2, 10, 20, 40, 60)
    RACE_FREQUENCY_OPTIONS = ("frequent", "normal", "occasional")
    CHORUS_FREQUENCY_OPTIONS = ("frequent", "normal", "occasional")
    MOOD_CLIMATE_OPTIONS = ("cheerful", "balanced", "expressive")
    UI_LOCALE_OPTIONS = SUPPORTED_UI_LOCALES

    def get_time_scale(self):
        return float(self.TIME_SCALE_OPTIONS[int(self.time_scale_idx)])

    def get_display_scale_multiplier(self):
        return float(self.DISPLAY_SCALE_OPTIONS[int(self.display_scale_idx)])

    def get_social_cooldown_label_seconds(self, pet_name):
        if pet_name == "Tokai Teio":
            return self.TEIO_DURATIONS[int(self.teio_dur_idx)]
        if pet_name == "Tsurumaru Tsuyoshi":
            return self.TSUYOSHI_DURATIONS[int(self.tsuyoshi_dur_idx)]
        return 0

    def get_social_cooldown_seconds(self, pet_name):
        duration = self.get_social_cooldown_label_seconds(pet_name)
        return float(duration) if duration else 0.0
