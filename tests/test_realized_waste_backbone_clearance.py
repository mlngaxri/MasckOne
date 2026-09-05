import cadquery as cq

from masck_one.model import build_model
from masck_one.realized_waste_backbone import Line3, build_cell4_waste_backbone
from masck_one.realized_waste_backbone_release import AUTHORED_AGAINST_MAIN_SHA


_DUMMY_ARCHITECTURE_SHA256 = "0" * 64


def _edge_for_line(line: Line3) -> cq.Edge:
    return cq.Edge.makeLine(
        cq.Vector(*line.start.as_tuple()),
        cq.Vector(*line.end.as_tuple()),
    )


def test_route_a_full_service_envelope_clears_current_released_package_geometry():
    """Bind Route A clearance to the actual released shell and actuator B-reps.

    Source-graph freshness is covered independently by the release-binding tests. This
    clearance regression deliberately constructs only the deterministic route geometry
    so the full product B-rep is not rebuilt twice in one test.

    This is a deterministic digital-geometry reservation check only. It does not
    establish tubing selection, deformation clearance, serviceability, or physical
    performance.
    """
    model = build_model()
    route = build_cell4_waste_backbone(
        source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=_DUMMY_ARCHITECTURE_SHA256,
    ).routes[0]

    assert len(route.centerline) == 1
    line = route.centerline[0]
    assert type(line) is Line3
    edge = _edge_for_line(line)
    required_radius_mm = route.service_envelope_radius_mm

    assert edge.distance(model.shell.solid.val()) >= required_radius_mm
    for actuator in model.actuator_envelopes:
        assert edge.distance(actuator.solid.val()) >= required_radius_mm
