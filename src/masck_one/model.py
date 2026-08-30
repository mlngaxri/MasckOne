from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

import cadquery as cq

from .anatomy import FacialReferenceLayer, build_facial_reference
from .authority import Authority, load_authority
from .coverage import FacialCoverageMesh, build_facial_coverage_mesh
from .facial_surface import FacialSurface, build_planar_development_surface
from .interface_boundaries import InterfaceBoundaryTopology, build_interface_boundary_topology
from .interface_topology import CompliantInterfaceTopology, build_compliant_interface_topology
from .nasal_subsystem import NasalSubsystemTopology, ROLE_LOBE, build_nasal_subsystem_topology
from .protected_volumes import ProtectedVolumeSet, build_protected_volumes
from .spatial import CanonicalDatums, Point2, Point3
from .worn_pose import WornPoseRegressionSet, generate_hard_envelope_regression_set


# Numerical-kernel diagnostics only. These are not product, drawing, process, or
# manufacturing tolerances and must never be presented as such.
CAD_BREP_BOUND_TOLERANCE_MM = 2e-6
CAD_PLANAR_FACE_SPAN_TOLERANCE_MM = 1e-10
CAD_AXIS_NORMAL_TOLERANCE = 1e-9


@dataclass(frozen=True)
class Component:
    name: str
    solid: cq.Workplane
    status: str
    notes: str = ""

    def brep_bounding_span_z_mm(self) -> float:
        """Return the OpenCascade bounding-box Z span."""
        return float(self.solid.val().BoundingBox().zlen)

    def horizontal_planar_face_span_z_mm(self) -> float:
        """Measure Z separation of horizontal planar support faces."""
        z_values: list[float] = []
        for face in self.solid.val().Faces():
            if face.geomType() != "PLANE":
                continue
            normal = face.normalAt()
            if abs(abs(float(normal.z)) - 1.0) <= CAD_AXIS_NORMAL_TOLERANCE:
                z_values.append(float(face.Center().z))
        if len(z_values) < 2:
            raise ValueError(
                f"Component {self.name!r} does not expose two horizontal planar faces for Z-span verification"
            )
        return max(z_values) - min(z_values)


@dataclass(frozen=True)
class MasckOneModel:
    authority: Authority
    datums: CanonicalDatums
    facial_reference: FacialReferenceLayer
    facial_surface: FacialSurface
    protected_volumes: ProtectedVolumeSet
    worn_pose_regression: WornPoseRegressionSet
    coverage_mesh: FacialCoverageMesh
    compliant_interface_topology: CompliantInterfaceTopology
    nasal_subsystem_topology: NasalSubsystemTopology
    interface_boundary_topology: InterfaceBoundaryTopology
    shell: Component
    nasal_interface: Component
    actuator_envelopes: tuple[Component, ...]
    water_reservoir_envelope: Component
    waste_cartridge_envelope: Component
    battery_reference_envelope: Component
    visual_keepouts: tuple[Component, ...]

    @property
    def components(self) -> tuple[Component, ...]:
        return (
            self.shell,
            self.nasal_interface,
            *self.actuator_envelopes,
            self.water_reservoir_envelope,
            self.waste_cartridge_envelope,
            self.battery_reference_envelope,
            *self.visual_keepouts,
        )


def _loft_ellipses(sections: Iterable[tuple[float, float, float]]) -> cq.Workplane:
    sections = list(sections)
    if len(sections) < 2:
        raise ValueError("At least two loft sections are required")
    z0, w0, h0 = sections[0]
    wp = cq.Workplane("XY").workplane(offset=z0).ellipse(w0 / 2.0, h0 / 2.0)
    previous_z = z0
    for z, width, height in sections[1:]:
        wp = wp.workplane(offset=z - previous_z).ellipse(width / 2.0, height / 2.0)
        previous_z = z
    return wp.loft(combine=True, ruled=True)


def _ellipse_cutter(width: float, height: float, center: Point2, depth: float = 50.0, z_start: float = -10.0, angle_deg: float = 0.0) -> cq.Workplane:
    cutter = (
        cq.Workplane("XY").workplane(offset=z_start).center(center.x, center.y)
        .ellipse(width / 2.0, height / 2.0).extrude(depth)
    )
    if angle_deg:
        cutter = cutter.rotate((center.x, center.y, 0.0), (center.x, center.y, 1.0), angle_deg)
    return cutter


