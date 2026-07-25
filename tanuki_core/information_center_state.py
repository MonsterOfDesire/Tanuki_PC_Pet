from dataclasses import dataclass

from .information_center_size_rules import INFORMATION_CENTER_SIZE_PRESET_BY_ID
from .information_center_spec import (
    DEFAULT_INFORMATION_CENTER_PAGE,
    INFORMATION_CENTER_PAGE_BY_ID,
)


DEFAULT_INFORMATION_CENTER_WIDTH = 1120
DEFAULT_INFORMATION_CENTER_HEIGHT = 720


@dataclass(frozen=True)
class InformationCenterConfigState:
    x: int | None = None
    y: int | None = None
    width: int = DEFAULT_INFORMATION_CENTER_WIDTH
    height: int = DEFAULT_INFORMATION_CENTER_HEIGHT
    page_id: str = DEFAULT_INFORMATION_CENTER_PAGE
    size_preset_id: str = ""

    @property
    def has_saved_position(self):
        return self.x is not None and self.y is not None


def _safe_optional_int(value, default=None):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_positive_int(value, default):
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return int(default)
    return normalized if normalized > 0 else int(default)


def _normalize_position(x, y, default_x=None, default_y=None):
    normalized_x = _safe_optional_int(x, default_x)
    normalized_y = _safe_optional_int(y, default_y)
    if normalized_x is None or normalized_y is None:
        return None, None
    return normalized_x, normalized_y


def _safe_page_id(value, default):
    normalized = str(value or "")
    if normalized in INFORMATION_CENTER_PAGE_BY_ID:
        return normalized
    return str(default)


def _safe_size_preset_id(value, default):
    normalized = str(value or "")
    if not normalized or normalized in INFORMATION_CENTER_SIZE_PRESET_BY_ID:
        return normalized
    return str(default)


def build_information_center_config_state(
    *,
    x=None,
    y=None,
    width=DEFAULT_INFORMATION_CENTER_WIDTH,
    height=DEFAULT_INFORMATION_CENTER_HEIGHT,
    page_id=DEFAULT_INFORMATION_CENTER_PAGE,
    size_preset_id="",
):
    defaults = InformationCenterConfigState()
    normalized_x, normalized_y = _normalize_position(x, y)
    return InformationCenterConfigState(
        x=normalized_x,
        y=normalized_y,
        width=_safe_positive_int(width, defaults.width),
        height=_safe_positive_int(height, defaults.height),
        page_id=_safe_page_id(page_id, defaults.page_id),
        size_preset_id=_safe_size_preset_id(
            size_preset_id,
            defaults.size_preset_id,
        ),
    )


def normalize_information_center_config_state(raw_state, defaults=None):
    if isinstance(raw_state, InformationCenterConfigState):
        return raw_state
    defaults = (
        defaults
        if isinstance(defaults, InformationCenterConfigState)
        else InformationCenterConfigState()
    )
    raw_state = raw_state if isinstance(raw_state, dict) else {}
    normalized_x, normalized_y = _normalize_position(
        raw_state.get("x"),
        raw_state.get("y"),
        defaults.x,
        defaults.y,
    )
    return InformationCenterConfigState(
        x=normalized_x,
        y=normalized_y,
        width=_safe_positive_int(
            raw_state.get("width", defaults.width),
            defaults.width,
        ),
        height=_safe_positive_int(
            raw_state.get("height", defaults.height),
            defaults.height,
        ),
        page_id=_safe_page_id(
            raw_state.get("page_id", defaults.page_id),
            defaults.page_id,
        ),
        size_preset_id=_safe_size_preset_id(
            raw_state.get("size_preset_id", defaults.size_preset_id),
            defaults.size_preset_id,
        ),
    )


def information_center_config_state_to_payload(state):
    normalized = (
        state
        if isinstance(state, InformationCenterConfigState)
        else InformationCenterConfigState()
    )
    return {
        "x": normalized.x,
        "y": normalized.y,
        "width": int(normalized.width),
        "height": int(normalized.height),
        "page_id": str(normalized.page_id),
        "size_preset_id": str(normalized.size_preset_id),
    }


def clamp_information_center_geometry(
    state,
    available_geometry,
    minimum_size=(1, 1),
):
    left, top, available_width, available_height = (
        int(value)
        for value in available_geometry
    )
    minimum_width, minimum_height = (
        max(1, int(value))
        for value in minimum_size
    )
    available_width = max(1, available_width)
    available_height = max(1, available_height)

    maximum_width = max(minimum_width, available_width)
    maximum_height = max(minimum_height, available_height)
    width = max(minimum_width, min(int(state.width), maximum_width))
    height = max(minimum_height, min(int(state.height), maximum_height))

    if not state.has_saved_position:
        return None, None, width, height

    maximum_x = left + available_width - width
    maximum_y = top + available_height - height
    x = left if maximum_x < left else max(left, min(int(state.x), maximum_x))
    y = top if maximum_y < top else max(top, min(int(state.y), maximum_y))
    return x, y, width, height
