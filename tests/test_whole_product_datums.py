from __future__ import annotations

from dataclasses import replace
import math

import pytest

import masck_one.whole_product_datums as datum_module
from masck_one.spatial import RigidTransform, Vector3
from masck_one.whole_product_datums import (
    ACTUATOR_FRAME_IDS,
    AUTHORITY_REVISION,
    BATTERY_PACKAGE_FRAME_ID,
    CLEANSER_ROOT_FRAME_ID,
    DRY_SIDE_ROOT_FRAME_ID,
    EVIDENCE_STATUS,
    HMI_ROOT_FRAME_ID,
    LEGACY_GLOBAL_FRAME_ID,
    RETENTION_ROOT_FRAME_ID,
    SHELL_PRIMARY_FRAME_ID,
    SOURCE_MAIN_SHA,
    STRUCTURAL_FRAME_REFERENCE_ID,
    STRUCTURAL_FRAME_DATUM_IDS,
    THERMAL_ROOT_FRAME_ID,
    WATER_RESERVOIR_PACKAGE_FRAME_ID,
    WATER_RESERVOIR_ROOT_FRAME_ID,
    WASTE_CARTRIDGE_PACKAGE_FRAME_ID,
    WASTE_CARTRIDGE_ROOT_FRAME_ID,
    WORLD_FRAME_ID,
    DatumHierarchyError,
    WholeProductDatumHierarchy,
    build_whole_product_datum_hierarchy,
)


@pytest.fixture(scope="module")
def hierarchy() -> WholeProductDatumHierarchy:
    return build_whole_product_datum_hierarchy()


def _translation(hierarchy: WholeProductDatumHierarchy, datum_id: str) -> tuple[float, float, float]:
    transform = hierarchy.local_to_world_transform(datum_id)
    assert transform is not None
    return transform.translation.as_tuple()


def test_world_shell_and_structural_references_are_explicit_and_canonical(hierarchy):
    nodes = hierarchy.node_by_id

    assert hierarchy.source_main_sha == SOURCE_MAIN_SHA
    assert hierarchy.authority_revision == AUTHORITY_REVISION
    assert hierarchy.axis_positive == ("wearer_right", "superior", "anterior")
    assert hierarchy.world_origin_xyz_mm == (0.0, 0.0, 0.0)

    assert nodes[WORLD_FRAME_ID].parent_id is None
    assert nodes[WORLD_FRAME_ID].transform_status == "ROOT"

    for datum_id in (LEGACY_GLOBAL_FRAME_ID, SHELL_PRIMARY_FRAME_ID, STRUCTURAL_FRAME_REFERENCE_ID):
        node = nodes[datum_id]
        assert node.parent_id == WORLD_FRAME_ID
        assert node.transform_status == "RESOLVED_IDENTITY"
        transform = hierarchy.local_to_world_transform(datum_id)
        assert transform == RigidTransform.identity()

    assert (
        nodes[SHELL_PRIMARY_FRAME_ID].manufacturing_status
        == "DIGITAL_PRIMARY_REFERENCE_NOT_QUALIFIED_MANUFACTURING_DATUM"
    )
    assert (
        nodes[STRUCTURAL_FRAME_REFERENCE_ID].manufacturing_status
        == "UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM"
    )


def test_released_structural_xy_datums_preserve_known_xy_and_unresolved_z(hierarchy):
    nodes = hierarchy.node_by_id
    expected = {
        "MASCK_ONE-FRAME-DATUM-CENTER": (0.0, 0.0, None),
        "MASCK_ONE-FRAME-DATUM-SUPERIOR": (0.0, 101.0, None),
        "MASCK_ONE-FRAME-DATUM-INFERIOR": (0.0, -101.0, None),
        "MASCK_ONE-FRAME-DATUM-WEARER_LEFT": (-77.5, 0.0, None),
        "MASCK_ONE-FRAME-DATUM-WEARER_RIGHT": (77.5, 0.0, None),
    }
    assert set(STRUCTURAL_FRAME_DATUM_IDS) == set(expected)
    for datum_id, partial in expected.items():
        node = nodes[datum_id]
        assert node.parent_id == STRUCTURAL_FRAME_REFERENCE_ID
        assert node.transform_status == "UNRESOLVED"
        assert node.local_to_parent is None
        assert node.partial_translation_mm == partial
        assert node.geometry_role == "STRUCTURAL_REFERENCE_WITH_UNRESOLVED_3D_DATUM_QUALIFICATION"
        assert "z_status=UNRESOLVED_UNTIL_STRUCTURAL_3D_SURFACE_AND_PACKAGING_CLOSURE" in node.blocker
        assert hierarchy.local_to_world_transform(datum_id) is None


