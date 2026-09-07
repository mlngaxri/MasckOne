from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
from typing import Iterable

import cadquery as cq

from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import (
    InterfaceAttachmentArchitecture,
    build_interface_attachment_architecture,
)
from .model import MasckOneModel, build_model
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology


SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_REALIZATION_V1"
SOURCE_MAIN_SHA = "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc"
AUTHORITY_REVISION = "2026-08-30-R1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
MEMBER_ID = "MASCK_ONE-FRAME-MEMBER-PERIMETER-REACTION-LOOP-V1"

# This is donor evidence, not authority and not a structural-performance claim. The
# legacy Manual A / PR #63 frame used 2.4 mm axial depth; Cell 6 retains only that
# bounded dimension as a provisional CAD seed while replacing its overlap-based
# attachment and unsourced radial member with current-main source geometry.
AXIAL_DEPTH_SEED_MM = 2.4
AXIAL_DEPTH_PROVENANCE = (
    "LEGACY_PR63_DONOR_DIMENSION_SEED_ONLY_NOT_AUTHORITY_OR_STRENGTH_EVIDENCE"
)

# A deterministic digital packaging margin used only to keep the first member B-rep
# posterior of the current waste-cartridge package reference. It is not a tolerance,
# process capability, service clearance, or physical requirement.
PACKAGE_CLEARANCE_SEED_MM = 1.0
PACKAGE_CLEARANCE_PROVENANCE = (
    "CELL6_DIGITAL_PACKAGING_SEED_NOT_AUTHORITY_TOLERANCE_OR_PHYSICAL_EVIDENCE"
)

GEOMETRY_ROLE = "INTENDED_PHYSICAL_STRUCTURAL_MEMBER_MATERIAL_UNSELECTED"
CAPTURE_SEMANTICS = "INNER_EDGE_COINCIDENT_WITH_EXACT_RELEASED_ATTACHMENT_OUTER_PERIMETER"
OUTER_PROFILE_SEMANTICS = "AUTHORITY_OUTER_XY_ENVELOPE_BOUND"
CROSS_SECTION_INTENT = (
    "VARIABLE_IN_PLANE_REACTION_BAND_BETWEEN_EXACT_ATTACHMENT_PERIMETER_AND_"
    "AUTHORITY_OUTER_ENVELOPE_WITH_PROVISIONAL_AXIAL_DEPTH"
)
FRAME_SHELL_JOIN_STATUS = "UNRESOLVED_NO_OVERLAP_AS_ATTACHMENT"
ACTUATOR_REACTION_STATUS = (
    "UNRESOLVED_CURRENT_MAIN_ACTUATOR_STRUCTURAL_MOUNT_DATUMS_AND_COUPLING_GEOMETRY_ABSENT"
)
RETENTION_ROOT_STATUS = "UNRESOLVED_NO_CURRENT_MAIN_POSITIVE_RETENTION_ROOT_COUNTERPART_GEOMETRY"
SERVICE_TOOL_ACCESS_STATUS = "UNRESOLVED_PENDING_FRAME_SHELL_JOIN_AND_LOCAL_INTERFACE_FEATURES"
ASSEMBLY_STATUS = (
    "STANDALONE_FRAME_MEMBER_BREP_ONLY_NOT_YET_JOINED_TO_CURRENT_PHYSICAL_ASSEMBLY"
)
EVIDENCE_STATUS = (
    "DIGITAL_CURRENT_MAIN_SOURCE_BOUND_BREP_ONLY_NOT_MATERIAL_STRENGTH_STIFFNESS_MODAL_"
    "FATIGUE_TOOLING_TOLERANCE_ASSEMBLY_SERVICE_RETENTION_FIT_OR_PHYSICAL_VALIDATION"
)

