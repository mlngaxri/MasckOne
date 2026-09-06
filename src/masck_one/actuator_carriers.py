from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import tempfile

import cadquery as cq

from .actuator_frames import ZONE_IDS
from .model import MasckOneModel, build_model


SCHEMA = "MASCK_ONE_CELL7_ACTUATOR_CARRIER_TEMPLATE_V1"
SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LOCAL_FRAME_ID = "MASCK_ONE_ACTUATOR_PACKAGE_LOCAL_MM"

SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuator_coupling.py", "d56160304190c030e3bc389803eaa456aaab5af0"),
)

PACKAGE_REFERENCE_DIAMETER_MM = 10.2
PACKAGE_REFERENCE_LENGTH_MM = 18.7
PACKAGE_RADIUS_MM = PACKAGE_REFERENCE_DIAMETER_MM / 2.0

CARRIER_RADIAL_CLEARANCE_SEED_MM = 0.30
CARRIER_INNER_RADIUS_MM = PACKAGE_RADIUS_MM + CARRIER_RADIAL_CLEARANCE_SEED_MM
CARRIER_OUTER_RADIUS_MM = 6.65
CARRIER_AXIAL_CLEARANCE_SEED_MM = 0.25
CARRIER_END_LIP_THICKNESS_MM = 0.80
CARRIER_END_LIP_RADIAL_OVERHANG_MM = 0.45
CARRIER_END_LIP_INNER_RADIUS_MM = PACKAGE_RADIUS_MM - CARRIER_END_LIP_RADIAL_OVERHANG_MM

CLOSURE_PIN_X_MM = 7.0
CLOSURE_PIN_Z_MM = PACKAGE_REFERENCE_LENGTH_MM / 2.0
CLOSURE_LUG_RADIUS_MM = 1.35
CLOSURE_LUG_HALF_SPAN_Y_MM = 1.80
CLOSURE_HOLE_RADIUS_MM = 0.65
CLOSURE_PIN_RADIUS_MM = 0.50
CLOSURE_PIN_GROOVE_RADIUS_MM = 0.35
CLOSURE_PIN_HEAD_RADIUS_MM = 0.95
CLOSURE_CLIP_INNER_RADIUS_MM = 0.38
CLOSURE_CLIP_OUTER_RADIUS_MM = 0.95

LOCAL_CAPTURE_PROBE_AXIAL_MM = 0.30
LOCAL_CAPTURE_PROBE_RADIAL_MM = 0.35
CLIP_SHOULDER_PROBE_MM = 0.15

EVIDENCE_STATUS = (
    "DIGITAL_LOCAL_CARRIER_BREP_AND_WORLD_COLLISION_REVIEW_ONLY_NOT_FINAL_MOUNT_FRAME_JOIN_"
    "FORCE_STIFFNESS_FATIGUE_ACOUSTIC_SUPPLIER_PROCESS_OR_PHYSICAL_VALIDATION"
)


class ActuatorCarrierError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceReferencePlacement:
    zone_id: str
    component_name: str
    base_xyz_mm: tuple[float, float, float]
    pitch_sign: float

    def __post_init__(self) -> None:
        if self.zone_id not in ZONE_IDS:
            raise ActuatorCarrierError("carrier source placement uses an unknown actuator zone")
        if type(self.component_name) is not str or not self.component_name:
            raise ActuatorCarrierError("carrier source component identity must be nonblank")
        if len(self.base_xyz_mm) != 3 or any(
            type(v) not in (int, float) or isinstance(v, bool) or not math.isfinite(float(v))
            for v in self.base_xyz_mm
        ):
            raise ActuatorCarrierError("carrier source base coordinates must be finite real numerics")
        if self.pitch_sign not in (-1.0, 1.0):
            raise ActuatorCarrierError("carrier source pitch sign must be exactly +/-1")

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "component_name": self.component_name,
            "base_xyz_mm": list(self.base_xyz_mm),
            "pitch_sign": self.pitch_sign,
            "frame_id": WORLD_FRAME_ID,
            "status": "CURRENT_MODEL_PACKAGE_REFERENCE_TRANSFORM_ONLY_NOT_STRUCTURAL_MOUNT_DATUM",
        }


