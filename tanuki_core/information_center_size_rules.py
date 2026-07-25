from dataclasses import dataclass
from types import MappingProxyType


SIZE_RECOMMENDED = "recommended_16_9"
SIZE_16_10 = "comfortable_16_10"
SIZE_4_3 = "tall_4_3"
SIZE_COMPACT = "compact_16_9"


@dataclass(frozen=True)
class InformationCenterSizePreset:
    preset_id: str
    label: str
    scene_size: tuple[int, int]

    def __post_init__(self):
        if not self.preset_id or not self.label or min(self.scene_size) <= 0:
            raise ValueError("information center size presets require an id, label and size")


INFORMATION_CENTER_SIZE_PRESETS = (
    InformationCenterSizePreset(SIZE_RECOMMENDED, "系統建議（16:9）", (1280, 720)),
    InformationCenterSizePreset(SIZE_16_10, "舒適閱讀（16:10）", (1280, 800)),
    InformationCenterSizePreset(SIZE_4_3, "垂直內容（4:3）", (1200, 900)),
    InformationCenterSizePreset(SIZE_COMPACT, "白板優先（裁切邊景）", (720, 420)),
)

INFORMATION_CENTER_SIZE_PRESET_BY_ID = MappingProxyType(
    {preset.preset_id: preset for preset in INFORMATION_CENTER_SIZE_PRESETS}
)


def get_information_center_size_preset(preset_id):
    try:
        return INFORMATION_CENTER_SIZE_PRESET_BY_ID[str(preset_id)]
    except KeyError as exc:
        raise ValueError(f"unknown information center size preset: {preset_id}") from exc


def fit_window_size_for_preset(
    preset,
    available_size,
    navigation_height,
    minimum_size=(1, 1),
    screen_margin=48,
):
    available_width, available_height = (max(1, int(value)) for value in available_size)
    minimum_width, minimum_height = (max(1, int(value)) for value in minimum_size)
    scene_width, scene_height = preset.scene_size
    maximum_width = max(1, available_width - screen_margin * 2)
    maximum_scene_height = max(1, available_height - screen_margin * 2 - navigation_height)
    scale = min(1.0, maximum_width / scene_width, maximum_scene_height / scene_height)
    target_width = max(minimum_width, int(round(scene_width * scale)))
    target_height = max(minimum_height, int(round(scene_height * scale)) + navigation_height)
    return target_width, target_height
