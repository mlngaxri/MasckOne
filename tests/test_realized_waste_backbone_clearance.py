import cadquery as cq

from masck_one.model import build_model
from masck_one.realized_waste_backbone import Line3
from masck_one.realized_waste_backbone_release import (
    build_current_cell4_waste_backbone_release,
)


def _edge_for_line(line: Line3) -> cq.Edge:
    return cq.Edge.makeLine(
        cq.Vector(*line.start.as_tuple()),
        cq.Vector(*line.end.as_tuple()),
    )


def test_route_a_full_service_envelope_clears_current_released_package_geometry():
    """Bind Route A clearance to the actual released shell and actuator B-reps.

    This is a deterministic digital-geometry reservation check only. It does not
    establish tubing selection, deformation clearance, serviceability, or physical
    performance.
    """
    model = build_model()
    route = build_current_cell4_waste_backbone_release().realization.routes[0]

    assert len(route.centerline) == 1
    line = route.centerline[0]
    assert type(line) is Line3
    edge = _edge_for_line(line)
    required_radius_mm = route.service_envelope_radius_mm

    assert edge.distance(model.shell.solid.val()) >= required_radius_mm
    for actuator in model.actuator_envelopes:
        assert edge.distance(actuator.solid.val()) >= required_radius_mm
