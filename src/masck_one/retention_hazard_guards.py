from __future__ import annotations

"""Cell 8 physical retention hazard-guard candidate geometry.

This module realizes compact guard/shroud B-reps around already-published Cell 3
retention hazards without importing unmerged Cell 3 code as release authority.
The candidate interface is pinned to exact PR heads/blobs/bounds and must be
revalidated if either producer moves.

The guards are intended product-material candidates, but they are deliberately
excluded from released assembly truth until the owning structural-frame lane
provides positive attachment counterparts. Digital clearance is not evidence of
hair/pinch safety, fit, comfort, release force/time, wet usability, or strength.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .authority import Authority, load_authority
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_CELL8_RETENTION_HAZARD_GUARDS_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
SOURCE_AUTHORITY_REVISION = "2026-08-30-R1"
SOURCE_AUTHORITY_BLOB_SHA = "2608dda483b995539de422290371c219668a1527"
SOURCE_MODEL_GIT_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA = "bda5ba87d232c0e6a22e200975a80414a10c9a83"

SOURCE_CELL3_RETENTION_PR = 92
SOURCE_CELL3_RETENTION_HEAD_SHA = "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70"
SOURCE_HAIR_PINCH_GIT_BLOB_SHA = "04ba87a6f8c6dbd103dae0f19869446b064e2057"
SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA = "9647405b36642105c929a3fdd0617d03bfe68c98"
SOURCE_RIGHT_RELEASE_PR = 71
SOURCE_RIGHT_RELEASE_HEAD_SHA = "0b5a619c6cea344038b0e8b8cc10a50e3d193390"
SOURCE_RIGHT_RELEASE_LATCH_GIT_BLOB_SHA = "11d90a75eb108c53f5a1621abdace7271bf5cac5"

DIGITAL_ONLY = "DIGITAL_GUARD_GEOMETRY_AND_CLEARANCE_NOT_PHYSICAL_SAFETY_VALIDATION"
CANDIDATE_INTERFACE_STATUS = "NON_AUTHORITATIVE_UNMERGED_CANDIDATE_INTERFACE"
KERNEL_ZERO_MM3 = 1e-8

# Exact published Cell 3 Prompt-10 / PR-71 candidate hazard and access bounds.
RIGHT_LATCH_HAZARD_BOUNDS_MM = (72.0, 101.5, -6.5, 6.5, -24.0, -12.0)
RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM = (91.0, 104.0, -7.0, 7.0, -25.0, -13.0)
RIGHT_ADJUSTMENT_HAZARD_BOUNDS_MM = (
    (77.75, 80.25, 6.0, 14.0, -35.75, -26.25),
    (84.75, 87.25, 6.0, 14.0, -35.75, -26.25),
    (80.2, 86.8, 3.0, 26.5, -32.85, -26.25),
    (78.1, 84.9, 0.7, 18.7, -35.75, -28.95),
)
RIGHT_ROOT_CAPTURE_HAZARD_BOUNDS_MM = (68.4, 75.6, 1.0, 19.0, -34.6, -27.4)
RIGHT_SCALP_HAIR_CORRIDOR_BOUNDS_MM = (48.0, 76.0, -9.0, 14.0, -53.5, -27.0)

CANDIDATE_INTERFACE_SHA256 = "ce2618f872e01733a2031085ccb402bc40b61ae1e9b427456c0da049bcd72061"

# Cell 8 provisional CAD seeds. These are package geometry, not safety thresholds.
QUICK_GUARD_X_BOUNDS_MM = (70.0, 90.0)
QUICK_GUARD_Y_OUTER_MM = (-8.5, 8.5)
QUICK_GUARD_Y_INNER_MM = (-7.25, 7.25)
QUICK_GUARD_Z_OUTER_MM = (-25.0, -10.0)
QUICK_GUARD_Z_INNER_FRONT_MM = -11.25
QUICK_GUARD_INSTALL_TRAVEL_X_MM = 35.0

ADJUST_GUARD_RIGHT_X_BOUNDS_MM = (76.5, 87.5)
ADJUST_GUARD_Y_OUTER_MM = (-1.5, 29.0)
ADJUST_GUARD_Y_INNER_MM = (-0.25, 27.75)
ADJUST_GUARD_Z_OUTER_MM = (-37.5, -25.75)
ADJUST_GUARD_Z_INNER_POSTERIOR_MM = -36.25
ADJUST_GUARD_INSTALL_TRAVEL_X_MM = 22.0


class RetentionHazardGuardError(ValueError):
    pass


def _finite(value: object, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise RetentionHazardGuardError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise RetentionHazardGuardError(f"{label} must be finite")
    return 0.0 if result == 0.0 else result


def _positive(value: object, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise RetentionHazardGuardError(f"{label} must be positive")
    return result


def _single(solid: cq.Workplane, label: str) -> cq.Workplane:
    shape = solid.val()
    if not shape.isValid() or len(shape.Solids()) != 1 or float(shape.Volume()) <= 0.0:
        raise RetentionHazardGuardError(f"{label} must be one valid positive-volume solid")
    return solid


def _box_from_bounds(bounds: tuple[float, float, float, float, float, float]) -> cq.Workplane:
    xmin, xmax, ymin, ymax, zmin, zmax = tuple(_finite(value, "box bound") for value in bounds)
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise RetentionHazardGuardError("box bounds must have positive extent")
    return (
        cq.Workplane("XY")
        .box(xmax - xmin, ymax - ymin, zmax - zmin, centered=(True, True, True))
        .translate(((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0))
    )


def _union(parts: tuple[cq.Workplane, ...], label: str) -> cq.Workplane:
    if not parts:
        raise RetentionHazardGuardError(f"{label} requires at least one primitive")
    result = parts[0]
    for part in parts[1:]:
        result = result.union(part)
    return _single(result, label)


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(
        round(float(value), 6)
        for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)
    )


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().intersect(second.val()).Volume())
    if not math.isfinite(value) or value < 0.0:
        raise RetentionHazardGuardError("intersection volume must be finite and nonnegative")
    return 0.0 if value < KERNEL_ZERO_MM3 else value


def _distance_mm(first: cq.Workplane, second: cq.Workplane) -> float:
    value = float(first.val().distance(second.val()))
    if not math.isfinite(value) or value < 0.0:
        raise RetentionHazardGuardError("shape distance must be finite and nonnegative")
    return 0.0 if value < 1e-9 else value


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def _assert_released_source_blobs() -> None:
    module_dir = Path(__file__).resolve().parent
    repo_root = Path(__file__).resolve().parents[2]
    sources = {
        module_dir / "model.py": SOURCE_MODEL_GIT_BLOB_SHA,
        module_dir / "structural_frame.py": SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA,
        repo_root / "config" / "masck_one_authority.yaml": SOURCE_AUTHORITY_BLOB_SHA,
    }
    for path, expected in sources.items():
        observed = _git_blob_sha(path)
        if observed != expected:
            raise RetentionHazardGuardError(
                f"{path.name} changed; Cell 8 guard package requires explicit released-source rebind"
            )


def _candidate_interface_payload() -> dict[str, object]:
    return {
        "source_cell3_retention_pr": SOURCE_CELL3_RETENTION_PR,
        "source_cell3_retention_head_sha": SOURCE_CELL3_RETENTION_HEAD_SHA,
        "source_hair_pinch_git_blob_sha": SOURCE_HAIR_PINCH_GIT_BLOB_SHA,
        "source_retention_load_path_git_blob_sha": SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA,
        "source_right_release_pr": SOURCE_RIGHT_RELEASE_PR,
        "source_right_release_head_sha": SOURCE_RIGHT_RELEASE_HEAD_SHA,
        "source_right_release_latch_git_blob_sha": SOURCE_RIGHT_RELEASE_LATCH_GIT_BLOB_SHA,
        "right_latch_hazard_bounds_mm": list(RIGHT_LATCH_HAZARD_BOUNDS_MM),
        "right_latch_emergency_pull_access_bounds_mm": list(
            RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM
        ),
        "right_adjustment_hazard_bounds_mm": [
            list(bounds) for bounds in RIGHT_ADJUSTMENT_HAZARD_BOUNDS_MM
        ],
        "right_root_capture_hazard_bounds_mm": list(RIGHT_ROOT_CAPTURE_HAZARD_BOUNDS_MM),
        "right_scalp_hair_corridor_bounds_mm": list(RIGHT_SCALP_HAIR_CORRIDOR_BOUNDS_MM),
    }


def _assert_candidate_interface_contract() -> None:
    raw = json.dumps(
        _candidate_interface_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if sha256(raw).hexdigest() != CANDIDATE_INTERFACE_SHA256:
        raise RetentionHazardGuardError(
            "candidate retention interface changed; exact Cell 3 source revalidation is required"
        )


def _mirror_x(
    bounds: tuple[float, float, float, float, float, float]
) -> tuple[float, float, float, float, float, float]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    return (-xmax, -xmin, ymin, ymax, zmin, zmax)


def _quick_guard_primitive_bounds(
    x_bounds: tuple[float, float]
) -> tuple[tuple[float, float, float, float, float, float], ...]:
    xmin, xmax = x_bounds
    yo0, yo1 = QUICK_GUARD_Y_OUTER_MM
    yi0, yi1 = QUICK_GUARD_Y_INNER_MM
    zo0, zo1 = QUICK_GUARD_Z_OUTER_MM
    return (
        (xmin, xmax, yo0, yi0, zo0, zo1),
        (xmin, xmax, yi1, yo1, zo0, zo1),
        (xmin, xmax, yi0, yi1, QUICK_GUARD_Z_INNER_FRONT_MM, zo1),
    )


def _adjust_guard_primitive_bounds(
    x_bounds: tuple[float, float]
) -> tuple[tuple[float, float, float, float, float, float], ...]:
    xmin, xmax = x_bounds
    yo0, yo1 = ADJUST_GUARD_Y_OUTER_MM
    yi0, yi1 = ADJUST_GUARD_Y_INNER_MM
    zo0, zo1 = ADJUST_GUARD_Z_OUTER_MM
    return (
        (xmin, xmax, yo0, yo1, zo0, ADJUST_GUARD_Z_INNER_POSTERIOR_MM),
        (xmin, xmax, yo0, yi0, ADJUST_GUARD_Z_INNER_POSTERIOR_MM, zo1),
        (xmin, xmax, yi1, yo1, ADJUST_GUARD_Z_INNER_POSTERIOR_MM, zo1),
    )


def _solid_from_primitive_bounds(
    bounds_set: tuple[tuple[float, float, float, float, float, float], ...],
    label: str,
) -> cq.Workplane:
    return _union(tuple(_box_from_bounds(bounds) for bounds in bounds_set), label)


def _translate_bounds_x(
    bounds: tuple[float, float, float, float, float, float],
    delta_x_mm: float,
) -> tuple[float, float, float, float, float, float]:
    delta = _finite(delta_x_mm, "X translation")
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    return (xmin + delta, xmax + delta, ymin, ymax, zmin, zmax)


def _exact_axis_x_sweep(
    final_primitive_bounds: tuple[tuple[float, float, float, float, float, float], ...],
    start_delta_x_mm: float,
    label: str,
) -> cq.Workplane:
    delta = _finite(start_delta_x_mm, "start X offset")
    swept_parts: list[cq.Workplane] = []
    for bounds in final_primitive_bounds:
        start = _translate_bounds_x(bounds, delta)
        xmin = min(bounds[0], start[0])
        xmax = max(bounds[1], start[1])
        swept_parts.append(
            _box_from_bounds((xmin, xmax, bounds[2], bounds[3], bounds[4], bounds[5]))
        )
    return _union(tuple(swept_parts), label)


def _protected_solid(model: MasckOneModel, index: int) -> tuple[str, cq.Workplane]:
    volume = model.protected_volumes.all[index]
    zone = volume.zone
    wp = cq.Workplane("XY").workplane(offset=-80.0).center(zone.center.x, zone.center.y)
    if zone.shape == "CIRCLE":
        solid = wp.circle(zone.envelope_width_mm / 2.0).extrude(120.0)
    else:
        solid = (
            wp.ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0)
            .extrude(120.0)
        )
    if zone.angle_deg:
        solid = solid.rotate(
            (zone.center.x, zone.center.y, 0.0),
            (zone.center.x, zone.center.y, 1.0),
            zone.angle_deg,
        )
    return zone.zone_id, solid


@dataclass(frozen=True, slots=True)
class GuardPart:
    part_id: str
    side: str
    role: str
    solid: cq.Workplane
    exact_factory_install_sweep: cq.Workplane
    install_translation_x_mm: float
    source_hazard_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.side not in {"WEARER_LEFT", "WEARER_RIGHT"}:
            raise RetentionHazardGuardError("guard side must use controlled wearer-relative vocabulary")
        if not self.part_id or not self.role or not self.source_hazard_ids:
            raise RetentionHazardGuardError("guard identity, role, and hazard bindings must be explicit")
        _single(self.solid, self.part_id)
        _single(self.exact_factory_install_sweep, f"{self.part_id} install sweep")
        _finite(self.install_translation_x_mm, "guard install translation")

    def manifest(self) -> dict[str, object]:
        return {
            "part_id": self.part_id,
            "side": self.side,
            "role": self.role,
            "bounds_mm": list(_bbox(self.solid)),
            "volume_mm3": round(float(self.solid.val().Volume()), 6),
            "source_hazard_ids": list(self.source_hazard_ids),
            "geometry_role": "PHYSICAL_MATERIAL_CANDIDATE_NOT_RELEASED_ASSEMBLY_TRUTH",
            "material": None,
            "mass_g": None,
            "positive_attachment_realized": False,
            "attachment_counterpart_dependency": "CELL6_REALIZED_STRUCTURAL_FRAME_OR_RETENTION_ROOT",
            "assembly_in_development_compound": False,
            "factory_install": {
                "motion": "EXACT_PURE_X_TRANSLATION_SWEEP",
                "translation_x_mm": self.install_translation_x_mm,
                "sweep_bounds_mm": list(_bbox(self.exact_factory_install_sweep)),
                "wearer_present": False,
                "powered": False,
            },
        }


@dataclass(frozen=True, slots=True)
class ClearanceCheck:
    check_id: str
    subject_id: str
    obstacle_id: str
    intersection_volume_mm3: float
    minimum_distance_mm: float

    @property
    def passes(self) -> bool:
        return self.intersection_volume_mm3 == 0.0

    def manifest(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "subject_id": self.subject_id,
            "obstacle_id": self.obstacle_id,
            "intersection_volume_mm3": self.intersection_volume_mm3,
            "minimum_distance_mm": self.minimum_distance_mm,
            "passes": self.passes,
        }


@dataclass(frozen=True, slots=True)
class RetentionHazardGuardPackage:
    right_quick_release_guard: GuardPart
    left_adjustment_guard: GuardPart
    right_adjustment_guard: GuardPart
    clearance_checks: tuple[ClearanceCheck, ...]

    def __post_init__(self) -> None:
        if any(not check.passes for check in self.clearance_checks):
            failed = tuple(check.check_id for check in self.clearance_checks if not check.passes)
            raise RetentionHazardGuardError(f"required Cell 8 guard clearance failed: {failed}")

    @property
    def guards(self) -> tuple[GuardPart, GuardPart, GuardPart]:
        return (
            self.right_quick_release_guard,
            self.left_adjustment_guard,
            self.right_adjustment_guard,
        )

    @property
    def package_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_authority_revision": SOURCE_AUTHORITY_REVISION,
            "source_authority_blob_sha": SOURCE_AUTHORITY_BLOB_SHA,
            "source_model_git_blob_sha": SOURCE_MODEL_GIT_BLOB_SHA,
            "source_structural_frame_git_blob_sha": SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "candidate_interface_status": CANDIDATE_INTERFACE_STATUS,
            "candidate_interface": _candidate_interface_payload(),
            "candidate_interface_sha256": CANDIDATE_INTERFACE_SHA256,
            "promotion_requires_live_candidate_head_revalidation": True,
            "guards": [guard.manifest() for guard in self.guards],
            "clearance_checks": [check.manifest() for check in self.clearance_checks],
            "guard_coverage": {
                "right_quick_release_hazard_shroud_realized_digitally": True,
                "bilateral_adjustment_guide_index_stop_shrouds_realized_digitally": True,
                "right_emergency_pull_access_preserved": True,
                "bilateral_root_capture_guard_closed": False,
                "bilateral_scalp_hair_corridor_guard_closed": False,
                "physical_hair_or_pinch_safety_validated": False,
            },
            "assembly_semantics": {
                "factory_sequence": [
                    "ASSEMBLE_CELL3_RETENTION_AND_RIGHT_RELEASE_SOURCE_MECHANISMS",
                    "INSTALL_BILATERAL_ADJUSTMENT_GUARDS_BY_EXACT_X_TRANSLATION_WITH_WEARER_ABSENT",
                    "INSTALL_RIGHT_RELEASE_GUARD_BY_EXACT_POSITIVE_X_TRANSLATION_WITH_WEARER_ABSENT",
                    "ATTACH_GUARDS_TO_FUTURE_POSITIVE_FRAME_OR_RETENTION_COUNTERPART",
                ],
                "positive_guard_attachment_realized": False,
                "friction_only_attachment_allowed": False,
                "overlap_as_attachment_allowed": False,
                "reference_sweeps_are_product_material": False,
            },
            "unresolved_digital_requirements": [
                "CELL6_REALIZED_FRAME_OR_RETENTION_ROOT_POSITIVE_GUARD_ATTACHMENT_COUNTERPART",
                "BILATERAL_ROOT_CAPTURE_GUARD_OR_EDGE_TREATMENT",
                "BILATERAL_SCALP_HAIR_APPROACH_GUARD_OR_CONTROLLED_SOFT_INTERFACE",
                "REBASE_AND_REBIND_AFTER_ANY_CELL3_71_OR_92_SOURCE_MOVEMENT",
                "INTEGRATED_POST_RELEASE_WHOLE_HEAD_REMOVAL_SWEEP",
            ],
            "unresolved_physical_gates": [
                "HAIR_ENTRAPMENT_AND_PINCH_SAFETY",
                "GUARD_EDGE_CONTACT_AND_COMFORT",
                "GUARD_STRENGTH_STIFFNESS_FATIGUE_WEAR_AND_MATERIAL",
                "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N",
                "WET_ONE_HAND_RELEASE_TIME_LE_2_S",
                "ACCIDENTAL_RELEASE_MARGIN",
                "FIT_CONTACT_PRESSURE_AND_HAIR_INTERACTION",
            ],
            "physical_validation_eligible": False,
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["package_sha256"] = self.package_sha256
        return payload


def _clearance(
    check_id: str,
    subject_id: str,
    subject: cq.Workplane,
    obstacle_id: str,
    obstacle: cq.Workplane,
) -> ClearanceCheck:
    return ClearanceCheck(
        check_id=check_id,
        subject_id=subject_id,
        obstacle_id=obstacle_id,
        intersection_volume_mm3=_intersection_mm3(subject, obstacle),
        minimum_distance_mm=round(_distance_mm(subject, obstacle), 6),
    )


def _build_guards() -> tuple[GuardPart, GuardPart, GuardPart]:
    quick_final_bounds = _quick_guard_primitive_bounds(QUICK_GUARD_X_BOUNDS_MM)
    quick = GuardPart(
        part_id="CELL8_RIGHT_QUICK_RELEASE_U_SHROUD",
        side="WEARER_RIGHT",
        role="shield top/bottom/anterior latch hazard surfaces while preserving outboard emergency pull access",
        solid=_solid_from_primitive_bounds(quick_final_bounds, "right quick-release U shroud"),
        exact_factory_install_sweep=_exact_axis_x_sweep(
            quick_final_bounds,
            -QUICK_GUARD_INSTALL_TRAVEL_X_MM,
            "right quick-release guard exact install sweep",
        ),
        install_translation_x_mm=QUICK_GUARD_INSTALL_TRAVEL_X_MM,
        source_hazard_ids=("RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION",),
    )

    right_adjust_final_bounds = _adjust_guard_primitive_bounds(ADJUST_GUARD_RIGHT_X_BOUNDS_MM)
    right_adjust = GuardPart(
        part_id="CELL8_RIGHT_ADJUSTMENT_U_SHROUD",
        side="WEARER_RIGHT",
        role="shield posterior/superior/inferior guide, index-pin, and stop-pin hazard surfaces",
        solid=_solid_from_primitive_bounds(right_adjust_final_bounds, "right adjustment U shroud"),
        exact_factory_install_sweep=_exact_axis_x_sweep(
            right_adjust_final_bounds,
            -ADJUST_GUARD_INSTALL_TRAVEL_X_MM,
            "right adjustment guard exact install sweep",
        ),
        install_translation_x_mm=ADJUST_GUARD_INSTALL_TRAVEL_X_MM,
        source_hazard_ids=(
            "RIGHT_ADJUSTMENT_MEDIAL_GUIDE_NIP",
            "RIGHT_ADJUSTMENT_OUTBOARD_GUIDE_NIP",
            "RIGHT_INDEX_PIN_SERVICE_PATH",
            "RIGHT_STOP_PIN_CLIP_REGION",
        ),
    )

    left_x_bounds = (-ADJUST_GUARD_RIGHT_X_BOUNDS_MM[1], -ADJUST_GUARD_RIGHT_X_BOUNDS_MM[0])
    left_adjust_final_bounds = _adjust_guard_primitive_bounds(left_x_bounds)
    left_adjust = GuardPart(
        part_id="CELL8_LEFT_ADJUSTMENT_U_SHROUD",
        side="WEARER_LEFT",
        role="shield posterior/superior/inferior guide, index-pin, and stop-pin hazard surfaces",
        solid=_solid_from_primitive_bounds(left_adjust_final_bounds, "left adjustment U shroud"),
        exact_factory_install_sweep=_exact_axis_x_sweep(
            left_adjust_final_bounds,
            ADJUST_GUARD_INSTALL_TRAVEL_X_MM,
            "left adjustment guard exact install sweep",
        ),
        install_translation_x_mm=-ADJUST_GUARD_INSTALL_TRAVEL_X_MM,
        source_hazard_ids=(
            "LEFT_ADJUSTMENT_MEDIAL_GUIDE_NIP",
            "LEFT_ADJUSTMENT_OUTBOARD_GUIDE_NIP",
            "LEFT_INDEX_PIN_SERVICE_PATH",
            "LEFT_STOP_PIN_CLIP_REGION",
        ),
    )
    return quick, left_adjust, right_adjust


def build_retention_hazard_guards(
    authority: Authority | None = None,
    model: MasckOneModel | None = None,
) -> RetentionHazardGuardPackage:
    _assert_released_source_blobs()
    _assert_candidate_interface_contract()
    authority = authority or load_authority()
    if authority.get("project", "authority_revision") != SOURCE_AUTHORITY_REVISION:
        raise RetentionHazardGuardError("machine authority revision changed; explicit guard rebind required")
    model = model or build_model(authority)

    quick, left_adjust, right_adjust = _build_guards()
    checks: list[ClearanceCheck] = []

    right_latch_hazard = _box_from_bounds(RIGHT_LATCH_HAZARD_BOUNDS_MM)
    right_pull_access = _box_from_bounds(RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM)
    checks.extend(
        (
            _clearance(
                "RIGHT_QUICK_GUARD_CLEAR_LATCH_HAZARD",
                quick.part_id,
                quick.solid,
                "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION",
                right_latch_hazard,
            ),
            _clearance(
                "RIGHT_QUICK_GUARD_INSTALL_SWEEP_CLEAR_LATCH_HAZARD",
                f"{quick.part_id}_INSTALL_SWEEP",
                quick.exact_factory_install_sweep,
                "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION",
                right_latch_hazard,
            ),
            _clearance(
                "RIGHT_QUICK_GUARD_CLEAR_EMERGENCY_PULL_ACCESS",
                quick.part_id,
                quick.solid,
                "RIGHT_LATCH_EMERGENCY_PULL_ACCESS",
                right_pull_access,
            ),
            _clearance(
                "RIGHT_QUICK_GUARD_INSTALL_SWEEP_CLEAR_EMERGENCY_PULL_ACCESS",
                f"{quick.part_id}_INSTALL_SWEEP",
                quick.exact_factory_install_sweep,
                "RIGHT_LATCH_EMERGENCY_PULL_ACCESS",
                right_pull_access,
            ),
        )
    )

    for index, bounds in enumerate(RIGHT_ADJUSTMENT_HAZARD_BOUNDS_MM, start=1):
        right_hazard = _box_from_bounds(bounds)
        left_hazard = _box_from_bounds(_mirror_x(bounds))
        checks.append(
            _clearance(
                f"RIGHT_ADJUST_GUARD_CLEAR_SOURCE_HAZARD_{index}",
                right_adjust.part_id,
                right_adjust.solid,
                f"RIGHT_ADJUSTMENT_SOURCE_HAZARD_{index}",
                right_hazard,
            )
        )
        checks.append(
            _clearance(
                f"LEFT_ADJUST_GUARD_CLEAR_SOURCE_HAZARD_{index}",
                left_adjust.part_id,
                left_adjust.solid,
                f"LEFT_ADJUSTMENT_SOURCE_HAZARD_{index}",
                left_hazard,
            )
        )
        checks.append(
            _clearance(
                f"RIGHT_ADJUST_GUARD_INSTALL_SWEEP_CLEAR_SOURCE_HAZARD_{index}",
                f"{right_adjust.part_id}_INSTALL_SWEEP",
                right_adjust.exact_factory_install_sweep,
                f"RIGHT_ADJUSTMENT_SOURCE_HAZARD_{index}",
                right_hazard,
            )
        )
        checks.append(
            _clearance(
                f"LEFT_ADJUST_GUARD_INSTALL_SWEEP_CLEAR_SOURCE_HAZARD_{index}",
                f"{left_adjust.part_id}_INSTALL_SWEEP",
                left_adjust.exact_factory_install_sweep,
                f"LEFT_ADJUSTMENT_SOURCE_HAZARD_{index}",
                left_hazard,
            )
        )

    right_root = _box_from_bounds(RIGHT_ROOT_CAPTURE_HAZARD_BOUNDS_MM)
    left_root = _box_from_bounds(_mirror_x(RIGHT_ROOT_CAPTURE_HAZARD_BOUNDS_MM))
    right_hair = _box_from_bounds(RIGHT_SCALP_HAIR_CORRIDOR_BOUNDS_MM)
    left_hair = _box_from_bounds(_mirror_x(RIGHT_SCALP_HAIR_CORRIDOR_BOUNDS_MM))
    for side, guard, root, hair in (
        ("RIGHT", right_adjust, right_root, right_hair),
        ("LEFT", left_adjust, left_root, left_hair),
    ):
        checks.append(
            _clearance(
                f"{side}_ADJUST_GUARD_CLEAR_UNRESOLVED_ROOT_CAPTURE_HAZARD",
                guard.part_id,
                guard.solid,
                f"{side}_ROOT_CAPTURE_FUTURE_PINCH_REGION",
                root,
            )
        )
        checks.append(
            _clearance(
                f"{side}_ADJUST_GUARD_CLEAR_SCALP_HAIR_APPROACH_CORRIDOR",
                guard.part_id,
                guard.solid,
                f"{side}_SCALP_HAIR_APPROACH_CORRIDOR",
                hair,
            )
        )

    checks.extend(
        (
            _clearance(
                "RIGHT_QUICK_GUARD_CLEAR_RIGHT_ADJUSTMENT_GUARD",
                quick.part_id,
                quick.solid,
                right_adjust.part_id,
                right_adjust.solid,
            ),
            _clearance(
                "RIGHT_QUICK_INSTALL_SWEEP_CLEAR_RIGHT_ADJUSTMENT_GUARD",
                f"{quick.part_id}_INSTALL_SWEEP",
                quick.exact_factory_install_sweep,
                right_adjust.part_id,
                right_adjust.solid,
            ),
        )
    )

    released_obstacles = (
        model.shell,
        model.nasal_interface,
        *model.actuator_envelopes,
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    )
    for guard in (quick, left_adjust, right_adjust):
        for obstacle in released_obstacles:
            checks.append(
                _clearance(
                    f"{guard.part_id}_CLEAR_RELEASED_{obstacle.name.upper()}",
                    guard.part_id,
                    guard.solid,
                    obstacle.name,
                    obstacle.solid,
                )
            )
            checks.append(
                _clearance(
                    f"{guard.part_id}_INSTALL_SWEEP_CLEAR_RELEASED_{obstacle.name.upper()}",
                    f"{guard.part_id}_INSTALL_SWEEP",
                    guard.exact_factory_install_sweep,
                    obstacle.name,
                    obstacle.solid,
                )
            )
        for index in range(len(model.protected_volumes.all)):
            protected_id, protected = _protected_solid(model, index)
            checks.append(
                _clearance(
                    f"{guard.part_id}_CLEAR_PROTECTED_{protected_id}",
                    guard.part_id,
                    guard.solid,
                    protected_id,
                    protected,
                )
            )

    return RetentionHazardGuardPackage(
        right_quick_release_guard=quick,
        left_adjustment_guard=left_adjust,
        right_adjustment_guard=right_adjust,
        clearance_checks=tuple(checks),
    )


def export_retention_hazard_guard_review(
    output_dir: Path,
    package: RetentionHazardGuardPackage | None = None,
) -> tuple[Path, ...]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    package = package or build_retention_hazard_guards()

    outputs: list[Path] = []
    for guard in package.guards:
        stem = guard.part_id.lower()
        part_path = output_dir / f"{stem}.step"
        sweep_path = output_dir / f"{stem}_exact_factory_install_sweep_reference.step"
        cq.exporters.export(guard.solid, str(part_path))
        cq.exporters.export(guard.exact_factory_install_sweep, str(sweep_path))
        outputs.extend((part_path, sweep_path))

    manifest_path = output_dir / "retention_hazard_guards_manifest.json"
    manifest_path.write_text(
        json.dumps(package.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    outputs.append(manifest_path)
    return tuple(outputs)
