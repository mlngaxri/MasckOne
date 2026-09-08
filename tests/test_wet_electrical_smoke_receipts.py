import json

import pytest

from masck_one.cli import (
    WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME,
    WET_ELECTRICAL_SOURCE_GRAPH_FILENAME,
    bind_wet_electrical_receipts_to_report,
    export_wet_electrical_receipts,
)


def test_wet_electrical_receipts_are_deterministic_standalone_smoke_artifacts(tmp_path):
    assert WET_ELECTRICAL_SOURCE_GRAPH_FILENAME == "wet_electrical_source_graph_v2.json"
    assert WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME == (
        "wet_electrical_candidate_landscape_v1.json"
    )
    first = export_wet_electrical_receipts(tmp_path)
    source_path = tmp_path / WET_ELECTRICAL_SOURCE_GRAPH_FILENAME
    candidate_path = tmp_path / WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME
    assert source_path.is_file()
    assert candidate_path.is_file()
    first_source_bytes = source_path.read_bytes()
    first_candidate_bytes = candidate_path.read_bytes()

    second = export_wet_electrical_receipts(tmp_path)
    assert second == first
    assert source_path.read_bytes() == first_source_bytes
    assert candidate_path.read_bytes() == first_candidate_bytes
    assert json.loads(source_path.read_text(encoding="utf-8")) == first[
        "wet_electrical_source_graph"
    ]
    assert json.loads(candidate_path.read_text(encoding="utf-8")) == first[
        "wet_electrical_candidate_landscape"
    ]


def test_receipt_hashes_are_bound_into_build_report(tmp_path):
    receipts = export_wet_electrical_receipts(tmp_path)
    report = {"project": "Masck One", "result": "PASS"}
    bind_wet_electrical_receipts_to_report(report, receipts, tmp_path)
    written = json.loads((tmp_path / "build_report.json").read_text(encoding="utf-8"))
    assert written == report
    assert written["wet_electrical_receipts"] == {
        "source_graph_manifest_sha256": receipts["wet_electrical_source_graph"][
            "manifest_sha256"
        ],
        "candidate_landscape_manifest_sha256": receipts[
            "wet_electrical_candidate_landscape"
        ]["manifest_sha256"],
        "files": [
            WET_ELECTRICAL_SOURCE_GRAPH_FILENAME,
            WET_ELECTRICAL_CANDIDATE_LANDSCAPE_FILENAME,
        ],
    }


def test_wet_electrical_receipt_output_requires_exact_types(tmp_path):
    with pytest.raises(TypeError, match="exact pathlib.Path"):
        export_wet_electrical_receipts(str(tmp_path))
    receipts = export_wet_electrical_receipts(tmp_path)
    with pytest.raises(TypeError, match="exact dict/dict/path types"):
        bind_wet_electrical_receipts_to_report([], receipts, tmp_path)