def _circle_cutter(diameter: float, center: Point2, depth: float = 50.0, z_start: float = -10.0) -> cq.Workplane:
    return (
        cq.Workplane("XY").workplane(offset=z_start).center(center.x, center.y)
        .circle(diameter / 2.0).extrude(depth)
    )


def _box_centered(width_x: float, height_y: float, depth_z: float, center: Point3) -> cq.Workplane:
    return cq.Workplane("XY").box(width_x, height_y, depth_z, centered=(True, True, True)).translate(center.as_tuple())


def _derived_nostril_diameter(authority: Authority) -> float:
    minimum_area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    minimum_dim = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    diameter_from_area = math.sqrt(4.0 * minimum_area * 1.02 / math.pi)
    return max(minimum_dim, diameter_from_area)


def _build_shell(authority: Authority, facial_reference: FacialReferenceLayer) -> cq.Workplane:
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    frame_w, frame_h = authority.pair("geometry", "functional_frame_xy_mm")
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    outer = _loft_ellipses([(0.0, frame_w, frame_h), (10.0, outer_w - 4.0, outer_h - 3.0), (22.0, outer_w, outer_h)])
    inner = _loft_ellipses([
        (-1.0, frame_w - 2.0 * wall, frame_h - 2.0 * wall),
        (10.0, outer_w - 4.0 - 2.0 * wall, outer_h - 3.0 - 2.0 * wall),
        (22.0 - wall, outer_w - 2.0 * wall, outer_h - 2.0 * wall),
    ])
    shell = outer.cut(inner)
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    cant = authority.number("geometry", "eye", "lateral_cant_deg")
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, facial_reference.eye_pair.left.point_xy, angle_deg=-cant))
    shell = shell.cut(_ellipse_cutter(eye_w, eye_h, facial_reference.eye_pair.right.point_xy, angle_deg=cant))
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    shell = shell.cut(_ellipse_cutter(mouth_w, mouth_h, facial_reference.mouth_center.point_xy))
    nostril_diameter = _derived_nostril_diameter(authority)
    shell = shell.cut(_circle_cutter(nostril_diameter, facial_reference.nostril_pair.left.point_xy))
    shell = shell.cut(_circle_cutter(nostril_diameter, facial_reference.nostril_pair.right.point_xy))
    return shell


def _build_nasal_lobe_membrane_reference(
    authority: Authority,
    nasal_topology: NasalSubsystemTopology,
    protected: ProtectedVolumeSet,
) -> cq.Workplane:
    role = nasal_topology.role_by_id[ROLE_LOBE]
    if role.nominal_thickness_mm is None:
        raise ValueError("Nasal lobe role must carry the authority-backed center thickness")
    thickness = role.nominal_thickness_mm
    b = nasal_topology.boundaries
    width = 2.0 * b.lobe_half_width_mm
    height = b.lobe_y_max_mm - b.lobe_y_min_mm
    center_y = (b.lobe_y_min_mm + b.lobe_y_max_mm) / 2.0
    membrane = (
        cq.Workplane("XY")
        .workplane(offset=-thickness)
        .center(0.0, center_y)
        .rect(width, height)
        .extrude(thickness)
    )
    for volume in (protected.nostril_left, protected.nostril_right):
        zone = volume.zone
        membrane = membrane.cut(
            _ellipse_cutter(
                zone.envelope_width_mm,
                zone.envelope_height_mm,
                zone.center,
                depth=5.0,
                z_start=-3.0,
                angle_deg=zone.angle_deg,
            )
        )
    return membrane


def _build_actuators(authority: Authority) -> tuple[Component, ...]:
    count = int(authority.number("actuation", "count"))
    if count != 4:
        raise ValueError(f"This architecture expects four actuator zones, authority gives {count}")
    angle = authority.number("actuation", "clean", "axis_angle_baseline_deg")
    diameter, length = 10.2, 18.7
    placements = [
        (Point3(-48.0, 52.0, 2.0), +1.0), (Point3(48.0, 52.0, 2.0), -1.0),
        (Point3(-50.0, -38.0, 2.0), +1.0), (Point3(50.0, -38.0, 2.0), -1.0),
    ]
    parts: list[Component] = []
    for index, (center, sign) in enumerate(placements, start=1):
        solid = cq.Workplane("XY").circle(diameter / 2.0).extrude(length)
        solid = solid.rotate((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), sign * angle).translate(center.as_tuple())
        parts.append(Component(
            name=f"actuator_envelope_{index}", solid=solid, status="ALPHA_PHYSICS_REFERENCE",
            notes="H2W NCM01-04-001-2IBH package envelope; production actuator remains validation-gated.",
        ))
    return tuple(parts)


