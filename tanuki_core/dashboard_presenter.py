from datetime import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardStatusPresentation:
    status_text: str
    show_status: bool
    exit_enabled: bool
    exit_text: str
    force_expanded: bool


@dataclass(frozen=True)
class DashboardDialogPresentation:
    title: str
    message: str
    severity: str


@dataclass(frozen=True)
class DashboardButtonPresentation:
    text: str


@dataclass(frozen=True)
class HouseholdMemberPresentation:
    character_name: str
    summoned: bool
    mood_score: float | None
    mood_state: str
    mood_label: str
    form_key: str = "base"
    form_label: str = "普通形態"


@dataclass(frozen=True)
class HouseholdRecentEventPresentation:
    sequence: int
    timestamp_text: str
    channel: str
    channel_label: str
    summary: str
    delta_text: str


@dataclass(frozen=True)
class HouseholdSummaryPresentation:
    title: str
    overview_text: str
    log_text: str
    living_fund: int | None = None
    household_pressure: float | None = None
    members: tuple[HouseholdMemberPresentation, ...] = ()
    recent_events: tuple[HouseholdRecentEventPresentation, ...] = ()
    member_count: int = 0
    summoned_count: int = 0
    average_mood: float | None = None
    recent_event_count: int = 0
    recent_fund_delta: int = 0
    recent_pressure_delta: float = 0.0


@dataclass(frozen=True)
class SocialLogEffectPresentation:
    key: str
    label: str
    value: float
    value_text: str


