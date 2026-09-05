from __future__ import annotations

"""Topology-agnostic Cell 1 ingestion gate for exterior-shell candidates.

The gate deliberately consumes a complete candidate shell B-rep as one controlled
object. It never identifies product geometry by face/edge index, and it never promotes
an unreviewed specialist branch into released product truth. Digital checks in this
module are not physical fit, comfort, seal, leakage, hygiene, durability, tooling-
capability, or safety evidence.
"""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import math
from typing import Iterable

import cadquery as cq

from .authority import Authority
from .model import Component, MasckOneModel
from .realized_waste_backbone import Line3
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release


SCHEMA = "MASCK_ONE_CELL1_EXTERIOR_INGESTION_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
KERNEL_INTERSECTION_TOLERANCE_MM3 = 1e-5
WALL_PROBE_RADIAL_STEP_MM = 0.25
WALL_PROBE_ANGLE_STEP_DEG = 15
BOUNDARY_BISECTION_ITERATIONS = 28
DIGITAL_EVIDENCE_STATUS = (
    "DIGITAL_EXTERIOR_INGESTION_ONLY_NOT_FIT_COMFORT_SEAL_LEAKAGE_HYGIENE_"
    "DURABILITY_TOOLING_CAPABILITY_OR_PHYSICAL_SAFETY_EVIDENCE"
)


class ExteriorIngestionError(ValueError):
    pass


