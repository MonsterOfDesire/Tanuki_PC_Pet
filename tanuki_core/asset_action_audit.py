from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import json

from .validation import load_manifest_entries


ANIMATION_EXTENSIONS = {".gif", ".png", ".webp"}
KNOWN_PURPOSES = {"idle", "move", "drag", "interaction"}
SUSPICIOUS_TOKENS = ("darg", "dacne", "Teioy", "lolipop")
RANDOM_COVERAGE_PURPOSES = ("idle", "move")
RANDOM_COVERAGE_BANDS = ("normal", "low", "severe")


@dataclass(frozen=True)
class AssetActionRecord:
    character: str
    file_name: str
    purpose: str
    action: str
    mood: str


@dataclass(frozen=True)
class ActionMoodInventory:
    total_assets: int
    purpose_counts: dict[str, int]
    action_moods: dict[tuple[str, str], tuple[str, ...]]


@dataclass(frozen=True)
class ManifestAuditResult:
    character: str
    manifest_path: str
    manifest_entry_count: int
    asset_count: int
    manifest_missing_files: tuple[str, ...] = ()
    assets_missing_manifest: tuple[str, ...] = ()
    manifest_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RandomManifestCoverageEntry:
    character: str
    purpose: str
    band: str
    asset_count: int
    files: tuple[str, ...] = ()


@dataclass(frozen=True)
class RandomManifestCoverageIssue:
    character: str
    purpose: str
    band: str
    issue: str = "missing_random_manifest_assets"


@dataclass(frozen=True)
class CandidateRequirement:
    feature: str
    role: str
    character: str
    candidates: tuple[tuple[str, str], ...]
    item_kind: str = ""
    exact_mood: str = ""
    required_context: str = ""
    preferred_moods: tuple[str, ...] = ()
    source: str = ""


@dataclass(frozen=True)
class CandidateIssue:
    feature: str
    role: str
    character: str
    purpose: str = ""
    action: str = ""
    item_kind: str = ""
    exact_mood: str = ""
    required_context: str = ""
    issue: str = ""
    source: str = ""


@dataclass(frozen=True)
class AssetActionAuditReport:
    assets_dir: str
    records: tuple[AssetActionRecord, ...]
    inventories: dict[str, ActionMoodInventory]
    naming_issues: tuple[str, ...]
    manifest_results: tuple[ManifestAuditResult, ...]
    random_manifest_coverage: tuple[RandomManifestCoverageEntry, ...]
    random_manifest_coverage_issues: tuple[RandomManifestCoverageIssue, ...]
    requirements: tuple[CandidateRequirement, ...]
    candidate_issues: tuple[CandidateIssue, ...]


def parse_asset_filename(file_name: str) -> tuple[str, str, str]:
    base_name = Path(file_name).stem
    if "-" in base_name:
        name_part, mood = base_name.split("-", 1)
    else:
        name_part, mood = base_name, ""
    parts = name_part.split("_")
    purpose = parts[0] if parts else ""
    action = "_".join(parts[1:]) if len(parts) > 1 else "default"
    return purpose, action, mood


def scan_asset_records(assets_dir: str | Path) -> tuple[AssetActionRecord, ...]:
    root = Path(assets_dir)
    if not root.exists():
        return ()
    records: list[AssetActionRecord] = []
    for character_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for asset_path in sorted(character_dir.iterdir()):
            if not asset_path.is_file() or asset_path.suffix.lower() not in ANIMATION_EXTENSIONS:
                continue
            purpose, action, mood = parse_asset_filename(asset_path.name)
            records.append(
                AssetActionRecord(
                    character=character_dir.name,
                    file_name=asset_path.name,
                    purpose=purpose,
                    action=action,
                    mood=mood,
                )
            )
    return tuple(records)


def build_action_mood_inventory(records: tuple[AssetActionRecord, ...]) -> dict[str, ActionMoodInventory]:
    grouped: dict[str, list[AssetActionRecord]] = defaultdict(list)
    for record in records:
        grouped[record.character].append(record)

    inventories: dict[str, ActionMoodInventory] = {}
    for character, character_records in sorted(grouped.items()):
        purpose_counts: dict[str, int] = defaultdict(int)
        moods_by_action: dict[tuple[str, str], set[str]] = defaultdict(set)
        for record in character_records:
            purpose_counts[record.purpose] += 1
            moods_by_action[(record.purpose, record.action)].add(record.mood)
        inventories[character] = ActionMoodInventory(
            total_assets=len(character_records),
            purpose_counts=dict(sorted(purpose_counts.items())),
            action_moods={
                key: tuple(sorted(mood for mood in moods if mood))
                for key, moods in sorted(moods_by_action.items())
            },
        )
    return inventories


