from __future__ import annotations

from .activity_event_contract import (
    ACTIVITY_EVENT_CHORUS_COMPLETED,
    ACTIVITY_EVENT_CHORUS_INTERRUPTED,
    build_activity_event_metadata,
)
from .chorus_state import ChorusEvent
from .chorus_settlement import build_chorus_settlement_plan


CHORUS_EVENT_DISPLAY_NAMES = {
    "Air Groove": "氣槽",
    "Sirius Symboli": "天狼星",
    "Symboli Rudolf": "魯道夫",
    "Tokai Teio": "帝寶",
    "Tsurumaru Tsuyoshi": "鶴寶",
}


class ChorusEventAdapter:
    def __init__(self):
        self._processed_event_keys: set[str] = set()

    def apply(
        self,
        event: ChorusEvent,
        *,
        record_household_event,
        apply_mood_reward=None,
        apply_relationship_reward=None,
    ):
        if not callable(record_household_event):
            return None
        if event.source == "settings_preview":
            return None
        event_key = f"{event.session_id}:{event.event_type}"
        if event_key in self._processed_event_keys:
            return None
        completed = event.event_type == "chorus_completed"
        event_name = (
            ACTIVITY_EVENT_CHORUS_COMPLETED
            if completed
            else ACTIVITY_EVENT_CHORUS_INTERRUPTED
        )
        display = lambda name: CHORUS_EVENT_DISPLAY_NAMES.get(name, name)
        performer_names = tuple(event.performer_names)
        audience_names = tuple(event.audience_names)
        performer_text = "、".join(display(name) for name in performer_names)
        audience_text = "、".join(display(name) for name in audience_names)
        performance_label = "獨奏" if len(performer_names) == 1 else "合奏"
        if completed:
            summary = f"{performer_text}完成了一場{performance_label}"
            if audience_text:
                summary += f"，{audience_text}在旁欣賞"
            summary += f"，共持續{event.elapsed_seconds:.1f}秒。"
        else:
            summary = (
                f"{performance_label}因{self._reason_text(event.reason)}"
                "提前結束。"
            )
        metadata = build_activity_event_metadata(
            event_name=event_name,
            event_id=event_key,
            activity_id=event.session_id,
            activity_kind="chorus",
            participants=event.participant_roles,
            source=event.source,
            execution_mode="autonomous",
            world_mode=event.world_mode,
            phase="finish",
            started_at=event.started_at,
            ended_at=event.occurred_at,
            outcome=event.outcome,
            reason=event.reason,
            extra={
                "performer_names": list(performer_names),
                "audience_names": list(audience_names),
                "performer_count": len(performer_names),
                "audience_count": len(audience_names),
                "performance_kind": (
                    "solo" if len(performer_names) == 1 else "ensemble"
                ),
                "settlement_applied": completed,
            },
        )
        entry = record_household_event(
            occurred_at=float(event.occurred_at),
            category="social",
            event_type=event.event_type,
            channel="social",
            importance="normal" if completed else "low",
            summary=summary,
            actor_name="",
            target_name="",
            tags=("chorus", "completed" if completed else "interrupted"),
            metadata=metadata,
            apply_deltas=False,
        )
        settlement = build_chorus_settlement_plan(event)
        if callable(apply_mood_reward):
            for reward in settlement.mood_rewards:
                apply_mood_reward(reward.character_name, reward.amount)
        if callable(apply_relationship_reward):
            for reward in settlement.relationship_rewards:
                apply_relationship_reward(
                    reward.actor_name,
                    reward.target_name,
                    reward.relation_delta,
                    event.occurred_at,
                )
        self._processed_event_keys.add(event_key)
        return entry

    @staticmethod
    def _reason_text(reason: str) -> str:
        return {
            "tsuyoshi_honey_guard_needed": "鶴寶需要蜂蜜保護",
            "child_care_needed": "有小孩需要照護",
            "no_performers_remaining": "表演者已全數離開",
        }.get(str(reason or ""), "現場狀況改變")
