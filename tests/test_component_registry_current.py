from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from masck_one.component_registry import (
    AUTHORITY_REVISION,
    HYGIENE_UNRESOLVED,
    IDENTITY_WORLD_TRANSFORM,
    LENGTH_UNIT,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PHYSICAL_MATERIAL,
    ROLE_REALIZED_CENTERLINE,
    ROLE_TOPOLOGY,
    ROLE_UNRESOLVED,
    SOURCE_GIT_BLOBS,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    ComponentRegistryError,
    build_current_component_registry,
)
from masck_one.model import build_model
from masck_one.waste_cartridge_dfm import REQUIREMENT_IDS


class _FakeRealization:
    manifest_sha256 = "a" * 64


class _FakeWasteRelease:
    def __init__(self) -> None:
        self.realization = _FakeRealization()

    def validate_invariants(self) -> None:
        return None


def _build_fast_registry(model):
    import masck_one.component_registry as registry_module

    original_type = registry_module.Cell4WasteBackboneRelease
    registry_module.Cell4WasteBackboneRelease = _FakeWasteRelease
    try:
        return registry_module.build_current_component_registry(
            model=model,
            waste_release=_FakeWasteRelease(),
        )
    finally:
        registry_module.Cell4WasteBackboneRelease = original_type


@pytest.fixture(scope="module")
def current_model():
    return build_model()


@pytest.fixture(scope="module")
def registry(current_model):
    return _build_fast_registry(current_model)


def _by_id(registry):
    return {item.component_id: item for item in registry.components}


def test_registry_is_bound_to_post_121_released_base(registry):
    assert SOURCE_MAIN_SHA == "d02bce5b5cb43e33febd6e1a40fdc98f3893efca"
    assert registry.source_main_sha == SOURCE_MAIN_SHA
    assert registry.coordinate_frame_id == WORLD_FRAME_ID
    assert registry.length_unit == LENGTH_UNIT
    assert registry.physical_validation_eligible is False


def test_registry_reconciles_released_geometry_roles_without_proxy_promotion(registry):
    by_id = _by_id(registry)
    assert registry.physical_material_model_component_names == ("rigid_shell",)
    assert by_id["MASCK_ONE-COMP-RIGID-SHELL"].geometry_role == ROLE_PHYSICAL_MATERIAL

    package = by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"]
    assert package.geometry_role == ROLE_PACKAGE_REFERENCE
    assert package.physical_material_eligible is False
    assert by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY"].geometry_role == ROLE_UNRESOLVED

    routes = by_id["MASCK_ONE-COMP-MIXED-WASTE-ROUTES"]
    assert routes.geometry_role == ROLE_REALIZED_CENTERLINE
    assert routes.supersedes_geometry_role == ROLE_TOPOLOGY
    assert routes.source_path == "src/masck_one/realized_waste_backbone.py"


def test_unresolved_hardware_cannot_gain_material_or_realized_digest(registry):
    by_id = _by_id(registry)
    ids = (
        "MASCK_ONE-COMP-WATER-PUMP",
        "MASCK_ONE-COMP-CLEANSER-PUMP",
        "MASCK_ONE-COMP-WASTE-PUMP",
        "MASCK_ONE-COMP-RETENTION-HALO",
        "MASCK_ONE-COMP-QUICK-RELEASE-RIGHT",
        "MASCK_ONE-COMP-PCB",
        "MASCK_ONE-COMP-HARNESS",
        "MASCK_ONE-COMP-CHARGING-INTERFACE",
        "MASCK_ONE-COMP-DRY-BAY",
        "MASCK_ONE-COMP-WET-DRY-BULKHEAD",
        "MASCK_ONE-COMP-HMI",
        "MASCK_ONE-COMP-WARM",
        "MASCK_ONE-COMP-DRAIN-DRY-PATH",
        "MASCK_ONE-COMP-BATTERY",
        "MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY",
    ) + tuple(f"MASCK_ONE-COMP-ACTUATOR-{i:02d}" for i in range(1, 5)) + tuple(
        f"MASCK_ONE-COMP-ACTUATOR-{i:02d}-COUPLING" for i in range(1, 5)
    )
    for component_id in ids:
        item = by_id[component_id]
        assert item.geometry_role == ROLE_UNRESOLVED
        assert item.source_digest_sha256 is None
        assert item.physical_material_eligible is False
        assert item.physical_validation_eligible is False


