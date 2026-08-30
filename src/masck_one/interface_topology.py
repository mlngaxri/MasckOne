from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .coverage import (
    FacialCoverageMesh,
    REGION_ACTIVE_OTHER,
    REGION_PROTECTED_EYE_LEFT,
    REGION_PROTECTED_EYE_RIGHT,
    REGION_PROTECTED_MOUTH,
    REGION_PROTECTED_NOSTRIL_LEFT,
    REGION_PROTECTED_NOSTRIL_RIGHT,
    REGION_T_FOREHEAD,
    REGION_T_NOSE_PHILTRUM,
)


class InterfaceTopologyError(ValueError):
    """Raised when the compliant-interface topology violates its engineering contract."""


ZONE_GENERAL_FACE = "INTERFACE_GENERAL_FACE"
ZONE_T_FOREHEAD = "INTERFACE_T_ZONE_FOREHEAD"
ZONE_T_NOSE_PHILTRUM = "INTERFACE_T_ZONE_NOSE_PHILTRUM"
ZONE_OPENING_EYE_LEFT = "INTERFACE_OPENING_EYE_LEFT"
ZONE_OPENING_EYE_RIGHT = "INTERFACE_OPENING_EYE_RIGHT"
ZONE_OPENING_MOUTH = "INTERFACE_OPENING_MOUTH"
ZONE_OPENING_NOSTRIL_LEFT = "INTERFACE_OPENING_NOSTRIL_LEFT"
ZONE_OPENING_NOSTRIL_RIGHT = "INTERFACE_OPENING_NOSTRIL_RIGHT"


@dataclass(frozen=True, slots=True)
class InterfaceParameterZone:
    zone_id: str
    functional_role: str
    coverage_region_ids: tuple[str, ...]
    contact_intent: bool
    cleansing_target: bool
    nominal_thickness_mm: float | None
    thickness_doe_mm: tuple[float, ...]
    thickness_status: str
    material_status: str
    geometry_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in {
            "zone_id": self.zone_id,
            "functional_role": self.functional_role,
            "thickness_status": self.thickness_status,
            "material_status": self.material_status,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
        }.items():
            if not str(value).strip():
                raise InterfaceTopologyError(f"{label} must be non-empty")
        if not self.coverage_region_ids or any(not item.strip() for item in self.coverage_region_ids):
            raise InterfaceTopologyError("coverage_region_ids must contain explicit region identifiers")
        if len(set(self.coverage_region_ids)) != len(self.coverage_region_ids):
            raise InterfaceTopologyError("coverage_region_ids cannot contain duplicates")
        if self.cleansing_target and not self.contact_intent:
            raise InterfaceTopologyError("A cleansing-target zone must have contact intent")

        if self.nominal_thickness_mm is None:
            if self.thickness_doe_mm:
                raise InterfaceTopologyError(
                    "A zone without a frozen/derived nominal thickness cannot carry a numeric DOE thickness range"
                )
        else:
            nominal = float(self.nominal_thickness_mm)
            if not math.isfinite(nominal) or nominal <= 0.0:
                raise InterfaceTopologyError("nominal_thickness_mm must be finite and positive")
            object.__setattr__(self, "nominal_thickness_mm", nominal)
            doe = tuple(float(value) for value in self.thickness_doe_mm)
            if any(not math.isfinite(value) or value <= 0.0 for value in doe):
                raise InterfaceTopologyError("thickness_doe_mm values must be finite and positive")
            object.__setattr__(self, "thickness_doe_mm", doe)

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "functional_role": self.functional_role,
            "coverage_region_ids": list(self.coverage_region_ids),
            "contact_intent": self.contact_intent,
            "cleansing_target": self.cleansing_target,
            "nominal_thickness_mm": self.nominal_thickness_mm,
            "thickness_doe_mm": list(self.thickness_doe_mm),
            "thickness_status": self.thickness_status,
            "material_status": self.material_status,
            "geometry_status": self.geometry_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class NasalLobeThicknessAuthority:
    """Authority-backed thickness data whose geometric application boundary is not yet invented."""

    center_thickness_mm: float
    doe_mm: tuple[float, ...]
    authority_status: str
    application_status: str = "BOUNDARY_UNRESOLVED_UNTIL_DEDICATED_NASAL_SUBSYSTEM"

    def __post_init__(self) -> None:
        center = float(self.center_thickness_mm)
        doe = tuple(float(value) for value in self.doe_mm)
        if not math.isfinite(center) or center <= 0.0:
            raise InterfaceTopologyError("Nasal-lobe center thickness must be finite and positive")
        if not doe or any(not math.isfinite(value) or value <= 0.0 for value in doe):
            raise InterfaceTopologyError("Nasal-lobe DOE must contain finite positive values")
        if center not in doe:
            raise InterfaceTopologyError("Nasal-lobe center thickness must be represented in the authority DOE")
        if not self.authority_status.strip() or not self.application_status.strip():
            raise InterfaceTopologyError("Nasal-lobe thickness status fields must be explicit")
        object.__setattr__(self, "center_thickness_mm", center)
        object.__setattr__(self, "doe_mm", doe)

    def manifest(self) -> dict[str, object]:
        return {
            "center_thickness_mm": self.center_thickness_mm,
            "doe_mm": list(self.doe_mm),
            "authority_status": self.authority_status,
            "application_status": self.application_status,
        }