SOURCE_REFERENCE_PLACEMENTS: tuple[SourceReferencePlacement, ...] = (
    SourceReferencePlacement(ZONE_IDS[0], "actuator_envelope_1", (-48.0, 52.0, 2.0), 1.0),
    SourceReferencePlacement(ZONE_IDS[1], "actuator_envelope_2", (48.0, 52.0, 2.0), -1.0),
    SourceReferencePlacement(ZONE_IDS[2], "actuator_envelope_3", (-50.0, -38.0, 2.0), 1.0),
    SourceReferencePlacement(ZONE_IDS[3], "actuator_envelope_4", (50.0, -38.0, 2.0), -1.0),
)


@dataclass(frozen=True, slots=True)
class CarrierPart:
    part_id: str
    role: str
    solid: cq.Workplane
    material_semantics: str

    def __post_init__(self) -> None:
        if type(self.part_id) is not str or not self.part_id:
            raise ActuatorCarrierError("carrier part identity must be nonblank")
        if type(self.role) is not str or not self.role:
            raise ActuatorCarrierError("carrier part role must be nonblank")
        if type(self.material_semantics) is not str or not self.material_semantics:
            raise ActuatorCarrierError("carrier material semantics must be explicit")
        solids = self.solid.solids().vals()
        if len(solids) != 1 or not solids[0].isValid() or float(solids[0].Volume()) <= 0.0:
            raise ActuatorCarrierError(f"{self.part_id} must be one valid positive B-rep solid")

    @property
    def brep_sha256(self) -> str:
        return _brep_sha256(self.solid)

    def manifest(self) -> dict[str, object]:
        box = self.solid.val().BoundingBox()
        return {
            "part_id": self.part_id,
            "role": self.role,
            "material_semantics": self.material_semantics,
            "local_frame_id": LOCAL_FRAME_ID,
            "bounds_min_xyz_mm": [float(box.xmin), float(box.ymin), float(box.zmin)],
            "bounds_max_xyz_mm": [float(box.xmax), float(box.ymax), float(box.zmax)],
            "volume_mm3": float(self.solid.val().Volume()),
            "brep_sha256": self.brep_sha256,
        }


@dataclass(frozen=True, slots=True)
class ZoneWorldScreen:
    zone_id: str
    source_component_name: str
    source_component_brep_sha256: str
    source_package_protected_intersection_mm3: float
    carrier_review_protected_intersection_mm3: float
    baseline_world_transform_status: str
    world_mount_eligible: bool
    angle_doe_clearance_status: str
    frame_attachment_status: str

    def __post_init__(self) -> None:
        if self.zone_id not in ZONE_IDS:
            raise ActuatorCarrierError("unknown world-screen zone")
        for value in (
            self.source_package_protected_intersection_mm3,
            self.carrier_review_protected_intersection_mm3,
        ):
            if type(value) not in (int, float) or not math.isfinite(float(value)) or float(value) < 0.0:
                raise ActuatorCarrierError("protected-intersection measurements must be finite and nonnegative")
        if self.source_package_protected_intersection_mm3 <= 0.0:
            raise ActuatorCarrierError(
                "current source package must remain explicitly blocked by its protected hard-envelope conflict"
            )
        if self.carrier_review_protected_intersection_mm3 <= 0.0:
            raise ActuatorCarrierError(
                "world-positioned carrier review geometry must not hide the inherited protected-envelope blocker"
            )
        if type(self.world_mount_eligible) is not bool or self.world_mount_eligible:
            raise ActuatorCarrierError("carrier cannot become a world mount while the protected conflict remains")
        if not all(
            type(value) is str and value
            for value in (
                self.source_component_name,
                self.source_component_brep_sha256,
                self.baseline_world_transform_status,
                self.angle_doe_clearance_status,
                self.frame_attachment_status,
            )
        ):
            raise ActuatorCarrierError("world-screen status metadata must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "source_component_name": self.source_component_name,
            "source_component_brep_sha256": self.source_component_brep_sha256,
            "source_package_protected_intersection_mm3": self.source_package_protected_intersection_mm3,
            "carrier_review_protected_intersection_mm3": self.carrier_review_protected_intersection_mm3,
            "baseline_world_transform_status": self.baseline_world_transform_status,
            "world_mount_eligible": self.world_mount_eligible,
            "angle_doe_clearance_status": self.angle_doe_clearance_status,
            "frame_attachment_status": self.frame_attachment_status,
        }