def find_naming_issues(records: tuple[AssetActionRecord, ...]) -> tuple[str, ...]:
    issues: list[str] = []
    for record in records:
        if record.mood != record.mood.strip():
            issues.append(
                f"{record.character}/{record.file_name}: mood 含前後空白，實際解析為 '{record.mood}'"
            )
        if not record.mood:
            issues.append(
                f"{record.character}/{record.file_name}: 沒有 `-mood`，mood 會解析為空字串"
            )
        if record.purpose not in KNOWN_PURPOSES:
            issues.append(
                f"{record.character}/{record.file_name}: purpose='{record.purpose}' 不在預期集合 {sorted(KNOWN_PURPOSES)}"
            )
        for token in SUSPICIOUS_TOKENS:
            if token in record.file_name:
                issues.append(
                    f"{record.character}/{record.file_name}: 檔名含疑似拼字 token `{token}`，請確認是否刻意"
                )
                break
    return tuple(issues)


def audit_manifests(
    assets_dir: str | Path,
    records: tuple[AssetActionRecord, ...],
) -> tuple[ManifestAuditResult, ...]:
    root = Path(assets_dir)
    records_by_character: dict[str, set[str]] = defaultdict(set)
    for record in records:
        records_by_character[record.character].add(record.file_name)

    results: list[ManifestAuditResult] = []
    for character_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = character_dir / "manifest_edit.json"
        manifest_entries, warnings = load_manifest_entries(str(manifest_path))
        asset_names = records_by_character.get(character_dir.name, set())
        manifest_names = set(manifest_entries.keys())
        results.append(
            ManifestAuditResult(
                character=character_dir.name,
                manifest_path=str(manifest_path),
                manifest_entry_count=len(manifest_names),
                asset_count=len(asset_names),
                manifest_missing_files=tuple(sorted(manifest_names - asset_names)),
                assets_missing_manifest=tuple(sorted(asset_names - manifest_names)),
                manifest_warnings=tuple(warnings),
            )
        )
    return tuple(results)


def audit_random_manifest_coverage(
    assets_dir: str | Path,
    records: tuple[AssetActionRecord, ...],
    *,
    purposes: tuple[str, ...] = RANDOM_COVERAGE_PURPOSES,
    bands: tuple[str, ...] = RANDOM_COVERAGE_BANDS,
) -> tuple[tuple[RandomManifestCoverageEntry, ...], tuple[RandomManifestCoverageIssue, ...]]:
    root = Path(assets_dir)
    if not root.exists():
        return (), ()

    records_by_character: dict[str, dict[str, AssetActionRecord]] = defaultdict(dict)
    for record in records:
        records_by_character[record.character][record.file_name] = record

    entries: list[RandomManifestCoverageEntry] = []
    issues: list[RandomManifestCoverageIssue] = []

    for character_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        character = character_dir.name
        manifest_entries, _warnings = load_manifest_entries(str(character_dir / "manifest_edit.json"))
        asset_records = records_by_character.get(character, {})
        for purpose in purposes:
            for band in bands:
                files: list[str] = []
                for file_name, meta in manifest_entries.items():
                    record = asset_records.get(file_name)
                    if record is None or record.purpose != purpose:
                        continue
                    contexts = meta.get("contexts") or []
                    if "random" not in contexts:
                        continue
                    manifest_bands = meta.get("band") or []
                    if manifest_bands and band not in manifest_bands:
                        continue
                    files.append(file_name)
                entry = RandomManifestCoverageEntry(
                    character=character,
                    purpose=purpose,
                    band=band,
                    asset_count=len(files),
                    files=tuple(sorted(files)),
                )
                entries.append(entry)
                if not files:
                    issues.append(
                        RandomManifestCoverageIssue(
                            character=character,
                            purpose=purpose,
                            band=band,
                        )
                    )
    return tuple(entries), tuple(issues)


