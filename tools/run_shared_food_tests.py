from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.suite_catalog import SHARED_FOOD_TEST_LAYERS


def build_shared_food_suite(layer: str) -> unittest.TestSuite:
    selected_layers = (
        tuple(SHARED_FOOD_TEST_LAYERS)
        if layer == "all"
        else (layer,)
    )
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for layer_name in selected_layers:
        for module_name in SHARED_FOOD_TEST_LAYERS[layer_name]:
            suite.addTests(
                loader.loadTestsFromName(f"tests.{module_name}")
            )
    return suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Tanuki shared-food tests by architecture layer.",
    )
    parser.add_argument(
        "--layer",
        choices=(*SHARED_FOOD_TEST_LAYERS, "all"),
        default="all",
        help="Test layer to run. Defaults to all layers.",
    )
    parser.add_argument(
        "--verbosity",
        type=int,
        choices=(0, 1, 2),
        default=1,
        help="unittest output verbosity. Defaults to 1.",
    )
    args = parser.parse_args(argv)

    result = unittest.TextTestRunner(
        verbosity=args.verbosity,
    ).run(build_shared_food_suite(args.layer))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
