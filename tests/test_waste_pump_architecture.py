from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_geometry import build_distribution_geometry_architecture
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.fresh_pump_packaging import build_fresh_pump_packaging_architecture
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import RESERVATION_WASTE, build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture
from masck_one.waste_acquisition import build_waste_acquisition_architecture
from masck_one.waste_pump_architecture import (
    ARCHITECTURE_EVIDENCE_STATUS,
    BACKFLOW_BARRIER_NODE_ID,
    BACKFLOW_STATUS,
    CARTRIDGE_INLET_INTERFACE,
    CARTRIDGE_INLET_NODE_ID,
    CARTRIDGE_RETENTION_NODE_ID,
    CARTRIDGE_STATE_STATUS,
    FAULT_EVIDENCE_STATUS,
    FAULT_IDS,
    HYDRAULIC_STATUS,
    MIXED_PHASE_STATUS,
    PACKAGE_STATUS,
    PUMP_INLET_NODE_ID,
    PUMP_OUTLET_INTERFACE,
    PUMP_OUTLET_NODE_ID,
    PUMP_STATION_ID,
    ROUTING_STATUS,
    SERVICE_STATUS,
    WastePumpArchitectureError,
    build_waste_pump_architecture,
)
from masck_one.waste_routes import WasteNode, WasteNodeKind, WasteRouteSegment
from masck_one.waste_system import REQUIRED_MIXED_PHASE_FAULTS


class Alias(str):
    pass


@pytest.fixture(scope="module")
def current_sources():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    fresh_pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    waste = build_waste_acquisition_architecture(model.authority, distribution)
    return model, frame, waste


@pytest.fixture(scope="module")
def architecture(current_sources):
    _, frame, waste = current_sources
    return build_waste_pump_architecture(waste, frame)


def test_builder_closes_only_digital_pump_stage_topology(architecture):
    a = architecture
    assert a.pump.station_id == PUMP_STATION_ID
    assert a.pump.pump_inlet_node_id == PUMP_INLET_NODE_ID
    assert a.pump.pump_outlet_node_id == PUMP_OUTLET_NODE_ID
    assert a.pump.outlet_interface_id == PUMP_OUTLET_INTERFACE
    assert a.downstream_interface_id == CARTRIDGE_INLET_INTERFACE
    assert BACKFLOW_BARRIER_NODE_ID in a.route_network.nodes
    assert CARTRIDGE_INLET_NODE_ID in a.route_network.nodes
    assert CARTRIDGE_RETENTION_NODE_ID in a.route_network.nodes
    assert a.physical_validation_eligible is False
    assert a.evidence_status == ARCHITECTURE_EVIDENCE_STATUS
    assert len(a.architecture_sha256) == 64


def test_all_regions_preserve_mixed_phase_paths_to_single_pump_inlet(architecture):
    a = architecture
    acquisitions = [
        node for node in a.route_network.nodes.values()
        if node.kind is WasteNodeKind.REGIONAL_ACQUISITION
    ]
    buffers = [
        node for node in a.route_network.nodes.values()
        if node.kind is WasteNodeKind.TRANSIENT_BUFFER
    ]
    assert len(acquisitions) == 5
    assert len(buffers) == 5
    assert sum(node.kind is WasteNodeKind.PUMP_INLET for node in a.route_network.nodes.values()) == 1
    assert sum(node.kind is WasteNodeKind.PUMP_OUTLET for node in a.route_network.nodes.values()) == 1
    assert all(segment.mixed_phase is True for segment in a.route_network.segments)
    assert all(segment.physical_performance_state == "VALIDATION_GATED" for segment in a.route_network.segments)


def test_package_geometry_and_pressure_flow_values_cannot_be_invented(architecture):
    pump = architecture.pump
    for field, value in (
        ("package_candidate_id", "unsourced-pump"),
        ("package_evidence_sha256", "b" * 64),
        ("envelope_mm", (20.0, 20.0, 10.0)),
        ("placement_xyz_mm", (0.0, 0.0, 0.0)),
        ("orientation_axis_xyz", (0.0, 0.0, 1.0)),
        ("tubing_inner_diameter_mm", 1.0),
        ("minimum_bend_radius_mm", 5.0),
        ("connector_standard", "invented"),
        ("nominal_flow_mL_s", 1.0),
        ("suction_pressure_kPa", -10.0),
        ("discharge_pressure_kPa", 10.0),
    ):
        with pytest.raises(WastePumpArchitectureError, match="cannot invent"):
            replace(pump, **{field: value})


def test_pump_evidence_states_cannot_be_promoted_or_reworded(architecture):
    pump = architecture.pump
    for field, value in (
        ("package_status", "SELECTED"),
        ("routing_status", "GEOMETRY_VERIFIED"),
        ("hydraulic_status", "VERIFIED"),
        ("mixed_phase_status", "VERIFIED"),
        ("service_status", "VERIFIED"),
    ):
        with pytest.raises(WastePumpArchitectureError, match="controlled exact state"):
            replace(pump, **{field: value})
    assert pump.package_status == PACKAGE_STATUS
    assert pump.routing_status == ROUTING_STATUS
    assert pump.hydraulic_status == HYDRAULIC_STATUS
    assert pump.mixed_phase_status == MIXED_PHASE_STATUS
    assert pump.service_status == SERVICE_STATUS


def test_fault_registry_is_complete_ordered_and_validation_gated(architecture):
    a = architecture
    assert tuple(case.fault_id for case in a.faults) == FAULT_IDS
    assert frozenset(case.fault_id.lower() for case in a.faults) == REQUIRED_MIXED_PHASE_FAULTS
    assert "PROTECTED_REGION_POOLING" in FAULT_IDS
    assert all(case.evidence_status == FAULT_EVIDENCE_STATUS for case in a.faults)
    assert a.backflow_status == BACKFLOW_STATUS
    assert a.cartridge_state_status == CARTRIDGE_STATE_STATUS


