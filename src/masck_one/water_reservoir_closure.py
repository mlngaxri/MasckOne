from __future__ import annotations

"""Positive digital lid capture and seal-interface geometry for the fresh-water module.

The closure in this module is a manufacturable-in-principle Cell 4 CAD baseline, not
a production closure selection. Rail, key, groove and service dimensions are explicit
provisional geometry. No seal material/compression, insertion force, flexure strain,
leakage, durability, wet-hand usability or hygiene performance is established here.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

import cadquery as cq

from .authority import Authority
from .realized_water_reservoir import (
    PACKAGE_CLEARANCE_RESERVATION_MM,
    SERVICE_WITHDRAWAL_TRAVEL_MM,
    RealizedWaterReservoir,
    build_realized_water_reservoir,
)
from .spatial import Point3, Vector3
from .water_reservoir import WaterReservoirError
from .water_reservoir_interfaces import (
    FLUID_IDENTITY,
    WaterReservoirInterfaceGeometry,
    build_water_reservoir_interface_geometry,
)

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
CLOSURE_STATUS = "CELL4_PROVISIONAL_CAPTURED_SLIDE_LID_NOT_PRODUCTION_CLOSURE"
SEAL_STATUS = "CONTINUOUS_SEAL_LAND_GROOVE_GEOMETRY_NO_SEAL_MATERIAL_OR_COMPRESSION_SELECTION"
KEY_STATUS = "PROVISIONAL_COMPLIANT_DETENT_SERVICE_KEY_FORCE_AND_STRAIN_UNVALIDATED"
SERVICE_STATUS = "MODULE_REMOVAL_PRECEDES_KEY_RELEASE_AND_LID_SERVICE_DIGITAL_SEQUENCE_ONLY"
PHYSICAL_EVIDENCE_STATUS = (
    "DIGITAL_POSITIVE_LID_CAPTURE_AND_SEAL_INTERFACE_ONLY_NOT_LEAKAGE_SEAL_FORCE_"
    "MATERIAL_STRAIN_DURABILITY_WET_HAND_HYGIENE_OR_SERVICE_VALIDATION"
)

# Bilateral guide/capture rails stay outside the continuous seal land. The only package
# growth is local service/retention material and is separately collision-screened.
RAIL_SUPPORT_INNER_X_MM = 13.9
RAIL_SUPPORT_OUTER_X_MM = 15.0
RAIL_Y_MIN_MM = 64.0
RAIL_Y_MAX_MM = 88.0
RAIL_SUPPORT_Z_MIN_MM = 11.5
RAIL_SUPPORT_Z_MAX_MM = 12.85
RAIL_OVERHANG_INNER_X_MM = 13.45
RAIL_OVERHANG_Z_MIN_MM = 12.55
RAIL_OVERHANG_Z_MAX_MM = 12.85
LID_SUPPORT_CLEARANCE_INNER_X_MM = 13.85
LID_OVERHANG_RELIEF_INNER_X_MM = 13.40
LID_OVERHANG_RELIEF_Z_MIN_MM = 12.50
LID_RELIEF_Y_MIN_MM = 63.70
LID_RELIEF_Y_MAX_MM = 89.70
RAIL_RUNNING_CLEARANCE_Z_MM = RAIL_OVERHANG_Z_MIN_MM - LID_OVERHANG_RELIEF_Z_MIN_MM

# Continuous shallow groove in the lid underside. It lies completely inside the 1 mm
# reservoir wall footprint and outside the fluid cavity. It reserves a seal interface
# only; no gasket/O-ring section, material or compression ratio is selected.
SEAL_GROOVE_OUTER_X_MM = 27.6
SEAL_GROOVE_OUTER_Y_MM = 26.6
SEAL_GROOVE_WIDTH_MM = 0.5
SEAL_GROOVE_DEPTH_MM = 0.2
SEAL_LAND_REFERENCE_DEPTH_MM = 0.05

# A removable cross-key prevents the lid from translating out of the capture rails.
# Its larger distal detent and service head are geometric anti-ejection features. Their
# insertion/removal compliance and forces remain unvalidated.
KEY_STEM_DIAMETER_MM = 0.50
KEY_BORE_DIAMETER_MM = 0.70
KEY_DETENT_DIAMETER_MM = 1.00
KEY_HEAD_DIAMETER_MM = 2.00
KEY_STEM_X_MIN_MM = -15.50
KEY_STEM_X_MAX_MM = 15.50
KEY_HEAD_LENGTH_MM = 1.40
KEY_Y_MM = 65.0
KEY_Z_MM = 12.55

# Closure service occurs only after the complete removable reservoir has followed the
# already-controlled posterior module withdrawal. The lid then slides inferiorly until
# it is fully clear of the fixed guide rails before being lifted away.
LID_SLIDE_RELEASE_TRAVEL_MM = 26.0
LID_LIFT_SERVICE_TRAVEL_MM = 3.0
KEY_WITHDRAWAL_TRAVEL_MM = 34.0
SERVICE_SEQUENCE_IDS = (
    "WATER-CLOSURE-SERVICE-01-MODULE-WITHDRAW",
    "WATER-CLOSURE-SERVICE-02-KEY-RELEASE",
    "WATER-CLOSURE-SERVICE-03-LID-SLIDE",
    "WATER-CLOSURE-SERVICE-04-LID-LIFT",
)


def _canonical_sha256(value: object, *, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise WaterReservoirError(f"{label} must be canonical lowercase SHA-256")
    return value


def _box_from_bounds(
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    zmin: float,
    zmax: float,
) -> cq.Workplane:
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise WaterReservoirError("Closure box bounds must be strictly ordered")
    return (
        cq.Workplane("XY")
        .box(xmax - xmin, ymax - ymin, zmax - zmin, centered=(True, True, True))
        .translate(((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0))
    )


def _cylinder(radius_mm: float, length_mm: float, start: Point3, direction: Vector3) -> cq.Workplane:
    if radius_mm <= 0.0 or length_mm <= 0.0:
        raise WaterReservoirError("Closure cylinder requires positive radius and length")
    axis = direction.normalized()
    solid = cq.Solid.makeCylinder(
        radius_mm,
        length_mm,
        cq.Vector(*start.as_tuple()),
        cq.Vector(*axis.as_tuple()),
    )
    return cq.Workplane(obj=solid)


def _rectangular_ring(
    outer_x_mm: float,
    outer_y_mm: float,
    width_mm: float,
    depth_mm: float,
    z_min_mm: float,
) -> cq.Workplane:
    if width_mm <= 0.0 or 2.0 * width_mm >= min(outer_x_mm, outer_y_mm):
        raise WaterReservoirError("Seal ring width must fit inside its outer dimensions")
    outer = (
        cq.Workplane("XY")
        .workplane(offset=z_min_mm)
        .rect(outer_x_mm, outer_y_mm)
        .extrude(depth_mm)
    )
    inner = (
        cq.Workplane("XY")
        .workplane(offset=z_min_mm - 0.1)
        .rect(outer_x_mm - 2.0 * width_mm, outer_y_mm - 2.0 * width_mm)
        .extrude(depth_mm + 0.2)
    )
    return outer.cut(inner).translate((0.0, 76.0, 0.0))


def _side_rail(sign: float) -> cq.Workplane:
    if sign not in (-1.0, 1.0):
        raise WaterReservoirError("Rail side sign must be -1 or +1")
    if sign > 0.0:
        support_xmin, support_xmax = RAIL_SUPPORT_INNER_X_MM, RAIL_SUPPORT_OUTER_X_MM
        overhang_xmin, overhang_xmax = RAIL_OVERHANG_INNER_X_MM, RAIL_SUPPORT_OUTER_X_MM
    else:
        support_xmin, support_xmax = -RAIL_SUPPORT_OUTER_X_MM, -RAIL_SUPPORT_INNER_X_MM
        overhang_xmin, overhang_xmax = -RAIL_SUPPORT_OUTER_X_MM, -RAIL_OVERHANG_INNER_X_MM
    support = _box_from_bounds(
        support_xmin,
        support_xmax,
        RAIL_Y_MIN_MM,
        RAIL_Y_MAX_MM,
        RAIL_SUPPORT_Z_MIN_MM,
        RAIL_SUPPORT_Z_MAX_MM,
    )
    overhang = _box_from_bounds(
        overhang_xmin,
        overhang_xmax,
        RAIL_Y_MIN_MM,
        RAIL_Y_MAX_MM,
        RAIL_OVERHANG_Z_MIN_MM,
        RAIL_OVERHANG_Z_MAX_MM,
    )
    return support.union(overhang)


def _lid_side_relief(sign: float) -> tuple[cq.Workplane, cq.Workplane]:
    if sign > 0.0:
        support_xmin, support_xmax = LID_SUPPORT_CLEARANCE_INNER_X_MM, 14.2
        overhang_xmin, overhang_xmax = LID_OVERHANG_RELIEF_INNER_X_MM, 14.2
    else:
        support_xmin, support_xmax = -14.2, -LID_SUPPORT_CLEARANCE_INNER_X_MM
        overhang_xmin, overhang_xmax = -14.2, -LID_OVERHANG_RELIEF_INNER_X_MM
    support_clearance = _box_from_bounds(
        support_xmin,
        support_xmax,
        LID_RELIEF_Y_MIN_MM,
        LID_RELIEF_Y_MAX_MM,
        11.9,
        13.1,
    )
    overhang_relief = _box_from_bounds(
        overhang_xmin,
        overhang_xmax,
        LID_RELIEF_Y_MIN_MM,
        LID_RELIEF_Y_MAX_MM,
        LID_OVERHANG_RELIEF_Z_MIN_MM,
        13.1,
    )
    return support_clearance, overhang_relief


def _key_bore() -> cq.Workplane:
    return _cylinder(
        KEY_BORE_DIAMETER_MM / 2.0,
        (RAIL_SUPPORT_OUTER_X_MM - KEY_STEM_X_MIN_MM) + 0.5,
        Point3(KEY_STEM_X_MIN_MM - 0.25, KEY_Y_MM, KEY_Z_MM),
        Vector3(1.0, 0.0, 0.0),
    )


def _retention_key() -> cq.Workplane:
    stem = _cylinder(
        KEY_STEM_DIAMETER_MM / 2.0,
        KEY_STEM_X_MAX_MM - KEY_STEM_X_MIN_MM,
        Point3(KEY_STEM_X_MIN_MM, KEY_Y_MM, KEY_Z_MM),
        Vector3(1.0, 0.0, 0.0),
    )
    detent = cq.Workplane(obj=cq.Solid.makeSphere(
        KEY_DETENT_DIAMETER_MM / 2.0,
        cq.Vector(KEY_STEM_X_MIN_MM, KEY_Y_MM, KEY_Z_MM),
    ))
    head = _cylinder(
        KEY_HEAD_DIAMETER_MM / 2.0,
        KEY_HEAD_LENGTH_MM,
        Point3(KEY_STEM_X_MAX_MM - 0.2, KEY_Y_MM, KEY_Z_MM),
        Vector3(1.0, 0.0, 0.0),
    )
    return stem.union(detent).union(head)


def _translate(shape: cq.Workplane, vector: Vector3) -> cq.Workplane:
    return cq.Workplane(obj=shape.val().moved(cq.Location(cq.Vector(*vector.as_tuple()))))


@dataclass(frozen=True, slots=True)
class ClosureServiceStep:
    step_id: str
    moving_part: str
    translation_world_mm: Vector3
    precondition: str
    evidence_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        if self.step_id not in SERVICE_SEQUENCE_IDS:
            raise WaterReservoirError(f"Unknown water-closure service step {self.step_id!r}")
        if type(self.moving_part) is not str or not self.moving_part:
            raise WaterReservoirError("Closure service moving part must be exact nonblank text")
        if self.translation_world_mm.norm() <= 0.0:
            raise WaterReservoirError("Closure service step must carry nonzero digital translation")
        if self.evidence_status != SERVICE_STATUS:
            raise WaterReservoirError("Closure service sequence cannot promote physical usability evidence")

    def manifest(self) -> dict[str, object]:
        return {
            "step_id": self.step_id,
            "moving_part": self.moving_part,
            "translation_world_mm": list(self.translation_world_mm.as_tuple()),
            "precondition": self.precondition,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class WaterReservoirClosureGeometry:
    source_authority_revision: str
    source_interface_manifest_sha256: str
    closure_body_solid: cq.Workplane
    closure_lid_solid: cq.Workplane
    retention_key_solid: cq.Workplane
    key_bore_solid: cq.Workplane
    seal_groove_reservation_solid: cq.Workplane
    seal_land_reference_solid: cq.Workplane
    bilateral_capture_rails_solid: cq.Workplane
    module_service_sweep_solid: cq.Workplane
    lid_service_sweep_solid: cq.Workplane
    key_service_sweep_solid: cq.Workplane
    service_sequence: tuple[ClosureServiceStep, ...]
    fluid_identity: str = FLUID_IDENTITY
    closure_status: str = CLOSURE_STATUS
    seal_status: str = SEAL_STATUS
    key_status: str = KEY_STATUS
    service_status: str = SERVICE_STATUS
    physical_validation_eligible: bool = False
    evidence_status: str = PHYSICAL_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _canonical_sha256(self.source_interface_manifest_sha256, label="water-service interface source manifest")
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise WaterReservoirError("Closure geometry requires exact authority revision")
        if self.fluid_identity != "FRESH_WATER":
            raise WaterReservoirError("Closure cannot change FRESH_WATER module identity")
        if self.closure_status != CLOSURE_STATUS or self.seal_status != SEAL_STATUS or self.key_status != KEY_STATUS:
            raise WaterReservoirError("Closure/seal/key provenance must remain explicitly provisional")
        if self.service_status != SERVICE_STATUS:
            raise WaterReservoirError("Closure service evidence status must remain exact")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WaterReservoirError("Closure geometry cannot become physical validation evidence")
        if self.evidence_status != PHYSICAL_EVIDENCE_STATUS:
            raise WaterReservoirError("Closure evidence firewall must remain exact")
        if tuple(step.step_id for step in self.service_sequence) != SERVICE_SEQUENCE_IDS:
            raise WaterReservoirError("Closure service sequence order is not controlled")
        if not (KEY_STEM_DIAMETER_MM < KEY_BORE_DIAMETER_MM < KEY_DETENT_DIAMETER_MM):
            raise WaterReservoirError("Closure key must have running stem clearance and positive distal detent")
        if KEY_HEAD_DIAMETER_MM <= KEY_BORE_DIAMETER_MM:
            raise WaterReservoirError("Closure key head must be larger than the service bore")
        if RAIL_RUNNING_CLEARANCE_Z_MM <= 0.0:
            raise WaterReservoirError("Closure rail must retain positive digital running clearance")

        for label, shape in (
            ("closure body", self.closure_body_solid),
            ("closure lid", self.closure_lid_solid),
            ("retention key", self.retention_key_solid),
            ("key bore", self.key_bore_solid),
            ("seal groove", self.seal_groove_reservation_solid),
            ("seal land", self.seal_land_reference_solid),
            ("capture rails", self.bilateral_capture_rails_solid),
            ("module service sweep", self.module_service_sweep_solid),
            ("lid service sweep", self.lid_service_sweep_solid),
            ("key service sweep", self.key_service_sweep_solid),
        ):
            if not shape.val().isValid() or shape.solids().size() != 1:
                raise WaterReservoirError(f"Water reservoir {label} must be one valid deterministic solid")

    def validate_current_sources(self, authority: Authority) -> tuple[RealizedWaterReservoir, WaterReservoirInterfaceGeometry]:
        realized = build_realized_water_reservoir(authority)
        interfaces = build_water_reservoir_interface_geometry(authority, realized)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise WaterReservoirError("Water closure geometry is stale for current authority")
        if self.source_interface_manifest_sha256 != interfaces.manifest_sha256:
            raise WaterReservoirError("Water closure geometry is stale for current water-service interfaces")
        return realized, interfaces

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "MASCK_ONE_CELL4_WATER_RESERVOIR_CLOSURE_V1",
            "source_authority_revision": self.source_authority_revision,
            "source_interface_manifest_sha256": self.source_interface_manifest_sha256,
            "world_frame_id": WORLD_FRAME_ID,
            "fluid_identity": self.fluid_identity,
            "capture_rails": {
                "support_x_abs_mm": [RAIL_SUPPORT_INNER_X_MM, RAIL_SUPPORT_OUTER_X_MM],
                "y_mm": [RAIL_Y_MIN_MM, RAIL_Y_MAX_MM],
                "support_z_mm": [RAIL_SUPPORT_Z_MIN_MM, RAIL_SUPPORT_Z_MAX_MM],
                "overhang_inner_x_abs_mm": RAIL_OVERHANG_INNER_X_MM,
                "overhang_z_mm": [RAIL_OVERHANG_Z_MIN_MM, RAIL_OVERHANG_Z_MAX_MM],
                "running_clearance_z_mm": RAIL_RUNNING_CLEARANCE_Z_MM,
                "role": "BILATERAL_POSITIVE_Z_CAPTURE_WITH_INFERIOR_SLIDE_SERVICE",
            },
            "retention_key": {
                "axis": "+X",
                "center_yz_mm": [KEY_Y_MM, KEY_Z_MM],
                "stem_diameter_mm": KEY_STEM_DIAMETER_MM,
                "bore_diameter_mm": KEY_BORE_DIAMETER_MM,
                "distal_detent_diameter_mm": KEY_DETENT_DIAMETER_MM,
                "service_head_diameter_mm": KEY_HEAD_DIAMETER_MM,
                "status": self.key_status,
            },
            "seal_interface": {
                "groove_outer_xy_mm": [SEAL_GROOVE_OUTER_X_MM, SEAL_GROOVE_OUTER_Y_MM],
                "groove_width_mm": SEAL_GROOVE_WIDTH_MM,
                "groove_depth_mm": SEAL_GROOVE_DEPTH_MM,
                "land_reference_depth_mm": SEAL_LAND_REFERENCE_DEPTH_MM,
                "status": self.seal_status,
            },
            "service_sequence": [step.manifest() for step in self.service_sequence],
            "module_withdrawal_travel_mm": SERVICE_WITHDRAWAL_TRAVEL_MM,
            "key_withdrawal_travel_mm": KEY_WITHDRAWAL_TRAVEL_MM,
            "lid_slide_release_travel_mm": LID_SLIDE_RELEASE_TRAVEL_MM,
            "lid_lift_service_travel_mm": LID_LIFT_SERVICE_TRAVEL_MM,
            "package_clearance_reservation_mm": PACKAGE_CLEARANCE_RESERVATION_MM,
            "closure_status": self.closure_status,
            "service_status": self.service_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }

    @property
    def manifest_sha256(self) -> str:
        return sha256(
            json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()


def _service_sequence() -> tuple[ClosureServiceStep, ...]:
    return (
        ClosureServiceStep(
            SERVICE_SEQUENCE_IDS[0],
            "complete removable fresh-water module",
            Vector3(0.0, 0.0, -SERVICE_WITHDRAWAL_TRAVEL_MM),
            "module released from its frame-side mounting references",
        ),
        ClosureServiceStep(
            SERVICE_SEQUENCE_IDS[1],
            "retention key",
            Vector3(KEY_WITHDRAWAL_TRAVEL_MM, 0.0, 0.0),
            "module already withdrawn; compliant distal detent intentionally released",
        ),
        ClosureServiceStep(
            SERVICE_SEQUENCE_IDS[2],
            "ported closure lid",
            Vector3(0.0, -LID_SLIDE_RELEASE_TRAVEL_MM, 0.0),
            "retention key removed; lid stays guided beneath bilateral capture rails",
        ),
        ClosureServiceStep(
            SERVICE_SEQUENCE_IDS[3],
            "ported closure lid",
            Vector3(0.0, 0.0, LID_LIFT_SERVICE_TRAVEL_MM),
            "lid has fully cleared the fixed capture-rail Y span",
        ),
    )


def build_water_reservoir_closure_geometry(
    authority: Authority,
    realized: RealizedWaterReservoir | None = None,
    interfaces: WaterReservoirInterfaceGeometry | None = None,
) -> WaterReservoirClosureGeometry:
    realized = realized or build_realized_water_reservoir(authority)
    interfaces = interfaces or build_water_reservoir_interface_geometry(authority, realized)
    interfaces.validate_current_sources(authority)

    left_rail = _side_rail(-1.0)
    right_rail = _side_rail(1.0)
    rails = left_rail.union(right_rail)
    body = interfaces.body_with_pickup_port_solid.union(left_rail).union(right_rail)

    groove = _rectangular_ring(
        SEAL_GROOVE_OUTER_X_MM,
        SEAL_GROOVE_OUTER_Y_MM,
        SEAL_GROOVE_WIDTH_MM,
        SEAL_GROOVE_DEPTH_MM,
        12.0,
    )
    seal_land = _rectangular_ring(
        SEAL_GROOVE_OUTER_X_MM,
        SEAL_GROOVE_OUTER_Y_MM,
        SEAL_GROOVE_WIDTH_MM,
        SEAL_LAND_REFERENCE_DEPTH_MM,
        12.0 - SEAL_LAND_REFERENCE_DEPTH_MM,
    )
    lid = interfaces.lid_with_fill_vent_ports_solid.cut(groove)
    for sign in (-1.0, 1.0):
        support_clearance, overhang_relief = _lid_side_relief(sign)
        lid = lid.cut(support_clearance).cut(overhang_relief)

    key_bore = _key_bore()
    body = body.cut(key_bore)
    lid = lid.cut(key_bore)
    key = _retention_key()

    # Conservative continuous service reservations. These are not assembly material.
    closure_x_half = KEY_STEM_X_MAX_MM + KEY_HEAD_LENGTH_MM + KEY_HEAD_DIAMETER_MM / 2.0
    module_sweep = _box_from_bounds(
        -closure_x_half,
        closure_x_half,
        62.5,
        89.5,
        1.0 - SERVICE_WITHDRAWAL_TRAVEL_MM,
        13.0,
    )
    lid_sweep = _box_from_bounds(
        -14.0,
        14.0,
        62.5 - LID_SLIDE_RELEASE_TRAVEL_MM,
        89.5,
        12.0 - SERVICE_WITHDRAWAL_TRAVEL_MM,
        13.0 - SERVICE_WITHDRAWAL_TRAVEL_MM + LID_LIFT_SERVICE_TRAVEL_MM,
    )
    key_sweep = _box_from_bounds(
        KEY_STEM_X_MIN_MM,
        KEY_STEM_X_MAX_MM + KEY_HEAD_LENGTH_MM + KEY_WITHDRAWAL_TRAVEL_MM,
        KEY_Y_MM - KEY_HEAD_DIAMETER_MM / 2.0,
        KEY_Y_MM + KEY_HEAD_DIAMETER_MM / 2.0,
        KEY_Z_MM - SERVICE_WITHDRAWAL_TRAVEL_MM - KEY_HEAD_DIAMETER_MM / 2.0,
        KEY_Z_MM - SERVICE_WITHDRAWAL_TRAVEL_MM + KEY_HEAD_DIAMETER_MM / 2.0,
    )

    result = WaterReservoirClosureGeometry(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_interface_manifest_sha256=interfaces.manifest_sha256,
        closure_body_solid=body,
        closure_lid_solid=lid,
        retention_key_solid=key,
        key_bore_solid=key_bore,
        seal_groove_reservation_solid=groove,
        seal_land_reference_solid=seal_land,
        bilateral_capture_rails_solid=rails,
        module_service_sweep_solid=module_sweep,
        lid_service_sweep_solid=lid_sweep,
        key_service_sweep_solid=key_sweep,
        service_sequence=_service_sequence(),
    )
    result.validate_current_sources(authority)
    return result