def _build_visual_keepouts(authority: Authority, facial_reference: FacialReferenceLayer) -> tuple[Component, ...]:
    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    nostril_d = _derived_nostril_diameter(authority)
    return (
        Component("visual_eye_left", _ellipse_cutter(eye_w, eye_h, facial_reference.eye_pair.left.point_xy), "REFERENCE_ONLY"),
        Component("visual_eye_right", _ellipse_cutter(eye_w, eye_h, facial_reference.eye_pair.right.point_xy), "REFERENCE_ONLY"),
        Component("visual_mouth", _ellipse_cutter(mouth_w, mouth_h, facial_reference.mouth_center.point_xy), "REFERENCE_ONLY"),
        Component("visual_nostril_left", _circle_cutter(nostril_d, facial_reference.nostril_pair.left.point_xy), "REFERENCE_ONLY"),
        Component("visual_nostril_right", _circle_cutter(nostril_d, facial_reference.nostril_pair.right.point_xy), "REFERENCE_ONLY"),
    )


def build_model(authority: Authority | None = None) -> MasckOneModel:
    authority = authority or load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    facial_surface = build_planar_development_surface(authority)
    protected_volumes = build_protected_volumes(authority, facial_reference, facial_surface)
    worn_pose_regression = generate_hard_envelope_regression_set(authority)
    coverage_mesh = build_facial_coverage_mesh(authority, facial_reference, facial_surface, protected_volumes)
    compliant_interface_topology = build_compliant_interface_topology(authority, coverage_mesh)
    nasal_subsystem_topology = build_nasal_subsystem_topology(
        authority,
        coverage_mesh,
        compliant_interface_topology,
        protected_volumes,
    )
    interface_boundary_topology = build_interface_boundary_topology(
        authority,
        facial_surface,
        coverage_mesh,
        compliant_interface_topology,
    )
    shell = Component(
        "rigid_shell", _build_shell(authority, facial_reference), "CAD_BASELINE",
        "XY envelope and apertures follow authority; Class-A Z surface remains CAD-CLOSURE.",
    )
    nasal_interface = Component(
        "nasal_lobe_membrane_reference",
        _build_nasal_lobe_membrane_reference(authority, nasal_subsystem_topology, protected_volumes),
        "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE",
        "Only the dedicated nasal-lobe development role carries the 0.30 mm authority thickness; bridge, dorsum, sidewall and philtrum thicknesses remain unresolved. Not final anatomical membrane CAD.",
    )
    water_reservoir = Component(
        "water_reservoir_envelope", _box_centered(26.0, 25.0, 10.0, Point3(0.0, 76.0, 7.0)),
        "ENGINEERING_BASELINE_ENVELOPE", "6500 mm^3 gross volume; final wall/port geometry not frozen.",
    )
    cw, ch, cd = (float(v) for v in authority.get("fluid", "cartridge", "external_envelope_mm"))
    waste_cartridge = Component(
        "waste_cartridge_envelope", _box_centered(cw, ch, cd, Point3(0.0, -80.0, 8.0)),
        "ENGINEERING_BASELINE_ENVELOPE", "External envelope only; retained capacity is a physical validation gate.",
    )
    bw, bh, bd = authority.get("battery_reference", "envelope_mm")
    battery = Component(
        "battery_reference_envelope", _box_centered(float(bw), float(bh), float(bd), Point3(0.0, 0.0, -15.0)),
        "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE", "Halo-location benchmark only; not a production-qualified battery pack.",
    )
    return MasckOneModel(
        authority=authority,
        datums=datums,
        facial_reference=facial_reference,
        facial_surface=facial_surface,
        protected_volumes=protected_volumes,
        worn_pose_regression=worn_pose_regression,
        coverage_mesh=coverage_mesh,
        compliant_interface_topology=compliant_interface_topology,
        nasal_subsystem_topology=nasal_subsystem_topology,
        interface_boundary_topology=interface_boundary_topology,
        shell=shell,
        nasal_interface=nasal_interface,
        actuator_envelopes=_build_actuators(authority),
        water_reservoir_envelope=water_reservoir,
        waste_cartridge_envelope=waste_cartridge,
        battery_reference_envelope=battery,
        visual_keepouts=_build_visual_keepouts(authority, facial_reference),
    )
