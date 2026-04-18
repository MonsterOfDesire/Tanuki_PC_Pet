import json
import os
import re

from .config_rules import CONFIG_SCHEMA_VERSION, normalize_config_state
from .manifest_rules import MANIFEST_SCHEMA_VERSION, normalize_manifest_entry


def load_json_loose(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw), []
    except json.JSONDecodeError:
        sanitized = re.sub(r",(\s*[}\]])", r"\1", raw)
        return json.loads(sanitized), ["已自動清理 trailing comma"]

def load_manifest_entries(manifest_path):
    if not os.path.exists(manifest_path):
        return {}, []
    warnings = []
    try:
        data, parse_warnings = load_json_loose(manifest_path)
        warnings.extend(parse_warnings)
    except Exception as exc:
        return {}, [f"讀取失敗: {exc}"]

    schema_version = MANIFEST_SCHEMA_VERSION
    entries = data
    if isinstance(data, dict) and "animations" in data:
        schema_version = int(data.get("_schema_version", MANIFEST_SCHEMA_VERSION) or MANIFEST_SCHEMA_VERSION)
        entries = data.get("animations", {})
    elif isinstance(data, dict):
        entries = {k: v for k, v in data.items() if not str(k).startswith("_")}
    else:
        return {}, ["manifest 根節點不是物件"]

    normalized = {}
    for file_name, meta in entries.items():
        if not isinstance(meta, dict):
            warnings.append(f"{file_name}: 不是物件，已忽略")
            continue
        normalized_entry, entry_warnings = normalize_manifest_entry(meta, file_name=file_name)
        normalized[file_name] = normalized_entry
        warnings.extend(entry_warnings)

    if schema_version != MANIFEST_SCHEMA_VERSION:
        warnings.append(f"schema_version={schema_version}，目前預期 {MANIFEST_SCHEMA_VERSION}")
    return normalized, warnings


def validate_manifest_file(manifest_path):
    normalized, warnings = load_manifest_entries(manifest_path)
    return {
        "path": manifest_path,
        "ok": len(warnings) == 0,
        "entry_count": len(normalized),
        "warnings": warnings,
    }


def scan_manifest_directory(assets_dir):
    reports = []
    if not os.path.isdir(assets_dir):
        return {"count": 0, "warnings": [f"找不到素材資料夾: {assets_dir}"], "reports": reports}

    for entry in sorted(os.listdir(assets_dir)):
        folder = os.path.join(assets_dir, entry)
        if not os.path.isdir(folder):
            continue
        manifest_path = os.path.join(folder, "manifest_edit.json")
        if os.path.exists(manifest_path):
            reports.append(validate_manifest_file(manifest_path))

    warnings = []
    for report in reports:
        for warning in report["warnings"]:
            warnings.append(f"{os.path.basename(os.path.dirname(report['path']))}: {warning}")

    return {
        "count": len(reports),
        "warnings": warnings,
        "reports": reports,
    }

def validate_config_file(config_path):
    if not os.path.exists(config_path):
        return {"path": config_path, "ok": True, "warnings": ["找不到 config.json，會在首次儲存時建立"]}
    try:
        data, parse_warnings = load_json_loose(config_path)
    except Exception as exc:
        return {"path": config_path, "ok": False, "warnings": [f"讀取失敗: {exc}"]}
    _normalized, warnings = normalize_config_state(data)
    warnings = parse_warnings + warnings
    return {
        "path": config_path,
        "ok": len(warnings) == 0,
        "warnings": warnings,
    }


def build_validation_report(assets_dir, config_path):
    manifest_result = scan_manifest_directory(assets_dir)
    config_result = validate_config_file(config_path)
    lines = [
        f"Config schema: {CONFIG_SCHEMA_VERSION}",
        f"Manifest schema: {MANIFEST_SCHEMA_VERSION}",
        f"Manifest 檢查角色數: {manifest_result['count']}",
    ]
    warnings = []
    warnings.extend(config_result["warnings"])
    warnings.extend(manifest_result["warnings"])
    if warnings:
        lines.append("")
        lines.append("警告 / 提示:")
        lines.extend(f"- {warning}" for warning in warnings[:20])
        if len(warnings) > 20:
            lines.append(f"- 其餘 {len(warnings) - 20} 筆已省略")
    else:
        lines.append("")
        lines.append("未發現明顯問題。")
    return "\n".join(lines), warnings
