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


def test_candidate_rebind_updates_observation_without_promoting_release_maturity():
    audit = dfm.build_waste_cartridge_dfm_audit()
    manifest = audit.manifest()
    states = {item["requirement_id"]: item["current_state"] for item in manifest["requirements"]}

    assert "source-bound body" in states[dfm.REQ_BODY_CAVITY_WALLS]
    assert "protected" in states[dfm.REQ_BODY_CAVITY_WALLS].lower()
    assert "27.401629 mL" in states[dfm.REQ_GEOMETRIC_CAPACITY]
    assert "short of the requirement" in states[dfm.REQ_GEOMETRIC_CAPACITY]
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
