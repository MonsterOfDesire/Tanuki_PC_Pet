from __future__ import annotations

import argparse
import json
import math
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from .manifest_rules import MANIFEST_SCHEMA_VERSION, VALID_BANDS


MANIFEST_XLSX_NAME = "manifest_edit.xlsx"
MANIFEST_JSON_NAME = "manifest_edit.json"
STALE_BACKUP_SHEET_NAME = "stale_backup"
REQUIRED_COLUMNS = ("filename", "band", "contexts", "weight")
OPTIONAL_COLUMNS = ("notes",)
ANIMATION_EXTENSION = ".gif"


KNOWN_CONTEXTS = frozenset(
    {
        "activity_race_accept",
        "activity_race_challenge",
        "activity_race_consider",
        "activity_race_decline",
        "activity_race_finish_lose",
        "activity_race_finish_win",
        "activity_race_ready",
        "activity_race_recovery",
        "activity_race_running",
        "activity_race_running_teio",
        "activity_race_to_start",
        "activity_sleep_join_approach",
        "activity_sleep_join_settling",
        "activity_sleep_observing",
        "activity_sleep_settling",
        "activity_sleeping",
        "activity_sleep_waking",
        "activity_work_rest",
        "activity_work_stationary",
        "activity_work_transport",
        "bottle_feed_child_approach",
        "bottle_feed_child_drink",
        "bottle_feed_hold",
        "bottle_feed_watch",
        "care_approach",
        "care_approach_teio",
        "care_approach_tsuyoshi",
        "care_child_comfort",
        "care_child_recovery",
        "care_companion",
        "care_interaction",
        "care_interaction_teio",
        "care_interaction_tsuyoshi",
        "disabled",
        "drag",
        "future_ensemble",
        "future_lie_read",
        "future_music",
        "future_race",
        "future_sleep",
        "future_teach",
        "future_think",
        "future_tsuyoshi_think",
        "future_work",
        "future_work_money",
        "hard_landing",
        "honey_guard_move",
        "honey_guard_take",
        "interaction",
        "moving_care_interaction",
        "moving_care_interaction_teio",
        "moving_care_interaction_tsuyoshi",
        "moving_interaction",
        "negative_reaction",
        "observe_hold",
        "offer_accept_honey",
        "offer_accept_lollipop",
        "offer_accept_milk",
        "offer_accept_ramen",
        "offer_accept_tea",
        "offer_denied",
        "offer_preview",
        "offer_timeout_route_a_step1",
        "offer_timeout_route_a_step2",
        "offer_timeout_route_a_step3",
        "offer_timeout_route_b_step1",
        "offer_timeout_route_b_step2",
        "post_observe",
        "random",
        "relation_close",
        "relation_watch",
        "shared_food_approach",
        "shared_food_consume",
        "shared_food_hold",
        "shared_food_react",
        "shared_food_request",
        "shared_food_watch",
        "side_ready_followup",
        "social_follow",
        "social_mimic",
        "window_flight",
        "window_perch",
        "window_walk",
    }
)

NS_MAIN = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_REL = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OD_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@dataclass(frozen=True)
class ManifestXlsxIssue:
    character: str
    workbook: str
    message: str
    row: int | None = None

    def format(self) -> str:
        row_text = f" row {self.row}" if self.row is not None else ""
        return f"{self.character}{row_text}: {self.message}"


@dataclass(frozen=True)
class ManifestXlsxConversionReport:
    character: str
    workbook: str
    output_path: str
    entry_count: int
    asset_count: int
    written: bool = False


class ManifestXlsxValidationError(Exception):
    def __init__(self, issues: Iterable[ManifestXlsxIssue]):
        self.issues = tuple(issues)
        message = "\n".join(issue.format() for issue in self.issues)
        super().__init__(message)


def _xml_name(local_name: str) -> str:
    return f"{{{NS_MAIN['x']}}}{local_name}"


def _relationship_name(local_name: str) -> str:
    return f"{{{REL_NS}}}{local_name}"


def _office_relationship_attr(local_name: str) -> str:
    return f"{{{OD_REL_NS}}}{local_name}"


def _column_index(cell_reference: str) -> int:
    letters = ""
    for char in cell_reference:
        if char.isalpha():
            letters += char.upper()
        else:
            break
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def _read_xml(zip_file: zipfile.ZipFile, name: str) -> ET.Element:
    with zip_file.open(name) as stream:
        return ET.fromstring(stream.read())


def _read_shared_strings(zip_file: zipfile.ZipFile) -> list[str]:
    try:
        root = _read_xml(zip_file, "xl/sharedStrings.xml")
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall("x:si", NS_MAIN):
        texts = [node.text or "" for node in item.findall(".//x:t", NS_MAIN)]
        strings.append("".join(texts))
    return strings


