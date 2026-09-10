from __future__ import annotations

"""Whole-product exterior convergence for Masck One.

This integration layer owns exterior composition and interface consumption only. It
reconstructs the strongest accepted Cell 2 A-surface, cuts the exact current Cell 6
shell-joint tools into that surface, realizes only the HMI opening and wearer-side
reaction land owned by exterior, and adds compact removable retention-root fairings.

Owner-controlled cartridge, dry-side, treatment and thermal geometry remains separate
from integration-owned manufactured material. Package conflicts block rear skin growth
instead of being hidden by cosmetic bulges. All force, leakage, comfort, thermal,
hygiene, acoustic, durability and production-capability claims remain physically open.
"""

from dataclasses import dataclass, field
from hashlib import sha1, sha256
import json
import math
from pathlib import Path

import cadquery as cq

from .dry_side_disconnect_interface import build_battery_disconnect_interface
from .dry_side_harness_service import DRY_BAY_BOUNDS_WORLD_MM, build_dry_side_harness_service
from .exterior_eye_roll import build_eye_rolled_exterior_shell, eye_inner_roll_manifest
from .model import MasckOneModel, build_model
from .realized_waste_cartridge import build_realized_waste_cartridge
from .cartridge_service_corridor import build_service_corridor
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_retention_roots import build_structural_frame_retention_roots
from .structural_frame_shell_joints import build_structural_frame_shell_joints
from .warm_cool_package import build_warm_cool_package


SCHEMA = "MASCK_ONE_WHOLE_PRODUCT_EXTERIOR_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"
AUTHORITY_REVISION = "2026-08-30-R1"

# Exact owner snapshot consumed for this integration checkpoint. Heads are evidence
# identities, not permission to promote another owner's unmerged geometry to released
# product truth.
OWNER_HEADS = {
    "exterior_pr70": "152312fe6eced419eef4e1e58c33df09fd0710ea",
    "frame_pr117": "fe8e73a2002632633ad1978ca22245eb401d864d",
    "treatment_pr135": "b3a224770f724fbc625534ea563fa09c1b910729",
    "cartridge_pr140": "40b9c12238d208fd631a8c52f6a4f9008a38b31d",
    "retention_pr141": "13dff9efb2bebf099a6cbb054d72620b9e0b0672",
    "dry_side_pr142": "6ee47ecba639a9ce09c3cd076bbfe0408c2d089f",
    "thermal_pr143": "d2b82e50d5bfbadb4a60588a9119139b4742031a",
    "hmi_pr144": "9fb64aa4753dad03a455aad4802910d8814ef5ce",
}

# Files copied source-exact into this integration lineage are fail-closed by Git blob.
SOURCE_GIT_BLOBS = {
    "config/masck_one_authority.yaml": "2608dda483b995539de422290371c219668a1527",
    "src/masck_one/model.py": "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894",
    "src/masck_one/exterior_surface.py": "bb9185ffadc91f11ccac3285bb4c3d4db496e9dd",
    "src/masck_one/exterior_construction.py": "2bc77bd0ddd95b13ccab246d6ee26fbfbc8d482d",
    "src/masck_one/exterior_rigid_clearance.py": "dd3e4e1b6c8bfaf3c4b6b36d79a02305329b74ed",
    "src/masck_one/exterior_inferior_turnover.py": "559559abab8a41d234f50e0c8a326999efea8ee1",
    "src/masck_one/exterior_eye_roll.py": "f75d39af17f2ba30e2a061a684006a5eee3e3668",
    "src/masck_one/structural_frame_realization.py": "5e626e73cc130dc6cc6570e40183380562cf5b5e",
    "src/masck_one/structural_frame_shell_joints.py": "ec6c94dda6f5e439e887e929810bbc5dc729964e",
    "src/masck_one/structural_frame_actuator_reactions.py": "dae953807584b97747cf3f936271e019b6746d4f",
    "src/masck_one/structural_frame_retention_roots.py": "1cf6357898d62afc9ebdc28d3f6394c12dd76644",
    "src/masck_one/structural_frame_dry_package_supports.py": "781bc97131de99b7d473ca865e352364cae8b98a",
    "src/masck_one/realized_waste_cartridge.py": "324447c16307cb930358c1cf32a6f1a56d829d8e",
    "src/masck_one/cartridge_service_corridor.py": "55c2e04d9ae025ac32c9a435673ecd1d0001d802",
    "src/masck_one/dry_side_harness_service.py": "3214f3ef78de839b0f2f6d427f365eac20293c99",
    "src/masck_one/dry_side_disconnect_interface.py": "aa09c28a5dca54f3fed39af606782b8af64704d2",
    "src/masck_one/warm_cool_package.py": "96bc48a24bc6d1c81afc3540e9930e9e52470ef6",
}

