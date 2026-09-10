from __future__ import annotations

"""Primary-control V10: positive outward capture plus a rooted soft return datum.

V9 protects the tactile element during the press, but nominal return still lacked an
explicit hierarchy between the compliant rest seat and a positive pull-out stop. V10
adds that hierarchy without tightening the precision guides.

A shell-captured diaphragm outer bead is represented with separate manufactured-free
and installed/deformed geometry. Its membrane supplies only a low-rate axial return
bias and compliant nominal rest datum; it does not guide the stem. A one-piece rear
polymer capture flange on the moving stem sits behind the lower guide with deliberate
clearance. Normal return therefore ends on the compliant diaphragm datum first, while
an abnormal outward pull is arrested mechanically by the lower guide.

Return force, seal compression, friction, rebound, noise, wear and subjective feel
remain physical validation. Free manufactured elastomer and installed/deformed
reference geometry remain explicitly separate.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v9 as v9
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V10"
SOURCE_MAIN_SHA = v9.SOURCE_MAIN_SHA

CAPTURE_FLANGE_OD_MM = 7.70
CAPTURE_FLANGE_ID_MM = v9.PLUNGER_SHAFT_BORE_DIAMETER_MM
CAPTURE_FLANGE_THICKNESS_MM = 0.10
NOMINAL_CAPTURE_CLEARANCE_MM = 0.04
HOSTILE_OVERPULL_MM = NOMINAL_CAPTURE_CLEARANCE_MM + 0.02
MIN_CAPTURE_HOSTILE_INTERSECTION_MM3 = 0.005

DIAPHRAGM_GROOVE_OD_MM = 10.90
DIAPHRAGM_GROOVE_ID_MM = 8.55
DIAPHRAGM_GROOVE_HEIGHT_MM = 0.36
DIAPHRAGM_GROOVE_Z0_FROM_REST_MM = -0.22
INSTALLED_DIAPHRAGM_MEMBRANE_THICKNESS_MM = 0.16
INSTALLED_DIAPHRAGM_OUTER_BEAD_HEIGHT_MM = 0.34
INSTALLED_DIAPHRAGM_INNER_BEAD_HEIGHT_MM = 0.34
INSTALLED_DIAPHRAGM_OUTER_BEAD_Z0_FROM_REST_MM = -0.21
INSTALLED_DIAPHRAGM_INNER_BEAD_Z0_FROM_REST_MM = -0.34
FREE_TO_INSTALLED_MEMBRANE_COMPRESSION_SEED_MM = (
    v1.DIAPHRAGM_MEMBRANE_THICKNESS_MM - INSTALLED_DIAPHRAGM_MEMBRANE_THICKNESS_MM
)
MIN_GROOVE_LIGAMENT_TO_BARREL_OD_MM = 0.45
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV10Error(ValueError):
    pass


def _capture_flange(rest_z: float) -> cq.Shape:
    trim_z = rest_z - v9.STEM_REAR_FROM_REST_MM
    flange = v1._ring(
        CAPTURE_FLANGE_OD_MM,
        CAPTURE_FLANGE_ID_MM,
        CAPTURE_FLANGE_THICKNESS_MM,
        trim_z,
    )
    if not flange.isValid() or len(flange.Solids()) != 1 or flange.Volume() <= 0.0:
        raise PrimaryControlHapticV10Error("capture flange must be one positive ring")
    return flange


def _add_capture_flange(moving: cq.Shape, rest_z: float) -> tuple[cq.Shape, float]:
    flange = _capture_flange(rest_z)
    overlap = v1._intersection_volume(moving, flange)
    moving = moving.fuse(flange).clean()
    if not moving.isValid() or len(moving.Solids()) != 1 or moving.Volume() <= 0.0:
        raise PrimaryControlHapticV10Error("capture flange must remain integral with moving polymer")
    if overlap <= 0.0:
        raise PrimaryControlHapticV10Error("capture flange requires positive root overlap with moving stem")
    return moving, overlap


def _cut_diaphragm_reaction_groove(shell: cq.Shape, rest_z: float) -> tuple[cq.Shape, float]:
    groove_z0 = rest_z + DIAPHRAGM_GROOVE_Z0_FROM_REST_MM
    groove = v1._ring(
        DIAPHRAGM_GROOVE_OD_MM,
        DIAPHRAGM_GROOVE_ID_MM,
        DIAPHRAGM_GROOVE_HEIGHT_MM,
        groove_z0,
    )
    before = float(shell.Volume())
    shell = shell.cut(groove).clean()
    removed = before - float(shell.Volume())
    if not shell.isValid() or not shell.Solids() or removed <= 0.0:
        raise PrimaryControlHapticV10Error("diaphragm reaction groove must remove positive shell material")
    return shell, removed


def _installed_diaphragm_reference(rest_z: float) -> cq.Shape:
    membrane_z0 = rest_z - 0.16
    membrane = v1._ring(
        v1.DIAPHRAGM_OD_MM,
        v1.DIAPHRAGM_ID_MM,
        INSTALLED_DIAPHRAGM_MEMBRANE_THICKNESS_MM,
        membrane_z0,
    )
    outer_bead = v1._ring(
        v1.DIAPHRAGM_OD_MM + 0.28,
        v1.DIAPHRAGM_OD_MM - 0.45,
        INSTALLED_DIAPHRAGM_OUTER_BEAD_HEIGHT_MM,
        rest_z + INSTALLED_DIAPHRAGM_OUTER_BEAD_Z0_FROM_REST_MM,
    )
    inner_bead = v1._ring(
        v1.DIAPHRAGM_ID_MM + 0.48,
        v1.STEM_DIAMETER_MM,
        INSTALLED_DIAPHRAGM_INNER_BEAD_HEIGHT_MM,
        rest_z + INSTALLED_DIAPHRAGM_INNER_BEAD_Z0_FROM_REST_MM,
    )
    diaphragm = membrane.fuse(outer_bead).fuse(inner_bead).clean()
    if not diaphragm.isValid() or len(diaphragm.Solids()) != 1 or diaphragm.Volume() <= 0.0:
        raise PrimaryControlHapticV10Error("installed diaphragm reference must be one connected solid")
    return diaphragm


def _replace_material_parts(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    shell: cq.Shape,
    moving: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    saw_shell = False
    saw_moving = False
    for name, shape in parts:
        if name == "shell_with_primary_control_interface":
            output.append((name, shell))
            saw_shell = True
        elif name == "primary_control_cap_stem":
            output.append((name, moving))
            saw_moving = True
        else:
            output.append((name, shape))
    if not saw_shell or not saw_moving:
        raise PrimaryControlHapticV10Error("V10 requires donor shell and moving component")
    return tuple(output)


def _replace_motion_reference(
    parts: tuple[tuple[str, cq.Shape], ...],
    *,
    motion: cq.Shape,
    installed_diaphragm: cq.Shape,
) -> tuple[tuple[str, cq.Shape], ...]:
    output: list[tuple[str, cq.Shape]] = []
    saw_motion = False
    for name, shape in parts:
        if name == "cap_motion_sweep":
            output.append((name, motion))
            saw_motion = True
        else:
            output.append((name, shape))
    if not saw_motion:
        raise PrimaryControlHapticV10Error("V10 requires donor cap motion reference")
    output.append(("wet_diaphragm_installed_return_reference", installed_diaphragm))
    return tuple(output)


def _motion_with_capture_flange(base_motion: cq.Shape, rest_z: float) -> cq.Shape:
    trim_z = rest_z - v9.STEM_REAR_FROM_REST_MM
    flange_sweep = v1._ring(
        CAPTURE_FLANGE_OD_MM,
        CAPTURE_FLANGE_ID_MM,
        CAPTURE_FLANGE_THICKNESS_MM + v1.HARD_STOP_MM,
        trim_z - v1.HARD_STOP_MM,
    )
    return cq.Compound.makeCompound([base_motion, flange_sweep])


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV10:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    capture_flange_root_overlap_mm3: float = 0.0
    capture_rest_bushing_intersection_mm3: float = 0.0
    capture_at_nominal_limit_intersection_mm3: float = 0.0
    capture_hostile_overpull_intersection_mm3: float = 0.0
    diaphragm_groove_removed_mm3: float = 0.0
    installed_diaphragm_shell_intersection_mm3: float = 0.0
    installed_diaphragm_moving_intersection_mm3: float = 0.0
    groove_outer_ligament_mm: float = 0.0
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV10Error("V10 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV10Error("digital rest/capture geometry is not physical validation")
        if self.capture_flange_root_overlap_mm3 <= 0.0:
            raise PrimaryControlHapticV10Error("capture flange must be integrally rooted")
        if self.capture_rest_bushing_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV10Error("capture flange collides with lower guide at nominal rest")
        if self.capture_at_nominal_limit_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV10Error("capture limit should resolve at contact without positive overlap")
        if self.capture_hostile_overpull_intersection_mm3 < MIN_CAPTURE_HOSTILE_INTERSECTION_MM3:
            raise PrimaryControlHapticV10Error("hostile outward pull does not engage positive lower-guide capture")
        if self.diaphragm_groove_removed_mm3 <= 0.0:
            raise PrimaryControlHapticV10Error("diaphragm outer bead lacks shell reaction groove")
        if self.installed_diaphragm_shell_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV10Error("installed diaphragm reference collides with rigid shell")
        if self.installed_diaphragm_moving_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise PrimaryControlHapticV10Error("installed diaphragm reference has positive rigid moving overlap")
        if self.groove_outer_ligament_mm < MIN_GROOVE_LIGAMENT_TO_BARREL_OD_MM:
            raise PrimaryControlHapticV10Error("diaphragm groove leaves insufficient outer barrel ligament")
        if FREE_TO_INSTALLED_MEMBRANE_COMPRESSION_SEED_MM <= 0.0:
            raise PrimaryControlHapticV10Error("return seat requires positive free-to-installed compression seed")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV10Error("V10 primary-control module intersects released package keepout")
        refs = dict(self.reference_parts)
        if "wet_diaphragm_installed_return_reference" not in refs:
            raise PrimaryControlHapticV10Error("installed/deformed diaphragm reference is missing")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": self.source_main_sha,
            "supersedes": "V9_RETURN_WITHOUT_EXPLICIT_POSITIVE_OUTWARD_CAPTURE_AND_ROOTED_COMPLIANT_REST_DATUM",
            "return_hierarchy": {
                "normal_return": "ROOTED_COMPLIANT_DIAPHRAGM_MEMBRANE_DATUM",
                "abnormal_outward_capture": "INTEGRAL_REAR_STEM_FLANGE_BEHIND_LOWER_GUIDE",
                "capture_flange_od_mm": CAPTURE_FLANGE_OD_MM,
                "nominal_capture_clearance_mm": NOMINAL_CAPTURE_CLEARANCE_MM,
                "free_to_installed_membrane_compression_seed_mm": FREE_TO_INSTALLED_MEMBRANE_COMPRESSION_SEED_MM,
                "capture_flange_root_overlap_mm3": self.capture_flange_root_overlap_mm3,
                "rest_bushing_intersection_mm3": self.capture_rest_bushing_intersection_mm3,
                "nominal_limit_intersection_mm3": self.capture_at_nominal_limit_intersection_mm3,
                "hostile_overpull_intersection_mm3": self.capture_hostile_overpull_intersection_mm3,
            },
            "diaphragm": {
                "manufactured_free_geometry": "wet_diaphragm",
                "installed_deformed_reference": "wet_diaphragm_installed_return_reference",
                "outer_bead_shell_reaction_groove_removed_mm3": self.diaphragm_groove_removed_mm3,
                "installed_shell_intersection_mm3": self.installed_diaphragm_shell_intersection_mm3,
                "installed_moving_intersection_mm3": self.installed_diaphragm_moving_intersection_mm3,
                "groove_outer_ligament_mm": self.groove_outer_ligament_mm,
                "guidance_role": "NONE_AXIAL_RETURN_AND_WET_BARRIER_ONLY",
            },
            "tactile_sequence": (
                "LOW_SLACK_DUAL_GUIDANCE -> DOME_FORCE_BUILD_AND_BREAK -> PROTECTED_LOST_MOTION -> "
                "PROGRESSIVE_ELASTOMER_LANDING -> CONTROLLED_DIAPHRAGM_RETURN -> SOFT_REST_DATUM"
            ),
            "cost_rule": (
                "CAPTURE_FLANGE_IS_INTEGRAL_MOVING_POLYMER; DIAPHRAGM_ALREADY_REQUIRED_FOR_WET_BARRIER; "
                "ZERO_EXTRA_REST_FASTENER_ZERO_EXTRA_RETURN_SPRING"
            ),
            "tactile_reference_rule": "S_T_DUPONT_LIGNE_2_PRECISION_FEEL_ONLY_NOT_SOUND_OR_MECHANISM_COPY",
            "keepout_intersections_mm3": self.keepout_intersections_mm3,
            "material_parts": [name for name, _shape in self.material_parts],
            "reference_parts": [name for name, _shape in self.reference_parts],
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_DIAPHRAGM_MATERIAL_DUROMETER_RETURN_FORCE_RATE_HYSTERESIS_COMPRESSION_SET_SEAL_LEAKAGE_"
                "CAPTURE_IMPACT_ABUSE_PULL_FORCE_GUIDE_FRICTION_WOBBLE_REBOUND_RETURN_TIME_SOUND_WET_AGING_"
                "LIFETIME_AND_SUBJECTIVE_FEEL"
            ),
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_primary_control_haptic_architecture_v10(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV10:
    model = build_model() if model is None else model
    base = v9.build_primary_control_haptic_architecture_v9(model=model)
    base.__post_init__()
    material = dict(base.material_parts)
    refs = dict(base.reference_parts)

    moving, flange_root_overlap = _add_capture_flange(
        material["primary_control_cap_stem"],
        base.rest_cap_underside_z_mm,
    )
    shell, groove_removed = _cut_diaphragm_reaction_groove(
        material["shell_with_primary_control_interface"],
        base.rest_cap_underside_z_mm,
    )
    installed_diaphragm = _installed_diaphragm_reference(base.rest_cap_underside_z_mm)

    material_parts = _replace_material_parts(base.material_parts, shell=shell, moving=moving)
    motion = _motion_with_capture_flange(base.motion_sweep, base.rest_cap_underside_z_mm)
    reference_parts = _replace_motion_reference(
        base.reference_parts,
        motion=motion,
        installed_diaphragm=installed_diaphragm,
    )

    lower_guide = refs["lower_split_bushing_installed_reference"]
    flange = _capture_flange(base.rest_cap_underside_z_mm)
    capture_rest = v1._intersection_volume(flange, lower_guide)
    capture_limit = v1._intersection_volume(
        flange.translate((0.0, 0.0, NOMINAL_CAPTURE_CLEARANCE_MM)),
        lower_guide,
    )
    capture_hostile = v1._intersection_volume(
        flange.translate((0.0, 0.0, HOSTILE_OVERPULL_MM)),
        lower_guide,
    )

    installed_shell_overlap = v1._intersection_volume(installed_diaphragm, shell)
    installed_moving_overlap = v1._intersection_volume(installed_diaphragm, moving)
    groove_outer_ligament = (
        v1.BARREL_OD_MM / 2.0 - DIAPHRAGM_GROOVE_OD_MM / 2.0
    )

    # The new flange sits inside the existing barrel and the diaphragm groove is
    # subtractive. Re-run module keepouts with the modified moving part anyway.
    keepouts = v9._module_keepouts(model, material_parts, reference_parts)

    result = PrimaryControlHapticArchitectureV10(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        reference_parts,
        motion,
        round(flange_root_overlap, 9),
        round(capture_rest, 9),
        round(capture_limit, 9),
        round(capture_hostile, 9),
        round(groove_removed, 9),
        round(installed_shell_overlap, 9),
        round(installed_moving_overlap, 9),
        round(groove_outer_ligament, 9),
        keepouts,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v10(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v10()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v10_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
