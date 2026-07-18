from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re
import subprocess
import sys


BLOCKED_BASENAMES = {
    "sign_tanuki.ps1": "blocked_signing_script",
    "\u65b0\u6587\u5b57\u6587\u4ef6.txt": "blocked_sensitive_filename",
}
BLOCKED_SUFFIXES = {
    ".pfx": "certificate_file",
    ".p12": "certificate_file",
    ".pem": "key_or_certificate_file",
    ".key": "private_key_file",
}

CONTENT_RULES = (
    (
        "private_key_header",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    ),
    (
        "known_token_format",
        re.compile(
            r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
            r"AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{20,})"
        ),
    ),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|"
            r"client[_-]?secret)\b\s*[:=]\s*['\"]?[^\s'\"${}]{6,}"
        ),
    ),
    (
        "inline_signing_credential",
        re.compile(
            r"(?is)\bsign(?:ing)?tool\b.{0,240}(?:/p|-p|certificate-password)\s+\S+"
        ),
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str


def filename_findings(path: str) -> tuple[Finding, ...]:
    normalized = path.replace("\\", "/")
    pure_path = PurePosixPath(normalized)
    basename = pure_path.name.casefold()
    findings: list[Finding] = []

    blocked_rule = BLOCKED_BASENAMES.get(basename)
    if blocked_rule:
        findings.append(Finding(path=normalized, rule=blocked_rule))

    suffix_rule = BLOCKED_SUFFIXES.get(pure_path.suffix.casefold())
    if suffix_rule:
        findings.append(Finding(path=normalized, rule=suffix_rule))

    if basename == ".env" or (basename.startswith(".env.") and basename != ".env.example"):
        findings.append(Finding(path=normalized, rule="environment_file"))
    return tuple(findings)


def content_findings(path: str, data: bytes) -> tuple[Finding, ...]:
    if b"\0" in data[:8192]:
        return ()
    text = data.decode("utf-8", errors="ignore")
    return tuple(
        Finding(path=path, rule=rule)
        for rule, pattern in CONTENT_RULES
        if pattern.search(text)
    )


def scan_staged_path(path: str, data: bytes) -> tuple[Finding, ...]:
    return (*filename_findings(path), *content_findings(path, data))


def run_git(repo_root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def get_repo_root() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("not inside a Git work tree")
    return result.stdout.strip()


def get_staged_paths(repo_root: str) -> tuple[str, ...]:
    result = run_git(
        repo_root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMR",
        "-z",
    )
    if result.returncode != 0:
        raise RuntimeError("unable to list staged files")
    return tuple(
        part.decode("utf-8", errors="surrogateescape")
        for part in result.stdout.split(b"\0")
        if part
    )


def get_staged_blob(repo_root: str, path: str) -> bytes | None:
    result = run_git(repo_root, "show", f":{path}")
    if result.returncode != 0:
        return None
    return result.stdout


def main() -> int:
    try:
        repo_root = get_repo_root()
        staged_paths = get_staged_paths(repo_root)
    except RuntimeError as exc:
        print(f"staged security check failed [{exc}]", file=sys.stderr)
        return 2

    print("Staged files:")
    if not staged_paths:
        print("  (none)")
        return 0
    for path in staged_paths:
        print(f"  {path}")

    findings: list[Finding] = []
    for path in staged_paths:
        data = get_staged_blob(repo_root, path)
        if data is None:
            findings.append(Finding(path=path, rule="staged_blob_unreadable"))
            continue
        findings.extend(scan_staged_path(path, data))

    if findings:
        print("Blocked staged files:", file=sys.stderr)
        for finding in sorted(set(findings), key=lambda item: (item.path, item.rule)):
            print(f"  {finding.path} [{finding.rule}]", file=sys.stderr)
        return 1

    print("Staged security check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