# Current HMI owner interface. The current owner mechanism is explicitly rejected as a
# functional series-force path at V11; exterior therefore consumes only mount/opening
# geometry and does not claim the tactile mechanism is production-ready.
HMI_SOURCE_FILE_BLOB = "5d6b95175000ae3eba58e88306b09b9ba5c76825"
HMI_MOUNT_X_MM = 69.0
HMI_MOUNT_Y_MM = 25.0
HMI_CAP_DIAMETER_MM = 9.72
HMI_BARREL_OD_MM = 12.0
HMI_BORE_DIAMETER_MM = 8.50
HMI_BSIDE_EXTENSION_MM = 1.80
HMI_SHELL_OVERLAP_MM = 0.55

# Treatment owner-derived bounding references only. The owner is still based on an
# older frame head, so these are keepout/depth witnesses rather than assembly material.
TREATMENT_CENTERS_WORLD_MM = (
    (-36.0, 70.0, 7.0),
    (36.0, 70.0, 7.0),
    (-52.0, -45.0, 3.0),
    (52.0, -45.0, 3.0),
)
TREATMENT_AXIS_ANGLE_DEG = 61.0
TREATMENT_BOUND_DIAMETER_MM = 17.4
TREATMENT_LOCAL_AXIAL_SPAN_MM = 17.7

# Integration-owned retention fairing shell. It is a removable cosmetic/service cover,
# not the retention guard, load path, quick release or root itself.
ROOT_FAIRING_OUTER_XYZ_MM = (18.0, 22.0, 16.0)
ROOT_FAIRING_THROUGH_CLEARANCE_XYZ_MM = (14.0, 28.0, 12.0)

MINERAL_IVORY = "#E9E5DC"
WARM_PORCELAIN = "#DED9CF"
SOFT_STONE = "#CFC8BC"
SMOKE_GRAPHITE = "#454542"
OPAL_NEUTRAL = "OPAL_NEUTRAL"

_TOL_MM3 = 1e-7
_REPO_ROOT = Path(__file__).resolve().parents[2]


class WholeProductExteriorError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def require_sources() -> None:
    for relative_path, expected in SOURCE_GIT_BLOBS.items():
        path = _REPO_ROOT / relative_path
        if not path.is_file():
            raise WholeProductExteriorError(f"whole-product exterior source missing: {relative_path}")
        actual = _git_blob_sha(path)
        if actual != expected:
            raise WholeProductExteriorError(
                f"whole-product exterior source moved at {relative_path}; expected {expected}, got {actual}"
            )


def _single(shape: cq.Workplane, label: str) -> cq.Workplane:
    value = shape.val()
    solids = value.Solids()
    if not value.isValid() or len(solids) != 1 or float(solids[0].Volume()) <= 0.0:
        raise WholeProductExteriorError(f"{label} must be one valid positive-volume B-rep solid")
    return shape


def _volume(shape: cq.Workplane) -> float:
    value = shape.val()
    total = math.fsum(float(solid.Volume()) for solid in value.Solids())
    if not math.isfinite(total) or total < 0.0:
        raise WholeProductExteriorError("B-rep volume must be finite and nonnegative")
    return total


def _ivol(first: cq.Workplane, second: cq.Workplane) -> float:
    try:
        value = float(first.val().intersect(second.val()).Volume())
    except Exception:
        return 0.0
    if not math.isfinite(value) or value < 0.0:
        raise WholeProductExteriorError("intersection volume must be finite and nonnegative")
    return 0.0 if value <= _TOL_MM3 else value


def _shape_ivol(first: cq.Shape, second: cq.Workplane) -> float:
    try:
        value = float(first.intersect(second.val()).Volume())
    except Exception:
        return 0.0
    if not math.isfinite(value) or value < 0.0:
        raise WholeProductExteriorError("shape intersection volume must be finite and nonnegative")
    return 0.0 if value <= _TOL_MM3 else value


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    if any(not math.isfinite(float(value)) or float(value) <= 0.0 for value in size):
        raise WholeProductExteriorError("box dimensions must be finite and positive")
    return _single(cq.Workplane("XY").box(*size, centered=(True, True, True)).translate(center), "box")


def _box_from_bounds(bounds: tuple[float, float, float, float, float, float]) -> cq.Workplane:
    xmin, xmax, ymin, ymax, zmin, zmax = (float(value) for value in bounds)
    if not (xmax > xmin and ymax > ymin and zmax > zmin):
        raise WholeProductExteriorError("invalid package bounds")
    return _box(
        (xmax - xmin, ymax - ymin, zmax - zmin),
        ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, (zmin + zmax) / 2.0),
    )


def _protected_prism(zone: object) -> cq.Workplane:
    center = zone.center
    shape = (
        cq.Workplane("XY", origin=(center.x, center.y, -120.0))
        .ellipse(zone.envelope_width_mm / 2.0, zone.envelope_height_mm / 2.0)
        .extrude(240.0)
    )
    if zone.angle_deg:
        shape = shape.rotate(
            (center.x, center.y, 0.0),
            (center.x, center.y, 1.0),
            zone.angle_deg,
        )
    return shape