def _git_sha(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ExteriorIngestionError(f"{label} must be exact lowercase 40-hex")
    return value


def _sha256(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ExteriorIngestionError(f"{label} must be exact lowercase SHA-256")
    return value


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise ExteriorIngestionError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise ExteriorIngestionError(f"{label} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class ExteriorCandidateBinding:
    source_pr: int
    source_head_sha: str
    source_base_main_sha: str
    source_geometry_blob_sha: str
    source_integration_blob_sha: str
    source_evidence_blob_sha: str
    source_manifest_sha256: str
    world_frame_id: str
    ci_conclusion: str
    independent_review_disposition: str
    blockers: tuple[str, ...]

    def validate(self, *, reconstructed_main_sha: str) -> None:
        if type(self.source_pr) is not int or isinstance(self.source_pr, bool) or self.source_pr <= 0:
            raise ExteriorIngestionError("source PR must be a positive exact integer")
        _git_sha(self.source_head_sha, "source head")
        _git_sha(self.source_base_main_sha, "source base main")
        _git_sha(self.source_geometry_blob_sha, "source geometry blob")
        _git_sha(self.source_integration_blob_sha, "source integration blob")
        _git_sha(self.source_evidence_blob_sha, "source evidence blob")
        _sha256(self.source_manifest_sha256, "source manifest")
        current = _git_sha(reconstructed_main_sha, "reconstructed main")
        if self.source_base_main_sha != current:
            raise ExteriorIngestionError("exterior candidate is stale for reconstructed main")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise ExteriorIngestionError("exterior candidate must use the canonical authority-world frame")
        if self.ci_conclusion != "SUCCESS":
            raise ExteriorIngestionError("exterior candidate exact-head engineering CI is not SUCCESS")
        if self.independent_review_disposition != "APPROVED":
            raise ExteriorIngestionError("exterior candidate lacks exact-head independent approval")
        if type(self.blockers) is not tuple or any(type(item) is not str or not item.strip() for item in self.blockers):
            raise ExteriorIngestionError("candidate blockers must be an immutable tuple of nonblank strings")
        if self.blockers:
            raise ExteriorIngestionError("exterior candidate still has release blockers")

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExteriorManufacturingClosure:
    eye_inner_edge_roll_radius_mm: float
    eye_roll_geometry_status: str
    tooling_architecture_status: str
    mold_draft_screen_status: str
    mold_draft_nominal_deg: float
    secondary_operation_exceptions: tuple[str, ...] = ()
    mvp_design_review_status: str = "APPROVED_FOR_MVP_FREEZE"
    physical_validation_eligible: bool = False

    def validate(self, authority: Authority) -> None:
        actual_roll = _finite(self.eye_inner_edge_roll_radius_mm, "eye inner-edge roll")
        required_roll = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
        if not math.isclose(actual_roll, required_roll, rel_tol=0.0, abs_tol=1e-6):
            raise ExteriorIngestionError("final B-rep eye inner-edge roll does not match machine authority")
        if self.eye_roll_geometry_status != "FINAL_BREP_VERIFIED":
            raise ExteriorIngestionError("eye inner-edge roll must be verified on the final B-rep")
        if self.tooling_architecture_status != "DIGITAL_TOOLING_ARCHITECTURE_RESOLVED":
            raise ExteriorIngestionError("exterior tooling/part-split architecture remains unresolved")
        if self.mold_draft_screen_status not in {"PASS", "CONTROLLED_SECONDARY_OPERATION_EXCEPTIONS"}:
            raise ExteriorIngestionError("exterior mold-draft screen has not closed")
        actual_draft = _finite(self.mold_draft_nominal_deg, "mold draft")
        required_draft = authority.number("manufacturing", "mold_draft_nominal_deg")
        if not math.isclose(actual_draft, required_draft, rel_tol=0.0, abs_tol=1e-9):
            raise ExteriorIngestionError("candidate draft baseline does not match machine authority")
        if type(self.secondary_operation_exceptions) is not tuple or any(
            type(item) is not str or not item.strip() for item in self.secondary_operation_exceptions
        ):
            raise ExteriorIngestionError("secondary-operation exceptions must be immutable nonblank strings")
        if self.mold_draft_screen_status == "CONTROLLED_SECONDARY_OPERATION_EXCEPTIONS" and not self.secondary_operation_exceptions:
            raise ExteriorIngestionError("controlled draft exceptions require explicit exception identities")
        if self.mold_draft_screen_status == "PASS" and self.secondary_operation_exceptions:
            raise ExteriorIngestionError("a full draft PASS cannot also carry secondary-operation exceptions")
        if self.mvp_design_review_status != "APPROVED_FOR_MVP_FREEZE":
            raise ExteriorIngestionError("candidate has not cleared the MVP exterior design review")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ExteriorIngestionError("digital manufacturing closure cannot become physical validation evidence")

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RadialWallScreen:
    minimum_wall_mm: float
    sampled_ray_count: int
    z_levels_mm: tuple[float, ...]
    angle_step_deg: int
    radial_step_mm: float
    evidence_status: str = "FINAL_BREP_RADIAL_WALL_SCREEN_DIGITAL_ONLY"

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExteriorGeometryAssessment:
    shell_valid: bool
    shell_solid_count: int
    shell_volume_mm3: float
    bounding_box_mm: tuple[float, float, float]
    package_intersection_mm3: tuple[tuple[str, float], ...]
    protected_keepout_intersection_mm3: tuple[tuple[str, float], ...]
    mixed_waste_route_a_clearance_mm: float
    mixed_waste_route_a_required_radius_mm: float
    released_waste_manifest_sha256: str
    wall_screen: RadialWallScreen
    absolute_wall_requirement_mm: float
    accepted: bool
    blockers: tuple[str, ...]
    physical_validation_eligible: bool = False

    def manifest(self) -> dict[str, object]:
        payload = asdict(self)
        payload["package_intersection_mm3"] = [list(item) for item in self.package_intersection_mm3]
        payload["protected_keepout_intersection_mm3"] = [list(item) for item in self.protected_keepout_intersection_mm3]
        return payload


@dataclass(frozen=True, slots=True)
class ExteriorIngestionReceipt:
    binding: ExteriorCandidateBinding
    manufacturing: ExteriorManufacturingClosure
    geometry: ExteriorGeometryAssessment
    reconstructed_main_sha: str
    source_component_name: str
    accepted: bool
    evidence_status: str = DIGITAL_EVIDENCE_STATUS
    physical_validation_eligible: bool = False

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "reconstructed_main_sha": self.reconstructed_main_sha,
            "source_component_name": self.source_component_name,
            "binding": self.binding.manifest(),
            "manufacturing": self.manufacturing.manifest(),
            "geometry": self.geometry.manifest(),
            "accepted": self.accepted,
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["receipt_sha256"] = self.receipt_sha256
        return payload

    @property
    def receipt_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()


def _inside(shape: cq.Shape, radius_mm: float, angle_deg: float, z_mm: float) -> bool:
    angle = math.radians(angle_deg)
    return bool(
        shape.isInside(
            cq.Vector(radius_mm * math.cos(angle), radius_mm * math.sin(angle), z_mm),
            1e-7,
        )
    )


def _transition_radius(
    shape: cq.Shape,
    *,
    lower_mm: float,
    upper_mm: float,
    angle_deg: float,
    z_mm: float,
    lower_state: bool,
) -> float:
    lower = float(lower_mm)
    upper = float(upper_mm)
    if _inside(shape, upper, angle_deg, z_mm) == lower_state:
        raise ExteriorIngestionError("wall probe transition bracket does not change occupancy")
    for _ in range(BOUNDARY_BISECTION_ITERATIONS):
        midpoint = 0.5 * (lower + upper)
        if _inside(shape, midpoint, angle_deg, z_mm) == lower_state:
            lower = midpoint
        else:
            upper = midpoint
    return 0.5 * (lower + upper)


def _default_wall_z_levels(shape: cq.Shape) -> tuple[float, ...]:
    bb = shape.BoundingBox()
    zmin = float(bb.zmin)
    zmax = float(bb.zmax)
    span = zmax - zmin
    if not math.isfinite(span) or span <= 0.0:
        raise ExteriorIngestionError("candidate shell has invalid Z extent")
    offsets = (0.25, 0.75, 1.25, 1.75, 2.0)
    levels = [zmin + offset for offset in offsets if offset < span - 1e-4]
    levels.extend(zmin + span * fraction for fraction in (0.25, 0.5, 0.75))
    return tuple(sorted({round(level, 9) for level in levels if zmin < level < zmax}))


def radial_wall_screen(
    shape: cq.Shape,
    *,
    z_levels_mm: Iterable[float] | None = None,
    angle_step_deg: int = WALL_PROBE_ANGLE_STEP_DEG,
    radial_step_mm: float = WALL_PROBE_RADIAL_STEP_MM,
) -> RadialWallScreen:
    """Measure radial material-run thickness on the actual final B-rep.

    Rays originate from the frozen product XY origin and use occupancy transitions,
    not face IDs or edge ordering. For each ray the longest material run is used so an
    aperture-edge/tangent sliver cannot masquerade as shell wall. This is a digital
    development screen, not a production metrology method.
    """
    if type(angle_step_deg) is not int or isinstance(angle_step_deg, bool) or angle_step_deg <= 0 or 360 % angle_step_deg:
        raise ExteriorIngestionError("wall-probe angle step must be a positive integer divisor of 360")
    step = _finite(radial_step_mm, "wall-probe radial step")
    if step <= 0.0 or step > 1.0:
        raise ExteriorIngestionError("wall-probe radial step must be in (0, 1] mm")
    levels = tuple(_finite(value, "wall-probe Z level") for value in (z_levels_mm or _default_wall_z_levels(shape)))
    if not levels:
        raise ExteriorIngestionError("wall probe requires at least one Z level")

    bb = shape.BoundingBox()
    radial_limit = 1.05 * max(abs(float(bb.xmin)), abs(float(bb.xmax)), abs(float(bb.ymin)), abs(float(bb.ymax))) + 2.0
    sample_count = int(math.ceil(radial_limit / step))
    radii = tuple(min(radial_limit, index * step) for index in range(sample_count + 1))
    ray_walls: list[float] = []

    for z_mm in levels:
        for angle_deg in range(0, 360, angle_step_deg):
            states = tuple(_inside(shape, radius, float(angle_deg), z_mm) for radius in radii)
            runs: list[float] = []
            run_start: float | None = 0.0 if states[0] else None
            for index in range(len(radii) - 1):
                left_state = states[index]
                right_state = states[index + 1]
                if left_state == right_state:
                    continue
                boundary = _transition_radius(
                    shape,
                    lower_mm=radii[index],
                    upper_mm=radii[index + 1],
                    angle_deg=float(angle_deg),
                    z_mm=z_mm,
                    lower_state=left_state,
                )
                if not left_state and right_state:
                    run_start = boundary
                elif left_state and not right_state and run_start is not None:
                    runs.append(boundary - run_start)
                    run_start = None
            if states[-1] and run_start is not None:
                runs.append(radial_limit - run_start)
            positive_runs = [run for run in runs if run > 1e-6]
            if positive_runs:
                ray_walls.append(max(positive_runs))

    if not ray_walls:
        raise ExteriorIngestionError("wall probe found no radial material runs")
    minimum = min(ray_walls)
    return RadialWallScreen(
        minimum_wall_mm=minimum,
        sampled_ray_count=len(ray_walls),
        z_levels_mm=levels,
        angle_step_deg=angle_step_deg,
        radial_step_mm=step,
    )


def _intersection_volume(a: cq.Shape, b: cq.Shape) -> float:
    return abs(float(a.intersect(b).Volume()))


def _route_a_clearance(shell: cq.Shape) -> tuple[float, float, str]:
    release = build_current_cell4_waste_backbone_release()
    route = release.realization.routes[0]
    if len(route.centerline) != 1 or type(route.centerline[0]) is not Line3:
        raise ExteriorIngestionError("released limiting mixed-waste Route A is no longer one exact line")
    line = route.centerline[0]
    edge = cq.Edge.makeLine(cq.Vector(*line.start.as_tuple()), cq.Vector(*line.end.as_tuple()))
    return float(edge.distance(shell)), float(route.service_envelope_radius_mm), release.manifest_sha256


def assess_exterior_geometry(
    baseline: MasckOneModel,
    candidate_shell: Component,
) -> ExteriorGeometryAssessment:
    if type(baseline) is not MasckOneModel:
        raise ExteriorIngestionError("baseline must use the exact MasckOneModel type")
    if type(candidate_shell) is not Component or candidate_shell.name != "rigid_shell":
        raise ExteriorIngestionError("candidate must be the complete rigid_shell Component")
    solid = candidate_shell.solid.val()
    valid = bool(solid.isValid())
    solid_count = int(candidate_shell.solid.solids().size())
    volume = float(solid.Volume())
    bb = solid.BoundingBox()
    outer_w, outer_h = baseline.authority.pair("geometry", "outer_xy_envelope_mm")

    packages = (
        *baseline.actuator_envelopes,
        baseline.water_reservoir_envelope,
        baseline.waste_cartridge_envelope,
        baseline.battery_reference_envelope,
    )
    package_intersections = tuple(
        (component.name, _intersection_volume(solid, component.solid.val()))
        for component in packages
    )
    keepout_intersections = tuple(
        (component.name, _intersection_volume(solid, component.solid.val()))
        for component in baseline.visual_keepouts
    )
    route_clearance, route_required, route_manifest_sha = _route_a_clearance(solid)
    wall = radial_wall_screen(solid)
    wall_requirement = baseline.authority.number("geometry", "shell_absolute_development_min_mm")

    blockers: list[str] = []
    if not valid or solid_count != 1 or volume <= 0.0:
        blockers.append("FINAL_BREP_NOT_ONE_VALID_POSITIVE_VOLUME_SOLID")
    if float(bb.xlen) > outer_w + 1e-5 or float(bb.ylen) > outer_h + 1e-5:
        blockers.append("AUTHORITY_XY_ENVELOPE_EXCEEDED")
    if any(value > KERNEL_INTERSECTION_TOLERANCE_MM3 for _, value in package_intersections):
        blockers.append("RELEASED_PACKAGE_MATERIAL_INTERSECTION")
    if any(value > KERNEL_INTERSECTION_TOLERANCE_MM3 for _, value in keepout_intersections):
        blockers.append("PROTECTED_VISUAL_APERTURE_OCCLUDED")
    if route_clearance + 1e-9 < route_required:
        blockers.append("RELEASED_MIXED_WASTE_SERVICE_ENVELOPE_VIOLATION")
    if wall.minimum_wall_mm + 1e-6 < wall_requirement:
        blockers.append("FINAL_BREP_WALL_BELOW_AUTHORITY_MINIMUM")

    return ExteriorGeometryAssessment(
        shell_valid=valid,
        shell_solid_count=solid_count,
        shell_volume_mm3=volume,
        bounding_box_mm=(float(bb.xlen), float(bb.ylen), float(bb.zlen)),
        package_intersection_mm3=package_intersections,
        protected_keepout_intersection_mm3=keepout_intersections,
        mixed_waste_route_a_clearance_mm=route_clearance,
        mixed_waste_route_a_required_radius_mm=route_required,
        released_waste_manifest_sha256=route_manifest_sha,
        wall_screen=wall,
        absolute_wall_requirement_mm=wall_requirement,
        accepted=not blockers,
        blockers=tuple(blockers),
        physical_validation_eligible=False,
    )


def replace_shell_only(baseline: MasckOneModel, candidate_shell: Component) -> MasckOneModel:
    """Substitute exactly one complete shell object without reauthoring foreign geometry."""
    if type(baseline) is not MasckOneModel or type(candidate_shell) is not Component:
        raise ExteriorIngestionError("shell substitution requires exact model/component types")
    if candidate_shell.name != baseline.shell.name or candidate_shell.name != "rigid_shell":
        raise ExteriorIngestionError("candidate shell identity must remain rigid_shell")
    return replace(baseline, shell=candidate_shell)


def ingest_exterior_candidate(
    baseline: MasckOneModel,
    candidate_shell: Component,
    *,
    binding: ExteriorCandidateBinding,
    manufacturing: ExteriorManufacturingClosure,
    reconstructed_main_sha: str,
) -> tuple[MasckOneModel, ExteriorIngestionReceipt]:
    binding.validate(reconstructed_main_sha=reconstructed_main_sha)
    manufacturing.validate(baseline.authority)
    geometry = assess_exterior_geometry(baseline, candidate_shell)
    if not geometry.accepted:
        raise ExteriorIngestionError(
            "candidate final B-rep failed exterior ingestion: " + ", ".join(geometry.blockers)
        )
    integrated = replace_shell_only(baseline, candidate_shell)

    # Object-identity checks protect the boundary against accidental topology-coupled
    # reauthoring of another Cell's released product data.
    preserved_fields = (
        "authority",
        "datums",
        "facial_reference",
        "facial_surface",
        "protected_volumes",
        "worn_pose_regression",
        "coverage_mesh",
        "compliant_interface_topology",
        "nasal_subsystem_topology",
        "nasal_interface",
        "actuator_envelopes",
        "water_reservoir_envelope",
        "waste_cartridge_envelope",
        "battery_reference_envelope",
        "visual_keepouts",
    )
    if any(getattr(integrated, field) is not getattr(baseline, field) for field in preserved_fields):
        raise ExteriorIngestionError("exterior ingestion reauthored foreign-lane model objects")

    receipt = ExteriorIngestionReceipt(
        binding=binding,
        manufacturing=manufacturing,
        geometry=geometry,
        reconstructed_main_sha=_git_sha(reconstructed_main_sha, "reconstructed main"),
        source_component_name=candidate_shell.name,
        accepted=True,
        evidence_status=DIGITAL_EVIDENCE_STATUS,
        physical_validation_eligible=False,
    )
    return integrated, receipt
