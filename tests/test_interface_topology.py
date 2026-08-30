import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.coverage import REGION_T_NOSE_PHILTRUM, build_facial_coverage_mesh
from masck_one.facial_surface import build_planar_development_surface
from masck_one.interface_topology import (
    CONTACT_CONNECTIVITY_STATUS,
    MATERIAL_CONTINUITY_STATUS,
    InterfaceParameterZone,
    InterfaceTopologyError,
    ZONE_OPENING_NOSTRIL_LEFT,
    ZONE_OPENING_NOSTRIL_RIGHT,
    ZONE_T_NOSE_PHILTRUM,
    build_compliant_interface_topology,
)
from masck_one.protected_volumes import build_protected_volumes
from masck_one.spatial import CanonicalDatums


def _build():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    reference = build_facial_reference(authority, datums)
    surface = build_planar_development_surface(authority)
    protected = build_protected_volumes(authority, reference, surface)
    coverage = build_facial_coverage_mesh(authority, reference, surface, protected)
    topology = build_compliant_interface_topology(authority, coverage)
    return authority, coverage, topology


def test_every_coverage_triangle_receives_exactly_one_interface_assignment():
    _, coverage, topology = _build()
    assert len(topology.assignments) == len(coverage.triangles)
    assert [item.triangle_index for item in topology.assignments] == list(range(len(coverage.triangles)))
    assert topology.coverage_segmentation_sha256 == coverage.segmentation_sha256
    assert len(topology.topology_sha256) == 64


def test_contact_and_protected_areas_are_exactly_conserved():
    _, coverage, topology = _build()
    assert topology.contact_area_mm2 == pytest.approx(coverage.target_area_mm2, abs=1e-8)
    assert topology.protected_opening_area_mm2 == pytest.approx(coverage.protected_area_mm2, abs=1e-8)
    assert topology.t_zone_contact_area_mm2 == pytest.approx(coverage.t_zone_target_area_mm2, abs=1e-8)


def test_refined_contact_topology_is_one_edge_connected_field():
    _, coverage, topology = _build()
    components = topology.contact_components(coverage)
    assert len(components) == 1
    assert components[0].area_mm2 == pytest.approx(topology.contact_area_mm2, abs=1e-8)
    assert topology.contact_component_count(coverage) == 1
    assert topology.contact_connectivity_status == CONTACT_CONNECTIVITY_STATUS


def test_connectivity_diagnostics_do_not_claim_physical_membrane_continuity():
    _, coverage, topology = _build()
    manifest = topology.connectivity_manifest(coverage)
    assert manifest["component_count"] == 1
    assert manifest["contact_connectivity_status"] == CONTACT_CONNECTIVITY_STATUS
    assert manifest["material_continuity_status"] == MATERIAL_CONTINUITY_STATUS
    assert topology.material_continuity_status == MATERIAL_CONTINUITY_STATUS


def test_nostrils_are_protected_openings_and_never_skin_contact_targets():
    _, coverage, topology = _build()
    assignments = topology.assignments
    left = [item for item in assignments if item.parameter_zone_id == ZONE_OPENING_NOSTRIL_LEFT]
    right = [item for item in assignments if item.parameter_zone_id == ZONE_OPENING_NOSTRIL_RIGHT]
    assert left and right
    assert all(item.protected_opening and not item.contact_intent for item in left + right)
    coverage_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
    assert all(not coverage_by_id[item.triangle_index].is_target for item in left + right)


def test_nose_to_upper_lip_region_remains_an_active_contact_target():
    _, coverage, topology = _build()
    coverage_by_id = {triangle.triangle_index: triangle for triangle in coverage.triangles}
    philtrum_assignments = [
        item
        for item in topology.assignments
        if item.parameter_zone_id == ZONE_T_NOSE_PHILTRUM
        and item.contact_intent
        and coverage.t_zone_definition.stem_y_min_mm
        <= coverage_by_id[item.triangle_index].centroid.y
        <= 0.0
    ]
    assert philtrum_assignments
    assert sum(item.area_mm2 for item in philtrum_assignments) == pytest.approx(
        coverage.philtrum_target_area_mm2,
        abs=1e-8,
    )
    assert all(
        coverage_by_id[item.triangle_index].region_id == REGION_T_NOSE_PHILTRUM
        for item in philtrum_assignments
    )


def test_nasal_lobe_authority_thickness_is_preserved_but_not_misapplied_to_whole_t_zone():
    authority, _, topology = _build()
    nasal = topology.nasal_lobe_thickness_authority
    nose_zone = topology.zone_by_id[ZONE_T_NOSE_PHILTRUM]
    assert nasal.center_thickness_mm == authority.number(
        "geometry", "nasal_lobe_membrane", "thickness_center_mm"
    )
    assert nasal.doe_mm == tuple(
        float(value) for value in authority.get("geometry", "nasal_lobe_membrane", "thickness_doe_mm")
    )
    assert nasal.application_status == "BOUNDARY_UNRESOLVED_UNTIL_DEDICATED_NASAL_SUBSYSTEM"
    assert nose_zone.nominal_thickness_mm is None
    assert nose_zone.thickness_doe_mm == ()
    assert "DEDICATED_NASAL_SUBSYSTEM_BOUNDARY_REQUIRED" in nose_zone.thickness_status


def test_interface_topology_is_deterministic():
    _, coverage, first = _build()
    _, _, second = _build()
    assert first.topology_sha256 == second.topology_sha256
    assert first.manifest(coverage) == second.manifest(coverage)


def test_contact_zone_cannot_claim_numeric_doe_without_nominal_thickness():
    with pytest.raises(InterfaceTopologyError):
        InterfaceParameterZone(
            zone_id="INVALID",
            functional_role="invalid test zone",
            coverage_region_ids=("ACTIVE",),
            contact_intent=True,
            cleansing_target=True,
            nominal_thickness_mm=None,
            thickness_doe_mm=(0.3,),
            thickness_status="INVALID",
            material_status="UNSELECTED",
            geometry_status="TEST",
            evidence_status="TEST",
        )


def test_iteration_10_cannot_be_promoted_to_anatomical_validation_evidence():
    _, _, topology = _build()
    assert topology.anatomical_validation_eligible is False
    assert "NOT_CONTACT_FIT_MATERIAL_OR_EFFICACY_EVIDENCE" in topology.evidence_status
