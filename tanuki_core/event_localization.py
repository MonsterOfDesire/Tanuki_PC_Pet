from __future__ import annotations

from .event_summary_formatter import (
    format_localized_event_summary,
    localized_item_label,
)
from .ui_localization import translate_ui


def localized_event_type_label(event_type):
    event_type = str(event_type or "")
    return translate_ui(
        f"events.types.{event_type}",
        default=event_type,
    )


def localized_event_summary(entry):
    return format_localized_event_summary(entry)


__all__ = (
    "localized_event_summary",
    "localized_event_type_label",
    "localized_item_label",
)
