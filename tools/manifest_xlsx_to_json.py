from __future__ import annotations

from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from tanuki_core.manifest_xlsx_converter import main as run_converter

    return run_converter(argv)


if __name__ == "__main__":
    raise SystemExit(main())
