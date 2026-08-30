from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math

from .authority import Authority
from .interface_attachment import InterfaceAttachmentArchitecture


class StructuralFrameError(ValueError):
    """Raised when the Iteration-15 structural-frame topology contract is violated."""


DATUM_CENTER = "MASCK_ONE-FRAME-DATUM-CENTER"
DATUM_SUPERIOR = "MASCK_ONE-FRAME-DATUM-SUPERIOR"
DATUM_INFERIOR = "MASCK_ONE-FRAME-DATUM-INFERIOR"
DATUM_LEFT = "MASCK_ONE-FRAME-DATUM-WEARER_LEFT"
DATUM_RIGHT = "MASCK_ONE-FRAME-DATUM-WEARER_RIGHT"
DATUM_IDS = (DATUM_CENTER, DATUM_SUPERIOR, DATUM_INFERIOR, DATUM_LEFT, DATUM_RIGHT)

RESERVATION_ACTUATION = "FRAME_RESERVATION_ACTUATION_4_ZONE"
RESERVATION_FRESH_FLUID = "FRAME_RESERVATION_FRESH_FLUID_ROUTING"
RESERVATION_WASTE = "FRAME_RESERVATION_WASTE_ROUTING"
RESERVATION_RETENTION = "FRAME_RESERVATION_RETENTION_INTERFACE"
RESERVATION_HMI_ELECTRONICS = "FRAME_RESERVATION_HMI_ELECTRONICS"
RESERVATION_THERMAL = "FRAME_RESERVATION_THERMAL_SYSTEM"
RESERVATION_IDS = (
    RESERVATION_ACTUATION,
    RESERVATION_FRESH_FLUID,
    RESERVATION_WASTE,
    RESERVATION_RETENTION,
    RESERVATION_HMI_ELECTRONICS,
    RESERVATION_THERMAL,
)


@dataclass(frozen=True, slots=True)
class FrameDatum:
    datum_id: str
    x_mm: float
    y_mm: float
    z_status: str
    derivation: str
    geometry_status: str

    def __post_init__(self) -> None:
        if self.datum_id not in DATUM_IDS:
            raise StructuralFrameError(f"Unknown frame datum ID {self.datum_id!r}")
        for field_name in ("x_mm", "y_mm"):
            value = float(getattr(self, field_name))
            if not math.isfinite(value):
                raise StructuralFrameError("Frame datum coordinates must be finite")
            object.__setattr__(self, field_name, value)
        if not self.z_status.strip() or not self.derivation.strip() or not self.geometry_status.strip():
            raise StructuralFrameError("Frame datum metadata must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "datum_id": self.datum_id,
            "x_mm": self.x_mm,
            "y_mm": self.y_mm,
            "z_mm": None,
            "z_status": self.z_status,
            "derivation": self.derivation,
            "geometry_status": self.geometry_status,
        }


