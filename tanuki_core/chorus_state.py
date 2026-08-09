from __future__ import annotations

from dataclasses import dataclass, field


CHORUS_REACTION_PERFORM = "perform"
CHORUS_REACTION_AUDIENCE = "audience"


@dataclass
class ChorusScheduleState:
    next_proposal_at: float = 0.0
    last_finished_at: float = 0.0
    world_mode: str = ""
    frequency_key: str = ""
    last_wait_reason: str = ""


@dataclass
class ChorusParticipantState:
    name: str
    reaction: str
    activity_id: str
    phase: str
    slot: int
    joined_at: float
    approach_deadline_at: float = 0.0

    @property
    def is_performer(self) -> bool:
        return self.reaction == CHORUS_REACTION_PERFORM


@dataclass
class ChorusSessionState:
    session_id: str
    source: str
    world_mode: str
    started_at: float
    ends_at: float
    center_x: float
    participants: dict[str, ChorusParticipantState] = field(
        default_factory=dict
    )
    considered_names: set[str] = field(default_factory=set)
    participant_roles: dict[str, str] = field(default_factory=dict)
    next_consider_at: float = 0.0
    next_performer_slot_ordinal: int = 1
    next_audience_slot_ordinal: int = 1
    finishing: bool = False
    finish_ends_at: float = 0.0

    @property
    def performer_count(self) -> int:
        return sum(
            participant.is_performer
            for participant in self.participants.values()
        )

    @property
    def audience_count(self) -> int:
        return sum(
            not participant.is_performer
            for participant in self.participants.values()
        )


@dataclass(frozen=True)
class ChorusEvent:
    session_id: str
    event_type: str
    occurred_at: float
    started_at: float
    source: str
    world_mode: str
    participant_roles: tuple[tuple[str, str], ...]
    outcome: str
    reason: str = ""

    @property
    def performer_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, role in self.participant_roles
            if role == CHORUS_REACTION_PERFORM
        )

    @property
    def audience_names(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, role in self.participant_roles
            if role == CHORUS_REACTION_AUDIENCE
        )

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, float(self.occurred_at) - float(self.started_at))
