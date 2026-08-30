from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .actuation_sweep_contract import ActuationDisplacementContract, ActuationSweepContractError
from .actuator_frames import ActuatorFrameArchitecture, ZONE_IDS
from .authority import Authority
from .interface_topology import (
    CompliantInterfaceTopology,
    ZONE_GENERAL_FACE,
    ZONE_T_FOREHEAD,
    ZONE_T_NOSE_PHILTRUM,
)
from .structural_frame import StructuralFrameTopology
from .sweep_geometry import AABB, LinearSweep


class ActuatorCouplingError(ValueError):
    """Raised when the Iteration-18 coupling/load-path contract is inconsistent or stale."""


SUPERIOR_IDS = ZONE_IDS[:2]
INFERIOR_IDS = ZONE_IDS[2:]


def _canonical_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ActuatorCouplingError(f"{label} must be an exact lowercase canonical SHA-256 digest")
    return value


def _nonblank(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ActuatorCouplingError(f"{label} must be an exact nonblank string")
    return value


@dataclass(frozen=True, slots=True)
class CouplingZone:
    zone_id: str
    coupling_node_id: str
    flexure_id: str
    reaction_path_id: str
    target_contact_zone_ids: tuple[str, ...]
    motion_axis_status: str
    flexure_geometry_status: str
    mechanical_stop_status: str
    protected_exclusion_status: str
    reaction_path_status: str
    off_axis_sensitivity_status: str

    def __post_init__(self) -> None:
        if self.zone_id not in ZONE_IDS:
            raise ActuatorCouplingError(f"Unknown actuator coupling zone {self.zone_id!r}")
        for label, value in (
            ("coupling node identity", self.coupling_node_id),
            ("flexure identity", self.flexure_id),
            ("reaction-path identity", self.reaction_path_id),
            ("motion-axis status", self.motion_axis_status),
            ("flexure status", self.flexure_geometry_status),
            ("mechanical-stop status", self.mechanical_stop_status),
            ("protected-exclusion status", self.protected_exclusion_status),
            ("reaction-path status", self.reaction_path_status),
            ("off-axis sensitivity status", self.off_axis_sensitivity_status),
        ):
            _nonblank(value, label=label)
        if not self.target_contact_zone_ids or len(set(self.target_contact_zone_ids)) != len(self.target_contact_zone_ids):
            raise ActuatorCouplingError("Each actuator coupling must reference unique non-empty compliant contact zones")
        if any(not isinstance(item, str) or not item or item.startswith("INTERFACE_OPENING_") for item in self.target_contact_zone_ids):
            raise ActuatorCouplingError("Actuator coupling cannot target a protected opening")

    def manifest(self) -> dict[str, object]:
        return {
            "zone_id": self.zone_id,
            "coupling_node_id": self.coupling_node_id,
            "flexure_id": self.flexure_id,
            "reaction_path_id": self.reaction_path_id,
            "target_contact_zone_ids": list(self.target_contact_zone_ids),
            "motion_axis_status": self.motion_axis_status,
            "flexure_geometry_status": self.flexure_geometry_status,
            "mechanical_stop_status": self.mechanical_stop_status,
            "protected_exclusion_status": self.protected_exclusion_status,
            "reaction_path_status": self.reaction_path_status,
            "off_axis_sensitivity_status": self.off_axis_sensitivity_status,
        }


@dataclass(frozen=True, slots=True)
class ActuatorCouplingArchitecture:
    source_actuator_architecture_sha256: str
    source_displacement_contract_sha256: str
    source_structural_frame_sha256: str
    source_interface_topology_sha256: str
    source_registered_mesh_sha256: str
    source_authority_revision: str
    zones: tuple[CouplingZone, ...]
    swept_volume_status: str
    collision_assertion_status: str
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        for label, value in (
            ("actuator architecture identity", self.source_actuator_architecture_sha256),
            ("displacement contract identity", self.source_displacement_contract_sha256),
            ("structural frame identity", self.source_structural_frame_sha256),
            ("interface topology identity", self.source_interface_topology_sha256),
            ("registered mesh identity", self.source_registered_mesh_sha256),
        ):
            _canonical_sha256(value, label=label)
        _nonblank(self.source_authority_revision, label="authority revision")
        if tuple(zone.zone_id for zone in self.zones) != ZONE_IDS:
            raise ActuatorCouplingError("Coupling zones must preserve the controlled four-zone order")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise ActuatorCouplingError("Digital coupling/load-path topology cannot be physical validation evidence")
        _nonblank(self.swept_volume_status, label="swept-volume status")
        _nonblank(self.collision_assertion_status, label="collision assertion status")
        _nonblank(self.evidence_status, label="evidence status")
        self._validate_bilateral_contract()

    def _validate_bilateral_contract(self) -> None:
        by_id = {zone.zone_id: zone for zone in self.zones}
        pairs = ((ZONE_IDS[0], ZONE_IDS[1]), (ZONE_IDS[2], ZONE_IDS[3]))
        for left_id, right_id in pairs:
            left = by_id[left_id]
            right = by_id[right_id]
            if left.target_contact_zone_ids != right.target_contact_zone_ids:
                raise ActuatorCouplingError("Bilateral coupling zones must use symmetric target-role contracts unless a controlled asymmetry exists")
            for field_name in (
                "motion_axis_status",
                "flexure_geometry_status",
                "mechanical_stop_status",
                "protected_exclusion_status",
                "reaction_path_status",
                "off_axis_sensitivity_status",
            ):
                if getattr(left, field_name) != getattr(right, field_name):
                    raise ActuatorCouplingError("Bilateral coupling status semantics must remain symmetric")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        actuator_architecture: ActuatorFrameArchitecture,
        displacement_contract: ActuationDisplacementContract,
        structural_frame: StructuralFrameTopology,
        interface_topology: CompliantInterfaceTopology,
    ) -> None:
        if self.source_actuator_architecture_sha256 != actuator_architecture.architecture_sha256:
            raise ActuatorCouplingError("Coupling architecture is stale for the actuator-frame architecture")
        if self.source_displacement_contract_sha256 != displacement_contract.contract_sha256:
            raise ActuatorCouplingError("Coupling architecture is stale for the actuation displacement contract")
        if self.source_structural_frame_sha256 != structural_frame.topology_sha256:
            raise ActuatorCouplingError("Coupling architecture is stale for the structural frame")
        if self.source_interface_topology_sha256 != interface_topology.topology_sha256:
            raise ActuatorCouplingError("Coupling architecture is stale for the compliant interface topology")
        if self.source_registered_mesh_sha256 != structural_frame.source_registered_mesh_sha256:
            raise ActuatorCouplingError("Coupling architecture registered-mesh provenance is stale")
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise ActuatorCouplingError("Coupling architecture authority revision is stale")
        known_contact = {zone.zone_id for zone in interface_topology.zones if zone.contact_intent}
        for zone in self.zones:
            if not set(zone.target_contact_zone_ids).issubset(known_contact):
                raise ActuatorCouplingError("Coupling architecture references a non-contact or stale interface zone")

    def require_sweep_analysis_ready(
        self,
        *,
        authority: Authority,
        actuator_architecture: ActuatorFrameArchitecture,
        displacement_contract: ActuationDisplacementContract,
        structural_frame: StructuralFrameTopology,
        interface_topology: CompliantInterfaceTopology,
    ) -> None:
        self.validate_current_sources(
            authority=authority,
            actuator_architecture=actuator_architecture,
            displacement_contract=displacement_contract,
            structural_frame=structural_frame,
            interface_topology=interface_topology,
        )
        try:
            displacement_contract.require_geometry_ready(
                authority=authority,
                architecture=actuator_architecture,
                structural_frame=structural_frame,
            )
        except ActuationSweepContractError as exc:
            raise ActuatorCouplingError(f"Rigid-body sweep/collision analysis remains blocked: {exc}") from exc

    def assert_no_rigid_body_interference(
        self,
        *,
        sweeps_by_zone: dict[str, LinearSweep],
        keepouts: tuple[AABB, ...],
        expected_geometry_sha256_by_zone: dict[str, str],
        clearance_mm: float = 0.0,
    ) -> None:
        if set(sweeps_by_zone) != set(ZONE_IDS) or set(expected_geometry_sha256_by_zone) != set(ZONE_IDS):
            raise ActuatorCouplingError("Collision assertion requires exactly one sweep and current geometry identity per actuator zone")
        if not keepouts:
            raise ActuatorCouplingError("Collision assertion requires at least one explicit adjacent-part/protected keepout")
        for zone_id in ZONE_IDS:
            sweep = sweeps_by_zone[zone_id]
            if sweep.source_id != zone_id:
                raise ActuatorCouplingError("Sweep source identity does not match its actuator zone")
            expected_sha = expected_geometry_sha256_by_zone[zone_id]
            for keepout in keepouts:
                if sweep.collides_with(keepout, expected_geometry_sha256=expected_sha, clearance_mm=clearance_mm):
                    raise ActuatorCouplingError(f"Rigid-body interference detected for {zone_id}")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_actuator_architecture_sha256": self.source_actuator_architecture_sha256,
            "source_displacement_contract_sha256": self.source_displacement_contract_sha256,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "source_interface_topology_sha256": self.source_interface_topology_sha256,
            "source_registered_mesh_sha256": self.source_registered_mesh_sha256,
            "source_authority_revision": self.source_authority_revision,
            "zones": [zone.manifest() for zone in self.zones],
            "swept_volume_status": self.swept_volume_status,
            "collision_assertion_status": self.collision_assertion_status,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_actuator_coupling_architecture(
    authority: Authority,
    actuator_architecture: ActuatorFrameArchitecture,
    displacement_contract: ActuationDisplacementContract,
    structural_frame: StructuralFrameTopology,
    interface_topology: CompliantInterfaceTopology,
) -> ActuatorCouplingArchitecture:
    superior_targets = (ZONE_GENERAL_FACE, ZONE_T_FOREHEAD)
    inferior_targets = (ZONE_GENERAL_FACE, ZONE_T_NOSE_PHILTRUM)
    zones = []
    for index, zone_id in enumerate(ZONE_IDS, start=1):
        targets = superior_targets if zone_id in SUPERIOR_IDS else inferior_targets
        zones.append(
            CouplingZone(
                zone_id=zone_id,
                coupling_node_id=f"MASCK_ONE-COUPLING-NODE-{index}",
                flexure_id=f"MASCK_ONE-ACTUATION-FLEXURE-{index}",
                reaction_path_id=f"MASCK_ONE-ACTUATION-REACTION-PATH-{index}",
                target_contact_zone_ids=targets,
                motion_axis_status="BOUND_TO_ACTUATOR_LOCAL_AXIS_ANGLE_SEMANTICS_PLACEMENT_AZIMUTH_UNRESOLVED",
                flexure_geometry_status="ABSTRACTION_ONLY_GEOMETRY_MATERIAL_STIFFNESS_AND_FATIGUE_UNRESOLVED",
                mechanical_stop_status="REQUIRED_INTERFACE_RESERVED_FINAL_STOP_GEOMETRY_AND_TRAVEL_MARGIN_UNRESOLVED",
                protected_exclusion_status="CONTACT_ROLE_MAPPING_EXCLUDES_PROTECTED_OPENINGS_3D_CLEARANCE_REMAINS_BLOCKED",
                reaction_path_status="TOPOLOGY_BINDS_COUPLING_TO_STRUCTURAL_ACTUATION_RESERVATION_LOADS_UNVALIDATED",
                off_axis_sensitivity_status="HANDOFF_HOOK_REQUIRED_NUMERIC_OFF_AXIS_LOAD_CASES_UNRESOLVED",
            )
        )
    architecture = ActuatorCouplingArchitecture(
        source_actuator_architecture_sha256=actuator_architecture.architecture_sha256,
        source_displacement_contract_sha256=displacement_contract.contract_sha256,
        source_structural_frame_sha256=structural_frame.topology_sha256,
        source_interface_topology_sha256=interface_topology.topology_sha256,
        source_registered_mesh_sha256=structural_frame.source_registered_mesh_sha256,
        source_authority_revision=str(authority.get("project", "authority_revision")),
        zones=tuple(zones),
        swept_volume_status="CONTINUOUS_TRANSLATION_PRIMITIVE_AVAILABLE_FINAL_3D_SWEEP_BLOCKED_BY_UNRESOLVED_ACTUATOR_PLACEMENT_ENVELOPE_AND_COUPLING_GEOMETRY",
        collision_assertion_status="FAIL_CLOSED_ENGINE_AVAILABLE_NO_PASS_CLAIM_UNTIL_CURRENT_3D_SWEEPS_AND_KEEPOUTS_EXIST",
        physical_validation_eligible=False,
        evidence_status="DIGITAL_COUPLING_REACTION_PATH_AND_COLLISION_CONTRACT_ONLY_NOT_FORCE_FATIGUE_ACOUSTIC_OR_PHYSICAL_COLLISION_EVIDENCE",
    )
    architecture.validate_current_sources(
        authority=authority,
        actuator_architecture=actuator_architecture,
        displacement_contract=displacement_contract,
        structural_frame=structural_frame,
        interface_topology=interface_topology,
    )
    return architecture
