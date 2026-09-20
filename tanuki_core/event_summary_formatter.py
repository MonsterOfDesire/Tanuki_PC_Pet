from __future__ import annotations

from dataclasses import dataclass
import re

from .pet_social_log_rules import (
    find_social_log_template_index,
    get_social_log_template_count,
    normalize_social_log_source,
)
from .ui_localization import (
    character_display_name,
    get_ui_locale,
    localize_character_names_in_text,
    translate_ui,
)


def _name(value):
    return character_display_name(str(value or ""))


def _number_from_text(text, default=0):
    match = re.search(r"-?\d+(?:\.\d+)?", str(text or ""))
    return match.group(0) if match else str(default)


def _event_template(event_type, default, **values):
    return translate_ui(
        f"events.summaries.{event_type}",
        default=default,
        **values,
    )


def localized_item_label(item_kind):
    item_kind = str(item_kind or "")
    defaults = {
        "ramen": "拉麵",
        "honey": "蜂蜜",
        "tea": "茶",
        "bottle": "奶瓶",
        "lollipop": "棒棒糖",
    }
    return translate_ui(
        f"items.{item_kind}",
        default=defaults.get(item_kind, item_kind),
    )


@dataclass(frozen=True)
class EventSummaryContext:
    entry: object
    original: str
    event_type: str
    metadata: dict
    actor_name: str
    target_name: str
    actor: str
    target: str

    @classmethod
    def from_entry(cls, entry):
        actor_name = str(getattr(entry, "actor_name", "") or "")
        target_name = str(getattr(entry, "target_name", "") or "")
        return cls(
            entry=entry,
            original=str(getattr(entry, "summary", "") or "").strip(),
            event_type=str(getattr(entry, "event_type", "") or ""),
            metadata=dict(getattr(entry, "metadata", {}) or {}),
            actor_name=actor_name,
            target_name=target_name,
            actor=_name(actor_name),
            target=_name(target_name),
        )


def _format_household_event(context):
    event_type = context.event_type
    if event_type == "opening_note":
        return _event_template(
            event_type,
            "魯道夫一家開始今天的桌面生活。",
            rudolf=_name("Symboli Rudolf"),
        )
    if event_type == "fund_snapshot":
        return _event_template(
            event_type,
            "目前生活費為 {amount} 元。",
            amount=_number_from_text(context.original),
        )
    if event_type == "pressure_snapshot":
        return _event_template(
            event_type,
            "家庭壓力目前為 {amount}%。",
            amount=_number_from_text(context.original),
        )
    if event_type == "player_donate_fund":
        return _event_template(
            event_type,
            "玩家捐助了 {amount} 元生活費。",
            player=_name("Player"),
            amount=abs(int(getattr(context.entry, "living_fund_delta", 0) or 0)),
        )
    if event_type in {
        "teio_drink_expense",
        "rudolf_collectible_expense",
        "rudolf_work_completed",
    }:
        defaults = {
            "teio_drink_expense": "帝寶又偷偷買了飲料。",
            "rudolf_collectible_expense": "魯道夫忍不住添購了一件收藏品。",
            "rudolf_work_completed": "魯道夫完成工作，替家裡賺了一筆生活費。",
        }
        return _event_template(
            event_type,
            defaults[event_type],
            teio=_name("Tokai Teio"),
            rudolf=_name("Symboli Rudolf"),
        )
    if event_type in {"transformation_started", "transformation_ended"}:
        return _event_template(
            event_type,
            "{character}完成形態切換。",
            character=context.actor,
        )
    return None


def _format_observe_event(context):
    if context.event_type not in {
        "observe_social_log",
        "post_observe_social_log",
    }:
        return None
    source = normalize_social_log_source(
        context.metadata.get("source")
        or (
            "post_observe_interaction"
            if context.event_type == "post_observe_social_log"
            else "observe"
        )
    )
    template_count = get_social_log_template_count(source)
    try:
        template_index = int(context.metadata.get("template_index"))
    except (TypeError, ValueError):
        template_index = -1
    if not 0 <= template_index < template_count:
        inferred_index = find_social_log_template_index(
            context.original,
            actor_name=context.actor_name,
            target_name=context.target_name,
            source_context=source,
        )
        template_index = inferred_index if inferred_index is not None else -1
    if template_index >= 0:
        return translate_ui(
            f"events.social_templates.{source}.{template_index}",
            default=(
                "{actor}和{target}相處了一會兒。"
                if source == "post_observe_interaction"
                else "{actor}注意了{target}一會兒。"
            ),
            actor=context.actor,
            target=context.target,
        )
    return _event_template(
        context.event_type,
        "{actor}注意了{target}一會兒。",
        actor=context.actor,
        target=context.target,
    )


def _format_race_event(context):
    if context.event_type == "race_completed":
        direction_key = context.metadata.get("direction_key", "")
        return _event_template(
            context.event_type,
            "{winner}在 {distance}px、{direction}的賽跑中，以 {elapsed:.1f} 秒勝過{loser}。",
            winner=_name(context.metadata.get("winner_name") or context.actor_name),
            loser=_name(context.metadata.get("loser_name") or context.target_name),
            distance=int(round(float(
                context.metadata.get("race_distance_px", 0) or 0
            ))),
            direction=translate_ui(
                f"events.directions.{direction_key}",
                default=str(direction_key),
            ),
            elapsed=float(
                context.metadata.get("race_elapsed_seconds", 0.0) or 0.0
            ),
        )
    if context.event_type == "race_declined":
        return _event_template(
            context.event_type,
            "{opponent}婉拒了{challenger}的賽跑挑戰。",
            opponent=_name(
                context.metadata.get("opponent_name") or context.actor_name
            ),
            challenger=_name(
                context.metadata.get("challenger_name") or context.target_name
            ),
        )
    return None