def test_actuator_required_identity_is_not_package_reference(registry):
    by_id = _by_id(registry)
    expected_zones = (
        "ACTUATOR_ZONE_SUPERIOR_LEFT",
        "ACTUATOR_ZONE_SUPERIOR_RIGHT",
        "ACTUATOR_ZONE_INFERIOR_LEFT",
        "ACTUATOR_ZONE_INFERIOR_RIGHT",
    )
    actual = tuple(by_id[f"MASCK_ONE-COMP-ACTUATOR-{i:02d}"].source_object_id for i in range(1, 5))
    assert actual == expected_zones
    for i in range(1, 5):
        actual_item = by_id[f"MASCK_ONE-COMP-ACTUATOR-{i:02d}"]
        package_item = by_id[f"MASCK_ONE-COMP-ACTUATOR-{i:02d}-PACKAGE"]
        coupling_item = by_id[f"MASCK_ONE-COMP-ACTUATOR-{i:02d}-COUPLING"]
        assert actual_item.source_path == "src/masck_one/actuator_frames.py"
        assert actual_item.geometry_role == ROLE_UNRESOLVED
        assert package_item.source_path == "src/masck_one/model.py"
        assert package_item.geometry_role == ROLE_PACKAGE_REFERENCE
        assert package_item.world_mount_eligible is False
        assert actual_item.world_mount_eligible is False
        assert coupling_item.source_path == "src/masck_one/actuator_coupling.py"
        assert coupling_item.source_object_id == f"MASCK_ONE-COUPLING-NODE-{i}"
        assert f"MASCK_ONE-ACTUATION-FLEXURE-{i}" in coupling_item.service_state
        assert f"MASCK_ONE-ACTUATION-REACTION-PATH-{i}" in coupling_item.service_state


def test_production_battery_is_separate_from_packaging_benchmark(registry):
    by_id = _by_id(registry)
    package = by_id["MASCK_ONE-COMP-BATTERY-PACKAGE"]
    battery = by_id["MASCK_ONE-COMP-BATTERY"]
    assert package.geometry_role == ROLE_PACKAGE_REFERENCE
    assert package.source_object_id == "battery_reference_envelope"
    assert battery.geometry_role == ROLE_UNRESOLVED
    assert battery.source_object_id == "battery_reference.candidate"
    assert battery.physical_material_eligible is False


def test_released_hygiene_classes_survive_canonical_reconciliation(registry):
    by_id = _by_id(registry)
    assert by_id["MASCK_ONE-COMP-WATER-RESERVOIR"].hygiene_class == "WET_REMOVABLE"
    assert by_id["MASCK_ONE-COMP-CLEANSER-RESERVOIR"].hygiene_class == "WET_REMOVABLE"
    assert by_id["MASCK_ONE-COMP-WASTE-ACQUISITION"].hygiene_class == "WET_DRAINABLE"
    assert by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY"].hygiene_class == HYGIENE_UNRESOLVED
    assert by_id["MASCK_ONE-COMP-DRAIN-DRY-PATH"].hygiene_class == HYGIENE_UNRESOLVED
    for component_id in (
        "MASCK_ONE-COMP-WATER-RESERVOIR",
        "MASCK_ONE-COMP-CLEANSER-RESERVOIR",
        "MASCK_ONE-COMP-WASTE-ACQUISITION",
    ):
        assert "PHYSICAL_HYGIENE" in by_id[component_id].evidence_status


def test_cartridge_dfm_firewall_is_source_bound_and_fail_closed(registry):
    by_id = _by_id(registry)
    gate = by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-DFM-GATE"]
    assert gate.source_path == "src/masck_one/waste_cartridge_dfm.py"
    assert gate.geometry_role == ROLE_UNRESOLVED
    assert gate.physical_material_eligible is False
    assert gate.physical_validation_eligible is False
    assert gate.digital_mvp_ready is False
    assert gate.hygiene_class == HYGIENE_UNRESOLVED
    assert gate.required_p0_ids == tuple(REQUIREMENT_IDS)
    assert len(gate.required_p0_ids) == 7


