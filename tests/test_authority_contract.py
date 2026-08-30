from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from masck_one.authority import (
    load_authority,
    validate_authority_data,
    validate_authority_path,
)


def _valid_data() -> dict:
    return deepcopy(load_authority().data)


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_current_authority_passes_schema_and_semantics():
    authority = load_authority()
    assert authority.validation_report.valid is True
    assert authority.validation_report.issues == ()
    assert authority.get("project", "schema_version") == "1.0.0"


def test_schema_rejects_unknown_status():
    data = _valid_data()
    data["geometry"]["eye"]["center_status"] = "MADE_UP_STATUS"
    report = validate_authority_data(data)
    assert report.valid is False
    assert "SCHEMA_ENUM" in _codes(report)


def test_schema_rejects_unregistered_unit_symbol():
    data = _valid_data()
    data["project"]["units"]["length"] = "cm"
    report = validate_authority_data(data)
    assert report.valid is False
    assert "SCHEMA_CONST" in _codes(report)


def test_schema_rejects_uncontrolled_additional_property():
    data = _valid_data()
    data["mass"]["mystery_allowance_g"] = 7.0
    report = validate_authority_data(data)
    assert report.valid is False
    assert "SCHEMA_ADDITIONALPROPERTIES" in _codes(report)


def test_semantics_reject_duplicate_airway_area_drift():
    data = _valid_data()
    data["safety"]["airway"]["minimum_area_each_mm2"] = 121.0
    report = validate_authority_data(data)
    assert report.valid is False
    assert "AIRWAY_AREA_DUPLICATION_MISMATCH" in _codes(report)


def test_semantics_reject_duplicate_airway_dimension_drift():
    data = _valid_data()
    data["safety"]["airway"]["minimum_local_dimension_mm"] = 8.1
    report = validate_authority_data(data)
    assert report.valid is False
    assert "AIRWAY_DIMENSION_DUPLICATION_MISMATCH" in _codes(report)


def test_semantics_reject_clean_cycle_ledger_drift():
    data = _valid_data()
    data["fluid"]["clean_cycle"]["nominal_introduced_liquid_mL"] = 4.7
    report = validate_authority_data(data)
    assert report.valid is False
    assert "CLEAN_CYCLE_LEDGER_MISMATCH" in _codes(report)


def test_semantics_reject_under_capacity_cartridge_ledger():
    data = _valid_data()
    data["fluid"]["cartridge"]["retained_capacity_min_mL"] = 34.99
    report = validate_authority_data(data)
    assert report.valid is False
    assert "CARTRIDGE_CAPACITY_LEDGER_MARGIN" in _codes(report)


def test_semantics_reject_functional_frame_outside_outer_envelope():
    data = _valid_data()
    data["geometry"]["functional_frame_xy_mm"] = [173.0, 202.0]
    report = validate_authority_data(data)
    assert report.valid is False
    assert "FRAME_EXCEEDS_OUTER_ENVELOPE" in _codes(report)


def test_semantics_reject_baseline_missing_from_actuator_doe():
    data = _valid_data()
    data["actuation"]["clean"]["axis_angle_doe_deg"] = [50.0, 55.0, 67.0, 72.0]
    report = validate_authority_data(data)
    assert report.valid is False
    assert "ACTUATOR_ANGLE_CENTER_NOT_IN_DOE" in _codes(report)


def test_semantics_reject_protected_classification_drift():
    data = _valid_data()
    data["actuation"]["architecture_status"] = "ENGINEERING_BASELINE"
    report = validate_authority_data(data)
    assert report.valid is False
    assert "AUTHORITY_CLASSIFICATION_DRIFT" in _codes(report)


def test_semantics_reject_paid_preorder_without_private_gate():
    data = _valid_data()
    data["commercial"]["initial_state"] = "PAID_PREORDER"
    data["commercial"]["paid_preorder_gate"] = False
    report = validate_authority_data(data)
    assert report.valid is False
    assert "COMMERCIAL_STATE_GATE_CONTRADICTION" in _codes(report)


def test_duplicate_yaml_key_is_rejected_before_schema_validation(tmp_path: Path):
    source = Path("config/masck_one_authority.yaml").read_text(encoding="utf-8")
    source = source.replace(
        "  name: Masck One\n",
        "  name: Masck One\n  name: Masck One\n",
        1,
    )
    candidate = tmp_path / "duplicate.yaml"
    candidate.write_text(source, encoding="utf-8")

    report = validate_authority_path(candidate)
    assert report.valid is False
    assert "AUTHORITY_PARSE_OR_SCHEMA_ERROR" in _codes(report)
    assert "Duplicate YAML key" in report.issues[0].message


def test_yaml_round_trip_does_not_change_current_authority_meaning(tmp_path: Path):
    authority = load_authority()
    candidate = tmp_path / "roundtrip.yaml"
    candidate.write_text(
        yaml.safe_dump(authority.data, sort_keys=False),
        encoding="utf-8",
    )
    report = validate_authority_path(candidate)
    assert report.valid is True
    assert report.issues == ()
