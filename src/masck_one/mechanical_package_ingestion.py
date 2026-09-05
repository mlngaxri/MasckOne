from __future__ import annotations

"""Cell 1 source-bound integration of the current Cell 3 mechanical package.

This module is intentionally an integration adapter, not a second mechanism authoring
lane. It consumes the exact current Cell 3 right-release B-reps and the released
current-main actuator objects, while keeping the released structural frame at its
actual topology-only maturity. Motion geometry is first-class review evidence but is
never mixed into the static product compound.

All evidence here is digital CAD/provenance evidence only. It does not establish
retention fit or comfort, release force/time, wet one-hand usability, fatigue, wear,
structural capacity, manufacturability, or physical safety.
"""

from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

import cadquery as cq

from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import build_interface_attachment_architecture
from .model import Component, MasckOneModel, build_model
from .realized_waste_backbone import ArcXY, Line3, RealizedWasteRoute
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .right_quick_release_assembly import (
    CLOSURE_START_Z,
    HOOK_DEFLECTION,
    SLIDER_START_Z,
    RightQuickReleaseAssembly,
    build_right_quick_release_assembly,
)
from .right_quick_release_latch import RELEASE_TRAVEL_MM, WORLD_FRAME_ID
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology


SCHEMA = "MASCK_ONE_CELL1_MECHANICAL_PACKAGE_INGESTION_V1"
SOURCE_MAIN_SHA = "628ec5f5766937433b1bdf8f30edc372924cf41e"
SOURCE_CELL3_PR = 71
SOURCE_CELL3_HEAD_SHA = "0b5a619c6cea344038b0e8b8cc10a50e3d193390"
AUTHORITY_REVISION = "2026-08-30-R1"
AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
MODEL_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
STRUCTURAL_FRAME_BLOB_SHA = "bda5ba87d232c0e6a22e200975a80414a10c9a83"
CELL3_SOURCE_BLOBS = (
    ("src/masck_one/right_quick_release_latch.py", "11d90a75eb108c53f5a1621abdace7271bf5cac5"),
    ("src/masck_one/right_quick_release_reset.py", "10d2dcb22506bba03b5ec604ef2bfb964c38a8cb"),
    ("src/masck_one/right_quick_release_sweep.py", "d9be83d27deef9afd7e98dcbb874ebed1d1ab360"),
    ("src/masck_one/right_quick_release_assembly.py", "bb6887c3b78384942f620a61df92d8cee87b336b"),
    ("src/masck_one/right_quick_release_travel.py", "7330cf9fbcc5d3e690aadec9bafe3fdf7b94bacd"),
)

STATIC_ROLE = "STATIC_PRODUCT_COMPONENT"
MOTION_ROLE = "MOTION_OR_FACTORY_REVIEW_GEOMETRY"
DIGITAL_ONLY = (
    "DIGITAL_MECHANICAL_INTEGRATION_ONLY_NOT_RETENTION_FIT_COMFORT_RELEASE_FORCE_TIME_"
    "WET_USE_FATIGUE_STRUCTURAL_CAPACITY_MANUFACTURABILITY_OR_PHYSICAL_SAFETY_EVIDENCE"
)
KERNEL_ZERO_MM3 = 1e-7


class MechanicalPackageIngestionError(ValueError):
    pass


