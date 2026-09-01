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
from masck_one.waste_pump_packaging import (
    ARCHITECTURE_EVIDENCE_STATUS,
    FAULT_DETECTION_STATUS,
    FAULT_IDS,
    FAULT_MITIGATION_STATUS,
    FAULT_REPORTING_STATUS,
    FAULT_VALIDATION_STATUS,
    HYDRAULIC_STATUS,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_WASTE_PUMP_OUTLET,
    PACKAGE_STATUS,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_IDS,
    ROUTE_PUMP_TO_CARTRIDGE,
    ROUTING_STATUS,
    SERVICE_STATUS,
    STATION_WASTE,
    WastePumpPackagingError,
    build_waste_pump_packaging_architecture,
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
    architecture = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    return model, frame, distribution, acquisition, architecture


def test_station_binds_exact_iteration25_source_and_waste_frame_reservation(built):
    _, frame, _, acquisition, architecture = built
    station = architecture.station
    assert station.station_id == STATION_WASTE
    assert station.source_waste_acquisition_sha256 == acquisition.architecture_sha256
    assert architecture.source_waste_acquisition_sha256 == acquisition.architecture_sha256
    assert architecture.source_structural_frame_sha256 == frame.topology_sha256
    assert station.frame_reservation_id == RESERVATION_WASTE


def test_package_geometry_hydraulics_and_supplier_selection_remain_unresolved(built):
    *_, architecture = built
    station = architecture.station
    assert station.package_candidate_id is None
    assert station.package_evidence_sha256 is None
    assert station.envelope_mm is None
    assert station.placement_xyz_mm is None
    assert station.orientation_axis_xyz is None
    assert station.tubing_inner_diameter_mm is None
    assert station.minimum_bend_radius_mm is None
    assert station.connector_standard is None
    assert station.nominal_mixed_phase_flow_mL_s is None
    assert station.suction_pressure_kPa is None
    assert station.package_status == PACKAGE_STATUS
    assert station.routing_status == ROUTING_STATUS
    assert station.hydraulic_status == HYDRAULIC_STATUS
    assert station.service_status == SERVICE_STATUS

    with pytest.raises(WastePumpPackagingError, match="cannot invent pump selection"):
        replace(station, envelope_mm=(20.0, 10.0, 8.0))
    with pytest.raises(WastePumpPackagingError, match="cannot invent pump selection"):
        replace(station, nominal_mixed_phase_flow_mL_s=3.0)
    with pytest.raises(WastePumpPackagingError, match="cannot invent pump selection"):
        replace(station, suction_pressure_kPa=12.0)


def test_routes_preserve_stage_boundary_and_iteration27_handoff(built):
    *_, architecture = built
    assert tuple(route.route_id for route in architecture.routes) == ROUTE_IDS
    assert architecture.routes[0].route_id == ROUTE_ACQUISITION_TO_PUMP
    assert architecture.routes[0].target_interface_id == STATION_WASTE
    assert architecture.routes[1].route_id == ROUTE_PUMP_TO_CARTRIDGE
    assert architecture.routes[1].source_interface_id == INTERFACE_WASTE_PUMP_OUTLET
    assert architecture.routes[1].target_interface_id == INTERFACE_CARTRIDGE_INLET_I27
    assert all(route.hydraulic_status == HYDRAULIC_STATUS for route in architecture.routes)


def test_route_bypass_reversal_alias_and_mutability_fail_closed(built):
    *_, architecture = built
    routes = list(architecture.routes)
    routes[0] = replace(routes[0], target_interface_id=INTERFACE_CARTRIDGE_INLET_I27)
    with pytest.raises(WastePumpPackagingError, match="cannot bypass"):
        replace(architecture, routes=tuple(routes))
    with pytest.raises(WastePumpPackagingError, match="complete controlled route order"):
        replace(architecture, routes=architecture.routes[:-1])
    with pytest.raises(WastePumpPackagingError, match="immutable tuple"):
        replace(architecture, routes=list(architecture.routes))


def test_fault_registry_is_complete_mixed_phase_and_evidence_gated(built):
    *_, architecture = built
    assert tuple(fault.fault_id for fault in architecture.faults) == FAULT_IDS
    for fault in architecture.faults:
        assert fault.detection_status == FAULT_DETECTION_STATUS
        assert fault.mitigation_implementation_status == FAULT_MITIGATION_STATUS
        assert fault.validation_status == FAULT_VALIDATION_STATUS
        assert fault.reporting_status == FAULT_REPORTING_STATUS


def test_fault_registry_missing_reordered_mutable_or_promoted_states_fail_closed(built):
    *_, architecture = built
    with pytest.raises(WastePumpPackagingError, match="complete controlled fault order"):
        replace(architecture, faults=architecture.faults[:-1])
    with pytest.raises(WastePumpPackagingError, match="complete controlled fault order"):
        replace(architecture, faults=tuple(reversed(architecture.faults)))
    with pytest.raises(WastePumpPackagingError, match="immutable tuple"):
        replace(architecture, faults=list(architecture.faults))
    with pytest.raises(WastePumpPackagingError, match="detection status"):
        replace(architecture.faults[0], detection_status="VERIFIED")
    with pytest.raises(WastePumpPackagingError, match="mitigation status"):
        replace(architecture.faults[0], mitigation_implementation_status="IMPLEMENTED")
    with pytest.raises(WastePumpPackagingError, match="validation status"):
        replace(architecture.faults[0], validation_status="VERIFIED")


def test_stale_iteration25_frame_authority_and_requirements_fail_closed(built):
    model, frame, distribution, acquisition, architecture = built
    architecture.validate_current_sources(
        authority=model.authority,
        acquisition=acquisition,
        distribution=distribution,
        frame=frame,
    )

    with pytest.raises(WastePumpPackagingError, match="stale for current Iteration 25"):
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
    with pytest.raises(WastePumpPackagingError, match="stale for current structural frame"):
        replace(architecture, source_structural_frame_sha256="a" * 64).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpPackagingError, match="stale for current authority revision"):
        replace(architecture, source_authority_revision="STALE-REVISION").validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpPackagingError, match="recovery requirement is stale"):
        replace(
            architecture,
            recovery_ratio_requirement_min=architecture.recovery_ratio_requirement_min - 0.01,
        ).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )
    with pytest.raises(WastePumpPackagingError, match="residual-liquid requirement is stale"):
        replace(
            architecture,
            residual_free_liquid_limit_uL=architecture.residual_free_liquid_limit_uL + 1.0,
        ).validate_current_sources(
            authority=model.authority,
            acquisition=acquisition,
            distribution=distribution,
            frame=frame,
        )


