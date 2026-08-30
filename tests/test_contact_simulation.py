from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.contact_simulation import (
    FRICTION_CASES,
    MESH_LEVELS,
    PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX,
    PRELOAD_CASES_N,
    PRESSURE_CONVERGENCE_RELATIVE_MAX,
    ContactSimulationError,
    ContactSimulationResult,
    HyperelasticMaterialCard,
    MaterialParameter,
    build_contact_simulation_framework,
    evaluate_mesh_convergence,
)
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model


def _build():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    framework = build_contact_simulation_framework(model.authority, attachment)
    return model, attachment, framework


def _synthetic_result(
    framework,
    *,
    mesh_level: str,
    bridge: float,
    cheek: float,
    p95_strain: float,
    local_strain: float,
):
    return ContactSimulationResult(
        case_id=framework.cases[0].case_id,
        mesh_level=mesh_level,
        material_card_sha256=framework.material_card.card_sha256,
        bridge_p95_kPa=bridge,
        cheek_p95_kPa=cheek,
        membrane_p95_strain_percent=p95_strain,
        membrane_local_max_strain_percent=local_strain,
        result_provenance="SYNTHETIC_REGRESSION_FIXTURE_ONLY",
        synthetic_regression_fixture=True,
        physical_validation_eligible=False,
    )


def test_contact_case_matrix_is_complete_and_deterministic():
    _, _, first = _build()
    _, _, second = _build()
    expected = tuple((preload, friction) for preload in PRELOAD_CASES_N for friction in FRICTION_CASES)
    actual = tuple((case.preload_N, case.friction_coefficient) for case in first.cases)
    assert actual == expected
    assert len(first.cases) == 12
    assert first.framework_sha256 == second.framework_sha256
    assert first.manifest() == second.manifest()


def test_framework_is_bound_to_iteration13_attachment_revision():
    _, attachment, framework = _build()
    assert framework.source_attachment_topology_sha256 == attachment.topology_sha256
    assert framework.source_registered_mesh_sha256 == attachment.source_registered_mesh_sha256


def test_unresolved_material_card_carries_no_fabricated_constants():
    _, _, framework = _build()
    assert framework.material_card.evidence_eligible is False
    assert framework.material_card.parameters == ()
    assert framework.solver_execution_ready is False
    assert all(case.solver_execution_status == "BLOCKED_MATERIAL_CARD_REQUIRED" for case in framework.cases)


def test_non_evidence_material_card_rejects_numeric_constitutive_parameters():
    parameter = MaterialParameter("C10", 0.1, "MPa", "SYNTHETIC_TEST_ONLY")
    with pytest.raises(ContactSimulationError, match="cannot carry constitutive constants"):
        HyperelasticMaterialCard(
            card_id="SYNTHETIC-NOT-EVIDENCE",
            model_family="YEOH",
            parameters=(parameter,),
            source_type="SYNTHETIC_TEST",
            source_reference=None,
            source_sha256=None,
            status="NOT_EVIDENCE_ELIGIBLE",
            evidence_eligible=False,
        )


def test_evidence_eligible_material_card_requires_source_hash():
    parameter = MaterialParameter("C10", 0.1, "MPa", "SYNTHETIC_TEST_ONLY")
    with pytest.raises(ContactSimulationError, match="requires a source SHA-256"):
        HyperelasticMaterialCard(
            card_id="SYNTHETIC-MISSING-HASH",
            model_family="YEOH",
            parameters=(parameter,),
            source_type="SYNTHETIC_TEST",
            source_reference="synthetic://test",
            source_sha256=None,
            status="TEST_ONLY",
            evidence_eligible=True,
        )


def test_authority_pressure_and_strain_limits_are_carried_without_result_claims():
    model, _, framework = _build()
    assert dict(framework.pressure_limits_kPa) == {
        "bridge_p95_max_kPa": float(model.authority.get("safety", "pressure", "bridge_p95_max_kPa")),
        "bridge_steady_max_kPa": float(model.authority.get("safety", "pressure", "bridge_steady_max_kPa")),
        "cheek_p95_max_kPa": float(model.authority.get("safety", "pressure", "cheek_p95_max_kPa")),
        "dynamic_max_kPa": float(model.authority.get("safety", "pressure", "dynamic_max_kPa")),
    }
    assert dict(framework.membrane_strain_limits_percent) == {
        "p95_max_percent": float(model.authority.get("safety", "membrane_strain", "p95_max_percent")),
        "local_max_percent": float(model.authority.get("safety", "membrane_strain", "local_max_percent")),
    }
    assert framework.physical_validation_eligible is False


def test_mesh_convergence_screen_passes_only_under_both_controlled_criteria():
    _, _, framework = _build()
    coarse = _synthetic_result(
        framework,
        mesh_level=MESH_LEVELS[1],
        bridge=4.10,
        cheek=5.10,
        p95_strain=19.0,
        local_strain=30.6,
    )
    fine = _synthetic_result(
        framework,
        mesh_level=MESH_LEVELS[2],
        bridge=4.00,
        cheek=5.00,
        p95_strain=18.8,
        local_strain=30.0,
    )
    report = evaluate_mesh_convergence(coarse, fine)
    assert report.pressure_p95_relative_change_max < PRESSURE_CONVERGENCE_RELATIVE_MAX
    assert report.peak_strain_relative_change < PEAK_STRAIN_CONVERGENCE_RELATIVE_MAX
    assert report.converged is True
    assert report.physical_validation_eligible is False
    assert "NOT_PHYSICAL_VALIDATION" in report.status


def test_mesh_convergence_screen_fails_when_peak_strain_is_not_converged():
    _, _, framework = _build()
    coarse = _synthetic_result(
        framework,
        mesh_level=MESH_LEVELS[1],
        bridge=4.05,
        cheek=5.05,
        p95_strain=19.0,
        local_strain=32.0,
    )
    fine = _synthetic_result(
        framework,
        mesh_level=MESH_LEVELS[2],
        bridge=4.00,
        cheek=5.00,
        p95_strain=18.9,
        local_strain=30.0,
    )
    report = evaluate_mesh_convergence(coarse, fine)
    assert report.pressure_converged is True
    assert report.peak_strain_converged is False
    assert report.converged is False
    assert "REFINEMENT_REQUIRED" in report.status


def test_convergence_rejects_mismatched_case_identity():
    _, _, framework = _build()
    first = _synthetic_result(
        framework,
        mesh_level=MESH_LEVELS[1],
        bridge=4.0,
        cheek=5.0,
        p95_strain=19.0,
        local_strain=30.0,
    )
    second = replace(
        _synthetic_result(
            framework,
            mesh_level=MESH_LEVELS[2],
            bridge=4.0,
            cheek=5.0,
            p95_strain=19.0,
            local_strain=30.0,
        ),
        case_id=framework.cases[1].case_id,
    )
    with pytest.raises(ContactSimulationError, match="same case"):
        evaluate_mesh_convergence(first, second)


def test_result_cannot_be_promoted_directly_to_physical_validation():
    _, _, framework = _build()
    with pytest.raises(ContactSimulationError, match="cannot be promoted"):
        ContactSimulationResult(
            case_id=framework.cases[0].case_id,
            mesh_level=MESH_LEVELS[0],
            material_card_sha256=framework.material_card.card_sha256,
            bridge_p95_kPa=1.0,
            cheek_p95_kPa=1.0,
            membrane_p95_strain_percent=1.0,
            membrane_local_max_strain_percent=1.0,
            result_provenance="SYNTHETIC_REGRESSION_FIXTURE_ONLY",
            synthetic_regression_fixture=True,
            physical_validation_eligible=True,
        )
