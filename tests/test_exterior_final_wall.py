import cadquery as cq

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import build_refined_exterior_shell
from masck_one.spatial import CanonicalDatums


SIDE_BODY_THICKNESS_Z_SAMPLES_MM = (
    0.0,
    0.25,
    0.5,
    1.0,
    1.5,
    2.0,
    4.5,
    10.0,
    16.0,
    18.0,
    20.0,
)

# Axial probes through the final crown include the forehead, eye-adjacent field,
# nasal bridge, mouth-adjacent field and lower chin. They intentionally avoid the
# protected openings themselves and screen the final fused/cut B-rep, not the control net.
CROWN_AXIAL_THICKNESS_SAMPLES_XY_MM = (
    (0.0, 65.0),
    (-31.5, 54.0),
    (31.5, 54.0),
    (0.0, 35.0),
    (0.0, -7.5),
    (0.0, -30.0),
    (-35.0, -50.0),
    (35.0, -50.0),
    (0.0, -72.0),
)

KERNEL_TOLERANCE_MM = 1e-5


def _build_final_shell():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    shell = build_refined_exterior_shell(authority, facial_reference).val()
    return authority, shell


def _side_body_outer_to_inner_distance_mm(solid: cq.Shape, z_mm: float) -> float:
    section = cq.Workplane("XY").workplane(offset=z_mm).newObject([solid]).section().val()
    wires = section.Wires()
    assert len(wires) >= 2
    ordered = sorted(
        wires,
        key=lambda wire: wire.BoundingBox().xlen * wire.BoundingBox().ylen,
        reverse=True,
    )
    return float(ordered[0].distance(ordered[1]))


def test_final_brep_side_body_and_rear_rim_meet_absolute_wall_minimum():
    authority, solid = _build_final_shell()
    absolute_min = authority.number("geometry", "shell_absolute_development_min_mm")
    measured = {
        z_mm: _side_body_outer_to_inner_distance_mm(solid, z_mm)
        for z_mm in SIDE_BODY_THICKNESS_Z_SAMPLES_MM
    }
    assert min(measured.values()) + KERNEL_TOLERANCE_MM >= absolute_min


def test_final_brep_crown_and_aperture_adjacent_samples_meet_wall_minimum():
    authority, solid = _build_final_shell()
    absolute_min = authority.number("geometry", "shell_absolute_development_min_mm")

    for x_mm, y_mm in CROWN_AXIAL_THICKNESS_SAMPLES_XY_MM:
        probe = cq.Edge.makeLine(
            cq.Vector(x_mm, y_mm, 20.0),
            cq.Vector(x_mm, y_mm, 35.0),
        )
        material = solid.intersect(probe)
        segments = material.Edges()
        assert segments
        assert min(float(segment.Length()) for segment in segments) + KERNEL_TOLERANCE_MM >= absolute_min
