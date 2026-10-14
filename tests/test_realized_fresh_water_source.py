from dataclasses import replace
import subprocess

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.model import build_model
from masck_one.realized_fresh_water_source import (
    AUTHORED_MAIN_SHA,
    AUTHORITY_BLOB_SHA,
    DONOR_PR75_HEAD,
    DONOR_PR78_HEAD,
    DONOR_REALIZED_WATER_BLOB,
    DONOR_STATUS,
    FILL_BORE_DIAMETER_MM,
    FLUID_IDENTITY,
    PACKAGE_CLEARANCE_RESERVATION_MM,
    PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM,
    PICKUP_CONNECTOR_RESERVATION_LENGTH_MM,
    PICKUP_PASSAGE_DIAMETER_MM,
    VENT_LUMEN_DIAMETER_MM,
    WATER_ARCHITECTURE_BLOB_SHA,
    build_realized_fresh_water_source,
)
from masck_one.water_reservoir import PORT_FILL, PORT_PICKUP, PORT_VENT, WaterReservoirError


def _datum(source, datum_id):
    return next(item for item in source.datums if item.datum_id == datum_id)


def _protected_prism(zone, z_min, z_max):
    work = (
        cq.Workplane("XY")
        .workplane(offset=z_min)
        .center(zone.center.x, zone.center.y)
    )
    if zone.shape == "CIRCLE":
        work = work.circle(zone.envelope_width_mm / 2.0)
    else:
        work = work.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0)
    solid = work.extrude(z_max - z_min)
    if zone.angle_deg:
        solid = solid.rotate(
            (zone.center.x, zone.center.y, z_min),
            (zone.center.x, zone.center.y, z_max),
            zone.angle_deg,
        )
    return solid


def test_current_main_source_geometry_preserves_fresh_water_identity_and_datums():
    source = build_realized_fresh_water_source(load_authority())

    assert source.fluid_identity == FLUID_IDENTITY == "FRESH_WATER"
    assert _datum(source, PORT_FILL).point.as_tuple() == (-6.0, 76.0, 13.0)
    assert _datum(source, PORT_FILL).axis.as_tuple() == (0.0, 0.0, 1.0)
    assert _datum(source, PORT_VENT).point.as_tuple() == (6.0, 76.0, 13.0)
    assert _datum(source, PORT_PICKUP).point.as_tuple() == (0.0, 62.5, 3.0)
    assert _datum(source, PORT_PICKUP).axis.as_tuple() == (0.0, -1.0, 0.0)
    assert all(item.fluid_identity == "FRESH_WATER" for item in source.datums)


def test_geometric_volume_and_reference_material_partition_are_explicit():
    source = build_realized_fresh_water_source(load_authority())

    assert source.gross_geometric_volume_mL == pytest.approx(6.5, abs=1e-9)
    assert source.neutral_geometric_dead_volume_mL == pytest.approx(0.65, abs=1e-9)
    assert source.neutral_geometric_usable_volume_mL == pytest.approx(5.85, abs=1e-9)
    assert len(source.physical_material_solids) == 2
    assert len(source.reference_only_solids) == 9
    assert source.body_solid.val().intersect(source.lid_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)
    assert source.fill_bore_reference_solid.val().intersect(source.lid_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)
    assert source.pickup_passage_reference_solid.val().intersect(source.body_solid.val()).Volume() == pytest.approx(0.0, abs=1e-7)


