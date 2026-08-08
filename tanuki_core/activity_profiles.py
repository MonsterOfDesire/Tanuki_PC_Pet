from __future__ import annotations

from dataclasses import dataclass

from .asset_selection_rules import get_mood_band
from .manifest_animation_resolver import (
    BAND_POLICY_IGNORE,
    BAND_POLICY_MATCH,
    VALID_BAND_POLICIES,
    ManifestAnimationRequest,
)
from .manifest_rules import VALID_BANDS


def _normalize_unique_strings(values) -> tuple[str, ...]:
    normalized = []
    for value in values or ():
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return tuple(normalized)


@dataclass(frozen=True)
class ActivityAnimationBinding:
    contexts: tuple[str, ...]
    band_policy: str = BAND_POLICY_MATCH
    fallback_bands: tuple[str, ...] = ()

    def __post_init__(self):
        contexts = _normalize_unique_strings(self.contexts)
        band_policy = str(self.band_policy or "").strip()
        fallback_bands = _normalize_unique_strings(self.fallback_bands)
        if not contexts:
            raise ValueError("activity animation binding requires contexts")
        if band_policy not in VALID_BAND_POLICIES:
            raise ValueError(
                f"unknown activity animation band policy: {band_policy}"
            )
        unknown_bands = tuple(
            band
            for band in fallback_bands
            if band not in VALID_BANDS
        )
        if unknown_bands:
            raise ValueError(
                "activity animation binding contains unknown fallback bands: "
                + ", ".join(unknown_bands)
            )
        if band_policy == BAND_POLICY_IGNORE and fallback_bands:
            raise ValueError(
                "ignore-band activity animation must not declare fallbacks"
            )
        object.__setattr__(self, "contexts", contexts)
        object.__setattr__(self, "band_policy", band_policy)
        object.__setattr__(self, "fallback_bands", fallback_bands)

    def build_request(
        self,
        mood_score: float,
        *,
        band_override: str = "",
    ) -> ManifestAnimationRequest:
        band_override = str(band_override or "").strip()
        if band_override and band_override not in VALID_BANDS:
            raise ValueError(
                f"unknown activity animation band override: {band_override}"
            )
        if self.band_policy == BAND_POLICY_IGNORE:
            if band_override:
                raise ValueError(
                    "ignore-band activity animation cannot override band"
                )
            return ManifestAnimationRequest(
                contexts=self.contexts,
                band_policy=BAND_POLICY_IGNORE,
            )
        current_band = band_override or get_mood_band(float(mood_score))
        band_order = _normalize_unique_strings(
            (current_band, *self.fallback_bands)
        )
        return ManifestAnimationRequest(
            contexts=self.contexts,
            band_order=band_order,
            band_policy=BAND_POLICY_MATCH,
        )
