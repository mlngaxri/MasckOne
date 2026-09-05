from __future__ import annotations

"""Exact continuous withdrawal sweep for the Cell 3 right quick-release latch.

The source latch already carries a conservative all-state AABB and the reset successor
carries exact low/high pure-translation sub-sweeps. This module promotes a single exact
rigid-slider swept solid over the complete 0..7.3 mm interval and uses it for complete
withdrawal collision checks. The construction is exact for the current slider because
every slider primitive translates only along its own X axis; extending each primitive
by the travel interval is its Minkowski sum with that segment, and sweep distributes
over the primitive union.

Digital geometry only. This does not establish release force/time, flexure response,
wet usability, wear, fatigue, comfort, full-head removal, or physical safety.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .right_quick_release_latch import (
    RELEASE_TRAVEL_MM,
    WORLD_FRAME_ID,
    _bbox,
    _intersection_mm3,
    _protected_solid,
    _source_model_sha,
)
from .right_quick_release_reset import (
    RightQuickReleaseResetMechanics,
    _translation_sweep,
    build_right_quick_release_reset_mechanics,
)

SCHEMA = "MASCK_ONE_CELL3_RIGHT_QUICK_RELEASE_CONTINUOUS_SWEEP_V1"
DIGITAL_ONLY = "DIGITAL_CONTINUOUS_SWEEP_ONLY_NOT_PHYSICAL_VALIDATION"
KERNEL_VOLUME_TOL_MM3 = 1e-7


class RightQuickReleaseSweepError(ValueError):
    pass


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or float(shape.Volume()) <= 0.0 or len(shape.Solids()) != 1:
        raise RightQuickReleaseSweepError(
            f"{label} must be one valid positive-volume solid"
        )
    return solid


def _difference_volume_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().cut(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RightQuickReleaseSweepError("difference volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_VOLUME_TOL_MM3 else value


@dataclass(frozen=True, slots=True)
class SweepCollisionCheck:
    check_id: str
    obstacle_id: str
    intersection_volume_mm3: float

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "obstacle_id": self.obstacle_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class RightQuickReleaseContinuousSweep:
    reset: RightQuickReleaseResetMechanics
    exact_slider_sweep: cq.Workplane
    collision_checks: tuple[SweepCollisionCheck, ...]
    exact_outside_legacy_aabb_mm3: float
    low_partition_outside_exact_mm3: float
    high_partition_outside_exact_mm3: float
    exact_not_covered_by_partition_mm3: float

    def __post_init__(self) -> None:
        _single(self.exact_slider_sweep, "exact continuous withdrawal sweep")
        if any(not check.passes for check in self.collision_checks):
            raise RightQuickReleaseSweepError(
                "exact continuous withdrawal sweep intersects required fixed geometry"
            )
        for label, value in (
            ("exact outside legacy AABB", self.exact_outside_legacy_aabb_mm3),
            ("low partition outside exact", self.low_partition_outside_exact_mm3),
            ("high partition outside exact", self.high_partition_outside_exact_mm3),
            ("exact not covered by partition", self.exact_not_covered_by_partition_mm3),
        ):
            if not math.isfinite(value) or value != 0.0:
                raise RightQuickReleaseSweepError(f"{label} must be zero")

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(raw.encode()).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        exact_shape = self.exact_slider_sweep.val()
        legacy = self.reset.latch.continuous_withdrawal_sweep.solid
        exact_volume = float(exact_shape.Volume())
        legacy_volume = float(legacy.val().Volume())
        clear_offset = self.reset.manifest()["detent_geometry"]["detent_clear_translation_offset_mm"]
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_reset_package_sha256": self.reset.package_sha256,
            "source_latch_package_sha256": self.reset.latch.package_sha256,
            "motion": {
                "kind": "PURE_TRANSLATION",
                "direction_xyz": [1.0, 0.0, 0.0],
                "offset_interval_mm": [0.0, RELEASE_TRAVEL_MM],
                "independent_rotation": False,
            },
            "exact_sweep": {
                "construction": (
                    "EXACT_MINKOWSKI_SUM_OF_EACH_CURRENT_SLIDER_PRIMITIVE_WITH_X_SEGMENT"
                ),
                "primitive_union_distribution": True,
                "solid_count": len(exact_shape.Solids()),
                "volume_mm3": exact_volume,
                "bounds_mm": list(_bbox(self.exact_slider_sweep)),
                "complete_withdrawal_interval_covered": True,
            },
            "legacy_conservative_bound": {
                "kind": "AABB_OF_ALL_TRANSLATED_SLIDER_STATES",
                "volume_mm3": legacy_volume,
                "bounds_mm": list(_bbox(legacy)),
                "exact_sweep_outside_bound_mm3": self.exact_outside_legacy_aabb_mm3,
                "overcoverage_mm3": legacy_volume - exact_volume,
                "retained_as_cross_check_not_primary_collision_proof": True,
            },
            "reset_partition_cross_check": {
                "low_offset_interval_mm": [0.0, clear_offset],
                "high_offset_interval_mm": [clear_offset, RELEASE_TRAVEL_MM],
                "low_partition_outside_exact_mm3": self.low_partition_outside_exact_mm3,
                "high_partition_outside_exact_mm3": self.high_partition_outside_exact_mm3,
                "exact_not_covered_by_partition_mm3": self.exact_not_covered_by_partition_mm3,
                "partitions_cover_exact_complete_sweep": True,
            },
            "collision_checks": [check.manifest() for check in self.collision_checks],
            "all_complete_withdrawal_collision_checks_clear": all(
                check.passes for check in self.collision_checks
            ),
            "four_zone_actuation_preserved": True,
            "full_head_removal_trajectory_included": False,
            "physical_validation_eligible": False,
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def build_right_quick_release_continuous_sweep(
    *,
    reset: RightQuickReleaseResetMechanics | None = None,
    model: MasckOneModel | None = None,
) -> RightQuickReleaseContinuousSweep:
    model = model or build_model()
    reset = reset or build_right_quick_release_reset_mechanics(
        authority=model.authority,
        model=model,
    )
    if reset.source_model_sha256 != _source_model_sha(model):
        raise RightQuickReleaseSweepError(
            "continuous sweep model does not match reset/source model provenance"
        )

    exact = _single(
        _translation_sweep(0.0, RELEASE_TRAVEL_MM),
        "exact continuous withdrawal sweep",
    )
    legacy = reset.latch.continuous_withdrawal_sweep.solid
    exact_outside_aabb = _difference_volume_mm3(exact, legacy)

    low = reset.low_offset_translation_sweep.solid
    high = reset.high_offset_translation_sweep.solid
    low_outside_exact = _difference_volume_mm3(low, exact)
    high_outside_exact = _difference_volume_mm3(high, exact)
    partition = _single(low.union(high), "combined reset translation partition")
    exact_not_covered = _difference_volume_mm3(exact, partition)

    checks: list[SweepCollisionCheck] = []

    def add(check_id: str, obstacle_id: str, obstacle: cq.Workplane) -> None:
        checks.append(
            SweepCollisionCheck(
                check_id,
                obstacle_id,
                _intersection_mm3(exact, obstacle),
            )
        )

    latch = reset.latch
    add("EXACT_WITHDRAWAL_VS_FRAME_SOCKET", latch.socket.part_id, latch.socket.solid)
    add("EXACT_WITHDRAWAL_VS_HALO_TONGUE", latch.tongue.part_id, latch.tongue.solid)
    add(
        "EXACT_WITHDRAWAL_VS_CAPTIVE_GUIDE",
        latch.guide_capsule.part_id,
        latch.guide_capsule.solid,
    )
    add("EXACT_WITHDRAWAL_VS_CURRENT_MAIN_SHELL", "RIGID_SHELL", model.shell.solid)
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        add(
            f"EXACT_WITHDRAWAL_VS_ACTUATOR_{index}",
            actuator.name.upper(),
            actuator.solid,
        )
    for component in (
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    ):
        add(
            f"EXACT_WITHDRAWAL_VS_{component.name.upper()}",
            component.name.upper(),
            component.solid,
        )
    for index in range(len(model.protected_volumes.all)):
        zone_id, protected = _protected_solid(model, index)
        add(f"EXACT_WITHDRAWAL_VS_{zone_id}", zone_id, protected)

    return RightQuickReleaseContinuousSweep(
        reset=reset,
        exact_slider_sweep=exact,
        collision_checks=tuple(checks),
        exact_outside_legacy_aabb_mm3=exact_outside_aabb,
        low_partition_outside_exact_mm3=low_outside_exact,
        high_partition_outside_exact_mm3=high_outside_exact,
        exact_not_covered_by_partition_mm3=exact_not_covered,
    )


def export_right_quick_release_continuous_sweep(
    output_dir: str | Path,
    sweep: RightQuickReleaseContinuousSweep,
) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    step_path = root / "right_latch_exact_continuous_withdrawal_sweep.step"
    shape = sweep.exact_slider_sweep.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise RuntimeError("exact continuous withdrawal sweep must be one valid solid")
    cq.exporters.export(sweep.exact_slider_sweep, str(step_path))
    if not step_path.is_file() or step_path.stat().st_size <= 0:
        raise RuntimeError("failed to export exact continuous withdrawal sweep STEP")

    manifest_path = root / "right_quick_release_continuous_sweep_manifest.json"
    manifest_path.write_text(
        json.dumps(sweep.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return step_path, manifest_path
