from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

import cadquery as cq

from .authority import Authority
from .spatial import Point3
from .structural_frame import RESERVATION_RETENTION, StructuralFrameTopology


class WearableArchitectureError(ValueError):
    pass


CONTROL_STATE_PRINCIPLES = (
    "NO_FLUID_RELEASE_IN_UNDEFINED_OR_UNSAFE_STATE",
    "POWER_LOSS_DEFAULTS_TO_SAFE_FLUID_AND_ACTUATION_STATE",
    "MECHANICAL_RELEASE_INDEPENDENT_OF_FIRMWARE",
    "PUMP_ACTUATOR_AND_THERMAL_COMMANDS_STATE_MACHINE_CONTROLLED",
    "FAULTS_DISTINGUISH_RECOVERABLE_SERVICE_AND_UNSAFE_LOCKOUT_STATES",
    "INDICATORS_REPORT_ONLY_SENSED_OR_DETERMINISTICALLY_KNOWN_STATES",
)


@dataclass(frozen=True, slots=True)
class RetentionArchitecture:
    support_roles: tuple[str, ...]
    frame_reservation_id: str
    interface_points_mm: tuple[Point3, ...]
    facial_preload_transfer_status: str
    load_path_status: str
    fit_status: str

    def cad_interface_references(self) -> cq.Workplane:
        vertices = [cq.Vertex.makeVertex(*point.as_tuple()) for point in self.interface_points_mm]
        return cq.Workplane("XY").newObject([cq.Compound.makeCompound(vertices)])


@dataclass(frozen=True, slots=True)
class QuickReleaseArchitecture:
    release_time_max_s: float
    target_force_N: tuple[float, float]
    one_hand_wet_unpowered: bool
    pinch_keepout_status: str
    hair_keepout_status: str
    accidental_activation_status: str
    reset_semantics_status: str
    test_fixture_handoff_status: str
    geometry_status: str


@dataclass(frozen=True, slots=True)
class DryBayArchitecture:
    battery_reference_id: str
    battery_envelope_mm: tuple[float, float, float]
    battery_center_mm: Point3
    nominal_voltage_V: float
    benchmark_capacity_mAh: float
    benchmark_mass_g: float
    swelling_clearance_mm: float | None
    protection_status: str
    charging_status: str
    harness_status: str
    strain_relief_status: str
    ingress_status: str
    thermal_isolation_status: str
    production_selection_status: str

    def cad_battery_reference(self) -> cq.Workplane:
        x, y, z = self.battery_envelope_mm
        return cq.Workplane("XY").box(x, y, z, centered=(True, True, True)).translate(
            self.battery_center_mm.as_tuple()
        )


@dataclass(frozen=True, slots=True)
class PhysicalControl:
    control_id: str
    semantic_reservation: str
    position_mm: Point3 | None
    wet_access_status: str
    tactile_status: str
    seal_status: str
    indication_status: str


@dataclass(frozen=True, slots=True)
class HMIArchitecture:
    controls: tuple[PhysicalControl, ...]
    state_principles: tuple[str, ...]
    firmware_contract_status: str


@dataclass(frozen=True, slots=True)
class ThermalArchitecture:
    warm_heater_reference: str
    warm_heater_geometry_status: str
    warm_sensor_location_status: str
    warm_limit_status: str
    warm_fault_shutdown_status: str
    cool_implementation_status: str
    cool_condensation_model_status: str
    cool_dew_point_model_status: str
    cool_heat_rejection_status: str
    cool_power_status: str


