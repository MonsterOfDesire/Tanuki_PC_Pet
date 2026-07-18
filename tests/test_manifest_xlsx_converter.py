import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from tanuki_core.manifest_xlsx_converter import (
    ManifestXlsxValidationError,
    convert_assets_manifests,
    convert_character_manifest_xlsx,
    validate_manifest_xlsx,
)


def _cell(col, row, value):
    return (
        f'<c r="{col}{row}" t="inlineStr">'
        f"<is><t>{escape(str(value))}</t></is>"
        "</c>"
    )


def _sheet_xml(rows):
    row_nodes = []
    columns = ("A", "B", "C", "D", "E")
    for row_index, values in enumerate(rows, start=1):
        cells = "".join(_cell(col, row_index, value) for col, value in zip(columns, values))
        row_nodes.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        + "".join(row_nodes)
        + "</sheetData></worksheet>"
    )


def write_minimal_xlsx(path, rows, stale_rows=None):
    stale_rows = stale_rows or []
    sheets = [
        ("Sheet1", "worksheets/sheet1.xml", _sheet_xml(rows)),
    ]
    if stale_rows:
        sheets.append(("stale_backup", "worksheets/sheet2.xml", _sheet_xml(stale_rows)))

    workbook_sheets = []
    rels = []
    overrides = []
    for index, (name, target, _xml) in enumerate(sheets, start=1):
        workbook_sheets.append(
            f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        )
        rels.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="{target}"/>'
        )
        overrides.append(
            f'<Override PartName="/xl/{target}" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        + "".join(workbook_sheets)
        + "</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels)
        + "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(overrides)
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for _name, target, xml in sheets:
            archive.writestr(f"xl/{target}", xml)


class ManifestXlsxConverterTests(unittest.TestCase):
    def test_convert_character_manifest_xlsx_writes_schema_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            character_dir = Path(tmp) / "Tokai Teio"
            character_dir.mkdir()
            (character_dir / "idle_get-happy.gif").write_bytes(b"gif")
            (character_dir / "move_walk-sad.gif").write_bytes(b"gif")
            write_minimal_xlsx(
                character_dir / "manifest_edit.xlsx",
                [
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("idle_get-happy.gif", "normal", "random,offer_preview", "1.25", ""),
                    ("move_walk-sad.gif", "low,severe", "window_walk", "0", ""),
                ],
                stale_rows=[
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("old.gif", "normal", "random", "1", ""),
                ],
            )

            report = convert_character_manifest_xlsx(character_dir, write=True)
            payload = json.loads((character_dir / "manifest_edit.json").read_text(encoding="utf-8"))

        self.assertTrue(report.written)
        self.assertEqual(payload["_schema_version"], 1)
        self.assertEqual(set(payload["animations"].keys()), {"idle_get-happy.gif", "move_walk-sad.gif"})
        self.assertEqual(payload["animations"]["idle_get-happy.gif"]["contexts"], ["random", "offer_preview"])
        self.assertEqual(payload["animations"]["idle_get-happy.gif"]["weight"], 1.25)
        self.assertEqual(payload["animations"]["move_walk-sad.gif"]["weight"], 0.0)

    def test_validate_manifest_xlsx_reports_stale_and_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            character_dir = Path(tmp) / "Air Groove"
            character_dir.mkdir()
            (character_dir / "idle_get-happy.gif").write_bytes(b"gif")
            (character_dir / "idle_side-smile.gif").write_bytes(b"gif")
            write_minimal_xlsx(
                character_dir / "manifest_edit.xlsx",
                [
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("idle_get-happy.gif", "normal", "random", "1", ""),
                    ("stale.gif", "normal", "random", "1", ""),
                ],
            )

            _entries, issues = validate_manifest_xlsx(character_dir)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("xlsx 列出不存在素材: stale.gif" in message for message in messages))
        self.assertTrue(any("素材未列入 xlsx: idle_side-smile.gif" in message for message in messages))

    def test_validate_manifest_xlsx_rejects_unknown_context_bad_band_and_weight(self):
        with tempfile.TemporaryDirectory() as tmp:
            character_dir = Path(tmp) / "Symboli Rudolf"
            character_dir.mkdir()
            (character_dir / "idle_get-happy.gif").write_bytes(b"gif")
            write_minimal_xlsx(
                character_dir / "manifest_edit.xlsx",
                [
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("idle_get-happy.gif", "nornal", "random,typo_context", "bad", ""),
                ],
            )

            _entries, issues = validate_manifest_xlsx(character_dir)

        messages = [issue.message for issue in issues]
        self.assertTrue(any("未知 band `nornal`" in message for message in messages))
        self.assertTrue(any("未知 context `typo_context`" in message for message in messages))
        self.assertTrue(any("weight 必須是 0 以上數字" in message for message in messages))

    def test_assets_directory_validates_all_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid_dir = root / "Tokai Teio"
            invalid_dir = root / "Air Groove"
            valid_dir.mkdir()
            invalid_dir.mkdir()
            (valid_dir / "idle_get-happy.gif").write_bytes(b"gif")
            (invalid_dir / "idle_get-happy.gif").write_bytes(b"gif")
            write_minimal_xlsx(
                valid_dir / "manifest_edit.xlsx",
                [
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("idle_get-happy.gif", "normal", "random", "1", ""),
                ],
            )
            write_minimal_xlsx(
                invalid_dir / "manifest_edit.xlsx",
                [
                    ("filename", "band", "contexts", "weight", "notes"),
                    ("idle_get-happy.gif", "normal", "not_a_context", "1", ""),
                ],
            )

            with self.assertRaises(ManifestXlsxValidationError):
                convert_assets_manifests(root, write=True)

            self.assertFalse((valid_dir / "manifest_edit.json").exists())


if __name__ == "__main__":
    unittest.main()
