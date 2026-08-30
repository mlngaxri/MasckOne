from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .coverage import FacialCoverageMesh, REGION_T_NOSE_PHILTRUM
from .interface_topology import CompliantInterfaceTopology, ZONE_T_NOSE_PHILTRUM
from .protected_volumes import ProtectedVolumeSet


class NasalSubsystemError(ValueError):
    """Raised when the dedicated nasal subsystem violates its deterministic contract."""


ROLE_BRIDGE_DORSUM = "NASAL_BRIDGE_DORSUM"
ROLE_SIDEWALL_LEFT = "NASAL_SIDEWALL_LEFT"
ROLE_SIDEWALL_RIGHT = "NASAL_SIDEWALL_RIGHT"
ROLE_LOBE = "NASAL_LOBE"
ROLE_PHILTRUM = "NASAL_PHILTRUM"

ROLE_IDS = (
    ROLE_BRIDGE_DORSUM,
    ROLE_SIDEWALL_LEFT,
    ROLE_SIDEWALL_RIGHT,
    ROLE_LOBE,
    ROLE_PHILTRUM,
)


@dataclass(frozen=True, slots=True)
class NasalRoleDefinition:
    role_id: str
    functional_role: str
    contact_intent: bool
    cleansing_target: bool
    nominal_thickness_mm: float | None
    thickness_doe_mm: tuple[float, ...]
    thickness_status: str
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if self.role_id not in ROLE_IDS:
            raise NasalSubsystemError(f"Unknown nasal role {self.role_id!r}")
        for value in (
            self.functional_role,
            self.thickness_status,
            self.geometry_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise NasalSubsystemError("Nasal role metadata must be explicit")
        if self.cleansing_target and not self.contact_intent:
            raise NasalSubsystemError("A nasal cleansing target must have contact intent")
        if self.nominal_thickness_mm is None:
            if self.thickness_doe_mm:
                raise NasalSubsystemError("Unresolved-thickness nasal roles cannot carry numeric DOE values")
        else:
            nominal = float(self.nominal_thickness_mm)
            doe = tuple(float(value) for value in self.thickness_doe_mm)
            if not math.isfinite(nominal) or nominal <= 0.0:
                raise NasalSubsystemError("Nasal nominal thickness must be finite and positive")
            if not doe or any(not math.isfinite(value) or value <= 0.0 for value in doe):
                raise NasalSubsystemError("Nasal thickness DOE must contain finite positive values")
            if nominal not in doe:
                raise NasalSubsystemError("Nasal nominal thickness must occur in its DOE")
            object.__setattr__(self, "nominal_thickness_mm", nominal)
            object.__setattr__(self, "thickness_doe_mm", doe)

    def manifest(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "functional_role": self.functional_role,
            "contact_intent": self.contact_intent,
            "cleansing_target": self.cleansing_target,
            "nominal_thickness_mm": self.nominal_thickness_mm,
            "thickness_doe_mm": list(self.thickness_doe_mm),
            "thickness_status": self.thickness_status,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class NasalTriangleAssignment:
    triangle_index: int
    role_id: str
    area_mm2: float
    centroid_x_mm: float
    centroid_y_mm: float

    def __post_init__(self) -> None:
        if self.triangle_index < 0:
            raise NasalSubsystemError("triangle_index cannot be negative")
        if self.role_id not in ROLE_IDS:
            raise NasalSubsystemError(f"Unknown role ID {self.role_id!r}")
        for label, value in {
            "area_mm2": self.area_mm2,
            "centroid_x_mm": self.centroid_x_mm,
            "centroid_y_mm": self.centroid_y_mm,
        }.items():
            number = float(value)
            if not math.isfinite(number):
                raise NasalSubsystemError(f"{label} must be finite")
            object.__setattr__(self, label, number)
        if self.area_mm2 <= 0.0:
            raise NasalSubsystemError("Nasal assignment area must be positive")


@dataclass(frozen=True, slots=True)
class NasalDevelopmentBoundaries:
    """Derived development-only role boundaries, never anatomical nose dimensions."""

    stem_half_width_mm: float
    stem_y_min_mm: float
    stem_y_max_mm: float
    nostril_left_center_x_mm: float
    nostril_right_center_x_mm: float
    nostril_center_y_mm: float
    nostril_envelope_half_height_mm: float
    nostril_envelope_outer_half_width_mm: float
    lobe_y_min_mm: float
    lobe_y_max_mm: float
    lobe_half_width_mm: float
    bridge_dorsum_half_width_mm: float
    bridge_dorsum_y_min_mm: float
    evidence_status: str = "DEVELOPMENT_ROLE_BOUNDARIES_DERIVED_FROM_EXISTING_AUTHORITY_GEOMETRY_NOT_ANATOMICAL_TRUTH"

    def __post_init__(self) -> None:
        for field_name in (
            "stem_half_width_mm",
            "stem_y_min_mm",
            "stem_y_max_mm",
            "nostril_left_center_x_mm",
            "nostril_right_center_x_mm",
            "nostril_center_y_mm",
            "nostril_envelope_half_height_mm",
            "nostril_envelope_outer_half_width_mm",
            "lobe_y_min_mm",
            "lobe_y_max_mm",
            "lobe_half_width_mm",
            "bridge_dorsum_half_width_mm",
            "bridge_dorsum_y_min_mm",
        ):
            value = float(getattr(self, field_name))
            if not math.isfinite(value):
                raise NasalSubsystemError(f"{field_name} must be finite")
            object.__setattr__(self, field_name, value)
        if min(self.stem_half_width_mm, self.lobe_half_width_mm, self.bridge_dorsum_half_width_mm) <= 0.0:
            raise NasalSubsystemError("Nasal development half-widths must be positive")
        if not self.stem_y_min_mm < self.stem_y_max_mm:
            raise NasalSubsystemError("Nasal T-zone stem Y bounds are inverted")
        if not self.lobe_y_min_mm < self.lobe_y_max_mm:
            raise NasalSubsystemError("Nasal lobe Y bounds are inverted")
        if not self.stem_y_min_mm <= self.lobe_y_min_mm < self.lobe_y_max_mm <= self.stem_y_max_mm:
            raise NasalSubsystemError("Nasal lobe development band must lie inside the T-zone stem")
        if not self.evidence_status.strip():
            raise NasalSubsystemError("Nasal boundary evidence status must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "stem_half_width_mm": self.stem_half_width_mm,
            "stem_y_min_mm": self.stem_y_min_mm,
            "stem_y_max_mm": self.stem_y_max_mm,
            "nostril_left_center_x_mm": self.nostril_left_center_x_mm,
            "nostril_right_center_x_mm": self.nostril_right_center_x_mm,
            "nostril_center_y_mm": self.nostril_center_y_mm,
            "nostril_envelope_half_height_mm": self.nostril_envelope_half_height_mm,
            "nostril_envelope_outer_half_width_mm": self.nostril_envelope_outer_half_width_mm,
            "lobe_y_min_mm": self.lobe_y_min_mm,
            "lobe_y_max_mm": self.lobe_y_max_mm,
            "lobe_half_width_mm": self.lobe_half_width_mm,
            "bridge_dorsum_half_width_mm": self.bridge_dorsum_half_width_mm,
            "bridge_dorsum_y_min_mm": self.bridge_dorsum_y_min_mm,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class NasalSubsystemTopology:
    source_surface_id: str
    source_surface_sha256: str
    source_coverage_sha256: str
    source_interface_sha256: str
    boundaries: NasalDevelopmentBoundaries
    roles: tuple[NasalRoleDefinition, ...]
    assignments: tuple[NasalTriangleAssignment, ...]
    topology_status: str
    evidence_status: str
    anatomical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for label, value in {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
        }.items():
            if not str(value).strip():
                raise NasalSubsystemError(f"{label} must be explicit")
        for digest in (self.source_surface_sha256, self.source_coverage_sha256, self.source_interface_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise NasalSubsystemError("Nasal subsystem source hashes must be SHA-256 values")
        if self.anatomical_validation_eligible:
            raise NasalSubsystemError("Development nasal topology cannot be anatomical-validation evidence")
        role_ids = [role.role_id for role in self.roles]
        if role_ids != list(ROLE_IDS):
            raise NasalSubsystemError("Nasal role order/identity is not the controlled five-role contract")
        indices = [assignment.triangle_index for assignment in self.assignments]
        if len(indices) != len(set(indices)):
            raise NasalSubsystemError("Nasal subsystem cannot assign a triangle more than once")
        unknown = {assignment.role_id for assignment in self.assignments} - set(role_ids)
        if unknown:
            raise NasalSubsystemError(f"Nasal assignments reference unknown roles: {sorted(unknown)}")

    @property
    def role_by_id(self) -> dict[str, NasalRoleDefinition]:
        return {role.role_id: role for role in self.roles}

    @property
    def role_area_mm2(self) -> dict[str, float]:
        areas: dict[str, float] = defaultdict(float)
        for assignment in self.assignments:
            areas[assignment.role_id] += assignment.area_mm2
        return {role_id: areas.get(role_id, 0.0) for role_id in ROLE_IDS}

    @property
    def total_target_area_mm2(self) -> float:
        return sum(assignment.area_mm2 for assignment in self.assignments)

    @property
    def triangle_indices(self) -> frozenset[int]:
        return frozenset(assignment.triangle_index for assignment in self.assignments)

    @property
    def topology_sha256(self) -> str:
        payload = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "boundaries": self.boundaries.manifest(),
            "roles": [role.manifest() for role in self.roles],
            "assignments": [
                [
                    assignment.triangle_index,
                    assignment.role_id,
                    round(assignment.area_mm2, 12),
                    round(assignment.centroid_x_mm, 12),
                    round(assignment.centroid_y_mm, 12),
                ]
                for assignment in self.assignments
            ],
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    def manifest(self) -> dict[str, object]:
        return {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "source_coverage_sha256": self.source_coverage_sha256,
            "source_interface_sha256": self.source_interface_sha256,
            "boundaries": self.boundaries.manifest(),
            "role_area_mm2": self.role_area_mm2,
            "triangle_count": len(self.assignments),
            "total_target_area_mm2": self.total_target_area_mm2,
            "roles": [role.manifest() for role in self.roles],
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
            "topology_sha256": self.topology_sha256,
        }


def _build_roles(authority: Authority) -> tuple[NasalRoleDefinition, ...]:
    center = authority.number("geometry", "nasal_lobe_membrane", "thickness_center_mm")
    doe = tuple(float(value) for value in authority.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm"))
    common = {
        "contact_intent": True,
        "cleansing_target": True,
        "geometry_status": "DEVELOPMENT_ROLE_TOPOLOGY_NOT_FINAL_3D_CONFORMING_GEOMETRY",
        "evidence_status": "FUNCTIONAL_ROLE_ONLY_NOT_FIT_PRESSURE_OR_EFFICACY_EVIDENCE",
    }
    unresolved = {
        "nominal_thickness_mm": None,
        "thickness_doe_mm": (),
        "thickness_status": "UNRESOLVED_PENDING_DETAILED_INTERFACE_GEOMETRY_AND_MATERIAL_SELECTION",
    }
    return (
        NasalRoleDefinition(ROLE_BRIDGE_DORSUM, "nasal bridge and dorsum cleansing/contact field", **common, **unresolved),
        NasalRoleDefinition(ROLE_SIDEWALL_LEFT, "left nasal sidewall cleansing/contact field", **common, **unresolved),
        NasalRoleDefinition(ROLE_SIDEWALL_RIGHT, "right nasal sidewall cleansing/contact field", **common, **unresolved),
        NasalRoleDefinition(
            ROLE_LOBE,
            "nasal lobe/tip/alar development field surrounding but excluding protected nostril openings",
            contact_intent=True,
            cleansing_target=True,
            nominal_thickness_mm=center,
            thickness_doe_mm=doe,
            thickness_status=str(authority.get("geometry", "nasal_lobe_membrane", "status")),
            geometry_status="DEDICATED_LOBE_DEVELOPMENT_BOUNDARY_LOCAL_THICKNESS_AUTHORITY_APPLIES",
            evidence_status="AUTHORITY_THICKNESS_LOCALIZED_TO_DEVELOPMENT_LOBE_ROLE_NOT_ANATOMICAL_VALIDATION",
        ),
        NasalRoleDefinition(ROLE_PHILTRUM, "nose-to-upper-lip/philtrum cleansing/contact continuity field", **common, **unresolved),
    )


def derive_nasal_development_boundaries(
    coverage: FacialCoverageMesh,
    protected: ProtectedVolumeSet,
) -> NasalDevelopmentBoundaries:
    left = protected.nostril_left.zone
    right = protected.nostril_right.zone
    if not math.isclose(left.center.y, right.center.y, rel_tol=0.0, abs_tol=1e-12):
        raise NasalSubsystemError("Neutral baseline nostril centers must share Y for deterministic role derivation")
    if not math.isclose(abs(left.center.x), abs(right.center.x), rel_tol=0.0, abs_tol=1e-12):
        raise NasalSubsystemError("Neutral baseline nostril centers must be sagittally symmetric")
    half_height = max(left.envelope_height_mm, right.envelope_height_mm) / 2.0
    outer_half_width = max(
        abs(left.center.x) + left.envelope_width_mm / 2.0,
        abs(right.center.x) + right.envelope_width_mm / 2.0,
    )
    lobe_y_min = max(coverage.t_zone_definition.stem_y_min_mm, left.center.y - half_height)
    lobe_y_max = min(coverage.t_zone_definition.stem_y_max_mm, left.center.y + half_height)
    lobe_half_width = min(coverage.t_zone_definition.stem_half_width_mm, outer_half_width)
    # The bridge/dorsum development half-width is anchored directly to the
    # authority-defined nostril-center spacing: the central band extends to each
    # nostril centerline. No arbitrary percentage or anatomical width is invented.
    bridge_dorsum_half_width = min(abs(left.center.x), abs(right.center.x))
    return NasalDevelopmentBoundaries(
        stem_half_width_mm=coverage.t_zone_definition.stem_half_width_mm,
        stem_y_min_mm=coverage.t_zone_definition.stem_y_min_mm,
        stem_y_max_mm=coverage.t_zone_definition.stem_y_max_mm,
        nostril_left_center_x_mm=left.center.x,
        nostril_right_center_x_mm=right.center.x,
        nostril_center_y_mm=left.center.y,
        nostril_envelope_half_height_mm=half_height,
        nostril_envelope_outer_half_width_mm=outer_half_width,
        lobe_y_min_mm=lobe_y_min,
        lobe_y_max_mm=lobe_y_max,
        lobe_half_width_mm=lobe_half_width,
        bridge_dorsum_half_width_mm=bridge_dorsum_half_width,
        bridge_dorsum_y_min_mm=lobe_y_max,
    )


def _role_for_xy(x: float, y: float, boundaries: NasalDevelopmentBoundaries) -> str:
    if y < boundaries.lobe_y_min_mm:
        return ROLE_PHILTRUM
    if y <= boundaries.lobe_y_max_mm:
        return ROLE_LOBE
    if abs(x) <= boundaries.bridge_dorsum_half_width_mm:
        return ROLE_BRIDGE_DORSUM
    return ROLE_SIDEWALL_LEFT if x < 0.0 else ROLE_SIDEWALL_RIGHT


def build_nasal_subsystem_topology(
    authority: Authority,
    coverage: FacialCoverageMesh,
    interface: CompliantInterfaceTopology,
    protected: ProtectedVolumeSet,
) -> NasalSubsystemTopology:
    if interface.source_surface_id != coverage.source_surface_id:
        raise NasalSubsystemError("Nasal subsystem coverage/interface source surfaces differ")
    if interface.coverage_segmentation_sha256 != coverage.segmentation_sha256:
        raise NasalSubsystemError("Nasal subsystem requires the exact interface/coverage segmentation pair")
    if protected.source_surface_id != coverage.source_surface_id:
        raise NasalSubsystemError("Nasal subsystem protected-volume source surface differs")

    boundaries = derive_nasal_development_boundaries(coverage, protected)
    roles = _build_roles(authority)
    interface_contact_ids = {
        assignment.triangle_index
        for assignment in interface.contact_assignments
        if assignment.parameter_zone_id == ZONE_T_NOSE_PHILTRUM
    }
    central_targets = tuple(
        triangle
        for triangle in coverage.triangles
        if triangle.region_id == REGION_T_NOSE_PHILTRUM and triangle.is_target
    )
    coverage_ids = {triangle.triangle_index for triangle in central_targets}
    if coverage_ids != interface_contact_ids:
        raise NasalSubsystemError("Central T-zone coverage and interface contact assignments disagree")

    assignments = tuple(
        NasalTriangleAssignment(
            triangle_index=triangle.triangle_index,
            role_id=_role_for_xy(triangle.centroid.x, triangle.centroid.y, boundaries),
            area_mm2=triangle.area_mm2,
            centroid_x_mm=triangle.centroid.x,
            centroid_y_mm=triangle.centroid.y,
        )
        for triangle in central_targets
    )
    topology = NasalSubsystemTopology(
        source_surface_id=coverage.source_surface_id,
        source_surface_sha256=coverage.source_surface_sha256,
        source_coverage_sha256=coverage.segmentation_sha256,
        source_interface_sha256=interface.topology_sha256,
        boundaries=boundaries,
        roles=roles,
        assignments=assignments,
        topology_status="PHASE2_ITERATION11_DEDICATED_NASAL_SUBSYSTEM_DEVELOPMENT_TOPOLOGY",
        evidence_status="DETERMINISTIC_FUNCTIONAL_PARTITION_NOT_ANATOMICAL_FIT_PRESSURE_OR_EFFICACY_EVIDENCE",
        anatomical_validation_eligible=False,
    )

    if topology.triangle_indices != coverage_ids:
        raise NasalSubsystemError("Nasal subsystem did not assign every central T-zone target exactly once")
    central_target_area = sum(triangle.area_mm2 for triangle in central_targets)
    if abs(topology.total_target_area_mm2 - central_target_area) > 1e-8:
        raise NasalSubsystemError("Nasal subsystem role partition does not conserve central T-zone target area")
    areas = topology.role_area_mm2
    missing_roles = [role_id for role_id, area in areas.items() if area <= 0.0]
    if missing_roles:
        raise NasalSubsystemError(f"Current development mesh produced empty nasal roles: {missing_roles}")
    if topology.role_by_id[ROLE_LOBE].nominal_thickness_mm != authority.number(
        "geometry", "nasal_lobe_membrane", "thickness_center_mm"
    ):
        raise NasalSubsystemError("Nasal lobe role lost the authority center thickness")
    for role_id in (ROLE_BRIDGE_DORSUM, ROLE_SIDEWALL_LEFT, ROLE_SIDEWALL_RIGHT, ROLE_PHILTRUM):
        role = topology.role_by_id[role_id]
        if role.nominal_thickness_mm is not None or role.thickness_doe_mm:
            raise NasalSubsystemError(f"Authority nasal-lobe thickness leaked into unresolved role {role_id}")
    return topology
