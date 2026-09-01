"""Iteration 26 mixed-phase waste-pump packaging, routing and fault-state architecture.

This module closes the digital pump-stage topology without selecting a physical pump
or inventing tubing dimensions, pressure-flow operating points, suction limits,
orientation robustness, backflow performance, recovery, leakage, or cartridge
performance. Those remain controlled evidence gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from .structural_frame import RESERVATION_WASTE, StructuralFrameTopology
from .waste_acquisition import (
    PHASE_MIXED_WASTE,
    REGIONS,
    ROUTE_DESTINATION,
    WasteAcquisitionArchitecture,
)
from .waste_routes import WasteNode, WasteNodeKind, WasteRouteNetwork, WasteRouteSegment


class WastePumpArchitectureError(ValueError):
    """Raised when the Iteration 26 topology or evidence firewall is violated."""


PUMP_STATION_ID = "PUMP-STATION-WASTE-I26"
PUMP_OUTLET_INTERFACE = "WASTE_PUMP_OUTLET_ITERATION_26_INTERFACE"
CARTRIDGE_INLET_INTERFACE = "WASTE_CARTRIDGE_INLET_ITERATION_27_INTERFACE"
PUMP_INLET_NODE_ID = "pump-in"
PUMP_OUTLET_NODE_ID = "pump-out"
BACKFLOW_BARRIER_NODE_ID = "barrier-passive"
CARTRIDGE_INLET_NODE_ID = "cartridge-in-i27"
CARTRIDGE_RETENTION_NODE_ID = "cartridge-retention-i27"

PACKAGE_STATUS = "UNRESOLVED_PENDING_CONTROLLED_MIXED_PHASE_PUMP_PACKAGE_EVIDENCE"
ROUTING_STATUS = "TOPOLOGY_ONLY_TUBING_CENTERLINES_DIAMETERS_BENDS_CONNECTORS_UNRESOLVED"
HYDRAULIC_STATUS = "VALIDATION_GATED_PENDING_PRESSURE_FLOW_SUCTION_AND_MIXED_PHASE_RIG_EVIDENCE"
MIXED_PHASE_STATUS = "VALIDATION_GATED_PENDING_GAS_SLUG_FOAM_CONTAMINANT_RIG_EVIDENCE"
BACKFLOW_STATUS = "PASSIVE_BARRIER_TOPOLOGY_REQUIRED_PERFORMANCE_VALIDATION_GATED"
CARTRIDGE_STATE_STATUS = "SEMANTICS_DEFINED_I26_PHYSICAL_KEYING_SEAL_CAPACITY_AND_INTERLOCK_DEFERRED_I27"
SERVICE_STATUS = "ACCESS_PURGE_DRAIN_DRY_REPLACEMENT_CLEARANCE_DEFERRED_I27_I28"
FAULT_EVIDENCE_STATUS = "VALIDATION_GATED_NO_FAULT_RESPONSE_PERFORMANCE_CLAIM"
ARCHITECTURE_EVIDENCE_STATUS = (
    "DIGITAL_MIXED_PHASE_WASTE_PUMP_ROUTING_AND_FAULT_ARCHITECTURE_ONLY_NOT_PUMP_SELECTION_"
    "PRESSURE_FLOW_SUCTION_BACKFLOW_RECOVERY_LEAKAGE_OR_CARTRIDGE_PHYSICAL_EVIDENCE"
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise WastePumpArchitectureError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise WastePumpArchitectureError(f"{label} must be canonical lowercase SHA-256")
    return value


def _exact(value: object, expected: str, label: str) -> str:
    _text(value, label)
    if value != expected:
        raise WastePumpArchitectureError(f"{label} must use its controlled exact state")
    return value


def _digest(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _region_slug(region_id: str) -> str:
    return region_id.lower().replace("_", "-")


FAULT_SPECS = (
    (
        "PUMP_OFF_POWER_LOSS",
        "PUMP_NOT_DRIVEN_OR_POWER_UNAVAILABLE",
        "FAULT_SIGNAL_IMPLEMENTATION_DEFERRED_TO_CONTROL_ARCHITECTURE",
        "NO_REVERSE_WASTE_MIGRATION_PATH_PERMITTED_WHEN_PUMP_IS_NOT_DRIVEN",
    ),
    (
        "GAS_INGESTION",
        "GAS_FRACTION_REACHES_PUMP_INLET_DURING_MIXED_PHASE_TRANSFER",
        "NO_DIGITAL_DETECTION_CLAIM_MIXED_PHASE_BENCH_CHARACTERIZATION_REQUIRED",
        "PUMP_AND_ROUTE_SELECTION_MUST_TOLERATE_OR_DETECT_AND_ENTER_A_FAIL_SAFE_STATE",
    ),
    (
        "LIQUID_SLUGGING",
        "TRANSIENT_LIQUID_SLUG_REACHES_PUMP_INLET",
        "NO_DIGITAL_DETECTION_CLAIM_MIXED_PHASE_BENCH_CHARACTERIZATION_REQUIRED",
        "PUMP_AND_ROUTE_SELECTION_MUST_TOLERATE_OR_DETECT_AND_ENTER_A_FAIL_SAFE_STATE",
    ),
    (
        "FOAM_INGESTION",
        "FOAM_REACHES_PUMP_INLET_OR_PUMP_STAGE",
        "NO_DIGITAL_DETECTION_CLAIM_MIXED_PHASE_BENCH_CHARACTERIZATION_REQUIRED",
        "PUMP_AND_ROUTE_SELECTION_MUST_TOLERATE_OR_DETECT_AND_ENTER_A_FAIL_SAFE_STATE",
    ),
    (
        "ROUTE_OCCLUSION",
        "UPSTREAM_OR_DOWNSTREAM_WASTE_ROUTE_BECOMES_RESTRICTED_OR_BLOCKED",
        "OCCLUSION_DETECTION_IMPLEMENTATION_UNRESOLVED_PENDING_SENSOR_AND_PUMP_SELECTION",
        "SYSTEM_MUST_NOT_RELY_ON_UNVALIDATED_SUCTION_OR_CONTINUE_BLIND_TRANSFER_INTO_OCCLUSION",
    ),
    (
        "BACKFLOW",
        "REVERSE_FLOW_TENDENCY_EXISTS_FROM_DOWNSTREAM_CONTAINMENT_TOWARD_PUMP_OR_FACE",
        "PASSIVE_BARRIER_TOPOLOGY_REQUIRED_DETECTION_IMPLEMENTATION_UNRESOLVED",
        "DIRECT_REVERSE_PATH_MUST_BE_INTERRUPTED_BY_A_PASSIVE_BACKFLOW_BARRIER",
    ),
    (
        "PROTECTED_REGION_POOLING",
        "FREE_LIQUID_OR_FOAM_ACCUMULATES_AT_OR_MIGRATES_TOWARD_A_PROTECTED_REGION",
        "POOLING_DETECTION_IMPLEMENTATION_UNRESOLVED_PENDING_SENSOR_AND_SYSTEM_ARCHITECTURE",
        "SYSTEM_MUST_ENTER_A_FAIL_SAFE_STATE_AND_MUST_NOT_CONTINUE_BLIND_TRANSFER_OR_DELIVERY_WHILE_PROTECTED_REGION_POOLING_PERSISTS",
    ),
    (
        "CARTRIDGE_MISSING",
        "DOWNSTREAM_CARTRIDGE_IS_NOT_PRESENT",
        "CARTRIDGE_STATE_DETECTION_IMPLEMENTATION_DEFERRED_TO_ITERATION_27",
        "WASTE_TRANSFER_MUST_NOT_DISCHARGE_UNCONTAINED",
    ),
    (
        "CARTRIDGE_MISINSTALLED",
        "CARTRIDGE_IS_PRESENT_BUT_NOT_IN_THE_CONTROLLED_SEATED_AND_SEALED_STATE",
        "CARTRIDGE_STATE_DETECTION_IMPLEMENTATION_DEFERRED_TO_ITERATION_27",
        "WASTE_TRANSFER_MUST_NOT_DISCHARGE_UNCONTAINED",
    ),
    (
        "CARTRIDGE_FULL_OR_REDUCED_RETENTION",
        "AVAILABLE_RETAINED_CAPACITY_IS_INSUFFICIENT_FOR_CONTINUED_TRANSFER",
        "CARTRIDGE_CAPACITY_STATE_DETECTION_IMPLEMENTATION_DEFERRED_TO_ITERATION_27",
        "TRANSFER_MUST_NOT_CONTINUE_BEYOND_THE_VALIDATED_RETENTION_STATE",
    ),
)
FAULT_IDS = tuple(item[0] for item in FAULT_SPECS)


@dataclass(frozen=True, slots=True)
class WastePumpStationReservation:
    station_id: str
    source_waste_architecture_sha256: str
    source_structural_frame_sha256: str
    source_interface_id: str
    outlet_interface_id: str
    frame_reservation_id: str
    pump_inlet_node_id: str
    pump_outlet_node_id: str
    package_candidate_id: None = None
    package_evidence_sha256: None = None
    envelope_mm: None = None
    placement_xyz_mm: None = None
    orientation_axis_xyz: None = None
    tubing_inner_diameter_mm: None = None
    minimum_bend_radius_mm: None = None
    connector_standard: None = None
    nominal_flow_mL_s: None = None
    suction_pressure_kPa: None = None
    discharge_pressure_kPa: None = None
    package_status: str = PACKAGE_STATUS
    routing_status: str = ROUTING_STATUS
    hydraulic_status: str = HYDRAULIC_STATUS
    mixed_phase_status: str = MIXED_PHASE_STATUS
    service_status: str = SERVICE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _exact(self.station_id, PUMP_STATION_ID, "waste pump station ID")
        _sha(self.source_waste_architecture_sha256, "pump source waste architecture")
        _sha(self.source_structural_frame_sha256, "pump source structural frame")
        _exact(self.source_interface_id, ROUTE_DESTINATION, "pump source interface")
        _exact(self.outlet_interface_id, PUMP_OUTLET_INTERFACE, "pump outlet interface")
        _exact(self.frame_reservation_id, RESERVATION_WASTE, "pump frame reservation")
        _exact(self.pump_inlet_node_id, PUMP_INLET_NODE_ID, "pump inlet node")
        _exact(self.pump_outlet_node_id, PUMP_OUTLET_NODE_ID, "pump outlet node")

        unresolved = (
            self.package_candidate_id,
            self.package_evidence_sha256,
            self.envelope_mm,
            self.placement_xyz_mm,
            self.orientation_axis_xyz,
            self.tubing_inner_diameter_mm,
            self.minimum_bend_radius_mm,
            self.connector_standard,
            self.nominal_flow_mL_s,
            self.suction_pressure_kPa,
            self.discharge_pressure_kPa,
        )
        if any(value is not None for value in unresolved):
            raise WastePumpArchitectureError(
                "Iteration 26 cannot invent pump selection, package/routing geometry, tubing data, or pressure-flow values"
            )
        _exact(self.package_status, PACKAGE_STATUS, "pump package status")
        _exact(self.routing_status, ROUTING_STATUS, "pump routing status")
        _exact(self.hydraulic_status, HYDRAULIC_STATUS, "pump hydraulic status")
        _exact(self.mixed_phase_status, MIXED_PHASE_STATUS, "pump mixed-phase status")
        _exact(self.service_status, SERVICE_STATUS, "pump service status")

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "station_id": self.station_id,
            "source_waste_architecture_sha256": self.source_waste_architecture_sha256,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "source_interface_id": self.source_interface_id,
            "outlet_interface_id": self.outlet_interface_id,
            "frame_reservation_id": self.frame_reservation_id,
            "pump_inlet_node_id": self.pump_inlet_node_id,
            "pump_outlet_node_id": self.pump_outlet_node_id,
            "package_candidate_id": self.package_candidate_id,
            "package_evidence_sha256": self.package_evidence_sha256,
            "envelope_mm": self.envelope_mm,
            "placement_xyz_mm": self.placement_xyz_mm,
            "orientation_axis_xyz": self.orientation_axis_xyz,
            "tubing_inner_diameter_mm": self.tubing_inner_diameter_mm,
            "minimum_bend_radius_mm": self.minimum_bend_radius_mm,
            "connector_standard": self.connector_standard,
            "nominal_flow_mL_s": self.nominal_flow_mL_s,
            "suction_pressure_kPa": self.suction_pressure_kPa,
            "discharge_pressure_kPa": self.discharge_pressure_kPa,
            "package_status": self.package_status,
            "routing_status": self.routing_status,
            "hydraulic_status": self.hydraulic_status,
            "mixed_phase_status": self.mixed_phase_status,
            "service_status": self.service_status,
        }


@dataclass(frozen=True, slots=True)
class WastePumpFaultCase:
    fault_id: str
    state_semantics: str
    detection_status: str
    required_response: str
    evidence_status: str = FAULT_EVIDENCE_STATUS

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        for label, value in (
            ("fault ID", self.fault_id),
            ("fault state semantics", self.state_semantics),
            ("fault detection status", self.detection_status),
            ("fault required response", self.required_response),
        ):
            _text(value, label)
        try:
            expected = next(item for item in FAULT_SPECS if item[0] == self.fault_id)
        except StopIteration as exc:
            raise WastePumpArchitectureError(f"unknown Iteration 26 fault state {self.fault_id!r}") from exc
        if (self.state_semantics, self.detection_status, self.required_response) != expected[1:]:
            raise WastePumpArchitectureError("fault case must preserve its controlled exact semantics")
        _exact(self.evidence_status, FAULT_EVIDENCE_STATUS, "fault evidence status")

    def manifest(self) -> dict[str, str]:
        self.validate_invariants()
        return {
            "fault_id": self.fault_id,
            "state_semantics": self.state_semantics,
            "detection_status": self.detection_status,
            "required_response": self.required_response,
            "evidence_status": self.evidence_status,
        }


def _expected_node_signature() -> tuple[tuple[str, str, bool], ...]:
    regional = []
    for region_id in REGIONS:
        slug = _region_slug(region_id)
        regional.extend(
            (
                (f"acq-{slug}", WasteNodeKind.REGIONAL_ACQUISITION.value, False),
                (f"buffer-{slug}", WasteNodeKind.TRANSIENT_BUFFER.value, False),
            )
        )
    regional.extend(
        (
            (PUMP_INLET_NODE_ID, WasteNodeKind.PUMP_INLET.value, False),
            (PUMP_OUTLET_NODE_ID, WasteNodeKind.PUMP_OUTLET.value, False),
            (BACKFLOW_BARRIER_NODE_ID, WasteNodeKind.PASSIVE_BACKFLOW_BARRIER.value, False),
            (CARTRIDGE_INLET_NODE_ID, WasteNodeKind.CARTRIDGE_INLET.value, False),
            (CARTRIDGE_RETENTION_NODE_ID, WasteNodeKind.CARTRIDGE_RETENTION.value, False),
        )
    )
    return tuple(sorted(regional))


def _expected_segment_signature() -> tuple[tuple[str, str, str, bool, str], ...]:
    regional = []
    for region_id in REGIONS:
        slug = _region_slug(region_id)
        regional.extend(
            (
                (f"seg-acq-{slug}-to-buffer", f"acq-{slug}", f"buffer-{slug}", True, "VALIDATION_GATED"),
                (f"seg-buffer-{slug}-to-pump-in", f"buffer-{slug}", PUMP_INLET_NODE_ID, True, "VALIDATION_GATED"),
            )
        )
    regional.extend(
        (
            ("seg-pump-out-to-barrier", PUMP_OUTLET_NODE_ID, BACKFLOW_BARRIER_NODE_ID, True, "VALIDATION_GATED"),
            ("seg-barrier-to-cartridge-in", BACKFLOW_BARRIER_NODE_ID, CARTRIDGE_INLET_NODE_ID, True, "VALIDATION_GATED"),
            ("seg-cartridge-in-to-retention", CARTRIDGE_INLET_NODE_ID, CARTRIDGE_RETENTION_NODE_ID, True, "VALIDATION_GATED"),
        )
    )
    return tuple(sorted(regional))


def _build_route_network(source_waste_architecture_sha256: str) -> WasteRouteNetwork:
    nodes: dict[str, WasteNode] = {}
    segments: list[WasteRouteSegment] = []
    for region_id in REGIONS:
        slug = _region_slug(region_id)
        acquisition_id = f"acq-{slug}"
        buffer_id = f"buffer-{slug}"
        nodes[acquisition_id] = WasteNode(acquisition_id, WasteNodeKind.REGIONAL_ACQUISITION)
        nodes[buffer_id] = WasteNode(buffer_id, WasteNodeKind.TRANSIENT_BUFFER)
        segments.extend(
            (
                WasteRouteSegment(f"seg-acq-{slug}-to-buffer", acquisition_id, buffer_id, True),
                WasteRouteSegment(f"seg-buffer-{slug}-to-pump-in", buffer_id, PUMP_INLET_NODE_ID, True),
            )
        )
    nodes.update(
        {
            PUMP_INLET_NODE_ID: WasteNode(PUMP_INLET_NODE_ID, WasteNodeKind.PUMP_INLET),
            PUMP_OUTLET_NODE_ID: WasteNode(PUMP_OUTLET_NODE_ID, WasteNodeKind.PUMP_OUTLET),
            BACKFLOW_BARRIER_NODE_ID: WasteNode(BACKFLOW_BARRIER_NODE_ID, WasteNodeKind.PASSIVE_BACKFLOW_BARRIER),
            CARTRIDGE_INLET_NODE_ID: WasteNode(CARTRIDGE_INLET_NODE_ID, WasteNodeKind.CARTRIDGE_INLET),
            CARTRIDGE_RETENTION_NODE_ID: WasteNode(CARTRIDGE_RETENTION_NODE_ID, WasteNodeKind.CARTRIDGE_RETENTION),
        }
    )
    segments.extend(
        (
            WasteRouteSegment("seg-pump-out-to-barrier", PUMP_OUTLET_NODE_ID, BACKFLOW_BARRIER_NODE_ID, True),
            WasteRouteSegment("seg-barrier-to-cartridge-in", BACKFLOW_BARRIER_NODE_ID, CARTRIDGE_INLET_NODE_ID, True),
            WasteRouteSegment("seg-cartridge-in-to-retention", CARTRIDGE_INLET_NODE_ID, CARTRIDGE_RETENTION_NODE_ID, True),
        )
    )
    network = WasteRouteNetwork(source_waste_architecture_sha256, nodes, tuple(segments))
    network.validate()
    return network


@dataclass(frozen=True, slots=True)
class WastePumpArchitecture:
    source_waste_architecture_sha256: str
    source_structural_frame_sha256: str
    authority_revision: str
    phase_semantics: str
    pump: WastePumpStationReservation
    route_network: WasteRouteNetwork
    faults: tuple[WastePumpFaultCase, ...]
    backflow_status: str
    cartridge_state_status: str
    downstream_interface_id: str
    physical_validation_eligible: bool
    evidence_status: str

    def __post_init__(self) -> None:
        self.validate_invariants()

    def validate_invariants(self) -> None:
        _sha(self.source_waste_architecture_sha256, "source Iteration 25 waste architecture")
        _sha(self.source_structural_frame_sha256, "source structural frame")
        _text(self.authority_revision, "authority revision")
        _exact(self.phase_semantics, PHASE_MIXED_WASTE, "waste phase semantics")
        if type(self.pump) is not WastePumpStationReservation:
            raise WastePumpArchitectureError("pump must be the exact WastePumpStationReservation type")
        self.pump.validate_invariants()
        if self.pump.source_waste_architecture_sha256 != self.source_waste_architecture_sha256:
            raise WastePumpArchitectureError("pump source waste architecture must match Iteration 26 source")
        if self.pump.source_structural_frame_sha256 != self.source_structural_frame_sha256:
            raise WastePumpArchitectureError("pump source frame must match Iteration 26 source")

        if type(self.route_network) is not WasteRouteNetwork:
            raise WastePumpArchitectureError("route_network must be the exact WasteRouteNetwork type")
        self.route_network.validate()
        if self.route_network.source_waste_architecture_sha256 != self.source_waste_architecture_sha256:
            raise WastePumpArchitectureError("waste route network is stale for Iteration 26 source")
        node_signature = tuple(
            sorted(
                (node_id, node.kind.value, node.protected_region_adjacent)
                for node_id, node in self.route_network.nodes.items()
            )
        )
        if node_signature != _expected_node_signature():
            raise WastePumpArchitectureError("Iteration 26 waste route nodes must preserve the complete controlled topology")
        segment_signature = tuple(
            sorted(
                (
                    segment.segment_id,
                    segment.source_node_id,
                    segment.target_node_id,
                    segment.mixed_phase,
                    segment.physical_performance_state,
                )
                for segment in self.route_network.segments
            )
        )
        if segment_signature != _expected_segment_signature():
            raise WastePumpArchitectureError("Iteration 26 waste route segments must preserve the complete controlled topology")

        if type(self.faults) is not tuple or any(type(item) is not WastePumpFaultCase for item in self.faults):
            raise WastePumpArchitectureError("fault registry must be an immutable tuple of exact fault records")
        if tuple(item.fault_id for item in self.faults) != FAULT_IDS:
            raise WastePumpArchitectureError("fault registry must contain the complete controlled Iteration 26 fault set in order")
        for item in self.faults:
            item.validate_invariants()

        _exact(self.backflow_status, BACKFLOW_STATUS, "backflow status")
        _exact(self.cartridge_state_status, CARTRIDGE_STATE_STATUS, "cartridge-state status")
        _exact(self.downstream_interface_id, CARTRIDGE_INLET_INTERFACE, "downstream cartridge interface")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise WastePumpArchitectureError("Iteration 26 digital architecture is not physical validation evidence")
        _exact(self.evidence_status, ARCHITECTURE_EVIDENCE_STATUS, "architecture evidence status")

    def validate_current_sources(
        self,
        *,
        waste: WasteAcquisitionArchitecture,
        frame: StructuralFrameTopology,
    ) -> None:
        self.validate_invariants()
        if type(waste) is not WasteAcquisitionArchitecture:
            raise WastePumpArchitectureError("waste must be the exact Iteration 25 architecture type")
        if type(frame) is not StructuralFrameTopology:
            raise WastePumpArchitectureError("frame must be the exact StructuralFrameTopology type")
        waste.validate_invariants()
        if self.source_waste_architecture_sha256 != waste.architecture_sha256:
            raise WastePumpArchitectureError("Iteration 26 architecture is stale for current Iteration 25 waste acquisition")
        if self.authority_revision != waste.authority_revision:
            raise WastePumpArchitectureError("Iteration 26 architecture is stale for current authority revision")
        if self.source_structural_frame_sha256 != frame.topology_sha256:
            raise WastePumpArchitectureError("Iteration 26 architecture is stale for current structural frame")
        reservations = tuple(item for item in frame.reservations if item.reservation_id == RESERVATION_WASTE)
        if len(reservations) != 1:
            raise WastePumpArchitectureError("structural frame must expose exactly one waste-routing reservation")
        if any(region.destination != ROUTE_DESTINATION for region in waste.regions):
            raise WastePumpArchitectureError("Iteration 25 regions no longer terminate at the Iteration 26 pump interface")

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        self.validate_invariants()
        payload: dict[str, object] = {
            "source_waste_architecture_sha256": self.source_waste_architecture_sha256,
            "source_structural_frame_sha256": self.source_structural_frame_sha256,
            "authority_revision": self.authority_revision,
            "phase_semantics": self.phase_semantics,
            "pump": self.pump.manifest(),
            "route_network_sha256": self.route_network.manifest_sha256(),
            "faults": [item.manifest() for item in self.faults],
            "backflow_status": self.backflow_status,
            "cartridge_state_status": self.cartridge_state_status,
            "downstream_interface_id": self.downstream_interface_id,
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
    waste: WasteAcquisitionArchitecture,
    frame: StructuralFrameTopology,
) -> WastePumpArchitecture:
    if type(waste) is not WasteAcquisitionArchitecture:
        raise WastePumpArchitectureError("waste must be the exact Iteration 25 architecture type")
    if type(frame) is not StructuralFrameTopology:
        raise WastePumpArchitectureError("frame must be the exact StructuralFrameTopology type")
    waste.validate_invariants()

    source_waste_sha = waste.architecture_sha256
    source_frame_sha = frame.topology_sha256
    pump = WastePumpStationReservation(
        station_id=PUMP_STATION_ID,
        source_waste_architecture_sha256=source_waste_sha,
        source_structural_frame_sha256=source_frame_sha,
        source_interface_id=ROUTE_DESTINATION,
        outlet_interface_id=PUMP_OUTLET_INTERFACE,
        frame_reservation_id=RESERVATION_WASTE,
        pump_inlet_node_id=PUMP_INLET_NODE_ID,
        pump_outlet_node_id=PUMP_OUTLET_NODE_ID,
    )
    route_network = _build_route_network(source_waste_sha)
    faults = tuple(
        WastePumpFaultCase(
            fault_id=fault_id,
            state_semantics=state_semantics,
            detection_status=detection_status,
            required_response=required_response,
        )
        for fault_id, state_semantics, detection_status, required_response in FAULT_SPECS
    )
    architecture = WastePumpArchitecture(
        source_waste_architecture_sha256=source_waste_sha,
        source_structural_frame_sha256=source_frame_sha,
        authority_revision=waste.authority_revision,
        phase_semantics=PHASE_MIXED_WASTE,
        pump=pump,
        route_network=route_network,
        faults=faults,
        backflow_status=BACKFLOW_STATUS,
        cartridge_state_status=CARTRIDGE_STATE_STATUS,
        downstream_interface_id=CARTRIDGE_INLET_INTERFACE,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )
    architecture.validate_current_sources(waste=waste, frame=frame)
    return architecture