def _protected_intersections(
    shape: cq.Workplane,
    model: MasckOneModel,
) -> dict[str, float]:
    return {
        item.zone.zone_id: _ivol(shape, _protected_prism(item.zone))
        for item in model.protected_volumes.all
    }


def _treatment_reference(center: tuple[float, float, float]) -> cq.Workplane:
    side_sign = -1.0 if center[0] < 0.0 else 1.0
    theta = math.radians(TREATMENT_AXIS_ANGLE_DEG)
    axis = cq.Vector(side_sign * math.sin(theta), 0.0, math.cos(theta))
    half = TREATMENT_LOCAL_AXIAL_SPAN_MM / 2.0
    start = cq.Vector(
        center[0] - axis.x * half,
        center[1] - axis.y * half,
        center[2] - axis.z * half,
    )
    solid = cq.Solid.makeCylinder(
        TREATMENT_BOUND_DIAMETER_MM / 2.0,
        TREATMENT_LOCAL_AXIAL_SPAN_MM,
        start,
        axis,
    )
    return _single(cq.Workplane("XY").newObject([solid]), "treatment bounding reference")


def _apply_current_frame_joint_tools(
    shell: cq.Workplane,
    shell_joints: object,
) -> cq.Workplane:
    current = shell
    for joint in shell_joints.joints:
        current = current.cut(joint.mortise_tool).cut(joint.pin_bore_tool)
    return _single(current.clean(), "exterior with current frame mortises")


def _hmi_interface(shell: cq.Workplane) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane, dict[str, float]]:
    probe = (
        cq.Workplane("XY")
        .workplane(offset=-100.0)
        .center(HMI_MOUNT_X_MM, HMI_MOUNT_Y_MM)
        .circle(HMI_BARREL_OD_MM / 2.0 + 0.7)
        .extrude(200.0)
    )
    local = shell.intersect(probe)
    if not local.val().Solids() or _volume(local) <= _TOL_MM3:
        raise WholeProductExteriorError("HMI mount does not intersect current exterior material")
    bb = local.val().BoundingBox()
    posterior_z = float(bb.zmin)
    anterior_z = float(bb.zmax)
    if anterior_z - posterior_z <= HMI_SHELL_OVERLAP_MM:
        raise WholeProductExteriorError("HMI mount lacks enough local shell thickness for B-side capture")

    land_front_z = min(
        posterior_z + HMI_SHELL_OVERLAP_MM,
        anterior_z - 0.20,
    )
    if land_front_z <= posterior_z:
        raise WholeProductExteriorError("HMI B-side land would escape the current shell thickness")
    land_z0 = posterior_z - HMI_BSIDE_EXTENSION_MM
    land_height = land_front_z - land_z0
    land = (
        cq.Workplane("XY")
        .workplane(offset=land_z0)
        .center(HMI_MOUNT_X_MM, HMI_MOUNT_Y_MM)
        .circle(HMI_BARREL_OD_MM / 2.0)
        .circle(HMI_BORE_DIAMETER_MM / 2.0)
        .extrude(land_height)
    )
    land = _single(land, "HMI wearer-side reaction land")
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-100.0)
        .center(HMI_MOUNT_X_MM, HMI_MOUNT_Y_MM)
        .circle(HMI_BORE_DIAMETER_MM / 2.0)
        .extrude(200.0)
    )
    combined = _single(shell.union(land).cut(bore).clean(), "exterior with HMI opening and B-side land")

    combined_probe = combined.intersect(probe)
    combined_bb = combined_probe.val().BoundingBox()
    anterior_growth = max(0.0, float(combined_bb.zmax) - anterior_z)
    if anterior_growth > 1e-6:
        raise WholeProductExteriorError("HMI B-side land created a forbidden visible A-surface bulge")

    cap_reference = (
        cq.Workplane("XY")
        .workplane(offset=anterior_z + 0.02)
        .center(HMI_MOUNT_X_MM, HMI_MOUNT_Y_MM)
        .circle(HMI_CAP_DIAMETER_MM / 2.0)
        .extrude(0.66)
    )
    cap_reference = _single(cap_reference, "HMI cap appearance reference")
    return combined, land, cap_reference, {
        "local_posterior_shell_z_mm": posterior_z,
        "local_anterior_shell_z_mm": anterior_z,
        "local_shell_depth_mm": anterior_z - posterior_z,
        "bside_land_posterior_extension_mm": HMI_BSIDE_EXTENSION_MM,
        "bside_land_shell_overlap_mm": land_front_z - posterior_z,
        "visible_anterior_growth_mm": anterior_growth,
    }