def test_current_main_rigid_packages_and_protected_hard_envelopes_are_clear():
    model = build_model()
    source = build_realized_fresh_water_source(model.authority)
    sweep = source.service_sweep_reservation_solid.val()

    assert sweep.distance(model.shell.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM
    for actuator in model.actuator_envelopes:
        assert sweep.distance(actuator.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM
    assert sweep.distance(model.waste_cartridge_envelope.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM
    assert sweep.distance(model.battery_reference_envelope.solid.val()) >= PACKAGE_CLEARANCE_RESERVATION_MM

    bb = sweep.BoundingBox()
    z_min = float(bb.zmin) - 1.0
    z_max = float(bb.zmax) + 1.0
    for protected in model.protected_volumes.all:
        prism = _protected_prism(protected.zone, z_min, z_max)
        assert sweep.intersect(prism.val()).Volume() == pytest.approx(0.0, abs=1e-7)


def test_port_reservations_retain_provisional_dimensions_without_supplier_claims():
    source = build_realized_fresh_water_source(load_authority())

    fill_bb = source.fill_bore_reference_solid.val().BoundingBox()
    pickup_bb = source.pickup_connector_reservation_solid.val().BoundingBox()
    assert fill_bb.xlen == pytest.approx(FILL_BORE_DIAMETER_MM, abs=2e-6)
    assert fill_bb.ylen == pytest.approx(FILL_BORE_DIAMETER_MM, abs=2e-6)
    assert VENT_LUMEN_DIAMETER_MM == 1.2
    assert PICKUP_PASSAGE_DIAMETER_MM == 2.0
    assert pickup_bb.xlen == pytest.approx(PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert pickup_bb.ylen == pytest.approx(PICKUP_CONNECTOR_RESERVATION_LENGTH_MM, abs=2e-6)
    assert pickup_bb.zlen == pytest.approx(PICKUP_CONNECTOR_RESERVATION_DIAMETER_MM, abs=2e-6)
    assert source.physical_validation_eligible is False


def test_manifest_binds_current_main_and_labels_abandoned_heads_as_donors_only():
    first = build_realized_fresh_water_source(load_authority())
    second = build_realized_fresh_water_source(load_authority())
    manifest = first.manifest()

    assert manifest["authored_main_sha"] == AUTHORED_MAIN_SHA
    assert manifest["source_git_blobs"] == {
        "authority": AUTHORITY_BLOB_SHA,
        "water_reservoir_architecture": WATER_ARCHITECTURE_BLOB_SHA,
    }
    assert manifest["historical_donor_provenance"] == {
        "status": DONOR_STATUS,
        "pr75_head": DONOR_PR75_HEAD,
        "pr78_head": DONOR_PR78_HEAD,
        "realized_water_blob": DONOR_REALIZED_WATER_BLOB,
    }
    assert first.manifest_sha256 == second.manifest_sha256


def test_git_source_blob_provenance_is_exact():
    authority_blob = subprocess.check_output(
        ["git", "hash-object", "config/masck_one_authority.yaml"],
        text=True,
    ).strip()
    water_blob = subprocess.check_output(
        ["git", "hash-object", "src/masck_one/water_reservoir.py"],
        text=True,
    ).strip()
    assert authority_blob == AUTHORITY_BLOB_SHA
    assert water_blob == WATER_ARCHITECTURE_BLOB_SHA


def test_stale_sources_identity_drift_and_evidence_promotion_fail_closed():
    authority = load_authority()
    source = build_realized_fresh_water_source(authority)

    with pytest.raises(WaterReservoirError, match="cannot change FRESH_WATER"):
        replace(source, fluid_identity="CLEANSER")
    with pytest.raises(WaterReservoirError, match="cannot become physical validation evidence"):
        replace(source, physical_validation_eligible=True)
    with pytest.raises(WaterReservoirError, match="stale for current water architecture"):
        replace(source, source_architecture_sha256="0" * 64).validate_current_sources(authority)
    with pytest.raises(WaterReservoirError, match="cannot change fluid identity"):
        replace(source.datums[2], fluid_identity="CLEANSER")


def test_material_steps_round_trip_as_two_separate_valid_solids(tmp_path):
    source = build_realized_fresh_water_source(load_authority())

    for name, solid in (("body", source.body_solid), ("lid", source.lid_solid)):
        path = tmp_path / f"fresh_water_{name}.step"
        cq.exporters.export(solid, str(path))
        imported = cq.importers.importStep(str(path))
        assert imported.solids().size() == 1
        assert imported.val().isValid()
        source_bb = solid.val().BoundingBox()
        imported_bb = imported.val().BoundingBox()
        assert imported_bb.xlen == pytest.approx(source_bb.xlen, abs=1e-4)
        assert imported_bb.ylen == pytest.approx(source_bb.ylen, abs=1e-4)
        assert imported_bb.zlen == pytest.approx(source_bb.zlen, abs=1e-4)
