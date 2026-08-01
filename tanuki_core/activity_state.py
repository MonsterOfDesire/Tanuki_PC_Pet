from __future__ import annotations

from dataclasses import dataclass, field


ACTIVITY_EVENT_SCHEMA_VERSION = 1

COLLISION_POLICY_NORMAL = "normal"
COLLISION_POLICY_IGNORE = "ignore"
COLLISION_POLICY_BLOCK = "block"
VALID_COLLISION_POLICIES = frozenset(
    {
        COLLISION_POLICY_NORMAL,
        COLLISION_POLICY_IGNORE,
        COLLISION_POLICY_BLOCK,
    }
)

INTERRUPT_POLICY_ALLOW = "allow"
INTERRUPT_POLICY_FORCE_ONLY = "force_only"
VALID_INTERRUPT_POLICIES = frozenset(
    {
        INTERRUPT_POLICY_ALLOW,
        INTERRUPT_POLICY_FORCE_ONLY,
    }
)


def _normalize_unique_strings(values) -> tuple[str, ...]:
    normalized = []
    for value in values or ():
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return tuple(normalized)


@dataclass(frozen=True)
class ActivityPhaseSpec:
    name: str
    duration_seconds: float
    blocked_operations: frozenset[str] | None = None
    collision_policy: str | None = None
    interrupt_policy: str | None = None

    def __post_init__(self):
        name = str(self.name or "").strip()
        duration_seconds = float(self.duration_seconds)
        if not name:
            raise ValueError("activity phase requires a name")
        if duration_seconds <= 0.0:
            raise ValueError("activity phase duration must be positive")
        if (
            self.collision_policy is not None
            and self.collision_policy not in VALID_COLLISION_POLICIES
        ):
            raise ValueError(
                f"unknown activity collision policy: {self.collision_policy}"
            )
        if (
            self.interrupt_policy is not None
            and self.interrupt_policy not in VALID_INTERRUPT_POLICIES
        ):
            raise ValueError(
                f"unknown activity interrupt policy: {self.interrupt_policy}"
            )
        blocked_operations = self.blocked_operations
        if blocked_operations is not None:
            blocked_operations = frozenset(
                _normalize_unique_strings(blocked_operations)
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "duration_seconds", duration_seconds)
        object.__setattr__(self, "blocked_operations", blocked_operations)


@dataclass(frozen=True)
class ActivitySpec:
    kind: str
    phases: tuple[ActivityPhaseSpec, ...]
    blocked_operations: frozenset[str] = frozenset()
    collision_policy: str = COLLISION_POLICY_NORMAL
    interrupt_policy: str = INTERRUPT_POLICY_ALLOW

    def __post_init__(self):
        kind = str(self.kind or "").strip()
        phases = tuple(self.phases or ())
        if not kind:
            raise ValueError("activity spec requires a kind")
        if not phases:
            raise ValueError("activity spec requires at least one phase")
        phase_names = tuple(phase.name for phase in phases)
        if len(set(phase_names)) != len(phase_names):
            raise ValueError("activity phase names must be unique")
        if self.collision_policy not in VALID_COLLISION_POLICIES:
            raise ValueError(
                f"unknown activity collision policy: {self.collision_policy}"
            )
        if self.interrupt_policy not in VALID_INTERRUPT_POLICIES:
            raise ValueError(
                f"unknown activity interrupt policy: {self.interrupt_policy}"
            )
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "phases", phases)
        object.__setattr__(
            self,
            "blocked_operations",
            frozenset(_normalize_unique_strings(self.blocked_operations)),
        )

    @property
    def duration_seconds(self) -> float:
        return sum(phase.duration_seconds for phase in self.phases)


@dataclass(frozen=True)
class ActivityParticipant:
    name: str
    role: str

    def __post_init__(self):
        name = str(self.name or "").strip()
        role = str(self.role or "").strip()
        if not name:
            raise ValueError("activity participant requires a name")
        if not role:
            raise ValueError("activity participant requires a role")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "role", role)


@dataclass(frozen=True)
class ActivityParticipantSnapshot:
    participant: ActivityParticipant
    visible: bool = True
    enabled: bool = True
    active_activity_id: str = ""
    busy_reasons: tuple[str, ...] = ()
    capability_ready: bool = True
    capability_reason: str = ""

    def __post_init__(self):
        object.__setattr__(
            self,
            "active_activity_id",
            str(self.active_activity_id or "").strip(),
        )
        object.__setattr__(
            self,
            "busy_reasons",
            _normalize_unique_strings(self.busy_reasons),
        )
        object.__setattr__(
            self,
            "capability_reason",
            str(self.capability_reason or "").strip(),
        )


@dataclass(frozen=True)
class ResolvedActivityPolicy:
    blocked_operations: frozenset[str]
    collision_policy: str
    interrupt_policy: str


@dataclass
class PetActivityState:
    activity_id: str = ""
    activity_kind: str = "none"
    owner_name: str = ""
    participant_role: str = ""
    phase: str = "none"
    started_at: float = 0.0
    phase_started_at: float = 0.0
    phase_ends_at: float = 0.0
    deadline_at: float = 0.0
    blocked_operations: frozenset[str] = frozenset()
    collision_policy: str = COLLISION_POLICY_NORMAL
    interrupt_policy: str = INTERRUPT_POLICY_ALLOW

    @property
    def active(self) -> bool:
        return bool(self.activity_id and self.activity_kind != "none")

    def clear(self, *, expected_activity_id: str | None = None) -> bool:
        if (
            expected_activity_id is not None
            and self.activity_id != str(expected_activity_id)
        ):
            return False
        if not self.active:
            return False
        self.activity_id = ""
        self.activity_kind = "none"
        self.owner_name = ""
        self.participant_role = ""
        self.phase = "none"
        self.started_at = 0.0
        self.phase_started_at = 0.0
        self.phase_ends_at = 0.0
        self.deadline_at = 0.0
        self.blocked_operations = frozenset()
        self.collision_policy = COLLISION_POLICY_NORMAL
        self.interrupt_policy = INTERRUPT_POLICY_ALLOW
        return True


@dataclass
class ActiveActivity:
    activity_id: str
    spec: ActivitySpec
    owner_name: str
    participants: tuple[ActivityParticipant, ...]
    source: str
    started_at: float
    phase_index: int
    phase_started_at: float
    phase_ends_at: float
    deadline_at: float
    result_committed: bool = False
    committed_result: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def phase(self) -> ActivityPhaseSpec:
        return self.spec.phases[self.phase_index]


@dataclass(frozen=True)
class ActivityDomainEvent:
    event_name: str
    event_id: str
    activity_id: str
    activity_kind: str
    owner_name: str
    participants: tuple[ActivityParticipant, ...]
    phase: str
    occurred_at: float
    started_at: float
    source: str
    reason: str = ""
    result: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)
    schema_version: int = ACTIVITY_EVENT_SCHEMA_VERSION

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "event_name": self.event_name,
            "event_id": self.event_id,
            "activity_id": self.activity_id,
            "activity_kind": self.activity_kind,
            "owner_name": self.owner_name,
            "participants": [
                {
                    "name": participant.name,
                    "role": participant.role,
                }
                for participant in self.participants
            ],
            "phase": self.phase,
            "occurred_at": self.occurred_at,
            "started_at": self.started_at,
            "elapsed_seconds": max(0.0, self.occurred_at - self.started_at),
            "source": self.source,
            "reason": self.reason,
            "result": dict(self.result),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ActivityStateProjection:
    participant_name: str
    state: PetActivityState
