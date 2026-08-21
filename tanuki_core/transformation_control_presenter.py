from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .ui_localization import character_display_name, translate_ui


FORM_BASE = "base"
FORM_TRANSFORMED = "transformed"
SANDBOX_WORLD_MODE = "sandbox"

TRANSFORMATION_CONTROL_NAMES = {
    "Tokai Teio": "帝寶",
    "Symboli Rudolf": "魯道夫",
}

AUTONOMOUS_SOURCES = frozenset(
    {
        "autonomous_start",
        "autonomous_end",
        "sandbox_autonomous_start",
        "sandbox_autonomous_end",
    }
)


@dataclass(frozen=True)
class TransformationButtonPresentation:
    character_name: str
    text: str
    enabled: bool
    tooltip: str


@dataclass(frozen=True)
class TransformationControlPresentation:
    buttons: tuple[TransformationButtonPresentation, ...]
    status_text: str
    should_poll: bool
    poll_interval_ms: int
    has_active_operation: bool


def build_transformation_control_presentation(
    state_payloads: Mapping[str, Mapping[str, object]],
    *,
    world_mode: str,
) -> TransformationControlPresentation:
    sandbox = str(world_mode or "") == SANDBOX_WORLD_MODE
    normalized_states = tuple(
        _normalized_state(
            character_name,
            state_payloads.get(character_name, {}),
        )
        for character_name in TRANSFORMATION_CONTROL_NAMES
    )
    active_operation = any(
        state["active"] or state["manual_end_requested"]
        for state in normalized_states
    )
    buttons = tuple(
        _button_presentation(state, sandbox=sandbox)
        for state in normalized_states
    )
    return TransformationControlPresentation(
        buttons=buttons,
        status_text=_status_text(normalized_states, sandbox=sandbox),
        should_poll=sandbox,
        poll_interval_ms=100 if active_operation else 400 if sandbox else 0,
        has_active_operation=active_operation,
    )


def build_transformation_completion_text(
    character_name: str,
    target_form: str,
) -> str:
    display_name = TRANSFORMATION_CONTROL_NAMES.get(
        str(character_name or ""),
        str(character_name or ""),
    )
    display_name = character_display_name(character_name) or display_name
    if str(target_form or "") == FORM_BASE:
        return translate_ui(
            "transformation.completed_base",
            default="{character}已解除變身，目前為普通形態。",
            character=display_name,
        )
    return translate_ui(
        "transformation.completed_transformed",
        default="{character}已完成變身，目前為變身形態。",
        character=display_name,
    )


def _normalized_state(
    character_name: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    current_form = str(payload.get("current_form", FORM_BASE) or FORM_BASE)
    target_form = str(payload.get("target_form", "") or "")
    source = str(payload.get("source", "") or "")
    return {
        "character_name": character_name,
        "display_name": character_display_name(character_name),
        "available": bool(payload.get("available", False)),
        "current_form": current_form,
        "target_form": target_form,
        "active": bool(payload.get("active", False)),
        "manual_end_requested": bool(
            payload.get("manual_end_requested", False)
        ),
        "autonomous": bool(payload.get("auto_session", False))
        or source in AUTONOMOUS_SOURCES,
    }


def _button_presentation(
    state: Mapping[str, object],
    *,
    sandbox: bool,
) -> TransformationButtonPresentation:
    display_name = str(state["display_name"])
    active = bool(state["active"])
    waiting = bool(state["manual_end_requested"])
    current_form = str(state["current_form"])
    target_form = str(state["target_form"])

    if waiting:
        text = translate_ui("transformation.button_waiting", default="等待解除{character}變身", character=display_name)
        tooltip = translate_ui("transformation.tooltip_waiting", default="解除要求已排入等待；角色回到地面且空閒後會安全解除。")
    elif active and target_form == FORM_BASE:
        text = translate_ui("transformation.button_reverting", default="{character}解除變身中", character=display_name)
        tooltip = translate_ui("transformation.tooltip_reverting", default="角色正在安全解除變身。")
    elif active:
        text = translate_ui("transformation.button_transforming", default="{character}變身中", character=display_name)
        tooltip = translate_ui("transformation.tooltip_transforming", default="角色正在切換為變身形態。")
    elif current_form == FORM_TRANSFORMED:
        text = translate_ui("transformation.button_revert", default="解除{character}變身", character=display_name)
        tooltip = translate_ui("transformation.tooltip_revert", default="手動解除目前形態；忙碌或在空中時會等待安全時機。")
    else:
        text = translate_ui("transformation.button_transform", default="手動變身{character}", character=display_name)
        tooltip = translate_ui("transformation.tooltip_transform", default="手動切換為變身形態；不會觸發正式事件或結算。")

    if not sandbox:
        tooltip = translate_ui("transformation.tooltip_sandbox_only", default="只可在沙盒模式手動控制形態。")
    elif not bool(state["available"]):
        tooltip = translate_ui("transformation.tooltip_unavailable", default="執行中的 Runtime 找不到這個角色或其變身狀態。")

    return TransformationButtonPresentation(
        character_name=str(state["character_name"]),
        text=text,
        enabled=(
            sandbox
            and bool(state["available"])
            and not active
            and not waiting
        ),
        tooltip=tooltip,
    )


def _status_text(
    states: tuple[Mapping[str, object], ...],
    *,
    sandbox: bool,
) -> str:
    if not sandbox:
        return translate_ui(
            "transformation.status_sandbox_only",
            default="切換至沙盒模式後，可查看並手動控制{teio}與{rudolf}的形態。",
            teio=character_display_name("Tokai Teio"),
            rudolf=character_display_name("Symboli Rudolf"),
        )

    unavailable = [
        str(state["display_name"])
        for state in states
        if not bool(state["available"])
    ]
    if unavailable:
        return translate_ui(
            "transformation.status_unavailable",
            default="目前無法取得{characters}的形態狀態。",
            characters=translate_ui("common.name_separator", default="、").join(unavailable),
        )

    descriptions = []
    for state in states:
        display_name = str(state["display_name"])
        if bool(state["manual_end_requested"]):
            descriptions.append(translate_ui(
                "transformation.status_waiting",
                default="{character}解除變身已排入等待；角色回到地面且空閒後會安全解除。",
                character=display_name,
            ))
        elif bool(state["active"]):
            action = (
                "解除變身"
                if str(state["target_form"]) == FORM_BASE
                else "變身"
            )
            descriptions.append(translate_ui(
                "transformation.status_active",
                default="{character}{action}中。",
                character=display_name,
                action=translate_ui(
                    "transformation.action_revert" if action == "解除變身" else
                    "transformation.action_transform",
                    default=action,
                ),
            ))
        elif str(state["current_form"]) == FORM_TRANSFORMED:
            source = translate_ui(
                "transformation.source_autonomous"
                if bool(state["autonomous"]) else
                "transformation.source_manual",
                default="自主" if bool(state["autonomous"]) else "手動",
            )
            descriptions.append(translate_ui(
                "transformation.status_transformed",
                default="{character}目前為{source}變身形態；到期後會自動安全解除，也可使用按鈕提前解除。",
                character=display_name,
                source=source,
            ))

    if descriptions:
        return " ".join(descriptions)
    return translate_ui(
        "transformation.status_base",
        default="{teio}、{rudolf}目前皆為普通形態；沙盒仍可能自主變身。",
        teio=character_display_name("Tokai Teio"),
        rudolf=character_display_name("Symboli Rudolf"),
    )
