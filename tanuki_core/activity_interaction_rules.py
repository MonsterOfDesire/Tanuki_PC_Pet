from __future__ import annotations


CHORUS_SLEEP_WAKE_DISTANCE_PX = 800.0
CHORUS_SLEEP_WAKE_BAND = "low"
CHORUS_SLEEP_WAKE_AFTERGLOW_SECONDS = 8.0


def should_chorus_wake_sleeping_pet(
    *,
    distance: float,
    performer_phase: str,
    sleeper_phase: str,
) -> bool:
    return bool(
        str(performer_phase or "") == "performing"
        and str(sleeper_phase or "") == "sleeping"
        and max(0.0, float(distance))
        <= CHORUS_SLEEP_WAKE_DISTANCE_PX
    )
