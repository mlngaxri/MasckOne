from dataclasses import replace

import pytest

import masck_one.wet_electrical_source_graph as source_graph_module
from masck_one.cleanser_storage import PORT_OUTLET as CLEANSER_PORT_OUTLET
from masck_one.distribution_manifold import (
    BRANCH_CLEANSER,
    BRANCH_FRESH_WATER,
    INLET_CLEANSER,
    INLET_FRESH_WATER,
)
from masck_one.fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    INTERFACE_CLEANSER_PUMP_OUTLET,
    INTERFACE_WATER_PUMP_OUTLET,
    ROUTE_CLEANSER_MANIFOLD,
    ROUTE_CLEANSER_SOURCE,
    ROUTE_WATER_MANIFOLD,
    ROUTE_WATER_SOURCE,
    STATION_CLEANSER,
    STATION_WATER,
)
from masck_one.waste_acquisition import PHASE_MIXED_WASTE, ROUTE_DESTINATION
from masck_one.waste_pump_architecture import (
    BARRIER_WASTE,
    INTERFACE_BARRIER_OUTLET,
    INTERFACE_CARTRIDGE_INLET_I27,
    INTERFACE_PUMP_OUTLET,
    ROUTE_ACQUISITION_TO_PUMP,
    ROUTE_BARRIER_TO_CARTRIDGE,
    ROUTE_PUMP_TO_BARRIER,
    STATION_WASTE,
)
from masck_one.water_reservoir import PORT_PICKUP as WATER_PORT_PICKUP
from masck_one.wet_electrical_source_graph import (
    AUTHORITY_REVISION,
    BLOCKER_ASSEMBLY_BOUNDARY,
    BLOCKER_DRY_SIDE,
    BLOCKER_FRESH_ROUTE_GEOMETRY,
    BLOCKER_HARNESS,
    BLOCKER_HMI_WARM_THERMAL,
    BLOCKER_IDS,
    CANONICAL_FLUID_DOMAINS,
    EVIDENCE_STATUS,
    FLUID_DOMAIN_CLEANSER,
    FLUID_DOMAIN_FRESH_WATER,
    FLUID_DOMAIN_MIXED_WASTE,
    MANIFOLD_INLET_BRANCH_BINDING_BY_DOMAIN,
    PHYSICAL_MATERIAL_NAMES,
    REFERENCE_REVIEW_NAMES,
    RELEASED_FLUID_IDENTITY_BY_DOMAIN,
    SCHEMA,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    SourceEdge,
    SourceNode,
    WetElectricalSourceGraphError,
    build_wet_electrical_source_graph,
)


@pytest.fixture(scope="module")
def graph():
    return build_wet_electrical_source_graph()


def test_source_graph_binds_live_main_authority_and_world_frame(graph):
    assert graph.schema == SCHEMA
    assert graph.source_main_sha == SOURCE_MAIN_SHA
    assert graph.authority_revision == AUTHORITY_REVISION
    assert graph.world_frame_id == WORLD_FRAME_ID
    assert graph.evidence_status == EVIDENCE_STATUS
    assert graph.integration_release_ready is False
    assert graph.physical_validation_eligible is False


def test_canonical_fluid_domains_are_distinct_and_preserve_released_identity(graph):
    assert CANONICAL_FLUID_DOMAINS == ("FRESH_WATER", "CLEANSER", "MIXED_WASTE")
    assert len(set(CANONICAL_FLUID_DOMAINS)) == 3
    assert RELEASED_FLUID_IDENTITY_BY_DOMAIN == {
        FLUID_DOMAIN_FRESH_WATER: FLUID_FRESH_WATER,
        FLUID_DOMAIN_CLEANSER: FLUID_CLEANSER,
        FLUID_DOMAIN_MIXED_WASTE: PHASE_MIXED_WASTE,
    }
    manifest = graph.manifest()
    assert manifest["canonical_fluid_domains"] == list(CANONICAL_FLUID_DOMAINS)
    assert manifest["released_fluid_identity_by_domain"]["MIXED_WASTE"] == PHASE_MIXED_WASTE