@dataclass(frozen=True, slots=True)
class InterfaceTriangleAssignment:
    triangle_index: int
    coverage_region_id: str
    parameter_zone_id: str
    area_mm2: float
    contact_intent: bool
    protected_opening: bool

    def __post_init__(self) -> None:
        if self.triangle_index < 0:
            raise InterfaceTopologyError("triangle_index cannot be negative")
        if not self.coverage_region_id.strip() or not self.parameter_zone_id.strip():
            raise InterfaceTopologyError("Triangle assignments require explicit region and zone IDs")
        area = float(self.area_mm2)
        if not math.isfinite(area) or area <= 0.0:
            raise InterfaceTopologyError("Triangle assignment area must be finite and positive")
        object.__setattr__(self, "area_mm2", area)
        if self.contact_intent == self.protected_opening:
            raise InterfaceTopologyError(
                "Every interface triangle must be exactly one of contact-intent or protected-opening"
            )


@dataclass(frozen=True, slots=True)
class CompliantInterfaceTopology:
    source_surface_id: str
    source_surface_sha256: str
    coverage_segmentation_sha256: str
    zones: tuple[InterfaceParameterZone, ...]
    assignments: tuple[InterfaceTriangleAssignment, ...]
    nasal_lobe_thickness_authority: NasalLobeThicknessAuthority
    topology_status: str
    evidence_status: str
    anatomical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for label, value in {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "coverage_segmentation_sha256": self.coverage_segmentation_sha256,
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
        }.items():
            if not str(value).strip():
                raise InterfaceTopologyError(f"{label} must be non-empty")
        for digest in (self.source_surface_sha256, self.coverage_segmentation_sha256):
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.lower()):
                raise InterfaceTopologyError("Source hashes must be 64-character hexadecimal SHA-256 digests")
        if self.anatomical_validation_eligible:
            raise InterfaceTopologyError(
                "Iteration-10 topology cannot be promoted to anatomical/contact validation evidence"
            )
        if not self.zones or not self.assignments:
            raise InterfaceTopologyError("Interface topology requires zones and triangle assignments")
        zone_ids = [zone.zone_id for zone in self.zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise InterfaceTopologyError("Interface parameter-zone IDs must be unique")
        indices = [assignment.triangle_index for assignment in self.assignments]
        if indices != list(range(len(self.assignments))):
            raise InterfaceTopologyError("Interface assignments must be contiguous and deterministic")
        known = set(zone_ids)
        unknown = {assignment.parameter_zone_id for assignment in self.assignments} - known
        if unknown:
            raise InterfaceTopologyError(f"Assignments reference unknown parameter zones: {sorted(unknown)}")

    @property
    def zone_by_id(self) -> dict[str, InterfaceParameterZone]:
        return {zone.zone_id: zone for zone in self.zones}

    @property
    def contact_assignments(self) -> tuple[InterfaceTriangleAssignment, ...]:
        return tuple(item for item in self.assignments if item.contact_intent)

    @property
    def protected_assignments(self) -> tuple[InterfaceTriangleAssignment, ...]:
        return tuple(item for item in self.assignments if item.protected_opening)

    @property
    def contact_area_mm2(self) -> float:
        return sum(item.area_mm2 for item in self.contact_assignments)

    @property
    def protected_opening_area_mm2(self) -> float:
        return sum(item.area_mm2 for item in self.protected_assignments)

    @property
    def t_zone_contact_area_mm2(self) -> float:
        return sum(
            item.area_mm2
            for item in self.contact_assignments
            if item.parameter_zone_id in {ZONE_T_FOREHEAD, ZONE_T_NOSE_PHILTRUM}
        )

    @property
    def parameter_zone_area_mm2(self) -> dict[str, float]:
        areas: dict[str, float] = defaultdict(float)
        for item in self.assignments:
            areas[item.parameter_zone_id] += item.area_mm2
        return dict(sorted(areas.items()))

    def contact_component_count(self, coverage: FacialCoverageMesh) -> int:
        """Count edge-connected contact components without inventing geometric thickness."""

        contact_ids = {item.triangle_index for item in self.contact_assignments}
        triangle_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
        if set(triangle_by_id) != set(range(len(self.assignments))):
            raise InterfaceTopologyError("Coverage and interface triangle indices are inconsistent")

        edge_to_triangles: dict[tuple[int, int], list[int]] = defaultdict(list)
        for triangle_id in contact_ids:
            a, b, c = triangle_by_id[triangle_id].vertex_indices
            for u, v in ((a, b), (b, c), (c, a)):
                edge_to_triangles[tuple(sorted((u, v)))].append(triangle_id)

        adjacency: dict[int, set[int]] = {triangle_id: set() for triangle_id in contact_ids}
        for incident in edge_to_triangles.values():
            for source in incident:
                for destination in incident:
                    if source != destination:
                        adjacency[source].add(destination)

        remaining = set(contact_ids)
        components = 0
        while remaining:
            components += 1
            start = min(remaining)
            queue: deque[int] = deque([start])
            remaining.remove(start)
            while queue:
                current = queue.popleft()
                for neighbor in sorted(adjacency[current]):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
        return components

    @property
    def topology_sha256(self) -> str:
        payload = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "coverage_segmentation_sha256": self.coverage_segmentation_sha256,
            "zones": [zone.manifest() for zone in self.zones],
            "assignments": [
                [
                    item.triangle_index,
                    item.coverage_region_id,
                    item.parameter_zone_id,
                    round(item.area_mm2, 12),
                    item.contact_intent,
                    item.protected_opening,
                ]
                for item in self.assignments
            ],
            "nasal_lobe_thickness_authority": self.nasal_lobe_thickness_authority.manifest(),
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, coverage: FacialCoverageMesh | None = None) -> dict[str, object]:
        result: dict[str, object] = {
            "source_surface_id": self.source_surface_id,
            "source_surface_sha256": self.source_surface_sha256,
            "coverage_segmentation_sha256": self.coverage_segmentation_sha256,
            "zone_count": len(self.zones),
            "triangle_assignment_count": len(self.assignments),
            "contact_triangle_count": len(self.contact_assignments),
            "protected_triangle_count": len(self.protected_assignments),
            "contact_area_mm2": self.contact_area_mm2,
            "protected_opening_area_mm2": self.protected_opening_area_mm2,
            "t_zone_contact_area_mm2": self.t_zone_contact_area_mm2,
            "parameter_zone_area_mm2": self.parameter_zone_area_mm2,
            "nasal_lobe_thickness_authority": self.nasal_lobe_thickness_authority.manifest(),
            "topology_status": self.topology_status,
            "evidence_status": self.evidence_status,
            "anatomical_validation_eligible": self.anatomical_validation_eligible,
            "topology_sha256": self.topology_sha256,
        }
        if coverage is not None:
            result["contact_component_count"] = self.contact_component_count(coverage)
        return result


