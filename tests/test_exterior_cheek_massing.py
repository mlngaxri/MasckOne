import cadquery as cq

from masck_one.exterior_construction import (
    CHEEK_TEMPLE_SCALE_X,
    constructed_exterior_sections,
)
from masck_one.integrated_product import build_mvp_product_candidate
from masck_one.realized_waste_backbone import ArcXY, Line3
from masck_one.realized_waste_backbone_release import (
    build_current_cell4_waste_backbone_release,
)


EXPECTED_SCALE_X = (1.000, 1.020, 1.028, 1.036, 1.004)
MIDBODY_MAX_WIDTH_MM = 161.5
ANTERIOR_TAPER_MIN_MM = 4.0
COLLISION_VOLUME_TOLERANCE_MM3 = 1e-6
KERNEL_TOLERANCE_MM = 1e-5


def _section_x_span_mm(solid: cq.Shape, z_mm: float) -> float:
    section = cq.Workplane("XY").workplane(offset=z_mm).newObject([solid]).section()
    assert section.size() > 0
    return float(section.val().BoundingBox().xlen)


def _primitive_edge(primitive: Line3 | ArcXY) -> cq.Edge:
    if type(primitive) is Line3:
        return cq.Edge.makeLine(
            cq.Vector(*primitive.start.as_tuple()),
            cq.Vector(*primitive.end.as_tuple()),
        )
    if type(primitive) is ArcXY:
        return cq.Edge.makeCircle(
            primitive.radius_mm,
            cq.Vector(*primitive.center.as_tuple()),
            cq.Vector(0.0, 0.0, 1.0),
            primitive.start_angle_deg,
            primitive.start_angle_deg + primitive.sweep_angle_deg,
        )
    raise AssertionError("uncontrolled waste-route primitive")


def test_cheek_temple_massing_is_tightened_without_losing_anterior_taper():
    model = build_mvp_product_candidate()
    solid = model.shell.solid.val()
    sections = constructed_exterior_sections(model.authority)

    assert CHEEK_TEMPLE_SCALE_X == EXPECTED_SCALE_X
    assert max(section[1] for section in sections) <= MIDBODY_MAX_WIDTH_MM

    midbody_width = _section_x_span_mm(solid, 16.0)
    anterior_width = _section_x_span_mm(solid, 21.5)
    assert midbody_width <= MIDBODY_MAX_WIDTH_MM
    assert midbody_width - anterior_width >= ANTERIOR_TAPER_MIN_MM


def test_tightened_side_mass_preserves_released_actuator_envelopes():
    model = build_mvp_product_candidate()
    shell = model.shell.solid.val()
    for actuator in model.actuator_envelopes:
        intersection = shell.intersect(actuator.solid.val())
        assert abs(float(intersection.Volume())) <= COLLISION_VOLUME_TOLERANCE_MM3


def test_tightened_side_mass_preserves_released_waste_route_service_reservation():
    model = build_mvp_product_candidate()
    shell = model.shell.solid.val()
    release = build_current_cell4_waste_backbone_release()

    for route in release.realization.routes:
        for primitive in route.centerline:
            centerline_edge = _primitive_edge(primitive)
            assert (
                float(shell.distance(centerline_edge))
                + KERNEL_TOLERANCE_MM
                >= route.service_envelope_radius_mm
            )