def test_released_fresh_interfaces_and_branches_are_isolated_not_shared_alias_nodes(graph):
    nodes = {node.node_id: node for node in graph.nodes}
    assert "FRESH_DISTRIBUTION" not in nodes
    assert MANIFOLD_INLET_BRANCH_BINDING_BY_DOMAIN == {
        FLUID_DOMAIN_FRESH_WATER: (INLET_FRESH_WATER, BRANCH_FRESH_WATER),
        FLUID_DOMAIN_CLEANSER: (INLET_CLEANSER, BRANCH_CLEANSER),
    }
    for node_id in (
        WATER_PORT_PICKUP,
        INTERFACE_WATER_PUMP_OUTLET,
        INLET_FRESH_WATER,
        BRANCH_FRESH_WATER,
    ):
        assert nodes[node_id].fluid_domain == FLUID_DOMAIN_FRESH_WATER
        assert nodes[node_id].fluid_identity == FLUID_FRESH_WATER
    for node_id in (
        CLEANSER_PORT_OUTLET,
        INTERFACE_CLEANSER_PUMP_OUTLET,
        INLET_CLEANSER,
        BRANCH_CLEANSER,
    ):
        assert nodes[node_id].fluid_domain == FLUID_DOMAIN_CLEANSER
        assert nodes[node_id].fluid_identity == FLUID_CLEANSER
    manifest = graph.manifest()["manifold_inlet_branch_binding_by_domain"]
    assert manifest == {
        "FRESH_WATER": {
            "inlet_interface_id": INLET_FRESH_WATER,
            "branch_id": BRANCH_FRESH_WATER,
        },
        "CLEANSER": {
            "inlet_interface_id": INLET_CLEANSER,
            "branch_id": BRANCH_CLEANSER,
        },
    }


def test_route_identity_domain_exact_producer_interfaces_and_stage_order_are_exact(graph):
    actual = tuple(
        (
            edge.edge_id,
            edge.fluid_domain,
            edge.fluid_identity,
            edge.source_node_id,
            edge.target_node_id,
            edge.stage,
        )
        for edge in graph.edges
    )
    assert actual == (
        (
            ROUTE_WATER_SOURCE,
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
            WATER_PORT_PICKUP,
            STATION_WATER,
            "SOURCE_TO_PUMP",
        ),
        (
            ROUTE_WATER_MANIFOLD,
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
            INTERFACE_WATER_PUMP_OUTLET,
            INLET_FRESH_WATER,
            "PUMP_TO_MANIFOLD",
        ),
        (
            ROUTE_CLEANSER_SOURCE,
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
            CLEANSER_PORT_OUTLET,
            STATION_CLEANSER,
            "SOURCE_TO_PUMP",
        ),
        (
            ROUTE_CLEANSER_MANIFOLD,
            FLUID_DOMAIN_CLEANSER,
            FLUID_CLEANSER,
            INTERFACE_CLEANSER_PUMP_OUTLET,
            INLET_CLEANSER,
            "PUMP_TO_MANIFOLD",
        ),
        (
            ROUTE_ACQUISITION_TO_PUMP,
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
            ROUTE_DESTINATION,
            STATION_WASTE,
            "ACQUISITION_TO_PUMP",
        ),
        (
            ROUTE_PUMP_TO_BARRIER,
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
            INTERFACE_PUMP_OUTLET,
            BARRIER_WASTE,
            "PUMP_TO_PASSIVE_BACKFLOW_BARRIER",
        ),
        (
            ROUTE_BARRIER_TO_CARTRIDGE,
            FLUID_DOMAIN_MIXED_WASTE,
            PHASE_MIXED_WASTE,
            INTERFACE_BARRIER_OUTLET,
            INTERFACE_CARTRIDGE_INLET_I27,
            "PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE_HANDOFF",
        ),
    )


