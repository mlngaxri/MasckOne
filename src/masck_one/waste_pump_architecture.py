"""Iteration 26 mixed-phase waste-pump architecture.

This is the single reconciled Iteration 26 owner. It combines repository-rooted
Iteration 25 current-source proof with an explicit passive backflow-barrier stage.
It does not select a pump or barrier component and does not claim pressure-flow,
recovery, containment, orientation, hygiene, cartridge, or physical performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from .authority import Authority
from .distribution_geometry import DistributionGeometryArchitecture
from .structural_frame import RESERVATION_WASTE, StructuralFrameTopology
from .waste_acquisition import (
    PHASE_MIXED_WASTE,
    ROUTE_DESTINATION,
    WasteAcquisitionArchitecture,
    WasteAcquisitionError,
)


class WastePumpArchitectureError(ValueError):
    """Raised when Iteration 26 topology or evidence contracts are violated."""


STATION_WASTE = "PUMP-STATION-WASTE-I26"
BARRIER_WASTE = "PASSIVE-BACKFLOW-BARRIER-WASTE-I26"
INTERFACE_PUMP_OUTLET = "WASTE_PUMP_OUTLET_ITERATION_26_INTERFACE"
INTERFACE_BARRIER_OUTLET = "WASTE_BACKFLOW_BARRIER_OUTLET_ITERATION_26_INTERFACE"
INTERFACE_CARTRIDGE_INLET_I27 = "WASTE_CARTRIDGE_INLET_ITERATION_27_INTERFACE"

ROUTE_ACQUISITION_TO_PUMP = "ROUTE-WASTE-ACQUISITION-TO-PUMP-I26"
ROUTE_PUMP_TO_BARRIER = "ROUTE-WASTE-PUMP-TO-BACKFLOW-BARRIER-I26"
ROUTE_BARRIER_TO_CARTRIDGE = "ROUTE-WASTE-BARRIER-TO-CARTRIDGE-I27"
ROUTE_IDS = (
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_PUMP_TO_BARRIER,
    ROUTE_BARRIER_TO_CARTRIDGE,
)
ROUTE_STAGES = (
    "ACQUISITION_TO_PUMP",
    "PUMP_TO_PASSIVE_BACKFLOW_BARRIER",
    "PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF",
)

FAULT_IDS = (
    "PUMP_OFF_POWER_LOSS",
    "PUMP_STALL_OR_NO_MOTION",
    "GAS_INGESTION",
    "LIQUID_SLUGGING",
    "FOAM_INGESTION",
    "CONTAMINANT_INGESTION",
    "UPSTREAM_ROUTE_OCCLUSION",
    "DOWNSTREAM_ROUTE_OCCLUSION",
    "BACKFLOW_RISK",
    "PROTECTED_REGION_POOLING_RISK",
    "CARTRIDGE_MISSING",
    "CARTRIDGE_MISINSTALLED",
    "CARTRIDGE_FULL_OR_REDUCED_RETENTION",
)

PACKAGE_STATUS = "UNRESOLVED_PENDING_CONTROLLED_MIXED_PHASE_PUMP_PACKAGE_EVIDENCE"
ROUTING_STATUS = (
    "INTERFACE_TOPOLOGY_ONLY_CENTERLINES_TUBING_CONNECTORS_AND_SERVICE_CLEARANCE_UNRESOLVED"
)
HYDRAULIC_STATUS = (
    "VALIDATION_GATED_PENDING_MIXED_PHASE_PRESSURE_FLOW_RECOVERY_ORIENTATION_AND_LEAKAGE_EVIDENCE"
)
SERVICE_STATUS = "ACCESS_REPLACEMENT_PURGE_DRAIN_DRY_AND_STRAIN_RELIEF_UNRESOLVED"
BARRIER_SELECTION_STATUS = "UNRESOLVED_PENDING_CONTROLLED_PASSIVE_BACKFLOW_COMPONENT_EVIDENCE"
BARRIER_PERFORMANCE_STATUS = (
    "VALIDATION_GATED_PENDING_REVERSE_FLOW_CRACKING_LEAKAGE_FOAM_CONTAMINANT_AND_ORIENTATION_EVIDENCE"
)
FAULT_DETECTION_STATUS = "UNRESOLVED_PENDING_SENSOR_CONTROL_AND_DIAGNOSTIC_ARCHITECTURE"
FAULT_MITIGATION_STATUS = "UNRESOLVED_PENDING_FAIL_SAFE_CONTROL_AND_PHYSICAL_CONTAINMENT_DESIGN"
FAULT_VALIDATION_STATUS = "VALIDATION_GATED_PENDING_MIXED_PHASE_FAULT_INJECTION_EVIDENCE"
FAULT_REPORTING_STATUS = "FAULT_CASE_CANNOT_BE_TREATED_AS_VALIDATED_RECOVERY_OR_CONTAINMENT"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_MIXED_PHASE_WASTE_PUMP_PASSIVE_BACKFLOW_ROUTING_AND_FAULT_ARCHITECTURE_ONLY_"
    "NOT_PUMP_SELECTION_HYDRAULIC_RECOVERY_LEAKAGE_CONTAINMENT_HYGIENE_CARTRIDGE_OR_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _exact(value: object, expected: str, *, label: str) -> str:
    if type(value) is not str or value != expected:
        raise WastePumpArchitectureError(f"{label} must use its controlled exact state")
    return value


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WastePumpArchitectureError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, *, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise WastePumpArchitectureError(f"{label} must be canonical lowercase SHA-256")
    return value


def _real(
    value: object,
    *,
    label: str,
    positive: bool = False,
    nonnegative: bool = False,
    at_most: float | None = None,
) -> float:
    if type(value) not in (int, float):
        raise WastePumpArchitectureError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise WastePumpArchitectureError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise WastePumpArchitectureError(f"{label} must be finite")
    if result == 0.0:
        result = 0.0
    if positive and result <= 0.0:
        raise WastePumpArchitectureError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise WastePumpArchitectureError(f"{label} must be nonnegative")
    if at_most is not None and result > at_most:
        raise WastePumpArchitectureError(f"{label} must be <= {at_most}")
    return result


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class WastePumpStationReservation:
    station_id: str
    phase_semantics: str
    source_waste_acquisition_sha256: str
    pump_inlet_interface_id: str
    pump_outlet_interface_id: str
    frame_reservation_id: str
    package_candidate_id: None = None
    package_evidence_sha256: None = None
    envelope_mm: None = None
    placement_xyz_mm: None = None
    orientation_axis_xyz: None = None
    tubing_inner_diameter_mm: None = None
    minimum_bend_radius_mm: None = None
    connector_standard: None = None
    nominal_mixed_phase_flow_mL_s: None = None
    suction_pressure_kPa: None = None
    discharge_pressure_kPa: None = None
    package_status: str = PACKAGE_STATUS
    routing_status: str = ROUTING_STATUS
    hydraulic_status: str = HYDRAULIC_STATUS
    service_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _exact(self.station_id, STATION_WASTE, label="waste pump station ID")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="waste pump phase semantics")
        _sha(self.source_waste_acquisition_sha256, label="waste pump source acquisition")
        _exact(self.pump_inlet_interface_id, ROUTE_DESTINATION, label="waste pump inlet interface")
        _exact(self.pump_outlet_interface_id, INTERFACE_PUMP_OUTLET, label="waste pump outlet interface")
        _exact(self.frame_reservation_id, RESERVATION_WASTE, label="waste frame reservation")
        unresolved = (
            self.package_candidate_id,
            self.package_evidence_sha256,
            self.envelope_mm,
            self.placement_xyz_mm,
            self.orientation_axis_xyz,
            self.tubing_inner_diameter_mm,
            self.minimum_bend_radius_mm,
            self.connector_standard,
            self.nominal_mixed_phase_flow_mL_s,
            self.suction_pressure_kPa,
            self.discharge_pressure_kPa,
        )
        if any(value is not None for value in unresolved):
            raise WastePumpArchitectureError(
                "Iteration 26 cannot invent pump selection, package geometry, placement, tubing, connector, flow, or pressure"
            )
        _exact(self.package_status, PACKAGE_STATUS, label="waste pump package status")
        _exact(self.routing_status, ROUTING_STATUS, label="waste pump routing status")
        _exact(self.hydraulic_status, HYDRAULIC_STATUS, label="waste pump hydraulic status")
        _exact(self.service_status, SERVICE_STATUS, label="waste pump service status")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "station_id": self.station_id,
            "phase_semantics": self.phase_semantics,
            "source_waste_acquisition_sha256": self.source_waste_acquisition_sha256,
            "pump_inlet_interface_id": self.pump_inlet_interface_id,
            "pump_outlet_interface_id": self.pump_outlet_interface_id,
            "frame_reservation_id": self.frame_reservation_id,
            "package_candidate_id": self.package_candidate_id,
            "package_evidence_sha256": self.package_evidence_sha256,
            "envelope_mm": self.envelope_mm,
            "placement_xyz_mm": self.placement_xyz_mm,
            "orientation_axis_xyz": self.orientation_axis_xyz,
            "tubing_inner_diameter_mm": self.tubing_inner_diameter_mm,
            "minimum_bend_radius_mm": self.minimum_bend_radius_mm,
            "connector_standard": self.connector_standard,
            "nominal_mixed_phase_flow_mL_s": self.nominal_mixed_phase_flow_mL_s,
            "suction_pressure_kPa": self.suction_pressure_kPa,
            "discharge_pressure_kPa": self.discharge_pressure_kPa,
            "package_status": self.package_status,
            "routing_status": self.routing_status,
            "hydraulic_status": self.hydraulic_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class PassiveBackflowBarrierReservation:
    barrier_id: str
    phase_semantics: str
    source_interface_id: str
    target_interface_id: str
    component_candidate_id: None = None
    component_evidence_sha256: None = None
    envelope_mm: None = None
    placement_xyz_mm: None = None
    orientation_axis_xyz: None = None
    cracking_pressure_kPa: None = None
    reverse_leakage_mL_min: None = None
    selection_status: str = BARRIER_SELECTION_STATUS
    performance_status: str = BARRIER_PERFORMANCE_STATUS
    service_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _exact(self.barrier_id, BARRIER_WASTE, label="backflow barrier ID")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="backflow barrier phase semantics")
        _exact(self.source_interface_id, INTERFACE_PUMP_OUTLET, label="backflow barrier source interface")
        _exact(self.target_interface_id, INTERFACE_BARRIER_OUTLET, label="backflow barrier target interface")
        unresolved = (
            self.component_candidate_id,
            self.component_evidence_sha256,
            self.envelope_mm,
            self.placement_xyz_mm,
            self.orientation_axis_xyz,
            self.cracking_pressure_kPa,
            self.reverse_leakage_mL_min,
        )
        if any(value is not None for value in unresolved):
            raise WastePumpArchitectureError(
                "Iteration 26 cannot invent passive backflow component, geometry, placement, cracking pressure, or leakage"
            )
        _exact(self.selection_status, BARRIER_SELECTION_STATUS, label="backflow barrier selection status")
        _exact(self.performance_status, BARRIER_PERFORMANCE_STATUS, label="backflow barrier performance status")
        _exact(self.service_status, SERVICE_STATUS, label="backflow barrier service status")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "barrier_id": self.barrier_id,
            "phase_semantics": self.phase_semantics,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "component_candidate_id": self.component_candidate_id,
            "component_evidence_sha256": self.component_evidence_sha256,
            "envelope_mm": self.envelope_mm,
            "placement_xyz_mm": self.placement_xyz_mm,
            "orientation_axis_xyz": self.orientation_axis_xyz,
            "cracking_pressure_kPa": self.cracking_pressure_kPa,
            "reverse_leakage_mL_min": self.reverse_leakage_mL_min,
            "selection_status": self.selection_status,
            "performance_status": self.performance_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class WasteRouteInterface:
    route_id: str
    stage: str
    phase_semantics: str
    source_interface_id: str
    target_interface_id: str
    geometry_status: str = ROUTING_STATUS
    hydraulic_status: str = HYDRAULIC_STATUS
    service_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        if type(self.route_id) is not str or self.route_id not in ROUTE_IDS:
            raise WastePumpArchitectureError("waste route must use a controlled Iteration 26 route ID")
        if type(self.stage) is not str or self.stage not in ROUTE_STAGES:
            raise WastePumpArchitectureError("waste route stage must use the controlled vocabulary")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="waste route phase semantics")
        _text(self.source_interface_id, label="waste route source interface")
        _text(self.target_interface_id, label="waste route target interface")
        _exact(self.geometry_status, ROUTING_STATUS, label="waste route geometry status")
        _exact(self.hydraulic_status, HYDRAULIC_STATUS, label="waste route hydraulic status")
        _exact(self.service_status, SERVICE_STATUS, label="waste route service status")

    def manifest(self) -> dict[str, str]:
        self.validate_invariants()
        return {
            "route_id": self.route_id,
            "stage": self.stage,
            "phase_semantics": self.phase_semantics,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "geometry_status": self.geometry_status,
            "hydraulic_status": self.hydraulic_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class WastePumpFaultIntent:
    fault_id: str
    phase_semantics: str
    detection_status: str = FAULT_DETECTION_STATUS
    mitigation_implementation_status: str = FAULT_MITIGATION_STATUS
    validation_status: str = FAULT_VALIDATION_STATUS
    reporting_status: str = FAULT_REPORTING_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        if type(self.fault_id) is not str or self.fault_id not in FAULT_IDS:
            raise WastePumpArchitectureError("waste pump fault must use a controlled Iteration 26 fault ID")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, label="waste fault phase semantics")
        _exact(self.detection_status, FAULT_DETECTION_STATUS, label="waste fault detection status")
        _exact(self.mitigation_implementation_status, FAULT_MITIGATION_STATUS, label="waste fault mitigation status")
        _exact(self.validation_status, FAULT_VALIDATION_STATUS, label="waste fault validation status")
        _exact(self.reporting_status, FAULT_REPORTING_STATUS, label="waste fault reporting status")

    def manifest(self) -> dict[str, str]:
        self.validate_invariants()
        return {
            "fault_id": self.fault_id,
            "phase_semantics": self.phase_semantics,
            "detection_status": self.detection_status,
            "mitigation_implementation_status": self.mitigation_implementation_status,
            "validation_status": self.validation_status,
            "reporting_status": self.reporting_status,
        }


@dataclass(frozen=True, slots=True)
class WastePumpArchitecture:
    source_waste_acquisition_sha256: str
    source_structural_frame_sha256: str
    source_authority_revision: str
    recovery_ratio_requirement_min: float
    residual_free_liquid_limit_uL: float
    station: WastePumpStationReservation
    barrier: PassiveBackflowBarrierReservation
    routes: tuple[WasteRouteInterface, ...]
    faults: tuple[WastePumpFaultIntent, ...]
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _sha(self.source_waste_acquisition_sha256, label="source waste acquisition")
        _sha(self.source_structural_frame_sha256, label="source structural frame")
        _text(self.source_authority_revision, label="source authority revision")
        recovery = _real(
            self.recovery_ratio_requirement_min,
            label="waste recovery ratio requirement",
            positive=True,
            at_most=1.0,
        )
        residual = _real(
            self.residual_free_liquid_limit_uL,
            label="waste residual free-liquid limit",
            nonnegative=True,
        )
        if type(self.station) is not WastePumpStationReservation:
            raise WastePumpArchitectureError("station must use the exact pump-station reservation type")
        if type(self.barrier) is not PassiveBackflowBarrierReservation:
            raise WastePumpArchitectureError("barrier must use the exact passive-barrier reservation type")
        self.station.validate_invariants()
        self.barrier.validate_invariants()
        if self.station.source_waste_acquisition_sha256 != self.source_waste_acquisition_sha256:
            raise WastePumpArchitectureError("station source must bind the exact Iteration 25 acquisition")

        if type(self.routes) is not tuple or any(type(item) is not WasteRouteInterface for item in self.routes):
            raise WastePumpArchitectureError("routes must be an immutable tuple of exact route records")
        if tuple(item.route_id for item in self.routes) != ROUTE_IDS:
            raise WastePumpArchitectureError("routes must retain the complete controlled route order")
        for item in self.routes:
            item.validate_invariants()
        expected_routes = (
            (ROUTE_ACQUISITION_TO_PUMP, "ACQUISITION_TO_PUMP", ROUTE_DESTINATION, STATION_WASTE),
            (ROUTE_PUMP_TO_BARRIER, "PUMP_TO_PASSIVE_BACKFLOW_BARRIER", INTERFACE_PUMP_OUTLET, BARRIER_WASTE),
            (
                ROUTE_BARRIER_TO_CARTRIDGE,
                "PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF",
                INTERFACE_BARRIER_OUTLET,
                INTERFACE_CARTRIDGE_INLET_I27,
            ),
        )
        actual_routes = tuple(
            (item.route_id, item.stage, item.source_interface_id, item.target_interface_id)
            for item in self.routes
        )
        if actual_routes != expected_routes:
            raise WastePumpArchitectureError(
                "waste routes cannot bypass, reverse, cross, or alias the passive backflow stage"
            )

        if type(self.faults) is not tuple or any(type(item) is not WastePumpFaultIntent for item in self.faults):
            raise WastePumpArchitectureError("faults must be an immutable tuple of exact fault records")
        if tuple(item.fault_id for item in self.faults) != FAULT_IDS:
            raise WastePumpArchitectureError("faults must retain the complete controlled fault order")
        for item in self.faults:
            item.validate_invariants()

        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WastePumpArchitectureError("Iteration 26 digital architecture is not physical validation evidence")
        _exact(self.evidence_status, ARCHITECTURE_EVIDENCE_STATUS, label="architecture evidence status")
        object.__setattr__(self, "recovery_ratio_requirement_min", recovery)
        object.__setattr__(self, "residual_free_liquid_limit_uL", residual)

    def validate_current_sources(
        self,
        *,
        authority: Authority,
        acquisition: WasteAcquisitionArchitecture,
        distribution: DistributionGeometryArchitecture,
        frame: StructuralFrameTopology,
    ) -> None:
        self.validate_invariants()
        if type(authority) is not Authority:
            raise WastePumpArchitectureError("authority must be the exact Authority type")
        if type(acquisition) is not WasteAcquisitionArchitecture:
            raise WastePumpArchitectureError("acquisition must be the exact Iteration 25 architecture type")
        if type(distribution) is not DistributionGeometryArchitecture:
            raise WastePumpArchitectureError("distribution must be the exact Iteration 24 architecture type")
        if type(frame) is not StructuralFrameTopology:
            raise WastePumpArchitectureError("frame must be the exact structural-frame topology type")
        try:
            acquisition.validate_current_sources(
                authority=authority,
                distribution=distribution,
                frame=frame,
            )
        except WasteAcquisitionError as exc:
            raise WastePumpArchitectureError(
                "Iteration 25 waste acquisition or inherited source graph is stale"
            ) from exc

        if self.source_waste_acquisition_sha256 != acquisition.architecture_sha256:
            raise WastePumpArchitectureError("architecture is stale for current Iteration 25 acquisition")
        if self.source_structural_frame_sha256 != frame.topology_sha256:
            raise WastePumpArchitectureError("architecture is stale for current structural frame")

        current_revision = _text(
            authority.get("project", "authority_revision"),
            label="current authority revision",
        )
        if self.source_authority_revision != current_revision:
            raise WastePumpArchitectureError("architecture is stale for current authority revision")

        waste = authority.get("fluid", "waste")
        if type(waste) is not dict:
            raise WastePumpArchitectureError("waste authority must be an exact mapping")
        _exact(waste.get("status"), "VALIDATION_GATED", label="waste authority performance status")
        expected_recovery = _real(
            waste.get("recovery_ratio_min"),
            label="waste authority recovery ratio",
            positive=True,
            at_most=1.0,
        )
        expected_residual = _real(
            waste.get("residual_free_liquid_max_uL"),
            label="waste authority residual free-liquid limit",
            nonnegative=True,
        )
        if self.recovery_ratio_requirement_min != expected_recovery:
            raise WastePumpArchitectureError("recovery requirement is stale")
        if self.residual_free_liquid_limit_uL != expected_residual:
            raise WastePumpArchitectureError("residual-liquid requirement is stale")
        if acquisition.recovery_ratio_min != expected_recovery:
            raise WastePumpArchitectureError("Iteration 25 recovery requirement disagrees with current authority")
        if acquisition.residual_free_liquid_max_uL != expected_residual:
            raise WastePumpArchitectureError("Iteration 25 residual-liquid requirement disagrees with current authority")

        reservations = tuple(
            item for item in frame.reservations if item.reservation_id == RESERVATION_WASTE
        )
        if len(reservations) != 1:
            raise WastePumpArchitectureError("structural frame must expose exactly one waste-routing reservation")
        if self.station.frame_reservation_id != reservations[0].reservation_id:
            raise WastePumpArchitectureError("pump station is stale for current frame reservation")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "source_waste_acquisition_sha256": self.source_waste_acquisition_sha256,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "source_authority_revision": self.source_authority_revision,
            "recovery_ratio_requirement_min": self.recovery_ratio_requirement_min,
            "residual_free_liquid_limit_uL": self.residual_free_liquid_limit_uL,
            "station": self.station.manifest(),
            "barrier": self.barrier.manifest(),
            "routes": [item.manifest() for item in self.routes],
            "faults": [item.manifest() for item in self.faults],
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload

    @property
    def architecture_sha256(self) -> str:
        return _digest(self.manifest(include_sha=False))


def build_waste_pump_architecture(
    authority: Authority,
    acquisition: WasteAcquisitionArchitecture,
    distribution: DistributionGeometryArchitecture,
    frame: StructuralFrameTopology,
) -> WastePumpArchitecture:
    if type(authority) is not Authority:
        raise WastePumpArchitectureError("authority must be the exact Authority type")
    if type(acquisition) is not WasteAcquisitionArchitecture:
        raise WastePumpArchitectureError("acquisition must be the exact Iteration 25 architecture type")
    if type(distribution) is not DistributionGeometryArchitecture:
        raise WastePumpArchitectureError("distribution must be the exact Iteration 24 architecture type")
    if type(frame) is not StructuralFrameTopology:
        raise WastePumpArchitectureError("frame must be the exact structural-frame topology type")
    try:
        acquisition.validate_current_sources(
            authority=authority,
            distribution=distribution,
            frame=frame,
        )
    except WasteAcquisitionError as exc:
        raise WastePumpArchitectureError(
            "Iteration 25 waste acquisition or inherited source graph is stale"
        ) from exc

    waste = authority.get("fluid", "waste")
    if type(waste) is not dict:
        raise WastePumpArchitectureError("waste authority must be an exact mapping")
    _exact(waste.get("status"), "VALIDATION_GATED", label="waste authority performance status")
    recovery = _real(
        waste.get("recovery_ratio_min"),
        label="waste authority recovery ratio",
        positive=True,
        at_most=1.0,
    )
    residual = _real(
        waste.get("residual_free_liquid_max_uL"),
        label="waste authority residual free-liquid limit",
        nonnegative=True,
    )
    revision = _text(authority.get("project", "authority_revision"), label="authority revision")

    station = WastePumpStationReservation(
        station_id=STATION_WASTE,
        phase_semantics=PHASE_MIXED_WASTE,
        source_waste_acquisition_sha256=acquisition.architecture_sha256,
        pump_inlet_interface_id=ROUTE_DESTINATION,
        pump_outlet_interface_id=INTERFACE_PUMP_OUTLET,
        frame_reservation_id=RESERVATION_WASTE,
    )
    barrier = PassiveBackflowBarrierReservation(
        barrier_id=BARRIER_WASTE,
        phase_semantics=PHASE_MIXED_WASTE,
        source_interface_id=INTERFACE_PUMP_OUTLET,
        target_interface_id=INTERFACE_BARRIER_OUTLET,
    )
    routes = (
        WasteRouteInterface(
            route_id=ROUTE_ACQUISITION_TO_PUMP,
            stage="ACQUISITION_TO_PUMP",
            phase_semantics=PHASE_MIXED_WASTE,
            source_interface_id=ROUTE_DESTINATION,
            target_interface_id=STATION_WASTE,
        ),
        WasteRouteInterface(
            route_id=ROUTE_PUMP_TO_BARRIER,
            stage="PUMP_TO_PASSIVE_BACKFLOW_BARRIER",
            phase_semantics=PHASE_MIXED_WASTE,
            source_interface_id=INTERFACE_PUMP_OUTLET,
            target_interface_id=BARRIER_WASTE,
        ),
        WasteRouteInterface(
            route_id=ROUTE_BARRIER_TO_CARTRIDGE,
            stage="PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF",
            phase_semantics=PHASE_MIXED_WASTE,
            source_interface_id=INTERFACE_BARRIER_OUTLET,
            target_interface_id=INTERFACE_CARTRIDGE_INLET_I27,
        ),
    )
    faults = tuple(
        WastePumpFaultIntent(fault_id=fault_id, phase_semantics=PHASE_MIXED_WASTE)
        for fault_id in FAULT_IDS
    )
    architecture = WastePumpArchitecture(
        source_waste_acquisition_sha256=acquisition.architecture_sha256,
        source_structural_frame_sha256=frame.topology_sha256,
        source_authority_revision=revision,
        recovery_ratio_requirement_min=recovery,
        residual_free_liquid_limit_uL=residual,
        station=station,
        barrier=barrier,
        routes=routes,
        faults=faults,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(
        authority=authority,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )
    return architecture
