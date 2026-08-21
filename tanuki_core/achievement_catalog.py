from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


ACHIEVEMENT_WORLD_SANDBOX = "sandbox"
ACHIEVEMENT_WORLD_GOLDEN_LEGEND = "golden_legend"
ACHIEVEMENT_WORLD_MODES = frozenset(
    {
        ACHIEVEMENT_WORLD_SANDBOX,
        ACHIEVEMENT_WORLD_GOLDEN_LEGEND,
    }
)
ACHIEVEMENT_TIERS = frozenset({"G1", "G2", "G3"})

SUPPORTED_ACHIEVEMENT_RULE_TYPES = frozenset(
    {
        "event_count",
        "distinct_values",
        "single_event_threshold",
        "distinct_participants_by_role",
        "all_of",
        "distinct_composite_values",
        "simultaneous_state_threshold",
        "all_of_achievements",
    }
)


@dataclass(frozen=True)
class AchievementTrophyDefinition:
    trophy_type: str
    trophy_id: str
    image: str


@dataclass(frozen=True)
class AchievementDefinition:
    achievement_id: str
    world_mode: str
    title_zh_tw: str
    description_zh_tw: str
    tier: str
    trophy: AchievementTrophyDefinition
    rule: Mapping[str, object]
    implementation_status: str


@dataclass(frozen=True)
class AchievementCatalog:
    schema_version: int
    definitions: tuple[AchievementDefinition, ...]
    definitions_by_id: Mapping[str, AchievementDefinition]

    def definitions_for_mode(
        self,
        world_mode: str,
    ) -> tuple[AchievementDefinition, ...]:
        world_mode = str(world_mode or "").strip()
        return tuple(
            definition
            for definition in self.definitions
            if definition.world_mode == world_mode
        )

    def get(self, achievement_id: str) -> AchievementDefinition | None:
        return self.definitions_by_id.get(str(achievement_id or "").strip())


def load_achievement_catalog(path: str | Path) -> AchievementCatalog:
    catalog_path = Path(path)
    with catalog_path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    return load_achievement_catalog_payload(payload)


def load_achievement_catalog_payload(payload) -> AchievementCatalog:
    if not isinstance(payload, Mapping):
        raise ValueError("achievement catalog root must be an object")
    try:
        schema_version = int(payload.get("schema_version", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("achievement catalog schema_version must be an integer") from exc
    if schema_version <= 0:
        raise ValueError("achievement catalog schema_version must be positive")

    raw_definitions = payload.get("achievements", ())
    if not isinstance(raw_definitions, list):
        raise ValueError("achievement catalog achievements must be a list")

    definitions = []
    definitions_by_id = {}
    for raw_definition in raw_definitions:
        definition = _parse_definition(raw_definition)
        if definition.achievement_id in definitions_by_id:
            raise ValueError(
                f"duplicate achievement id: {definition.achievement_id}"
            )
        definitions.append(definition)
        definitions_by_id[definition.achievement_id] = definition

    _validate_achievement_dependencies(definitions_by_id)
    return AchievementCatalog(
        schema_version=schema_version,
        definitions=tuple(definitions),
        definitions_by_id=MappingProxyType(dict(definitions_by_id)),
    )


def _parse_definition(raw_definition) -> AchievementDefinition:
    if not isinstance(raw_definition, Mapping):
        raise ValueError("achievement definition must be an object")

    achievement_id = str(
        raw_definition.get("achievement_id", "") or ""
    ).strip()
    if not achievement_id:
        raise ValueError("achievement definition requires achievement_id")

    raw_world_modes = raw_definition.get("world_modes", ())
    if not isinstance(raw_world_modes, list) or len(raw_world_modes) != 1:
        raise ValueError(
            f"{achievement_id}: definition must belong to exactly one world mode"
        )
    world_mode = str(raw_world_modes[0] or "").strip()
    if world_mode not in ACHIEVEMENT_WORLD_MODES:
        raise ValueError(
            f"{achievement_id}: unsupported world mode {world_mode!r}"
        )

    tier = str(raw_definition.get("tier", "") or "").strip()
    if tier not in ACHIEVEMENT_TIERS:
        raise ValueError(f"{achievement_id}: unsupported tier {tier!r}")

    raw_trophy = raw_definition.get("trophy", {})
    if not isinstance(raw_trophy, Mapping):
        raise ValueError(f"{achievement_id}: trophy must be an object")
    trophy_image = str(raw_trophy.get("image", "") or "").replace(
        "\\", "/"
    ).strip()
    if (
        not trophy_image
        or trophy_image.startswith("/")
        or "/../" in f"/{trophy_image}/"
    ):
        raise ValueError(f"{achievement_id}: invalid trophy image path")

    raw_rule = raw_definition.get("rule", {})
    if not isinstance(raw_rule, Mapping):
        raise ValueError(f"{achievement_id}: rule must be an object")
    rule_type = str(raw_rule.get("type", "") or "").strip()
    if rule_type not in SUPPORTED_ACHIEVEMENT_RULE_TYPES:
        raise ValueError(
            f"{achievement_id}: unsupported rule type {rule_type!r}"
        )

    return AchievementDefinition(
        achievement_id=achievement_id,
        world_mode=world_mode,
        title_zh_tw=str(raw_definition.get("title_zh_tw", "") or ""),
        description_zh_tw=str(
            raw_definition.get("description_zh_tw", "") or ""
        ),
        tier=tier,
        trophy=AchievementTrophyDefinition(
            trophy_type=str(raw_trophy.get("type", "") or ""),
            trophy_id=str(raw_trophy.get("id", "") or ""),
            image=trophy_image,
        ),
        rule=MappingProxyType(dict(raw_rule)),
        implementation_status=str(
            raw_definition.get("implementation_status", "") or ""
        ),
    )


def _validate_achievement_dependencies(definitions_by_id) -> None:
    for definition in definitions_by_id.values():
        if definition.rule.get("type") != "all_of_achievements":
            continue
        raw_ids = definition.rule.get("achievement_ids", ())
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValueError(
                f"{definition.achievement_id}: achievement_ids must be a non-empty list"
            )
        for dependency_id in raw_ids:
            dependency = definitions_by_id.get(str(dependency_id or ""))
            if dependency is None:
                raise ValueError(
                    f"{definition.achievement_id}: unknown dependency {dependency_id!r}"
                )
            if dependency.world_mode != definition.world_mode:
                raise ValueError(
                    f"{definition.achievement_id}: dependency crosses world modes"
                )
