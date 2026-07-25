import math
from dataclasses import dataclass
from types import MappingProxyType


FIT_CONTAIN = "contain"
FIT_COVER = "cover"
OCCLUSION_SOLID = "solid"
OCCLUSION_DARK_PIXELS = "dark_pixels"

SKIN_DIET = "diet"
SKIN_RELATION_SUMMON = "relation_summon"
SKIN_EVENT_LOG = "event_log"
SKIN_FAMILY_STATUS = "family_status"
SKIN_STATUS_SETTINGS = "status_settings"

ASSET_DIET_BACKGROUND = "diet_background"
ASSET_DIET_CHARACTER = "diet_character"
ASSET_RELATION_BACKGROUND = "relation_background"
ASSET_RELATION_CHARACTER = "relation_character"
ASSET_EVENT_BACKGROUND = "event_background"
ASSET_EVENT_CHARACTER = "event_character"
ASSET_FAMILY_BACKGROUND = "family_background"
ASSET_FAMILY_CHARACTER = "family_character"
ASSET_SETTINGS_BACKGROUND = "settings_background"
ASSET_SETTINGS_CHARACTER = "settings_character"
ASSET_DASHBOARD_SIDE_ICON = "dashboard_side_icon"


@dataclass(frozen=True)
class NormalizedRect:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("normalized rectangle values must be finite")
        if self.x < 0.0 or self.y < 0.0 or self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("normalized rectangle must have a positive size inside the source")
        if self.x + self.width > 1.0 + 1e-9 or self.y + self.height > 1.0 + 1e-9:
            raise ValueError("normalized rectangle must stay inside the source")


