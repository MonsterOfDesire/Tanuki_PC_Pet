from __future__ import annotations

from .activity_event_contract import (
    ACTIVITY_EVENT_RACE_COMPLETED,
    ACTIVITY_EVENT_RACE_DECLINED,
    build_activity_event_metadata,
)
from .race_rules import (
    RACE_RELATION_FAMILIARITY_REWARD,
    RACE_RELATION_TRUST_REWARD,
    RACE_WINNER_MOOD_REWARD,
)
from .race_state import RaceEvent


RACE_EVENT_DISPLAY_NAMES = {
    "Tokai Teio": "帝寶",
    "Sirius Symboli": "天狼星",
    "Symboli Rudolf": "魯道夫",
}


class RaceEventAdapter:
    def __init__(self):
        self._processed_event_keys: set[str] = set()

    def apply(
        self,
        event: RaceEvent,
        *,
        record_household_event,
        race_statistics=None,
        apply_winner_mood_reward=None,
        apply_reverse_relationship_reward=None,
    ):
        if not callable(record_household_event):
            return None
        event_key = f"{event.activity_id}:{event.event_type}"
        if event_key in self._processed_event_keys:
            return None
        challenger_name = str(event.challenger_name or "")
        opponent_name = str(event.opponent_name or "")
        winner_name = str(event.winner_name or "")
        loser_name = str(event.loser_name or "")
        display = lambda name: RACE_EVENT_DISPLAY_NAMES.get(name, name)
        completed = event.event_type == "race_completed"
        direction_key = (
            (
                "clockwise_left"
                if int(event.race_direction or 1) < 0
                else "counterclockwise_right"
            )
            if completed
            else ""
        )
        direction_label = (
            "順時鐘（朝左）"
            if direction_key == "clockwise_left"
            else "逆時鐘（朝右）"
        )
        relation_reward = {
            "familiarity": RACE_RELATION_FAMILIARITY_REWARD,
            "trust": RACE_RELATION_TRUST_REWARD,
        }
        activity_event_name = (
            ACTIVITY_EVENT_RACE_COMPLETED
            if completed
            else ACTIVITY_EVENT_RACE_DECLINED
        )
        metadata = build_activity_event_metadata(
            event_name=activity_event_name,
            event_id=event_key,
            activity_id=event.activity_id,
            activity_kind="race",
            participants=(
                (challenger_name, "challenger"),
                (opponent_name, "opponent"),
            ),
            source=event.source,
            execution_mode=event.execution_mode,
            world_mode=event.world_mode,
            phase="finish" if completed else "response",
            started_at=event.activity_started_at,
            ended_at=event.occurred_at,
            outcome="completed" if completed else "declined",
            reason="" if completed else "opponent_declined",
            extra={
                "source": event.source,
                "execution_mode": event.execution_mode,
                "world_mode": event.world_mode,
                "challenger_name": challenger_name,
                "opponent_name": opponent_name,
                "winner_name": winner_name,
                "loser_name": loser_name,
                "challenger_form": event.challenger_form,
                "opponent_form": event.opponent_form,
                "race_distance_px": float(event.race_distance),
                "race_course_key": event.race_course_key,
                "race_nominal_meters": int(event.race_nominal_meters),
                "race_direction": int(event.race_direction or 1),
                "direction_key": direction_key,
                "running_started_at": float(event.running_started_at),
                "winner_arrived_at": float(event.winner_arrived_at),
                "race_elapsed_seconds": float(
                    event.race_elapsed_seconds
                ),
                "race_rewards": (
                    {
                        "winner_mood": RACE_WINNER_MOOD_REWARD,
                        "both_familiarity": (
                            RACE_RELATION_FAMILIARITY_REWARD
                        ),
                        "both_trust": RACE_RELATION_TRUST_REWARD,
                        "loser_penalty": 0.0,
                    }
                    if completed
                    else {}
                ),
            },
        )
        entry = record_household_event(
            occurred_at=float(event.occurred_at),
            category="social",
            event_type=event.event_type,
            channel="social",
            importance="normal" if completed else "low",
            summary=(
                (
                    f"{display(winner_name)}在"
                    f"{int(round(float(event.race_distance)))}px、"
                    f"{direction_label}的賽跑中，以"
                    f"{float(event.race_elapsed_seconds):.1f}秒"
                    f"勝過{display(loser_name)}。"
                )
                if completed
                else (
                    f"{display(opponent_name)}婉拒了"
                    f"{display(challenger_name)}的賽跑挑戰。"
                )
            ),
            actor_name=winner_name if completed else opponent_name,
            target_name=loser_name if completed else challenger_name,
            mood_delta=(RACE_WINNER_MOOD_REWARD if completed else 0.0),
            relation_delta=(relation_reward if completed else None),
            tags=("race", "completed" if completed else "declined"),
            metadata=metadata,
            apply_deltas=completed,
        )
        if completed and callable(apply_winner_mood_reward):
            apply_winner_mood_reward(
                winner_name,
                RACE_WINNER_MOOD_REWARD,
            )
        if completed and callable(apply_reverse_relationship_reward):
            apply_reverse_relationship_reward(
                loser_name,
                winner_name,
                relation_reward,
                float(event.occurred_at),
            )
        if completed and race_statistics is not None:
            race_statistics.record_completed(event)
        self._processed_event_keys.add(event_key)
        return entry
