from dataclasses import replace
import math

import pytest

from masck_one.export import export_release
from masck_one.model import build_model
from masck_one.waste_cartridge import KEYING_STATUS, SEALING_STATUS, SERVICE_STATUS
from masck_one.waste_cartridge_dfm import (
    CAPACITY_STATUS,
    CURRENT_HYGIENE_CLASSIFICATION,
    EVIDENCE_STATUS,
    MODEL_ENVELOPE_STATUS,
    REQUIREMENT_IDS,
    SCHEMA,
    SOURCE_MAIN_SHA,
    WasteCartridgeDfmError,
    WasteCartridgeDfmRequirement,
    build_waste_cartridge_dfm_audit,
)


@pytest.fixture(scope="module")
def audit():
    return build_waste_cartridge_dfm_audit()


def test_audit_binds_exact_released_architecture_and_package_arithmetic(audit):
    assert audit.schema == SCHEMA
    assert audit.source_main_sha == SOURCE_MAIN_SHA
    assert audit.model_envelope_status == MODEL_ENVELOPE_STATUS
    assert audit.external_envelope_mm == (74.0, 36.0, 20.0)
    assert audit.external_bounding_volume_mL == pytest.approx(53.28, abs=1e-12)
    assert audit.retained_capacity_requirement_mL == 35.0
    assert audit.retained_requirement_to_external_bound_ratio == pytest.approx(35.0 / 53.28, abs=1e-15)
    assert audit.service_cycles_baseline == 6
    assert audit.usable_internal_capacity_mL is None
    assert audit.current_keying_status == KEYING_STATUS
    assert audit.current_sealing_status == SEALING_STATUS
    assert audit.current_service_status == SERVICE_STATUS
    assert audit.current_capacity_status == CAPACITY_STATUS
    assert audit.current_hygiene_classification == CURRENT_HYGIENE_CLASSIFICATION
    assert audit.development_assembly_material_eligible is False
    assert audit.digital_mvp_cartridge_dfm_ready is False
    assert audit.physical_validation_eligible is False
    assert audit.evidence_status == EVIDENCE_STATUS


def test_all_material_digital_freeze_blockers_are_controlled_and_unique(audit):
    assert tuple(req.requirement_id for req in audit.requirements) == REQUIREMENT_IDS
    assert len(audit.requirements) == 7
    assert len(set(REQUIREMENT_IDS)) == len(REQUIREMENT_IDS)
    assert {req.severity for req in audit.requirements} == {"P0"}
    assert all(req.evidence_status == "DIGITAL_DFM_REQUIREMENT_ONLY" for req in audit.requirements)
    assert audit.manifest()["release_blocker_count"] == 7


def test_released_package_envelope_is_not_promoted_to_cartridge_material_or_capacity(audit):
    manifest = audit.manifest()
    assert manifest["current_released_geometry_role"] == "EXTERNAL_PACKAGE_ENVELOPE_ONLY_NOT_CARTRIDGE_MATERIAL"
    assert manifest["external_bounding_volume_semantics"] == "PACKAGE_UPPER_BOUND_ONLY_NOT_INTERNAL_OR_USABLE_CAPACITY"
    assert manifest["usable_internal_capacity_mL"] is None
    assert manifest["development_assembly_material_eligible"] is False


def test_stale_source_architecture_and_maturity_promotions_fail_closed(audit):
    with pytest.raises(WasteCartridgeDfmError, match="stale for released main"):
        replace(audit, source_main_sha="0" * 40)
    with pytest.raises(WasteCartridgeDfmError, match="canonical SHA-256"):
        replace(audit, cartridge_architecture_sha256="0" * 40)
    with pytest.raises(WasteCartridgeDfmError, match="model cartridge maturity changed"):
        replace(audit, model_envelope_status="REALIZED_SOLID")
    with pytest.raises(WasteCartridgeDfmError, match="keying maturity changed"):
        replace(audit, current_keying_status="REALIZED")
    with pytest.raises(WasteCartridgeDfmError, match="sealing maturity changed"):
        replace(audit, current_sealing_status="REALIZED")
    with pytest.raises(WasteCartridgeDfmError, match="service maturity changed"):
        replace(audit, current_service_status="REALIZED")
    with pytest.raises(WasteCartridgeDfmError, match="capacity maturity changed"):
        replace(audit, current_capacity_status="REALIZED")