def test_incomplete_reordered_or_promoted_fault_registry_fails_closed(architecture):
    a = architecture
    with pytest.raises(WastePumpArchitectureError, match="complete controlled"):
        replace(a, faults=a.faults[:-1])
    with pytest.raises(WastePumpArchitectureError, match="complete controlled"):
        replace(a, faults=tuple(reversed(a.faults)))
    with pytest.raises(WastePumpArchitectureError, match="fault evidence status"):
        replace(a.faults[0], evidence_status="VERIFIED")
    with pytest.raises(WastePumpArchitectureError, match="exact semantics"):
        replace(a.faults[1], required_response="CONTINUE_RUNNING")


def test_route_cannot_gain_uncontrolled_parallel_or_hidden_topology(architecture):
    a = architecture
    nodes = dict(a.route_network.nodes)
    nodes["hidden-buffer"] = WasteNode("hidden-buffer", WasteNodeKind.TRANSIENT_BUFFER)
    segments = a.route_network.segments + (
        WasteRouteSegment("hidden-link", PUMP_OUTLET_NODE_ID, "hidden-buffer", True),
        WasteRouteSegment("hidden-return", "hidden-buffer", BACKFLOW_BARRIER_NODE_ID, True),
    )
    altered = replace(a.route_network, nodes=nodes, segments=segments)
    altered.validate()
    with pytest.raises(WastePumpArchitectureError, match="complete controlled topology"):
        replace(a, route_network=altered)


def test_direct_backflow_barrier_bypass_is_rejected_by_route_contract(architecture):
    a = architecture
    bypass = replace(
        a.route_network,
        segments=a.route_network.segments
        + (WasteRouteSegment("bypass", PUMP_OUTLET_NODE_ID, CARTRIDGE_INLET_NODE_ID, True),),
    )
    with pytest.raises(ValueError, match="bypasses all passive backflow barriers"):
        bypass.validate()


def test_current_source_validation_rejects_waste_and_frame_drift(current_sources, architecture):
    _, frame, waste = current_sources
    architecture.validate_current_sources(waste=waste, frame=frame)

    stale_waste = replace(waste, authority_revision="STALE-REVISION")
    with pytest.raises(WastePumpArchitectureError, match="stale for current Iteration 25"):
        architecture.validate_current_sources(waste=stale_waste, frame=frame)

    changed_frame = replace(frame, functional_frame_status=frame.functional_frame_status + "_CHANGED")
    with pytest.raises(WastePumpArchitectureError, match="stale for current structural frame"):
        architecture.validate_current_sources(waste=waste, frame=changed_frame)


def test_structural_reservation_container_and_identity_aliases_fail_closed(current_sources, architecture):
    _, frame, waste = current_sources
    list_backed_frame = replace(frame, reservations=list(frame.reservations))
    assert list_backed_frame.topology_sha256 == frame.topology_sha256
    with pytest.raises(WastePumpArchitectureError, match="immutable tuple"):
        architecture.validate_current_sources(waste=waste, frame=list_backed_frame)

    reservations = list(frame.reservations)
    waste_index = next(
        index for index, item in enumerate(reservations)
        if item.reservation_id == RESERVATION_WASTE
    )
    aliased_waste_reservation = replace(reservations[waste_index])
    object.__setattr__(aliased_waste_reservation, "reservation_id", Alias(RESERVATION_WASTE))
    reservations[waste_index] = aliased_waste_reservation
    aliased_frame = replace(frame, reservations=tuple(reservations))
    assert aliased_frame.topology_sha256 == frame.topology_sha256
    with pytest.raises(WastePumpArchitectureError, match="exact built-in text"):
        architecture.validate_current_sources(waste=waste, frame=aliased_frame)


def test_architecture_source_and_interface_aliases_fail_closed(architecture):
    a = architecture
    with pytest.raises(WastePumpArchitectureError, match="canonical lowercase"):
        replace(a, source_waste_architecture_sha256=Alias(a.source_waste_architecture_sha256))
    with pytest.raises(WastePumpArchitectureError, match="exact built-in"):
        replace(a.pump, source_interface_id=Alias(a.pump.source_interface_id))
    with pytest.raises(WastePumpArchitectureError, match="exact built-in"):
        replace(a.faults[0], fault_id=Alias(a.faults[0].fault_id))


def test_physical_evidence_promotion_fails_closed(architecture):
    with pytest.raises(WastePumpArchitectureError, match="not physical validation evidence"):
        replace(architecture, physical_validation_eligible=True)
    with pytest.raises(WastePumpArchitectureError, match="controlled exact state"):
        replace(architecture, evidence_status="PHYSICAL_VERIFIED")


def test_manifest_revalidates_post_construction_fault_corruption(current_sources):
    _, frame, waste = current_sources
    a = build_waste_pump_architecture(waste, frame)
    object.__setattr__(a.faults[0], "required_response", "CONTINUE_RUNNING")
    with pytest.raises(WastePumpArchitectureError, match="exact semantics"):
        _ = a.architecture_sha256


def test_manifest_revalidates_post_construction_pump_corruption(current_sources):
    _, frame, waste = current_sources
    a = build_waste_pump_architecture(waste, frame)
    object.__setattr__(a.pump, "nominal_flow_mL_s", 99.0)
    with pytest.raises(WastePumpArchitectureError, match="cannot invent"):
        _ = a.architecture_sha256