def test_component_shorthand_never_replaces_released_route_interfaces(graph):
    endpoints = {
        endpoint
        for edge in graph.edges
        for endpoint in (edge.source_node_id, edge.target_node_id)
    }
    assert "WATER_RESERVOIR" not in endpoints
    assert "CLEANSER_STORAGE" not in endpoints
    assert "WASTE_ACQUISITION" not in endpoints
    assert "WASTE_CARTRIDGE" not in endpoints
    assert WATER_PORT_PICKUP in endpoints
    assert CLEANSER_PORT_OUTLET in endpoints
    assert ROUTE_DESTINATION in endpoints
    assert INTERFACE_CARTRIDGE_INLET_I27 in endpoints


def test_mixed_waste_retains_explicit_passive_backflow_stage_and_interfaces(graph):
    waste = tuple(edge for edge in graph.edges if edge.fluid_domain == FLUID_DOMAIN_MIXED_WASTE)
    assert tuple(edge.edge_id for edge in waste) == (
        ROUTE_ACQUISITION_TO_PUMP,
        ROUTE_PUMP_TO_BARRIER,
        ROUTE_BARRIER_TO_CARTRIDGE,
    )
    assert waste[0].source_node_id == ROUTE_DESTINATION
    assert waste[0].target_node_id == STATION_WASTE
    assert waste[1].source_node_id == INTERFACE_PUMP_OUTLET
    assert waste[1].target_node_id == BARRIER_WASTE
    assert waste[2].source_node_id == INTERFACE_BARRIER_OUTLET
    assert waste[2].target_node_id == INTERFACE_CARTRIDGE_INLET_I27
    assert not any(
        edge.source_node_id == INTERFACE_PUMP_OUTLET
        and edge.target_node_id == INTERFACE_CARTRIDGE_INLET_I27
        for edge in waste
    )


def test_released_main_does_not_claim_unmerged_realization_geometry(graph):
    nodes = {item.node_id: item for item in graph.nodes}
    assert nodes[STATION_WATER].geometry_state == "PACKAGE_AND_CENTERLINES_UNRESOLVED"
    assert nodes[STATION_CLEANSER].geometry_state == "PACKAGE_AND_CENTERLINES_UNRESOLVED"
    assert nodes[STATION_WASTE].geometry_state == (
        "PACKAGE_UNRESOLVED_CENTERLINE_BACKBONE_RELEASED"
    )
    assert nodes[BARRIER_WASTE].geometry_state == (
        "COMPONENT_UNRESOLVED_CENTERLINE_BACKBONE_RELEASED"
    )
    assert nodes["WASTE_CARTRIDGE"].material_role == "PACKAGE_REFERENCE"


def test_cells_12_to_14_missing_producers_remain_explicit_blockers(graph):
    nodes = {item.node_id: item for item in graph.nodes}
    assert nodes["BATTERY_REFERENCE"].release_state == "RELEASED_REFERENCE_ONLY"
    for node_id in ("DRY_SIDE_BAY", "HARNESS_BULKHEAD", "HMI_WARM_THERMAL"):
        assert nodes[node_id].release_state == "ABSENT"
        assert nodes[node_id].material_role == "UNRESOLVED"
        assert nodes[node_id].fluid_domain is None
        assert nodes[node_id].fluid_identity is None
    assert graph.blockers == (
        BLOCKER_ASSEMBLY_BOUNDARY,
        BLOCKER_FRESH_ROUTE_GEOMETRY,
        BLOCKER_DRY_SIDE,
        BLOCKER_HARNESS,
        BLOCKER_HMI_WARM_THERMAL,
    )
    assert graph.blockers == BLOCKER_IDS


def test_current_export_reference_material_mixing_is_machine_visible(graph):
    assert graph.physical_material_names == PHYSICAL_MATERIAL_NAMES == ("rigid_shell",)
    assert graph.reference_review_names == REFERENCE_REVIEW_NAMES
    assert graph.current_export_selected_names == (
        "rigid_shell",
        "nasal_lobe_membrane_reference",
        "actuator_envelope_1",
        "actuator_envelope_2",
        "actuator_envelope_3",
        "actuator_envelope_4",
        "water_reservoir_envelope",
        "battery_reference_envelope",
    )
    assert graph.illegal_reference_material_names == (
        "nasal_lobe_membrane_reference",
        "actuator_envelope_1",
        "actuator_envelope_2",
        "actuator_envelope_3",
        "actuator_envelope_4",
        "water_reservoir_envelope",
        "battery_reference_envelope",
    )
    assert graph.manifest()["first_integration_blocker"] == BLOCKER_ASSEMBLY_BOUNDARY