def _format_chorus_event(context):
    if context.event_type not in {"chorus_completed", "chorus_interrupted"}:
        return None
    performer_names = tuple(context.metadata.get("performer_names", ()) or ())
    audience_names = tuple(context.metadata.get("audience_names", ()) or ())
    separator = translate_ui("common.name_separator", default="、")
    performers = separator.join(_name(name) for name in performer_names)
    audiences = separator.join(_name(name) for name in audience_names)
    performance_key = "solo" if len(performer_names) == 1 else "ensemble"
    performance = translate_ui(
        f"events.performance.{performance_key}",
        default="獨奏" if performance_key == "solo" else "合奏",
    )
    if context.event_type == "chorus_completed":
        template_key = (
            "chorus_completed_with_audience" if audiences else "chorus_completed"
        )
        return _event_template(
            template_key,
            "{performers}完成了一場{performance}，共持續 {elapsed:.1f} 秒。",
            performers=performers,
            audiences=audiences,
            performance=performance,
            elapsed=float(
                context.metadata.get("duration_seconds", 0.0)
                or context.metadata.get("elapsed_seconds", 0.0)
                or _number_from_text(context.original)
            ),
        )
    reason = translate_ui(
        f"events.chorus_reasons.{context.metadata.get('reason', '')}",
        default=translate_ui(
            "events.chorus_reasons.default",
            default="現場狀況改變",
        ),
    )
    return _event_template(
        context.event_type,
        "{performance}因{reason}提前結束。",
        performance=performance,
        reason=reason,
    )


def _format_item_event(context):
    event_type = context.event_type
    if event_type in {
        "offer_bottle_success",
        "ground_bottle_pickup",
        "offer_bottle_feed",
        "ground_bottle_feed",
        "offer_honey_success",
        "ground_honey_pickup",
        "offer_honey_guarded",
        "offer_honey_denied",
        "offer_hover_timeout",
    }:
        return _event_template(
            event_type,
            "{actor}與{target}完成了道具互動。",
            actor=context.actor,
            target=context.target,
            tsuyoshi=_name("Tsurumaru Tsuyoshi"),
            item=localized_item_label(context.metadata.get("item_kind")),
        )
    if event_type in {"shared_ramen", "shared_tea_chat", "shared_honey"}:
        outcome = str(context.metadata.get("outcome", "") or "")
        template_key = f"{event_type}_{outcome}" if outcome else event_type
        return _event_template(
            template_key,
            "{holder}和{partner}一起享用了{item}。",
            holder=_name(
                context.metadata.get("holder_name") or context.actor_name
            ),
            partner=_name(
                context.metadata.get("partner_name") or context.target_name
            ),
            item=localized_item_label(context.metadata.get("item_kind")),
        )
    if event_type.startswith("offer_") or event_type.startswith("ground_"):
        template_key = (
            "ground_item_pickup"
            if event_type.startswith("ground_")
            else "offer_item_success"
        )
        return _event_template(
            template_key,
            "{target}享用了{item}。",
            target=context.target,
            item=localized_item_label(context.metadata.get("item_kind")),
        )
    return None


def _format_generic_event(context):
    channel = str(getattr(context.entry, "channel", "") or "")
    category = str(getattr(context.entry, "category", "") or "")
    if category == "care":
        return _event_template(
            "generic_care",
            "{actor}照護了{target}。",
            actor=context.actor,
            target=context.target,
        )
    if channel == "social" or category in {"social", "relationship"}:
        return _event_template(
            "generic_social",
            "{actor}和{target}進行了一次互動。",
            actor=context.actor,
            target=context.target,
        )
    if channel == "item" or category in {"item", "player_offer"}:
        return _event_template(
            "generic_item",
            "{actor}和{target}完成了一次道具互動。",
            actor=context.actor,
            target=context.target,
        )
    if channel == "economy" or category in {"economy", "player_help"}:
        return _event_template("generic_economy", "家庭記錄了一筆收支事件。")
    if channel == "system" or category in {"system", "debug"}:
        return _event_template("generic_system", "系統記錄了一項事件。")
    return _event_template("generic_family", "家庭記錄了一項生活事件。")


_SPECIFIC_FORMATTERS = (
    _format_household_event,
    _format_observe_event,
    _format_race_event,
    _format_chorus_event,
    _format_item_event,
)


def format_localized_event_summary(entry):
    context = EventSummaryContext.from_entry(entry)
    if get_ui_locale() == "zh_TW":
        return localize_character_names_in_text(
            context.original
            or translate_ui("events.unnamed", default="未命名事件")
        )
    for formatter in _SPECIFIC_FORMATTERS:
        formatted = formatter(context)
        if formatted is not None:
            return formatted
    return _format_generic_event(context)
