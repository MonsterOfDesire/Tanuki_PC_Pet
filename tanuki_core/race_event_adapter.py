from __future__ import annotations

from .race_state import RaceEvent


RACE_EVENT_DISPLAY_NAMES = {
    "Tokai Teio": "帝寶",
    "Sirius Symboli": "天狼星",
    "Symboli Rudolf": "魯道夫",
}


class RaceEventAdapter:
    def apply(
        self,
        event: RaceEvent,
        *,
        record_household_event,
        race_statistics=None,
    ):
        if not callable(record_household_event):
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
            tags=("race", "completed" if completed else "declined"),
            metadata={
                "activity_id": event.activity_id,
                "challenger_name": challenger_name,
                "opponent_name": opponent_name,
                "winner_name": winner_name,
                "loser_name": loser_name,
                "source": event.source,
                "challenger_form": event.challenger_form,
                "opponent_form": event.opponent_form,
                "execution_mode": event.execution_mode,
                "world_mode": event.world_mode,
                "race_distance_px": float(event.race_distance),
                "race_direction": int(event.race_direction or 1),
                "direction_key": direction_key,
                "running_started_at": float(event.running_started_at),
                "winner_arrived_at": float(event.winner_arrived_at),
                "race_elapsed_seconds": float(event.race_elapsed_seconds),
            },
            apply_deltas=False,
        )
        if completed and race_statistics is not None:
            race_statistics.record_completed(event)
        return entry
