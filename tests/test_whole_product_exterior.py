from __future__ import annotations

import math

import pytest

from masck_one.whole_product_exterior import (
    AUTHORITY_REVISION,
    HMI_BARREL_OD_MM,
    HMI_BORE_DIAMETER_MM,
    OWNER_HEADS,
    SCHEMA,
    SOURCE_MAIN_SHA,
    WholeProductExterior,
    build_whole_product_exterior,
    require_sources,
)


@pytest.fixture(scope="module")
def exterior() -> WholeProductExterior:
    return build_whole_product_exterior()


def test_whole_product_exterior_sources_are_exact_and_owner_snapshot_is_explicit() -> None:
    require_sources()
    assert SOURCE_MAIN_SHA == "ac59fcd59f50b019cb972bfc526c2daea784bd17"
    assert AUTHORITY_REVISION == "2026-08-30-R1"
    assert OWNER_HEADS == {
        "exterior_pr70": "152312fe6eced419eef4e1e58c33df09fd0710ea",
        "frame_pr117": "fe8e73a2002632633ad1978ca22245eb401d864d",
        "treatment_pr135": "b3a224770f724fbc625534ea563fa09c1b910729",
        "cartridge_pr140": "40b9c12238d208fd631a8c52f6a4f9008a38b31d",
        "retention_pr141": "13dff9efb2bebf099a6cbb054d72620b9e0b0672",
        "dry_side_pr142": "6ee47ecba639a9ce09c3cd076bbfe0408c2d089f",
        "thermal_pr143": "d2b82e50d5bfbadb4a60588a9119139b4742031a",
        "hmi_pr144": "9fb64aa4753dad03a455aad4802910d8814ef5ce",
    }


def test_front_shell_is_one_real_surface_with_real_bside_interfaces(exterior: WholeProductExterior) -> None:
    manifest = exterior.manifest()
    assert manifest["schema"] == SCHEMA
    shell = manifest["manufacturing_components"]["EXTERIOR_FRONT_SHELL"]
    assert shell["role"] == "INTEGRATION_OWNED_CANDIDATE_MATERIAL"
    assert shell["valid"] is True
    assert shell["solid_count"] == 1
    assert shell["volume_mm3"] > 0.0
    assert manifest["surface_language"]["eye_treatment"] == "NEUTRAL_HARD_OPENING_WITH_3MM_INNER_ROLL_NO_BEZEL"
    assert manifest["b_side_and_tooling"]["realized_bside_features"] == [
        "FOUR_FRAME_MORTISES",
        "FOUR_TRANSVERSE_PIN_BORES",
        "HMI_12MM_OD_REACTION_LAND",
        "HMI_8P5MM_THROUGH_BORE",
    ]


def test_hmi_is_bside_only_and_current_owner_functional_rejection_is_not_hidden(exterior: WholeProductExterior) -> None:
    manifest = exterior.manifest()
    measurements = manifest["measurements"]
    assert HMI_BARREL_OD_MM == 12.0
    assert HMI_BORE_DIAMETER_MM == 8.5
    assert measurements["hmi_visible_anterior_growth_mm"] <= 1e-6
    assert manifest["reference_and_owner_geometry"]["hmi_cap"]["visible_bezel_added"] is False
    assert manifest["reference_and_owner_geometry"]["hmi_cap"]["role"].startswith("APPEARANCE_REFERENCE_ONLY")
    assert "HMI_V11_CURRENT_OWNER_SERIES_FORCE_PATH_REJECTED_EXTERIOR_INTERFACE_ONLY" in manifest["blockers"]


def test_integration_owned_material_never_blocks_eye_mouth_or_airway(exterior: WholeProductExterior) -> None:
    intersections = exterior.measurements["physical_exterior_protected_intersections_mm3"]
    assert intersections
    assert all(math.isfinite(float(value)) and float(value) <= 1e-7 for value in intersections.values())


def test_cartridge_closure_is_the_service_reveal_not_a_second_decorative_door(exterior: WholeProductExterior) -> None:
    manifest = exterior.manifest()
    cartridge = manifest["manufacturing_components"]["WASTE_CARTRIDGE_CLOSURE_REVEAL"]
    assert cartridge["secondary_decorative_door_added"] is False
    assert exterior.measurements["cartridge_closure_is_service_reveal"] is True
    assert exterior.measurements["secondary_cartridge_door_added"] is False
    assert exterior.measurements["cartridge_service_translation_world_mm"] == [0.0, 30.0, -45.0]

    frame_collision = exterior.measurements["cartridge_service_sweep_frame_intersection_mm3"]
    blocker = "CARTRIDGE_SERVICE_SWEEP_INTERSECTS_REAL_FRAME"
    assert (blocker in exterior.blockers) is (float(frame_collision) > 1e-7)


def test_dry_side_reflows_before_rear_skin_growth(exterior: WholeProductExterior) -> None:
    protected = exterior.measurements["dry_bay_protected_intersections_mm3"]
    package_blocked = any(float(value) > 1e-7 for value in protected.values())
    if package_blocked:
        assert exterior.rear_cover is None
        assert exterior.measurements["rear_cover_created"] is False
        assert "DRY_BAY_PACKAGE_REFLOW_REQUIRED_BEFORE_REAR_SKIN" in exterior.blockers
        assert exterior.manifest()["manufacturing_components"]["REAR_DRY_COVER"]["role"] == "BLOCKED_NOT_CREATED"
    else:
        assert exterior.rear_cover is not None
        assert exterior.measurements["rear_cover_created"] is True


def test_treatment_and_retention_stay_reference_only_until_current_frame_rebind(exterior: WholeProductExterior) -> None:
    manifest = exterior.manifest()
    assert manifest["reference_and_owner_geometry"]["treatment"]["role"] == "OWNER_DERIVED_DEPTH_AND_KEEPOUT_REFERENCE_ONLY"
    assert manifest["reference_and_owner_geometry"]["treatment"]["local_axial_span_mm"] == 17.7
    assert "TREATMENT_PR135_STILL_BASED_ON_OBSOLETE_FRAME_HEAD_NOT_PROMOTABLE" in exterior.blockers
    assert "RETENTION_PR141_STILL_BASED_ON_OBSOLETE_FRAME_HEAD_GUARD_REMAINS_REFERENCE_ONLY" in exterior.blockers


def test_physical_validation_and_freeze_are_fail_closed(exterior: WholeProductExterior) -> None:
    manifest = exterior.manifest()
    assert exterior.physical_validation_eligible is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["whole_product_freeze_eligible"] is False
    assert "PHYSICAL_CLEANABILITY_WET_USE_SEALING_FEEL_THERMAL_COMFORT_AND_TOOLING_VALIDATION_REQUIRED" in exterior.blockers
    digest = exterior.architecture_sha256
    assert len(digest) == 64
    assert digest == exterior.architecture_sha256
