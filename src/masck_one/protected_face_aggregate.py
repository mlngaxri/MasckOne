from __future__ import annotations

"""Source-bound protected-face aggregate precheck.

This module centralizes the five authority-derived facial protected regions across:

* finite static development B-reps on released ``main``;
* the deterministic authority-limit worn-pose/misregistration regression set;
* current fluid outlet placement with outlet-radius and position-sensitivity margin; and
* moving-mechanism readiness, which fails closed when no released sweep B-rep exists.

The protected regions remain the existing 2.5D XY hard envelopes with unresolved Z.
This precheck therefore cannot prove anatomical fit, physical clearance, leakage,
airway performance, wet safety, cleansing efficacy, or any other physical outcome.
"""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

import cadquery as cq

from .actuation_sweep_contract import build_actuation_displacement_contract
from .actuator_frames import build_actuator_frame_architecture
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import build_cleanser_storage_architecture
from .distribution_geometry import (
    DistributionGeometryArchitecture,
    _clearance_to_zone_mm,
    build_distribution_geometry_architecture,
)
from .distribution_manifold import build_distribution_manifold_architecture
from .fresh_pump_packaging import build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .model import Component, MasckOneModel, build_model
from .protected_volumes import PlanarProtectedZone, ProtectedVolumeSet
from .spatial import Point2, Point3
from .structural_frame import build_structural_frame_topology
from .water_reservoir import build_water_reservoir_architecture


SCHEMA = "MASCK_ONE_PROTECTED_FACE_AGGREGATE_PRECHECK_V1"
SOURCE_MAIN_SHA = "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_BLOBS = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("src/masck_one/cleanser_storage.py", "5e087ca8b05da8352ad4800b2ef8280ea8ddcf29"),
    ("src/masck_one/fresh_pump_packaging.py", "40cb6fb4c3efbfcf25ed0b7d7a75a4269d90a1b4"),
    ("src/masck_one/distribution_manifold.py", "8f2a6c784b51734aba4d1f3809015707fc328405"),
    ("src/masck_one/distribution_geometry.py", "d2dd8b47bb6a2aa1edf57ac0632778228add7997"),
    ("src/masck_one/actuator_frames.py", "4c2013f994bdc9e084fe227eb5e166f973500ebb"),
    ("src/masck_one/actuation_sweep_contract.py", "7d3180a92646b262f665adbb38030f94a2955df4"),
)

STATIC_METHOD = "EXACT_FINITE_BREP_VS_AUTHORITY_2P5D_PROTECTED_XY_HARD_ENVELOPE"
FLUID_METHOD = "DETERMINISTIC_DISCRETE_WORN_POSE_OUTLET_CENTER_CLEARANCE_SCREEN"
STATIC_CLEAR = "CLEAR_DIGITAL_NOMINAL_POSE"
STATIC_CONFLICT = "PROTECTED_HARD_ENVELOPE_CONFLICT"
STATIC_TOUCHING = "TOUCHING_REVIEW_REQUIRED"
FLUID_CLEAR = "CLEAR_SAMPLED_WORN_POSE_SCREEN"
FLUID_CONFLICT = "SAMPLED_WORN_POSE_PROTECTED_CONFLICT"
MOVING_BLOCKED = "BLOCKED_NO_RELEASED_SWEEP_GEOMETRY"
DIRECTION_BLOCKED = "BLOCKED_NO_REGISTERED_SURFACE_PATH_LENGTH"
KERNEL_VOLUME_EPS_MM3 = 1e-7
KERNEL_DISTANCE_EPS_MM = 1e-7
DIGITAL_ONLY = (
    "DIGITAL_PROTECTED_FACE_AGGREGATE_PRECHECK_ONLY_NOT_ANATOMICAL_FIT_COMFORT_"
    "LEAKAGE_AIRWAY_RELEASE_FORCE_WET_SAFETY_HYGIENE_EFFICACY_OR_PHYSICAL_VALIDATION"
)


class ProtectedFaceAggregateError(ValueError):
    """Raised when the aggregate loses source identity or evidence boundaries."""


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise ProtectedFaceAggregateError(f"{label} must be exact nonblank text")
    return value