@dataclass(frozen=True)
class NormalizedLayerRect:
    """A source-relative layer rectangle that may overscan its clipped viewport."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("normalized layer rectangle values must be finite")
        if self.width <= 0.0 or self.height <= 0.0:
            raise ValueError("normalized layer rectangle must have a positive size")


@dataclass(frozen=True)
class GeometryRect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def rounded(self):
        return (
            int(round(self.x)),
            int(round(self.y)),
            max(0, int(round(self.width))),
            max(0, int(round(self.height))),
        )


@dataclass(frozen=True)
class UiAssetSpec:
    key: str
    relative_path: str
    source_size: tuple[int, int]
    animated: bool = False
    first_frame_only: bool = False
    frame_offsets: tuple[tuple[int, int], ...] = ()

    def __post_init__(self):
        relative_path = str(self.relative_path).replace("\\", "/")
        if not self.key or not relative_path.startswith("UI/"):
            raise ValueError("UI assets must have a key and a path below UI/")
        if relative_path.startswith("/") or "/../" in f"/{relative_path}/":
            raise ValueError("UI asset paths must be relative and cannot contain '..'")
        if len(self.source_size) != 2 or min(self.source_size) <= 0:
            raise ValueError("UI assets must declare a positive source size")
        if any(len(offset) != 2 for offset in self.frame_offsets):
            raise ValueError("frame offsets must contain x/y pairs")


@dataclass(frozen=True)
class UiSkinSpec:
    key: str
    background_asset_key: str
    content_rect: NormalizedRect
    minimum_frame_size: tuple[int, int]
    minimum_window_size: tuple[int, int]
    minimum_content_size: tuple[int, int]
    surface_role: str
    fit_mode: str = FIT_COVER
    foreground_asset_key: str = ""
    foreground_rect: NormalizedRect | NormalizedLayerRect | None = None
    foreground_frame_map: tuple[int, ...] = ()
    occlusion_rects: tuple[NormalizedRect, ...] = ()
    occlusion_role: str = ""
    occlusion_mask_mode: str = OCCLUSION_SOLID

    def __post_init__(self):
        if self.fit_mode not in {FIT_CONTAIN, FIT_COVER}:
            raise ValueError(f"unsupported fit mode: {self.fit_mode}")
        if (
            min(self.minimum_frame_size) <= 0
            or min(self.minimum_window_size) <= 0
            or min(self.minimum_content_size) <= 0
        ):
            raise ValueError("skin minimum sizes must be positive")
        if any(
            window_size > frame_size
            for window_size, frame_size in zip(
                self.minimum_window_size,
                self.minimum_frame_size,
            )
        ):
            raise ValueError("skin minimum window size cannot exceed its scene floor")
        if bool(self.foreground_asset_key) != bool(self.foreground_rect):
            raise ValueError("foreground asset and foreground rectangle must be declared together")
        if self.foreground_frame_map and not self.foreground_asset_key:
            raise ValueError("foreground frame mapping requires a foreground asset")
        if any(frame_number < 0 for frame_number in self.foreground_frame_map):
            raise ValueError("foreground frame mapping cannot contain negative frame numbers")
        if bool(self.occlusion_rects) != bool(self.occlusion_role):
            raise ValueError("occlusion rectangles and role must be declared together")
        if self.occlusion_mask_mode not in {OCCLUSION_SOLID, OCCLUSION_DARK_PIXELS}:
            raise ValueError(f"unsupported occlusion mask mode: {self.occlusion_mask_mode}")
        if self.occlusion_mask_mode != OCCLUSION_SOLID and not self.occlusion_rects:
            raise ValueError("non-solid occlusion masks require sample rectangles")


@dataclass(frozen=True)
class UiAvatarSourceSpec:
    character_name: str
    asset_key: str
    crop_rect: NormalizedRect | None = None


def compute_scene_rect(container_size, source_size, fit_mode=FIT_COVER):
    container_width, container_height = (float(value) for value in container_size)
    source_width, source_height = (float(value) for value in source_size)
    if min(container_width, container_height, source_width, source_height) <= 0.0:
        raise ValueError("scene and container sizes must be positive")
    if fit_mode not in {FIT_CONTAIN, FIT_COVER}:
        raise ValueError(f"unsupported fit mode: {fit_mode}")

    width_scale = container_width / source_width
    height_scale = container_height / source_height
    scale = min(width_scale, height_scale) if fit_mode == FIT_CONTAIN else max(width_scale, height_scale)
    scene_width = source_width * scale
    scene_height = source_height * scale
    return GeometryRect(
        x=(container_width - scene_width) / 2.0,
        y=(container_height - scene_height) / 2.0,
        width=scene_width,
        height=scene_height,
    )


def project_normalized_rect(rect, outer_rect):
    return GeometryRect(
        x=outer_rect.x + outer_rect.width * rect.x,
        y=outer_rect.y + outer_rect.height * rect.y,
        width=outer_rect.width * rect.width,
        height=outer_rect.height * rect.height,
    )


def expand_rect_to_minimum(rect, minimum_size, bounds):
    minimum_width, minimum_height = (float(value) for value in minimum_size)
    target_width = min(bounds.width, max(rect.width, minimum_width))
    target_height = min(bounds.height, max(rect.height, minimum_height))
    target_x = rect.x + (rect.width - target_width) / 2.0
    target_y = rect.y + (rect.height - target_height) / 2.0
    target_x = max(bounds.x, min(target_x, bounds.right - target_width))
    target_y = max(bounds.y, min(target_y, bounds.bottom - target_height))
    return GeometryRect(target_x, target_y, target_width, target_height)


def align_scene_to_focus(container_size, scene_size, focus_rect):
    """Position an oversized scene so its protected content is cropped last."""

    container_width, container_height = (float(value) for value in container_size)
    scene_width, scene_height = (float(value) for value in scene_size)
    if min(container_width, container_height, scene_width, scene_height) <= 0.0:
        raise ValueError("scene focus alignment requires positive sizes")

    def aligned_origin(container_length, scene_length, focus_start, focus_length):
        if scene_length <= container_length:
            return (container_length - scene_length) / 2.0

        centered = (
            container_length / 2.0
            - (focus_start + focus_length / 2.0)
        )
        lower_bound = container_length - scene_length
        upper_bound = 0.0
        if focus_length <= container_length:
            lower_bound = max(lower_bound, -focus_start)
            upper_bound = min(
                upper_bound,
                container_length - focus_start - focus_length,
            )
        return max(lower_bound, min(centered, upper_bound))

    return GeometryRect(
        x=aligned_origin(
            container_width,
            scene_width,
            focus_rect.x,
            focus_rect.width,
        ),
        y=aligned_origin(
            container_height,
            scene_height,
            focus_rect.y,
            focus_rect.height,
        ),
        width=scene_width,
        height=scene_height,
    )


def compute_skinned_scene_layout(
    frame_size,
    skin_spec,
    asset_specs=None,
):
    """Return scene geometry plus scene-local content geometry.

    The scene scales normally until it reaches ``minimum_frame_size``. Below
    that breakpoint the scene keeps its scale and moves behind the frame,
    preserving the content area while outer artwork is clipped.
    """

    asset_specs = UI_ASSET_SPECS if asset_specs is None else asset_specs
    background = asset_specs[skin_spec.background_asset_key]
    natural_scene = compute_scene_rect(
        frame_size,
        background.source_size,
        skin_spec.fit_mode,
    )
    minimum_scene = compute_scene_rect(
        skin_spec.minimum_frame_size,
        background.source_size,
        skin_spec.fit_mode,
    )
    scene_width = max(natural_scene.width, minimum_scene.width)
    scene_height = max(natural_scene.height, minimum_scene.height)
    scene_bounds = GeometryRect(0.0, 0.0, scene_width, scene_height)
    viewport_rect = compute_scene_rect(
        (scene_width, scene_height),
        background.source_size,
        skin_spec.fit_mode,
    )
    content_rect = expand_rect_to_minimum(
        project_normalized_rect(skin_spec.content_rect, viewport_rect),
        skin_spec.minimum_content_size,
        scene_bounds,
    )
    scene_rect = align_scene_to_focus(
        frame_size,
        (scene_width, scene_height),
        content_rect,
    )
    return scene_rect, content_rect


def intersect_geometry_rect(first, second):
    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(first.right, second.right)
    bottom = min(first.bottom, second.bottom)
    return GeometryRect(
        left,
        top,
        max(0.0, right - left),
        max(0.0, bottom - top),
    )


def compute_content_rect(frame_size, skin_spec, asset_specs=None):
    scene_rect, content_rect = compute_skinned_scene_layout(
        frame_size,
        skin_spec,
        asset_specs,
    )
    return GeometryRect(
        scene_rect.x + content_rect.x,
        scene_rect.y + content_rect.y,
        content_rect.width,
        content_rect.height,
    )


UI_ASSET_SPECS = MappingProxyType(
    {
        ASSET_DIET_BACKGROUND: UiAssetSpec(
            ASSET_DIET_BACKGROUND,
            "UI/diet.png",
            (1200, 900),
        ),
        ASSET_DIET_CHARACTER: UiAssetSpec(
            ASSET_DIET_CHARACTER,
            "UI/diet_char.gif",
            (500, 500),
            animated=True,
        ),
        ASSET_RELATION_BACKGROUND: UiAssetSpec(
            ASSET_RELATION_BACKGROUND,
            "UI/relation_summon.gif",
            (1920, 1080),
            animated=True,
        ),
        ASSET_RELATION_CHARACTER: UiAssetSpec(
            ASSET_RELATION_CHARACTER,
            "UI/relation_summon_char.gif",
            (500, 500),
            animated=True,
        ),
        ASSET_EVENT_BACKGROUND: UiAssetSpec(
            ASSET_EVENT_BACKGROUND,
            "UI/event_note.jpg",
            (1600, 900),
        ),
        ASSET_EVENT_CHARACTER: UiAssetSpec(
            ASSET_EVENT_CHARACTER,
            "UI/event_note_char.gif",
            (500, 500),
            animated=True,
        ),
        ASSET_FAMILY_BACKGROUND: UiAssetSpec(
            ASSET_FAMILY_BACKGROUND,
            "UI/family_status_abstract.png",
            (2420, 1490),
        ),
        ASSET_FAMILY_CHARACTER: UiAssetSpec(
            ASSET_FAMILY_CHARACTER,
            "UI/family_status_abstract_char.gif",
            (500, 500),
            animated=True,
        ),
        ASSET_SETTINGS_BACKGROUND: UiAssetSpec(
            ASSET_SETTINGS_BACKGROUND,
            "UI/status_setting.png",
            (2560, 1440),
        ),
        ASSET_SETTINGS_CHARACTER: UiAssetSpec(
            ASSET_SETTINGS_CHARACTER,
            "UI/status_setting_char.gif",
            (500, 500),
            animated=True,
        ),
        ASSET_DASHBOARD_SIDE_ICON: UiAssetSpec(
            ASSET_DASHBOARD_SIDE_ICON,
            "UI/side.png",
            (393, 388),
        ),
        "avatar_air_groove": UiAssetSpec(
            "avatar_air_groove",
            "UI/family_icon/Air Groove.gif",
            (252, 378),
            animated=True,
            first_frame_only=True,
        ),
        "avatar_sirius_symboli": UiAssetSpec(
            "avatar_sirius_symboli",
            "UI/family_icon/Sirius Symboli.gif",
            (342, 398),
            animated=True,
            first_frame_only=True,
        ),
        "avatar_symboli_rudolf": UiAssetSpec(
            "avatar_symboli_rudolf",
            "UI/family_icon/Symboli Rudolf.gif",
            (315, 354),
            animated=True,
            first_frame_only=True,
        ),
        "avatar_tokai_teio": UiAssetSpec(
            "avatar_tokai_teio",
            "UI/family_icon/Tokai Teio.gif",
            (281, 382),
            animated=True,
            first_frame_only=True,
        ),
        "avatar_tsurumaru_tsuyoshi": UiAssetSpec(
            "avatar_tsurumaru_tsuyoshi",
            "UI/family_icon/Tsurumaru Tsuyoshi.gif",
            (235, 327),
            animated=True,
            first_frame_only=True,
        ),
    }
)


UI_SKIN_SPECS = MappingProxyType(
    {
        SKIN_DIET: UiSkinSpec(
            key=SKIN_DIET,
            background_asset_key=ASSET_DIET_BACKGROUND,
            content_rect=NormalizedRect(0.423, 0.209, 0.508, 0.392),
            minimum_frame_size=(680, 510),
            minimum_window_size=(680, 510),
            minimum_content_size=(330, 180),
            surface_role="glass",
            fit_mode=FIT_CONTAIN,
            foreground_asset_key=ASSET_DIET_CHARACTER,
            foreground_rect=NormalizedLayerRect(0.015, 0.380, 0.400, 0.540),
        ),
        SKIN_RELATION_SUMMON: UiSkinSpec(
            key=SKIN_RELATION_SUMMON,
            background_asset_key=ASSET_RELATION_BACKGROUND,
            content_rect=NormalizedRect(0.405, 0.070, 0.440, 0.475),
            minimum_frame_size=(1080, 608),
            minimum_window_size=(520, 320),
            minimum_content_size=(480, 300),
            surface_role="whiteboard_content",
            fit_mode=FIT_CONTAIN,
            foreground_asset_key=ASSET_RELATION_CHARACTER,
            foreground_rect=NormalizedLayerRect(0.5875, 0.2889, 0.4505, 0.8009),
            foreground_frame_map=(3, 3, 0, 1, 1, 0, 3, 3, 0, 1, 1, 0, 0),
            occlusion_rects=(
                NormalizedRect(0.421, 0.130, 0.416, 0.175),
                NormalizedRect(0.440, 0.318, 0.344, 0.168),
            ),
            occlusion_role="whiteboard",
            occlusion_mask_mode=OCCLUSION_DARK_PIXELS,
        ),
        SKIN_EVENT_LOG: UiSkinSpec(
            key=SKIN_EVENT_LOG,
            background_asset_key=ASSET_EVENT_BACKGROUND,
            content_rect=NormalizedRect(0.122, 0.037, 0.760, 0.566),
            minimum_frame_size=(900, 506),
            minimum_window_size=(700, 300),
            minimum_content_size=(680, 280),
            surface_role="chalkboard",
            fit_mode=FIT_CONTAIN,
            foreground_asset_key=ASSET_EVENT_CHARACTER,
            foreground_rect=NormalizedLayerRect(-0.017, 0.460, 0.300, 0.540),
        ),
        SKIN_FAMILY_STATUS: UiSkinSpec(
            key=SKIN_FAMILY_STATUS,
            background_asset_key=ASSET_FAMILY_BACKGROUND,
            content_rect=NormalizedRect(0.100, 0.080, 0.800, 0.750),
            minimum_frame_size=(900, 555),
            minimum_window_size=(720, 420),
            minimum_content_size=(700, 400),
            surface_role="frosted",
            fit_mode=FIT_CONTAIN,
            foreground_asset_key=ASSET_FAMILY_CHARACTER,
            foreground_rect=NormalizedLayerRect(0.575, 0.490, 0.300, 0.500),
        ),
        SKIN_STATUS_SETTINGS: UiSkinSpec(
            key=SKIN_STATUS_SETTINGS,
            background_asset_key=ASSET_SETTINGS_BACKGROUND,
            content_rect=NormalizedRect(0.160, 0.030, 0.680, 0.470),
            minimum_frame_size=(900, 506),
            minimum_window_size=(620, 260),
            minimum_content_size=(600, 240),
            surface_role="dark",
            fit_mode=FIT_CONTAIN,
            foreground_asset_key=ASSET_SETTINGS_CHARACTER,
            foreground_rect=NormalizedLayerRect(0.720, 0.390, 0.280, 0.500),
        ),
    }
)


FAMILY_AVATAR_SPECS = (
    UiAvatarSourceSpec("Air Groove", "avatar_air_groove", NormalizedRect(0.00, 0.00, 1.00, 0.67)),
    UiAvatarSourceSpec("Sirius Symboli", "avatar_sirius_symboli", NormalizedRect(0.00, 0.00, 1.00, 0.72)),
    UiAvatarSourceSpec("Symboli Rudolf", "avatar_symboli_rudolf", NormalizedRect(0.00, 0.00, 1.00, 0.68)),
    UiAvatarSourceSpec("Tokai Teio", "avatar_tokai_teio", NormalizedRect(0.00, 0.00, 1.00, 0.66)),
    UiAvatarSourceSpec("Tsurumaru Tsuyoshi", "avatar_tsurumaru_tsuyoshi", NormalizedRect(0.00, 0.00, 1.00, 0.72)),
)


def iter_runtime_asset_paths():
    return tuple(spec.relative_path for spec in UI_ASSET_SPECS.values())
