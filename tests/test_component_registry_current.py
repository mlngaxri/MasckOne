from __future__ import annotations

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from masck_one.component_registry import (
    AUTHORITY_REVISION,
    IDENTITY_WORLD_TRANSFORM,
    LENGTH_UNIT,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PHYSICAL_MATERIAL,
    ROLE_REALIZED_CENTERLINE,
    ROLE_TOPOLOGY,
    ROLE_UNRESOLVED,
    SOURCE_GIT_BLOBS,
    WORLD_FRAME_ID,
    ComponentRegistryError,
    build_current_component_registry,
)
from masck_one.model import build_model


class _FakeWasteRelease:
    def manifest(self) -> dict[str, object]:
        return {
            "realization_manifest_sha256": "a" * 64,
            "authority_revision": AUTHORITY_REVISION,
            "release_state": "TEST_FIXTURE_CURRENT_SOURCE_VALIDATION_OWNED_BY_EXISTING_RELEASE_TESTS",
        }


@pytest.fixture(scope="module")
def current_model():
    return build_model()


@pytest.fixture(scope="module")
def registry(current_model):
    return build_current_component_registry(
        model=current_model,
        waste_release=_FakeWasteRelease(),
    )


def test_registry_reconciles_released_geometry_roles_without_proxy_promotion(registry):
    by_id = {item.component_id: item for item in registry.components}

    assert registry.coordinate_frame_id == WORLD_FRAME_ID
    assert registry.length_unit == LENGTH_UNIT
    assert registry.physical_material_model_component_names == ("rigid_shell",)
    assert by_id["MASCK_ONE-COMP-RIGID-SHELL"].geometry_role == ROLE_PHYSICAL_MATERIAL

    assert by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"].geometry_role == ROLE_PACKAGE_REFERENCE
    assert by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"].physical_material_eligible is False
    assert by_id["MASCK_ONE-COMP-WASTE-CARTRIDGE-BODY"].geometry_role == ROLE_UNRESOLVED

    routes = by_id["MASCK_ONE-COMP-MIXED-WASTE-ROUTES"]
    assert routes.geometry_role == ROLE_REALIZED_CENTERLINE
    assert routes.supersedes_geometry_role == ROLE_TOPOLOGY
    assert routes.source_path == "src/masck_one/realized_waste_backbone.py"

    for component_id in (
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
    ):
        assert by_id[component_id].geometry_role == ROLE_UNRESOLVED
        assert by_id[component_id].source_digest_sha256 is None
        assert by_id[component_id].physical_material_eligible is False


def test_model_review_geometry_is_explicitly_nonmaterial(registry):
    by_object = {item.source_object_id: item for item in registry.components if item.source_path == "src/masck_one/model.py"}

    assert by_object["nasal_lobe_membrane_reference"].physical_material_eligible is False
    assert by_object["water_reservoir_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    assert by_object["waste_cartridge_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    assert by_object["battery_reference_envelope"].geometry_role == ROLE_PACKAGE_REFERENCE
    for index in range(1, 5):
        assert by_object[f"actuator_envelope_{index}"].geometry_role == ROLE_PACKAGE_REFERENCE
        assert by_object[f"actuator_envelope_{index}"].physical_material_eligible is False
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
    ),
)
def test_reference_record_rejects_frame_unit_nonfinite_stale_source_and_material_spoof(registry, field, value):
    reference = next(
        item for item in registry.components
        if item.component_id == "MASCK_ONE-COMP-WASTE-CARTRIDGE-PACKAGE"
    )
    with pytest.raises(ComponentRegistryError):
        replace(reference, **{field: value})


def test_unresolved_record_rejects_geometry_digest_promotion(registry):
    unresolved = next(
        item for item in registry.components
        if item.component_id == "MASCK_ONE-COMP-WASTE-PUMP"
    )
    with pytest.raises(ComponentRegistryError):
        replace(unresolved, source_digest_sha256="b" * 64)


def test_source_movement_invalidates_registry(monkeypatch, current_model):
    original = SOURCE_GIT_BLOBS["src/masck_one/model.py"]
    monkeypatch.setitem(SOURCE_GIT_BLOBS, "src/masck_one/model.py", "0" * 40)
    with pytest.raises(ComponentRegistryError, match="source moved"):
        build_current_component_registry(
            model=current_model,
            waste_release=_FakeWasteRelease(),
        )
    assert original != "0" * 40


def test_model_identity_or_evidence_role_drift_fails_closed(current_model):
    bad_shell = replace(current_model.shell, status="REFERENCE_ONLY")
    bad_model = replace(current_model, shell=bad_shell)
    with pytest.raises(ComponentRegistryError, match="rigid shell maturity changed"):
        build_current_component_registry(
            model=bad_model,
            waste_release=_FakeWasteRelease(),
        )


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
    assert "waste_cartridge_envelope" in report["development_assembly_exclusions"]
    assert "battery_reference_envelope" in report["development_assembly_exclusions"]
    assert "water_reservoir_envelope" in report["development_assembly_exclusions"]
    assert "actuator_envelope_1" in report["development_assembly_exclusions"]
    assert report["component_registry"]["registry_sha256"] == registry.registry_sha256

    manifest_path = tmp_path / "component_registry.json"
    assert manifest_path.is_file()
    emitted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert emitted == registry.manifest()
