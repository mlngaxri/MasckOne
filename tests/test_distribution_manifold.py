from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_manifold import (
    ARCHITECTURE_EVIDENCE_STATUS,
    AUTHORITY_GEOMETRY_STATUS,
    BRANCH_CLEANSER,
    BRANCH_FRESH_WATER,
    BRANCH_GEOMETRY_STATUS,
    FLOW_BALANCE_STATUS,
    OUTLET_COUNT_STATUS,
    OUTLET_REALIZATION_STATUS,
    PRESSURE_DROP_STATUS,
    DistributionManifoldError,
    build_distribution_manifold_architecture,
)
from masck_one.fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_WATER_MANIFOLD,
    build_fresh_pump_packaging_architecture,
)
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture


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
    pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        pump,
        water,
        cleanser,
        frame,
    )
    return model.authority, water, cleanser, frame, pump, manifold


def test_authority_counts_and_pump_provenance_are_bound(built):
    authority, _, _, _, pump, manifold = built
    assert manifold.source_authority_revision == authority.get("project", "authority_revision")
    assert manifold.source_pump_architecture_sha256 == pump.architecture_sha256
    assert manifold.water_outlet_count == 18
    assert manifold.cleanser_outlet_count == 6
    assert len(manifold.outlets) == 24
    assert manifold.outlet_count_status == OUTLET_COUNT_STATUS
    assert manifold.authority_geometry_status == AUTHORITY_GEOMETRY_STATUS


def test_branches_are_isolated_and_bind_exact_upstream_routes(built):
    *_, manifold = built
    assert tuple(item.branch_id for item in manifold.branches) == (
        BRANCH_FRESH_WATER,
        BRANCH_CLEANSER,
    )
    assert tuple(item.fluid_identity for item in manifold.branches) == (
        FLUID_FRESH_WATER,
        FLUID_CLEANSER,
    )
    assert tuple(item.upstream_route_id for item in manifold.branches) == (
        ROUTE_WATER_MANIFOLD,
        ROUTE_CLEANSER_MANIFOLD,
    )
    assert tuple(len(item.outlet_ids) for item in manifold.branches) == (18, 6)
    assert set(manifold.branches[0].outlet_ids).isdisjoint(manifold.branches[1].outlet_ids)


def test_iteration23_does_not_invent_realized_geometry_or_performance(built):
    *_, manifold = built
    for branch in manifold.branches:
        assert branch.nominal_inner_diameter_mm is None
        assert branch.metering_restriction_geometry_mm is None
        assert branch.centerline_xyz_mm is None
        assert branch.geometry_status == BRANCH_GEOMETRY_STATUS
        assert branch.pressure_drop_status == PRESSURE_DROP_STATUS
        assert branch.flow_balance_status == FLOW_BALANCE_STATUS
    for outlet in manifold.outlets:
        assert outlet.position_xyz_mm is None
        assert outlet.direction_xyz is None
        assert outlet.realization_status == OUTLET_REALIZATION_STATUS


def test_crossed_branch_or_upstream_route_fails_closed(built):
    *_, manifold = built
    with pytest.raises(DistributionManifoldError, match="cannot cross fluid branches"):
        replace(manifold.outlets[0], branch_id=BRANCH_CLEANSER)
    with pytest.raises(DistributionManifoldError, match="cannot cross or alias"):
        replace(manifold.branches[0], upstream_route_id=ROUTE_CLEANSER_MANIFOLD)


def test_missing_duplicate_or_cross_owned_outlets_fail_closed(built):
    *_, manifold = built
    with pytest.raises(DistributionManifoldError, match="complete controlled identity"):
        replace(manifold, outlets=manifold.outlets[:-1])
    duplicate = manifold.outlets[:-1] + (manifold.outlets[0],)
    with pytest.raises(DistributionManifoldError, match="complete controlled identity"):
        replace(manifold, outlets=duplicate)
    branches = list(manifold.branches)
    branches[0] = replace(branches[0], outlet_ids=branches[0].outlet_ids[:-1])
    with pytest.raises(DistributionManifoldError, match="cannot cross, omit, or alias"):
        replace(manifold, branches=tuple(branches))


