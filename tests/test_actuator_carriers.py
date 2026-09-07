from __future__ import annotations

from dataclasses import replace
import json

import cadquery as cq
import pytest

import masck_one.actuator_carriers as carrier_module
from masck_one.actuator_carriers import (
    ActuatorCarrierError,
    EVIDENCE_STATUS,
    LOCAL_FRAME_ID,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    build_actuator_carrier_package,
    export_actuator_carrier_package,
)
from masck_one.model import build_model


@pytest.fixture(scope="module")
def carrier_package():
    return build_actuator_carrier_package()


def test_local_carrier_realizes_positive_capture_without_promoting_world_mount(carrier_package):
    assert carrier_package.source_main_sha == SOURCE_MAIN_SHA
    assert carrier_package.local_frame_id == LOCAL_FRAME_ID
    assert carrier_package.target_world_frame_id == WORLD_FRAME_ID
    assert carrier_package.positive_radial_capture_realized is True
    assert carrier_package.positive_axial_stops_realized is True
    assert carrier_package.split_closure_positive_retention_realized is True
    assert carrier_package.structural_frame_attachment_realized is False
    assert carrier_package.production_tolerance_stack_resolved is False
    assert carrier_package.physical_validation_eligible is False
    assert carrier_package.evidence_status == EVIDENCE_STATUS
    assert len(carrier_package.parts) == 6
    assert all(len(part.solid.solids().vals()) == 1 for part in carrier_package.parts)


def test_world_reference_screens_fail_closed_on_inherited_protected_conflicts(carrier_package):
    assert len(carrier_package.zone_world_screens) == 4
    for screen in carrier_package.zone_world_screens:
        assert screen.source_package_protected_intersection_mm3 > 0.0
        assert screen.carrier_review_protected_intersection_mm3 > 0.0
        assert screen.world_mount_eligible is False
        assert screen.baseline_world_transform_status.endswith(
            "INHERITED_PROTECTED_HARD_ENVELOPE_CONFLICT"
        )
        assert screen.angle_doe_clearance_status.startswith("BLOCKED_BASELINE_PROTECTED_HARD_ENVELOPE")
        assert screen.frame_attachment_status.startswith("BLOCKED_RELEASED_STRUCTURAL_FRAME_IS_TOPOLOGY_ONLY")


def test_manifest_separates_reference_placements_from_mount_datums(carrier_package):
    manifest = carrier_package.manifest()
    assert manifest["schema"] == "MASCK_ONE_CELL7_ACTUATOR_CARRIER_TEMPLATE_V1"
    assert manifest["world_material_promotion_status"].startswith("BLOCKED_CURRENT_MODEL_REFERENCE_PLACEMENTS")
    assert manifest["angle_doe_status"].startswith("BLOCKED_NO_CLEARANCE_PASS_CLAIM")
    assert manifest["structural_frame_attachment_realized"] is False
    assert manifest["production_tolerance_stack_resolved"] is False
    assert manifest["supplier_status"].endswith("PACKAGE_EVIDENCE_ONLY")
    assert len(manifest["source_reference_placements"]) == 4
    assert all(
        item["status"] == "CURRENT_MODEL_PACKAGE_REFERENCE_TRANSFORM_ONLY_NOT_STRUCTURAL_MOUNT_DATUM"
        for item in manifest["source_reference_placements"]
    )
    assert len(manifest["package_sha256"]) == 64


def test_source_model_geometry_substitution_is_rejected_before_mount_review():
    model = build_model()
    bad_first = replace(
        model.actuator_envelopes[0],
        solid=cq.Workplane("XY").box(10.2, 10.2, 18.7),
    )
    bad_model = replace(
        model,
        actuator_envelopes=(bad_first, *model.actuator_envelopes[1:]),
    )
    with pytest.raises(ActuatorCarrierError, match="no longer matches the source-bound"):
        build_actuator_carrier_package(model=bad_model)


def test_source_component_evidence_status_drift_is_rejected():
    model = build_model()
    bad_first = replace(model.actuator_envelopes[0], status="PRODUCTION_FROZEN")
    bad_model = replace(model, actuator_envelopes=(bad_first, *model.actuator_envelopes[1:]))
    with pytest.raises(ActuatorCarrierError, match="evidence status changed"):
        build_actuator_carrier_package(model=bad_model)


def test_source_blob_movement_is_fail_closed(monkeypatch):
    original = carrier_module.SOURCE_GIT_BLOB_IDENTITIES
    mutated = tuple(
        (path, "0" * 40 if path == "src/masck_one/model.py" else digest)
        for path, digest in original
    )
    monkeypatch.setattr(carrier_module, "SOURCE_GIT_BLOB_IDENTITIES", mutated)
    with pytest.raises(ActuatorCarrierError, match="source moved at src/masck_one/model.py"):
        build_actuator_carrier_package()


def test_deterministic_carrier_artifacts_round_trip(tmp_path, carrier_package):
    exported = export_actuator_carrier_package(tmp_path, package=carrier_package)
    assert exported["world_review_is_product_material"] is False
    assert exported["local_template_is_world_mount"] is False
    assert len(exported["step_files"]) == 8

    for filename in exported["step_files"]:
        path = tmp_path / filename
        assert path.is_file()
        imported = cq.importers.importStep(str(path))
        assert imported.solids().size() >= 1

    manifest_path = tmp_path / exported["manifest_file"]
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted == carrier_package.manifest()