def _build_parameter_zones() -> tuple[InterfaceParameterZone, ...]:
    contact_common = {
        "contact_intent": True,
        "cleansing_target": True,
        "nominal_thickness_mm": None,
        "thickness_doe_mm": (),
        "material_status": "UNSELECTED_VALIDATION_GATED",
        "geometry_status": "TOPOLOGY_ONLY_DEVELOPMENT_BASELINE",
        "evidence_status": "FUNCTIONAL_ZONE_ONLY_NOT_CONTACT_OR_EFFICACY_VALIDATION",
    }
    opening_common = {
        "contact_intent": False,
        "cleansing_target": False,
        "nominal_thickness_mm": None,
        "thickness_doe_mm": (),
        "thickness_status": "NO_INTERFACE_MATERIAL_PROTECTED_OPENING",
        "material_status": "NOT_APPLICABLE_PROTECTED_OPENING",
        "geometry_status": "PROTECTED_OPENING_TOPOLOGY",
        "evidence_status": "SAFETY_EXCLUSION_TOPOLOGY_ONLY_DYNAMIC_3D_STILL_BLOCKED",
    }

    return (
        InterfaceParameterZone(
            ZONE_GENERAL_FACE,
            "primary compliant skin-contact cleansing field",
            (REGION_ACTIVE_OTHER,),
            thickness_status="UNRESOLVED_PENDING_INTERFACE_GEOMETRY_AND_MATERIAL_SELECTION",
            **contact_common,
        ),
        InterfaceParameterZone(
            ZONE_T_FOREHEAD,
            "forehead T-zone skin-contact cleansing field",
            (REGION_T_FOREHEAD,),
            thickness_status="UNRESOLVED_PENDING_INTERFACE_GEOMETRY_AND_MATERIAL_SELECTION",
            **contact_common,
        ),
        InterfaceParameterZone(
            ZONE_T_NOSE_PHILTRUM,
            "central T-zone and nose-to-upper-lip cleansing target field",
            (REGION_T_NOSE_PHILTRUM,),
            thickness_status="DEDICATED_NASAL_SUBSYSTEM_BOUNDARY_REQUIRED_BEFORE_THICKNESS_APPLICATION",
            **contact_common,
        ),
        InterfaceParameterZone(
            ZONE_OPENING_EYE_LEFT,
            "left eye protected opening",
            (REGION_PROTECTED_EYE_LEFT,),
            **opening_common,
        ),
        InterfaceParameterZone(
            ZONE_OPENING_EYE_RIGHT,
            "right eye protected opening",
            (REGION_PROTECTED_EYE_RIGHT,),
            **opening_common,
        ),
        InterfaceParameterZone(
            ZONE_OPENING_MOUTH,
            "mouth protected opening",
            (REGION_PROTECTED_MOUTH,),
            **opening_common,
        ),
        InterfaceParameterZone(
            ZONE_OPENING_NOSTRIL_LEFT,
            "left nostril/airway protected opening",
            (REGION_PROTECTED_NOSTRIL_LEFT,),
            **opening_common,
        ),
        InterfaceParameterZone(
            ZONE_OPENING_NOSTRIL_RIGHT,
            "right nostril/airway protected opening",
            (REGION_PROTECTED_NOSTRIL_RIGHT,),
            **opening_common,
        ),
    )