def test_released_package_reference_frames_bind_actual_brep_centres_without_material_promotion(hierarchy):
    nodes = hierarchy.node_by_id

    assert _translation(hierarchy, WATER_RESERVOIR_PACKAGE_FRAME_ID) == pytest.approx((0.0, 76.0, 7.0), abs=1e-9)
    assert _translation(hierarchy, WASTE_CARTRIDGE_PACKAGE_FRAME_ID) == pytest.approx((0.0, -80.0, 8.0), abs=1e-9)
    assert _translation(hierarchy, BATTERY_PACKAGE_FRAME_ID) == pytest.approx((0.0, 0.0, -15.0), abs=1e-9)

    for datum_id in (
        WATER_RESERVOIR_PACKAGE_FRAME_ID,
        WASTE_CARTRIDGE_PACKAGE_FRAME_ID,
        BATTERY_PACKAGE_FRAME_ID,
    ):
        node = nodes[datum_id]
        assert node.datum_class == "PACKAGE_REFERENCE"
        assert node.geometry_role == "PACKAGE_REFERENCE_ONLY"
        assert node.manufacturing_status == "REFERENCE_ONLY_NOT_MANUFACTURING_DATUM"
        assert node.transform_status == "RESOLVED_RIGID"


def test_actuator_local_datums_do_not_inherit_proxy_envelope_placements(hierarchy):
    nodes = hierarchy.node_by_id

    for datum_id in ACTUATOR_FRAME_IDS:
        node = nodes[datum_id]
        assert node.parent_id == STRUCTURAL_FRAME_REFERENCE_ID
        assert node.transform_status == "UNRESOLVED"
        assert node.local_to_parent is None
        assert node.geometry_role == "NO_RELEASED_PLACEMENT_GEOMETRY"
        assert hierarchy.local_to_world_transform(datum_id) is None
        assert "model.py actuator cylinders are package/development proxies only" in node.blocker


def test_released_fluid_and_unreleased_neighboring_subsystem_roots_fail_closed(hierarchy):
    nodes = hierarchy.node_by_id

    for datum_id in (
        WATER_RESERVOIR_ROOT_FRAME_ID,
        WASTE_CARTRIDGE_ROOT_FRAME_ID,
        CLEANSER_ROOT_FRAME_ID,
        RETENTION_ROOT_FRAME_ID,
        DRY_SIDE_ROOT_FRAME_ID,
        HMI_ROOT_FRAME_ID,
        THERMAL_ROOT_FRAME_ID,
    ):
        node = nodes[datum_id]
        assert node.transform_status == "UNRESOLVED"
        assert node.local_to_parent is None
        assert node.manufacturing_status == "UNRESOLVED_NOT_QUALIFIED_MANUFACTURING_DATUM"
        assert node.geometry_role == "NO_RELEASED_PLACEMENT_GEOMETRY"
        assert hierarchy.local_to_world_transform(datum_id) is None

    assert nodes[WATER_RESERVOIR_ROOT_FRAME_ID].producer_path == "src/masck_one/water_reservoir.py"
    assert nodes[WASTE_CARTRIDGE_ROOT_FRAME_ID].producer_path == "src/masck_one/waste_cartridge.py"
    assert nodes[CLEANSER_ROOT_FRAME_ID].producer_path == "src/masck_one/cleanser_storage.py"
    assert nodes[HMI_ROOT_FRAME_ID].parent_id == DRY_SIDE_ROOT_FRAME_ID
    assert nodes[THERMAL_ROOT_FRAME_ID].parent_id == DRY_SIDE_ROOT_FRAME_ID


def test_manifest_is_deterministic_source_bound_and_keeps_physical_firewall(hierarchy):
    first = hierarchy.manifest()
    second = hierarchy.manifest()

    assert first == second
    assert first["hierarchy_sha256"] == hierarchy.hierarchy_sha256
    assert first["source_main_sha"] == SOURCE_MAIN_SHA
    assert first["authority_world_frame_id"] == WORLD_FRAME_ID
    assert first["length_unit"] == "mm"
    assert first["physical_validation_eligible"] is False
    assert first["evidence_status"] == EVIDENCE_STATUS

    source_paths = [item["path"] for item in first["source_git_blobs"]]
    assert len(source_paths) == len(set(source_paths))
    assert "config/masck_one_authority.yaml" in source_paths
    assert "src/masck_one/model.py" in source_paths
    assert "src/masck_one/water_reservoir.py" in source_paths
    assert "src/masck_one/cleanser_storage.py" in source_paths
    assert "src/masck_one/waste_cartridge.py" in source_paths


