from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .actuation_sweep_contract import build_actuation_displacement_contract
from .actuator_coupling import build_actuator_coupling_architecture
from .actuator_frames import ZONE_IDS, build_actuator_frame_architecture
from .boundary_release import build_verified_interface_boundary_topology
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model
from .structural_frame import build_structural_frame_topology


@dataclass(frozen=True)
class ActuatorCouplingPreflightCheck:
    id: str
    status: str
    message: str
    actual: object | None = None
    expected: object | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


def run_actuator_coupling_preflight() -> dict[str, object]:
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    actuators = build_actuator_frame_architecture(model.authority, frame)
    displacement = build_actuation_displacement_contract(model.authority, actuators)
    coupling = build_actuator_coupling_architecture(
        model.authority,
        actuators,
        displacement,
        frame,
        model.compliant_interface_topology,
    )

    contact_ids = {zone.zone_id for zone in model.compliant_interface_topology.zones if zone.contact_intent}
    checks = [
        ActuatorCouplingPreflightCheck(
            "COUPLING_SOURCE_CHAIN",
            "PASS" if (
                coupling.source_actuator_architecture_sha256 == actuators.architecture_sha256
                and coupling.source_displacement_contract_sha256 == displacement.contract_sha256
                and coupling.source_structural_frame_sha256 == frame.topology_sha256
                and coupling.source_interface_topology_sha256 == model.compliant_interface_topology.topology_sha256
                and coupling.source_registered_mesh_sha256 == frame.source_registered_mesh_sha256
            ) else "FAIL",
            "Coupling topology is cryptographically bound to the released actuator, displacement, structural and interface sources.",
        ),
        ActuatorCouplingPreflightCheck(
            "COUPLING_ZONE_COMPLETENESS",
            "PASS" if tuple(zone.zone_id for zone in coupling.zones) == ZONE_IDS else "FAIL",
            "All four frozen actuator zones have stable coupling, flexure and reaction-path identities.",
            actual=[zone.zone_id for zone in coupling.zones],
            expected=list(ZONE_IDS),
        ),
        ActuatorCouplingPreflightCheck(
            "COUPLING_PROTECTED_EXCLUSION",
            "PASS" if all(set(zone.target_contact_zone_ids).issubset(contact_ids) for zone in coupling.zones) else "FAIL",
            "Coupling role mapping targets only compliant contact regions and never a protected opening.",
            actual={zone.zone_id: list(zone.target_contact_zone_ids) for zone in coupling.zones},
        ),
        ActuatorCouplingPreflightCheck(
            "COUPLING_BILATERAL_CONTRACT",
            "PASS" if (
                coupling.zones[0].target_contact_zone_ids == coupling.zones[1].target_contact_zone_ids
                and coupling.zones[2].target_contact_zone_ids == coupling.zones[3].target_contact_zone_ids
            ) else "FAIL",
            "Left/right coupling semantics remain bilaterally symmetric until a controlled asymmetry is justified.",
        ),
        ActuatorCouplingPreflightCheck(
            "COUPLING_SWEEP_GATE",
            "PASS" if (
                actuators.sweep_ready is False
                and "BLOCKED_BY_UNRESOLVED_ACTUATOR_PLACEMENT" in coupling.swept_volume_status
                and "NO_PASS_CLAIM" in coupling.collision_assertion_status
            ) else "FAIL",
            "Continuous sweep/collision machinery exists, but current unresolved actuator placement/envelopes prevent a false digital collision pass.",
            actual={"actuator_sweep_ready": actuators.sweep_ready, "swept_volume_status": coupling.swept_volume_status},
        ),
        ActuatorCouplingPreflightCheck(
            "COUPLING_EVIDENCE_BOUNDARY",
            "PASS" if coupling.physical_validation_eligible is False else "FAIL",
            "Coupling topology, flexure abstractions and collision contracts remain digital-only evidence.",
            actual=coupling.evidence_status,
        ),
    ]
    result = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    return {
        "project": "Masck One",
        "phase": 3,
        "iteration": 18,
        "result": result,
        "checks": [check.to_dict() for check in checks],
        "actuator_coupling_architecture_sha256": coupling.architecture_sha256,
    }


def main() -> int:
    report = run_actuator_coupling_preflight()
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
