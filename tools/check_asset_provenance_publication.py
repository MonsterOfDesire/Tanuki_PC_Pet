"""Validate the public provenance snapshot, not third-party rights or policies."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import unquote, urlsplit


PREFIX = "docs/asset_provenance/"


def is_public_provenance_path(path: str) -> bool:
    if not path.startswith(PREFIX):
        return False
    relative = PurePosixPath(path[len(PREFIX):])
    if any(part in {".", ".."} for part in relative.parts):
        return False
    return (
        len(relative.parts) == 1 and relative.suffix == ".md"
    ) or (
        len(relative.parts) == 2
        and relative.parts[0] == "data"
        and relative.suffix == ".json"
    )


def validate_records(inventory, decisions, graph) -> None:
    assets = inventory["assets"]
    asset_ids = [asset["asset_id"] for asset in assets]
    decision_ids = [asset["asset_id"] for asset in decisions["assets"]]
    assert len(asset_ids) == len(set(asset_ids)), "duplicate asset ID"
    assert len(decision_ids) == len(set(decision_ids)), "duplicate decision ID"
    assert set(asset_ids) == set(decision_ids), "decision coverage mismatch"
    assert inventory["asset_count"] == len(assets), "asset count mismatch"
    assert decisions["asset_count"] == len(decision_ids), "decision count mismatch"
    actual_counts = Counter(asset["publication_decision"] for asset in decisions["assets"])
    expected_counts = {key: value for key, value in decisions["decision_counts"].items() if value}
    assert dict(actual_counts) == expected_counts, "decision colour counts mismatch"
    node_ids = [node["node_id"] for node in graph["nodes"]]
    edge_ids = [edge["edge_id"] for edge in graph["edges"]]
    assert len(node_ids) == len(set(node_ids)), "duplicate graph node ID"
    assert len(edge_ids) == len(set(edge_ids)), "duplicate graph edge ID"
    assert graph["node_count"] == len(node_ids), "node count mismatch"
    assert graph["edge_count"] == len(edge_ids), "edge count mismatch"
    known_nodes = set(node_ids)
    for edge in graph["edges"]:
        assert edge["source"] in known_nodes and edge["target"] in known_nodes, "dangling graph edge"


def validate_snapshot(repo_root: Path) -> tuple[int, int]:
    root = repo_root / PREFIX
    public_files = sorted(root.glob("*.md")) + sorted((root / "data").glob("*.json"))
    payloads = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in public_files if path.suffix == ".json"
    }
    inventory = payloads["asset_inventory.json"]
    validate_records(inventory, payloads["publication_decisions.json"], payloads["asset_relationship_graph.json"])
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=repo_root
    ).decode("utf-8").split("\0")
    available = {repo_root / path for path in tracked if path} | set(public_files)
    available.add(repo_root / "tools/check_asset_provenance_publication.py")
    for path in public_files:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            parts = urlsplit(target)
            if parts.scheme in {"http", "https", "mailto"} or not parts.path:
                continue
            assert not parts.scheme and not target.startswith("/"), f"absolute doc link: {path.name}"
            resolved = (path.parent / unquote(parts.path)).resolve()
            assert resolved in {candidate.resolve() for candidate in available}, f"non-public doc link: {path.name}: {target}"
    for asset in inventory["assets"]:
        path = (repo_root / asset["relative_path"]).resolve()
        assert path.is_relative_to(repo_root), "asset escapes repository"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["file_sha256"], f"asset changed: {asset['asset_id']}"
    staged = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "-z"], cwd=repo_root
    ).decode("utf-8").split("\0")
    for path in staged:
        if path.startswith(PREFIX):
            assert is_public_provenance_path(path), f"non-public research file staged: {path}"
    return len(public_files), len(inventory["assets"])


if __name__ == "__main__":
    file_count, asset_count = validate_snapshot(Path(__file__).resolve().parents[1])
    print(f"PASS: {file_count} public documents/data files; {asset_count} local asset hashes; graph and staging scope valid")
