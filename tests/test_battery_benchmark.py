from __future__ import annotations

from dataclasses import replace
import math

import pytest

import masck_one.battery_benchmark as bb
import masck_one.dry_side_package as dsp
from masck_one.authority import load_authority
from masck_one.model import build_model


@pytest.fixture(scope="module")
def current_context():
    authority = load_authority()
    model = build_model(authority)
    binding = bb.build_battery_benchmark_binding(authority, model)
    package = dsp.build_dry_side_package(authority, model)
    return authority, model, binding, package


def _dry_side_battery(package):
    matches = tuple(item for item in package.reference_geometry if item.geometry_id == "BATTERY_PACKAGING_BENCHMARK")
    assert len(matches) == 1
    return matches[0]


def test_benchmark_consumes_exact_live_authority_values(current_context) -> None:
    authority, _model, binding, _package = current_context
    assert binding.candidate == authority.get("battery_reference", "candidate") == "EEMB LP603450HA"
    assert binding.envelope_mm == tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
    assert binding.nominal_voltage_V == authority.number("battery_reference", "nominal_voltage_V")
    assert binding.capacity_mAh == authority.number("battery_reference", "capacity_mAh")
    assert binding.mass_g == authority.number("battery_reference", "mass_g")
    assert binding.status == authority.get("battery_reference", "status") == bb.PACKAGING_ONLY_STATUS


def test_binding_pins_authority_schema_validator_and_model_sources(current_context) -> None:
    _authority, _model, binding, _package = current_context
    sources = binding.manifest()["sources"]
    assert sources == {
        "main_sha": bb.SOURCE_MAIN_SHA,
        "authority_path": bb.AUTHORITY_PATH,
        "authority_git_blob_sha": bb.AUTHORITY_BLOB_SHA,
        "authority_field_path": "battery_reference",
        "authority_schema_path": bb.AUTHORITY_SCHEMA_PATH,
        "authority_schema_git_blob_sha": bb.AUTHORITY_SCHEMA_BLOB_SHA,
        "authority_validator_path": bb.AUTHORITY_VALIDATOR_PATH,
        "authority_validator_git_blob_sha": bb.AUTHORITY_VALIDATOR_BLOB_SHA,
        "model_path": bb.MODEL_PATH,
        "model_git_blob_sha": bb.MODEL_BLOB_SHA,
    }


def test_released_model_brep_is_exactly_bound_to_authority_envelope(current_context) -> None:
    authority, model, binding, _package = current_context
    expected = tuple(float(value) for value in authority.get("battery_reference", "envelope_mm"))
    actual = binding.model_component_spans_mm
    assert model.battery_reference_envelope.status == bb.PACKAGING_ONLY_STATUS
    for expected_value, actual_value in zip(expected, actual, strict=True):
        assert actual_value == pytest.approx(expected_value, abs=5e-6)
    manifest = binding.manifest()
    assert manifest["model_binding"]["matches_authority_envelope"] is True
    assert manifest["model_binding"]["component_id"] == "battery_reference_envelope"


def test_supplier_provenance_stays_candidate_only_without_invented_document(current_context) -> None:
    _authority, _model, binding, _package = current_context
    provenance = binding.manifest()["supplier_provenance"]
    assert provenance["candidate"] == "EEMB LP603450HA"
    assert provenance["candidate_identity_source"] == "MACHINE_AUTHORITY_BATTERY_REFERENCE_CANDIDATE"
    assert provenance["status"] == bb.SUPPLIER_PROVENANCE_STATUS
    assert provenance["supplier_document_url"] is None
    assert provenance["supplier_document_sha256"] is None
    assert provenance["supplier_document_bound"] is False


def test_packaging_only_evidence_firewall_cannot_promote(current_context) -> None:
    _authority, _model, binding, _package = current_context
    firewall = binding.manifest()["evidence_firewall"]
    assert firewall == {
        "packaging_only": True,
        "production_selected": False,
        "supplier_qualified": False,
        "physical_validation_complete": False,
        "runtime_validated": False,
        "electrical_safety_validated": False,
        "swelling_abuse_clearance_validated": False,
    }
    with pytest.raises(bb.BatteryBenchmarkError, match="status drifted"):
        replace(binding, status="PRODUCTION_FREEZE")
    with pytest.raises(bb.BatteryBenchmarkError, match="cannot be promoted"):
        replace(binding, production_selected=True)
    with pytest.raises(bb.BatteryBenchmarkError, match="cannot be promoted"):
        replace(binding, supplier_document_bound=True)
    with pytest.raises(bb.BatteryBenchmarkError, match="cannot be promoted"):
        replace(binding, physical_validation_complete=True)


def test_dry_side_package_consumes_same_benchmark_without_reference_material_promotion(current_context) -> None:
    authority, _model, binding, package = current_context
    battery = _dry_side_battery(package)
    spans = dsp._geometry(battery.solid)["spans_mm"]
    expected = list(float(value) for value in authority.get("battery_reference", "envelope_mm"))
    assert spans == pytest.approx(expected, abs=5e-6)
    assert battery.geometry_status == binding.status
    assert battery.material_class == "REFERENCE_ONLY"
    assert package.battery_nominal_voltage_V == binding.nominal_voltage_V
    assert package.battery_capacity_mAh == binding.capacity_mAh
    assert package.battery_mass_g == binding.mass_g
    assert package.manifest()["integration"]["development_assembly_status"].startswith("REVIEW_ONLY")


def test_binding_is_deterministic_and_source_movement_fails_closed(monkeypatch, current_context) -> None:
    _authority, _model, binding, _package = current_context
    assert binding.binding_sha256 == bb.build_battery_benchmark_binding().binding_sha256

    authority_blob = bb.AUTHORITY_BLOB_SHA
    monkeypatch.setattr(bb, "AUTHORITY_BLOB_SHA", "0" * 40)
    with pytest.raises(bb.BatteryBenchmarkError, match="source moved"):
        bb._require_sources()
    monkeypatch.setattr(bb, "AUTHORITY_BLOB_SHA", authority_blob)

    schema_blob = bb.AUTHORITY_SCHEMA_BLOB_SHA
    monkeypatch.setattr(bb, "AUTHORITY_SCHEMA_BLOB_SHA", "0" * 40)
    with pytest.raises(bb.BatteryBenchmarkError, match="source moved"):
        bb._require_sources()
    monkeypatch.setattr(bb, "AUTHORITY_SCHEMA_BLOB_SHA", schema_blob)


def test_malformed_or_nonfinite_benchmark_values_fail_closed(current_context) -> None:
    _authority, _model, binding, _package = current_context
    with pytest.raises(bb.BatteryBenchmarkError, match="finite"):
        replace(binding, mass_g=float("nan"))
    with pytest.raises(bb.BatteryBenchmarkError, match="positive"):
        replace(binding, capacity_mAh=0.0)
    with pytest.raises(bb.BatteryBenchmarkError, match="geometry differs"):
        replace(binding, model_component_spans_mm=(binding.envelope_mm[0] + 1.0, *binding.envelope_mm[1:]))
    assert all(math.isfinite(value) for value in binding.envelope_mm)