def test_uncontrolled_geometry_cannot_enter_iteration23(built):
    *_, manifold = built
    with pytest.raises(DistributionManifoldError, match="cannot invent branch bore"):
        replace(manifold.branches[0], nominal_inner_diameter_mm=0.8)
    with pytest.raises(DistributionManifoldError, match="cannot assign outlet positions"):
        replace(manifold.outlets[0], position_xyz_mm=(0.0, 0.0, 0.0))
    with pytest.raises(DistributionManifoldError, match="cannot assign outlet positions"):
        replace(manifold.outlets[0], direction_xyz=(1.0, 0.0, 0.0))


def test_stale_pump_and_authority_inputs_fail_closed(built):
    authority, water, cleanser, frame, pump, manifold = built
    with pytest.raises(DistributionManifoldError, match="stale for current pump"):
        replace(manifold, source_pump_architecture_sha256="a" * 64).validate_current_sources(
            authority=authority,
            pump=pump,
            water=water,
            cleanser=cleanser,
            frame=frame,
        )
    with pytest.raises(DistributionManifoldError, match="authority inputs are stale"):
        replace(manifold, source_authority_revision="STALE-AUTHORITY").validate_current_sources(
            authority=authority,
            pump=pump,
            water=water,
            cleanser=cleanser,
            frame=frame,
        )
    with pytest.raises(DistributionManifoldError, match="exact Authority"):
        manifold.validate_current_sources(
            authority=object(),
            pump=pump,
            water=water,
            cleanser=cleanser,
            frame=frame,
        )


def test_status_promotions_and_hostile_string_subclasses_fail_closed(built):
    *_, manifold = built
    branch = manifold.branches[0]
    outlet = manifold.outlets[0]
    with pytest.raises(DistributionManifoldError, match="branch geometry status"):
        replace(branch, geometry_status="GEOMETRY_VALIDATED")
    with pytest.raises(DistributionManifoldError, match="pressure-drop status"):
        replace(branch, pressure_drop_status="PRESSURE_DROP_VALIDATED")
    with pytest.raises(DistributionManifoldError, match="flow-balance status"):
        replace(branch, flow_balance_status="FLOW_BALANCED")
    with pytest.raises(DistributionManifoldError, match="realization status"):
        replace(outlet, realization_status="POSITION_AND_DIRECTION_VALIDATED")
    with pytest.raises(DistributionManifoldError, match="evidence status"):
        replace(manifold, evidence_status="PHYSICALLY_VALIDATED")

    class LyingStr(str):
        pass

    with pytest.raises(DistributionManifoldError, match="branch geometry status"):
        replace(branch, geometry_status=LyingStr(BRANCH_GEOMETRY_STATUS))
    with pytest.raises(DistributionManifoldError, match="realization status"):
        replace(outlet, realization_status=LyingStr(OUTLET_REALIZATION_STATUS))
    with pytest.raises(DistributionManifoldError, match="evidence status"):
        replace(manifold, evidence_status=LyingStr(ARCHITECTURE_EVIDENCE_STATUS))


def test_mutable_containers_and_numeric_aliases_fail_closed(built):
    *_, manifold = built
    with pytest.raises(DistributionManifoldError, match="exact immutable two-branch"):
        replace(manifold, branches=list(manifold.branches))
    with pytest.raises(DistributionManifoldError, match="immutable tuple"):
        replace(manifold, outlets=list(manifold.outlets))
    with pytest.raises(DistributionManifoldError, match="finite real"):
        replace(manifold.outlets[0], diameter_seed_mm=True)
    with pytest.raises(DistributionManifoldError, match="finite"):
        replace(manifold.outlets[0], direction_sensitivity_deg=float("nan"))


def test_manifest_is_deterministic_and_not_physical_evidence(built):
    authority, water, cleanser, frame, pump, manifold = built
    second = build_distribution_manifold_architecture(
        authority,
        pump,
        water,
        cleanser,
        frame,
    )
    assert manifold.manifest() == second.manifest()
    assert manifold.architecture_sha256 == second.architecture_sha256
    assert manifold.physical_validation_eligible is False
    assert manifold.evidence_status == ARCHITECTURE_EVIDENCE_STATUS
