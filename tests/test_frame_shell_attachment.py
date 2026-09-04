import hashlib
import json

import pytest

from masck_one.authority import load_authority
from masck_one.frame_shell_attachment import (
    BRIDGE_IDS,
    SCHEMA,
    build_frame_shell_attachment,
)


@pytest.fixture(scope="module")
def attachment():
    return build_frame_shell_attachment(load_authority())


def test_attachment_is_deterministic_and_uses_three_controlled_bridges(attachment):
    assert attachment.manifest()["schema"] == SCHEMA
    assert tuple(bridge.bridge_id for bridge in attachment.bridges) == BRIDGE_IDS
    payload = attachment.manifest(include_sha=False)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert attachment.attachment_sha256 == digest


def test_every_bridge_has_positive_3d_frame_and_shell_engagement(attachment):
    for bridge in attachment.bridges:
        assert bridge.frame_intersection_mm3 > 0.0
        assert bridge.shell_intersection_mm3 > 0.0
        assert "NOT_MATERIAL_FASTENER_ADHESIVE_STIFFNESS_FATIGUE" in bridge.evidence_status


def test_bridges_clear_released_packages_and_conservative_protected_screens(attachment):
    failures = [record.manifest() for record in attachment.clearance_records if not record.passes]
    assert not failures, f"Frame-shell attachment conflicts remain: {failures}"


def test_three_point_support_has_real_lateral_and_superior_reaction_span(attachment):
    assert attachment.support_x_span_mm > 140.0
    assert attachment.support_y_span_mm > 90.0
    assert attachment.lower_center_service_preserved


def test_actuator_load_paths_use_authority_force_demands_without_claiming_capacity(attachment):
    authority = load_authority()
    continuous = float(authority.get("actuation", "clean", "continuous_force_requirement_N"))
    transient = float(authority.get("actuation", "clean", "transient_force_requirement_N"))
    actuator_paths = tuple(path for path in attachment.load_paths if path.load_path_id.startswith("ACTUATOR-"))
    assert len(actuator_paths) == 8
    assert sorted(path.demand_N for path in actuator_paths).count(continuous) == 4
    assert sorted(path.demand_N for path in actuator_paths).count(transient) == 4
    assert all(path.geometry_closed for path in actuator_paths)
    assert all(not path.physical_capacity_validated for path in actuator_paths)


def test_retention_load_path_is_geometry_closed_but_force_and_capacity_remain_unresolved(attachment):
    retention = next(path for path in attachment.load_paths if path.load_path_id == "RETENTION-HALO-TO-SHELL")
    assert retention.geometry_closed
    assert retention.demand_N is None
    assert "UNRESOLVED" in retention.demand_status
    assert not retention.physical_capacity_validated
    assert "NOT_MATERIAL_STIFFNESS_STRESS_FATIGUE_FASTENER_OR_PHYSICAL_VALIDATION" in attachment.evidence_status