def _req(
    feature: str,
    role: str,
    character: str,
    candidates,
    *,
    item_kind: str = "",
    exact_mood: str = "",
    required_context: str = "",
    preferred_moods=(),
    source: str = "",
) -> CandidateRequirement:
    normalized = tuple((str(purpose), str(action)) for purpose, action in candidates)
    return CandidateRequirement(
        feature=feature,
        role=role,
        character=str(character),
        candidates=normalized,
        item_kind=str(item_kind or ""),
        exact_mood=str(exact_mood or ""),
        required_context=str(required_context or ""),
        preferred_moods=tuple(dict.fromkeys(str(mood) for mood in preferred_moods if mood)),
        source=str(source or ""),
    )


def collect_hardcoded_requirements() -> tuple[CandidateRequirement, ...]:
    from . import offer_interaction_rules as offer
    from . import pet_social_catalog as catalog
    from .shared_food_profiles import (
        SHARED_FOOD_CONTEXT_BY_CAPABILITY,
        SHARED_FOOD_PROFILES,
    )

    requirements: list[CandidateRequirement] = []

    adults = ("Symboli Rudolf", "Sirius Symboli", "Air Groove")
    children = ("Tokai Teio", "Tsurumaru Tsuyoshi")
    all_characters = (*adults, *children)
    for character in adults:
        requirements.append(
            _req(
                "care",
                "adult_companion",
                character,
                catalog.get_adult_companion_candidates(character),
                source="pet_social_catalog.get_adult_companion_candidates",
            )
        )

    for character in children:
        requirements.append(
            _req(
                "care",
                "child_comfort",
                character,
                catalog.get_child_comfort_candidates(character),
                source="pet_social_catalog.get_child_comfort_candidates",
            )
        )
        requirements.append(
            _req(
                "care",
                "child_recovery",
                character,
                catalog.get_child_recovery_candidates(character),
                source="pet_social_catalog.get_child_recovery_candidates",
            )
        )

    for character, candidate in offer.DIRECT_OFFER_PREVIEW_CANDIDATES_BY_NAME.items():
        requirements.append(
            _req(
                "offer",
                "direct_offer_preview",
                character,
                (candidate,),
                source="offer_interaction_rules.DIRECT_OFFER_PREVIEW_CANDIDATES_BY_NAME",
            )
        )

    for item_kind, candidates_by_name in offer.DIRECT_OFFER_ACCEPT_CANDIDATES.items():
        for character, candidates in candidates_by_name.items():
            requirements.append(
                _req(
                    "offer",
                    "direct_offer_accept",
                    character,
                    candidates,
                    item_kind=item_kind,
                    source="offer_interaction_rules.DIRECT_OFFER_ACCEPT_CANDIDATES",
                )
            )

    for character, candidates in offer.HONEY_GUARDIAN_MOVE_CANDIDATES.items():
        requirements.append(
            _req(
                "offer",
                "honey_guard_move",
                character,
                candidates,
                item_kind=offer.ITEM_HONEY,
                source="offer_interaction_rules.HONEY_GUARDIAN_MOVE_CANDIDATES",
            )
        )

    for character, candidates in offer.HONEY_GUARDIAN_TAKE_CANDIDATES.items():
        requirements.append(
            _req(
                "offer",
                "honey_guard_take",
                character,
                candidates,
                item_kind=offer.ITEM_HONEY,
                source="offer_interaction_rules.HONEY_GUARDIAN_TAKE_CANDIDATES",
            )
        )

    for character, candidates in offer.DENIED_OFFER_REACTION_CANDIDATES.items():
        requirements.append(
            _req(
                "offer",
                "offer_denied",
                character,
                candidates,
                source="offer_interaction_rules.DENIED_OFFER_REACTION_CANDIDATES",
            )
        )

    bottle_roles = (
        ("bottle_feed_hold", offer.BOTTLE_FEED_HOLDER_IDLE_CANDIDATES_BY_NAME),
        ("bottle_feed_watch", offer.BOTTLE_FEED_HOLDER_WATCH_CANDIDATES_BY_NAME),
        ("bottle_feed_child_approach", offer.BOTTLE_FEED_CHILD_APPROACH_CANDIDATES_BY_NAME),
        ("bottle_feed_child_drink", offer.BOTTLE_FEED_CHILD_DRINK_CANDIDATES_BY_NAME),
    )
    for role, candidates_by_name in bottle_roles:
        for character, candidates in candidates_by_name.items():
            requirements.append(
                _req(
                    "offer",
                    role,
                    character,
                    candidates,
                    item_kind=offer.ITEM_BOTTLE,
                    source=f"offer_interaction_rules.{role}",
                )
            )

    for item_definition in offer.get_offer_item_definitions():
        for character in all_characters:
            variants = offer.get_offer_hover_reaction_variants(item_definition.kind, character)
            for variant in variants:
                for index, stage in enumerate(variant.stages):
                    requirements.append(
                        _req(
                            "offer",
                            f"offer_hover_timeout_stage_{index + 1}",
                            character,
                            ((stage.purpose, stage.action_type),),
                            item_kind=item_definition.kind,
                            exact_mood=stage.mood_tag,
                            source=f"offer_interaction_rules.OFFER_HOVER_TIMEOUT_REACTION_STAGES:{variant.label}",
                        )
                    )

    for profile in SHARED_FOOD_PROFILES:
        for character_name, capabilities in profile.capabilities_by_name.items():
            for capability_name in ("hold", "approach", "consume", "request", "watch", "react"):
                candidates = getattr(capabilities, f"{capability_name}_candidates")
                requirements.append(
                    _req(
                        "shared_food",
                        capability_name,
                        character_name,
                        candidates,
                        item_kind=profile.item_kind,
                        required_context=SHARED_FOOD_CONTEXT_BY_CAPABILITY[capability_name],
                        preferred_moods=(
                            *profile.holder_preferred_moods,
                            *profile.partner_preferred_moods,
                        ),
                        source=(
                            f"shared_food_profiles.{profile.profile_key}."
                            f"capabilities_by_name.{character_name}.{capability_name}_candidates"
                        ),
                    )
                )

    return tuple(requirements)