def test_builder_revalidates_iteration25_source_chain(built):
    model, frame, distribution, acquisition, _ = built
    stale_acquisition = replace(acquisition, source_distribution_sha256="a" * 64)
    with pytest.raises(WastePumpPackagingError, match="Iteration 25 waste acquisition is stale"):
        build_waste_pump_packaging_architecture(
            model.authority,
            stale_acquisition,
            distribution,
            frame,
        )


def test_hostile_string_aliases_and_status_spoofing_fail_closed(built):
    class Alias(str):
        pass

    *_, architecture = built
    with pytest.raises(WastePumpPackagingError, match="station ID"):
        replace(architecture.station, station_id=Alias(STATION_WASTE))
    with pytest.raises(WastePumpPackagingError, match="canonical lowercase SHA-256"):
        replace(architecture, source_waste_acquisition_sha256=Alias("a" * 64))
    with pytest.raises(WastePumpPackagingError, match="hydraulic status"):
        replace(architecture.station, hydraulic_status="NOT_VALIDATION_GATED_BUT_CONTAINS_TOKEN")
    with pytest.raises(WastePumpPackagingError, match="evidence status"):
        replace(architecture, evidence_status=Alias(ARCHITECTURE_EVIDENCE_STATUS))


def test_nonfinite_boolean_and_oversized_numeric_requirements_fail_closed(built):
    *_, architecture = built
    for value in (float("nan"), float("inf"), float("-inf"), True, 10**10000):
        with pytest.raises(WastePumpPackagingError):
            replace(architecture, recovery_ratio_requirement_min=value)
    for value in (float("nan"), float("inf"), float("-inf"), False, 10**10000):
        with pytest.raises(WastePumpPackagingError):
            replace(architecture, residual_free_liquid_limit_uL=value)


def test_manifest_revalidates_nested_corruption_and_is_deterministic(built):
    model, frame, distribution, acquisition, architecture = built
    second = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    assert architecture.manifest() == second.manifest()
    assert architecture.architecture_sha256 == second.architecture_sha256
    assert architecture.physical_validation_eligible is False
    assert architecture.evidence_status == ARCHITECTURE_EVIDENCE_STATUS

    corrupted = second
    object.__setattr__(corrupted.faults[0], "validation_status", "VERIFIED")
    with pytest.raises(WastePumpPackagingError, match="validation status"):
        _ = corrupted.architecture_sha256


def test_physical_evidence_promotion_is_rejected(built):
    *_, architecture = built
    with pytest.raises(WastePumpPackagingError, match="not physical validation evidence"):
        replace(architecture, physical_validation_eligible=True)
    with pytest.raises(WastePumpPackagingError, match="evidence status"):
        replace(architecture, evidence_status="PHYSICAL_VALIDATED")
