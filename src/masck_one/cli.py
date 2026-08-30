from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .export import export_release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="masck-one-cad",
        description="Generate the current deterministic Masck One code-CAD baseline.",
    )
    parser.add_argument(
        "--output",
        default="generated",
        help="Directory for generated STEP files and build_report.json (default: generated)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = export_release(Path(args.output))
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