def build_asset_index(records: tuple[AssetActionRecord, ...]) -> dict[tuple[str, str, str], set[str]]:
    index: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for record in records:
        index[(record.character, record.purpose, record.action)].add(record.mood)
    return index


def audit_candidate_requirements(
    records: tuple[AssetActionRecord, ...],
    requirements: tuple[CandidateRequirement, ...],
) -> tuple[CandidateIssue, ...]:
    index = build_asset_index(records)
    issues: list[CandidateIssue] = []
    for requirement in requirements:
        if not requirement.candidates:
            issues.append(
                CandidateIssue(
                    feature=requirement.feature,
                    role=requirement.role,
                    character=requirement.character,
                    item_kind=requirement.item_kind,
                    issue="no_candidates_defined",
                    source=requirement.source,
                )
            )
            continue

        role_has_match = False
        for purpose, action in requirement.candidates:
            moods = index.get((requirement.character, purpose, action), set())
            if not moods:
                issues.append(
                    CandidateIssue(
                        feature=requirement.feature,
                        role=requirement.role,
                        character=requirement.character,
                        purpose=purpose,
                        action=action,
                        item_kind=requirement.item_kind,
                        exact_mood=requirement.exact_mood,
                        issue="missing_action",
                        source=requirement.source,
                    )
                )
                continue
            if requirement.exact_mood and requirement.exact_mood not in moods:
                issues.append(
                    CandidateIssue(
                        feature=requirement.feature,
                        role=requirement.role,
                        character=requirement.character,
                        purpose=purpose,
                        action=action,
                        item_kind=requirement.item_kind,
                        exact_mood=requirement.exact_mood,
                        issue="missing_exact_mood",
                        source=requirement.source,
                    )
                )
                continue
            role_has_match = True

        if not role_has_match and requirement.candidates:
            issues.append(
                CandidateIssue(
                    feature=requirement.feature,
                    role=requirement.role,
                    character=requirement.character,
                    item_kind=requirement.item_kind,
                    issue="no_candidate_matches",
                    source=requirement.source,
                )
            )
    return tuple(issues)


