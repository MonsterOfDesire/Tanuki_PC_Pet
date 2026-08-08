from __future__ import annotations

from dataclasses import dataclass, field


RACE_EXECUTION_AUTONOMOUS = "autonomous"
RACE_EXECUTION_NORMAL = RACE_EXECUTION_AUTONOMOUS
RACE_EXECUTION_SANDBOX_PREVIEW = "sandbox_preview"


@dataclass
class RaceScheduleState:
    next_proposal_at: float = 0.0
    last_finished_at: float = 0.0
    world_mode: str = ""
    frequency_key: str = ""
    last_wait_reason: str = ""


@dataclass(frozen=True)
class RaceLaneGeometry:
    challenger_start_x: float
    opponent_start_x: float
    finish_x: float
    direction: int = 1
    distance: float = 0.0


@dataclass(frozen=True)
class RacePerformanceDecision:
    winner_name: str
    challenger_speed: float
    opponent_speed: float


@dataclass(frozen=True)
class RacePlan:
    challenger_name: str
    opponent_name: str
    accepted: bool
    winner_name: str = ""
    challenger_speed: float = 0.0
    opponent_speed: float = 0.0
    execution_mode: str = RACE_EXECUTION_NORMAL
    source: str = "runtime"
    world_mode: str = "golden_legend"

    @property
    def participant_names(self) -> tuple[str, str]:
        return self.challenger_name, self.opponent_name

    @property
    def loser_name(self) -> str:
        if not self.accepted or not self.winner_name:
            return ""
        return (
            self.opponent_name
            if self.winner_name == self.challenger_name
            else self.challenger_name
        )


@dataclass(frozen=True)
class RaceEvent:
    event_type: str
    occurred_at: float
    challenger_name: str
    opponent_name: str
    winner_name: str = ""
    loser_name: str = ""
    source: str = "runtime"
    activity_id: str = ""
    challenger_form: str = "base"
    opponent_form: str = "base"
    execution_mode: str = RACE_EXECUTION_AUTONOMOUS
    world_mode: str = "golden_legend"
    race_distance: float = 0.0
    race_direction: int = 1
    running_started_at: float = 0.0
    winner_arrived_at: float = 0.0
    race_elapsed_seconds: float = 0.0


@dataclass
class RaceCharacterStatistics:
    character_name: str
    completed_races: int = 0
    wins: int = 0
    losses: int = 0
    golden_races: int = 0
    sandbox_races: int = 0
    autonomous_races: int = 0
    manual_races: int = 0

    @property
    def win_rate(self) -> float:
        if self.completed_races <= 0:
            return 0.0
        return (float(self.wins) / float(self.completed_races)) * 100.0


@dataclass
class RaceStatisticsLedger:
    entries: dict[str, RaceCharacterStatistics] = field(default_factory=dict)
    processed_activity_ids: set[str] = field(default_factory=set)

    def clear(self) -> None:
        self.entries.clear()
        self.processed_activity_ids.clear()

    def get_entry(self, character_name: str) -> RaceCharacterStatistics:
        name = str(character_name or "").strip()
        entry = self.entries.get(name)
        if entry is None:
            entry = RaceCharacterStatistics(character_name=name)
            self.entries[name] = entry
        return entry

    def record_completed(self, event: RaceEvent) -> bool:
        activity_id = str(event.activity_id or "").strip()
        if (
            event.event_type != "race_completed"
            or not activity_id
            or activity_id in self.processed_activity_ids
            or not event.winner_name
            or not event.loser_name
            or event.execution_mode == RACE_EXECUTION_SANDBOX_PREVIEW
        ):
            return False
        self.processed_activity_ids.add(activity_id)
        for name, won in (
            (event.winner_name, True),
            (event.loser_name, False),
        ):
            entry = self.get_entry(name)
            entry.completed_races += 1
            entry.wins += int(won)
            entry.losses += int(not won)
            if event.world_mode == "sandbox":
                entry.sandbox_races += 1
            else:
                entry.golden_races += 1
            if event.execution_mode == RACE_EXECUTION_AUTONOMOUS:
                entry.autonomous_races += 1
            else:
                entry.manual_races += 1
        return True


@dataclass(frozen=True)
class RaceRuntimeResult:
    handled: bool
    reason: str = ""
    activity_id: str = ""
    started: bool = False
    phase_changed: bool = False
    finished: bool = False
    interrupted: bool = False
    accepted: bool | None = None
    winner_name: str = ""