def _git_sha(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if len(text) != 40 or any(char not in "0123456789abcdef" for char in text):
        raise ProtectedFaceAggregateError(f"{label} must be lowercase 40-hex")
    return text


def _canonical_sha256(value: object, *, label: str) -> str:
    text = _text(value, label=label)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise ProtectedFaceAggregateError(f"{label} must be lowercase 64-hex")
    return text


def _finite(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise ProtectedFaceAggregateError(f"{label} must be an exact finite real number")
    result = float(value)
    if not math.isfinite(result):
        raise ProtectedFaceAggregateError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _protected_sha256(protected: ProtectedVolumeSet) -> str:
    raw = json.dumps(protected.manifest(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _shape(component: Component) -> cq.Shape:
    shape = component.solid.val()
    if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
        raise ProtectedFaceAggregateError(f"static participant {component.name!r} requires a valid positive-volume B-rep")
    return shape


def _brep_sha256(component: Component) -> str:
    buffer = BytesIO()
    _shape(component).exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise ProtectedFaceAggregateError("B-rep serialization produced no bytes")
    return sha256(payload).hexdigest()


def _protected_prism(zone: PlanarProtectedZone, zmin: float, zmax: float) -> cq.Shape:
    if not math.isfinite(zmin) or not math.isfinite(zmax) or zmax <= zmin:
        raise ProtectedFaceAggregateError("protected prism requires a finite positive participant Z span")
    base = cq.Workplane("XY").workplane(offset=zmin).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        result = base.circle(zone.envelope_width_mm / 2.0).extrude(zmax - zmin)
    elif zone.shape == "ELLIPSE":
        result = base.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0).extrude(zmax - zmin)
    else:
        raise ProtectedFaceAggregateError(f"unsupported protected-zone shape {zone.shape!r}")
    if zone.angle_deg:
        result = result.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    shape = result.val()
    if not shape.isValid() or not shape.Solids():
        raise ProtectedFaceAggregateError("protected reference prism did not produce a valid solid")
    return shape


@dataclass(frozen=True, slots=True)
class SourceBinding:
    source_main_sha: str
    authority_revision: str
    world_frame_id: str
    source_blobs: tuple[tuple[str, str], ...]

    def validate(self) -> None:
        if _git_sha(self.source_main_sha, label="source main") != SOURCE_MAIN_SHA:
            raise ProtectedFaceAggregateError("protected-face aggregate is stale for its released-main source")
        if self.authority_revision != AUTHORITY_REVISION:
            raise ProtectedFaceAggregateError("protected-face aggregate authority revision changed")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise ProtectedFaceAggregateError("protected-face aggregate world frame changed")
        if self.source_blobs != SOURCE_BLOBS:
            raise ProtectedFaceAggregateError("protected-face aggregate source blob set changed")
        for path, digest in self.source_blobs:
            _text(path, label="source path")
            _git_sha(digest, label=f"source blob {path}")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "source_main_sha": self.source_main_sha,
            "authority_revision": self.authority_revision,
            "world_frame_id": self.world_frame_id,
            "source_blobs": [list(item) for item in self.source_blobs],
        }


@dataclass(frozen=True, slots=True)
class StaticProtectedCheck:
    component_id: str
    component_status: str
    component_brep_sha256: str
    zone_id: str
    method: str
    status: str
    intersection_volume_mm3: float
    minimum_distance_mm: float
    evidence_status: str

    def validate(self) -> None:
        for label, value in (
            ("component ID", self.component_id),
            ("component status", self.component_status),
            ("zone ID", self.zone_id),
            ("method", self.method),
            ("status", self.status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label=label)
        _canonical_sha256(self.component_brep_sha256, label="component B-rep")
        if self.method != STATIC_METHOD:
            raise ProtectedFaceAggregateError("static protected check method changed")
        if self.status not in {STATIC_CLEAR, STATIC_CONFLICT, STATIC_TOUCHING}:
            raise ProtectedFaceAggregateError("static protected check status is uncontrolled")
        volume = _finite(self.intersection_volume_mm3, label="intersection volume")
        distance = _finite(self.minimum_distance_mm, label="minimum distance")
        if volume < 0.0 or distance < 0.0:
            raise ProtectedFaceAggregateError("static protected metrics must be nonnegative")
        if self.status == STATIC_CONFLICT and volume <= 0.0:
            raise ProtectedFaceAggregateError("protected conflict requires positive intersection volume")
        if self.status == STATIC_CLEAR and distance <= 0.0:
            raise ProtectedFaceAggregateError("clear protected check requires positive minimum distance")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "component_id": self.component_id,
            "component_status": self.component_status,
            "component_brep_sha256": self.component_brep_sha256,
            "zone_id": self.zone_id,
            "method": self.method,
            "status": self.status,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class FluidOutletProtectedCheck:
    outlet_id: str
    fluid_identity: str
    nominal_protected_clearance_mm: float
    required_clearance_mm: float
    minimum_sampled_clearance_mm: float
    worst_zone_id: str
    worst_pose_index: int
    worst_pose_signature: tuple[float, float, float, float, float]
    sampled_pose_count: int
    outlet_position_sensitivity_mm: float
    outlet_radius_mm: float
    outlet_direction_sensitivity_deg: float
    method: str
    status: str
    direction_path_status: str
    evidence_status: str

    def validate(self) -> None:
        for label, value in (
            ("outlet ID", self.outlet_id),
            ("fluid identity", self.fluid_identity),
            ("worst zone ID", self.worst_zone_id),
            ("method", self.method),
            ("status", self.status),
            ("direction path status", self.direction_path_status),
            ("evidence status", self.evidence_status),
        ):
            _text(value, label=label)
        if self.method != FLUID_METHOD:
            raise ProtectedFaceAggregateError("fluid protected check method changed")
        if self.status not in {FLUID_CLEAR, FLUID_CONFLICT}:
            raise ProtectedFaceAggregateError("fluid protected check status is uncontrolled")
        if self.direction_path_status != DIRECTION_BLOCKED:
            raise ProtectedFaceAggregateError("fluid direction-path evidence boundary changed")
        nominal = _finite(self.nominal_protected_clearance_mm, label="nominal protected clearance")
        required = _finite(self.required_clearance_mm, label="required protected clearance")
        sampled = _finite(self.minimum_sampled_clearance_mm, label="sampled protected clearance")
        position = _finite(self.outlet_position_sensitivity_mm, label="outlet position sensitivity")
        radius = _finite(self.outlet_radius_mm, label="outlet radius")
        direction = _finite(self.outlet_direction_sensitivity_deg, label="outlet direction sensitivity")
        if nominal < 0.0 or required <= 0.0 or position < 0.0 or radius <= 0.0 or direction < 0.0:
            raise ProtectedFaceAggregateError("fluid protected check dimensions are invalid")
        if not math.isclose(required, position + radius, rel_tol=0.0, abs_tol=1e-12):
            raise ProtectedFaceAggregateError("fluid protected margin must equal position sensitivity plus outlet radius")
        if type(self.worst_pose_index) is not int or self.worst_pose_index < 0:
            raise ProtectedFaceAggregateError("worst pose index must be a nonnegative exact integer")
        if type(self.sampled_pose_count) is not int or self.sampled_pose_count <= 0:
            raise ProtectedFaceAggregateError("sampled pose count must be a positive exact integer")
        if type(self.worst_pose_signature) is not tuple or len(self.worst_pose_signature) != 5:
            raise ProtectedFaceAggregateError("worst pose signature must contain five values")
        for value in self.worst_pose_signature:
            _finite(value, label="worst pose signature value")
        if self.status == FLUID_CLEAR and sampled + 1e-12 < required:
            raise ProtectedFaceAggregateError("fluid outlet marked clear below its required protected margin")
        if self.status == FLUID_CONFLICT and sampled + 1e-12 >= required:
            raise ProtectedFaceAggregateError("fluid outlet marked conflict despite meeting required margin")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "outlet_id": self.outlet_id,
            "fluid_identity": self.fluid_identity,
            "nominal_protected_clearance_mm": self.nominal_protected_clearance_mm,
            "required_clearance_mm": self.required_clearance_mm,
            "minimum_sampled_clearance_mm": self.minimum_sampled_clearance_mm,
            "worst_zone_id": self.worst_zone_id,
            "worst_pose_index": self.worst_pose_index,
            "worst_pose_signature": list(self.worst_pose_signature),
            "sampled_pose_count": self.sampled_pose_count,
            "outlet_position_sensitivity_mm": self.outlet_position_sensitivity_mm,
            "outlet_radius_mm": self.outlet_radius_mm,
            "outlet_direction_sensitivity_deg": self.outlet_direction_sensitivity_deg,
            "method": self.method,
            "status": self.status,
            "direction_path_status": self.direction_path_status,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class MovingMechanismProtectedStatus:
    domain_id: str
    source_contract_sha256: str | None
    released_sweep_geometry_available: bool
    status: str
    blocker: str
    evidence_status: str

    def validate(self) -> None:
        _text(self.domain_id, label="moving mechanism domain")
        _text(self.status, label="moving mechanism status")
        _text(self.blocker, label="moving mechanism blocker")
        _text(self.evidence_status, label="moving mechanism evidence status")
        if self.source_contract_sha256 is not None:
            _canonical_sha256(self.source_contract_sha256, label="moving mechanism source contract")
        if type(self.released_sweep_geometry_available) is not bool:
            raise ProtectedFaceAggregateError("moving mechanism geometry availability must be explicit boolean")
        if self.released_sweep_geometry_available or self.status != MOVING_BLOCKED:
            raise ProtectedFaceAggregateError("V1 may not imply released mechanism sweep geometry")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "domain_id": self.domain_id,
            "source_contract_sha256": self.source_contract_sha256,
            "released_sweep_geometry_available": self.released_sweep_geometry_available,
            "status": self.status,
            "blocker": self.blocker,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class ProtectedFaceAggregatePrecheck:
    binding: SourceBinding
    protected_volumes_sha256: str
    worn_pose_regression_sha256: str
    distribution_geometry_sha256: str
    actuator_frame_architecture_sha256: str
    actuation_displacement_contract_sha256: str
    protected_manifest: dict[str, object]
    worn_pose_manifest: dict[str, object]
    static_checks: tuple[StaticProtectedCheck, ...]
    fluid_checks: tuple[FluidOutletProtectedCheck, ...]
    moving_mechanisms: tuple[MovingMechanismProtectedStatus, ...]
    physical_validation_eligible: bool = False
    evidence_status: str = DIGITAL_ONLY

    def validate(self) -> None:
        self.binding.validate()
        for label, value in (
            ("protected volumes", self.protected_volumes_sha256),
            ("worn pose regression", self.worn_pose_regression_sha256),
            ("distribution geometry", self.distribution_geometry_sha256),
            ("actuator frame architecture", self.actuator_frame_architecture_sha256),
            ("actuation displacement contract", self.actuation_displacement_contract_sha256),
        ):
            _canonical_sha256(value, label=label)
        zones = self.protected_manifest.get("zones")
        if type(zones) is not list or len(zones) != 5:
            raise ProtectedFaceAggregateError("aggregate must bind exactly five protected facial regions")
        zone_ids = tuple(item.get("zone_id") for item in zones if type(item) is dict)
        if len(zone_ids) != 5 or len(set(zone_ids)) != 5:
            raise ProtectedFaceAggregateError("protected facial zone IDs must be unique")
        if self.worn_pose_manifest.get("pose_count") != 459:
            raise ProtectedFaceAggregateError("V1 requires the current 459-state deterministic worn-pose regression")
        if type(self.static_checks) is not tuple or not self.static_checks:
            raise ProtectedFaceAggregateError("aggregate requires static protected checks")
        for check in self.static_checks:
            check.validate()
        if set(check.zone_id for check in self.static_checks) != set(zone_ids):
            raise ProtectedFaceAggregateError("static checks must cover every protected facial region")
        component_ids = tuple(sorted(set(check.component_id for check in self.static_checks)))
        if len(self.static_checks) != len(component_ids) * len(zone_ids):
            raise ProtectedFaceAggregateError("static protected checks must form a complete component-by-zone matrix")
        if type(self.fluid_checks) is not tuple or len(self.fluid_checks) != 24:
            raise ProtectedFaceAggregateError("aggregate must screen all 24 current distribution outlets")
        if len({item.outlet_id for item in self.fluid_checks}) != len(self.fluid_checks):
            raise ProtectedFaceAggregateError("fluid outlet IDs must be unique")
        for check in self.fluid_checks:
            check.validate()
            if check.sampled_pose_count != self.worn_pose_manifest.get("pose_count"):
                raise ProtectedFaceAggregateError("fluid check lost complete worn-pose sample coverage")
        if type(self.moving_mechanisms) is not tuple or len(self.moving_mechanisms) < 2:
            raise ProtectedFaceAggregateError("aggregate must state current moving-mechanism protected-face readiness")
        for item in self.moving_mechanisms:
            item.validate()
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ProtectedFaceAggregateError("aggregate cannot become physical validation evidence")
        if self.evidence_status != DIGITAL_ONLY:
            raise ProtectedFaceAggregateError("aggregate evidence firewall changed")

    @property
    def static_conflict_count(self) -> int:
        return sum(item.status == STATIC_CONFLICT for item in self.static_checks)

    @property
    def static_review_required_count(self) -> int:
        return sum(item.status == STATIC_TOUCHING for item in self.static_checks)

    @property
    def fluid_sampled_conflict_count(self) -> int:
        return sum(item.status == FLUID_CONFLICT for item in self.fluid_checks)

    @property
    def moving_sweep_blocked_count(self) -> int:
        return sum(item.status == MOVING_BLOCKED for item in self.moving_mechanisms)

    @property
    def precheck_status(self) -> str:
        if self.static_conflict_count or self.fluid_sampled_conflict_count:
            return "DIGITAL_PROTECTED_FACE_CONFLICT_PRESENT_RELEASE_BLOCKED"
        if self.static_review_required_count or self.moving_sweep_blocked_count:
            return "NO_CHECKED_CONFLICT_BUT_PROTECTED_FACE_PRECHECK_INCOMPLETE"
        return "CHECKED_DIGITAL_PRECHECK_CLEAR_PHYSICAL_VALIDATION_STILL_REQUIRED"

    @property
    def aggregate_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "binding": self.binding.manifest(),
            "source_contracts": {
                "protected_volumes_sha256": self.protected_volumes_sha256,
                "worn_pose_regression_sha256": self.worn_pose_regression_sha256,
                "distribution_geometry_sha256": self.distribution_geometry_sha256,
                "actuator_frame_architecture_sha256": self.actuator_frame_architecture_sha256,
                "actuation_displacement_contract_sha256": self.actuation_displacement_contract_sha256,
            },
            "protected_face": self.protected_manifest,
            "misregistration": self.worn_pose_manifest,
            "static_checks": [item.manifest() for item in self.static_checks],
            "fluid_delivery_checks": [item.manifest() for item in self.fluid_checks],
            "moving_mechanisms": [item.manifest() for item in self.moving_mechanisms],
            "static_conflict_count": self.static_conflict_count,
            "static_review_required_count": self.static_review_required_count,
            "fluid_sampled_conflict_count": self.fluid_sampled_conflict_count,
            "moving_sweep_blocked_count": self.moving_sweep_blocked_count,
            "precheck_status": self.precheck_status,
            "physical_validation_eligible": False,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["aggregate_sha256"] = self.aggregate_sha256
        return payload


def _build_current_distribution_geometry(
    model: MasckOneModel,
) -> tuple[object, DistributionGeometryArchitecture]:
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    pump = build_fresh_pump_packaging_architecture(model.authority, water, cleanser, frame)
    manifold = build_distribution_manifold_architecture(
        model.authority,
        pump,
        water,
        cleanser,
        frame,
    )
    geometry = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    geometry.validate_current_sources(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )
    return frame, geometry


def _static_check(component: Component, zone: PlanarProtectedZone) -> StaticProtectedCheck:
    shape = _shape(component)
    box = shape.BoundingBox()
    prism = _protected_prism(zone, float(box.zmin), float(box.zmax))
    volume = abs(float(shape.intersect(prism).Volume()))
    distance = float(shape.distance(prism))
    if not math.isfinite(volume) or not math.isfinite(distance) or distance < 0.0:
        raise ProtectedFaceAggregateError("static protected B-rep metrics must be finite and nonnegative")
    volume = 0.0 if volume <= KERNEL_VOLUME_EPS_MM3 else volume
    distance = 0.0 if distance <= KERNEL_DISTANCE_EPS_MM else distance
    if volume > 0.0:
        status = STATIC_CONFLICT
    elif distance == 0.0:
        status = STATIC_TOUCHING
    else:
        status = STATIC_CLEAR
    return StaticProtectedCheck(
        component_id=component.name,
        component_status=component.status,
        component_brep_sha256=_brep_sha256(component),
        zone_id=zone.zone_id,
        method=STATIC_METHOD,
        status=status,
        intersection_volume_mm3=volume,
        minimum_distance_mm=distance,
        evidence_status=(
            "RELEASED_MAIN_FINITE_DEVELOPMENT_BREP_VS_AUTHORITY_2P5D_HARD_ENVELOPE;"
            "PROTECTED_Z_REMAINS_UNBOUNDED_AND_NOT_REGISTERED_DYNAMIC_3D_ANATOMY"
        ),
    )


def _static_checks(model: MasckOneModel) -> tuple[StaticProtectedCheck, ...]:
    participants = tuple(component for component in model.components if component.status != "REFERENCE_ONLY")
    return tuple(
        _static_check(component, volume.zone)
        for component in participants
        for volume in model.protected_volumes.all
    )


def _sampled_clearance(
    center_xyz_mm: tuple[float, float, float],
    model: MasckOneModel,
) -> tuple[float, str, int, tuple[float, float, float, float, float]]:
    point = Point3.from_triple(center_xyz_mm)
    best: tuple[float, str, int, tuple[float, float, float, float, float]] | None = None
    for pose_index, pose in enumerate(model.worn_pose_regression.poses):
        point_in_reference = pose.transform.inverse().apply_point(point)
        point_xy = Point2(point_in_reference.x, point_in_reference.y)
        for volume in model.protected_volumes.all:
            clearance = _clearance_to_zone_mm(point_xy, volume)
            record = (clearance, volume.zone.zone_id, pose_index, pose.signature_payload())
            if best is None or (record[0], record[1], record[2]) < (best[0], best[1], best[2]):
                best = record
    if best is None:
        raise ProtectedFaceAggregateError("worn-pose protected clearance screen produced no samples")
    return best


def _fluid_checks(
    model: MasckOneModel,
    geometry: DistributionGeometryArchitecture,
) -> tuple[FluidOutletProtectedCheck, ...]:
    position_sensitivity = model.authority.number("fluid", "outlets", "outlet_position_sensitivity_mm")
    outlet_radius = model.authority.number("fluid", "outlets", "manifold_outlet_diameter_seed_mm") / 2.0
    direction_sensitivity = model.authority.number("fluid", "outlets", "outlet_direction_sensitivity_deg")
    required = position_sensitivity + outlet_radius
    if not math.isclose(required, geometry.required_clearance_mm, rel_tol=0.0, abs_tol=1e-12):
        raise ProtectedFaceAggregateError("aggregate fluid margin drifted from distribution geometry")
    checks: list[FluidOutletProtectedCheck] = []
    for placement in geometry.placements:
        minimum, zone_id, pose_index, signature = _sampled_clearance(placement.center_xyz_mm, model)
        status = FLUID_CLEAR if minimum + 1e-12 >= required else FLUID_CONFLICT
        checks.append(
            FluidOutletProtectedCheck(
                outlet_id=placement.outlet_id,
                fluid_identity=placement.fluid_identity,
                nominal_protected_clearance_mm=placement.protected_clearance_mm,
                required_clearance_mm=required,
                minimum_sampled_clearance_mm=minimum,
                worst_zone_id=zone_id,
                worst_pose_index=pose_index,
                worst_pose_signature=signature,
                sampled_pose_count=model.worn_pose_regression.pose_count,
                outlet_position_sensitivity_mm=position_sensitivity,
                outlet_radius_mm=outlet_radius,
                outlet_direction_sensitivity_deg=direction_sensitivity,
                method=FLUID_METHOD,
                status=status,
                direction_path_status=DIRECTION_BLOCKED,
                evidence_status=(
                    "CURRENT_OUTLET_CENTER_SCREEN_ACROSS_DETERMINISTIC_AUTHORITY_LIMIT_POSES;"
                    "OUTLET_RADIUS_AND_POSITION_SENSITIVITY_INCLUDED;DIRECTION_PATH_REMAINS_BLOCKED_"
                    "WITHOUT_REGISTERED_SKIN_FACING_SURFACE_OR_GROOVE_PATH_LENGTH;NOT_PHYSICAL_FLUID_EVIDENCE"
                ),
            )
        )
    return tuple(checks)


def build_protected_face_aggregate_precheck(
    model: MasckOneModel | None = None,
) -> ProtectedFaceAggregatePrecheck:
    model = model or build_model()
    if type(model) is not MasckOneModel:
        raise ProtectedFaceAggregateError("aggregate requires exact MasckOneModel")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise ProtectedFaceAggregateError("model authority revision is stale for protected-face V1")

    frame, distribution = _build_current_distribution_geometry(model)
    actuator_frames = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuator_frames)
    if actuator_frames.sweep_ready:
        raise ProtectedFaceAggregateError(
            "released actuator sweep geometry became ready; protected-face V1 must be upgraded before reuse"
        )

    moving = (
        MovingMechanismProtectedStatus(
            domain_id="ACTUATION_SWEEP",
            source_contract_sha256=displacement.contract_sha256,
            released_sweep_geometry_available=False,
            status=MOVING_BLOCKED,
            blocker=(
                "current released actuator-frame architecture has unresolved origins, axis azimuths, "
                "mount datums and actuator envelopes, so continuous sweep geometry is unavailable"
            ),
            evidence_status="AUTHORITY_DISPLACEMENT_SEMANTICS_BOUND_BUT_NO_RELEASED_SWEEP_BREP",
        ),
        MovingMechanismProtectedStatus(
            domain_id="RETENTION_AND_EMERGENCY_RELEASE_SWEEP",
            source_contract_sha256=None,
            released_sweep_geometry_available=False,
            status=MOVING_BLOCKED,
            blocker=(
                "released main contains no integrated retention/emergency-release motion B-rep bound to the "
                "protected-face aggregate; candidate PR geometry is intentionally not consumed"
            ),
            evidence_status="RELEASED_MAIN_ABSENCE_RECORDED_CANDIDATE_GEOMETRY_NOT_AUTHORITY",
        ),
    )

    aggregate = ProtectedFaceAggregatePrecheck(
        binding=SourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            authority_revision=AUTHORITY_REVISION,
            world_frame_id=WORLD_FRAME_ID,
            source_blobs=SOURCE_BLOBS,
        ),
        protected_volumes_sha256=_protected_sha256(model.protected_volumes),
        worn_pose_regression_sha256=model.worn_pose_regression.sha256,
        distribution_geometry_sha256=distribution.architecture_sha256,
        actuator_frame_architecture_sha256=actuator_frames.architecture_sha256,
        actuation_displacement_contract_sha256=displacement.contract_sha256,
        protected_manifest=model.protected_volumes.manifest(),
        worn_pose_manifest=model.worn_pose_regression.manifest(),
        static_checks=_static_checks(model),
        fluid_checks=_fluid_checks(model, distribution),
        moving_mechanisms=moving,
    )
    aggregate.validate()
    return aggregate


def export_protected_face_aggregate_precheck(
    output_dir: str | Path,
    aggregate: ProtectedFaceAggregatePrecheck | None = None,
) -> Path:
    aggregate = aggregate or build_protected_face_aggregate_precheck()
    aggregate.validate()
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    path = output / "protected_face_aggregate_precheck_v1.json"
    path.write_text(json.dumps(aggregate.manifest(), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path