def _git_sha(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise MechanicalPackageIngestionError(f"{label} must be exact lowercase 40-hex")
    return value


def _sha256_digest(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise MechanicalPackageIngestionError(f"{label} must be exact lowercase SHA-256")
    return value


def _bounds(shape: cq.Shape) -> tuple[float, float, float, float, float, float]:
    bb = shape.BoundingBox()
    return tuple(float(v) for v in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _brep_sha256(solid: cq.Workplane) -> str:
    shape = solid.val()
    if not shape.isValid() or not shape.Solids():
        raise MechanicalPackageIngestionError("B-rep digest requires valid solid geometry")
    buffer = BytesIO()
    shape.exportBrep(buffer)
    payload = buffer.getvalue()
    if not payload:
        raise MechanicalPackageIngestionError("B-rep export produced no bytes")
    return sha256(payload).hexdigest()


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = abs(float(first.val().intersect(second.val()).Volume()))
    if not math.isfinite(value):
        raise MechanicalPackageIngestionError("intersection volume must be finite")
    return 0.0 if value <= KERNEL_ZERO_MM3 else value


def _translated(solid: cq.Workplane, xyz: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane(obj=solid.val().translate(cq.Vector(*xyz)))


def _compound(parts: tuple[cq.Workplane, ...]) -> cq.Workplane:
    if not parts:
        raise MechanicalPackageIngestionError("mechanical compound requires at least one part")
    shapes = [part.val() for part in parts]
    if any(not shape.isValid() or not shape.Solids() for shape in shapes):
        raise MechanicalPackageIngestionError("mechanical compound contains invalid geometry")
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


@dataclass(frozen=True, slots=True)
class MechanicalSourceBinding:
    source_main_sha: str
    source_cell3_pr: int
    source_cell3_head_sha: str
    authority_revision: str
    authority_blob_sha: str
    model_blob_sha: str
    structural_frame_blob_sha: str
    cell3_source_blobs: tuple[tuple[str, str], ...]
    world_frame_id: str

    def validate(self) -> None:
        _git_sha(self.source_main_sha, "source main")
        _git_sha(self.source_cell3_head_sha, "Cell 3 source head")
        _git_sha(self.authority_blob_sha, "authority blob")
        _git_sha(self.model_blob_sha, "model blob")
        _git_sha(self.structural_frame_blob_sha, "structural frame blob")
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise MechanicalPackageIngestionError("mechanical integration is stale for current released main")
        if type(self.source_cell3_pr) is not int or isinstance(self.source_cell3_pr, bool) or self.source_cell3_pr != SOURCE_CELL3_PR:
            raise MechanicalPackageIngestionError("mechanical integration must bind exact Cell 3 PR identity")
        if self.source_cell3_head_sha != SOURCE_CELL3_HEAD_SHA:
            raise MechanicalPackageIngestionError("mechanical integration must bind exact Cell 3 head")
        if self.authority_revision != AUTHORITY_REVISION:
            raise MechanicalPackageIngestionError("machine authority revision changed")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise MechanicalPackageIngestionError("machine authority blob changed")
        if self.model_blob_sha != MODEL_BLOB_SHA or self.structural_frame_blob_sha != STRUCTURAL_FRAME_BLOB_SHA:
            raise MechanicalPackageIngestionError("released mechanical source blob changed")
        if self.world_frame_id != WORLD_FRAME_ID:
            raise MechanicalPackageIngestionError("mechanical package must use canonical authority world frame")
        if self.cell3_source_blobs != CELL3_SOURCE_BLOBS:
            raise MechanicalPackageIngestionError("Cell 3 source blob set changed")
        for path, digest in self.cell3_source_blobs:
            if type(path) is not str or not path.startswith("src/masck_one/"):
                raise MechanicalPackageIngestionError("Cell 3 source path must stay inside engineering source root")
            _git_sha(digest, f"Cell 3 blob for {path}")

    def manifest(self) -> dict[str, object]:
        return {
            "source_main_sha": self.source_main_sha,
            "source_cell3_pr": self.source_cell3_pr,
            "source_cell3_head_sha": self.source_cell3_head_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "model_blob_sha": self.model_blob_sha,
            "structural_frame_blob_sha": self.structural_frame_blob_sha,
            "cell3_source_blobs": [list(item) for item in self.cell3_source_blobs],
            "world_frame_id": self.world_frame_id,
        }


@dataclass(frozen=True, slots=True)
class MechanicalSolidRecord:
    assembly_id: str
    source_id: str
    role: str
    solid: cq.Workplane
    source_package_sha256: str | None = None
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if type(self.assembly_id) is not str or not self.assembly_id.strip():
            raise MechanicalPackageIngestionError("mechanical assembly ID must be exact nonblank text")
        if type(self.source_id) is not str or not self.source_id.strip():
            raise MechanicalPackageIngestionError("mechanical source ID must be exact nonblank text")
        if self.role not in {STATIC_ROLE, MOTION_ROLE}:
            raise MechanicalPackageIngestionError("mechanical solid role is uncontrolled")
        if self.source_package_sha256 is not None:
            _sha256_digest(self.source_package_sha256, "source package")
        shape = self.solid.val()
        if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
            raise MechanicalPackageIngestionError(f"{self.assembly_id} must contain valid positive-volume B-rep geometry")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise MechanicalPackageIngestionError("digital mechanical geometry cannot become physical evidence")

    @property
    def brep_sha256(self) -> str:
        return _brep_sha256(self.solid)

    def manifest(self) -> dict[str, object]:
        shape = self.solid.val()
        return {
            "assembly_id": self.assembly_id,
            "source_id": self.source_id,
            "role": self.role,
            "source_package_sha256": self.source_package_sha256,
            "brep_sha256": self.brep_sha256,
            "solid_count": len(shape.Solids()),
            "volume_mm3": float(shape.Volume()),
            "bounds_mm": list(_bounds(shape)),
            "physical_validation_eligible": False,
        }


@dataclass(frozen=True, slots=True)
class FrameIntegrationRecord:
    topology_sha256: str
    geometry_maturity: str
    cross_section_dimensions_mm: None
    material_selection: None
    unresolved_requirements: tuple[str, ...]
    physical_validation_eligible: bool = False

    def validate(self, frame: StructuralFrameTopology) -> None:
        _sha256_digest(self.topology_sha256, "frame topology")
        if self.topology_sha256 != frame.topology_sha256:
            raise MechanicalPackageIngestionError("frame topology provenance mismatch")
        if self.geometry_maturity != "TOPOLOGY_ONLY_3D_FRAME_NOT_YET_RELEASED":
            raise MechanicalPackageIngestionError("frame maturity cannot be promoted by mechanical ingestion")
        if self.cross_section_dimensions_mm is not None or self.material_selection is not None:
            raise MechanicalPackageIngestionError("mechanical ingestion cannot invent frame cross-section or material")
        if type(self.unresolved_requirements) is not tuple or not self.unresolved_requirements:
            raise MechanicalPackageIngestionError("frame integration must preserve explicit current blockers")
        if self.physical_validation_eligible:
            raise MechanicalPackageIngestionError("frame topology cannot become physical evidence")

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MechanicalStateRecord:
    state_id: str
    phase: str
    geometry_ids: tuple[str, ...]
    motion_semantics: str
    full_head_removal_included: bool = False

    def __post_init__(self) -> None:
        if type(self.state_id) is not str or not self.state_id.strip():
            raise MechanicalPackageIngestionError("mechanical state ID must be exact nonblank text")
        if self.phase not in {"OPERATIONAL_RESET", "FACTORY_ASSEMBLY"}:
            raise MechanicalPackageIngestionError("mechanical state phase is uncontrolled")
        if type(self.geometry_ids) is not tuple or not self.geometry_ids:
            raise MechanicalPackageIngestionError("mechanical state requires first-class geometry IDs")
        if type(self.motion_semantics) is not str or not self.motion_semantics.strip():
            raise MechanicalPackageIngestionError("mechanical state semantics must be explicit")
        if self.full_head_removal_included:
            raise MechanicalPackageIngestionError("current right-release package does not include full-head removal")

    def manifest(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MechanicalCollisionCheck:
    check_id: str
    obstacle_id: str
    intersection_volume_mm3: float

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "obstacle_id": self.obstacle_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class WasteSeparationCheck:
    motion_id: str
    route_id: str
    motion_xmin_mm: float
    route_service_xmax_mm: float
    separation_mm: float

    @property
    def passes(self) -> bool:
        return self.separation_mm > 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "motion_id": self.motion_id,
            "route_id": self.route_id,
            "motion_xmin_mm": self.motion_xmin_mm,
            "route_service_xmax_mm": self.route_service_xmax_mm,
            "separation_mm": self.separation_mm,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class MechanicalPackageIntegration:
    binding: MechanicalSourceBinding
    source_assembly_package_sha256: str
    source_reset_package_sha256: str
    source_continuous_sweep_package_sha256: str
    frame: FrameIntegrationRecord
    actuator_components: tuple[Component, ...]
    static_solids: tuple[MechanicalSolidRecord, ...]
    motion_solids: tuple[MechanicalSolidRecord, ...]
    states: tuple[MechanicalStateRecord, ...]
    collision_checks: tuple[MechanicalCollisionCheck, ...]
    waste_separation_checks: tuple[WasteSeparationCheck, ...]
    unresolved_integration: tuple[str, ...]
    evidence_status: str = DIGITAL_ONLY
    physical_validation_eligible: bool = False

    def validate(self) -> None:
        self.binding.validate()
        for digest, label in (
            (self.source_assembly_package_sha256, "source assembly package"),
            (self.source_reset_package_sha256, "source reset package"),
            (self.source_continuous_sweep_package_sha256, "source continuous sweep package"),
        ):
            _sha256_digest(digest, label)
        if len(self.actuator_components) != 4 or tuple(part.name for part in self.actuator_components) != tuple(
            f"actuator_envelope_{index}" for index in range(1, 5)
        ):
            raise MechanicalPackageIngestionError("mechanical integration must preserve all four released actuator components")
        if len({record.assembly_id for record in self.static_solids + self.motion_solids}) != len(self.static_solids + self.motion_solids):
            raise MechanicalPackageIngestionError("mechanical assembly IDs must be globally unique")
        if any(record.role != STATIC_ROLE for record in self.static_solids):
            raise MechanicalPackageIngestionError("static product compound cannot contain motion geometry")
        if any(record.role != MOTION_ROLE for record in self.motion_solids):
            raise MechanicalPackageIngestionError("motion registry contains a static product role")
        if any(not check.passes for check in self.collision_checks):
            raise MechanicalPackageIngestionError("mechanical motion intersects released fixed geometry")
        if any(not check.passes for check in self.waste_separation_checks):
            raise MechanicalPackageIngestionError("mechanical motion violates released mixed-waste service separation")
        state_ids = tuple(state.state_id for state in self.states)
        expected = (
            "LATCHED",
            "RELEASING_DETENT_LIFTED",
            "RELEASE_TRAVEL_LOW_OFFSET",
            "RELEASE_TRAVEL_HIGH_OFFSET",
            "RELEASED_RESET_REQUIRED",
            "RESET_TRAVEL_HIGH_OFFSET",
            "RESET_DETENT_LIFTED",
            "RESET_TRAVEL_LOW_OFFSET",
            "RESET_RESEATED_LATCHED",
            "GUIDE_OPEN_LOWER_HALF",
            "SLIDER_INSERTION",
            "UPPER_CLOSURE_DESCENT_HOOKS_DEFLECTED",
            "HOOK_RELAXATION_TO_POSITIVE_CAPTURE",
            "ASSEMBLED_OPERATIONAL",
        )
        if state_ids != expected:
            raise MechanicalPackageIngestionError("mechanical state sequence drifted from controlled Cell 3 semantics")
        if type(self.unresolved_integration) is not tuple or not self.unresolved_integration:
            raise MechanicalPackageIngestionError("mechanical integration must preserve unresolved whole-product work")
        if self.evidence_status != DIGITAL_ONLY or self.physical_validation_eligible:
            raise MechanicalPackageIngestionError("mechanical integration cannot promote physical validation")

    @property
    def static_compound(self) -> cq.Workplane:
        parts = tuple(component.solid for component in self.actuator_components) + tuple(
            record.solid for record in self.static_solids
        )
        return _compound(parts)

    @property
    def integration_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "binding": self.binding.manifest(),
            "source_assembly_package_sha256": self.source_assembly_package_sha256,
            "source_reset_package_sha256": self.source_reset_package_sha256,
            "source_continuous_sweep_package_sha256": self.source_continuous_sweep_package_sha256,
            "frame": self.frame.manifest(),
            "actuators": [
                {
                    "assembly_id": f"MECH_ACTUATOR_{index}",
                    "source_component_name": component.name,
                    "source_object_preserved": True,
                    "brep_sha256": _brep_sha256(component.solid),
                    "bounds_mm": list(_bounds(component.solid.val())),
                    "status": component.status,
                }
                for index, component in enumerate(self.actuator_components, start=1)
            ],
            "static_solids": [record.manifest() for record in self.static_solids],
            "motion_solids": [record.manifest() for record in self.motion_solids],
            "states": [state.manifest() for state in self.states],
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "waste_separation_checks": [check.manifest() for check in self.waste_separation_checks],
            "static_compound_brep_sha256": _brep_sha256(self.static_compound),
            "unresolved_integration": list(self.unresolved_integration),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["integration_sha256"] = self.integration_sha256
        return payload


def _build_current_frame(model: MasckOneModel) -> StructuralFrameTopology:
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    return build_structural_frame_topology(model.authority, attachment)


def _route_edge_distance_record(route: RealizedWasteRoute, motion: MechanicalSolidRecord) -> WasteSeparationCheck:
    bounds_min, bounds_max = route.bounds_xyz_mm
    route_service_xmax = float(bounds_max[0]) + float(route.service_envelope_radius_mm)
    motion_xmin = float(motion.solid.val().BoundingBox().xmin)
    return WasteSeparationCheck(
        motion_id=motion.assembly_id,
        route_id=route.route_id,
        motion_xmin_mm=motion_xmin,
        route_service_xmax_mm=route_service_xmax,
        separation_mm=motion_xmin - route_service_xmax,
    )


def _moving_vs_released_checks(model: MasckOneModel, motion: tuple[MechanicalSolidRecord, ...]) -> tuple[MechanicalCollisionCheck, ...]:
    obstacles = (
        model.shell,
        *model.actuator_envelopes,
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
        *model.visual_keepouts,
    )
    checks: list[MechanicalCollisionCheck] = []
    for moving in motion:
        for obstacle in obstacles:
            checks.append(
                MechanicalCollisionCheck(
                    check_id=f"{moving.assembly_id}_VS_{obstacle.name.upper()}",
                    obstacle_id=obstacle.name,
                    intersection_volume_mm3=_intersection_mm3(moving.solid, obstacle.solid),
                )
            )
    return tuple(checks)


def build_mechanical_package_integration() -> MechanicalPackageIntegration:
    model = build_model()
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise MechanicalPackageIngestionError("current authority revision changed")
    if len(model.actuator_envelopes) != 4:
        raise MechanicalPackageIngestionError("current released model no longer has four actuator envelopes")

    source = build_right_quick_release_assembly(model=model)
    reset = source.reset
    continuous = source.continuous
    latch = reset.latch
    frame = _build_current_frame(model)
    frame_record = FrameIntegrationRecord(
        topology_sha256=frame.topology_sha256,
        geometry_maturity="TOPOLOGY_ONLY_3D_FRAME_NOT_YET_RELEASED",
        cross_section_dimensions_mm=None,
        material_selection=None,
        unresolved_requirements=(
            "REALIZE_3D_FRAME_MEMBER_GEOMETRY_AND_CROSS_SECTION",
            "DEFINE_FRAME_TO_SHELL_JOIN_AND_PROCESS_OR_TOOL_ACCESS",
            "REALIZE_FOUR_ACTUATOR_REACTION_ATTACHMENTS_AND_FINAL_STOPS",
            "REALIZE_BILATERAL_RETENTION_TO_FRAME_ATTACHMENT_WITH_POSITIVE_RETENTION",
            "PROVE_CONTINUOUS_FRAME_INSERTION_AND_FINAL_JOIN_CLOSURE",
        ),
        physical_validation_eligible=False,
    )
    frame_record.validate(frame)

    static = (
        MechanicalSolidRecord("MECH_RIGHT_FRAME_SOCKET", latch.socket.part_id, STATIC_ROLE, latch.socket.solid, latch.package_sha256),
        MechanicalSolidRecord("MECH_RIGHT_HALO_TONGUE", latch.tongue.part_id, STATIC_ROLE, latch.tongue.solid, latch.package_sha256),
        MechanicalSolidRecord("MECH_RIGHT_GUIDE_LOWER", source.lower.part_id, STATIC_ROLE, source.lower.solid, source.package_sha256),
        MechanicalSolidRecord("MECH_RIGHT_GUIDE_UPPER", source.upper.part_id, STATIC_ROLE, source.upper.solid, source.package_sha256),
        MechanicalSolidRecord("MECH_RIGHT_SLIDER_LATCHED", latch.slider_and_grip.part_id, STATIC_ROLE, latch.slider_and_grip.solid, latch.package_sha256),
        MechanicalSolidRecord("MECH_RIGHT_RESET_FLEXURE_NOMINAL", reset.nominal_flexure.part_id, STATIC_ROLE, reset.nominal_flexure.solid, reset.package_sha256),
    )

    released_slider = _translated(latch.slider_and_grip.solid, (RELEASE_TRAVEL_MM, 0.0, 0.0))
    motion = (
        MechanicalSolidRecord("MOTION_RIGHT_EXACT_WITHDRAWAL_SWEEP", "RIGHT_LATCH_EXACT_CONTINUOUS_WITHDRAWAL_SWEEP", MOTION_ROLE, continuous.exact_slider_sweep, continuous.package_sha256),
        MechanicalSolidRecord("MOTION_RIGHT_SLIDER_RELEASED_STATE", "RIGHT_LATCH_SLIDER_AND_GRIP_AT_RELEASED_HARD_STOP", MOTION_ROLE, released_slider, latch.package_sha256),
        MechanicalSolidRecord("MOTION_RIGHT_RESET_FLEXURE_LIFTED", reset.lifted_flexure.part_id, MOTION_ROLE, reset.lifted_flexure.solid, reset.package_sha256),
        MechanicalSolidRecord("MOTION_RIGHT_RESET_FLEXURE_ENVELOPE", reset.deformation_envelope.part_id, MOTION_ROLE, reset.deformation_envelope.solid, reset.package_sha256),
        MechanicalSolidRecord("MOTION_RIGHT_RELEASE_RESET_LOW_SWEEP", reset.low_offset_translation_sweep.part_id, MOTION_ROLE, reset.low_offset_translation_sweep.solid, reset.package_sha256),
        MechanicalSolidRecord("MOTION_RIGHT_RELEASE_RESET_HIGH_SWEEP", reset.high_offset_translation_sweep.part_id, MOTION_ROLE, reset.high_offset_translation_sweep.solid, reset.package_sha256),
        MechanicalSolidRecord("FACTORY_RIGHT_SLIDER_INSERTION_SWEEP", source.insertion_sweep.part_id, MOTION_ROLE, source.insertion_sweep.solid, source.package_sha256),
        MechanicalSolidRecord("FACTORY_RIGHT_GUIDE_UPPER_DEFLECTED", source.upper_deflected.part_id, MOTION_ROLE, source.upper_deflected.solid, source.package_sha256),
    )

    states = (
        MechanicalStateRecord("LATCHED", "OPERATIONAL_RESET", ("MECH_RIGHT_SLIDER_LATCHED", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "positive tongue capture, nominal detent seated"),
        MechanicalStateRecord("RELEASING_DETENT_LIFTED", "OPERATIONAL_RESET", ("MECH_RIGHT_SLIDER_LATCHED", "MOTION_RIGHT_RESET_FLEXURE_LIFTED"), "anchored detent lift surrogate before +X translation"),
        MechanicalStateRecord("RELEASE_TRAVEL_LOW_OFFSET", "OPERATIONAL_RESET", ("MOTION_RIGHT_RELEASE_RESET_LOW_SWEEP", "MOTION_RIGHT_RESET_FLEXURE_LIFTED"), "exact low-offset translation interval with lifted detent"),
        MechanicalStateRecord("RELEASE_TRAVEL_HIGH_OFFSET", "OPERATIONAL_RESET", ("MOTION_RIGHT_RELEASE_RESET_HIGH_SWEEP", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "exact high-offset translation interval after detent clearance"),
        MechanicalStateRecord("RELEASED_RESET_REQUIRED", "OPERATIONAL_RESET", ("MOTION_RIGHT_SLIDER_RELEASED_STATE", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "slider at +7.3 mm outboard hard stop; tongue uncaptured; manual reset required"),
        MechanicalStateRecord("RESET_TRAVEL_HIGH_OFFSET", "OPERATIONAL_RESET", ("MOTION_RIGHT_RELEASE_RESET_HIGH_SWEEP", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "reverse -X traversal of high-offset interval"),
        MechanicalStateRecord("RESET_DETENT_LIFTED", "OPERATIONAL_RESET", ("MOTION_RIGHT_RESET_FLEXURE_LIFTED",), "detent lifted at controlled clear offset"),
        MechanicalStateRecord("RESET_TRAVEL_LOW_OFFSET", "OPERATIONAL_RESET", ("MOTION_RIGHT_RELEASE_RESET_LOW_SWEEP", "MOTION_RIGHT_RESET_FLEXURE_LIFTED"), "reverse -X traversal of low-offset interval"),
        MechanicalStateRecord("RESET_RESEATED_LATCHED", "OPERATIONAL_RESET", ("MECH_RIGHT_SLIDER_LATCHED", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "detent reseated and positive capture restored"),
        MechanicalStateRecord("GUIDE_OPEN_LOWER_HALF", "FACTORY_ASSEMBLY", ("MECH_RIGHT_GUIDE_LOWER",), "split guide open before captive-slider insertion"),
        MechanicalStateRecord("SLIDER_INSERTION", "FACTORY_ASSEMBLY", ("FACTORY_RIGHT_SLIDER_INSERTION_SWEEP", "MECH_RIGHT_GUIDE_LOWER"), f"exact connected-slider rigid insertion sweep over -Z {SLIDER_START_Z:.1f} mm"),
        MechanicalStateRecord("UPPER_CLOSURE_DESCENT_HOOKS_DEFLECTED", "FACTORY_ASSEMBLY", ("FACTORY_RIGHT_GUIDE_UPPER_DEFLECTED", "MECH_RIGHT_GUIDE_LOWER"), f"bounded upper closure descent from +Z {CLOSURE_START_Z:.1f} mm with {HOOK_DEFLECTION:.2f} mm hook deflection"),
        MechanicalStateRecord("HOOK_RELAXATION_TO_POSITIVE_CAPTURE", "FACTORY_ASSEMBLY", ("FACTORY_RIGHT_GUIDE_UPPER_DEFLECTED", "MECH_RIGHT_GUIDE_UPPER"), "bounded hook relaxation into positive shoulder capture"),
        MechanicalStateRecord("ASSEMBLED_OPERATIONAL", "FACTORY_ASSEMBLY", ("MECH_RIGHT_GUIDE_LOWER", "MECH_RIGHT_GUIDE_UPPER", "MECH_RIGHT_SLIDER_LATCHED", "MECH_RIGHT_RESET_FLEXURE_NOMINAL"), "factory assembly complete; operational release/reset state machine enabled"),
    )

    collision_motion = tuple(
        record
        for record in motion
        if record.assembly_id in {
            "MOTION_RIGHT_EXACT_WITHDRAWAL_SWEEP",
            "MOTION_RIGHT_RESET_FLEXURE_ENVELOPE",
            "MOTION_RIGHT_RELEASE_RESET_LOW_SWEEP",
            "MOTION_RIGHT_RELEASE_RESET_HIGH_SWEEP",
            "FACTORY_RIGHT_SLIDER_INSERTION_SWEEP",
            "FACTORY_RIGHT_GUIDE_UPPER_DEFLECTED",
        }
    )
    collision_checks = _moving_vs_released_checks(model, collision_motion)

    waste_release = build_current_cell4_waste_backbone_release()
    waste_checks = tuple(
        _route_edge_distance_record(route, moving)
        for moving in collision_motion
        for route in waste_release.realization.routes
    )

    integration = MechanicalPackageIntegration(
        binding=MechanicalSourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            source_cell3_pr=SOURCE_CELL3_PR,
            source_cell3_head_sha=SOURCE_CELL3_HEAD_SHA,
            authority_revision=AUTHORITY_REVISION,
            authority_blob_sha=AUTHORITY_BLOB_SHA,
            model_blob_sha=MODEL_BLOB_SHA,
            structural_frame_blob_sha=STRUCTURAL_FRAME_BLOB_SHA,
            cell3_source_blobs=CELL3_SOURCE_BLOBS,
            world_frame_id=WORLD_FRAME_ID,
        ),
        source_assembly_package_sha256=source.package_sha256,
        source_reset_package_sha256=reset.package_sha256,
        source_continuous_sweep_package_sha256=continuous.package_sha256,
        frame=frame_record,
        actuator_components=model.actuator_envelopes,
        static_solids=static,
        motion_solids=motion,
        states=states,
        collision_checks=collision_checks,
        waste_separation_checks=waste_checks,
        unresolved_integration=(
            "FULL_3D_STRUCTURAL_FRAME_AND_FRAME_TO_SHELL_JOIN_NOT_RELEASED",
            "LEFT_RETENTION_TO_FRAME_GEOMETRY_NOT_CURRENT_MAIN_RELEASED",
            "ACTUATOR_REACTION_CARRIERS_AND_FINAL_MECHANICAL_STOPS_NOT_CURRENT_MAIN_RELEASED",
            "FULL_POST_RELEASE_WHOLE_HEAD_REMOVAL_TRAJECTORY_OPEN",
            "RELEASE_FORCE_5_TO_12_N_PHYSICAL_GATE_OPEN",
            "RELEASE_TIME_LE_2S_PHYSICAL_GATE_OPEN",
            "WET_ONE_HAND_USE_FATIGUE_WEAR_AND_ACCIDENTAL_RELEASE_PHYSICAL_GATES_OPEN",
        ),
        evidence_status=DIGITAL_ONLY,
        physical_validation_eligible=False,
    )
    integration.validate()
    return integration


def export_mechanical_package_review(
    output_dir: str | Path,
    integration: MechanicalPackageIntegration | None = None,
) -> tuple[Path, ...]:
    integration = integration or build_mechanical_package_integration()
    integration.validate()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    static_step = root / "cell1_mechanical_static_candidate.step"
    cq.exporters.export(integration.static_compound, str(static_step))
    outputs.append(static_step)

    for record in integration.motion_solids:
        filename = record.assembly_id.lower() + ".step"
        path = root / filename
        cq.exporters.export(record.solid, str(path))
        outputs.append(path)

    manifest = root / "cell1_mechanical_package_ingestion_manifest.json"
    manifest.write_text(
        json.dumps(integration.manifest(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest)
    return tuple(outputs)
