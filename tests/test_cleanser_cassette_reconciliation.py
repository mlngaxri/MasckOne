from dataclasses import replace
from hashlib import sha1
import math
from pathlib import Path

import cadquery as cq
import pytest

from masck_one.authority import load_authority
from masck_one.cleanser_cassette_reconciliation import (
    KEY_UNLOCK_ROTATION_DEG,
    PACKAGE_CLEARANCE_RESERVATION_MM,
    PHYSICAL_SOLID_IDS,
    REFERENCE_SOLID_IDS,
    RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
    SERVICE_SEQUENCE_IDS,
    SOURCE_HEAD_SHA,
    SOURCE_STORAGE_BLOB_SHA,
    UPSTREAM_MODULE_X_BOUNDS_MM,
    UPSTREAM_MODULE_Y_BOUNDS_MM,
    UPSTREAM_MODULE_Z_BOUNDS_MM,
    CleanserCassetteReconciliationError,
    CleanserServiceStep,
    build_reconciled_cleanser_cassette,
)
from masck_one.model import build_model
import masck_one.realized_cleanser_storage as realized_cleanser_storage


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def _distance(a: cq.Workplane, b: cq.Workplane) -> float:
    return float(a.val().distance(b.val()))


def _bounds(shape: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = shape.val().BoundingBox()
    return (
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    )


def _xy_rect_distance(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax0, ax1, ay0, ay1 = a
    bx0, bx1, by0, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def _shape_xy(shape: cq.Workplane) -> tuple[float, float, float, float]:
    bb = shape.val().BoundingBox()
    return float(bb.xmin), float(bb.xmax), float(bb.ymin), float(bb.ymax)


def _protected_xy_rectangles(authority) -> tuple[tuple[float, float, float, float], ...]:
    eye_w, eye_h = (float(value) for value in authority.get("geometry", "eye", "visual_aperture_wh_mm"))
    eye_clear = float(authority.get("geometry", "eye", "rigid_dynamic_keepout_clearance_mm"))
    eye_rects = []
    for center in authority.get("geometry", "eye", "centers_mm").values():
        x, y = (float(value) for value in center)
        eye_rects.append(
            (
                x - eye_w / 2.0 - eye_clear,
                x + eye_w / 2.0 + eye_clear,
                y - eye_h / 2.0 - eye_clear,
                y + eye_h / 2.0 + eye_clear,
            )
        )

    mouth_x, mouth_y = (
        float(value) for value in authority.get("geometry", "mouth", "center_mm")
    )
    mouth_w, mouth_h = (
        float(value) for value in authority.get("geometry", "mouth", "visual_aperture_wh_mm")
    )
    mouth_clear = float(
        authority.get("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")
    )
    mouth = (
        mouth_x - mouth_w / 2.0 - mouth_clear,
        mouth_x + mouth_w / 2.0 + mouth_clear,
        mouth_y - mouth_h / 2.0 - mouth_clear,
        mouth_y + mouth_h / 2.0 + mouth_clear,
    )

    nostril_clear = float(
        authority.get("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm")
    )
    nostril_opening = float(
        authority.get("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    )
    nostril_rects = []
    for center in authority.get("geometry", "nostrils", "centers_mm").values():
        x, y = (float(value) for value in center)
        half = nostril_opening / 2.0 + nostril_clear
        nostril_rects.append((x - half, x + half, y - half, y + half))
    return tuple(eye_rects) + (mouth,) + tuple(nostril_rects)


def test_exact_cell4_donor_blob_is_vendored_and_source_bound():
    source_path = Path(realized_cleanser_storage.__file__).resolve()
    assert _git_blob_sha(source_path) == SOURCE_STORAGE_BLOB_SHA
    assert SOURCE_HEAD_SHA == "6e3e05812406620072b37f54827b8345ed55ccea"

    authority = load_authority()
    reconciled = build_reconciled_cleanser_cassette(authority)
    assert reconciled.source_storage.manifest_sha256 == reconciled.source_storage_manifest_sha256
    assert reconciled.validate_current_sources(authority).manifest_sha256 == reconciled.source_storage_manifest_sha256


def test_reconciliation_consumes_body_cavity_and_service_sweep_without_retyping_geometry():
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    source = reconciled.source_storage

    assert _bounds(reconciled.body_solid) == pytest.approx(_bounds(source.body_solid), abs=1e-9)
    assert reconciled.body_solid.val().Volume() == pytest.approx(source.body_solid.val().Volume(), abs=1e-8)
    assert _bounds(reconciled.cavity_reference_solid) == pytest.approx(
        _bounds(source.internal_cavity_solid), abs=1e-9
    )
    assert reconciled.geometric_cavity_volume_mL == pytest.approx(3.072, abs=1e-9)
    assert _bounds(reconciled.cassette_withdrawal_sweep_reference_solid) == pytest.approx(
        _bounds(source.cassette_service_sweep_solid), abs=1e-9
    )


def test_positive_bayonet_retention_has_continuous_unlock_and_withdraw_sequence():
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    manifest = reconciled.manifest()

    assert manifest["retention"]["positive_load_path"] == (
        "LOCKED_TAB_TO_CRADLE_WALL_GEOMETRIC_BLOCK_NOT_FRICTION"
    )
    assert manifest["retention"]["unlock_rotation_deg"] == KEY_UNLOCK_ROTATION_DEG
    assert tuple(step.step_id for step in reconciled.service_sequence) == SERVICE_SEQUENCE_IDS
    assert reconciled.service_sequence[0].motion_kind == "ROTATION"
    assert reconciled.service_sequence[0].rotation_axis_world == (1.0, 0.0, 0.0)
    assert reconciled.service_sequence[1].translation_world_mm == (
        RETENTION_KEY_WITHDRAWAL_TRAVEL_MM,
        0.0,
        0.0,
    )
    assert reconciled.service_sequence[2].translation_world_mm[2] < 0.0
    assert reconciled.key_unlock_rotation_sweep_reference_solid.val().Volume() > 0.0
    assert reconciled.key_withdrawal_sweep_reference_solid.val().Volume() > 0.0


def test_tolerance_stack_closes_running_fit_and_locked_blocking():
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    assert reconciled.cassette_min_side_clearance_mm == pytest.approx(0.4, abs=1e-12)
    assert reconciled.key_min_diametral_clearance_mm == pytest.approx(0.3, abs=1e-12)
    assert reconciled.unlocked_slot_min_clearance_yz_mm == pytest.approx((0.3, 0.3), abs=1e-12)
    assert reconciled.locked_tab_min_block_overhang_each_side_mm == pytest.approx(0.85, abs=1e-12)
    assert "NOT_PROCESS_CAPABILITY" in reconciled.manifest()["tolerance_stack"]["status"]


def test_physical_and_reference_geometry_roles_are_disjoint_and_join_remains_honest():
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    manifest = reconciled.manifest()
    assert set(PHYSICAL_SOLID_IDS).isdisjoint(REFERENCE_SOLID_IDS)
    assert manifest["geometry_roles"]["physical_material"] == list(PHYSICAL_SOLID_IDS)
    assert manifest["geometry_roles"]["reference_only"] == list(REFERENCE_SOLID_IDS)
    assert "UNRESOLVED" in manifest["cradle_to_frame_attachment"]
    assert "BLOCKED" in manifest["development_assembly_material_inclusion"]


def test_upstream_complete_module_service_envelope_is_exact_reference_only_guard():
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    bounds = _bounds(reconciled.upstream_complete_module_service_envelope_reference_solid)
    assert bounds == pytest.approx(
        (
            UPSTREAM_MODULE_X_BOUNDS_MM[0],
            UPSTREAM_MODULE_X_BOUNDS_MM[1],
            UPSTREAM_MODULE_Y_BOUNDS_MM[0],
            UPSTREAM_MODULE_Y_BOUNDS_MM[1],
            UPSTREAM_MODULE_Z_BOUNDS_MM[0],
            UPSTREAM_MODULE_Z_BOUNDS_MM[1],
        ),
        abs=1e-9,
    )
    assert "REFERENCE_ONLY" in reconciled.manifest()["service"]["upstream_complete_module_sweep_role"]


def test_current_released_packages_clear_material_and_service_sweeps():
    model = build_model()
    reconciled = build_reconciled_cleanser_cassette(model.authority)
    current_packages = (
        model.shell.solid,
        *(actuator.solid for actuator in model.actuator_envelopes),
        model.water_reservoir_envelope.solid,
        model.waste_cartridge_envelope.solid,
        model.battery_reference_envelope.solid,
    )
    screening_solids = (
        reconciled.body_solid,
        reconciled.cradle_solid,
        reconciled.retention_key_locked_solid,
        reconciled.key_unlock_rotation_sweep_reference_solid,
        reconciled.key_withdrawal_sweep_reference_solid,
        reconciled.cassette_withdrawal_sweep_reference_solid,
        reconciled.upstream_complete_module_service_envelope_reference_solid,
    )
    for cleanser_shape in screening_solids:
        for package in current_packages:
            assert _distance(cleanser_shape, package) >= PACKAGE_CLEARANCE_RESERVATION_MM


def test_authority_eye_mouth_nostril_and_airway_projections_remain_excluded():
    authority = load_authority()
    reconciled = build_reconciled_cleanser_cassette(authority)
    protected = _protected_xy_rectangles(authority)
    screening_solids = (
        reconciled.body_solid,
        reconciled.cradle_solid,
        reconciled.retention_key_locked_solid,
        reconciled.key_unlock_rotation_sweep_reference_solid,
        reconciled.key_withdrawal_sweep_reference_solid,
        reconciled.cassette_withdrawal_sweep_reference_solid,
        reconciled.upstream_complete_module_service_envelope_reference_solid,
    )
    for shape in screening_solids:
        shape_xy = _shape_xy(shape)
        for protected_xy in protected:
            assert _xy_rect_distance(shape_xy, protected_xy) > 0.0


def test_step_round_trip_preserves_physical_and_service_review_geometry(tmp_path):
    reconciled = build_reconciled_cleanser_cassette(load_authority())
    for name, shape in (
        ("body", reconciled.body_solid),
        ("cradle", reconciled.cradle_solid),
        ("key", reconciled.retention_key_locked_solid),
        ("key_sweep", reconciled.key_withdrawal_sweep_reference_solid),
    ):
        path = tmp_path / f"cleanser_{name}.step"
        cq.exporters.export(shape, str(path))
        loaded = cq.importers.importStep(str(path))
        assert path.exists() and path.stat().st_size > 0
        assert loaded.solids().size() == 1
        assert loaded.val().isValid()
        assert loaded.val().Volume() == pytest.approx(shape.val().Volume(), rel=2e-6, abs=2e-5)
        assert _bounds(loaded) == pytest.approx(_bounds(shape), abs=2e-6)


def test_hostile_identity_source_status_and_nonfinite_motion_fail_closed():
    authority = load_authority()
    reconciled = build_reconciled_cleanser_cassette(authority)

    with pytest.raises(CleanserCassetteReconciliationError, match="exact CLEANSER"):
        replace(reconciled, fluid_identity="FRESH_WATER")
    with pytest.raises(CleanserCassetteReconciliationError, match="cannot become physical validation"):
        replace(reconciled, physical_validation_eligible=True)
    with pytest.raises(CleanserCassetteReconciliationError, match="source storage manifest drifted"):
        replace(reconciled, source_storage_manifest_sha256="0" * 64)
    with pytest.raises(CleanserCassetteReconciliationError, match="finite numeric"):
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[1],
            "cleanser_retention_key",
            "TRANSLATION",
            (math.nan, 0.0, 0.0),
            None,
            None,
            "HOSTILE",
        )
    with pytest.raises(CleanserCassetteReconciliationError, match="remain about \+X"):
        CleanserServiceStep(
            SERVICE_SEQUENCE_IDS[0],
            "cleanser_retention_key",
            "ROTATION",
            (0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            KEY_UNLOCK_ROTATION_DEG,
            "HOSTILE",
        )
