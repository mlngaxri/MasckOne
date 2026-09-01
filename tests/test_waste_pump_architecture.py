from copy import deepcopy
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
    BARRIER_PERFORMANCE_STATUS,
    BARRIER_SELECTION_STATUS,
    BARRIER_WASTE,
    FAULT_IDS,
    HYDRAULIC_STATUS,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    PACKAGE_STATUS,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_IDS,
    ROUTE_PUMP_TO_BARRIER,
    ROUTING_STATUS,
    SERVICE_STATUS,
    STATION_WASTE,
    WastePumpArchitectureError,
    build_waste_pump_architecture,
)


@pytest.fixture(scope="module")
def built():
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
    fresh_pumps = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pumps,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pumps,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    architecture = build_waste_pump_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    return model, frame, distribution, acquisition, architecture


def test_single_owner_binds_canonical_iteration25_and_frame(built):
    _, frame, _, acquisition, architecture = built
    assert architecture.station.station_id == STATION_WASTE
    assert architecture.station.source_waste_acquisition_sha256 == acquisition.architecture_sha256
    assert architecture.source_waste_acquisition_sha256 == acquisition.architecture_sha256
    assert architecture.source_structural_frame_sha256 == frame.topology_sha256
    assert architecture.station.frame_reservation_id == RESERVATION_WASTE


def test_passive_backflow_barrier_is_mandatory_topology_not_only_fault_intent(built):
    *_, architecture = built
    assert architecture.barrier.barrier_id == BARRIER_WASTE
    assert architecture.barrier.source_interface_id == INTERFACE_PUMP_OUTLET
    assert architecture.barrier.target_interface_id == INTERFACE_BARRIER_OUTLET
    assert architecture.barrier.selection_status == BARRIER_SELECTION_STATUS
    assert architecture.barrier.performance_status == BARRIER_PERFORMANCE_STATUS

    assert tuple(route.route_id for route in architecture.routes) == ROUTE_IDS
    assert architecture.routes[0].route_id == ROUTE_ACQUISITION_TO_PUMP
    assert architecture.routes[0].target_interface_id == STATION_WASTE
    assert architecture.routes[1].route_id == ROUTE_PUMP_TO_BARRIER
    assert architecture.routes[1].source_interface_id == INTERFACE_PUMP_OUTLET
    assert architecture.routes[1].target_interface_id == BARRIER_WASTE
    assert architecture.routes[2].route_id == ROUTE_BARRIER_TO_CARTRIDGE
    assert architecture.routes[2].source_interface_id == INTERFACE_BARRIER_OUTLET
    assert architecture.routes[2].target_interface_id == INTERFACE_CARTRIDGE_INLET_I27
    assert not any(
        route.source_interface_id == INTERFACE_PUMP_OUTLET
        and route.target_interface_id == INTERFACE_CARTRIDGE_INLET_I27
        for route in architecture.routes
    )


def test_pump_and_barrier_physical_values_remain_unresolved(built):
    *_, architecture = built
    station = architecture.station
    assert station.package_status == PACKAGE_STATUS
    assert station.routing_status == ROUTING_STATUS
    assert station.hydraulic_status == HYDRAULIC_STATUS
    assert station.service_status == SERVICE_STATUS
    assert station.package_candidate_id is None
    assert station.envelope_mm is None
    assert station.nominal_mixed_phase_flow_mL_s is None
    assert station.suction_pressure_kPa is None
    assert station.discharge_pressure_kPa is None

    barrier = architecture.barrier
    assert barrier.component_candidate_id is None
    assert barrier.envelope_mm is None
    assert barrier.cracking_pressure_kPa is None
    assert barrier.reverse_leakage_mL_min is None

    with pytest.raises(WastePumpArchitectureError, match="cannot invent pump selection"):
        replace(station, envelope_mm=(20.0, 10.0, 8.0))
    with pytest.raises(WastePumpArchitectureError, match="cannot invent passive backflow"):
        replace(barrier, cracking_pressure_kPa=1.0)


def test_route_bypass_reversal_missing_or_mutable_routes_fail_closed(built):
    *_, architecture = built
    routes = list(architecture.routes)
    routes[1] = replace(routes[1], target_interface_id=INTERFACE_CARTRIDGE_INLET_I27)
    with pytest.raises(WastePumpArchitectureError, match="passive backflow stage"):
        replace(architecture, routes=tuple(routes))
    with pytest.raises(WastePumpArchitectureError, match="complete controlled route order"):
        replace(architecture, routes=architecture.routes[:-1])
    with pytest.raises(WastePumpArchitectureError, match="immutable tuple"):
        replace(architecture, routes=list(architecture.routes))


def test_fault_registry_is_complete_and_validation_gated(built):
    *_, architecture = built
    assert tuple(fault.fault_id for fault in architecture.faults) == FAULT_IDS
    assert "BACKFLOW_RISK" in FAULT_IDS
    assert "PROTECTED_REGION_POOLING_RISK" in FAULT_IDS
    assert "CARTRIDGE_MISSING" in FAULT_IDS
    assert "CARTRIDGE_MISINSTALLED" in FAULT_IDS
    assert "CARTRIDGE_FULL_OR_REDUCED_RETENTION" in FAULT_IDS
    assert all("VALIDATION_GATED" in fault.validation_status for fault in architecture.faults)