def _workbook_sheet_paths(zip_file: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = _read_xml(zip_file, "xl/workbook.xml")
    rels = _read_xml(zip_file, "xl/_rels/workbook.xml.rels")
    rel_targets: dict[str, str] = {}
    for rel in rels.findall(_relationship_name("Relationship")):
        rel_id = rel.attrib.get("Id", "")
        target = rel.attrib.get("Target", "")
        if not rel_id or not target:
            continue
        if target.startswith("/"):
            target = target.lstrip("/")
        elif not target.startswith("xl/"):
            target = f"xl/{target}"
        rel_targets[rel_id] = target

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(".//x:sheet", {**NS_MAIN, **NS_REL}):
        rel_id = sheet.attrib.get(_office_relationship_attr("id"), "")
        sheet_name = sheet.attrib.get("name", "")
        target = rel_targets.get(rel_id, "")
        if sheet_name and target:
            sheets.append((sheet_name, target))
    return sheets


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        texts = [node.text or "" for node in cell.findall(".//x:t", NS_MAIN)]
        return "".join(texts)

    value_node = cell.find("x:v", NS_MAIN)
    if value_node is None or value_node.text is None:
        return ""
    raw = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (IndexError, ValueError):
            return ""
    return raw


def _read_main_sheet_rows(workbook_path: Path) -> tuple[str, list[dict[str, str]], list[int]]:
    with zipfile.ZipFile(workbook_path) as zip_file:
        shared_strings = _read_shared_strings(zip_file)
        sheet_paths = _workbook_sheet_paths(zip_file)
        selected_sheet = next(
            ((name, path) for name, path in sheet_paths if name != STALE_BACKUP_SHEET_NAME),
            None,
        )
        if selected_sheet is None:
            return "", [], []

        sheet_name, sheet_path = selected_sheet
        sheet_root = _read_xml(zip_file, sheet_path)

    raw_rows: list[tuple[int, dict[int, str]]] = []
    for row in sheet_root.findall(".//x:sheetData/x:row", NS_MAIN):
        row_number = int(row.attrib.get("r", "0") or 0)
        cells: dict[int, str] = {}
        for cell in row.findall("x:c", NS_MAIN):
            cell_reference = cell.attrib.get("r", "")
            if not cell_reference:
                continue
            cells[_column_index(cell_reference)] = _cell_text(cell, shared_strings)
        raw_rows.append((row_number, cells))

    if not raw_rows:
        return sheet_name, [], []

    _header_row_number, header_cells = raw_rows[0]
    headers = {index: str(value).strip() for index, value in header_cells.items() if str(value).strip()}
    rows: list[dict[str, str]] = []
    row_numbers: list[int] = []
    for row_number, cells in raw_rows[1:]:
        mapped: dict[str, str] = {}
        for index, header in headers.items():
            mapped[header] = str(cells.get(index, "")).strip()
        rows.append(mapped)
        row_numbers.append(row_number)
    return sheet_name, rows, row_numbers


def _parse_token_list(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    for raw_token in str(value or "").split(","):
        token = raw_token.strip()
        if token and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _parse_weight(value: str) -> float | None:
    if str(value or "").strip() == "":
        return None
    try:
        weight = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(weight) or weight < 0:
        return None
    return weight


def _character_name(character_dir: Path) -> str:
    return character_dir.name


def validate_manifest_xlsx(character_dir: str | Path) -> tuple[dict[str, dict], tuple[ManifestXlsxIssue, ...]]:
    character_path = Path(character_dir)
    character = _character_name(character_path)
    workbook_path = character_path / MANIFEST_XLSX_NAME
    issues: list[ManifestXlsxIssue] = []

    if not workbook_path.exists():
        return {}, (
            ManifestXlsxIssue(character, str(workbook_path), f"找不到 {MANIFEST_XLSX_NAME}"),
        )

    try:
        _sheet_name, rows, row_numbers = _read_main_sheet_rows(workbook_path)
    except Exception as exc:
        return {}, (
            ManifestXlsxIssue(character, str(workbook_path), f"xlsx 讀取失敗: {exc}"),
        )

    if not rows:
        return {}, (
            ManifestXlsxIssue(character, str(workbook_path), "主工作表沒有資料列"),
        )

    headers = set(rows[0].keys())
    for column in REQUIRED_COLUMNS:
        if column not in headers:
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"缺少必要欄位 `{column}`")
            )

    if issues:
        return {}, tuple(issues)

    asset_names = {
        path.name
        for path in character_path.iterdir()
        if path.is_file() and path.suffix.lower() == ANIMATION_EXTENSION
    }
    seen_names: set[str] = set()
    entries: dict[str, dict] = {}

    for row_index, row in zip(row_numbers, rows):
        file_name = str(row.get("filename", "") or "").strip()
        if not file_name:
            continue

        if file_name in seen_names:
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"filename 重複: {file_name}", row_index)
            )
            continue
        seen_names.add(file_name)

        if Path(file_name).name != file_name or not file_name.lower().endswith(ANIMATION_EXTENSION):
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"filename 必須是第一層 .gif 檔名: {file_name}", row_index)
            )

        bands = _parse_token_list(row.get("band", ""))
        if not bands:
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"{file_name}: band 不可空白", row_index)
            )
        for band in bands:
            if band not in VALID_BANDS:
                issues.append(
                    ManifestXlsxIssue(character, str(workbook_path), f"{file_name}: 未知 band `{band}`", row_index)
                )

        contexts = _parse_token_list(row.get("contexts", ""))
        if not contexts:
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"{file_name}: contexts 不可空白", row_index)
            )
        for context in contexts:
            if context not in KNOWN_CONTEXTS:
                issues.append(
                    ManifestXlsxIssue(character, str(workbook_path), f"{file_name}: 未知 context `{context}`", row_index)
                )

        weight = _parse_weight(row.get("weight", ""))
        if weight is None:
            issues.append(
                ManifestXlsxIssue(character, str(workbook_path), f"{file_name}: weight 必須是 0 以上數字", row_index)
            )
            weight = 1.0

        entries[file_name] = {
            "band": list(bands),
            "contexts": list(contexts),
            "weight": weight,
        }

    stale_names = sorted(seen_names - asset_names)
    missing_names = sorted(asset_names - seen_names)
    for file_name in stale_names:
        issues.append(
            ManifestXlsxIssue(character, str(workbook_path), f"xlsx 列出不存在素材: {file_name}")
        )
    for file_name in missing_names:
        issues.append(
            ManifestXlsxIssue(character, str(workbook_path), f"素材未列入 xlsx: {file_name}")
        )

    if issues:
        return {}, tuple(issues)
    return entries, ()