def test_hygiene_capacity_and_evidence_cannot_be_invented(audit):
    with pytest.raises(WasteCartridgeDfmError, match="usable internal"):
        replace(audit, usable_internal_capacity_mL=35.0)
    with pytest.raises(WasteCartridgeDfmError, match="hygiene class must remain unresolved"):
        replace(audit, current_hygiene_classification="WET_REMOVABLE")
    with pytest.raises(WasteCartridgeDfmError, match="cannot be physical development-assembly material"):
        replace(audit, development_assembly_material_eligible=True)
    with pytest.raises(WasteCartridgeDfmError, match="not digitally DFM-ready"):
        replace(audit, digital_mvp_cartridge_dfm_ready=True)
    with pytest.raises(WasteCartridgeDfmError, match="cannot become physical validation"):
        replace(audit, physical_validation_eligible=True)
    with pytest.raises(WasteCartridgeDfmError, match="evidence boundary changed"):
        replace(audit, evidence_status="PHYSICAL_VALIDATION")


def test_bool_coercion_and_nonfinite_manufacturing_or_capacity_numbers_fail_closed(audit):
    for field in (
        "development_assembly_material_eligible",
        "digital_mvp_cartridge_dfm_ready",
        "physical_validation_eligible",
    ):
        with pytest.raises(WasteCartridgeDfmError, match="exact bool"):
            replace(audit, **{field: 0})
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(WasteCartridgeDfmError):
            replace(audit, external_bounding_volume_mL=value)
        with pytest.raises(WasteCartridgeDfmError):
            replace(audit, retained_capacity_requirement_mL=value)
        with pytest.raises(WasteCartridgeDfmError):
            replace(audit, retained_requirement_to_external_bound_ratio=value)
        with pytest.raises(WasteCartridgeDfmError):
            replace(audit, mold_draft_nominal_deg=value)
        with pytest.raises(WasteCartridgeDfmError):
            replace(audit, rib_thickness_ratio_range=(0.4, value))
    with pytest.raises(WasteCartridgeDfmError, match="reversed"):
        replace(audit, rib_thickness_ratio_range=(0.6, 0.4))


def test_requirement_reordering_duplication_and_spoofing_fail_closed(audit):
    reordered = (audit.requirements[1], audit.requirements[0], *audit.requirements[2:])
    with pytest.raises(WasteCartridgeDfmError, match="identity or order changed"):
        replace(audit, requirements=reordered)
    duplicated = (audit.requirements[0], audit.requirements[0], *audit.requirements[2:])
    with pytest.raises(WasteCartridgeDfmError):
        replace(audit, requirements=duplicated)
    with pytest.raises(WasteCartridgeDfmError, match="must remain P0"):
        WasteCartridgeDfmRequirement(
            REQUIREMENT_IDS[0],
            "P1",
            "CELL4_WASTE_CARTRIDGE_GEOMETRY",
            "state",
            "closure",
        )
    with pytest.raises(WasteCartridgeDfmError, match="cannot imply physical validation"):
        replace(audit.requirements[0], evidence_status="PHYSICALLY_VERIFIED")


def test_nested_mutation_is_revalidated_and_manifest_is_deterministic(audit):
    second = build_waste_cartridge_dfm_audit()
    assert second.manifest() == audit.manifest()
    assert second.manifest_sha256 == audit.manifest_sha256
    assert len(audit.manifest_sha256) == 64

    object.__setattr__(second.requirements[0], "severity", "P1")
    with pytest.raises(WasteCartridgeDfmError, match="must remain P0"):
        second.validate_current_sources()


def test_actual_model_package_brep_remains_source_bound(audit):
    model = build_model()
    cartridge = audit.validate_current_sources(model=model)
    assert cartridge.architecture_sha256 == audit.cartridge_architecture_sha256
    assert model.waste_cartridge_envelope.name == "waste_cartridge_envelope"
    assert float(model.waste_cartridge_envelope.solid.val().Volume()) / 1000.0 == pytest.approx(53.28, abs=1e-9)


def test_release_export_emits_dfm_gate_and_excludes_proxy_from_physical_assembly(tmp_path):
    report = export_release(tmp_path)
    gate = report["dfm_gates"]["waste_cartridge"]
    assert gate["manifest_sha256"] == build_waste_cartridge_dfm_audit().manifest_sha256
    assert gate["development_assembly_material_eligible"] is False
    assert "waste_cartridge_envelope" in report["development_assembly_exclusions"]
    assert "waste_cartridge_envelope.step" in report["exported_step_files"]
    assert (tmp_path / "waste_cartridge_envelope.step").is_file()
    assert (tmp_path / "masck_one_development_assembly.step").is_file()