def audit_candidate_context_requirements(
    assets_dir: str | Path,
    records: tuple[AssetActionRecord, ...],
    requirements: tuple[CandidateRequirement, ...],
) -> tuple[CandidateIssue, ...]:
    root = Path(assets_dir)
    records_by_key: dict[tuple[str, str, str], list[AssetActionRecord]] = defaultdict(list)
    for record in records:
        records_by_key[(record.character, record.purpose, record.action)].append(record)

    manifest_entries_by_character: dict[str, dict[str, dict]] = {}
    issues: list[CandidateIssue] = []
    for requirement in requirements:
        if not requirement.required_context or not requirement.candidates:
            continue
        manifest_entries = manifest_entries_by_character.get(requirement.character)
        if manifest_entries is None:
            manifest_entries, _warnings = load_manifest_entries(
                str(root / requirement.character / "manifest_edit.json")
            )
            manifest_entries_by_character[requirement.character] = manifest_entries

        context_found = False
        preferred_moods = set(requirement.preferred_moods)
        for purpose, action in requirement.candidates:
            for record in records_by_key.get(
                (requirement.character, purpose, action),
                (),
            ):
                if preferred_moods and record.mood not in preferred_moods:
                    continue
                contexts = (manifest_entries.get(record.file_name) or {}).get("contexts") or ()
                if requirement.required_context in contexts:
                    context_found = True
                    break
            if context_found:
                break
        if not context_found:
            issues.append(
                CandidateIssue(
                    feature=requirement.feature,
                    role=requirement.role,
                    character=requirement.character,
                    item_kind=requirement.item_kind,
                    required_context=requirement.required_context,
                    issue="missing_preferred_context",
                    source=requirement.source,
                )
            )
    return tuple(issues)


def build_asset_action_audit_report(assets_dir: str | Path) -> AssetActionAuditReport:
    records = scan_asset_records(assets_dir)
    requirements = collect_hardcoded_requirements()
    random_manifest_coverage, random_manifest_coverage_issues = audit_random_manifest_coverage(
        assets_dir,
        records,
    )
    return AssetActionAuditReport(
        assets_dir=str(assets_dir),
        records=records,
        inventories=build_action_mood_inventory(records),
        naming_issues=find_naming_issues(records),
        manifest_results=audit_manifests(assets_dir, records),
        random_manifest_coverage=random_manifest_coverage,
        random_manifest_coverage_issues=random_manifest_coverage_issues,
        requirements=requirements,
        candidate_issues=(
            *audit_candidate_requirements(records, requirements),
            *audit_candidate_context_requirements(assets_dir, records, requirements),
        ),
    )


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"`{name}={count}`" for name, count in sorted(counts.items())) or "(none)"


