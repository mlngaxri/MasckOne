import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.coverage import build_facial_coverage_mesh
from masck_one.facial_surface import build_planar_development_surface
from masck_one.interface_boundaries import (
    BOUNDARY_EYE_LEFT,
    BOUNDARY_EYE_RIGHT,
    BOUNDARY_IDS,
    BOUNDARY_OUTER_PERIMETER,
    InterfaceBoundaryDefinition,
    InterfaceBoundaryError,
    build_interface_boundary_topology,
)
from masck_one.interface_topology import build_compliant_interface_topology
from masck_one.protected_volumes import build_protected_volumes
from masck_one.spatial import CanonicalDatums


def _build():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    interface = build_compliant_interface_topology(authority, coverage)
    topology = build_interface_boundary_topology(authority, surface, coverage, interface)
    return authority, coverage, interface, topology


def test_all_six_interface_boundaries_are_present_as_single_closed_loops():
    _, _, _, topology = _build()

    assert tuple(topology.edges_by_boundary) == BOUNDARY_IDS
    assert all(topology.edges_by_boundary[boundary_id] for boundary_id in BOUNDARY_IDS)
    assert all(topology.boundary_component_count(boundary_id) == 1 for boundary_id in BOUNDARY_IDS)
    assert all(topology.boundary_is_closed_loop(boundary_id) for boundary_id in BOUNDARY_IDS)


def test_outer_perimeter_edges_have_contact_on_one_side_and_no_protected_triangle():
    _, _, _, topology = _build()

    outer = topology.edges_by_boundary[BOUNDARY_OUTER_PERIMETER]
    assert outer
    assert all(len(edge.incident_triangle_indices) == 1 for edge in outer)
    assert all(edge.protected_triangle_index is None for edge in outer)


def test_aperture_transition_edges_are_exact_contact_to_protected_boundaries():
    _, coverage, interface, topology = _build()
    coverage_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
    interface_by_id = {assignment.triangle_index: assignment for assignment in interface.assignments}

    for boundary_id in BOUNDARY_IDS[1:]:
        definition = topology.definition_by_id[boundary_id]
        for edge in topology.edges_by_boundary[boundary_id]:
            assert edge.protected_triangle_index is not None
            assert len(edge.incident_triangle_indices) == 2
            assert interface_by_id[edge.contact_triangle_index].contact_intent is True
            assert interface_by_id[edge.protected_triangle_index].contact_intent is False
            assert coverage_by_id[edge.protected_triangle_index].region_id == definition.protected_region_id


def test_no_transition_width_or_interface_thickness_is_invented():
    _, _, _, topology = _build()

    for definition in topology.definitions:
        assert definition.nominal_transition_width_mm is None
        assert definition.nominal_interface_thickness_mm is None
        assert definition.material_status == "UNSELECTED_VALIDATION_GATED"


def test_eye_rigid_roll_authority_is_preserved_as_reference_only():
    authority, _, _, topology = _build()
    expected = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")

    for boundary_id in (BOUNDARY_EYE_LEFT, BOUNDARY_EYE_RIGHT):
        definition = topology.definition_by_id[boundary_id]
        assert definition.rigid_roll_reference_mm == expected
        assert "NOT_COMPLIANT_PROFILE" in definition.rigid_roll_reference_status


def test_interface_boundary_topology_is_deterministic():
    _, _, _, first = _build()
    _, _, _, second = _build()

    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest() == second.manifest()


def test_numeric_transition_width_is_rejected_without_authority():
    with pytest.raises(InterfaceBoundaryError):
        InterfaceBoundaryDefinition(
            boundary_id=BOUNDARY_OUTER_PERIMETER,
            functional_role="invalid numeric-width test",
            boundary_kind="OUTER_PERIMETER",
            protected_region_id=None,
            compliance_intent=True,
            fluid_containment_intent=True,
            protected_opening_exclusion_intent=False,
            nominal_transition_width_mm=2.0,
            nominal_interface_thickness_mm=None,
            rigid_roll_reference_mm=None,
            rigid_roll_reference_status="TEST",
            geometry_status="TEST",
            material_status="TEST",
            evidence_status="TEST",
        )


def test_iteration_12_cannot_be_promoted_to_anatomical_validation_evidence():
    _, _, _, topology = _build()

    assert topology.anatomical_validation_eligible is False
    assert "NOT_SEAL_FIT_INGRESS_PRESSURE_OR_ANATOMICAL_VALIDATION" in topology.evidence_status
