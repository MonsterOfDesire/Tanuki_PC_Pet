from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LightweightFailure:
    kind: str
    name: str
    suite: str


@dataclass(frozen=True)
class LightweightCheckSummary:
    passed: bool
    total_tests: int
    failures: int
    errors: int
    failing_cases: tuple[LightweightFailure, ...]
    raw_output: str


def extract_test_module_name(failure_name: str) -> str:
    match = re.search(r"\(([^)]+)\)$", failure_name)
    if not match:
        return ""
    parts = match.group(1).split(".")
    if len(parts) >= 2:
        return parts[-2]
    return parts[0]


def parse_unittest_output(output: str) -> LightweightCheckSummary:
    try:
        from tests.suite_catalog import classify_test_module
    except Exception:
        classify_test_module = lambda _name: "uncategorized"

    total_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in", output)
    total_tests = int(total_match.group(1)) if total_match else 0

    failures = 0
    errors = 0
    failed_match = re.search(r"FAILED\s+\(([^)]+)\)", output)
    if failed_match:
        for token in failed_match.group(1).split(","):
            token = token.strip()
            if token.startswith("failures="):
                failures = int(token.split("=", 1)[1])
            elif token.startswith("errors="):
                errors = int(token.split("=", 1)[1])

    failing_cases = tuple(
        LightweightFailure(
            kind=kind,
            name=name,
            suite=classify_test_module(extract_test_module_name(name)),
        )
        for kind, name in re.findall(r"^(FAIL|ERROR):\s+(.+)$", output, flags=re.MULTILINE)
    )
    passed = bool(re.search(r"^OK$", output, flags=re.MULTILINE))
    return LightweightCheckSummary(
        passed=passed,
        total_tests=total_tests,
        failures=failures,
        errors=errors,
        failing_cases=failing_cases,
        raw_output=output,
    )


def build_lightweight_report(summary: LightweightCheckSummary, command: list[str]) -> str:
    status = "PASS" if summary.passed else "FAIL"
    lines = [
        "# Lightweight Test Report",
        "",
        f"- Result: `{status}`",
        f"- Total tests: `{summary.total_tests}`",
        f"- Failures: `{summary.failures}`",
        f"- Errors: `{summary.errors}`",
        f"- Command: `{' '.join(command)}`",
    ]
    if summary.failing_cases:
        lines.extend(["", "## Failing Cases", ""])
        for failure in summary.failing_cases:
            lines.append(f"- `{failure.kind}` `{failure.name}` `{failure.suite}`")
        suite_counts = {}
        for failure in summary.failing_cases:
            suite_counts[failure.suite] = suite_counts.get(failure.suite, 0) + 1
        lines.extend(["", "## Failing Suites", ""])
        for suite_name in sorted(suite_counts):
            lines.append(f"- `{suite_name}` `{suite_counts[suite_name]}`")
    return "\n".join(lines) + "\n"


def run_lightweight_checks(repo_root: str | Path, python_executable: str | None = None) -> tuple[int, LightweightCheckSummary, str]:
    repo_root = Path(repo_root)
    tanuki_app_dir = repo_root / "tanuki_app"
    tests_dir = tanuki_app_dir / "tests"
    command = [
        python_executable or sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        str(tests_dir),
    ]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(tanuki_app_dir) if not existing_pythonpath else f"{tanuki_app_dir}{os.pathsep}{existing_pythonpath}"
    completed = subprocess.run(
        command,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    summary = parse_unittest_output(output)
    report = build_lightweight_report(summary, command)
    return completed.returncode, summary, report


def write_lightweight_report(report_path: str | Path, report: str) -> Path:
    report_path = Path(report_path)
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main(argv: list[str] | None = None) -> int:
    _ = argv or sys.argv[1:]
    repo_root = Path(__file__).resolve().parents[2]
    exit_code, _summary, report = run_lightweight_checks(repo_root)
    report_path = write_lightweight_report(repo_root / "LIGHTWEIGHT_TEST_REPORT.md", report)
    print(report, end="")
    print(f"Report written to: {report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