@dataclass(frozen=True)
class SocialLogEntryPresentation:
    sequence: int
    timestamp_text: str
    channel: str
    channel_label: str
    category: str
    event_type: str
    importance: str
    summary: str
    actor_name: str
    target_name: str
    participant_text: str
    effects: tuple[SocialLogEffectPresentation, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class SocialLogPresentation:
    title: str
    filter_mode: str
    participant_name: str
    participant_names: tuple[str, ...]
    log_text: str
    entries: tuple[SocialLogEntryPresentation, ...] = ()


@dataclass(frozen=True)
class RelationshipRowPresentation:
    actor_name: str
    target_name: str
    affinity: float
    familiarity: float
    trust: float
    attachment: float
    tension: float
    event_count: int


@dataclass(frozen=True)
class RelationshipTablePresentation:
    title: str
    table_text: str
    actor_names: tuple[str, ...] = ()
    rows: tuple[RelationshipRowPresentation, ...] = ()


class DashboardPresenter:
    HOUSEHOLD_SUMMARY_EVENT_LIMIT = 24
    HOUSEHOLD_SUMMARY_VISIBLE_EVENT_LIMIT = 5
    HOUSEHOLD_SUMMARY_CHANNELS = {"economy", "item", "story", "system"}
    HOUSEHOLD_SUMMARY_CATEGORIES = {
        "household",
        "economy",
        "player_help",
        "player_offer",
        "item",
        "system",
    }
    SOCIAL_LOG_FILTER_LABELS = {
        "all": "全部",
        "personal": "個人",
        "social": "社交",
        "economy": "經濟",
        "item": "道具",
        "system": "系統",
    }
    SOCIAL_LOG_CHANNEL_LABELS = {
        "social": "社交",
        "economy": "經濟",
        "item": "道具",
        "story": "故事",
        "system": "系統",
    }
    RELATIONSHIP_METRIC_LABELS = {
        "familiarity": "熟悉",
        "trust": "信任",
        "attachment": "依附",
        "tension": "緊張",
    }
    MOOD_STATE_LABELS = {
        "normal": "平穩",
        "unhappy": "低落",
        "depressed": "非常低落",
    }
    FORM_LABELS = {
        "base": "普通形態",
        "transformed": "變身形態",
    }

    def build_shutdown_status(self):
        return DashboardStatusPresentation(
            status_text="正在儲存設定...",
            show_status=True,
            exit_enabled=False,
            exit_text="正在關閉...",
            force_expanded=True,
        )

    def build_debug_button(self, enabled):
        return DashboardButtonPresentation(text=f"Debug: {'開啟' if enabled else '關閉'}")

    def build_validation_dialog(self, result):
        title = "檢查結果（有警告）" if result.has_warnings else "檢查結果（正常）"
        return DashboardDialogPresentation(
            title=title,
            message=result.report,
            severity="warning" if result.has_warnings else "information",
        )

    def build_household_summary(self, household, entries, pet_states=()):
        members = self.build_household_member_presentations(pet_states)
        member_count = len(members)
        summoned_count = sum(1 for member in members if member.summoned)
        mood_scores = [
            member.mood_score
            for member in members
            if member.mood_score is not None
        ]
        average_mood = (
            sum(mood_scores) / len(mood_scores)
            if mood_scores else
            None
        )
        all_entries = list(entries or ())
        summary_entries = self.filter_household_summary_entries(all_entries)
        statistic_entries = all_entries[-self.HOUSEHOLD_SUMMARY_EVENT_LIMIT:]
        recent_events = tuple(
            self.build_household_recent_event_presentation(entry)
            for entry in reversed(
                all_entries[-self.HOUSEHOLD_SUMMARY_VISIBLE_EVENT_LIMIT:]
            )
        )
        recent_fund_delta = sum(
            int(getattr(entry, "living_fund_delta", 0) or 0)
            for entry in statistic_entries
        )
        recent_pressure_delta = sum(
            float(getattr(entry, "household_pressure_delta", 0.0) or 0.0)
            for entry in statistic_entries
        )
        summary_data = {
            "members": members,
            "recent_events": recent_events,
            "member_count": member_count,
            "summoned_count": summoned_count,
            "average_mood": average_mood,
            "recent_event_count": len(statistic_entries),
            "recent_fund_delta": recent_fund_delta,
            "recent_pressure_delta": recent_pressure_delta,
        }
        if household is None:
            return HouseholdSummaryPresentation(
                title="家庭摘要",
                overview_text="家庭資料尚未初始化。",
                log_text="目前尚無家庭重點事件。",
                **summary_data,
            )

        overview_text = "\n".join(
            (
                f"生活費: {household.living_fund} 元",
                f"家庭壓力: {int(round(household.household_pressure))}%",
            )
        )
        if not summary_entries:
            return HouseholdSummaryPresentation(
                title="家庭摘要",
                overview_text=overview_text,
                log_text="目前尚無家庭重點事件。",
                living_fund=int(household.living_fund),
                household_pressure=float(household.household_pressure),
                **summary_data,
            )

        log_lines = []
        for entry in summary_entries:
            summary_text = entry.summary.strip() if getattr(entry, "summary", "") else "未命名事件"
            wall_clock_time = float(getattr(entry, "wall_clock_time", 0.0) or 0.0)
            time_text = datetime.fromtimestamp(wall_clock_time).strftime("%H:%M:%S") if wall_clock_time > 0.0 else ""
            entry_parts = [f"#{entry.sequence:03d}"]
            if time_text:
                entry_parts.append(time_text)
            entry_parts.append(summary_text)
            delta_parts = []
            if entry.living_fund_delta:
                delta_parts.append(f"生活費 {entry.living_fund_delta:+d}")
            if entry.household_pressure_delta:
                delta_parts.append(f"壓力 {entry.household_pressure_delta:+.1f}")
            suffix = f" ({', '.join(delta_parts)})" if delta_parts else ""
            log_lines.append(" ".join(part for part in entry_parts if part).strip() + suffix)
        return HouseholdSummaryPresentation(
            title="家庭摘要",
            overview_text=overview_text,
            log_text="\n".join(log_lines),
            living_fund=int(household.living_fund),
            household_pressure=float(household.household_pressure),
            **summary_data,
        )

    def build_household_member_presentations(self, pet_states):
        members = []
        for state in pet_states or ():
            try:
                state_length = len(state)
            except TypeError:
                continue
            character_name = str(state[0] if state_length > 0 else "").strip()
            if not character_name:
                continue
            summoned = bool(state[1]) if state_length > 1 else False
            raw_mood_score = state[2] if state_length > 2 else None
            try:
                mood_score = (
                    None if raw_mood_score is None else
                    max(0.0, min(100.0, float(raw_mood_score)))
                )
            except (TypeError, ValueError):
                mood_score = None
            mood_state = str(state[3] if state_length > 3 else "").strip()
            form_key = str(
                state[4] if state_length > 4 else "base"
            ).strip()
            if form_key not in self.FORM_LABELS:
                form_key = "base"
            members.append(
                HouseholdMemberPresentation(
                    character_name=character_name,
                    summoned=summoned,
                    mood_score=mood_score,
                    mood_state=mood_state,
                    mood_label=self.MOOD_STATE_LABELS.get(
                        mood_state,
                        "尚無資料" if mood_score is None else "平穩",
                    ),
                    form_key=form_key,
                    form_label=self.FORM_LABELS[form_key],
                )
            )
        return tuple(members)

    def build_household_recent_event_presentation(self, entry):
        sequence = int(getattr(entry, "sequence", 0) or 0)
        wall_clock_time = float(getattr(entry, "wall_clock_time", 0.0) or 0.0)
        timestamp_text = (
            datetime.fromtimestamp(wall_clock_time).strftime("%m/%d %H:%M")
            if wall_clock_time > 0.0 else
            f"#{sequence:03d}"
        )
        channel = str(getattr(entry, "channel", "") or "")
        delta_parts = []
        living_fund_delta = int(getattr(entry, "living_fund_delta", 0) or 0)
        if living_fund_delta:
            delta_parts.append(f"生活費 {living_fund_delta:+,d}")
        pressure_delta = float(getattr(entry, "household_pressure_delta", 0.0) or 0.0)
        if pressure_delta:
            delta_parts.append(f"壓力 {pressure_delta:+.1f}")
        return HouseholdRecentEventPresentation(
            sequence=sequence,
            timestamp_text=timestamp_text,
            channel=channel,
            channel_label=self.SOCIAL_LOG_CHANNEL_LABELS.get(
                channel,
                channel or "事件",
            ),
            summary=str(getattr(entry, "summary", "") or "").strip() or "未命名事件",
            delta_text=" · ".join(delta_parts),
        )

    def filter_household_summary_entries(self, entries):
        selected = [
            entry for entry in entries or ()
            if self.household_summary_entry_is_relevant(entry)
        ]
        return selected[-self.HOUSEHOLD_SUMMARY_EVENT_LIMIT:]

    def household_summary_entry_is_relevant(self, entry):
        if not entry:
            return False
        if getattr(entry, "living_fund_delta", 0):
            return True
        if float(getattr(entry, "household_pressure_delta", 0.0) or 0.0):
            return True
        channel = str(getattr(entry, "channel", "") or "")
        category = str(getattr(entry, "category", "") or "")
        if channel == "social" or category in {"social", "care", "relationship"}:
            return False
        if str(getattr(entry, "importance", "") or "") in {"normal", "high", "critical"}:
            return True
        if channel in self.HOUSEHOLD_SUMMARY_CHANNELS:
            return True
        return category in self.HOUSEHOLD_SUMMARY_CATEGORIES

    def build_social_log(self, entries, filter_mode="all", participant_name=""):
        entries = list(entries or ())
        filter_mode = str(filter_mode or "all")
        if filter_mode not in self.SOCIAL_LOG_FILTER_LABELS:
            filter_mode = "all"
        participant_names = self.collect_social_log_participant_names(entries)
        participant_name = str(participant_name or "")
        if filter_mode == "personal" and participant_name not in participant_names:
            participant_name = participant_names[0] if participant_names else ""

        filtered_entries = [
            entry for entry in entries
            if self.social_log_entry_matches_filter(
                entry,
                filter_mode=filter_mode,
                participant_name=participant_name,
            )
        ]
        title = f"事件日誌 - {self.SOCIAL_LOG_FILTER_LABELS[filter_mode]}"
        if filter_mode == "personal" and participant_name:
            title = f"{title}: {participant_name}"
        log_text = (
            "\n".join(self.format_social_log_entry(entry) for entry in filtered_entries)
            if filtered_entries else
            "目前沒有符合條件的紀錄。"
        )
        structured_entries = tuple(
            self.build_social_log_entry_presentation(entry)
            for entry in reversed(filtered_entries)
        )
        return SocialLogPresentation(
            title=title,
            filter_mode=filter_mode,
            participant_name=participant_name,
            participant_names=participant_names,
            log_text=log_text,
            entries=structured_entries,
        )

    def collect_social_log_participant_names(self, entries):
        names = set()
        for entry in entries:
            for attr_name in ("actor_name", "target_name"):
                name = str(getattr(entry, attr_name, "") or "").strip()
                if name and name != "Player":
                    names.add(name)
        return tuple(sorted(names))

    def social_log_entry_matches_filter(self, entry, *, filter_mode, participant_name=""):
        if filter_mode == "all":
            return True
        if filter_mode == "personal":
            if not participant_name:
                return False
            return participant_name in {
                str(getattr(entry, "actor_name", "") or ""),
                str(getattr(entry, "target_name", "") or ""),
            }
        if filter_mode == "social":
            return (
                getattr(entry, "channel", "") == "social" or
                getattr(entry, "category", "") in {"social", "care", "relationship"}
            )
        if filter_mode == "economy":
            return (
                getattr(entry, "channel", "") == "economy" or
                getattr(entry, "category", "") in {"economy", "player_help"} or
                bool(getattr(entry, "living_fund_delta", 0))
            )
        if filter_mode == "item":
            return (
                getattr(entry, "channel", "") == "item" or
                getattr(entry, "category", "") in {"player_offer", "item"}
            )
        if filter_mode == "system":
            return (
                getattr(entry, "channel", "") == "system" or
                getattr(entry, "category", "") in {"system", "debug"}
            )
        return True

    def build_social_log_entry_presentation(self, entry):
        sequence = int(getattr(entry, "sequence", 0) or 0)
        wall_clock_time = float(getattr(entry, "wall_clock_time", 0.0) or 0.0)
        timestamp_text = (
            datetime.fromtimestamp(wall_clock_time).strftime("%m/%d %H:%M")
            if wall_clock_time > 0.0 else
            f"時序 #{sequence:03d}"
        )
        channel = str(getattr(entry, "channel", "") or "")
        channel_label = self.SOCIAL_LOG_CHANNEL_LABELS.get(channel, channel or "事件")
        actor_name = str(getattr(entry, "actor_name", "") or "").strip()
        target_name = str(getattr(entry, "target_name", "") or "").strip()
        if actor_name and target_name and actor_name != target_name:
            participant_text = f"{actor_name} → {target_name}"
        elif actor_name:
            participant_text = actor_name
        elif target_name:
            participant_text = target_name
        else:
            participant_text = "家庭／系統"

        effects = []
        living_fund_delta = int(getattr(entry, "living_fund_delta", 0) or 0)
        if living_fund_delta:
            effects.append(
                SocialLogEffectPresentation(
                    key="living_fund",
                    label="生活費",
                    value=float(living_fund_delta),
                    value_text=f"{living_fund_delta:+,d} 元",
                )
            )
        pressure_delta = float(getattr(entry, "household_pressure_delta", 0.0) or 0.0)
        if pressure_delta:
            effects.append(
                SocialLogEffectPresentation(
                    key="household_pressure",
                    label="家庭壓力",
                    value=pressure_delta,
                    value_text=f"{pressure_delta:+.1f}",
                )
            )
        mood_delta = float(getattr(entry, "mood_delta", 0.0) or 0.0)
        if mood_delta:
            effects.append(
                SocialLogEffectPresentation(
                    key="mood",
                    label="心情",
                    value=mood_delta,
                    value_text=f"{mood_delta:+.1f}",
                )
            )
        relation_delta = dict(getattr(entry, "relation_delta", {}) or {})
        for metric_name in self.RELATIONSHIP_METRIC_LABELS:
            value = float(relation_delta.get(metric_name, 0.0) or 0.0)
            if not value:
                continue
            effects.append(
                SocialLogEffectPresentation(
                    key=f"relationship_{metric_name}",
                    label=self.RELATIONSHIP_METRIC_LABELS[metric_name],
                    value=value,
                    value_text=f"{value:+.2f}",
                )
            )

        return SocialLogEntryPresentation(
            sequence=sequence,
            timestamp_text=timestamp_text,
            channel=channel,
            channel_label=channel_label,
            category=str(getattr(entry, "category", "") or ""),
            event_type=str(getattr(entry, "event_type", "") or ""),
            importance=str(getattr(entry, "importance", "") or ""),
            summary=str(getattr(entry, "summary", "") or "").strip() or "未命名事件",
            actor_name=actor_name,
            target_name=target_name,
            participant_text=participant_text,
            effects=tuple(effects),
            tags=tuple(str(tag) for tag in (getattr(entry, "tags", ()) or ()) if str(tag)),
        )

    def format_social_log_entry(self, entry):
        summary_text = str(getattr(entry, "summary", "") or "").strip() or "未命名事件"
        wall_clock_time = float(getattr(entry, "wall_clock_time", 0.0) or 0.0)
        time_text = datetime.fromtimestamp(wall_clock_time).strftime("%H:%M:%S") if wall_clock_time > 0.0 else ""
        channel = str(getattr(entry, "channel", "") or "")
        channel_label = self.SOCIAL_LOG_CHANNEL_LABELS.get(channel, channel or "事件")
        parts = [f"#{int(getattr(entry, 'sequence', 0)):03d}"]
        if time_text:
            parts.append(time_text)
        parts.append(f"[{channel_label}]")

        actor_name = str(getattr(entry, "actor_name", "") or "").strip()
        target_name = str(getattr(entry, "target_name", "") or "").strip()
        if actor_name and target_name and actor_name != target_name:
            parts.append(f"{actor_name} -> {target_name}:")
        elif actor_name:
            parts.append(f"{actor_name}:")
        elif target_name:
            parts.append(f"{target_name}:")
        parts.append(summary_text)

        delta_parts = []
        if getattr(entry, "living_fund_delta", 0):
            delta_parts.append(f"生活費 {int(getattr(entry, 'living_fund_delta')):+d}")
        pressure_delta = float(getattr(entry, "household_pressure_delta", 0.0) or 0.0)
        if pressure_delta:
            delta_parts.append(f"壓力 {pressure_delta:+.1f}")
        mood_delta = float(getattr(entry, "mood_delta", 0.0) or 0.0)
        if mood_delta:
            delta_parts.append(f"心情 {mood_delta:+.1f}")
        relation_delta = dict(getattr(entry, "relation_delta", {}) or {})
        if relation_delta:
            relation_text = ", ".join(
                f"{name} {float(value):+.2f}"
                for name, value in relation_delta.items()
                if float(value) != 0.0
            )
            if relation_text:
                delta_parts.append(f"關係 {relation_text}")
        suffix = f" ({'; '.join(delta_parts)})" if delta_parts else ""
        return " ".join(part for part in parts if part).strip() + suffix

    def build_relationship_table(self, household, pet_names=()):
        if household is None:
            return RelationshipTablePresentation(
                title="關係表",
                table_text="家庭資料尚未初始化。",
            )

        actor_names = self.collect_relationship_actor_names(household, pet_names=pet_names)
        if len(actor_names) < 2:
            return RelationshipTablePresentation(
                title="關係表",
                table_text="目前沒有足夠角色可顯示關係。",
            )

        lines = [
            "好感度為暫定加權分數：熟悉 45% + 信任 30% + 依附 35% - 緊張 20%",
            "",
        ]
        rows = []
        for actor_name in actor_names:
            lines.append(f"[{actor_name}]")
            for target_name in actor_names:
                if target_name == actor_name:
                    continue
                entry = self.get_relationship_entry(household, actor_name, target_name)
                row = self.build_relationship_row(actor_name, target_name, entry)
                rows.append(row)
                lines.append(self.format_relationship_row_presentation(row))
            lines.append("")

        return RelationshipTablePresentation(
            title="關係表",
            table_text="\n".join(lines).rstrip(),
            actor_names=actor_names,
            rows=tuple(rows),
        )

    def collect_relationship_actor_names(self, household, pet_names=()):
        names = set()
        for name in pet_names or ():
            text = str(name or "").strip()
            if text:
                names.add(text)
        relationships = getattr(household, "relationships", None)
        if relationships is not None and hasattr(relationships, "all_entries"):
            for entry in relationships.all_entries():
                actor_name = str(getattr(entry, "actor_name", "") or "").strip()
                target_name = str(getattr(entry, "target_name", "") or "").strip()
                if actor_name and actor_name != "Player":
                    names.add(actor_name)
                if target_name and target_name != "Player":
                    names.add(target_name)
        return tuple(sorted(names))

    def get_relationship_entry(self, household, actor_name, target_name):
        relationships = getattr(household, "relationships", None)
        if relationships is None or not hasattr(relationships, "get_entry"):
            return None
        return relationships.get_entry(actor_name, target_name)

    def format_relationship_row(self, target_name, entry):
        row = self.build_relationship_row("", target_name, entry)
        return self.format_relationship_row_presentation(row)

    def build_relationship_row(self, actor_name, target_name, entry):
        return RelationshipRowPresentation(
            actor_name=str(actor_name or ""),
            target_name=str(target_name or ""),
            affinity=self.calculate_relationship_affinity(entry),
            familiarity=float(getattr(entry, "familiarity", 0.0) or 0.0),
            trust=float(getattr(entry, "trust", 0.0) or 0.0),
            attachment=float(getattr(entry, "attachment", 0.0) or 0.0),
            tension=float(getattr(entry, "tension", 0.0) or 0.0),
            event_count=int(getattr(entry, "event_count", 0) or 0),
        )

    def format_relationship_row_presentation(self, row):
        return (
            f"  -> {row.target_name}: "
            f"好感度 {row.affinity:5.2f} | "
            f"熟悉 {row.familiarity:5.2f} / "
            f"信任 {row.trust:5.2f} / "
            f"依附 {row.attachment:5.2f} / "
            f"緊張 {row.tension:5.2f} | "
            f"事件 {row.event_count}"
        )

    def calculate_relationship_affinity(self, entry):
        if entry is None:
            return 0.0
        familiarity = float(getattr(entry, "familiarity", 0.0) or 0.0)
        trust = float(getattr(entry, "trust", 0.0) or 0.0)
        attachment = float(getattr(entry, "attachment", 0.0) or 0.0)
        tension = float(getattr(entry, "tension", 0.0) or 0.0)
        score = familiarity * 0.45 + trust * 0.30 + attachment * 0.35 - tension * 0.20
        return max(0.0, min(100.0, score))
