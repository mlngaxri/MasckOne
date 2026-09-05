from dataclasses import replace

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_service_envelope import (
    CleanserServiceEnvelopeError,
    build_complete_cleanser_module_service_envelope,
)
from masck_one.cleanser_service_interfaces import build_cleanser_service_geometry
from masck_one.model import build_model
from masck_one.realized_cleanser_storage import (
    CASSETTE_WITHDRAWAL_TRAVEL_MM,
    PACKAGE_CLEARANCE_RESERVATION_MM,
)


def _outside_volume(shape, envelope) -> float:
    return float(shape.val().cut(envelope.val()).Volume())


def _distance(a, b) -> float:
    return float(a.val().distance(b.val()))


def test_complete_module_service_envelope_binds_exact_successor_geometry_and_full_travel():
    authority = load_authority()
    service = build_cleanser_service_geometry(authority)
    envelope = build_complete_cleanser_module_service_envelope(authority)

    assert envelope.source_service_manifest_sha256 == service.manifest_sha256
    assert envelope.validate_current_sources(authority).manifest_sha256 == service.manifest_sha256
    assert envelope.withdrawal_travel_mm == CASSETTE_WITHDRAWAL_TRAVEL_MM
    assert envelope.physical_validation_eligible is False
    assert envelope.module_removal_sweep_solid.solids().size() == 1
    assert envelope.module_removal_sweep_solid.val().isValid()

    for shape in (
        service.ported_body_solid,
        service.service_closure_solid,
        service.service_retention_key_solid,
    ):
        assert _outside_volume(shape, envelope.module_removal_sweep_solid) <= 1e-7
        translated = shape.translate((0.0, 0.0, -CASSETTE_WITHDRAWAL_TRAVEL_MM))
        assert _outside_volume(translated, envelope.module_removal_sweep_solid) <= 1e-7


def test_complete_module_removal_envelope_clears_released_package_geometry():
    authority = load_authority()
    model = build_model(authority)
    envelope = build_complete_cleanser_module_service_envelope(authority)
    sweep = envelope.module_removal_sweep_solid

    for package in (
        model.shell.solid,
        *(actuator.solid for actuator in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    ):
        assert _distance(sweep, package) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_complete_module_service_envelope_round_trips_through_step(tmp_path):
    envelope = build_complete_cleanser_module_service_envelope(load_authority())
    source = envelope.module_removal_sweep_solid
    path = tmp_path / "cleanser_complete_module_removal_sweep.step"
    cq.exporters.export(source, str(path))

    assert path.exists() and path.stat().st_size > 0
    reloaded = cq.importers.importStep(str(path))
    assert reloaded.solids().size() == 1
    assert reloaded.val().isValid()
    assert reloaded.val().Volume() == pytest.approx(source.val().Volume(), rel=2e-6, abs=2e-5)
    source_bb = source.val().BoundingBox()
    loaded_bb = reloaded.val().BoundingBox()
    assert loaded_bb.xmin == pytest.approx(source_bb.xmin, abs=2e-6)
    assert loaded_bb.xmax == pytest.approx(source_bb.xmax, abs=2e-6)
    assert loaded_bb.ymin == pytest.approx(source_bb.ymin, abs=2e-6)
    assert loaded_bb.ymax == pytest.approx(source_bb.ymax, abs=2e-6)
    assert loaded_bb.zmin == pytest.approx(source_bb.zmin, abs=2e-6)
    assert loaded_bb.zmax == pytest.approx(source_bb.zmax, abs=2e-6)


def test_complete_module_service_manifest_is_explicitly_conservative_and_not_physical_evidence():
    envelope = build_complete_cleanser_module_service_envelope(load_authority())
    manifest = envelope.manifest()

    assert manifest["moving_package"] == "CLEANSER_SUCCESSOR_BODY_PLUS_REFILL_PURGE_CLOSURE_PLUS_CLOSURE_KEY"
    assert manifest["withdrawal_translation_world_mm"] == [0.0, 0.0, -CASSETTE_WITHDRAWAL_TRAVEL_MM]
    assert manifest["precondition"] == "BASE_CASSETTE_RETENTION_KEY_RETRACTED_MASK_UNPOWERED"
    assert "CONSERVATIVE" in manifest["sweep_construction"]
    assert manifest["physical_validation_eligible"] is False
    assert manifest["manifest_sha256"] == envelope.manifest_sha256


def test_complete_module_service_envelope_rejects_stale_source_and_evidence_promotion():
    authority = load_authority()
    envelope = build_complete_cleanser_module_service_envelope(authority)

    with pytest.raises(CleanserServiceEnvelopeError, match="stale for service geometry"):
        replace(envelope, source_service_manifest_sha256="0" * 64).validate_current_sources(authority)
    with pytest.raises(CleanserServiceEnvelopeError, match="cannot become physical validation"):
        replace(envelope, physical_validation_eligible=True)