def _retention_root_fairing(center: tuple[float, float, float]) -> cq.Workplane:
    outer = _box(ROOT_FAIRING_OUTER_XYZ_MM, center)
    through = _box(ROOT_FAIRING_THROUGH_CLEARANCE_XYZ_MM, center)
    return _single(outer.cut(through).clean(), "retention-root service fairing")


def _rear_cover_candidate(
    *,
    model: MasckOneModel,
    dry_bay: cq.Workplane,
    package_blocked: bool,
) -> cq.Workplane | None:
    if package_blocked:
        return None
    wall = float(model.authority.number("geometry", "shell_nominal_wall_mm"))
    seam = float(model.authority.number("manufacturing", "visible_seam_nominal_gap_mm"))
    xmin, xmax, ymin, ymax, zmin, _zmax = (float(value) for value in DRY_BAY_BOUNDS_WORLD_MM)
    cover = _box(
        (xmax - xmin + 2.0 * seam, ymax - ymin + 2.0 * seam, wall),
        ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, zmin - seam - wall / 2.0),
    )
    if any(value > _TOL_MM3 for value in _protected_intersections(cover, model).values()):
        return None
    return cover


@dataclass(frozen=True, slots=True)
class WholeProductExterior:
    front_shell: cq.Workplane = field(repr=False, compare=False)
    structural_frame: cq.Workplane = field(repr=False, compare=False)
    hmi_bside_land: cq.Workplane = field(repr=False, compare=False)
    hmi_cap_reference: cq.Workplane = field(repr=False, compare=False)
    retention_root_fairings: tuple[cq.Workplane, cq.Workplane] = field(repr=False, compare=False)
    cartridge_body: cq.Workplane = field(repr=False, compare=False)
    cartridge_closure_reveal: cq.Workplane = field(repr=False, compare=False)
    cartridge_service_sweep: cq.Workplane = field(repr=False, compare=False)
    dry_bay_reference: cq.Workplane = field(repr=False, compare=False)
    dry_route_reference: cq.Workplane = field(repr=False, compare=False)
    dry_disconnect_reference: cq.Workplane = field(repr=False, compare=False)
    rear_cover: cq.Workplane | None = field(default=None, repr=False, compare=False)
    treatment_references: tuple[cq.Workplane, ...] = field(default=(), repr=False, compare=False)
    warm_references: tuple[cq.Workplane, ...] = field(default=(), repr=False, compare=False)
    measurements: dict[str, object] = field(default_factory=dict)
    blockers: tuple[str, ...] = ()
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        for label, shape in (
            ("front shell", self.front_shell),
            ("structural frame", self.structural_frame),
            ("HMI B-side land", self.hmi_bside_land),
            ("HMI cap reference", self.hmi_cap_reference),
            ("left retention-root fairing", self.retention_root_fairings[0]),
            ("right retention-root fairing", self.retention_root_fairings[1]),
            ("cartridge body", self.cartridge_body),
            ("cartridge closure reveal", self.cartridge_closure_reveal),
            ("dry bay reference", self.dry_bay_reference),
            ("dry route reference", self.dry_route_reference),
            ("dry disconnect reference", self.dry_disconnect_reference),
        ):
            _single(shape, label)
        if self.rear_cover is not None:
            _single(self.rear_cover, "rear cover")
        if self.physical_validation_eligible is not False:
            raise WholeProductExteriorError("digital whole-product exterior cannot imply physical validation")
        protected = self.measurements.get("physical_exterior_protected_intersections_mm3")
        if not isinstance(protected, dict) or any(float(value) > _TOL_MM3 for value in protected.values()):
            raise WholeProductExteriorError("integration-owned exterior material blocks a protected facial pass-through")
        if float(self.measurements.get("hmi_visible_anterior_growth_mm", math.inf)) > 1e-6:
            raise WholeProductExteriorError("HMI integration must not create a raised exterior bezel or bulge")

    @property
    def architecture_sha256(self) -> str:
        return sha256(
            json.dumps(
                self.manifest(include_sha=False),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "authority_revision": AUTHORITY_REVISION,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "owner_heads": dict(OWNER_HEADS),
            "source_git_blobs": dict(sorted(SOURCE_GIT_BLOBS.items())),
            "source_policy": {
                "exterior_and_frame": "SOURCE_EXACT_LOCAL_COPIES",
                "cartridge_and_dry_side": "SOURCE_EXACT_CURRENT_OWNER_INTERFACE_COPIES_NOT_RELEASE_PROMOTION",
                "hmi": "CURRENT_OWNER_MOUNT_INTERFACE_ONLY_MECHANISM_V11_REJECTED_SERIES_FORCE_PATH",
                "retention_and_treatment": "UNMERGED_STALE_FRAME_ANCESTRY_REFERENCE_ONLY",
                "thermal": "RELEASED_MAIN_WARM_PACKAGE_CONTROLS_WEARABLE_REFERENCE;PR143_IS_BENCH_EVIDENCE_ONLY",
            },
            "manufacturing_components": {
                "EXTERIOR_FRONT_SHELL": {
                    "role": "INTEGRATION_OWNED_CANDIDATE_MATERIAL",
                    "cmf": MINERAL_IVORY,
                    "valid": self.front_shell.val().isValid(),
                    "solid_count": len(self.front_shell.val().Solids()),
                    "volume_mm3": _volume(self.front_shell),
                    "joint": "FIXED_TO_FRAME_VIA_FOUR_CURRENT_SOURCE_BOUND_TENON_MORTISE_PIN_INTERFACES",
                },
                "RETENTION_ROOT_FAIRING_LEFT": {
                    "role": "INTEGRATION_OWNED_REMOVABLE_EXTERIOR_COVER",
                    "cmf": MINERAL_IVORY,
                    "valid": self.retention_root_fairings[0].val().isValid(),
                    "volume_mm3": _volume(self.retention_root_fairings[0]),
                    "service_access": "THROUGH_Y_ROOT_PIN_ACCESS_PRESERVED",
                },
                "RETENTION_ROOT_FAIRING_RIGHT": {
                    "role": "INTEGRATION_OWNED_REMOVABLE_EXTERIOR_COVER",
                    "cmf": MINERAL_IVORY,
                    "valid": self.retention_root_fairings[1].val().isValid(),
                    "volume_mm3": _volume(self.retention_root_fairings[1]),
                    "service_access": "THROUGH_Y_ROOT_PIN_ACCESS_PRESERVED_QUICK_RELEASE_GUARD_REMAINS_OWNER_REFERENCE",
                },
                "WASTE_CARTRIDGE_CLOSURE_REVEAL": {
                    "role": "OWNER_CONTROLLED_CANDIDATE_MATERIAL_SERVICE_REVEAL_NOT_INTEGRATION_PROMOTION",
                    "cmf_direction": MINERAL_IVORY,
                    "secondary_decorative_door_added": False,
                    "visible_seam_nominal_gap_mm": self.measurements["visible_seam_nominal_gap_mm"],
                    "flushness_max_mm": self.measurements["visible_flushness_max_mm"],
                },
                "REAR_DRY_COVER": {
                    "role": "INTEGRATION_OWNED_CANDIDATE_MATERIAL" if self.rear_cover is not None else "BLOCKED_NOT_CREATED",
                    "cmf": MINERAL_IVORY,
                    "reason_if_blocked": "DRY_PACKAGE_REFLOW_REQUIRED_BEFORE_EXTERIOR_GROWTH" if self.rear_cover is None else None,
                },
            },
            "reference_and_owner_geometry": {
                "structural_frame": {
                    "role": "CURRENT_FRAME_OWNER_CANDIDATE_MATERIAL_SEPARATE_FROM_EXTERIOR",
                    "cmf_direction": SMOKE_GRAPHITE,
                },
                "hmi_cap": {
                    "role": "APPEARANCE_REFERENCE_ONLY_CURRENT_OWNER_FUNCTIONAL_ARCHITECTURE_REJECTED",
                    "cmf_direction": WARM_PORCELAIN,
                    "optical_detail": OPAL_NEUTRAL,
                    "visible_bezel_added": False,
                },
                "treatment": {
                    "role": "OWNER_DERIVED_DEPTH_AND_KEEPOUT_REFERENCE_ONLY",
                    "local_axial_span_mm": TREATMENT_LOCAL_AXIAL_SPAN_MM,
                    "bound_diameter_mm": TREATMENT_BOUND_DIAMETER_MM,
                    "axis_angle_deg": TREATMENT_AXIS_ANGLE_DEG,
                },
                "warm": {
                    "role": "RELEASED_MAIN_PACKAGE_REFERENCE_ONLY",
                    "physical_validation": False,
                },
                "dry_side": {
                    "role": "CURRENT_OWNER_PACKAGE_ROUTE_AND_DISCONNECT_REFERENCE_ONLY",
                    "full_rear_skin_not_permitted_until_complete_package_is_protected_clear",
                },
                "compliant_interface": {
                    "cmf_direction": SOFT_STONE,
                    "role": "REFERENCE_ONLY_FINAL_MATERIAL_AND_JOIN_UNRESOLVED",
                },
            },
            "surface_language": {
                "perceived_thinness": "NO_NEW_ANTERIOR_VOLUME_FROM_HMI;PACKAGE_REFLOW_PRECEDES_REAR_SKIN_GROWTH",
                "eye_treatment": "NEUTRAL_HARD_OPENING_WITH_3MM_INNER_ROLL_NO_BEZEL",
                "airway": "RELEASED_EYE_MOUTH_NOSTRIL_PROTECTED_PASS_THROUGHS_REMAIN_UNOBSTRUCTED_BY_INTEGRATION_OWNED_MATERIAL",
                "panelization": "FRONT_SHELL_PLUS_TWO_ROOT_FAIRINGS_PLUS_OWNER_CARTRIDGE_CLOSURE_REVEAL;NO_RANDOM_PANEL_BREAKS",
                "prohibited_cues": ["VR_BEZEL", "MEDICAL_PORT_DECORATION", "ROBOTIC_VENTS", "CYBERPUNK_PANELIZATION", "RANDOM_BULGES"],
            },
            "b_side_and_tooling": {
                "shell_nominal_wall_mm": self.measurements["shell_nominal_wall_mm"],
                "mold_draft_nominal_deg": self.measurements["mold_draft_nominal_deg"],
                "visible_seam_nominal_gap_mm": self.measurements["visible_seam_nominal_gap_mm"],
                "visible_seam_tolerance_mm": self.measurements["visible_seam_tolerance_mm"],
                "visible_flushness_max_mm": self.measurements["visible_flushness_max_mm"],
                "realized_bside_features": ["FOUR_FRAME_MORTISES", "FOUR_TRANSVERSE_PIN_BORES", "HMI_12MM_OD_REACTION_LAND", "HMI_8P5MM_THROUGH_BORE"],
                "tooling_status": "DIGITAL_PART_SPLIT_AND_BSIDE_GEOMETRY_ONLY_DRAFT_SHUTOFF_EJECTION_PROCESS_CAPABILITY_PHYSICAL_REVIEW_REQUIRED",
            },
            "measurements": self.measurements,
            "blockers": list(self.blockers),
            "whole_product_freeze_eligible": len(self.blockers) == 0,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": "DIGITAL_BREP_INTERFACE_AND_COLLISION_EVIDENCE_ONLY_NOT_FIT_COMFORT_LEAKAGE_THERMAL_HYGIENE_DURABILITY_ACOUSTIC_OR_PRODUCTION_VALIDATION",
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_whole_product_exterior(*, model: MasckOneModel | None = None) -> WholeProductExterior:
    require_sources()
    model = build_model() if model is None else model
    if type(model) is not MasckOneModel:
        raise WholeProductExteriorError("exact MasckOneModel type required")
    if str(model.authority.get("project", "authority_revision")) != AUTHORITY_REVISION:
        raise WholeProductExteriorError("engineering authority moved")

    # 1. Strongest accepted calm A-surface, then exact current frame-side joint tools.
    donor_shell = build_eye_rolled_exterior_shell(
        model.authority,
        model.facial_reference,
        model.protected_volumes,
    )
    donor_shell = _single(donor_shell, "source-exact calm exterior donor")
    donor_front_z = float(donor_shell.val().BoundingBox().zmax)

    shell_joints = build_structural_frame_shell_joints(model=model)
    shell_with_frame_interfaces = _apply_current_frame_joint_tools(donor_shell, shell_joints)
    reactions = build_structural_frame_actuator_reactions(model=model, shell_joints=shell_joints)
    roots = build_structural_frame_retention_roots(model=model, reactions=reactions)
    structural_frame = _single(roots.frame_with_retention_roots, "current structural frame with retention roots")

    # 2. HMI: smallest current-owner bore and completely B-side reaction land. No bezel.
    front_shell, hmi_land, hmi_cap_reference, hmi_metrics = _hmi_interface(shell_with_frame_interfaces)
    if float(front_shell.val().BoundingBox().zmax) - donor_front_z > 1e-6:
        raise WholeProductExteriorError("whole-product exterior gained forbidden anterior thickness")

    # 3. Root fairings are compact service covers, not a new retention mechanism.
    fairings = tuple(
        _retention_root_fairing(tuple(root.center_xyz_mm))
        for root in roots.roots
    )
    if len(fairings) != 2:
        raise WholeProductExteriorError("bilateral retention-root fairings required")

    # 4. Actual cartridge owner geometry supplies the service reveal. No decorative door.
    cartridge = build_realized_waste_cartridge(model=model)
    cartridge.validate()
    service_report, service_refs = build_service_corridor(cartridge)
    service_sweep = service_refs["oblique_service_sweeps"]

    # 5. Current dry-side geometry is consumed as package/reference geometry. Broad bay
    # containment is not allowed to force an exterior backpack or facial blockage.
    dry_harness = build_dry_side_harness_service()
    dry_disconnect = build_battery_disconnect_interface()
    dry_bay = _box_from_bounds(tuple(DRY_BAY_BOUNDS_WORLD_MM))
    dry_package_protected = _protected_intersections(dry_bay, model)
    dry_route_protected = _protected_intersections(dry_harness.route_envelope, model)
    dry_disconnect_protected = _protected_intersections(dry_disconnect.disconnect_service_sweep, model)
    dry_package_blocked = any(value > _TOL_MM3 for value in dry_package_protected.values())
    rear_cover = _rear_cover_candidate(model=model, dry_bay=dry_bay, package_blocked=dry_package_blocked)

    # 6. Treatment depth and released WARM package stay separate reference classes.
    treatment_refs = tuple(_treatment_reference(center) for center in TREATMENT_CENTERS_WORLD_MM)
    warm = build_warm_cool_package(model.authority)
    warm_refs = (warm.warm_left.solid, warm.warm_right.solid, warm.dock_heat_rejection_interface.solid)

    # Integration-owned exterior material is shell + removable root fairings + optional
    # rear cover only. Owner cartridge closure is reported separately and never silently
    # fused into this lane's material truth.
    integration_material = (front_shell, *fairings)
    if rear_cover is not None:
        integration_material = (*integration_material, rear_cover)

    protected_totals: dict[str, float] = {}
    for item in model.protected_volumes.all:
        keepout = _protected_prism(item.zone)
        protected_totals[item.zone.zone_id] = math.fsum(
            _ivol(shape, keepout) for shape in integration_material
        )
    if any(value > _TOL_MM3 for value in protected_totals.values()):
        raise WholeProductExteriorError("integration-owned exterior blocks protected eye/mouth/airway geometry")

    frame_shell_intersection = _ivol(front_shell, structural_frame)
    fairing_frame_intersections = tuple(_ivol(fairing, structural_frame) for fairing in fairings)
    cartridge_shell_intersection = math.fsum(
        _ivol(shape, front_shell) for shape in (cartridge.body_solid, cartridge.closure_solid)
    )
    cartridge_frame_intersection = math.fsum(
        _ivol(shape, structural_frame) for shape in (cartridge.body_solid, cartridge.closure_solid)
    )
    service_shell_intersection = _ivol(service_sweep, front_shell)
    service_frame_intersection = _ivol(service_sweep, structural_frame)

    treatment_shell_intersections = tuple(_ivol(reference, front_shell) for reference in treatment_refs)
    treatment_frame_intersections = tuple(_ivol(reference, structural_frame) for reference in treatment_refs)
    warm_shell_intersections = tuple(_ivol(reference, front_shell) for reference in warm_refs)
    warm_frame_intersections = tuple(_ivol(reference, structural_frame) for reference in warm_refs)
    warm_treatment_intersections = tuple(
        math.fsum(_ivol(warm_reference, treatment) for treatment in treatment_refs)
        for warm_reference in warm_refs[:2]
    )

    blockers: list[str] = []
    if frame_shell_intersection > _TOL_MM3:
        blockers.append("CURRENT_FRAME_STILL_INTERSECTS_RECONSTRUCTED_EXTERIOR_AFTER_EXACT_JOINT_TOOLS")
    if any(value > _TOL_MM3 for value in fairing_frame_intersections):
        blockers.append("RETENTION_ROOT_FAIRING_CLEARANCE_REQUIRES_LOCAL_BSIDE_REPAIR")
    if cartridge_shell_intersection > _TOL_MM3:
        blockers.append("CURRENT_CARTRIDGE_MATERIAL_INTERSECTS_RECONSTRUCTED_EXTERIOR")
    if cartridge_frame_intersection > _TOL_MM3:
        blockers.append("CURRENT_CARTRIDGE_MATERIAL_INTERSECTS_REAL_FRAME")
    if service_shell_intersection > _TOL_MM3:
        blockers.append("CARTRIDGE_SERVICE_SWEEP_INTERSECTS_RECONSTRUCTED_EXTERIOR")
    if service_frame_intersection > _TOL_MM3:
        blockers.append("CARTRIDGE_SERVICE_SWEEP_INTERSECTS_REAL_FRAME")
    if dry_package_blocked:
        blockers.append("DRY_BAY_PACKAGE_REFLOW_REQUIRED_BEFORE_REAR_SKIN")
    if any(value > _TOL_MM3 for value in treatment_shell_intersections):
        blockers.append("TREATMENT_OWNER_DEPTH_REFERENCE_INTERSECTS_EXTERIOR_REBIND_OR_REFLOW_REQUIRED")
    if any(value > _TOL_MM3 for value in treatment_frame_intersections):
        blockers.append("TREATMENT_OWNER_DEPTH_REFERENCE_INTERSECTS_CURRENT_FRAME_REBIND_REQUIRED")
    if any(value > _TOL_MM3 for value in warm_shell_intersections):
        blockers.append("RELEASED_WARM_PACKAGE_INTERSECTS_EXTERIOR_REFLOW_REQUIRED")
    if any(value > _TOL_MM3 for value in warm_frame_intersections):
        blockers.append("RELEASED_WARM_PACKAGE_INTERSECTS_CURRENT_FRAME_REFLOW_REQUIRED")
    if any(value > _TOL_MM3 for value in warm_treatment_intersections):
        blockers.append("WARM_AND_TREATMENT_PACKAGE_REFERENCES_OVERLAP_INTERNAL_REFLOW_REQUIRED")
    if OWNER_HEADS["treatment_pr135"] and True:
        blockers.append("TREATMENT_PR135_STILL_BASED_ON_OBSOLETE_FRAME_HEAD_NOT_PROMOTABLE")
    if OWNER_HEADS["retention_pr141"] and True:
        blockers.append("RETENTION_PR141_STILL_BASED_ON_OBSOLETE_FRAME_HEAD_GUARD_REMAINS_REFERENCE_ONLY")
    blockers.append("HMI_V11_CURRENT_OWNER_SERIES_FORCE_PATH_REJECTED_EXTERIOR_INTERFACE_ONLY")
    blockers.append("DRY_SIDE_FULL_BATTERY_PCB_ENCLOSURE_MATERIAL_NOT_RELEASED")
    blockers.append("PHYSICAL_CLEANABILITY_WET_USE_SEALING_FEEL_THERMAL_COMFORT_AND_TOOLING_VALIDATION_REQUIRED")

    manufacturing = model.authority.data.get("manufacturing", {})
    measurements: dict[str, object] = {
        "shell_nominal_wall_mm": float(model.authority.number("geometry", "shell_nominal_wall_mm")),
        "mold_draft_nominal_deg": float(manufacturing.get("mold_draft_nominal_deg", 1.0)),
        "visible_seam_nominal_gap_mm": float(manufacturing.get("visible_seam_nominal_gap_mm", 0.40)),
        "visible_seam_tolerance_mm": float(manufacturing.get("visible_seam_tolerance_mm", 0.15)),
        "visible_flushness_max_mm": float(manufacturing.get("visible_flushness_max_mm", 0.15)),
        "hmi_owner_head_sha": OWNER_HEADS["hmi_pr144"],
        "hmi_source_file_blob": HMI_SOURCE_FILE_BLOB,
        "hmi_mount_xy_mm": [HMI_MOUNT_X_MM, HMI_MOUNT_Y_MM],
        "hmi_barrel_od_mm": HMI_BARREL_OD_MM,
        "hmi_bore_diameter_mm": HMI_BORE_DIAMETER_MM,
        "hmi_visible_anterior_growth_mm": hmi_metrics["visible_anterior_growth_mm"],
        "hmi_local_shell_interface": hmi_metrics,
        "front_shell_volume_mm3": _volume(front_shell),
        "front_shell_frame_intersection_mm3": frame_shell_intersection,
        "retention_fairing_frame_intersections_mm3": list(fairing_frame_intersections),
        "physical_exterior_protected_intersections_mm3": protected_totals,
        "cartridge_owner_service_report_status": service_report["status"],
        "cartridge_material_front_shell_intersection_mm3": cartridge_shell_intersection,
        "cartridge_material_frame_intersection_mm3": cartridge_frame_intersection,
        "cartridge_service_sweep_front_shell_intersection_mm3": service_shell_intersection,
        "cartridge_service_sweep_frame_intersection_mm3": service_frame_intersection,
        "cartridge_service_translation_world_mm": service_report["translation_world_mm"],
        "cartridge_closure_is_service_reveal": True,
        "secondary_cartridge_door_added": False,
        "dry_bay_bounds_world_mm": list(DRY_BAY_BOUNDS_WORLD_MM),
        "dry_bay_protected_intersections_mm3": dry_package_protected,
        "dry_route_protected_intersections_mm3": dry_route_protected,
        "dry_disconnect_sweep_protected_intersections_mm3": dry_disconnect_protected,
        "rear_cover_created": rear_cover is not None,
        "treatment_reference_shell_intersections_mm3": list(treatment_shell_intersections),
        "treatment_reference_frame_intersections_mm3": list(treatment_frame_intersections),
        "warm_reference_shell_intersections_mm3": list(warm_shell_intersections),
        "warm_reference_frame_intersections_mm3": list(warm_frame_intersections),
        "warm_treatment_reference_intersections_mm3": list(warm_treatment_intersections),
        "front_a_surface_policy": eye_inner_roll_manifest(model.authority),
    }

    candidate = WholeProductExterior(
        front_shell=front_shell,
        structural_frame=structural_frame,
        hmi_bside_land=hmi_land,
        hmi_cap_reference=hmi_cap_reference,
        retention_root_fairings=(fairings[0], fairings[1]),
        cartridge_body=cartridge.body_solid,
        cartridge_closure_reveal=cartridge.closure_solid,
        cartridge_service_sweep=service_sweep,
        dry_bay_reference=dry_bay,
        dry_route_reference=dry_harness.route_envelope,
        dry_disconnect_reference=dry_disconnect.disconnect_service_sweep,
        rear_cover=rear_cover,
        treatment_references=treatment_refs,
        warm_references=warm_refs,
        measurements=measurements,
        blockers=tuple(dict.fromkeys(blockers)),
        physical_validation_eligible=False,
    )
    candidate.__post_init__()
    return candidate
