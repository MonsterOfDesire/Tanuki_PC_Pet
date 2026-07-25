from dataclasses import dataclass

from .dashboard_presenter import RelationshipRowPresentation


@dataclass(frozen=True)
class SummonMemberPresentation:
    character_name: str
    summoned: bool
    available: bool = True
    mood_score: float | None = None
    mood_state: str = ""


@dataclass(frozen=True)
class RelationSummonPresentation:
    title: str
    selected_character_name: str
    members: tuple[SummonMemberPresentation, ...]
    relationship_rows: tuple[RelationshipRowPresentation, ...]
    empty_text: str = "目前沒有可顯示的關係資料。"


class DashboardRelationSummonBinding:
    """Adapter joining relationship presentation data with summon state/actions."""

    def __init__(self, dashboard):
        self.dashboard = dashboard

    def presentation(self, selected_character_name=""):
        relationship = self.dashboard.controller.build_relationship_table_presentation(
            self.dashboard
        )
        summon_by_name = self._summon_state_by_name()
        names = list(summon_by_name)
        for character_name in relationship.actor_names:
            if character_name not in names:
                names.append(character_name)

        members = tuple(
            SummonMemberPresentation(
                character_name=character_name,
                summoned=summon_by_name.get(character_name, (False, None, ""))[0],
                available=character_name in summon_by_name,
                mood_score=summon_by_name.get(character_name, (False, None, ""))[1],
                mood_state=summon_by_name.get(character_name, (False, None, ""))[2],
            )
            for character_name in names
        )
        selected_character_name = str(selected_character_name or "")
        if selected_character_name not in names:
            selected_character_name = names[0] if names else ""
        relationship_rows = tuple(
            row
            for row in relationship.rows
            if row.actor_name == selected_character_name
        )
        return RelationSummonPresentation(
            title="角色關係＋召喚",
            selected_character_name=selected_character_name,
            members=members,
            relationship_rows=relationship_rows,
            empty_text=relationship.table_text if not relationship_rows else "",
        )

    def mood_snapshot(self):
        return {
            character_name: (state[1], state[2])
            for character_name, state in self._summon_state_by_name().items()
        }

    def _summon_state_by_name(self):
        summon_states = tuple(self.dashboard.get_pet_summon_states())
        summon_by_name = {}
        for state in summon_states:
            character_name = str(state[0] if len(state) > 0 else "").strip()
            if not character_name:
                continue
            summoned = bool(state[1]) if len(state) > 1 else False
            mood_score = state[2] if len(state) > 2 else None
            mood_state = str(state[3] if len(state) > 3 else "")
            summon_by_name[character_name] = (
                summoned,
                None if mood_score is None else float(mood_score),
                mood_state,
            )
        return summon_by_name

    def set_summoned(self, character_name, summoned):
        return self.dashboard.controller.set_pet_visibility_by_name(
            self.dashboard,
            character_name,
            summoned,
        )