@dataclass(frozen=True, slots=True)
class FrameReservation:
    reservation_id: str
    functional_role: str
    interface_count: int | None
    placement_status: str
    envelope_status: str
    evidence_status: str

    def __post_init__(self) -> None:
        if self.reservation_id not in RESERVATION_IDS:
            raise StructuralFrameError(f"Unknown structural-frame reservation {self.reservation_id!r}")
        if self.interface_count is not None and self.interface_count <= 0:
            raise StructuralFrameError("Reservation interface count must be positive when defined")
        for value in (
            self.functional_role,
            self.placement_status,
            self.envelope_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise StructuralFrameError("Frame reservation metadata must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "reservation_id": self.reservation_id,
            "functional_role": self.functional_role,
            "interface_count": self.interface_count,
            "placement_status": self.placement_status,
            "envelope_status": self.envelope_status,
            "evidence_status": self.evidence_status,
        }


@dataclass(frozen=True, slots=True)
class FrameLoadPath:
    path_id: str
    path_role: str
    source_attachment_edge_indices: tuple[int, ...]
    geometry_realization_status: str
    cross_section_status: str
    material_status: str
    load_validation_status: str

    def __post_init__(self) -> None:
        if not self.path_id.strip() or not self.path_role.strip():
            raise StructuralFrameError("Frame load-path identity must be explicit")
        if not self.source_attachment_edge_indices:
            raise StructuralFrameError("Frame load path requires source attachment edges")
        if tuple(sorted(self.source_attachment_edge_indices)) != self.source_attachment_edge_indices:
            raise StructuralFrameError("Frame load-path edge indices must be sorted")
        if len(set(self.source_attachment_edge_indices)) != len(self.source_attachment_edge_indices):
            raise StructuralFrameError("Frame load-path edge indices cannot repeat")
        for value in (
            self.geometry_realization_status,
            self.cross_section_status,
            self.material_status,
            self.load_validation_status,
        ):
            if not str(value).strip():
                raise StructuralFrameError("Frame load-path status metadata must be explicit")

    def manifest(self) -> dict[str, object]:
        return {
            "path_id": self.path_id,
            "path_role": self.path_role,
            "source_attachment_edge_indices": list(self.source_attachment_edge_indices),
            "geometry_realization_status": self.geometry_realization_status,
            "cross_section_status": self.cross_section_status,
            "material_status": self.material_status,
            "load_validation_status": self.load_validation_status,
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameTopology:
    source_attachment_topology_sha256: str
    source_registered_mesh_sha256: str
    functional_frame_xy_mm: tuple[float, float]
    functional_frame_status: str
    datums: tuple[FrameDatum, ...]
    perimeter_reaction_path: FrameLoadPath
    reservations: tuple[FrameReservation, ...]
    frame_deflection_p95_max_mm: float
    frame_deflection_status: str
    first_mode_preferred_min_hz: float
    first_mode_status: str
    cross_section_dimensions_mm: tuple[float, ...] | None
    material_selection: str | None
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        for digest in (self.source_attachment_topology_sha256, self.source_registered_mesh_sha256):
            value = digest.lower()
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise StructuralFrameError("Structural-frame source hashes must be SHA-256")
        width, height = (float(value) for value in self.functional_frame_xy_mm)
        if not all(math.isfinite(value) and value > 0.0 for value in (width, height)):
            raise StructuralFrameError("Functional-frame dimensions must be finite and positive")
        object.__setattr__(self, "functional_frame_xy_mm", (width, height))
        if tuple(datum.datum_id for datum in self.datums) != DATUM_IDS:
            raise StructuralFrameError("Structural frame datums must follow the controlled datum order")
        if tuple(reservation.reservation_id for reservation in self.reservations) != RESERVATION_IDS:
            raise StructuralFrameError("Structural frame reservations must follow the controlled order")
        if self.cross_section_dimensions_mm is not None:
            raise StructuralFrameError("Iteration 15 cannot invent structural-frame cross-section dimensions")
        if self.material_selection is not None:
            raise StructuralFrameError("Iteration 15 cannot select a frame material without evidence")
        if self.physical_validation_eligible:
            raise StructuralFrameError("Digital structural topology cannot be physical-validation evidence")
        for value in (
            self.functional_frame_status,
            self.frame_deflection_status,
            self.first_mode_status,
            self.evidence_status,
        ):
            if not str(value).strip():
                raise StructuralFrameError("Structural-frame status metadata must be explicit")
        for field_name in ("frame_deflection_p95_max_mm", "first_mode_preferred_min_hz"):
            value = float(getattr(self, field_name))
            if not math.isfinite(value) or value <= 0.0:
                raise StructuralFrameError("Structural requirements must be finite and positive")
            object.__setattr__(self, field_name, value)

    @property
    def topology_sha256(self) -> str:
        payload = self.manifest(include_sha=False)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_attachment_topology_sha256": self.source_attachment_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "functional_frame_xy_mm": list(self.functional_frame_xy_mm),
            "functional_frame_status": self.functional_frame_status,
            "datums": [datum.manifest() for datum in self.datums],
            "perimeter_reaction_path": self.perimeter_reaction_path.manifest(),
            "reservations": [reservation.manifest() for reservation in self.reservations],
            "frame_deflection_p95_max_mm": self.frame_deflection_p95_max_mm,
            "frame_deflection_status": self.frame_deflection_status,
            "first_mode_preferred_min_hz": self.first_mode_preferred_min_hz,
            "first_mode_status": self.first_mode_status,
            "cross_section_dimensions_mm": self.cross_section_dimensions_mm,
            "material_selection": self.material_selection,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["topology_sha256"] = self.topology_sha256
        return payload


def _datums(functional_frame_xy_mm: tuple[float, float]) -> tuple[FrameDatum, ...]:
    width, height = functional_frame_xy_mm
    half_w = width / 2.0
    half_h = height / 2.0
    z_status = "UNRESOLVED_UNTIL_STRUCTURAL_3D_SURFACE_AND_PACKAGING_CLOSURE"
    status = "AUTHORITY_DERIVED_XY_DATUM_REFERENCE_NOT_FINAL_3D_FRAME_GEOMETRY"
    return (
        FrameDatum(DATUM_CENTER, 0.0, 0.0, z_status, "canonical sagittal/transverse datum intersection", status),
        FrameDatum(DATUM_SUPERIOR, 0.0, half_h, z_status, "functional-frame authority height / 2", status),
        FrameDatum(DATUM_INFERIOR, 0.0, -half_h, z_status, "-functional-frame authority height / 2", status),
        FrameDatum(DATUM_LEFT, -half_w, 0.0, z_status, "-functional-frame authority width / 2", status),
        FrameDatum(DATUM_RIGHT, half_w, 0.0, z_status, "functional-frame authority width / 2", status),
    )


def _reservations(authority: Authority) -> tuple[FrameReservation, ...]:
    actuator_count = int(authority.number("actuation", "count"))
    return (
        FrameReservation(
            RESERVATION_ACTUATION,
            "reserve structural reactions/interfaces for four independently controllable actuation zones",
            actuator_count,
            "PLACEMENT_DEFERRED_TO_ITERATION17_ACTUATOR_LOCAL_FRAMES",
            "SUPPLIER_DEVELOPMENT_ENVELOPES_NOT_STRUCTURAL_MOUNT_FREEZE",
            "RESERVATION_ONLY_NOT_ACTUATOR_MOUNT_LOAD_OR_FATIGUE_EVIDENCE",
        ),
        FrameReservation(
            RESERVATION_FRESH_FLUID,
            "reserve pass-through and support topology for water/cleanser routing",
            None,
            "ROUTING_DEFERRED_TO_ITERATIONS20_TO24",
            "UNRESOLVED",
            "RESERVATION_ONLY_NOT_FLOW_OR_LEAKAGE_EVIDENCE",
        ),
        FrameReservation(
            RESERVATION_WASTE,
            "reserve pass-through and support topology for waste acquisition/routing",
            None,
            "ROUTING_DEFERRED_TO_ITERATIONS25_TO28",
            "UNRESOLVED",
            "RESERVATION_ONLY_NOT_WASTE_RECOVERY_OR_CONTAINMENT_EVIDENCE",
        ),
        FrameReservation(
            RESERVATION_RETENTION,
            "reserve structural load-transfer interface to halo/occipital/crown retention system",
            None,
            "RETENTION_GEOMETRY_DEFERRED_TO_ITERATION29",
            "UNRESOLVED",
            "RESERVATION_ONLY_NOT_PRELOAD_QUICK_RELEASE_OR_FIT_EVIDENCE",
        ),
        FrameReservation(
            RESERVATION_HMI_ELECTRONICS,
            "reserve future attachment/routing relationship for HMI and electronics dry-bay system",
            None,
            "PACKAGING_DEFERRED_TO_ITERATIONS31_AND32",
            "UNRESOLVED",
            "RESERVATION_ONLY_NOT_ELECTRICAL_OR_INGRESS_EVIDENCE",
        ),
        FrameReservation(
            RESERVATION_THERMAL,
            "reserve future thermal-system relationship without creating heater/cooler geometry",
            None,
            "THERMAL_GEOMETRY_DEFERRED_TO_ITERATIONS33_AND34",
            "UNRESOLVED",
            "RESERVATION_ONLY_NOT_THERMAL_SAFETY_EVIDENCE",
        ),
    )


def build_structural_frame_topology(
    authority: Authority,
    attachment: InterfaceAttachmentArchitecture,
) -> StructuralFrameTopology:
    """Establish the Iteration-15 structural skeleton at topology/datum level.

    The verified attachment perimeter becomes the first closed structural reaction loop.
    Physical cross-sections, 3D Z placement, materials and local mounts remain unresolved
    until their own dependent engineering iterations can justify them.
    """

    functional_frame = authority.pair("geometry", "functional_frame_xy_mm")
    edge_indices = tuple(item.source_boundary_edge_index for item in attachment.assignments)
    if len(edge_indices) != len(set(edge_indices)):
        raise StructuralFrameError("Attachment source perimeter cannot contain duplicate reaction edges")
    if tuple(sorted(edge_indices)) != edge_indices:
        raise StructuralFrameError("Attachment reaction edge order must remain deterministic")

    perimeter_path = FrameLoadPath(
        path_id="MASCK_ONE-FRAME-LOADPATH-PERIMETER-REACTION-LOOP",
        path_role=(
            "closed structural reaction topology inherited from the exact compliant-interface perimeter capture; "
            "future 3D member realization must preserve protected-opening separation"
        ),
        source_attachment_edge_indices=edge_indices,
        geometry_realization_status="TOPOLOGY_DEFINED_3D_MEMBER_GEOMETRY_AND_CROSS_SECTION_UNRESOLVED",
        cross_section_status="UNRESOLVED_NO_UNSOURCED_FRAME_MEMBER_DIMENSIONS",
        material_status="UNSELECTED_VALIDATION_GATED",
        load_validation_status="BLOCKED_PENDING_REALIZED_GEOMETRY_MATERIAL_AND_ANALYSIS_PHYSICAL_EVIDENCE",
    )

    return StructuralFrameTopology(
        source_attachment_topology_sha256=attachment.topology_sha256,
        source_registered_mesh_sha256=attachment.source_registered_mesh_sha256,
        functional_frame_xy_mm=functional_frame,
        functional_frame_status=str(authority.get("geometry", "functional_frame_status")),
        datums=_datums(functional_frame),
        perimeter_reaction_path=perimeter_path,
        reservations=_reservations(authority),
        frame_deflection_p95_max_mm=float(authority.get("structure", "frame_deflection_p95_max_mm")),
        frame_deflection_status=str(authority.get("structure", "frame_deflection_status")),
        first_mode_preferred_min_hz=float(authority.get("structure", "frame_first_mode_preferred_min_hz")),
        first_mode_status=str(authority.get("structure", "frame_first_mode_status")),
        cross_section_dimensions_mm=None,
        material_selection=None,
        physical_validation_eligible=False,
        evidence_status=(
            "DIGITAL_STRUCTURAL_TOPOLOGY_AND_DATUM_NETWORK_ONLY_NOT_DEFLECTION_MODAL_LOAD_FATIGUE_FIT_OR_PHYSICAL_VALIDATION"
        ),
    )

