from __future__ import annotations

import math

from masck_one import primary_control_haptic as v1
from masck_one.primary_control_haptic_v5 import (
    MAGNET_REAR_POLYMER_SKIN_MM,
    MIN_MAGNET_RADIAL_ENCAPSULATION_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v5,
)


def test_v5_magnet_no_longer_overlaps_stem_polymer_and_is_fully_trapped():
    architecture = build_primary_control_haptic_architecture_v5()
    material = dict(architecture.material_parts)
    moving = material["primary_control_cap_stem"]
    magnet = material["sensor_magnet"]

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert moving.isValid() and len(moving.Solids()) == 1
    assert magnet.isValid() and len(magnet.Solids()) == 1
    assert architecture.magnet_cavity_removed_mm3 > 0.0
    assert math.isclose(
        architecture.magnet_cavity_removed_mm3,
        magnet.Volume(),
        abs_tol=1e-6,
    )
    assert architecture.magnet_polymer_intersection_mm3 == 0.0

    radial_cover = (v1.STEM_DIAMETER_MM - v1.MAGNET_DIAMETER_MM) / 2.0
    assert radial_cover >= MIN_MAGNET_RADIAL_ENCAPSULATION_MM
    assert MAGNET_REAR_POLYMER_SKIN_MM > 0.0


def test_v5_retention_architecture_avoids_extra_hidden_retainer_and_adhesive():
    manifest = build_primary_control_haptic_architecture_v5().manifest()
    retention = manifest["sensor_magnet_retention"]

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"].endswith("SENSOR_MAGNET_FALSE_MATERIAL_OVERLAP_WITHOUT_RETENTION_PATH")
    assert retention["architecture"] == "FULLY_TRAPPED_INSERT_MOLDED_MAGNET_IN_STEM"
    assert retention["separate_retainer_parts"] == 0
    assert retention["adhesive_required_for_retention"] is False
    assert retention["post_mold_magnet_serviceable"] is False
    assert manifest["physical_validation_eligible"] is False


def test_v5_preserves_guidance_and_released_keepouts():
    architecture = build_primary_control_haptic_architecture_v5()
    manifest = architecture.manifest()

    assert manifest["guidance"]["architecture"] == "TWO_SHELL_FIXED_SPLIT_LOW_FRICTION_FLANGED_SLEEVES"
    assert min(architecture.bushing_capture_removed_mm3.values()) > 0.0
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
