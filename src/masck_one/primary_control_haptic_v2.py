from __future__ import annotations

"""Primary-control V2: continuous axial motion proof for the damped haptic control.

V2 preserves the production-intent V1 mechanism and replaces its sampled press poses
with an analytical conservative envelope for the complete 0 -> hard-stop translation.
The envelope is reference geometry only; manufactured parts remain the V1 B-reps.

The design intent is a low-slack guided press, one decisive force break, then a dense
progressive landing with no normal hard-shell impact. No claim is made that the
physical sound or feel is already validated.
"""

from dataclasses import dataclass
import json
from pathlib import Path

import cadquery as cq

from studies.primary_control_haptic_profile import build_manifest as haptic_profile_manifest
from .primary_control_haptic import (
    ANTI_ROTATION_RIB_RADIAL_MM,
    ANTI_ROTATION_RIB_WIDTH_MM,
    CAP_DIAMETER_MM,
    CAP_THICKNESS_MM,
    HARD_STOP_MM,
    INERTIA_CORE_DIAMETER_MM,
    INERTIA_CORE_THICKNESS_MM,
    MAGNET_DIAMETER_MM,
    MAGNET_LENGTH_MM,
    MOUNT_X_MM,
    MOUNT_Y_MM,
    SOURCE_MAIN_SHA,
    STEM_DIAMETER_MM,
    STEM_LENGTH_MM,
    PrimaryControlHapticArchitecture,
    _box,
    _cylinder,
    build_primary_control_haptic_architecture,
)

SCHEMA_V2 = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V2"


class PrimaryControlHapticV2Error(ValueError):
    pass


def _continuous_press_reference(rest_z: float) -> cq.Compound:
    """Conservative exact-in-travel envelope for all rigidly moving button bodies.

    Each primitive spans the full continuous -Z press interval. The cap cylinder
    deliberately fills the shallow finger dish, making this a conservative reference
    envelope rather than an optimistic copy of the manufactured cap surface.
    """
    cap = _cylinder(
        CAP_DIAMETER_MM,
        CAP_THICKNESS_MM + HARD_STOP_MM,
        rest_z - HARD_STOP_MM,
    )
    stem = _cylinder(
        STEM_DIAMETER_MM,
        STEM_LENGTH_MM + HARD_STOP_MM,
        rest_z - STEM_LENGTH_MM - HARD_STOP_MM,
    )

    rib_length = STEM_LENGTH_MM - 0.35
    rib_rest_zmin = rest_z - rib_length - 0.18
    rib_rest_zmax = rest_z - 0.18
    rib_sweep_zmin = rib_rest_zmin - HARD_STOP_MM
    rib_sweep_height = rib_rest_zmax - rib_sweep_zmin
    rib = _box(
        ANTI_ROTATION_RIB_RADIAL_MM,
        ANTI_ROTATION_RIB_WIDTH_MM,
        rib_sweep_height,
        (
            MOUNT_X_MM + STEM_DIAMETER_MM / 2.0 + ANTI_ROTATION_RIB_RADIAL_MM / 2.0,
            MOUNT_Y_MM,
            rib_sweep_zmin + rib_sweep_height / 2.0,
        ),
    )

    core_rest_z0 = rest_z + (CAP_THICKNESS_MM - INERTIA_CORE_THICKNESS_MM) / 2.0
    core = _cylinder(
        INERTIA_CORE_DIAMETER_MM,
        INERTIA_CORE_THICKNESS_MM + HARD_STOP_MM,
        core_rest_z0 - HARD_STOP_MM,
    )

    magnet_rest_z0 = rest_z - STEM_LENGTH_MM + 0.20
    magnet = _cylinder(
        MAGNET_DIAMETER_MM,
        MAGNET_LENGTH_MM + HARD_STOP_MM,
        magnet_rest_z0 - HARD_STOP_MM,
    )

    envelope = cq.Compound.makeCompound([cap, stem, rib, core, magnet])
    if not envelope.Solids() or any(not solid.isValid() for solid in envelope.Solids()):
        raise PrimaryControlHapticV2Error("continuous press reference must be valid positive geometry")
    return envelope


def build_primary_control_haptic_architecture_v2() -> PrimaryControlHapticArchitecture:
    base = build_primary_control_haptic_architecture()
    motion = _continuous_press_reference(base.rest_cap_underside_z_mm)
    references = tuple(
        (name, motion if name == "cap_motion_sweep" else shape)
        for name, shape in base.reference_parts
    )
    result = PrimaryControlHapticArchitecture(
        base.source_main_sha,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        base.material_parts,
        references,
        motion,
        base.keepout_intersections_mm3,
        False,
    )
    result.__post_init__()
    return result


def manifest_v2(architecture: PrimaryControlHapticArchitecture) -> dict[str, object]:
    payload = architecture.manifest()
    profile = haptic_profile_manifest()
    payload.update(
        {
            "schema": SCHEMA_V2,
            "source_main_sha": SOURCE_MAIN_SHA,
            "supersedes": "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V1_SAMPLED_MOTION_REFERENCE",
            "motion_reference": (
                "CONTINUOUS_CONSERVATIVE_ANALYTIC_AXIAL_ENVELOPE_0_TO_HARD_STOP; "
                "REFERENCE_ONLY_NOT_MANUFACTURED_MATERIAL"
            ),
            "satisfying_interaction_intent": (
                "LOW_SLACK_GUIDANCE -> CONTROLLED_FORCE_BUILD -> SINGLE_DECISIVE_FORCE_BREAK -> "
                "DENSE_TWO_STAGE_DAMPED_LANDING -> CONTROLLED_QUIET_RETURN"
            ),
            "haptic_profile_screen": profile,
            "physical_validation_eligible": False,
        }
    )
    return payload


def export_primary_control_haptic_architecture_v2(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v2()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = manifest_v2(architecture)
    (output_dir / "primary_control_haptic_v2_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