def test_model_review_geometry_is_explicitly_nonmaterial(registry):
    by_object = {
        item.source_object_id: item
        for item in registry.components
        if item.source_path == "src/masck_one/model.py"
    }
    assert by_object["nasal_lobe_membrane_reference"].physical_material_eligible is False
    assert by_object["water_reservoir_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    assert by_object["waste_cartridge_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    assert by_object["battery_reference_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    for index in range(1, 5):
        item = by_object[f"actuator_envelope_{index}"]
        assert item.geometry_role == ROLE_PACKAGE_REFERENCE
        assert item.physical_material_eligible is False
        assert item.world_mount_eligible is False
    for name in (
        "visual_eye_left",
        "visual_eye_right",
        "visual_mouth",
        "visual_nostril_left",
        "visual_nostril_right",
    ):
        assert by_object[name].physical_material_eligible is False


def test_registry_manifest_is_deterministic_and_source_bound(registry):
    first = registry.manifest()
    second = registry.manifest()
    assert first == second
    assert first["registry_sha256"] == registry.registry_sha256
    assert first["source_git_blobs"] == dict(sorted(SOURCE_GIT_BLOBS.items()))
    assert first["source_main_sha"] == SOURCE_MAIN_SHA
    assert len(first["registry_sha256"]) == 64
    assert first["physical_validation_eligible"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("coordinate_frame_id", "WRONG_FRAME"),
        ("length_unit", "cm"),
        ("world_from_source_transform", (float("nan"),) + IDENTITY_WORLD_TRANSFORM[1:]),
        ("source_blob_sha", "0" * 40),
        ("physical_material_eligible", True),
        ("physical_validation_eligible", True),
    ),
)
def test_reference_record_rejects_frame_unit_nonfinite_stale_source_and_promotion(registry, field, value):
    reference = _by_id(registry)["MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"]
    with pytest.raises(ComponentRegistryError):
        replace(reference, **{field: value})


def test_unresolved_record_rejects_geometry_digest_promotion(registry):
    unresolved = _by_id(registry)["MASCK_ONE-COMP-WASTE-PUMP"]
    with pytest.raises(ComponentRegistryError):
        replace(unresolved, source_digest_sha256="b" * 64)


@pytest.mark.parametrize(
    "source_path",
    (
        "src/masck_one/model.py",
        "src/masck_one/actuator_frames.py",
        "src/masck_one/actuator_coupling.py",
        "src/masck_one/waste_cartridge_dfm.py",
    ),
)
def test_critical_source_movement_invalidates_registry(monkeypatch, current_model, source_path):
    original = SOURCE_GIT_BLOBS[source_path]
    monkeypatch.setitem(SOURCE_GIT_BLOBS, source_path, "0" * 40)
    with pytest.raises(ComponentRegistryError, match="source moved"):
        _build_fast_registry(current_model)
    assert original != "0" * 40


def test_hygiene_retyping_fails_closed(registry):
    by_id = _by_id(registry)
    water = by_id["MASCK_ONE-COMP-WATER-RESERVOIR"]
    bad_water = replace(water, hygiene_class="WET_DRAINABLE")
    bad_components = tuple(bad_water if item.component_id == water.component_id else item for item in registry.components)
    with pytest.raises(ComponentRegistryError, match="hygiene classification moved"):
        replace(registry, components=bad_components)


def test_cartridge_dfm_readiness_spoof_fails_closed(registry):
    by_id = _by_id(registry)
    gate = by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-DFM-GATE"]
    bad_gate = replace(gate, digital_mvp_ready=True)
    bad_components = tuple(bad_gate if item.component_id == gate.component_id else item for item in registry.components)
    with pytest.raises(ComponentRegistryError, match="digitally not-ready"):
        replace(registry, components=bad_components)


def test_cartridge_dfm_requirement_loss_fails_closed(registry):
    by_id = _by_id(registry)
    gate = by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-DFM-GATE"]
    bad_gate = replace(gate, required_p0_ids=gate.required_p0_ids[:-1])
    bad_components = tuple(bad_gate if item.component_id == gate.component_id else item for item in registry.components)
    with pytest.raises(ComponentRegistryError, match="P0 requirement set moved"):
        replace(registry, components=bad_components)


def test_model_identity_or_evidence_role_drift_fails_closed(current_model):
    bad_shell = replace(current_model.shell, status="REFERENCE_ONLY")
    bad_model = replace(current_model, shell=bad_shell)
    with pytest.raises(ComponentRegistryError, match="rigid shell maturity changed"):
        _build_fast_registry(bad_model)


def test_export_uses_registry_as_physical_material_boundary(monkeypatch, tmp_path, current_model, registry):
    import masck_one.export as release_export

    fake_waste_release = _FakeWasteRelease()
    monkeypatch.setattr(
        release_export,
        "build_current_cell4_waste_backbone_release",
        lambda: fake_waste_release,
    )
    monkeypatch.setattr(
        release_export,
        "build_current_component_registry",
        lambda model, waste_release: registry,
    )
    monkeypatch.setattr(release_export.cq.exporters, "export", lambda *args, **kwargs: None)
    monkeypatch.setattr(release_export, "run_assertions", lambda model: ())
    monkeypatch.setattr(release_export, "build_verified_interface_boundary_topology", lambda *args: object())
    monkeypatch.setattr(
        release_export,
        "build_interface_attachment_architecture",
        lambda *args: SimpleNamespace(manifest=lambda: {}),
    )
    monkeypatch.setattr(
        release_export,
        "build_contact_simulation_framework",
        lambda *args: SimpleNamespace(manifest=lambda: {}),
    )
    monkeypatch.setattr(
        release_export,
        "build_structural_frame_topology",
        lambda *args: SimpleNamespace(manifest=lambda: {}),
    )
    monkeypatch.setattr(
        release_export,
        "build_waste_cartridge_dfm_audit",
        lambda **kwargs: SimpleNamespace(manifest=lambda: {}),
    )
    monkeypatch.setattr(release_export, "boundary_release_manifest", lambda *args: {})
    monkeypatch.setattr(release_export, "_realized_waste_backbone_manifest", lambda release=None: {})

    report = release_export.export_release(tmp_path, model=current_model)

    assert report["development_assembly_material_components"] == ["rigid_shell"]
    for name in (
        "waste_cartridge_envelope",
        "battery_reference_envelope",
        "water_reservoir_envelope",
        "actuator_envelope_1",
        "nasal_lobe_membrane_reference",
    ):
        assert name in report["development_assembly_exclusions"]
    assert report["component_registry"]["registry_sha256"] == registry.registry_sha256

    manifest_path = tmp_path / "component_registry.json"
    assert manifest_path.is_file()
    emitted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert emitted == registry.manifest()
