from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .manifest_rules import VALID_BANDS


DEFAULT_ANIMATION_PURPOSES = ("idle", "move")
BAND_POLICY_MATCH = "match"
BAND_POLICY_IGNORE = "ignore"
VALID_BAND_POLICIES = frozenset(
    {
        BAND_POLICY_MATCH,
        BAND_POLICY_IGNORE,
    }
)
BAND_PROBE_SCORES = {
    "normal": 60.0,
    "low": 30.0,
    "severe": 0.0,
}


class ManifestAnimationAssetManager(Protocol):
    def get_contextual_result_for_purposes(
        self,
        purposes,
        context=None,
        preferred_moods=None,
        forbidden=None,
        mood_score=None,
        ordered_preferences=False,
        excluded_variants=(),
    ):
        ...


class ManifestAnimationPet(Protocol):
    asset_manager: ManifestAnimationAssetManager

    def apply_animation_result(self, purpose, result):
        ...


def _normalize_unique_strings(values) -> tuple[str, ...]:
    normalized = []
    for value in values or ():
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return tuple(normalized)


@dataclass(frozen=True)
class ManifestAnimationRequest:
    contexts: tuple[str, ...]
    band_order: tuple[str, ...] = ()
    band_policy: str = BAND_POLICY_MATCH
    excluded_variants: tuple[tuple[str, str, str], ...] = ()

    def __post_init__(self):
        contexts = _normalize_unique_strings(self.contexts)
        band_order = _normalize_unique_strings(self.band_order)
        if not contexts:
            raise ValueError("manifest animation request requires at least one context")
        band_policy = str(self.band_policy or "").strip()
        if band_policy not in VALID_BAND_POLICIES:
            raise ValueError(
                f"unknown manifest animation band policy: {band_policy}"
            )
        if band_policy == BAND_POLICY_MATCH and not band_order:
            raise ValueError("manifest animation request requires at least one band")
        if band_policy == BAND_POLICY_IGNORE and band_order:
            raise ValueError(
                "ignore-band animation request must not declare band order"
            )
        unknown_bands = tuple(band for band in band_order if band not in VALID_BANDS)
        if unknown_bands:
            raise ValueError(
                "manifest animation request contains unknown bands: "
                + ", ".join(unknown_bands)
            )
        object.__setattr__(self, "contexts", contexts)
        object.__setattr__(self, "band_order", band_order)
        object.__setattr__(self, "band_policy", band_policy)
        excluded_variants = tuple(
            tuple(str(value or "").strip() for value in variant)
            for variant in self.excluded_variants or ()
        )
        if any(
            len(variant) != 3 or not all(variant)
            for variant in excluded_variants
        ):
            raise ValueError(
                "excluded animation variants require purpose, action and mood"
            )
        object.__setattr__(self, "excluded_variants", excluded_variants)


@dataclass(frozen=True)
class ManifestAnimationSelection:
    context: str
    band_policy: str
    band: str | None
    frames: object
    purpose: str
    action_type: str
    mood_tag: str

    def as_pet_result(self):
        return self.frames, self.action_type, self.mood_tag


@dataclass(frozen=True)
class ManifestAnimationResolution:
    found: bool
    reason: str = ""
    selection: ManifestAnimationSelection | None = None


@dataclass(frozen=True)
class ManifestAnimationApplyResult:
    applied: bool
    reason: str = ""
    selection: ManifestAnimationSelection | None = None


class ManifestAnimationResolver:
    """Resolve new scene animations from manifest contexts and bands only."""

    def resolve(
        self,
        asset_manager: ManifestAnimationAssetManager | None,
        request: ManifestAnimationRequest,
    ) -> ManifestAnimationResolution:
        if asset_manager is None:
            return ManifestAnimationResolution(
                found=False,
                reason="missing_asset_manager",
            )
        selector = getattr(
            asset_manager,
            "get_contextual_result_for_purposes",
            None,
        )
        if not callable(selector):
            return ManifestAnimationResolution(
                found=False,
                reason="context_selector_unavailable",
            )

        band_queries = (
            ((None, None),)
            if request.band_policy == BAND_POLICY_IGNORE
            else tuple(
                (band, BAND_PROBE_SCORES[band])
                for band in request.band_order
            )
        )
        for context in request.contexts:
            for band, mood_score in band_queries:
                selector_kwargs = {
                    "context": context,
                    "mood_score": mood_score,
                    "ordered_preferences": False,
                }
                if request.excluded_variants:
                    selector_kwargs["excluded_variants"] = (
                        request.excluded_variants
                    )
                result = selector(
                    DEFAULT_ANIMATION_PURPOSES,
                    **selector_kwargs,
                )
                if not result:
                    continue
                frames, purpose, action_type, mood_tag = result
                if not frames:
                    continue
                return ManifestAnimationResolution(
                    found=True,
                    selection=ManifestAnimationSelection(
                        context=context,
                        band_policy=request.band_policy,
                        band=band,
                        frames=frames,
                        purpose=purpose,
                        action_type=action_type,
                        mood_tag=mood_tag,
                    ),
                )

        return ManifestAnimationResolution(
            found=False,
            reason="no_manifest_match",
        )

    def apply(
        self,
        pet: ManifestAnimationPet | None,
        request: ManifestAnimationRequest,
    ) -> ManifestAnimationApplyResult:
        if pet is None:
            return ManifestAnimationApplyResult(
                applied=False,
                reason="missing_pet",
            )
        resolution = self.resolve(
            getattr(pet, "asset_manager", None),
            request,
        )
        if not resolution.found or resolution.selection is None:
            return ManifestAnimationApplyResult(
                applied=False,
                reason=resolution.reason,
            )
        selection = resolution.selection
        apply_animation = getattr(pet, "apply_animation_result", None)
        if not callable(apply_animation):
            return ManifestAnimationApplyResult(
                applied=False,
                reason="animation_apply_unavailable",
                selection=selection,
            )
        applied = bool(
            apply_animation(
                selection.purpose,
                selection.as_pet_result(),
            )
        )
        return ManifestAnimationApplyResult(
            applied=applied,
            reason="" if applied else "animation_apply_rejected",
            selection=selection,
        )
