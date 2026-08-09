from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .achievement_catalog import (
    ACHIEVEMENT_WORLD_GOLDEN_LEGEND,
    ACHIEVEMENT_WORLD_SANDBOX,
    AchievementCatalog,
)
from .achievement_state import AchievementState


ACHIEVEMENT_TIER_ORDER = ("G1", "G2", "G3")
ACHIEVEMENT_MODE_ORDER = (
    ACHIEVEMENT_WORLD_SANDBOX,
    ACHIEVEMENT_WORLD_GOLDEN_LEGEND,
)
ACHIEVEMENT_MODE_LABELS = {
    ACHIEVEMENT_WORLD_SANDBOX: "沙盒",
    ACHIEVEMENT_WORLD_GOLDEN_LEGEND: "黃金傳說",
}


@dataclass(frozen=True)
class AchievementCardSnapshot:
    slot_key: str
    tier: str
    unlocked: bool
    image_relative_path: str
    title: str = ""
    acquisition_method: str = ""
    unlocked_at_text: str = ""
    accessible_name: str = ""


@dataclass(frozen=True)
class AchievementTierSnapshot:
    tier: str
    cards: tuple[AchievementCardSnapshot, ...]
    unlocked_count: int
    total_count: int


@dataclass(frozen=True)
class AchievementModeSnapshot:
    world_mode: str
    mode_label: str
    tiers: tuple[AchievementTierSnapshot, ...]
    unlocked_count: int
    total_count: int
    recent_title: str = ""
    recent_unlocked_at_text: str = ""

    def tier_snapshot(self, tier: str) -> AchievementTierSnapshot | None:
        return next(
            (item for item in self.tiers if item.tier == str(tier or "")),
            None,
        )

    @property
    def summary_text(self) -> str:
        progress = f"已取得 {self.unlocked_count} / {self.total_count}"
        if self.recent_title:
            return f"{progress}｜最近：{self.recent_title}"
        return f"{progress}｜尚無完成成就"


@dataclass(frozen=True)
class AchievementCabinetSnapshot:
    modes: tuple[AchievementModeSnapshot, ...]

    def mode_snapshot(
        self,
        world_mode: str,
    ) -> AchievementModeSnapshot | None:
        return next(
            (
                item
                for item in self.modes
                if item.world_mode == str(world_mode or "")
            ),
            None,
        )

    def card_snapshot(
        self,
        achievement_id: str,
    ) -> AchievementCardSnapshot | None:
        achievement_id = str(achievement_id or "").strip()
        for mode in self.modes:
            for tier in mode.tiers:
                for card in tier.cards:
                    if card.slot_key == achievement_id:
                        return card
        return None


@dataclass(frozen=True)
class AchievementUnlockNotificationSnapshot:
    achievement_ids: tuple[str, ...]
    titles: tuple[str, ...]
    primary_image_relative_path: str
    heading: str
    message: str


def build_achievement_cabinet_snapshot(
    catalog: AchievementCatalog,
    state: AchievementState,
) -> AchievementCabinetSnapshot:
    modes = []
    for world_mode in ACHIEVEMENT_MODE_ORDER:
        definitions = catalog.definitions_for_mode(world_mode)
        cards_by_tier = {tier: [] for tier in ACHIEVEMENT_TIER_ORDER}
        recent = None
        unlocked_total = 0
        for definition in definitions:
            progress = state.progress_by_world_mode.get(
                world_mode,
                {},
            ).get(definition.achievement_id)
            unlocked = bool(progress and progress.unlocked)
            unlocked_at = (
                float(progress.unlocked_at)
                if unlocked and progress.unlocked_at is not None
                else None
            )
            if unlocked:
                unlocked_total += 1
                if recent is None or unlocked_at > recent[0]:
                    recent = (unlocked_at, definition.title_zh_tw)
            cards_by_tier[definition.tier].append(
                _build_card_snapshot(
                    definition,
                    unlocked=unlocked,
                    unlocked_at=unlocked_at,
                )
            )

        tiers = tuple(
            AchievementTierSnapshot(
                tier=tier,
                cards=tuple(cards_by_tier[tier]),
                unlocked_count=sum(
                    card.unlocked for card in cards_by_tier[tier]
                ),
                total_count=len(cards_by_tier[tier]),
            )
            for tier in ACHIEVEMENT_TIER_ORDER
        )
        modes.append(
            AchievementModeSnapshot(
                world_mode=world_mode,
                mode_label=ACHIEVEMENT_MODE_LABELS[world_mode],
                tiers=tiers,
                unlocked_count=unlocked_total,
                total_count=len(definitions),
                recent_title=recent[1] if recent else "",
                recent_unlocked_at_text=(
                    _format_unlocked_at(recent[0]) if recent else ""
                ),
            )
        )
    return AchievementCabinetSnapshot(modes=tuple(modes))


def build_achievement_unlock_notification(
    snapshot: AchievementCabinetSnapshot,
    achievement_ids,
) -> AchievementUnlockNotificationSnapshot | None:
    unique_ids = tuple(
        dict.fromkeys(
            normalized
            for normalized in (
                str(item or "").strip() for item in achievement_ids or ()
            )
            if normalized
        )
    )
    cards = tuple(
        card
        for card in (
            snapshot.card_snapshot(achievement_id)
            for achievement_id in unique_ids
        )
        if card is not None and card.unlocked
    )
    if not cards:
        return None
    titles = tuple(card.title for card in cards if card.title)
    if len(titles) == 1:
        heading = "獲得新成就"
        message = titles[0]
    else:
        heading = f"一次獲得 {len(titles)} 項成就"
        message = "、".join(titles[:3])
        if len(titles) > 3:
            message += f" 等 {len(titles)} 項"
    return AchievementUnlockNotificationSnapshot(
        achievement_ids=tuple(card.slot_key for card in cards),
        titles=titles,
        primary_image_relative_path=cards[0].image_relative_path,
        heading=heading,
        message=message,
    )


def _build_card_snapshot(
    definition,
    *,
    unlocked: bool,
    unlocked_at: float | None,
) -> AchievementCardSnapshot:
    image_relative_path = f"UI/{definition.trophy.image}"
    if not unlocked:
        return AchievementCardSnapshot(
            slot_key=definition.achievement_id,
            tier=definition.tier,
            unlocked=False,
            image_relative_path=image_relative_path,
            accessible_name=f"未取得的 {definition.tier} 獎盃",
        )
    return AchievementCardSnapshot(
        slot_key=definition.achievement_id,
        tier=definition.tier,
        unlocked=True,
        image_relative_path=image_relative_path,
        title=definition.title_zh_tw,
        acquisition_method=definition.description_zh_tw,
        unlocked_at_text=_format_unlocked_at(unlocked_at),
        accessible_name=(
            f"已取得 {definition.tier} 成就：{definition.title_zh_tw}"
        ),
    )


def _format_unlocked_at(timestamp: float | None) -> str:
    if timestamp is None:
        return ""
    try:
        return datetime.fromtimestamp(float(timestamp)).strftime(
            "%Y/%m/%d %H:%M"
        )
    except (OSError, OverflowError, TypeError, ValueError):
        return ""
