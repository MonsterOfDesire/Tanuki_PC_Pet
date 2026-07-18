import time
from dataclasses import dataclass, field


DEFAULT_LIVING_FUND = 1000
DEFAULT_HOUSEHOLD_PRESSURE = 0.0
DEFAULT_HOUSEHOLD_EVENT_LOG_CAPACITY = 128
MAX_HOUSEHOLD_PRESSURE = 100.0
PLAYER_DONATE_PRESSURE_RELIEF = -4.0
DEFAULT_EVENT_CHANNEL = "story"
DEFAULT_EVENT_IMPORTANCE = "normal"
RELATIONSHIP_METRIC_NAMES = ("familiarity", "trust", "attachment", "tension")

ECONOMY_EVENT_CATEGORIES = frozenset({"economy", "player_help"})
ITEM_EVENT_CATEGORIES = frozenset({"player_offer", "item"})
SOCIAL_EVENT_CATEGORIES = frozenset({"social", "relationship", "care"})
SYSTEM_EVENT_CATEGORIES = frozenset({"system", "debug"})


def clamp_household_pressure(value: float) -> float:
    return max(0.0, min(MAX_HOUSEHOLD_PRESSURE, value))


def clamp_relationship_metric(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def normalize_event_tags(tags) -> tuple[str, ...]:
    if not tags:
        return ()
    raw_tags = (tags,) if isinstance(tags, str) else tags
    try:
        iterator = iter(raw_tags)
    except TypeError:
        return ()
    normalized = []
    for tag in iterator:
        text = str(tag).strip()
        if text:
            normalized.append(text)
    return tuple(dict.fromkeys(normalized))


def normalize_relation_delta(relation_delta) -> dict[str, float]:
    if not isinstance(relation_delta, dict):
        return {}
    normalized = {}
    for metric_name in RELATIONSHIP_METRIC_NAMES:
        if metric_name not in relation_delta:
            continue
        try:
            normalized[metric_name] = float(relation_delta[metric_name])
        except (TypeError, ValueError):
            continue
    return normalized


def resolve_event_channel(channel: str = "", category: str = "") -> str:
    channel_text = str(channel or "").strip()
    if channel_text:
        return channel_text
    category_text = str(category or "").strip()
    if category_text in ECONOMY_EVENT_CATEGORIES:
        return "economy"
    if category_text in ITEM_EVENT_CATEGORIES:
        return "item"
    if category_text in SOCIAL_EVENT_CATEGORIES:
        return "social"
    if category_text in SYSTEM_EVENT_CATEGORIES:
        return "system"
    return DEFAULT_EVENT_CHANNEL


@dataclass
class HouseholdRelationshipEntry:
    actor_name: str
    target_name: str
    familiarity: float = 0.0
    trust: float = 0.0
    attachment: float = 0.0
    tension: float = 0.0
    updated_at: float = 0.0
    event_count: int = 0

    def clamp_metrics(self) -> None:
        self.familiarity = clamp_relationship_metric(self.familiarity)
        self.trust = clamp_relationship_metric(self.trust)
        self.attachment = clamp_relationship_metric(self.attachment)
        self.tension = clamp_relationship_metric(self.tension)


@dataclass
class HouseholdRelationshipLedger:
    entries: dict[tuple[str, str], HouseholdRelationshipEntry] = field(default_factory=dict)

    def clear(self) -> None:
        self.entries.clear()

    def get_entry(self, actor_name: str, target_name: str) -> HouseholdRelationshipEntry | None:
        return self.entries.get((str(actor_name).strip(), str(target_name).strip()))

    def upsert_entry(self, entry: HouseholdRelationshipEntry) -> HouseholdRelationshipEntry | None:
        actor_name = str(entry.actor_name).strip()
        target_name = str(entry.target_name).strip()
        if not actor_name or not target_name:
            return None
        stored = HouseholdRelationshipEntry(
            actor_name=actor_name,
            target_name=target_name,
            familiarity=entry.familiarity,
            trust=entry.trust,
            attachment=entry.attachment,
            tension=entry.tension,
            updated_at=float(entry.updated_at),
            event_count=max(0, int(entry.event_count)),
        )
        stored.clamp_metrics()
        self.entries[(actor_name, target_name)] = stored
        return stored

    def apply_delta(
        self,
        *,
        actor_name: str,
        target_name: str,
        relation_delta: dict[str, float],
        updated_at: float = 0.0,
    ) -> HouseholdRelationshipEntry | None:
        actor_name = str(actor_name).strip()
        target_name = str(target_name).strip()
        if not actor_name or not target_name:
            return None
        delta = normalize_relation_delta(relation_delta)
        if not delta:
            return None
        entry = self.entries.get((actor_name, target_name))
        if entry is None:
            entry = HouseholdRelationshipEntry(actor_name=actor_name, target_name=target_name)
            self.entries[(actor_name, target_name)] = entry

        entry.familiarity = clamp_relationship_metric(entry.familiarity + delta.get("familiarity", 0.0))
        entry.trust = clamp_relationship_metric(entry.trust + delta.get("trust", 0.0))
        entry.attachment = clamp_relationship_metric(entry.attachment + delta.get("attachment", 0.0))
        entry.tension = clamp_relationship_metric(entry.tension + delta.get("tension", 0.0))
        entry.updated_at = float(updated_at)
        entry.event_count += 1
        return entry

    def entries_for_actor(self, actor_name: str) -> list[HouseholdRelationshipEntry]:
        actor_name = str(actor_name).strip()
        return sorted(
            (entry for entry in self.entries.values() if entry.actor_name == actor_name),
            key=lambda entry: entry.target_name,
        )

    def all_entries(self) -> list[HouseholdRelationshipEntry]:
        return sorted(self.entries.values(), key=lambda entry: (entry.actor_name, entry.target_name))


@dataclass
class HouseholdState:
    living_fund: int = DEFAULT_LIVING_FUND
    household_pressure: float = DEFAULT_HOUSEHOLD_PRESSURE
    relationships: HouseholdRelationshipLedger = field(default_factory=HouseholdRelationshipLedger)

    def apply_delta(
        self,
        *,
        living_fund_delta: int = 0,
        household_pressure_delta: float = 0.0,
    ) -> None:
        self.living_fund = max(0, self.living_fund + living_fund_delta)
        self.household_pressure = clamp_household_pressure(
            self.household_pressure + household_pressure_delta
        )


@dataclass(frozen=True)
class HouseholdEventLogEntry:
    sequence: int
    occurred_at: float
    wall_clock_time: float = 0.0
    category: str = "system"
    event_type: str = "info"
    channel: str = DEFAULT_EVENT_CHANNEL
    importance: str = DEFAULT_EVENT_IMPORTANCE
    summary: str = ""
    actor_name: str = ""
    target_name: str = ""
    mood_delta: float = 0.0
    relation_delta: dict[str, float] = field(default_factory=dict)
    tags: tuple[str, ...] = field(default_factory=tuple)
    living_fund_delta: int = 0
    household_pressure_delta: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class HouseholdEventLog:
    max_entries: int = DEFAULT_HOUSEHOLD_EVENT_LOG_CAPACITY
    entries: list[HouseholdEventLogEntry] = field(default_factory=list)
    next_sequence: int = 1

    def append(self, entry: HouseholdEventLogEntry) -> HouseholdEventLogEntry:
        self.entries.append(entry)
        overflow = len(self.entries) - self.max_entries
        if overflow > 0:
            del self.entries[:overflow]
        self.next_sequence = max(self.next_sequence, entry.sequence + 1)
        return entry

    def create_entry(
        self,
        *,
        occurred_at: float,
        wall_clock_time: float | None = None,
        category: str = "system",
        event_type: str = "info",
        channel: str = "",
        importance: str = DEFAULT_EVENT_IMPORTANCE,
        summary: str = "",
        actor_name: str = "",
        target_name: str = "",
        mood_delta: float = 0.0,
        relation_delta: dict[str, float] | None = None,
        tags=(),
        living_fund_delta: int = 0,
        household_pressure_delta: float = 0.0,
        metadata: dict[str, object] | None = None,
    ) -> HouseholdEventLogEntry:
        return HouseholdEventLogEntry(
            sequence=self.next_sequence,
            occurred_at=occurred_at,
            wall_clock_time=time.time() if wall_clock_time is None else float(wall_clock_time),
            category=category,
            event_type=event_type,
            channel=resolve_event_channel(channel, category),
            importance=str(importance or DEFAULT_EVENT_IMPORTANCE).strip() or DEFAULT_EVENT_IMPORTANCE,
            summary=summary,
            actor_name=actor_name,
            target_name=target_name,
            mood_delta=float(mood_delta),
            relation_delta=normalize_relation_delta(relation_delta),
            tags=normalize_event_tags(tags),
            living_fund_delta=living_fund_delta,
            household_pressure_delta=household_pressure_delta,
            metadata=dict(metadata or {}),
        )

    def recent_entries(self, limit: int | None = None) -> list[HouseholdEventLogEntry]:
        if limit is None or limit >= len(self.entries):
            return list(self.entries)
        return list(self.entries[-limit:])

    def query_entries(
        self,
        *,
        limit: int | None = None,
        channel: str = "",
        category: str = "",
        event_type: str = "",
        actor_name: str = "",
        target_name: str = "",
        participant_name: str = "",
        tags=(),
    ) -> list[HouseholdEventLogEntry]:
        channel = str(channel or "").strip()
        category = str(category or "").strip()
        event_type = str(event_type or "").strip()
        actor_name = str(actor_name or "").strip()
        target_name = str(target_name or "").strip()
        participant_name = str(participant_name or "").strip()
        required_tags = set(normalize_event_tags(tags))

        results = []
        for entry in self.entries:
            if channel and entry.channel != channel:
                continue
            if category and entry.category != category:
                continue
            if event_type and entry.event_type != event_type:
                continue
            if actor_name and entry.actor_name != actor_name:
                continue
            if target_name and entry.target_name != target_name:
                continue
            if participant_name and participant_name not in {entry.actor_name, entry.target_name}:
                continue
            if required_tags and not required_tags.issubset(set(entry.tags)):
                continue
            results.append(entry)
        if limit is None or limit >= len(results):
            return list(results)
        return list(results[-limit:])


def build_default_household_state() -> HouseholdState:
    return HouseholdState()


def build_default_household_event_log() -> HouseholdEventLog:
    return HouseholdEventLog()


def seed_default_household_events(
    household: HouseholdState,
    event_log: HouseholdEventLog,
    *,
    occurred_at: float,
) -> list[HouseholdEventLogEntry]:
    return [
        record_household_event(
            household,
            event_log,
            occurred_at=occurred_at,
            category="household",
            event_type="opening_note",
            summary="魯道夫一家開始今天的桌面生活。",
            apply_deltas=False,
        ),
        record_household_event(
            household,
            event_log,
            occurred_at=occurred_at,
            category="economy",
            event_type="fund_snapshot",
            summary=f"目前生活費為 {household.living_fund} 元。",
            apply_deltas=False,
        ),
        record_household_event(
            household,
            event_log,
            occurred_at=occurred_at,
            category="household",
            event_type="pressure_snapshot",
            summary=f"家庭壓力目前為 {int(round(household.household_pressure))}%。",
            apply_deltas=False,
        ),
    ]


def record_household_event(
    household: HouseholdState,
    event_log: HouseholdEventLog,
    *,
    occurred_at: float,
    wall_clock_time: float | None = None,
    category: str = "system",
    event_type: str = "info",
    channel: str = "",
    importance: str = DEFAULT_EVENT_IMPORTANCE,
    summary: str = "",
    actor_name: str = "",
    target_name: str = "",
    mood_delta: float = 0.0,
    relation_delta: dict[str, float] | None = None,
    tags=(),
    living_fund_delta: int = 0,
    household_pressure_delta: float = 0.0,
    metadata: dict[str, object] | None = None,
    apply_deltas: bool = True,
) -> HouseholdEventLogEntry:
    entry = event_log.create_entry(
        occurred_at=occurred_at,
        wall_clock_time=wall_clock_time,
        category=category,
        event_type=event_type,
        channel=channel,
        importance=importance,
        summary=summary,
        actor_name=actor_name,
        target_name=target_name,
        mood_delta=mood_delta,
        relation_delta=relation_delta,
        tags=tags,
        living_fund_delta=living_fund_delta,
        household_pressure_delta=household_pressure_delta,
        metadata=metadata,
    )
    if apply_deltas:
        household.apply_delta(
            living_fund_delta=living_fund_delta,
            household_pressure_delta=household_pressure_delta,
        )
        household.relationships.apply_delta(
            actor_name=actor_name,
            target_name=target_name,
            relation_delta=entry.relation_delta,
            updated_at=occurred_at,
        )
    return event_log.append(entry)


def record_player_donate_household_fund(
    household: HouseholdState,
    event_log: HouseholdEventLog,
    *,
    occurred_at: float,
    wall_clock_time: float | None = None,
    amount: int,
    actor_name: str = "Player",
    summary: str | None = None,
) -> HouseholdEventLogEntry:
    amount = max(0, int(amount))
    summary = summary or f"玩家捐助了 {amount} 元生活費。"
    pressure_delta = PLAYER_DONATE_PRESSURE_RELIEF if amount > 0 else 0.0
    return record_household_event(
        household,
        event_log,
        occurred_at=occurred_at,
        wall_clock_time=wall_clock_time,
        category="player_help",
        event_type="player_donate_fund",
        summary=summary,
        actor_name=actor_name,
        living_fund_delta=amount,
        household_pressure_delta=pressure_delta,
        metadata={"source": "dashboard_player_action"},
    )
