from __future__ import annotations

from dataclasses import dataclass


SIRIUS_SYMBOLI_NAME = "Sirius Symboli"


@dataclass(frozen=True)
class SleepingCaregiverCandidate:
    name: str
    available: bool
    distance_to_child: float
    shallow_sleeper: bool = False


@dataclass(frozen=True)
class SleepCareWakeDecision:
    should_wake: bool
    caregiver_name: str = ""
    reason: str = ""


def choose_sleeping_caregiver_to_wake(
    candidates,
    *,
    distressed_child_name: str,
    awake_or_responding_caregiver_available: bool,
) -> SleepCareWakeDecision:
    if not str(distressed_child_name or "").strip():
        return SleepCareWakeDecision(False, reason="missing_child")
    if awake_or_responding_caregiver_available:
        return SleepCareWakeDecision(
            False,
            reason="awake_caregiver_available",
        )
    eligible = [candidate for candidate in candidates if candidate.available]
    if not eligible:
        return SleepCareWakeDecision(
            False,
            reason="sleeping_caregiver_unavailable",
        )
    eligible.sort(
        key=lambda candidate: (
            not bool(candidate.shallow_sleeper),
            max(0.0, float(candidate.distance_to_child)),
            str(candidate.name or ""),
        )
    )
    selected = eligible[0]
    return SleepCareWakeDecision(
        True,
        caregiver_name=selected.name,
        reason=(
            "shallow_sleeper_priority"
            if selected.shallow_sleeper
            else "nearest_sleeping_caregiver"
        ),
    )