def test_duplicate_ids_and_cycles_are_rejected(hierarchy):
    with pytest.raises(DatumHierarchyError, match="unique"):
        WholeProductDatumHierarchy(
            source_main_sha=hierarchy.source_main_sha,
            authority_revision=hierarchy.authority_revision,
            world_origin_xyz_mm=hierarchy.world_origin_xyz_mm,
            axis_positive=hierarchy.axis_positive,
            nodes=hierarchy.nodes + (hierarchy.nodes[-1],),
        )

    nodes = list(hierarchy.nodes)
    shell_index = next(i for i, node in enumerate(nodes) if node.datum_id == SHELL_PRIMARY_FRAME_ID)
    structural_index = next(i for i, node in enumerate(nodes) if node.datum_id == STRUCTURAL_FRAME_REFERENCE_ID)
    nodes[shell_index] = replace(nodes[shell_index], parent_id=STRUCTURAL_FRAME_REFERENCE_ID)
    nodes[structural_index] = replace(nodes[structural_index], parent_id=SHELL_PRIMARY_FRAME_ID)
    with pytest.raises(DatumHierarchyError, match="cycle"):
        WholeProductDatumHierarchy(
            source_main_sha=hierarchy.source_main_sha,
            authority_revision=hierarchy.authority_revision,
            world_origin_xyz_mm=hierarchy.world_origin_xyz_mm,
            axis_positive=hierarchy.axis_positive,
            nodes=tuple(nodes),
        )


def test_hostile_reference_promotion_and_numeric_unresolved_transform_are_rejected(hierarchy):
    package = hierarchy.node_by_id[WATER_RESERVOIR_PACKAGE_FRAME_ID]
    with pytest.raises(DatumHierarchyError, match="package reference"):
        replace(
            package,
            manufacturing_status="DIGITAL_PRIMARY_REFERENCE_NOT_QUALIFIED_MANUFACTURING_DATUM",
        )

    actuator = hierarchy.node_by_id[ACTUATOR_FRAME_IDS[0]]
    with pytest.raises(DatumHierarchyError, match="unresolved datum"):
        replace(actuator, local_to_parent=RigidTransform.identity())

    shell = hierarchy.node_by_id[SHELL_PRIMARY_FRAME_ID]
    with pytest.raises(DatumHierarchyError, match="only valid for unresolved"):
        replace(shell, partial_translation_mm=(0.0, 0.0, None))

    frame_datum = hierarchy.node_by_id[STRUCTURAL_FRAME_DATUM_IDS[0]]
    with pytest.raises(DatumHierarchyError, match="both known and unresolved"):
        replace(frame_datum, partial_translation_mm=(0.0, 0.0, 0.0))
    with pytest.raises(DatumHierarchyError, match="finite"):
        replace(frame_datum, partial_translation_mm=(0.0, math.inf, None))


def test_wrong_world_sign_origin_and_nonfinite_values_are_rejected(hierarchy):
    with pytest.raises(DatumHierarchyError, match="axis/sign"):
        replace(hierarchy, axis_positive=("wearer_left", "superior", "anterior"))
    with pytest.raises(DatumHierarchyError, match="exact zero"):
        replace(hierarchy, world_origin_xyz_mm=(1.0, 0.0, 0.0))
    with pytest.raises(DatumHierarchyError, match="finite"):
        replace(hierarchy, world_origin_xyz_mm=(math.nan, 0.0, 0.0))


def test_unknown_datum_lookup_fails_closed(hierarchy):
    with pytest.raises(DatumHierarchyError, match="unknown datum"):
        hierarchy.local_to_world_transform("MASCK_ONE_LOCAL_DOES_NOT_EXIST")


def test_source_blob_movement_invalidates_hierarchy(monkeypatch):
    monkeypatch.setattr(datum_module, "_git_blob_sha", lambda path: "0" * 40)
    with pytest.raises(DatumHierarchyError, match="source moved"):
        build_whole_product_datum_hierarchy()


def test_resolved_rigid_transform_must_not_be_hidden_identity(hierarchy):
    package = hierarchy.node_by_id[WATER_RESERVOIR_PACKAGE_FRAME_ID]
    with pytest.raises(DatumHierarchyError, match="non-identity"):
        replace(package, local_to_parent=RigidTransform.from_translation(Vector3(0.0, 0.0, 0.0)))
