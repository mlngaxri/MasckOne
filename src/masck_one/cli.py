from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .export import export_release
from .exterior_evidence import render_exterior_view_evidence


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
    output = Path(args.output)
    report = export_release(output)
    # Preserve actual Cell 2 shell plus rear-skin multiview evidence in the same
    # source-bound smoke artifact. Any invalid B-rep or empty section fails the CLI.
    render_exterior_view_evidence(output)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