def test_cross_fluid_edge_retagging_fails_closed(graph):
    first = graph.edges[0]
    with pytest.raises(WetElectricalSourceGraphError, match="fluid identity does not match"):
        replace(first, fluid_domain=FLUID_DOMAIN_CLEANSER)
    with pytest.raises(WetElectricalSourceGraphError, match="cannot cross or alias"):
        replace(
            graph,
            edges=(
                replace(first, fluid_domain=FLUID_DOMAIN_CLEANSER, fluid_identity=FLUID_CLEANSER),
                *graph.edges[1:],
            ),
        )


def test_cross_fluid_source_and_target_interface_aliasing_fails_closed(graph):
    water_source = graph.edges[0]
    water_to_manifold = graph.edges[1]
    with pytest.raises(WetElectricalSourceGraphError, match="cannot cross or alias"):
        replace(
            graph,
            edges=(
                replace(water_source, source_node_id=CLEANSER_PORT_OUTLET),
                *graph.edges[1:],
            ),
        )
    with pytest.raises(WetElectricalSourceGraphError, match="cannot cross or alias"):
        replace(
            graph,
            edges=(
                graph.edges[0],
                replace(water_to_manifold, target_node_id=INLET_CLEANSER),
                *graph.edges[2:],
            ),
        )


def test_manifold_inlet_and_branch_identity_aliasing_fails_closed(graph):
    cleanser_inlet_index = next(
        index for index, node in enumerate(graph.nodes) if node.node_id == INLET_CLEANSER
    )
    cleanser_inlet = graph.nodes[cleanser_inlet_index]
    with pytest.raises(WetElectricalSourceGraphError, match="fluid identity does not match"):
        replace(cleanser_inlet, fluid_domain=FLUID_DOMAIN_FRESH_WATER)
    mutated = replace(
        cleanser_inlet,
        fluid_domain=FLUID_DOMAIN_FRESH_WATER,
        fluid_identity=FLUID_FRESH_WATER,
    )
    nodes = list(graph.nodes)
    nodes[cleanser_inlet_index] = mutated
    with pytest.raises(WetElectricalSourceGraphError, match="cannot cross or alias"):
        replace(graph, nodes=tuple(nodes))


def test_mixed_waste_cannot_alias_fresh_or_bypass_barrier(graph):
    waste_pump_to_barrier = graph.edges[5]
    with pytest.raises(WetElectricalSourceGraphError, match="fluid identity does not match"):
        replace(waste_pump_to_barrier, fluid_domain=FLUID_DOMAIN_FRESH_WATER)
    with pytest.raises(WetElectricalSourceGraphError, match="route graph"):
        replace(
            graph,
            edges=(
                *graph.edges[:5],
                replace(
                    waste_pump_to_barrier,
                    target_node_id=INTERFACE_CARTRIDGE_INLET_I27,
                    stage="PUMP_TO_CARTRIDGE",
                ),
                graph.edges[6],
            ),
        )


def test_node_domain_identity_aliasing_fails_closed(graph):
    cleanser_branch = next(node for node in graph.nodes if node.node_id == BRANCH_CLEANSER)
    with pytest.raises(WetElectricalSourceGraphError, match="fluid identity does not match"):
        replace(cleanser_branch, fluid_domain=FLUID_DOMAIN_FRESH_WATER)
    with pytest.raises(WetElectricalSourceGraphError, match="fluid domain is not canonical"):
        replace(cleanser_branch, fluid_domain="WATER")


