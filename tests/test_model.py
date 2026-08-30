from masck_one.assertions import run_assertions
from masck_one.interface_boundaries import BOUNDARY_IDS
from masck_one.interface_topology import ZONE_T_NOSE_PHILTRUM
from masck_one.model import build_model
from masck_one.nasal_subsystem import (
    ROLE_BRIDGE_DORSUM,
    ROLE_LOBE,
    ROLE_PHILTRUM,
    ROLE_SIDEWALL_LEFT,
    ROLE_SIDEWALL_RIGHT,
)
from masck_one.spatial import Point3, Vector3


CAD_BREP_BOUND_TOLERANCE_MM = 2e-6


def test_model_builds():
    model = build_model()
    assert model.shell.solid.val().Volume() > 0
    assert model.nasal_interface.solid.val().Volume() > 0
    assert len(model.actuator_envelopes) == 4


def test_model_exposes_canonical_global_datums():
    model = build_model()
    frame = model.datums.global_frame
    assert frame.origin == Point3(0.0, 0.0, 0.0)
    assert frame.x_axis == Vector3(1.0, 0.0, 0.0)
    assert frame.y_axis == Vector3(0.0, 1.0, 0.0)
    assert frame.z_axis == Vector3(0.0, 0.0, 1.0)


def test_model_exposes_semantic_facial_reference_without_invented_depth():
    model = build_model()
    reference = model.facial_reference
    assert reference.source_revision == model.authority.get("project", "authority_revision")
    assert len(reference.landmarks) == 5
    assert len(reference.unresolved_3d_landmarks()) == 5
    assert reference.metrics.interpupillary_center_spacing_mm == 63.0
    assert reference.metrics.nostril_center_spacing_mm == 21.0


def test_model_exposes_neutral_surface_without_promoting_it_to_anatomical_evidence():
    model = build_model()
    surface = model.facial_surface
    assert surface.descriptor.kind == "PLANAR_DEVELOPMENT_REFERENCE"
    assert surface.descriptor.anatomical_validation_eligible is False
    assert surface.is_planar is True
    assert surface.mesh.vertex_count > 1000


def test_model_exposes_protected_volumes_without_fake_3d_validation():
    model = build_model()
    protected = model.protected_volumes
    assert len(protected.all) == 5
    assert all(volume.anatomical_validation_eligible is False for volume in protected.all)
    assert all(volume.z_policy == "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE" for volume in protected.all)
    assert "3D_DYNAMIC_GEOMETRY_BLOCKED" in protected.evidence_status


def test_model_exposes_deterministic_worn_pose_screen_without_measured_distribution_claim():
    model = build_model()
    regression = model.worn_pose_regression
    assert regression.pose_count == 459
    assert regression.maximum_sampled_radial_translation_mm == 5.0
    assert regression.maximum_sampled_absolute_rotation_deg == 4.0
    assert regression.poses[regression.identity_pose_index].translation_z_mm == 0.0
    assert regression.evidence_status == "DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION"


def test_model_exposes_coverage_topology_without_promoting_geometric_screen_to_efficacy():
    model = build_model()
    coverage = model.coverage_mesh
    assert len(coverage.triangles) == model.facial_surface.mesh.triangle_count
    assert coverage.aggregate_min_percent == 90.0
    assert coverage.t_zone_min_percent == 90.0
    assert coverage.unexplained_hole_max_mm2 == 100.0
    assert coverage.area_conservation_error_mm2 < 1e-8
    assert coverage.target_area_mm2 > 0.0
    assert coverage.t_zone_target_area_mm2 > 0.0
    assert coverage.philtrum_target_area_mm2 > 0.0
    assert coverage.anatomical_validation_eligible is False

    full_screen = coverage.evaluate(
        (cell.triangle_index for cell in coverage.target_triangles),
        evidence_status="MODEL_REGRESSION_SYNTHETIC_ALL_TARGETS",
        evidence_eligible=True,
    )
    assert full_screen.numeric_gate_passed is True
    assert full_screen.aggregate_percent == 100.0
    assert full_screen.t_zone_percent == 100.0
    assert full_screen.product_validation_status == "NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION"


