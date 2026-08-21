from .activity_rhythm import (
    ActivityRhythmSnapshot,
    CharacterRhythmSnapshot,
    clamp_percent,
)
from .runtime import app_now
from .sleep_rules import SLEEP_ACTIVITY_KIND
from .transformation_profiles import get_transformation_profile


class ActivityRhythmProvider:
    """Builds the dashboard's read-only life-rhythm snapshot."""

    def __init__(
        self,
        *,
        activity_coordinator,
        race_executor,
        chorus_executor,
        sleep_executor,
        pets,
        now_provider=app_now,
    ):
        self.activity_coordinator = activity_coordinator
        self.race_executor = race_executor
        self.chorus_executor = chorus_executor
        self.sleep_executor = sleep_executor
        self.pets = pets
        self.now_provider = now_provider

    def snapshot(self, *, now=None):
        now = self.now_provider() if now is None else float(now)
        active_race = next(
            (
                activity
                for activity in self.activity_coordinator.get_active_activities()
                if activity.spec.kind == "race"
            ),
            None,
        )
        race_schedule = self.race_executor.schedule
        if active_race is not None:
            race_status = "active"
            race_remaining = None
            race_wait_reason = active_race.phase.name
        elif race_schedule.next_proposal_at > 0.0:
            race_remaining = max(
                0.0,
                float(race_schedule.next_proposal_at) - now,
            )
            race_status = "cooldown" if race_remaining > 0.0 else "ready"
            race_wait_reason = str(race_schedule.last_wait_reason or "")
        else:
            race_status = "unscheduled"
            race_remaining = None
            race_wait_reason = ""

        active_chorus = next(
            (
                activity
                for activity in self.activity_coordinator.get_active_activities()
                if activity.spec.kind == "chorus"
            ),
            None,
        )
        chorus_schedule = self.chorus_executor.schedule
        if active_chorus is not None:
            chorus_status = "active"
            chorus_remaining = None
            chorus_wait_reason = active_chorus.phase.name
        elif chorus_schedule.next_proposal_at > 0.0:
            chorus_remaining = max(
                0.0,
                float(chorus_schedule.next_proposal_at) - now,
            )
            chorus_status = (
                "cooldown" if chorus_remaining > 0.0 else "ready"
            )
            chorus_wait_reason = str(
                chorus_schedule.last_wait_reason or ""
            )
        else:
            chorus_status = "unscheduled"
            chorus_remaining = None
            chorus_wait_reason = ""

        members = []
        for pet in self.pets:
            name = str(getattr(pet, "name", "") or "").strip()
            if not name:
                continue
            summoned = bool(getattr(pet, "user_visible", False))
            activity = self.activity_coordinator.get_activity_for_participant(
                name
            )
            if activity is not None and activity.spec.kind == SLEEP_ACTIVITY_KIND:
                sleep_status = str(activity.phase.name or "sleeping")
                sleepiness = 100.0
            elif not summoned:
                sleep_status = "standby"
                sleepiness = None
            else:
                schedule = self.sleep_executor.schedules.get(name)
                sleep_status = "awake"
                if schedule is None or schedule.awake_since < 0.0:
                    sleepiness = None
                elif schedule.next_proposal_at <= now:
                    sleepiness = 100.0
                else:
                    sleepiness = clamp_percent(
                        (now - float(schedule.awake_since))
                        / max(
                            1.0,
                            float(schedule.next_proposal_at)
                            - float(schedule.awake_since),
                        )
                        * 100.0
                    )

            profile = get_transformation_profile(name)
            state = getattr(pet, "transformation_state", None)
            transform_remaining = None
            if profile is None or state is None:
                transform_status = "unavailable"
            elif state.active:
                transform_status = "transition"
            elif str(state.current_form or "base") == "transformed":
                transform_status = "transformed"
                if state.auto_form_expires_at > 0.0:
                    transform_remaining = max(
                        0.0,
                        float(state.auto_form_expires_at) - now,
                    )
            elif state.auto_retry_at > now:
                transform_status = "waiting"
                transform_remaining = max(
                    0.0,
                    float(state.auto_retry_at) - now,
                )
            elif state.auto_next_attempt_at > 0.0:
                transform_status = "cooldown"
                transform_remaining = max(
                    0.0,
                    float(state.auto_next_attempt_at) - now,
                )
            else:
                transform_status = "ready"

            members.append(
                CharacterRhythmSnapshot(
                    character_name=name,
                    summoned=summoned,
                    sleep_status=sleep_status,
                    sleepiness_percent=sleepiness,
                    transformation_status=transform_status,
                    transformation_remaining_seconds=transform_remaining,
                )
            )
        return ActivityRhythmSnapshot(
            observed_at=now,
            race_status=race_status,
            race_remaining_seconds=race_remaining,
            race_wait_reason=race_wait_reason,
            chorus_status=chorus_status,
            chorus_remaining_seconds=chorus_remaining,
            chorus_wait_reason=chorus_wait_reason,
            members=tuple(members),
        )