@dataclass(frozen=True, slots=True)
class WearableArchitecture:
    source_structural_frame_sha256: str
    retention: RetentionArchitecture
    quick_release: QuickReleaseArchitecture
    dry_bay: DryBayArchitecture
    hmi: HMIArchitecture
    thermal: ThermalArchitecture
    completed_iterations: tuple[int, ...]
    evidence_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_structural_frame_sha256) != 64:
            raise WearableArchitectureError("Wearable architecture requires an exact structural-frame hash")
        if self.retention.support_roles != ("HALO", "OCCIPITAL", "CROWN"):
            raise WearableArchitectureError("Retention must reserve halo, occipital and crown support")
        release = self.quick_release
        if not release.one_hand_wet_unpowered or release.release_time_max_s > 2.0:
            raise WearableArchitectureError("Quick release must preserve frozen one-hand wet unpowered safety behavior")
        if release.target_force_N[0] > release.target_force_N[1]:
            raise WearableArchitectureError("Quick-release target force range must be ordered")
        if self.dry_bay.swelling_clearance_mm is not None:
            raise WearableArchitectureError("Battery swelling clearance requires selected pack evidence")
        if len(self.hmi.controls) != 4 or len({control.control_id for control in self.hmi.controls}) != 4:
            raise WearableArchitectureError("HMI baseline requires four unique physical controls")
        if any(control.position_mm is not None for control in self.hmi.controls):
            raise WearableArchitectureError("HMI positions remain unresolved without industrial-design closure")
        if self.hmi.state_principles != CONTROL_STATE_PRINCIPLES:
            raise WearableArchitectureError("HMI must preserve every brief-required control-state principle")
        if self.completed_iterations != tuple(range(29, 35)):
            raise WearableArchitectureError("Wearable tranche must close digital architecture Iterations 29-34")
        if self.physical_validation_eligible:
            raise WearableArchitectureError("Wearable digital architecture is not physical safety or fit evidence")

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "retention": {
                **asdict(self.retention),
                "interface_points_mm": [list(point.as_tuple()) for point in self.retention.interface_points_mm],
            },
            "quick_release": asdict(self.quick_release),
            "dry_bay": {
                **asdict(self.dry_bay),
                "battery_center_mm": list(self.dry_bay.battery_center_mm.as_tuple()),
            },
            "hmi": {
                "controls": [
                    {**asdict(control), "position_mm": None}
                    for control in self.hmi.controls
                ],
                "state_principles": list(self.hmi.state_principles),
                "firmware_contract_status": self.hmi.firmware_contract_status,
            },
            "thermal": asdict(self.thermal),
            "completed_iterations": list(self.completed_iterations),
            "evidence_status": self.evidence_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def build_wearable_architecture(
    authority: Authority,
    frame: StructuralFrameTopology,
    battery_center_mm: Point3,
) -> WearableArchitecture:
    retention_reservations = [
        reservation for reservation in frame.reservations
        if reservation.reservation_id == RESERVATION_RETENTION
    ]
    if len(retention_reservations) != 1:
        raise WearableArchitectureError("Official frame must expose exactly one retention reservation")
    interface_points = tuple(Point3(datum.x_mm, datum.y_mm, 0.0) for datum in frame.datums)
    retention = RetentionArchitecture(
        ("HALO", "OCCIPITAL", "CROWN"),
        RESERVATION_RETENTION,
        interface_points,
        "CONTROLLED_PRELOAD_TRANSFER_TO_OFF_FACE_SUPPORT_REQUIRES_HEADFORM_EVIDENCE",
        "TOPOLOGY_HANDOFF_ONLY_MEMBER_GEOMETRY_AND_LOADS_UNRESOLVED",
        "BLOCKED_PENDING_REPRESENTATIVE_HEADFORM_MATRIX",
    )
    release = QuickReleaseArchitecture(
        authority.number("safety", "quick_release", "time_max_s"),
        tuple(float(value) for value in authority.get("safety", "quick_release", "force_target_N")),
        bool(authority.get("safety", "quick_release", "one_hand_wet_unpowered")),
        "PINCH_KEEP_OUT_REQUIRED_GEOMETRY_UNRESOLVED",
        "HAIR_KEEP_OUT_REQUIRED_GEOMETRY_UNRESOLVED",
        "ACCIDENTAL_ACTIVATION_RESISTANCE_REQUIRES_MECHANISM_AND_RIG",
        "RESET_REQUIRES_EXPLICIT_USER_SAFE_STATE_TRANSITION",
        "MEASURABLE_RELEASE_TIME_FORCE_AND_WET_GRIP_FIXTURE_REQUIRED",
        "MECHANISM_GEOMETRY_BLOCKED_PENDING_RETENTION_MEMBER_GEOMETRY",
    )
    dry_bay = DryBayArchitecture(
        str(authority.get("battery_reference", "candidate")),
        tuple(float(value) for value in authority.get("battery_reference", "envelope_mm")),
        battery_center_mm,
        authority.number("battery_reference", "nominal_voltage_V"),
        authority.number("battery_reference", "capacity_mAh"),
        authority.number("battery_reference", "mass_g"),
        None,
        "CELL_PACK_PROTECTION_ARCHITECTURE_UNRESOLVED",
        "CHARGING_ARCHITECTURE_AND_COMPLIANCE_UNRESOLVED",
        "HARNESS_CONNECTORS_AND_ROUTING_UNRESOLVED",
        "STRAIN_RELIEF_GEOMETRY_UNRESOLVED",
        "DRY_BAY_INGRESS_BOUNDARY_REQUIRES_SEAL_ARCHITECTURE_AND_TEST",
        "THERMAL_ISOLATION_REQUIRES_LOAD_AND_FAULT_MODEL",
        str(authority.get("battery_reference", "status")),
    )
    controls = tuple(
        PhysicalControl(
            f"CONTROL_{index:02d}",
            semantic,
            None,
            "WET_USE_ACCESS_REQUIRED_POSITION_UNRESOLVED",
            "TACTILE_DIFFERENTIATION_REQUIRED_GEOMETRY_UNRESOLVED",
            "SEALED_INTERFACE_REQUIRED_STACK_UNRESOLVED",
            "REPORT_ONLY_SENSED_OR_DETERMINISTIC_STATE",
        )
        for index, semantic in enumerate(
            ("CLEAN_BASELINE", "WARM_RESERVATION", "COOL_EXPERIMENTAL_RESERVATION", "UNASSIGNED_PENDING_FIRMWARE_CONTRACT"),
            start=1,
        )
    )
    hmi = HMIArchitecture(
        controls,
        CONTROL_STATE_PRINCIPLES,
        "STATE_MACHINE_SCHEMA_DEFINED_COMMAND_TIMING_FAULT_RECOVERY_AND_FINAL_MODE_SEMANTICS_UNRESOLVED",
    )
    thermal = ThermalArchitecture(
        "MINCO_CLASS_POLYIMIDE_DEVELOPMENT_REFERENCE",
        "LOCALIZED_HEATER_ENVELOPE_UNRESOLVED",
        "SKIN_FACING_SENSOR_LOCATION_UNRESOLVED",
        "CLOSED_LOOP_LIMIT_AND_MAXIMUM_TEMPERATURE_REQUIRE_THERMAL_EVIDENCE",
        "POWER_REMOVAL_AND_FAULT_SHUTDOWN_LOGIC_REQUIRED_NOT_VALIDATED",
        "EXPERIMENTAL_RESERVATION_NO_FROZEN_THERMOELECTRIC_IMPLEMENTATION",
        "BLOCKED_PENDING_AMBIENT_HUMIDITY_SURFACE_AND_AIRFLOW_MODEL",
        "BLOCKED_PENDING_ENVIRONMENTAL_INPUTS",
        "BLOCKED_PENDING_HOT_SIDE_PATH_AND_WEARABLE_BOUNDARY",
        "BLOCKED_PENDING_COMPONENT_AND_DUTY_CYCLE_SELECTION",
    )
    return WearableArchitecture(
        frame.topology_sha256,
        retention,
        release,
        dry_bay,
        hmi,
        thermal,
        tuple(range(29, 35)),
        "NOT_RETENTION_FIT_RELEASE_SAFETY_ELECTRICAL_INGRESS_HMI_OR_THERMAL_VALIDATION",
    )