def test_material_reference_promotion_and_false_green_fail_closed(graph):
    with pytest.raises(WetElectricalSourceGraphError, match="physical material boundary changed"):
        replace(graph, physical_material_names=("rigid_shell", "water_reservoir_envelope"))
    with pytest.raises(WetElectricalSourceGraphError, match="reference review boundary changed"):
        replace(
            graph,
            reference_review_names=tuple(
                name for name in graph.reference_review_names
                if name != "water_reservoir_envelope"
            ),
        )
    with pytest.raises(WetElectricalSourceGraphError, match="no longer the first blocker"):
        replace(graph, illegal_reference_material_names=())
    with pytest.raises(WetElectricalSourceGraphError, match="cannot be marked release ready"):
        replace(graph, integration_release_ready=True)
    with pytest.raises(WetElectricalSourceGraphError, match="physical-validation eligibility"):
        replace(graph, physical_validation_eligible=True)


def test_bool_coercion_is_rejected(graph):
    with pytest.raises(WetElectricalSourceGraphError, match="cannot be marked release ready"):
        replace(graph, integration_release_ready=0)
    with pytest.raises(WetElectricalSourceGraphError, match="physical-validation eligibility"):
        replace(graph, physical_validation_eligible=0)


def test_edge_and_node_identity_fail_closed(graph):
    first = graph.edges[0]
    with pytest.raises(WetElectricalSourceGraphError, match="all fluid edges"):
        replace(
            graph,
            edges=(replace(first, target_node_id="NOT-A-NODE"), *graph.edges[1:]),
        )
    with pytest.raises(WetElectricalSourceGraphError, match="source edge IDs must be unique"):
        replace(graph, edges=(graph.edges[0], graph.edges[0], *graph.edges[2:]))
    with pytest.raises(WetElectricalSourceGraphError):
        SourceEdge(
            "",
            FLUID_DOMAIN_FRESH_WATER,
            FLUID_FRESH_WATER,
            WATER_PORT_PICKUP,
            STATION_WATER,
            "SOURCE_TO_PUMP",
            "UNRESOLVED",
        )
    with pytest.raises(WetElectricalSourceGraphError, match="source node IDs must be unique"):
        replace(graph, nodes=(graph.nodes[0], graph.nodes[0], *graph.nodes[2:]))
    with pytest.raises(WetElectricalSourceGraphError):
        SourceNode(" ", "CELL9", "RELEASED", "STATE", "TOPOLOGY_ONLY")


def test_source_blob_movement_forces_reconstruction(monkeypatch):
    original = source_graph_module.SOURCE_GIT_BLOB_IDENTITIES
    path, _ = original[0]
    monkeypatch.setattr(
        source_graph_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        ((path, "0" * 40), *original[1:]),
    )
    with pytest.raises(WetElectricalSourceGraphError, match="source moved"):
        build_wet_electrical_source_graph()


def test_new_realization_source_forces_reconstruction(monkeypatch):
    monkeypatch.setattr(
        source_graph_module,
        "UNRELEASED_REALIZATION_PATHS",
        ("src/masck_one/model.py",),
    )
    with pytest.raises(WetElectricalSourceGraphError, match="previously unmerged realization appeared"):
        build_wet_electrical_source_graph()


def test_partial_custom_reconstruction_is_rejected():
    with pytest.raises(WetElectricalSourceGraphError, match="both be supplied"):
        build_wet_electrical_source_graph(authority=source_graph_module.load_authority())


def test_manifest_is_deterministic_hash_bound_and_default_boundary_is_cached(graph):
    source_graph_module._default_model_boundary.cache_clear()
    first = build_wet_electrical_source_graph()
    cache_after_first = source_graph_module._default_model_boundary.cache_info()
    second = build_wet_electrical_source_graph()
    cache_after_second = source_graph_module._default_model_boundary.cache_info()
    assert second.manifest() == first.manifest()
    assert second.manifest_sha256 == first.manifest_sha256
    assert first.manifest()["manifest_sha256"] == first.manifest_sha256
    assert len(first.manifest_sha256) == 64
    assert cache_after_first.misses == 1
    assert cache_after_second.hits >= 1