@dataclass(frozen=True, slots=True)
class ActuatorCarrierPackage:
    source_main_sha: str
    authority_revision: str
    source_model_blob_sha: str
    local_frame_id: str
    target_world_frame_id: str
    parts: tuple[CarrierPart, ...]
    source_reference_placements: tuple[SourceReferencePlacement, ...]
    zone_world_screens: tuple[ZoneWorldScreen, ...]
    package_reference_diameter_mm: float
    package_reference_length_mm: float
    package_radial_clearance_seed_mm: float
    package_axial_clearance_seed_mm: float
    positive_radial_capture_realized: bool
    positive_axial_stops_realized: bool
    split_closure_positive_retention_realized: bool
    structural_frame_attachment_realized: bool
    production_tolerance_stack_resolved: bool
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise ActuatorCarrierError("carrier package is stale for its authored released-main source")
        if self.authority_revision != AUTHORITY_REVISION:
            raise ActuatorCarrierError("carrier package authority revision moved")
        if self.source_model_blob_sha != dict(SOURCE_GIT_BLOB_IDENTITIES)["src/masck_one/model.py"]:
            raise ActuatorCarrierError("carrier package model source moved")
        if self.local_frame_id != LOCAL_FRAME_ID or self.target_world_frame_id != WORLD_FRAME_ID:
            raise ActuatorCarrierError("carrier frame semantics changed")
        expected_part_ids = (
            "ACTUATOR-CARRIER-TEMPLATE-UPPER-HALF",
            "ACTUATOR-CARRIER-TEMPLATE-LOWER-HALF",
            "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-A",
            "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-B",
            "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-A",
            "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-B",
        )
        if tuple(part.part_id for part in self.parts) != expected_part_ids:
            raise ActuatorCarrierError("carrier template part identity/order changed")
        if self.source_reference_placements != SOURCE_REFERENCE_PLACEMENTS:
            raise ActuatorCarrierError("source reference placement set changed")
        if tuple(screen.zone_id for screen in self.zone_world_screens) != ZONE_IDS:
            raise ActuatorCarrierError("carrier world screens must preserve four-zone order")
        if not all(
            type(value) is bool
            for value in (
                self.positive_radial_capture_realized,
                self.positive_axial_stops_realized,
                self.split_closure_positive_retention_realized,
                self.structural_frame_attachment_realized,
                self.production_tolerance_stack_resolved,
                self.physical_validation_eligible,
            )
        ):
            raise ActuatorCarrierError("carrier readiness fields must be exact bools")
        if not (
            self.positive_radial_capture_realized
            and self.positive_axial_stops_realized
            and self.split_closure_positive_retention_realized
        ):
            raise ActuatorCarrierError("local carrier B-rep must retain positive package capture and closure")
        if self.structural_frame_attachment_realized:
            raise ActuatorCarrierError("topology-only released frame cannot be promoted to a carrier attachment")
        if self.production_tolerance_stack_resolved:
            raise ActuatorCarrierError("carrier nominal clearance seeds are not a production tolerance stack")
        if self.physical_validation_eligible:
            raise ActuatorCarrierError("digital carrier geometry cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise ActuatorCarrierError("carrier evidence firewall changed")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(raw.encode("utf-8")).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "source_git_blobs": [{"path": path, "sha": digest} for path, digest in SOURCE_GIT_BLOB_IDENTITIES],
            "source_model_blob_sha": self.source_model_blob_sha,
            "local_frame_id": self.local_frame_id,
            "target_world_frame_id": self.target_world_frame_id,
            "parts": [part.manifest() for part in self.parts],
            "source_reference_placements": [item.manifest() for item in self.source_reference_placements],
            "zone_world_screens": [screen.manifest() for screen in self.zone_world_screens],
            "package_reference_diameter_mm": self.package_reference_diameter_mm,
            "package_reference_length_mm": self.package_reference_length_mm,
            "nominal_geometry_seeds_mm": {
                "package_radial_clearance": self.package_radial_clearance_seed_mm,
                "package_axial_clearance_each_end": self.package_axial_clearance_seed_mm,
                "carrier_outer_radius": CARRIER_OUTER_RADIUS_MM,
                "end_lip_radial_overhang": CARRIER_END_LIP_RADIAL_OVERHANG_MM,
                "closure_pin_hole_radial_clearance": CLOSURE_HOLE_RADIUS_MM - CLOSURE_PIN_RADIUS_MM,
            },
            "positive_radial_capture_realized": self.positive_radial_capture_realized,
            "positive_axial_stops_realized": self.positive_axial_stops_realized,
            "split_closure_positive_retention_realized": self.split_closure_positive_retention_realized,
            "structural_frame_attachment_realized": self.structural_frame_attachment_realized,
            "structural_frame_attachment_status": (
                "BLOCKED_RELEASED_STRUCTURAL_FRAME_IS_TOPOLOGY_ONLY_NO_3D_MEMBER_OR_MOUNT_DATUM"
            ),
            "production_tolerance_stack_resolved": self.production_tolerance_stack_resolved,
            "production_tolerance_status": (
                "UNRESOLVED_NOMINAL_CLEARANCE_SEEDS_ONLY_MATERIAL_PROCESS_AND_TOLERANCE_ALLOCATION_PENDING"
            ),
            "world_material_promotion_status": (
                "BLOCKED_CURRENT_MODEL_REFERENCE_PLACEMENTS_INTERSECT_AUTHORITY_2P5D_PROTECTED_HARD_ENVELOPES"
            ),
            "angle_doe_status": (
                "BLOCKED_NO_CLEARANCE_PASS_CLAIM_WHILE_BASELINE_REFERENCE_TRANSFORMS_FAIL_PROTECTED_HARD_ENVELOPES"
            ),
            "supplier_status": "PRODUCTION_ACTUATOR_NOT_FROZEN_CURRENT_H2W_REFERENCE_IS_PACKAGE_EVIDENCE_ONLY",
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_blobs() -> None:
    root = Path(__file__).resolve().parents[2]
    for relative_path, expected in SOURCE_GIT_BLOB_IDENTITIES:
        source = root / relative_path
        if not source.is_file():
            raise ActuatorCarrierError(f"required source file is missing: {relative_path}")
        actual = _git_blob_sha(source)
        if actual != expected:
            raise ActuatorCarrierError(
                f"actuator carrier source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _brep_sha256(workplane: cq.Workplane) -> str:
    with tempfile.NamedTemporaryFile(suffix=".brep", delete=False) as handle:
        path = Path(handle.name)
    try:
        workplane.val().exportBrep(str(path))
        return sha256(path.read_bytes()).hexdigest()
    finally:
        path.unlink(missing_ok=True)


def _annulus(outer_radius_mm: float, inner_radius_mm: float, z0_mm: float, height_mm: float) -> cq.Workplane:
    outer = cq.Workplane("XY").workplane(offset=z0_mm).circle(outer_radius_mm).extrude(height_mm)
    inner = (
        cq.Workplane("XY")
        .workplane(offset=z0_mm - 0.1)
        .circle(inner_radius_mm)
        .extrude(height_mm + 0.2)
    )
    return outer.cut(inner)


def _axis_y_cylinder(radius_mm: float, x_mm: float, z_mm: float, y0_mm: float, y1_mm: float) -> cq.Workplane:
    solid = cq.Solid.makeCylinder(
        radius_mm,
        y1_mm - y0_mm,
        cq.Vector(x_mm, y0_mm, z_mm),
        cq.Vector(0.0, 1.0, 0.0),
    )
    return cq.Workplane("XY").newObject([solid])


def _capture_pin(x_mm: float) -> cq.Workplane:
    shaft = _axis_y_cylinder(CLOSURE_PIN_RADIUS_MM, x_mm, CLOSURE_PIN_Z_MM, -3.5, 3.0)
    groove_cut = _axis_y_cylinder(0.55, x_mm, CLOSURE_PIN_Z_MM, -3.0, -2.5)
    groove = _axis_y_cylinder(CLOSURE_PIN_GROOVE_RADIUS_MM, x_mm, CLOSURE_PIN_Z_MM, -3.05, -2.45)
    head = _axis_y_cylinder(CLOSURE_PIN_HEAD_RADIUS_MM, x_mm, CLOSURE_PIN_Z_MM, 3.0, 3.7)
    return shaft.cut(groove_cut).union(groove).union(head)


def _retainer_clip(x_mm: float) -> cq.Workplane:
    outer = _axis_y_cylinder(CLOSURE_CLIP_OUTER_RADIUS_MM, x_mm, CLOSURE_PIN_Z_MM, -2.95, -2.55)
    inner = _axis_y_cylinder(CLOSURE_CLIP_INNER_RADIUS_MM, x_mm, CLOSURE_PIN_Z_MM, -3.0, -2.5)
    ring = outer.cut(inner)
    sign = 1.0 if x_mm > 0.0 else -1.0
    inward_gap = (
        cq.Workplane("XY")
        .box(1.4, 1.0, 1.1, centered=(True, True, True))
        .translate((x_mm - sign * 0.78, -2.75, CLOSURE_PIN_Z_MM))
    )
    return ring.cut(inward_gap)


def _build_local_parts() -> tuple[CarrierPart, ...]:
    body = _annulus(
        CARRIER_OUTER_RADIUS_MM,
        CARRIER_INNER_RADIUS_MM,
        -CARRIER_AXIAL_CLEARANCE_SEED_MM,
        PACKAGE_REFERENCE_LENGTH_MM + 2.0 * CARRIER_AXIAL_CLEARANCE_SEED_MM,
    )
    body = body.union(
        _annulus(
            CARRIER_OUTER_RADIUS_MM,
            CARRIER_END_LIP_INNER_RADIUS_MM,
            -CARRIER_AXIAL_CLEARANCE_SEED_MM - CARRIER_END_LIP_THICKNESS_MM,
            CARRIER_END_LIP_THICKNESS_MM,
        )
    )
    body = body.union(
        _annulus(
            CARRIER_OUTER_RADIUS_MM,
            CARRIER_END_LIP_INNER_RADIUS_MM,
            PACKAGE_REFERENCE_LENGTH_MM + CARRIER_AXIAL_CLEARANCE_SEED_MM,
            CARRIER_END_LIP_THICKNESS_MM,
        )
    )

    upper_box = (
        cq.Workplane("XY")
        .box(40.0, 20.0, 40.0, centered=(True, False, True))
        .translate((0.0, 0.0, PACKAGE_REFERENCE_LENGTH_MM / 2.0))
    )
    lower_box = (
        cq.Workplane("XY")
        .box(40.0, 20.0, 40.0, centered=(True, False, True))
        .translate((0.0, -20.0, PACKAGE_REFERENCE_LENGTH_MM / 2.0))
    )
    upper = body.intersect(upper_box)
    lower = body.intersect(lower_box)

    for x_mm in (-CLOSURE_PIN_X_MM, CLOSURE_PIN_X_MM):
        upper = upper.union(
            cq.Workplane("XZ")
            .center(x_mm, CLOSURE_PIN_Z_MM)
            .circle(CLOSURE_LUG_RADIUS_MM)
            .extrude(-CLOSURE_LUG_HALF_SPAN_Y_MM)
        )
        lower = lower.union(
            cq.Workplane("XZ")
            .center(x_mm, CLOSURE_PIN_Z_MM)
            .circle(CLOSURE_LUG_RADIUS_MM)
            .extrude(CLOSURE_LUG_HALF_SPAN_Y_MM)
        )
        hole = (
            cq.Workplane("XZ")
            .center(x_mm, CLOSURE_PIN_Z_MM)
            .circle(CLOSURE_HOLE_RADIUS_MM)
            .extrude(2.3, both=True)
        )
        upper = upper.cut(hole)
        lower = lower.cut(hole)

    parts = (
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-UPPER-HALF",
            "split carrier half with integral end-stop lips and closure lugs",
            upper,
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-LOWER-HALF",
            "split carrier half with integral end-stop lips and closure lugs",
            lower,
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-A",
            "positive split-closure capture pin with head and retainer groove",
            _capture_pin(-CLOSURE_PIN_X_MM),
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-B",
            "positive split-closure capture pin with head and retainer groove",
            _capture_pin(CLOSURE_PIN_X_MM),
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-A",
            "split retainer clip positively captured between pin groove shoulders",
            _retainer_clip(-CLOSURE_PIN_X_MM),
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
        CarrierPart(
            "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-B",
            "split retainer clip positively captured between pin groove shoulders",
            _retainer_clip(CLOSURE_PIN_X_MM),
            "PHYSICAL_CANDIDATE_MATERIAL_LOCAL_TEMPLATE_ONLY",
        ),
    )
    _validate_local_mechanics(parts)
    return parts


def _validate_local_mechanics(parts: tuple[CarrierPart, ...]) -> None:
    by_id = {part.part_id: part.solid for part in parts}
    upper = by_id["ACTUATOR-CARRIER-TEMPLATE-UPPER-HALF"]
    lower = by_id["ACTUATOR-CARRIER-TEMPLATE-LOWER-HALF"]
    package = cq.Workplane("XY").circle(PACKAGE_RADIUS_MM).extrude(PACKAGE_REFERENCE_LENGTH_MM)

    if float(upper.val().intersect(lower.val()).Volume()) > 1e-8:
        raise ActuatorCarrierError("split carrier halves may touch at the split plane but cannot overlap in material")
    for half in (upper, lower):
        if float(half.val().intersect(package.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("nominal package reference intersects carrier material")

    combined = upper.union(lower)
    for dz in (-LOCAL_CAPTURE_PROBE_AXIAL_MM, LOCAL_CAPTURE_PROBE_AXIAL_MM):
        if float(package.translate((0.0, 0.0, dz)).val().intersect(combined.val()).Volume()) <= 1e-6:
            raise ActuatorCarrierError("carrier end lips do not create a positive axial overtravel stop")
    for dx, dy in (
        (-LOCAL_CAPTURE_PROBE_RADIAL_MM, 0.0),
        (LOCAL_CAPTURE_PROBE_RADIAL_MM, 0.0),
        (0.0, -LOCAL_CAPTURE_PROBE_RADIAL_MM),
        (0.0, LOCAL_CAPTURE_PROBE_RADIAL_MM),
    ):
        if float(package.translate((dx, dy, 0.0)).val().intersect(combined.val()).Volume()) <= 1e-6:
            raise ActuatorCarrierError("carrier bore does not create positive radial capture")

    pin_ids = (
        "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-A",
        "ACTUATOR-CARRIER-TEMPLATE-CAPTURE-PIN-B",
    )
    clip_ids = (
        "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-A",
        "ACTUATOR-CARRIER-TEMPLATE-RETAINER-CLIP-B",
    )
    for pin_id, clip_id in zip(pin_ids, clip_ids):
        pin = by_id[pin_id]
        clip = by_id[clip_id]
        if float(pin.val().intersect(upper.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("closure pin intersects upper carrier material")
        if float(pin.val().intersect(lower.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("closure pin intersects lower carrier material")
        if float(clip.val().intersect(pin.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("retainer clip intersects nominal pin material")
        if float(clip.val().intersect(upper.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("retainer clip intersects upper carrier material")
        if float(clip.val().intersect(lower.val()).Volume()) > 1e-8:
            raise ActuatorCarrierError("retainer clip intersects lower carrier material")
        for dy in (-CLIP_SHOULDER_PROBE_MM, CLIP_SHOULDER_PROBE_MM):
            if float(clip.translate((0.0, dy, 0.0)).val().intersect(pin.val()).Volume()) <= 1e-6:
                raise ActuatorCarrierError("retainer clip lacks positive axial capture against pin groove shoulders")


def _transform_local(solid: cq.Workplane, placement: SourceReferencePlacement, angle_deg: float) -> cq.Workplane:
    return (
        solid.rotate(
            (0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            placement.pitch_sign * float(angle_deg),
        )
        .translate(placement.base_xyz_mm)
    )


def _expected_source_package(placement: SourceReferencePlacement, baseline_angle_deg: float) -> cq.Workplane:
    local = cq.Workplane("XY").circle(PACKAGE_RADIUS_MM).extrude(PACKAGE_REFERENCE_LENGTH_MM)
    return _transform_local(local, placement, baseline_angle_deg)


def _shape_difference_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().cut(b.val()).Volume()) + float(b.val().cut(a.val()).Volume())


def _protected_prism(model: MasckOneModel, zone_index: int, z_min: float, z_max: float) -> cq.Workplane:
    protected = model.protected_volumes.all[zone_index].zone
    depth = z_max - z_min
    prism = (
        cq.Workplane("XY")
        .workplane(offset=z_min)
        .center(protected.center.x, protected.center.y)
        .ellipse(protected.envelope_width_mm / 2.0, protected.envelope_height_mm / 2.0)
        .extrude(depth)
    )
    if protected.angle_deg:
        prism = prism.rotate(
            (protected.center.x, protected.center.y, 0.0),
            (protected.center.x, protected.center.y, 1.0),
            protected.angle_deg,
        )
    return prism


def _protected_intersection_volume(model: MasckOneModel, solids: tuple[cq.Workplane, ...]) -> float:
    if not solids:
        return 0.0
    z_min = min(float(solid.val().BoundingBox().zmin) for solid in solids) - 1.0
    z_max = max(float(solid.val().BoundingBox().zmax) for solid in solids) + 1.0
    compound = cq.Compound.makeCompound([solid.val() for solid in solids])
    total = 0.0
    for index in range(len(model.protected_volumes.all)):
        prism = _protected_prism(model, index, z_min, z_max)
        total += float(compound.intersect(prism.val()).Volume())
    return total


def _validate_source_model(model: MasckOneModel, baseline_angle_deg: float) -> None:
    if type(model) is not MasckOneModel:
        raise ActuatorCarrierError("carrier package requires the exact MasckOneModel type")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise ActuatorCarrierError("carrier model authority revision is stale")
    if int(model.authority.number("actuation", "count")) != len(ZONE_IDS):
        raise ActuatorCarrierError("carrier model no longer preserves four independent actuator zones")
    if len(model.actuator_envelopes) != len(ZONE_IDS):
        raise ActuatorCarrierError("carrier model must expose exactly four actuator package references")

    for placement, component in zip(SOURCE_REFERENCE_PLACEMENTS, model.actuator_envelopes):
        if component.name != placement.component_name:
            raise ActuatorCarrierError("actuator package component order/identity changed")
        if component.status != "ALPHA_PHYSICS_REFERENCE":
            raise ActuatorCarrierError("current actuator package reference evidence status changed")
        expected = _expected_source_package(placement, baseline_angle_deg)
        if _shape_difference_volume(component.solid, expected) > 1e-6:
            raise ActuatorCarrierError(
                f"{placement.component_name} no longer matches the source-bound current model reference geometry"
            )


def build_actuator_carrier_package(model: MasckOneModel | None = None) -> ActuatorCarrierPackage:
    _require_source_blobs()
    model = model or build_model()
    baseline = float(model.authority.get("actuation", "clean", "axis_angle_baseline_deg"))
    doe = tuple(float(v) for v in model.authority.get("actuation", "clean", "axis_angle_doe_deg"))
    if baseline != 61.0 or doe != (50.0, 55.0, 61.0, 67.0, 72.0):
        raise ActuatorCarrierError("actuation angle baseline/DOE changed and requires carrier reconciliation")
    _validate_source_model(model, baseline)

    parts = _build_local_parts()
    local_solids = tuple(part.solid for part in parts)
    screens: list[ZoneWorldScreen] = []
    for placement, component in zip(SOURCE_REFERENCE_PLACEMENTS, model.actuator_envelopes):
        world_carrier = tuple(_transform_local(solid, placement, baseline) for solid in local_solids)
        source_conflict = _protected_intersection_volume(model, (component.solid,))
        carrier_conflict = _protected_intersection_volume(model, world_carrier)
        screens.append(
            ZoneWorldScreen(
                zone_id=placement.zone_id,
                source_component_name=placement.component_name,
                source_component_brep_sha256=_brep_sha256(component.solid),
                source_package_protected_intersection_mm3=source_conflict,
                carrier_review_protected_intersection_mm3=carrier_conflict,
                baseline_world_transform_status=(
                    "CURRENT_MODEL_REFERENCE_TRANSFORM_ONLY_INHERITED_PROTECTED_HARD_ENVELOPE_CONFLICT"
                ),
                world_mount_eligible=False,
                angle_doe_clearance_status=(
                    "BLOCKED_BASELINE_PROTECTED_HARD_ENVELOPE_CONFLICT_NO_DOE_CLEARANCE_PASS_CLAIM"
                ),
                frame_attachment_status=(
                    "BLOCKED_RELEASED_STRUCTURAL_FRAME_IS_TOPOLOGY_ONLY_NO_3D_MEMBER_OR_MOUNT_DATUM"
                ),
            )
        )

    return ActuatorCarrierPackage(
        source_main_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        source_model_blob_sha=dict(SOURCE_GIT_BLOB_IDENTITIES)["src/masck_one/model.py"],
        local_frame_id=LOCAL_FRAME_ID,
        target_world_frame_id=WORLD_FRAME_ID,
        parts=parts,
        source_reference_placements=SOURCE_REFERENCE_PLACEMENTS,
        zone_world_screens=tuple(screens),
        package_reference_diameter_mm=PACKAGE_REFERENCE_DIAMETER_MM,
        package_reference_length_mm=PACKAGE_REFERENCE_LENGTH_MM,
        package_radial_clearance_seed_mm=CARRIER_RADIAL_CLEARANCE_SEED_MM,
        package_axial_clearance_seed_mm=CARRIER_AXIAL_CLEARANCE_SEED_MM,
        positive_radial_capture_realized=True,
        positive_axial_stops_realized=True,
        split_closure_positive_retention_realized=True,
        structural_frame_attachment_realized=False,
        production_tolerance_stack_resolved=False,
        physical_validation_eligible=False,
        evidence_status=EVIDENCE_STATUS,
    )


def world_review_solids(
    package: ActuatorCarrierPackage,
    *,
    baseline_angle_deg: float = 61.0,
) -> tuple[cq.Workplane, ...]:
    if package.source_reference_placements != SOURCE_REFERENCE_PLACEMENTS:
        raise ActuatorCarrierError("carrier source placement set changed before world review export")
    return tuple(
        _transform_local(part.solid, placement, baseline_angle_deg)
        for placement in package.source_reference_placements
        for part in package.parts
    )


def export_actuator_carrier_package(
    output_dir: str | Path,
    *,
    package: ActuatorCarrierPackage | None = None,
) -> dict[str, object]:
    package = package or build_actuator_carrier_package()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    filenames: list[str] = []
    for part in package.parts:
        filename = f"{part.part_id.lower().replace('-', '_')}.step"
        cq.exporters.export(part.solid, str(output / filename))
        filenames.append(filename)

    local_compound = cq.Compound.makeCompound([part.solid.val() for part in package.parts])
    local_name = "actuator_carrier_local_template_assembly.step"
    cq.exporters.export(local_compound, str(output / local_name))
    filenames.append(local_name)

    review_compound = cq.Compound.makeCompound([solid.val() for solid in world_review_solids(package)])
    review_name = "actuator_carrier_world_reference_collision_review.step"
    cq.exporters.export(review_compound, str(output / review_name))
    filenames.append(review_name)

    manifest = package.manifest()
    manifest_name = "actuator_carrier_manifest.json"
    with (output / manifest_name).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

    return {
        "manifest": manifest,
        "step_files": filenames,
        "manifest_file": manifest_name,
        "world_review_is_product_material": False,
        "local_template_is_world_mount": False,
    }