def format_markdown_report(report: AssetActionAuditReport) -> str:
    lines: list[str] = [
        "# Asset Action Audit Report",
        "",
        f"- Assets dir: `{report.assets_dir}`",
        f"- Total assets: `{len(report.records)}`",
        f"- Characters: `{len(report.inventories)}`",
        f"- Hardcoded requirements: `{len(report.requirements)}`",
        f"- Candidate issues: `{len(report.candidate_issues)}`",
        "",
        "## Per-character action/mood inventory",
        "",
    ]

    for character, inventory in sorted(report.inventories.items()):
        lines.append(f"### {character}")
        lines.append("")
        lines.append(f"- Total assets: `{inventory.total_assets}`")
        lines.append(f"- Purpose counts: {_format_counts(inventory.purpose_counts)}")
        lines.append("- Actions:")
        for (purpose, action), moods in sorted(inventory.action_moods.items()):
            mood_text = ", ".join(f"`{mood}`" for mood in moods) if moods else "`(empty mood)`"
            lines.append(f"  - `{purpose}_{action}`: {len(moods)} mood(s): {mood_text}")
        lines.append("")

    lines.extend(["## Hardcoded candidate availability", ""])
    if report.candidate_issues:
        for issue in report.candidate_issues:
            item_text = f" item=`{issue.item_kind}`" if issue.item_kind else ""
            action_text = (
                f" `{issue.purpose}_{issue.action}`"
                if issue.purpose or issue.action
                else ""
            )
            mood_text = f" mood=`{issue.exact_mood}`" if issue.exact_mood else ""
            context_text = (
                f" context=`{issue.required_context}`"
                if issue.required_context
                else ""
            )
            lines.append(
                f"- `{issue.issue}` feature=`{issue.feature}` role=`{issue.role}` "
                f"character=`{issue.character}`{item_text}{action_text}{mood_text}"
                f"{context_text} source=`{issue.source}`"
            )
    else:
        lines.append("- No hardcoded candidate issues found.")
    lines.append("")

    lines.extend(["## Manifest sync", ""])
    for result in report.manifest_results:
        lines.append(f"### {result.character}")
        lines.append("")
        lines.append(f"- Assets: `{result.asset_count}`")
        lines.append(f"- Manifest entries: `{result.manifest_entry_count}`")
        if result.manifest_warnings:
            lines.append("- Manifest warnings:")
            lines.extend(f"  - {warning}" for warning in result.manifest_warnings)
        if result.manifest_missing_files:
            lines.append("- Manifest has missing files:")
            lines.extend(f"  - `{file_name}`" for file_name in result.manifest_missing_files)
        if result.assets_missing_manifest:
            lines.append("- Assets missing manifest entry:")
            lines.extend(f"  - `{file_name}`" for file_name in result.assets_missing_manifest)
        if not result.manifest_warnings and not result.manifest_missing_files and not result.assets_missing_manifest:
            lines.append("- Manifest is in sync with asset files.")
        lines.append("")

    lines.extend(["## Random manifest-only coverage", ""])
    if report.random_manifest_coverage:
        by_character: dict[str, list[RandomManifestCoverageEntry]] = defaultdict(list)
        for entry in report.random_manifest_coverage:
            by_character[entry.character].append(entry)
        for character, entries in sorted(by_character.items()):
            lines.append(f"### {character}")
            lines.append("")
            for purpose in RANDOM_COVERAGE_PURPOSES:
                purpose_entries = [entry for entry in entries if entry.purpose == purpose]
                if not purpose_entries:
                    continue
                counts = ", ".join(
                    f"`{entry.band}={entry.asset_count}`"
                    for entry in sorted(purpose_entries, key=lambda item: RANDOM_COVERAGE_BANDS.index(item.band))
                )
                lines.append(f"- `{purpose}`: {counts}")
            character_issues = [
                issue for issue in report.random_manifest_coverage_issues
                if issue.character == character
            ]
            if character_issues:
                lines.append("- Missing coverage:")
                for issue in character_issues:
                    lines.append(f"  - `{issue.purpose}` `{issue.band}`")
            else:
                lines.append("- Random manifest-only coverage is complete.")
            lines.append("")
    else:
        lines.append("- No random coverage data found.")
        lines.append("")

    lines.extend(["## Naming issues", ""])
    if report.naming_issues:
        lines.extend(f"- {issue}" for issue in report.naming_issues)
    else:
        lines.append("- No naming issues found.")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def report_to_jsonable(report: AssetActionAuditReport) -> dict:
    return {
        "assets_dir": report.assets_dir,
        "records": [record.__dict__ for record in report.records],
        "inventories": {
            character: {
                "total_assets": inventory.total_assets,
                "purpose_counts": inventory.purpose_counts,
                "action_moods": {
                    f"{purpose}_{action}": list(moods)
                    for (purpose, action), moods in inventory.action_moods.items()
                },
            }
            for character, inventory in report.inventories.items()
        },
        "naming_issues": list(report.naming_issues),
        "manifest_results": [result.__dict__ for result in report.manifest_results],
        "random_manifest_coverage": [entry.__dict__ for entry in report.random_manifest_coverage],
        "random_manifest_coverage_issues": [
            issue.__dict__ for issue in report.random_manifest_coverage_issues
        ],
        "requirements": [requirement.__dict__ for requirement in report.requirements],
        "candidate_issues": [issue.__dict__ for issue in report.candidate_issues],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Audit Tanuki asset actions, manifests, and hardcoded candidates.")
    parser.add_argument(
        "--assets-dir",
        default=str(Path(__file__).resolve().parents[1] / "assets_cropped"),
        help="Path to tanuki_app/assets_cropped.",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format.",
    )
    args = parser.parse_args(argv)

    report = build_asset_action_audit_report(args.assets_dir)
    if args.format == "json":
        print(json.dumps(report_to_jsonable(report), ensure_ascii=False, indent=2))
    else:
        print(format_markdown_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