def test_model_exposes_main_compliant_interface_topology_without_invented_material_truth():
    model = build_model()
    topology = model.compliant_interface_topology
    coverage = model.coverage_mesh
    assert len(topology.assignments) == len(coverage.triangles)
    assert topology.contact_area_mm2 == coverage.target_area_mm2
    assert topology.protected_opening_area_mm2 == coverage.protected_area_mm2
    assert topology.t_zone_contact_area_mm2 == coverage.t_zone_target_area_mm2
    assert topology.contact_component_count(coverage) == 1
    assert topology.anatomical_validation_eligible is False
    assert len(topology.topology_sha256) == 64

    nasal = topology.nasal_lobe_thickness_authority
    nose_zone = topology.zone_by_id[ZONE_T_NOSE_PHILTRUM]
    assert nasal.center_thickness_mm == 0.30
    assert nasal.doe_mm == (0.25, 0.30, 0.35)
    assert nose_zone.nominal_thickness_mm is None
    assert nose_zone.thickness_doe_mm == ()


def test_model_exposes_dedicated_nasal_roles_and_localized_lobe_cad():
    model = build_model()
    nasal = model.nasal_subsystem_topology
    assert set(nasal.role_area_mm2) == {
        ROLE_BRIDGE_DORSUM,
        ROLE_SIDEWALL_LEFT,
        ROLE_SIDEWALL_RIGHT,
        ROLE_LOBE,
        ROLE_PHILTRUM,
    }
    assert all(area > 0.0 for area in nasal.role_area_mm2.values())
    assert nasal.role_by_id[ROLE_LOBE].nominal_thickness_mm == 0.30
    for role_id in (ROLE_BRIDGE_DORSUM, ROLE_SIDEWALL_LEFT, ROLE_SIDEWALL_RIGHT, ROLE_PHILTRUM):
        assert nasal.role_by_id[role_id].nominal_thickness_mm is None
    assert model.nasal_interface.name == "nasal_lobe_membrane_reference"
    assert model.nasal_interface.status == "DEVELOPMENT_LOCAL_THICKNESS_REFERENCE"
    assert abs(model.nasal_interface.solid.val().BoundingBox().zlen - 0.30) <= CAD_BREP_BOUND_TOLERANCE_MM
    assert nasal.anatomical_validation_eligible is False


def test_model_exposes_perimeter_and_aperture_transition_topology_without_invented_seal_dimensions():
    model = build_model()
    boundaries = model.interface_boundary_topology

    assert tuple(boundaries.edges_by_boundary) == BOUNDARY_IDS
    assert all(boundaries.boundary_is_closed_loop(boundary_id) for boundary_id in BOUNDARY_IDS)
    assert all(boundaries.boundary_component_count(boundary_id) == 1 for boundary_id in BOUNDARY_IDS)
    assert all(definition.nominal_transition_width_mm is None for definition in boundaries.definitions)
    assert all(definition.nominal_interface_thickness_mm is None for definition in boundaries.definitions)
    assert boundaries.anatomical_validation_eligible is False
    assert len(boundaries.topology_sha256) == 64


def test_all_software_verifiable_assertions_pass():
    model = build_model()
    checks = run_assertions(model)
    failures = [c for c in checks if c.status == "FAIL"]
    assert failures == []


def test_cleansing_coverage_and_contact_physics_remain_evidence_blocked():
    model = build_model()
    checks = {check.id: check for check in run_assertions(model)}
    assert checks["COVERAGE_MESH_TOPOLOGY"].status == "PASS"
    assert checks["COMPLIANT_INTERFACE_TOPOLOGY"].status == "PASS"
    assert checks["DEDICATED_NASAL_SUBSYSTEM_TOPOLOGY"].status == "PASS"
    assert checks["CLEANSING_COVERAGE"].status == "BLOCKED"
    assert checks["FACIAL_PRESSURE"].status == "BLOCKED"
    assert checks["MEMBRANE_STRAIN"].status == "BLOCKED"
    assert checks["DYNAMIC_AIRWAY_SIGNED_DISTANCE"].status == "BLOCKED"


def test_shell_fits_xy_authority_envelope():
    model = build_model()
    bb = model.shell.solid.val().BoundingBox()
    max_x, max_y = model.authority.pair("geometry", "outer_xy_envelope_mm")
    assert bb.xlen <= max_x + 1e-6
    assert bb.ylen <= max_y + 1e-6


def test_water_reservoir_gross_volume_exact():
    model = build_model()
    volume_ml = model.water_reservoir_envelope.solid.val().Volume() / 1000.0
    assert abs(volume_ml - 6.5) < 1e-9


def test_cartridge_envelope_exact():
    model = build_model()
    bb = model.waste_cartridge_envelope.solid.val().BoundingBox()
    assert abs(bb.xlen - 74.0) < 1e-9
    assert abs(bb.ylen - 36.0) < 1e-9
    assert abs(bb.zlen - 20.0) < 1e-9