def build_compliant_interface_topology(
    authority: Authority,
    coverage: FacialCoverageMesh,
) -> CompliantInterfaceTopology:
    """Create the main interface topology without fabricating thickness/material/contact truth.

    Iteration 10 establishes exactly where the interface is intended to contact/cleanse
    and where material must not occupy protected openings. The authority's 0.30 mm nasal
    lobe center thickness and 0.25/0.30/0.35 mm DOE are preserved as subsystem parameters,
    but are deliberately *not* painted across the full T-zone because the dedicated nasal
    saddle boundary is an Iteration-11 closure item.
    """

    zones = _build_parameter_zones()
    region_to_zone: dict[str, InterfaceParameterZone] = {}
    for zone in zones:
        for region_id in zone.coverage_region_ids:
            if region_id in region_to_zone:
                raise InterfaceTopologyError(f"Coverage region {region_id!r} maps to multiple interface zones")
            region_to_zone[region_id] = zone

    assignments: list[InterfaceTriangleAssignment] = []
    for triangle in coverage.triangles:
        try:
            zone = region_to_zone[triangle.region_id]
        except KeyError as exc:
            raise InterfaceTopologyError(
                f"Coverage region {triangle.region_id!r} has no interface parameter-zone mapping"
            ) from exc
        if zone.contact_intent != triangle.is_target:
            raise InterfaceTopologyError(
                f"Triangle {triangle.triangle_index} target/contact intent mismatch for {triangle.region_id}"
            )
        assignments.append(
            InterfaceTriangleAssignment(
                triangle_index=triangle.triangle_index,
                coverage_region_id=triangle.region_id,
                parameter_zone_id=zone.zone_id,
                area_mm2=triangle.area_mm2,
                contact_intent=zone.contact_intent,
                protected_opening=not zone.contact_intent,
            )
        )

    nasal = NasalLobeThicknessAuthority(
        center_thickness_mm=authority.number("geometry", "nasal_lobe_membrane", "thickness_center_mm"),
        doe_mm=tuple(float(value) for value in authority.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm")),
        authority_status=str(authority.get("geometry", "nasal_lobe_membrane", "status")),
    )

    topology = CompliantInterfaceTopology(
        source_surface_id=coverage.source_surface_id,
        source_surface_sha256=coverage.source_surface_sha256,
        coverage_segmentation_sha256=coverage.segmentation_sha256,
        zones=zones,
        assignments=tuple(assignments),
        nasal_lobe_thickness_authority=nasal,
        topology_status="PHASE2_ITERATION10_FUNCTIONAL_TOPOLOGY_BASELINE",
        evidence_status="DETERMINISTIC_TOPOLOGY_ONLY_NOT_CONTACT_FIT_MATERIAL_OR_EFFICACY_EVIDENCE",
        anatomical_validation_eligible=False,
    )

    if len(topology.assignments) != len(coverage.triangles):
        raise InterfaceTopologyError("Interface topology did not assign every coverage triangle exactly once")
    if abs(topology.contact_area_mm2 - coverage.target_area_mm2) > 1e-8:
        raise InterfaceTopologyError("Interface contact area must exactly conserve coverage target area")
    if abs(topology.protected_opening_area_mm2 - coverage.protected_area_mm2) > 1e-8:
        raise InterfaceTopologyError("Interface protected area must exactly conserve coverage protected area")
    return topology