def test_fault_registry_missing_reordered_mutable_or_promoted_fails_closed(built):
    *_, architecture = built
    with pytest.raises(WastePumpArchitectureError, match="complete controlled fault order"):
        replace(architecture, faults=architecture.faults[:-1])
    with pytest.raises(WastePumpArchitectureError, match="complete controlled fault order"):
        replace(architecture, faults=tuple(reversed(architecture.faults)))
    with pytest.raises(WastePumpArchitectureError, match="immutable tuple"):
        replace(architecture, faults=list(architecture.faults))
    with pytest.raises(WastePumpArchitectureError, match="validation status"):
        replace(architecture.faults[0], validation_status="VERIFIED")


def test_current_source_validation_composes_full_iteration25_proof(built):
    model, frame, distribution, acquisition, architecture = built
    architecture.validate_current_sources(
        authority=model.authority,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )

    corrupted_distribution = deepcopy(distribution)
    object.__setattr__(corrupted_distribution.grooves[0], "width_mm", 0.4)
    with pytest.raises(WastePumpArchitectureError, match="Iteration 25 waste acquisition"):
        architecture.validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=corrupted_distribution,
            frame=frame,
        )


def test_caller_frame_is_proven_against_canonical_iteration25_graph(built):
    class Alias(str):
        pass

    model, frame, distribution, acquisition, architecture = built
    reservations = list(frame.reservations)
    index = next(i for i, item in enumerate(reservations) if item.reservation_id == RESERVATION_WASTE)
    aliased = replace(reservations[index])
    object.__setattr__(aliased, "reservation_id", Alias(RESERVATION_WASTE))
    reservations[index] = aliased
    aliased_frame = replace(frame, reservations=tuple(reservations))
    assert aliased_frame.topology_sha256 == frame.topology_sha256

    with pytest.raises(WastePumpArchitectureError, match="Iteration 25 waste acquisition"):
        architecture.validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=aliased_frame,
        )


def test_source_hash_authority_and_requirement_drift_fail_closed(built):
    model, frame, distribution, acquisition, architecture = built
    with pytest.raises(WastePumpArchitectureError, match="stale for current Iteration 25"):
        replace(
            architecture,
            source_waste_acquisition_sha256="a" * 64,
            station=replace(architecture.station, source_waste_acquisition_sha256="a" * 64),
        ).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpArchitectureError, match="stale for current structural frame"):
        replace(architecture, source_structural_frame_sha256="a" * 64).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpArchitectureError, match="stale for current authority revision"):
        replace(architecture, source_authority_revision="STALE-REVISION").validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpArchitectureError, match="recovery requirement is stale"):
        replace(
            architecture,
            recovery_ratio_requirement_min=architecture.recovery_ratio_requirement_min - 0.01,
        ).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )


def test_builder_rejects_stale_acquisition_and_corrupted_distribution(built):
    model, frame, distribution, acquisition, _ = built
    stale_acquisition = replace(acquisition, source_distribution_sha256="a" * 64)
    with pytest.raises(WastePumpArchitectureError, match="Iteration 25 waste acquisition"):
        build_waste_pump_architecture(
            model.authority,
            stale_acquisition,
            distribution,
            frame,
        )


def test_manifest_revalidates_nested_corruption_and_is_deterministic(built):
    model, frame, distribution, acquisition, architecture = built
    second = build_waste_pump_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    assert architecture.manifest() == second.manifest()
    assert architecture.architecture_sha256 == second.architecture_sha256
    assert architecture.physical_validation_eligible is False
    assert architecture.evidence_status == ARCHITECTURE_EVIDENCE_STATUS

    object.__setattr__(second.barrier, "performance_status", "VERIFIED")
    with pytest.raises(WastePumpArchitectureError, match="performance status"):
        _ = second.architecture_sha256


def test_hostile_alias_numeric_and_evidence_promotions_fail_closed(built):
    class Alias(str):
        pass

    *_, architecture = built
    with pytest.raises(WastePumpArchitectureError, match="station ID"):
        replace(architecture.station, station_id=Alias(STATION_WASTE))
    with pytest.raises(WastePumpArchitectureError, match="canonical lowercase SHA-256"):
        replace(architecture, source_waste_acquisition_sha256=Alias("a" * 64))
    with pytest.raises(WastePumpArchitectureError, match="not physical validation evidence"):
        replace(architecture, physical_validation_eligible=True)
    with pytest.raises(WastePumpArchitectureError, match="evidence status"):
        replace(architecture, evidence_status="PHYSICAL_VALIDATED")
    for value in (float("nan"), float("inf"), float("-inf"), True, 10**10000):
        with pytest.raises(WastePumpArchitectureError):
            replace(architecture, recovery_ratio_requirement_min=value)
