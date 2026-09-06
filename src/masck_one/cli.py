from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .export import export_release
from .wet_electrical_candidate_landscape import build_candidate_landscape_manifest
from .wet_electrical_source_graph import build_wet_electrical_source_graph


WET_ELECTRICAL_SOURCE_GRAPH_FILENAME = "wet_electrical_source_graph_v2.json"
WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME = "wet_electrical_candidate_landscape_v1.json"


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


def _write_json(path: Path, payload: dict[str, object], *, sort_keys: bool = True) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=sort_keys, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def export_wet_electrical_receipts(output_dir: Path) -> dict[str, object]:
    if not isinstance(output_dir, Path):
        raise TypeError("output_dir must be an exact pathlib.Path")
    output_dir.mkdir(parents=True, exist_ok=True)
    source_graph = build_wet_electrical_source_graph().manifest()
    candidate_landscape = build_candidate_landscape_manifest()
    _write_json(output_dir / WET_ELECTRICAL_SOURCE_GRAPH_FILENAME, source_graph)
    _write_json(
        output_dir / WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME,
        candidate_landscape,
    )
    return {
        "wet_electrical_source_graph": source_graph,
        "wet_electrical_candidate_landscape": candidate_landscape,
    }


def bind_wet_electrical_receipts_to_report(
    report: dict[str, object],
    receipts: dict[str, object],
    output_dir: Path,
) -> None:
    if type(report) is not dict or type(receipts) is not dict or not isinstance(output_dir, Path):
        raise TypeError("report/receipts/output_dir must be exact dict/dict/path types")
    source_graph = receipts["wet_electrical_source_graph"]
    candidate_landscape = receipts["wet_electrical_candidate_landscape"]
    if type(source_graph) is not dict or type(candidate_landscape) is not dict:
        raise TypeError("wet/electrical receipt payloads must be exact dicts")
    report["wet_electrical_receipts"] = {
        "source_graph_manifest_sha256": source_graph["manifest_sha256"],
        "candidate_landscape_manifest_sha256": candidate_landscape["manifest_sha256"],
        "files": [
            WET_ELECTRICAL_SOURCE_GRAPH_FILENAME,
            WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME,
        ],
    }
    _write_json(output_dir / "build_report.json", report, sort_keys=False)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output)
    report = export_release(output_dir)
    receipts = export_wet_electrical_receipts(output_dir)
    bind_wet_electrical_receipts_to_report(report, receipts, output_dir)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())