# Direct source graph required to reconstruct the released perimeter capture, model
# package references, hard protected envelopes, and Iteration-15 topology consumed here.
SOURCE_GIT_BLOB_IDENTITIES: tuple[tuple[str, str], ...] = (
    ("config/masck_one_authority.yaml", "2608dda483b995539de422290371c219668a1527"),
    ("src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("src/masck_one/interface_boundaries.py", "496c9b50867ca0bb319175d1d2e47caf4bc4fb64"),
    ("src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("src/masck_one/nasal_subsystem.py", "f1f22b828d0465636579fc31eff0bfb6a6bf2507"),
    ("src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GIT_SHA_RE_LENGTH = 40
_SHA256_LENGTH = 64
_GEOMETRY_DECIMALS = 8
_BREP_BOUND_TOLERANCE_MM = 2e-6
_INTERSECTION_VOLUME_TOLERANCE_MM3 = 1e-7
_CLEARANCE_TOLERANCE_MM = 1e-6


class StructuralFrameRealizationError(ValueError):
    """Raised when the current-main structural frame B-rep contract is stale or invalid."""


def _nonblank(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise StructuralFrameRealizationError(f"{label} must be exact nonblank text")
    return value


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StructuralFrameRealizationError(f"{label} must be a real numeric value")
    number = float(value)
    if not math.isfinite(number):
        raise StructuralFrameRealizationError(f"{label} must be finite")
    return number


def _canonical_sha(value: object, *, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise StructuralFrameRealizationError(
            f"{label} must be lowercase canonical hexadecimal with length {length}"
        )
    return value


def _quantized(value: object, *, label: str) -> float:
    number = _finite(value, label=label)
    rounded = round(number, _GEOMETRY_DECIMALS)
    return 0.0 if rounded == 0.0 else rounded


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def _require_source_files_current() -> None:
    seen: set[str] = set()
    for relative_path, expected_sha in SOURCE_GIT_BLOB_IDENTITIES:
        _nonblank(relative_path, label="source path")
        _canonical_sha(expected_sha, length=_GIT_SHA_RE_LENGTH, label="source git blob SHA")
        if relative_path in seen:
            raise StructuralFrameRealizationError(
                f"duplicate structural-frame source binding: {relative_path}"
            )
        seen.add(relative_path)
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise StructuralFrameRealizationError(
                f"structural-frame source file is missing: {relative_path}"
            )
        actual_sha = _git_blob_sha(path)
        if actual_sha != expected_sha:
            raise StructuralFrameRealizationError(
                f"structural-frame source moved at {relative_path}; "
                f"expected {expected_sha}, got {actual_sha}"
            )


@dataclass(frozen=True, slots=True)
class ClearanceRecord:
    target_id: str
    target_role: str
    source_status: str
    intersection_volume_mm3: float
    minimum_distance_mm: float

    def __post_init__(self) -> None:
        _nonblank(self.target_id, label="clearance target id")
        _nonblank(self.target_role, label="clearance target role")
        _nonblank(self.source_status, label="clearance source status")
        intersection = _finite(
            self.intersection_volume_mm3, label="intersection volume"
        )
        distance = _finite(self.minimum_distance_mm, label="minimum distance")
        if intersection < 0.0 or distance < 0.0:
            raise StructuralFrameRealizationError(
                "clearance measurements cannot be negative"
            )
        if intersection > _INTERSECTION_VOLUME_TOLERANCE_MM3:
            raise StructuralFrameRealizationError(
                f"unexplained structural-frame intersection with {self.target_id}: "
                f"{intersection} mm^3"
            )
        if distance <= _CLEARANCE_TOLERANCE_MM:
            raise StructuralFrameRealizationError(
                f"structural-frame target {self.target_id} touches or lacks positive clearance"
            )
        object.__setattr__(self, "intersection_volume_mm3", intersection)
        object.__setattr__(self, "minimum_distance_mm", distance)

    def manifest(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "target_role": self.target_role,
            "source_status": self.source_status,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameRealization:
    source_structural_frame_sha256: str
    source_attachment_topology_sha256: str
    source_registered_mesh_sha256: str
    source_capture_path_sha256: str
    source_capture_edge_indices: tuple[int, ...]
    source_capture_vertex_count: int
    source_capture_path_length_mm: float
    outer_xy_envelope_mm: tuple[float, float]
    axial_depth_mm: float
    z_range_mm: tuple[float, float]
    current_waste_package_zmin_mm: float
    geometry_measurements: tuple[tuple[str, object], ...]
    geometry_sha256: str
    component_clearances: tuple[ClearanceRecord, ...]
    protected_clearances: tuple[ClearanceRecord, ...]
    material_selection: str | None
    physical_validation_eligible: bool
    coordinate_frame_id: str = WORLD_FRAME_ID
    member_id: str = MEMBER_ID
    geometry_role: str = GEOMETRY_ROLE
    capture_semantics: str = CAPTURE_SEMANTICS
    outer_profile_semantics: str = OUTER_PROFILE_SEMANTICS
    cross_section_intent: str = CROSS_SECTION_INTENT
    axial_depth_provenance: str = AXIAL_DEPTH_PROVENANCE
    package_clearance_seed_mm: float = PACKAGE_CLEARANCE_SEED_MM
    package_clearance_provenance: str = PACKAGE_CLEARANCE_PROVENANCE
    frame_shell_join_status: str = FRAME_SHELL_JOIN_STATUS
    actuator_reaction_status: str = ACTUATOR_REACTION_STATUS
    retention_root_status: str = RETENTION_ROOT_STATUS
    service_tool_access_status: str = SERVICE_TOOL_ACCESS_STATUS
    assembly_status: str = ASSEMBLY_STATUS
    evidence_status: str = EVIDENCE_STATUS
    solid: cq.Workplane = field(repr=False, compare=False, default=None)

    def __post_init__(self) -> None:
        for label, digest in (
            ("source structural-frame topology SHA", self.source_structural_frame_sha256),
            ("source attachment topology SHA", self.source_attachment_topology_sha256),
            ("source registered-mesh SHA", self.source_registered_mesh_sha256),
            ("source capture-path SHA", self.source_capture_path_sha256),
            ("geometry SHA", self.geometry_sha256),
        ):
            _canonical_sha(digest, length=_SHA256_LENGTH, label=label)
        if self.coordinate_frame_id != WORLD_FRAME_ID:
            raise StructuralFrameRealizationError(
                "structural frame realization is not in the canonical authority world frame"
            )
        if self.member_id != MEMBER_ID or self.geometry_role != GEOMETRY_ROLE:
            raise StructuralFrameRealizationError(
                "structural frame member identity/geometry role drifted"
            )
        if self.capture_semantics != CAPTURE_SEMANTICS:
            raise StructuralFrameRealizationError(
                "structural frame no longer preserves the exact released capture path"
            )
        if self.outer_profile_semantics != OUTER_PROFILE_SEMANTICS:
            raise StructuralFrameRealizationError(
                "structural frame outer-profile semantics drifted"
            )
        if self.cross_section_intent != CROSS_SECTION_INTENT:
            raise StructuralFrameRealizationError(
                "structural frame cross-section intent drifted"
            )
        if self.axial_depth_provenance != AXIAL_DEPTH_PROVENANCE:
            raise StructuralFrameRealizationError(
                "structural frame axial-depth provenance drifted"
            )
        package_seed = _finite(
            self.package_clearance_seed_mm, label="package clearance seed"
        )
        if not math.isclose(
            package_seed, PACKAGE_CLEARANCE_SEED_MM, rel_tol=0.0, abs_tol=1e-12
        ):
            raise StructuralFrameRealizationError(
                "structural frame package-clearance seed drifted"
            )
        if self.package_clearance_provenance != PACKAGE_CLEARANCE_PROVENANCE:
            raise StructuralFrameRealizationError(
                "structural frame package-clearance provenance drifted"
            )
        if (
            self.frame_shell_join_status != FRAME_SHELL_JOIN_STATUS
            or self.actuator_reaction_status != ACTUATOR_REACTION_STATUS
            or self.retention_root_status != RETENTION_ROOT_STATUS
            or self.service_tool_access_status != SERVICE_TOOL_ACCESS_STATUS
            or self.assembly_status != ASSEMBLY_STATUS
        ):
            raise StructuralFrameRealizationError(
                "unresolved downstream structural-interface status was silently promoted"
            )
        if self.material_selection is not None:
            raise StructuralFrameRealizationError(
                "frame material cannot be selected without controlled evidence"
            )
        if type(self.physical_validation_eligible) is not bool:
            raise StructuralFrameRealizationError(
                "physical-validation eligibility must be an exact bool"
            )
        if self.physical_validation_eligible:
            raise StructuralFrameRealizationError(
                "digital frame B-rep cannot be physical-validation evidence"
            )
        if self.evidence_status != EVIDENCE_STATUS:
            raise StructuralFrameRealizationError(
                "structural frame evidence status drifted"
            )
        if (
            not self.source_capture_edge_indices
            or tuple(sorted(self.source_capture_edge_indices))
            != self.source_capture_edge_indices
            or len(set(self.source_capture_edge_indices))
            != len(self.source_capture_edge_indices)
        ):
            raise StructuralFrameRealizationError(
                "source capture edge identities must be unique, sorted, and nonempty"
            )
        if (
            isinstance(self.source_capture_vertex_count, bool)
            or not isinstance(self.source_capture_vertex_count, int)
            or self.source_capture_vertex_count < 3
        ):
            raise StructuralFrameRealizationError(
                "source capture path requires at least three vertices"
            )
        path_length = _finite(
            self.source_capture_path_length_mm, label="source capture path length"
        )
        if path_length <= 0.0:
            raise StructuralFrameRealizationError(
                "source capture path length must be positive"
            )
        outer_w, outer_h = (
            _finite(value, label="outer XY envelope")
            for value in self.outer_xy_envelope_mm
        )
        if outer_w <= 0.0 or outer_h <= 0.0:
            raise StructuralFrameRealizationError(
                "outer XY envelope must be positive"
            )
        depth = _finite(self.axial_depth_mm, label="axial depth")
        if depth <= 0.0 or not math.isclose(
            depth, AXIAL_DEPTH_SEED_MM, rel_tol=0.0, abs_tol=1e-12
        ):
            raise StructuralFrameRealizationError(
                "axial depth must remain the explicit donor-derived provisional seed"
            )
        if len(self.z_range_mm) != 2:
            raise StructuralFrameRealizationError("frame z range must contain two values")
        z_min, z_max = (
            _finite(value, label="frame z range") for value in self.z_range_mm
        )
        if z_min >= z_max or not math.isclose(
            z_max - z_min, depth, rel_tol=0.0, abs_tol=1e-9
        ):
            raise StructuralFrameRealizationError(
                "frame z range must match the authored axial depth"
            )
        waste_zmin = _finite(
            self.current_waste_package_zmin_mm, label="waste package z minimum"
        )
        if not math.isclose(
            z_max,
            waste_zmin - PACKAGE_CLEARANCE_SEED_MM,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise StructuralFrameRealizationError(
                "frame posterior placement no longer preserves the explicit waste-package margin"
            )
        if not self.geometry_measurements:
            raise StructuralFrameRealizationError(
                "frame geometry measurements cannot be empty"
            )
        measurement_keys = [key for key, _ in self.geometry_measurements]
        if measurement_keys != sorted(measurement_keys) or len(set(measurement_keys)) != len(
            measurement_keys
        ):
            raise StructuralFrameRealizationError(
                "frame geometry measurements must be uniquely sorted"
            )
        if not self.component_clearances or not self.protected_clearances:
            raise StructuralFrameRealizationError(
                "frame realization requires component and protected-envelope collision screens"
            )
        if type(self.solid) is not cq.Workplane:
            raise StructuralFrameRealizationError(
                "frame realization must retain exact CadQuery Workplane geometry"
            )
        shape = self.solid.val()
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise StructuralFrameRealizationError(
                "frame realization must be one valid B-rep solid"
            )

    @property
    def realization_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.__post_init__()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "authored_against_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "source_git_blob_identities": [
                {"path": path, "git_blob_sha": digest}
                for path, digest in SOURCE_GIT_BLOB_IDENTITIES
            ],
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "source_attachment_topology_sha256": self.source_attachment_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "source_capture_path_sha256": self.source_capture_path_sha256,
            "source_capture_edge_indices": list(self.source_capture_edge_indices),
            "source_capture_vertex_count": self.source_capture_vertex_count,
            "source_capture_path_length_mm": self.source_capture_path_length_mm,
            "coordinate_frame_id": self.coordinate_frame_id,
            "member_id": self.member_id,
            "geometry_role": self.geometry_role,
            "capture_semantics": self.capture_semantics,
            "outer_profile_semantics": self.outer_profile_semantics,
            "outer_xy_envelope_mm": list(self.outer_xy_envelope_mm),
            "cross_section_intent": self.cross_section_intent,
            "axial_depth_mm": self.axial_depth_mm,
            "axial_depth_provenance": self.axial_depth_provenance,
            "z_range_mm": list(self.z_range_mm),
            "current_waste_package_zmin_mm": self.current_waste_package_zmin_mm,
            "package_clearance_seed_mm": self.package_clearance_seed_mm,
            "package_clearance_provenance": self.package_clearance_provenance,
            "material_selection": self.material_selection,
            "frame_shell_join_status": self.frame_shell_join_status,
            "actuator_reaction_status": self.actuator_reaction_status,
            "retention_root_status": self.retention_root_status,
            "service_tool_access_status": self.service_tool_access_status,
            "assembly_status": self.assembly_status,
            "geometry_measurements": dict(self.geometry_measurements),
            "geometry_sha256": self.geometry_sha256,
            "component_clearances": [
                record.manifest() for record in self.component_clearances
            ],
            "protected_clearances": [
                record.manifest() for record in self.protected_clearances
            ],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["realization_sha256"] = self.realization_sha256
        return payload


def _current_attachment_and_frame(
    model: MasckOneModel,
) -> tuple[InterfaceAttachmentArchitecture, StructuralFrameTopology]:
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    return attachment, frame


def _ordered_capture_cycle(
    model: MasckOneModel,
    attachment: InterfaceAttachmentArchitecture,
    structural_frame: StructuralFrameTopology,
) -> tuple[tuple[int, ...], tuple[tuple[float, float, float], ...]]:
    expected_edges = structural_frame.perimeter_reaction_path.source_attachment_edge_indices
    actual_edges = tuple(
        assignment.source_boundary_edge_index for assignment in attachment.assignments
    )
    if actual_edges != expected_edges:
        raise StructuralFrameRealizationError(
            "structural frame perimeter reaction path moved from the exact attachment edge graph"
        )

    vertices = model.facial_surface.mesh.vertices
    adjacency: dict[int, list[int]] = defaultdict(list)
    source_pairs: set[tuple[int, int]] = set()
    for assignment in attachment.assignments:
        a, b = assignment.vertex_indices
        if a >= len(vertices) or b >= len(vertices):
            raise StructuralFrameRealizationError(
                "attachment perimeter references a missing facial-surface vertex"
            )
        pair = (a, b)
        if pair in source_pairs:
            raise StructuralFrameRealizationError(
                "attachment perimeter contains a duplicate vertex edge"
            )
        source_pairs.add(pair)
        pa, pb = vertices[a], vertices[b]
        measured = math.dist(pa.as_tuple(), pb.as_tuple())
        if not math.isclose(
            measured, assignment.length_mm, rel_tol=0.0, abs_tol=1e-9
        ):
            raise StructuralFrameRealizationError(
                "attachment edge length no longer matches source mesh coordinates"
            )
        adjacency[a].append(b)
        adjacency[b].append(a)

    if not adjacency or any(len(neighbors) != 2 for neighbors in adjacency.values()):
        raise StructuralFrameRealizationError(
            "attachment perimeter must be exactly one degree-2 closed cycle"
        )

    start = min(adjacency)
    ordered: list[int] = [start]
    previous: int | None = None
    current = start
    while True:
        neighbors = sorted(adjacency[current])
        next_vertex = neighbors[0] if neighbors[0] != previous else neighbors[1]
        if next_vertex == start:
            break
        if next_vertex in ordered:
            raise StructuralFrameRealizationError(
                "attachment perimeter self-revisits before closing"
            )
        ordered.append(next_vertex)
        previous, current = current, next_vertex

    if len(ordered) != len(adjacency):
        raise StructuralFrameRealizationError(
            "attachment perimeter contains more than one disconnected cycle"
        )

    points = tuple(vertices[index].as_tuple() for index in ordered)
    if any(not all(math.isfinite(float(value)) for value in point) for point in points):
        raise StructuralFrameRealizationError(
            "attachment perimeter contains nonfinite source coordinates"
        )
    z_values = [float(point[2]) for point in points]
    if max(z_values) - min(z_values) > 1e-12:
        raise StructuralFrameRealizationError(
            "first frame B-rep is planar-current-main only; nonplanar source perimeter requires a new 3D realization"
        )

    def signed_xy_area(cycle: Iterable[tuple[float, float, float]]) -> float:
        cycle = tuple(cycle)
        return 0.5 * sum(
            cycle[index][0] * cycle[(index + 1) % len(cycle)][1]
            - cycle[(index + 1) % len(cycle)][0] * cycle[index][1]
            for index in range(len(cycle))
        )

    if signed_xy_area(points) < 0.0:
        ordered.reverse()
        min_position = ordered.index(min(ordered))
        ordered = ordered[min_position:] + ordered[:min_position]
        points = tuple(vertices[index].as_tuple() for index in ordered)
    if signed_xy_area(points) <= 0.0:
        raise StructuralFrameRealizationError(
            "attachment perimeter does not form a positive-area planar capture cycle"
        )

    return tuple(ordered), tuple(
        (float(point[0]), float(point[1]), float(point[2])) for point in points
    )


def _capture_path_sha256(
    ordered_vertex_indices: tuple[int, ...],
    ordered_points: tuple[tuple[float, float, float], ...],
) -> str:
    payload = [
        {
            "vertex_index": vertex_index,
            "xyz_mm": [
                _quantized(point[0], label="capture point x"),
                _quantized(point[1], label="capture point y"),
                _quantized(point[2], label="capture point z"),
            ],
        }
        for vertex_index, point in zip(ordered_vertex_indices, ordered_points, strict=True)
    ]
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _build_member_solid(
    *,
    ordered_points: tuple[tuple[float, float, float], ...],
    outer_xy_envelope_mm: tuple[float, float],
    z_min_mm: float,
    axial_depth_mm: float,
) -> cq.Workplane:
    outer_w, outer_h = outer_xy_envelope_mm
    for x, y, _ in ordered_points:
        normalized = (x / (outer_w / 2.0)) ** 2 + (y / (outer_h / 2.0)) ** 2
        if normalized >= 1.0 - 1e-12:
            raise StructuralFrameRealizationError(
                "released capture perimeter is no longer strictly inside the authority outer envelope"
            )

    outer_wire = (
        cq.Workplane("XY")
        .ellipse(outer_w / 2.0, outer_h / 2.0)
        .val()
    )
    inner_wire = (
        cq.Workplane("XY")
        .polyline(tuple((x, y) for x, y, _ in ordered_points))
        .close()
        .val()
    )
    if not outer_wire.isValid() or not inner_wire.isValid():
        raise StructuralFrameRealizationError(
            "structural frame source profiles did not produce valid wires"
        )

    shape = cq.Solid.extrudeLinear(
        outer_wire,
        [inner_wire],
        (0.0, 0.0, axial_depth_mm),
    ).translate((0.0, 0.0, z_min_mm))
    solid = cq.Workplane(obj=shape)
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise StructuralFrameRealizationError(
            "structural frame reaction loop did not produce one valid B-rep solid"
        )
    horizontal_faces = [
        face
        for face in shape.Faces()
        if face.geomType() == "PLANE"
        and abs(abs(float(face.normalAt().z)) - 1.0) <= 1e-9
    ]
    if len(horizontal_faces) < 2 or max(len(face.Wires()) for face in horizontal_faces) < 2:
        raise StructuralFrameRealizationError(
            "structural frame reaction loop lost its source-bound central capture opening"
        )
    return solid


def _geometry_measurements(solid: cq.Workplane) -> tuple[tuple[str, object], ...]:
    shape = solid.val()
    bounds = shape.BoundingBox()
    measurements: dict[str, object] = {
        "area_mm2": _quantized(shape.Area(), label="frame area"),
        "bbox_mm": [
            _quantized(value, label="frame bounding box")
            for value in (
                bounds.xmin,
                bounds.ymin,
                bounds.zmin,
                bounds.xmax,
                bounds.ymax,
                bounds.zmax,
            )
        ],
        "edge_count": len(shape.Edges()),
        "face_count": len(shape.Faces()),
        "solid_count": len(shape.Solids()),
        "vertex_count": len(shape.Vertices()),
        "volume_mm3": _quantized(shape.Volume(), label="frame volume"),
    }
    return tuple(sorted(measurements.items()))


def _geometry_sha256(
    *,
    source_capture_path_sha256: str,
    outer_xy_envelope_mm: tuple[float, float],
    axial_depth_mm: float,
    z_range_mm: tuple[float, float],
    geometry_measurements: tuple[tuple[str, object], ...],
) -> str:
    payload = {
        "schema": SCHEMA,
        "member_id": MEMBER_ID,
        "capture_path_sha256": source_capture_path_sha256,
        "outer_xy_envelope_mm": list(outer_xy_envelope_mm),
        "axial_depth_mm": axial_depth_mm,
        "z_range_mm": list(z_range_mm),
        "measurements": dict(geometry_measurements),
    }
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _intersection_volume(left: cq.Workplane, right: cq.Workplane) -> float:
    return max(0.0, float(left.intersect(right).val().Volume()))


def _minimum_distance(left: cq.Workplane, right: cq.Workplane) -> float:
    return max(0.0, float(left.val().distance(right.val())))


def _component_role(name: str) -> str:
    if name == "rigid_shell":
        return "CURRENT_MAIN_PHYSICAL_MATERIAL"
    if name.startswith("visual_"):
        return "REFERENCE_VISUAL_KEEPOUT"
    if name == "nasal_lobe_membrane_reference":
        return "DEVELOPMENT_REFERENCE"
    return "PACKAGE_REFERENCE"


def _component_clearances(
    frame_solid: cq.Workplane,
    model: MasckOneModel,
) -> tuple[ClearanceRecord, ...]:
    records = []
    for component in model.components:
        records.append(
            ClearanceRecord(
                target_id=component.name,
                target_role=_component_role(component.name),
                source_status=component.status,
                intersection_volume_mm3=_quantized(
                    _intersection_volume(frame_solid, component.solid),
                    label=f"{component.name} intersection volume",
                ),
                minimum_distance_mm=_quantized(
                    _minimum_distance(frame_solid, component.solid),
                    label=f"{component.name} minimum distance",
                ),
            )
        )
    return tuple(records)


def _protected_zone_solid(
    *,
    center_x_mm: float,
    center_y_mm: float,
    envelope_width_mm: float,
    envelope_height_mm: float,
    angle_deg: float,
    z_min_mm: float,
    z_max_mm: float,
) -> cq.Workplane:
    depth = z_max_mm - z_min_mm
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=z_min_mm)
        .center(center_x_mm, center_y_mm)
        .ellipse(envelope_width_mm / 2.0, envelope_height_mm / 2.0)
        .extrude(depth)
    )
    if angle_deg:
        cutter = cutter.rotate(
            (center_x_mm, center_y_mm, 0.0),
            (center_x_mm, center_y_mm, 1.0),
            angle_deg,
        )
    return cutter


def _protected_clearances(
    frame_solid: cq.Workplane,
    model: MasckOneModel,
    *,
    z_min_mm: float,
    z_max_mm: float,
) -> tuple[ClearanceRecord, ...]:
    records = []
    for protected in model.protected_volumes.all:
        zone = protected.zone
        keepout = _protected_zone_solid(
            center_x_mm=zone.center.x,
            center_y_mm=zone.center.y,
            envelope_width_mm=zone.envelope_width_mm,
            envelope_height_mm=zone.envelope_height_mm,
            angle_deg=zone.angle_deg,
            z_min_mm=z_min_mm - 1.0,
            z_max_mm=z_max_mm + 1.0,
        )
        records.append(
            ClearanceRecord(
                target_id=zone.zone_id,
                target_role="AUTHORITY_DERIVED_PLANAR_HARD_PROTECTED_ENVELOPE_UNBOUNDED_Z_POLICY",
                source_status=zone.authority_status,
                intersection_volume_mm3=_quantized(
                    _intersection_volume(frame_solid, keepout),
                    label=f"{zone.zone_id} intersection volume",
                ),
                minimum_distance_mm=_quantized(
                    _minimum_distance(frame_solid, keepout),
                    label=f"{zone.zone_id} minimum distance",
                ),
            )
        )
    return tuple(records)


def build_structural_frame_realization(
    *,
    model: MasckOneModel | None = None,
    structural_frame: StructuralFrameTopology | None = None,
) -> StructuralFrameRealization:
    """Build the first current-main structural reaction-loop B-rep.

    The exact released attachment perimeter is consumed as the member's inner capture
    edge. The member expands only to the authority outer XY envelope and is placed
    posterior of the current waste-cartridge package reference. Shell joins, actuator
    reaction nodes, retention counterparts, tooling/service features, material, and
    structural performance remain explicitly unresolved.
    """

    _require_source_files_current()
    model = build_model() if model is None else model
    if type(model) is not MasckOneModel:
        raise StructuralFrameRealizationError(
            "structural frame realization requires the exact MasckOneModel type"
        )
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise StructuralFrameRealizationError(
            "authority revision moved and requires structural frame rebind"
        )

    attachment, current_frame = _current_attachment_and_frame(model)
    if structural_frame is None:
        structural_frame = current_frame
    elif type(structural_frame) is not StructuralFrameTopology:
        raise StructuralFrameRealizationError(
            "supplied structural frame must be the exact topology type"
        )
    elif structural_frame.topology_sha256 != current_frame.topology_sha256:
        raise StructuralFrameRealizationError(
            "supplied structural frame topology is stale for current released sources"
        )

    ordered_vertex_indices, ordered_points = _ordered_capture_cycle(
        model, attachment, structural_frame
    )
    capture_path_sha = _capture_path_sha256(
        ordered_vertex_indices, ordered_points
    )

    outer_xy = tuple(
        float(value)
        for value in model.authority.pair("geometry", "outer_xy_envelope_mm")
    )
    if structural_frame.functional_frame_xy_mm != tuple(
        float(value)
        for value in model.authority.pair("geometry", "functional_frame_xy_mm")
    ):
        raise StructuralFrameRealizationError(
            "structural frame functional reference moved from current authority"
        )

    waste_bounds = model.waste_cartridge_envelope.solid.val().BoundingBox()
    waste_zmin = round(float(waste_bounds.zmin), 6)
    if not math.isfinite(waste_zmin):
        raise StructuralFrameRealizationError(
            "current waste package has a nonfinite Z minimum"
        )
    z_max = waste_zmin - PACKAGE_CLEARANCE_SEED_MM
    z_min = z_max - AXIAL_DEPTH_SEED_MM
    z_range = (z_min, z_max)

    solid = _build_member_solid(
        ordered_points=ordered_points,
        outer_xy_envelope_mm=outer_xy,
        z_min_mm=z_min,
        axial_depth_mm=AXIAL_DEPTH_SEED_MM,
    )
    measurements = _geometry_measurements(solid)
    measured = dict(measurements)
    bbox = measured["bbox_mm"]
    expected_bbox = [
        -outer_xy[0] / 2.0,
        -outer_xy[1] / 2.0,
        z_min,
        outer_xy[0] / 2.0,
        outer_xy[1] / 2.0,
        z_max,
    ]
    if any(
        not math.isclose(
            float(actual),
            float(expected),
            rel_tol=0.0,
            abs_tol=_BREP_BOUND_TOLERANCE_MM,
        )
        for actual, expected in zip(bbox, expected_bbox, strict=True)
    ):
        raise StructuralFrameRealizationError(
            "realized frame B-rep no longer matches authored authority/axial bounds"
        )

    component_clearances = _component_clearances(solid, model)
    protected_clearances = _protected_clearances(
        solid, model, z_min_mm=z_min, z_max_mm=z_max
    )
    geometry_sha = _geometry_sha256(
        source_capture_path_sha256=capture_path_sha,
        outer_xy_envelope_mm=outer_xy,
        axial_depth_mm=AXIAL_DEPTH_SEED_MM,
        z_range_mm=z_range,
        geometry_measurements=measurements,
    )

    result = StructuralFrameRealization(
        source_structural_frame_sha256=structural_frame.topology_sha256,
        source_attachment_topology_sha256=attachment.topology_sha256,
        source_registered_mesh_sha256=structural_frame.source_registered_mesh_sha256,
        source_capture_path_sha256=capture_path_sha,
        source_capture_edge_indices=structural_frame.perimeter_reaction_path.source_attachment_edge_indices,
        source_capture_vertex_count=len(ordered_vertex_indices),
        source_capture_path_length_mm=_quantized(
            sum(assignment.length_mm for assignment in attachment.assignments),
            label="source capture path length",
        ),
        outer_xy_envelope_mm=outer_xy,
        axial_depth_mm=AXIAL_DEPTH_SEED_MM,
        z_range_mm=z_range,
        current_waste_package_zmin_mm=waste_zmin,
        geometry_measurements=measurements,
        geometry_sha256=geometry_sha,
        component_clearances=component_clearances,
        protected_clearances=protected_clearances,
        material_selection=None,
        physical_validation_eligible=False,
        solid=solid,
    )
    result.__post_init__()
    return result
