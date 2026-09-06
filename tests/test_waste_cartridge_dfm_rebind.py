import pytest

import masck_one.waste_cartridge_dfm as dfm
from masck_one.realized_waste_cartridge import HYGIENE_CLASSIFICATION


def test_dfm_rebind_preserves_released_audit_and_pins_candidate_sources():
    assert dfm.SOURCE_MAIN_SHA == "afe29ff78419b6625dca5594974b6351f6f80e1b"
    identities = dict(dfm.SOURCE_GIT_BLOB_IDENTITIES)
    assert identities["src/masck_one/waste_cartridge_dfm_legacy.py"] == dfm.LEGACY_AUDIT_BLOB_SHA
    assert identities["src/masck_one/realized_waste_cartridge.py"] == dfm.REALIZED_WASTE_CARTRIDGE_BLOB_SHA
    assert "src/masck_one/realized_waste_cartridge.py" not in dfm.EXPECTED_ABSENT_REALIZATION_PATHS
    assert "src/masck_one/waste_cartridge_geometry.py" in dfm.EXPECTED_ABSENT_REALIZATION_PATHS
    assert "src/masck_one/waste_cartridge_service.py" in dfm.EXPECTED_ABSENT_REALIZATION_PATHS


def test_capacity_feasibility_distinguishes_package_from_current_wall_topology():
    metrics = dfm.capacity_feasibility_metrics()

    assert metrics["package_external_volume_mL"] == pytest.approx(53.28, abs=1e-9)
    assert metrics["protected_mouth_excluded_package_volume_mL"] == pytest.approx(
        13.069331350564386,
        abs=1e-9,
    )
    assert metrics["protected_compliant_package_geometric_upper_bound_mL"] == pytest.approx(
        40.21066864943561,
        abs=1e-9,
    )
    assert metrics["protected_compliant_package_margin_to_retained_requirement_mL"] == pytest.approx(
        5.210668649435611,
        abs=1e-9,
    )
    assert metrics["current_wall_seed_zero_floor_lid_geometric_upper_bound_mL"] == pytest.approx(
        34.8879317091326,
        abs=1e-9,
    )
    assert metrics["current_wall_seed_zero_floor_lid_margin_to_retained_requirement_mL"] == pytest.approx(
        -0.11206829086740089,
        abs=1e-9,
    )
    assert metrics["retained_capacity_requirement_mL"] == 35.0
    assert metrics["package_geometry_can_theoretically_fit_requirement"] is True
    assert metrics["current_wall_seed_can_fit_requirement_even_with_zero_floor_lid"] is False
    assert "NOT_USABLE_RETAINED_LIQUID" in metrics["evidence_status"]


def test_candidate_rebind_updates_observation_without_promoting_release_maturity():
    audit = dfm.build_waste_cartridge_dfm_audit()
    manifest = audit.manifest()
    states = {item["requirement_id"]: item["current_state"] for item in manifest["requirements"]}

    assert "source-bound body" in states[dfm.REQ_BODY_CAVITY_WALLS]
    assert "protected" in states[dfm.REQ_BODY_CAVITY_WALLS].lower()
    assert "27.401629 mL" in states[dfm.REQ_GEOMETRIC_CAPACITY]
    assert "40.210669 mL geometric ceiling" in states[dfm.REQ_GEOMETRIC_CAPACITY]
    assert "34.887932 mL" in states[dfm.REQ_GEOMETRIC_CAPACITY]
    assert "current wall topology therefore cannot close capacity" in states[dfm.REQ_GEOMETRIC_CAPACITY]
    assert "body inlet bore" in states[dfm.REQ_INLET_SEAL_CLOSURE]
    assert "asymmetric key rib" in states[dfm.REQ_KEYING_RETENTION]
    assert "service reservation" in states[dfm.REQ_SERVICE_PATH]
    assert HYGIENE_CLASSIFICATION in states[dfm.REQ_REMOVED_STATE]

    assert audit.current_hygiene_classification == "UNRESOLVED"
    assert audit.development_assembly_material_eligible is False
    assert audit.digital_mvp_cartridge_dfm_ready is False
    assert audit.physical_validation_eligible is False
    assert manifest["release_blocker_count"] == 7


def test_candidate_source_tamper_still_fails_closed(monkeypatch):
    monkeypatch.setattr(
        dfm._legacy,
        "SOURCE_GIT_BLOB_IDENTITIES",
        (("src/masck_one/realized_waste_cartridge.py", "0" * 40),),
    )
    with pytest.raises(dfm.WasteCartridgeDfmError, match="source moved"):
        dfm.build_waste_cartridge_dfm_audit()
