from __future__ import annotations

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


def localized_event_type_label(event_type):
    event_type = str(event_type or "")
    return translate_ui(
        f"events.types.{event_type}",
        default=event_type,
    )


def _event_template(event_type, default, **values):
    return translate_ui(
        f"events.summaries.{event_type}",
        default=default,
        **values,
    )


def localized_event_summary(entry):
    original = str(getattr(entry, "summary", "") or "").strip()
    if get_ui_locale() == "zh_TW":
        return localize_character_names_in_text(
            original or translate_ui("events.unnamed", default="未命名事件")
        )

    event_type = str(getattr(entry, "event_type", "") or "")
    metadata = dict(getattr(entry, "metadata", {}) or {})
    actor_name = str(getattr(entry, "actor_name", "") or "")
    target_name = str(getattr(entry, "target_name", "") or "")
    actor = _name(actor_name)
    target = _name(target_name)

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
            amount=_number_from_text(original),
        )
    if event_type == "pressure_snapshot":
        return _event_template(
            event_type,
            "家庭壓力目前為 {amount}%。",
            amount=_number_from_text(original),
        )
    if event_type == "player_donate_fund":
        return _event_template(
            event_type,
            "玩家捐助了 {amount} 元生活費。",
            player=_name("Player"),
            amount=abs(int(getattr(entry, "living_fund_delta", 0) or 0)),
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
            character=actor,
        )
    if event_type in {"observe_social_log", "post_observe_social_log"}:
        source = normalize_social_log_source(
            metadata.get("source")
            or (
                "post_observe_interaction"
                if event_type == "post_observe_social_log"
                else "observe"
            )
        )
        template_count = get_social_log_template_count(source)
        try:
            template_index = int(metadata.get("template_index"))
        except (TypeError, ValueError):
            template_index = -1
        if not 0 <= template_index < template_count:
            inferred_index = find_social_log_template_index(
                original,
                actor_name=actor_name,
                target_name=target_name,
                source_context=source,
            )
            template_index = (
                inferred_index if inferred_index is not None else -1
            )
        if template_index >= 0:
            return translate_ui(
                f"events.social_templates.{source}.{template_index}",
                default=(
                    "{actor}和{target}相處了一會兒。"
                    if source == "post_observe_interaction"
                    else "{actor}注意了{target}一會兒。"
                ),
                actor=actor,
                target=target,
            )
        return _event_template(
            event_type,
            "{actor}注意了{target}一會兒。",
            actor=actor,
            target=target,
        )
    if event_type == "race_completed":
        winner = _name(metadata.get("winner_name") or actor_name)
        loser = _name(metadata.get("loser_name") or target_name)
        direction = translate_ui(
            f"events.directions.{metadata.get('direction_key', '')}",
            default=str(metadata.get("direction_key", "")),
        )
        return _event_template(
            event_type,
            "{winner}在 {distance}px、{direction}的賽跑中，以 {elapsed:.1f} 秒勝過{loser}。",
            winner=winner,
            loser=loser,
            distance=int(round(float(metadata.get("race_distance_px", 0) or 0))),
            direction=direction,
            elapsed=float(metadata.get("race_elapsed_seconds", 0.0) or 0.0),
        )
    if event_type == "race_declined":
        return _event_template(
            event_type,
            "{opponent}婉拒了{challenger}的賽跑挑戰。",
            opponent=_name(metadata.get("opponent_name") or actor_name),
            challenger=_name(metadata.get("challenger_name") or target_name),
        )
    if event_type in {"chorus_completed", "chorus_interrupted"}:
        performer_names = tuple(metadata.get("performer_names", ()) or ())
        audience_names = tuple(metadata.get("audience_names", ()) or ())
        separator = translate_ui("common.name_separator", default="、")
        performers = separator.join(_name(name) for name in performer_names)
        audiences = separator.join(_name(name) for name in audience_names)
        performance_key = (
            "solo" if len(performer_names) == 1 else "ensemble"
        )
        performance = translate_ui(
            f"events.performance.{performance_key}",
            default="獨奏" if performance_key == "solo" else "合奏",
        )
        if event_type == "chorus_completed":
            template_key = (
                "chorus_completed_with_audience"
                if audiences else
                "chorus_completed"
            )
            return _event_template(
                template_key,
                "{performers}完成了一場{performance}，共持續 {elapsed:.1f} 秒。",
                performers=performers,
                audiences=audiences,
                performance=performance,
                elapsed=float(
                    metadata.get("duration_seconds", 0.0)
                    or metadata.get("elapsed_seconds", 0.0)
                    or _number_from_text(original)
                ),
            )
        reason = translate_ui(
            f"events.chorus_reasons.{metadata.get('reason', '')}",
            default=translate_ui(
                "events.chorus_reasons.default",
                default="現場狀況改變",
            ),
        )
        return _event_template(
            event_type,
            "{performance}因{reason}提前結束。",
            performance=performance,
            reason=reason,
        )

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
            actor=actor,
            target=target,
            tsuyoshi=_name("Tsurumaru Tsuyoshi"),
            item=localized_item_label(metadata.get("item_kind")),
        )

    if event_type in {"shared_ramen", "shared_tea_chat", "shared_honey"}:
        holder = _name(metadata.get("holder_name") or actor_name)
        partner = _name(metadata.get("partner_name") or target_name)
        item = localized_item_label(metadata.get("item_kind"))
        outcome = str(metadata.get("outcome", "") or "")
        template_key = f"{event_type}_{outcome}" if outcome else event_type
        return _event_template(
            template_key,
            "{holder}和{partner}一起享用了{item}。",
            holder=holder,
            partner=partner,
            item=item,
        )

    if event_type.startswith("offer_") or event_type.startswith("ground_"):
        ground = event_type.startswith("ground_")
        return _event_template(
            "ground_item_pickup" if ground else "offer_item_success",
            "{target}享用了{item}。",
            target=target,
            item=localized_item_label(metadata.get("item_kind")),
        )

    channel = str(getattr(entry, "channel", "") or "")
    category = str(getattr(entry, "category", "") or "")
    if category == "care":
        return _event_template(
            "generic_care",
            "{actor}照護了{target}。",
            actor=actor,
            target=target,
        )
    if channel == "social" or category in {"social", "relationship"}:
        return _event_template(
            "generic_social",
            "{actor}和{target}進行了一次互動。",
            actor=actor,
            target=target,
        )
    if channel == "item" or category in {"item", "player_offer"}:
        return _event_template(
            "generic_item",
            "{actor}和{target}完成了一次道具互動。",
            actor=actor,
            target=target,
        )
    if channel == "economy" or category in {"economy", "player_help"}:
        return _event_template(
            "generic_economy",
            "家庭記錄了一筆收支事件。",
        )
    if channel == "system" or category in {"system", "debug"}:
        return _event_template(
            "generic_system",
            "系統記錄了一項事件。",
        )
    return _event_template(
        "generic_family",
        "家庭記錄了一項生活事件。",
    )
