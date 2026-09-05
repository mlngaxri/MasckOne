import cadquery as cq

from masck_one.model import build_model
from masck_one.realized_waste_backbone import Line3
from masck_one.realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from masck_one.waste_pump_architecture import ROUTE_ACQUISITION_TO_PUMP


def test_acquisition_route_service_envelope_clears_released_actuator_3_brep():
    """Bind the provisional route reservation to the actual accepted actuator package."""
    release = build_current_cell4_waste_backbone_release()
    route = next(
        item
        for item in release.realization.routes
        if item.route_id == ROUTE_ACQUISITION_TO_PUMP
    )
    assert len(route.centerline) == 1
    line = route.centerline[0]
    assert type(line) is Line3

    model = build_model()
    actuator = next(
        component
        for component in model.actuator_envelopes
        if component.name == "actuator_envelope_3"
    )

    centerline_edge = cq.Edge.makeLine(
        cq.Vector(*line.start.as_tuple()),
        cq.Vector(*line.end.as_tuple()),
    )
    centerline_to_actuator_surface_mm = centerline_edge.distance(actuator.solid.val())
    digital_service_margin_mm = (
        centerline_to_actuator_surface_mm - route.service_envelope_radius_mm
    )

    assert centerline_to_actuator_surface_mm > route.service_envelope_radius_mm
    assert digital_service_margin_mm > 0.0