def build_manifest_payload(entries: dict[str, dict]) -> dict[str, object]:
    return {
        "_schema_version": MANIFEST_SCHEMA_VERSION,
        "animations": entries,
    }


def write_manifest_json(output_path: str | Path, entries: dict[str, dict]) -> None:
    output = Path(output_path)
    payload = build_manifest_payload(entries)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def convert_character_manifest_xlsx(
    character_dir: str | Path,
    *,
    write: bool = False,
) -> ManifestXlsxConversionReport:
    character_path = Path(character_dir)
    entries, issues = validate_manifest_xlsx(character_path)
    if issues:
        raise ManifestXlsxValidationError(issues)

    output_path = character_path / MANIFEST_JSON_NAME
    if write:
        write_manifest_json(output_path, entries)
    return ManifestXlsxConversionReport(
        character=_character_name(character_path),
        workbook=str(character_path / MANIFEST_XLSX_NAME),
        output_path=str(output_path),
        entry_count=len(entries),
        asset_count=len(entries),
        written=write,
    )


def iter_character_dirs(assets_dir: str | Path) -> tuple[Path, ...]:
    root = Path(assets_dir)
    if not root.exists():
        return ()
    return tuple(
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / MANIFEST_XLSX_NAME).exists()
    )


def convert_assets_manifests(
    assets_dir: str | Path,
    *,
    write: bool = False,
    character_names: Iterable[str] | None = None,
) -> tuple[ManifestXlsxConversionReport, ...]:
    wanted = set(character_names or ())
    character_dirs = iter_character_dirs(assets_dir)
    if wanted:
        character_dirs = tuple(path for path in character_dirs if path.name in wanted)

    validation_results = []
    issues: list[ManifestXlsxIssue] = []
    for character_dir in character_dirs:
        entries, character_issues = validate_manifest_xlsx(character_dir)
        if character_issues:
            issues.extend(character_issues)
        else:
            validation_results.append((character_dir, entries))

    if issues:
        raise ManifestXlsxValidationError(issues)

    reports: list[ManifestXlsxConversionReport] = []
    for character_dir, entries in validation_results:
        output_path = character_dir / MANIFEST_JSON_NAME
        if write:
            write_manifest_json(output_path, entries)
        reports.append(
            ManifestXlsxConversionReport(
                character=_character_name(character_dir),
                workbook=str(character_dir / MANIFEST_XLSX_NAME),
                output_path=str(output_path),
                entry_count=len(entries),
                asset_count=len(entries),
                written=write,
            )
        )
    return tuple(reports)


def default_assets_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets_cropped"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate manifest_edit.xlsx files and optionally convert them to manifest_edit.json.",
    )
    parser.add_argument(
        "--assets-dir",
        default=str(default_assets_dir()),
        help="assets_cropped directory. Defaults to the bundled tanuki_app/assets_cropped.",
    )
    parser.add_argument(
        "--character",
        action="append",
        default=[],
        help="Character folder name to convert. Repeat to convert multiple characters. Defaults to all.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write manifest_edit.json. Without this flag the command only validates.",
    )
    args = parser.parse_args(argv)

    try:
        reports = convert_assets_manifests(
            args.assets_dir,
            write=args.write,
            character_names=args.character or None,
        )
    except ManifestXlsxValidationError as exc:
        print("manifest xlsx validation failed:")
        for issue in exc.issues:
            print(f"- {issue.format()}")
        return 1

    mode = "WROTE" if args.write else "DRY-RUN OK"
    for report in reports:
        print(f"{mode}: {report.character} entries={report.entry_count} -> {report.output_path}")
    if not reports:
        print("No manifest_edit.xlsx files found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
