from __future__ import annotations

"""Primary-control V4: shell-fixed, physically consistent split guide bushings.

V3 repaired the moving cap/stem/rib into one manufactured solid. V4 closes the next
high-value tactile defect: the donor guide sleeves floated inside the barrel and its
free/installed diameters implied nonphysical wall-thickness loss.

The selected low-cost architecture is a pair of molded low-friction split sleeves.
Each sleeve expands over the stem while preserving nominal wall thickness, bringing
its journal into the 8.50 mm shell bore. Shallow end flanges snap into shell-integral
annular capture grooves so the guide datum is shell-fixed instead of riding with the
button. Friction, wear, creep, insertion force and subjective wobble still require
physical validation.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from . import primary_control_haptic as v1
from . import primary_control_haptic_v3 as v3
from .model import MasckOneModel, build_model

SCHEMA = "MASCK_ONE_PRIMARY_CONTROL_HAPTIC_V4"
SOURCE_MAIN_SHA = v3.SOURCE_MAIN_SHA

BUSHING_FREE_ID_MM = 7.10
BUSHING_INSTALLED_ID_MM = v1.STEM_DIAMETER_MM
BUSHING_FREE_JOURNAL_OD_MM = 8.42
BUSHING_INSTALLED_JOURNAL_OD_MM = v1.BARREL_BORE_DIAMETER_MM
BUSHING_FREE_FLANGE_OD_MM = 8.62
BUSHING_INSTALLED_FLANGE_OD_MM = 8.70
BUSHING_CAPTURE_GROOVE_OD_MM = 8.72
BUSHING_FLANGE_THICKNESS_MM = 0.10
BUSHING_CAPTURE_GROOVE_HEIGHT_MM = 0.12
BUSHING_CAPTURE_GROOVE_END_CLEARANCE_MM = 0.01
BUSHING_FREE_SPLIT_GAP_MM = v1.BUSHING_SPLIT_GAP_MM
BUSHING_INSTALLED_SPLIT_GAP_MM = BUSHING_FREE_SPLIT_GAP_MM + math.pi * (
    BUSHING_INSTALLED_ID_MM - BUSHING_FREE_ID_MM
)
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class PrimaryControlHapticV4Error(ValueError):
    pass


def _split_flanged_sleeve(
    *,
    journal_od_mm: float,
    flange_od_mm: float,
    id_mm: float,
    z0_mm: float,
    split_gap_mm: float,
) -> cq.Shape:
    journal = v1._ring(journal_od_mm, id_mm, v1.BUSHING_LENGTH_MM, z0_mm)
    lower_flange = v1._ring(
        flange_od_mm,
        id_mm,
        BUSHING_FLANGE_THICKNESS_MM,
        z0_mm,
    )
    upper_flange = v1._ring(
        flange_od_mm,
        id_mm,
        BUSHING_FLANGE_THICKNESS_MM,
        z0_mm + v1.BUSHING_LENGTH_MM - BUSHING_FLANGE_THICKNESS_MM,
    )
    sleeve = journal.fuse(lower_flange).fuse(upper_flange)
    slot = v1._box(
        flange_od_mm + 0.30,
        split_gap_mm,
        v1.BUSHING_LENGTH_MM + 0.20,
        (
            v1.MOUNT_X_MM + flange_od_mm / 2.0,
            v1.MOUNT_Y_MM,
            z0_mm + v1.BUSHING_LENGTH_MM / 2.0,
        ),
    )
    sleeve = sleeve.cut(slot).clean()
    if not sleeve.isValid() or len(sleeve.Solids()) != 1 or sleeve.Volume() <= 0.0:
        raise PrimaryControlHapticV4Error("split flanged bushing must remain one positive C-sleeve")
    return sleeve


def _cut_capture_grooves(shell: cq.Shape, z0_mm: float) -> tuple[cq.Shape, float]:
    before = float(shell.Volume())
    lower_z0 = z0_mm - BUSHING_CAPTURE_GROOVE_END_CLEARANCE_MM
    upper_z0 = (
        z0_mm
        + v1.BUSHING_LENGTH_MM
        - BUSHING_FLANGE_THICKNESS_MM
        - BUSHING_CAPTURE_GROOVE_END_CLEARANCE_MM
    )
    for groove_z0 in (lower_z0, upper_z0):
        cutter = v1._cylinder(
            BUSHING_CAPTURE_GROOVE_OD_MM,
            BUSHING_CAPTURE_GROOVE_HEIGHT_MM,
            groove_z0,
        )
        shell = shell.cut(cutter).clean()
    removed = before - float(shell.Volume())
    if not shell.isValid() or not shell.Solids() or removed <= 0.0:
        raise PrimaryControlHapticV4Error("bushing capture grooves must remove positive shell material")
    return shell, removed


def _replace_named(
    parts: tuple[tuple[str, cq.Shape], ...],
    replacements: dict[str, cq.Shape],
) -> tuple[tuple[str, cq.Shape], ...]:
    names = {name for name, _shape in parts}
    missing = set(replacements) - names
    if missing:
        raise PrimaryControlHapticV4Error(f"cannot replace absent parts: {sorted(missing)}")
    return tuple((name, replacements.get(name, shape)) for name, shape in parts)


@dataclass(frozen=True, slots=True)
class PrimaryControlHapticArchitectureV4:
    source_main_sha: str
    shell_outer_z_mm: float
    rest_cap_underside_z_mm: float
    material_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    reference_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    motion_sweep: cq.Shape = field(repr=False, compare=False)
    joint_overlap_mm3: dict[str, float] = field(default_factory=dict)
    bushing_capture_removed_mm3: dict[str, float] = field(default_factory=dict)
    keepout_intersections_mm3: dict[str, float] = field(default_factory=dict)
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_main_sha != SOURCE_MAIN_SHA:
            raise PrimaryControlHapticV4Error("V4 source-main mismatch")
        if self.physical_validation_eligible:
            raise PrimaryControlHapticV4Error("digital guide geometry is not physical validation")
        if min(self.bushing_capture_removed_mm3.values(), default=0.0) <= 0.0:
            raise PrimaryControlHapticV4Error("both bushing stations require positive capture-groove material removal")
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in self.keepout_intersections_mm3.values()):
            raise PrimaryControlHapticV4Error("V4 primary control intersects a protected package/visual keepout")

        material = dict(self.material_parts)
        references = dict(self.reference_parts)
        for name in ("upper_split_bushing_free", "lower_split_bushing_free"):
            shape = material[name]
            if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
                raise PrimaryControlHapticV4Error(f"{name} must be one valid manufactured sleeve")
        for name in ("upper_split_bushing_installed_reference", "lower_split_bushing_installed_reference"):
            shape = references[name]
            if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
                raise PrimaryControlHapticV4Error(f"{name} must be one valid installed reference")

        free_journal_wall = (BUSHING_FREE_JOURNAL_OD_MM - BUSHING_FREE_ID_MM) / 2.0
        installed_journal_wall = (BUSHING_INSTALLED_JOURNAL_OD_MM - BUSHING_INSTALLED_ID_MM) / 2.0
        free_flange_wall = (BUSHING_FREE_FLANGE_OD_MM - BUSHING_FREE_ID_MM) / 2.0
        installed_flange_wall = (BUSHING_INSTALLED_FLANGE_OD_MM - BUSHING_INSTALLED_ID_MM) / 2.0
        if not math.isclose(free_journal_wall, installed_journal_wall, abs_tol=1e-12):
            raise PrimaryControlHapticV4Error("journal free/installed references must preserve nominal wall thickness")
        if not math.isclose(free_flange_wall, installed_flange_wall, abs_tol=1e-12):
            raise PrimaryControlHapticV4Error("flange free/installed references must preserve nominal wall thickness")
        if not math.isclose(BUSHING_INSTALLED_JOURNAL_OD_MM, v1.BARREL_BORE_DIAMETER_MM, abs_tol=1e-12):
            raise PrimaryControlHapticV4Error("installed bushing journal must register to shell barrel bore")
        if not BUSHING_INSTALLED_FLANGE_OD_MM < BUSHING_CAPTURE_GROOVE_OD_MM:
            raise PrimaryControlHapticV4Error("installed flange requires positive radial groove clearance")
        if not BUSHING_INSTALLED_SPLIT_GAP_MM > BUSHING_FREE_SPLIT_GAP_MM:
            raise PrimaryControlHapticV4Error("split gap must open as the sleeve expands over the stem")

    @property
    def architecture_sha256(self) -> str:
        payload = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(payload).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        base_payload = v3.PrimaryControlHapticArchitectureV3(
            self.source_main_sha,
            self.shell_outer_z_mm,
            self.rest_cap_underside_z_mm,
            self.material_parts,
            self.reference_parts,
            self.motion_sweep,
            self.joint_overlap_mm3,
            self.keepout_intersections_mm3,
            False,
        ).manifest(False)
        base_payload.update(
            {
                "schema": SCHEMA,
                "supersedes": "V3_FLOATING_DIMENSIONALLY_INCONSISTENT_GUIDE_BUSHING_REFERENCES",
                "guidance": {
                    "architecture": "TWO_SHELL_FIXED_SPLIT_LOW_FRICTION_FLANGED_SLEEVES",
                    "stem_diameter_mm": v1.STEM_DIAMETER_MM,
                    "station_span_mm": v1.BUSHING_SPAN_MM,
                    "free_id_mm": BUSHING_FREE_ID_MM,
                    "installed_id_mm": BUSHING_INSTALLED_ID_MM,
                    "free_journal_od_mm": BUSHING_FREE_JOURNAL_OD_MM,
                    "installed_journal_od_mm": BUSHING_INSTALLED_JOURNAL_OD_MM,
                    "barrel_bore_mm": v1.BARREL_BORE_DIAMETER_MM,
                    "free_flange_od_mm": BUSHING_FREE_FLANGE_OD_MM,
                    "installed_flange_od_mm": BUSHING_INSTALLED_FLANGE_OD_MM,
                    "capture_groove_od_mm": BUSHING_CAPTURE_GROOVE_OD_MM,
                    "capture_groove_height_mm": BUSHING_CAPTURE_GROOVE_HEIGHT_MM,
                    "free_split_gap_mm": BUSHING_FREE_SPLIT_GAP_MM,
                    "installed_split_gap_mm": BUSHING_INSTALLED_SPLIT_GAP_MM,
                    "nominal_journal_wall_preserved": True,
                    "nominal_flange_wall_preserved": True,
                    "shell_fixed_axial_capture": True,
                    "bushing_capture_removed_mm3": self.bushing_capture_removed_mm3,
                },
                "tactile_quality_interpretation": (
                    "DIGITAL PRECURSOR ONLY: SHELL-FIXED DATUMS PLUS TWO-STATION BEARING SEPARATION REMOVE A KNOWN "
                    "FLOATING-GUIDE FAILURE MODE. WOBBLE_FRICTION_STICTION_WEAR_CREEP_AND_CONTAMINATION_REQUIRE_BENCH_TEST."
                ),
                "physical_validation_eligible": False,
            }
        )
        if include_sha:
            base_payload["architecture_sha256"] = self.architecture_sha256
        return base_payload


def build_primary_control_haptic_architecture_v4(
    *,
    model: MasckOneModel | None = None,
) -> PrimaryControlHapticArchitectureV4:
    model = build_model() if model is None else model
    base = v3.build_primary_control_haptic_architecture_v3(model=model)
    material = dict(base.material_parts)
    references = dict(base.reference_parts)

    upper_z0 = base.rest_cap_underside_z_mm - v1.UPPER_BUSHING_CENTER_FROM_REST_MM - v1.BUSHING_LENGTH_MM / 2.0
    lower_z0 = base.rest_cap_underside_z_mm - v1.LOWER_BUSHING_CENTER_FROM_REST_MM - v1.BUSHING_LENGTH_MM / 2.0

    shell = material["shell_with_primary_control_interface"]
    capture_removed: dict[str, float] = {}
    shell, capture_removed["upper"] = _cut_capture_grooves(shell, upper_z0)
    shell, capture_removed["lower"] = _cut_capture_grooves(shell, lower_z0)

    free = {
        "upper_split_bushing_free": _split_flanged_sleeve(
            journal_od_mm=BUSHING_FREE_JOURNAL_OD_MM,
            flange_od_mm=BUSHING_FREE_FLANGE_OD_MM,
            id_mm=BUSHING_FREE_ID_MM,
            z0_mm=upper_z0,
            split_gap_mm=BUSHING_FREE_SPLIT_GAP_MM,
        ),
        "lower_split_bushing_free": _split_flanged_sleeve(
            journal_od_mm=BUSHING_FREE_JOURNAL_OD_MM,
            flange_od_mm=BUSHING_FREE_FLANGE_OD_MM,
            id_mm=BUSHING_FREE_ID_MM,
            z0_mm=lower_z0,
            split_gap_mm=BUSHING_FREE_SPLIT_GAP_MM,
        ),
    }
    installed = {
        "upper_split_bushing_installed_reference": _split_flanged_sleeve(
            journal_od_mm=BUSHING_INSTALLED_JOURNAL_OD_MM,
            flange_od_mm=BUSHING_INSTALLED_FLANGE_OD_MM,
            id_mm=BUSHING_INSTALLED_ID_MM,
            z0_mm=upper_z0,
            split_gap_mm=BUSHING_INSTALLED_SPLIT_GAP_MM,
        ),
        "lower_split_bushing_installed_reference": _split_flanged_sleeve(
            journal_od_mm=BUSHING_INSTALLED_JOURNAL_OD_MM,
            flange_od_mm=BUSHING_INSTALLED_FLANGE_OD_MM,
            id_mm=BUSHING_INSTALLED_ID_MM,
            z0_mm=lower_z0,
            split_gap_mm=BUSHING_INSTALLED_SPLIT_GAP_MM,
        ),
    }

    material_parts = _replace_named(
        base.material_parts,
        {"shell_with_primary_control_interface": shell, **free},
    )
    reference_parts = _replace_named(base.reference_parts, installed)
    material = dict(material_parts)
    references = dict(reference_parts)

    module = cq.Compound.makeCompound(
        [
            material["primary_control_cap_stem"],
            material["cap_inertia_core"],
            references["upper_split_bushing_installed_reference"],
            references["lower_split_bushing_installed_reference"],
            references["anti_rotation_leaf_installed_reference"],
            material["wet_diaphragm"],
            material["tactile_spring_formed"],
            material["tactile_damping_annulus"],
            material["tactile_snap_retainer"],
            material["landing_stage_1"],
            material["landing_stage_2"],
            material["sensor_magnet"],
            references["hall_sensor_envelope"],
            material["hall_pcb_support"],
        ]
    )
    keepouts = {
        **{component.name: component.solid.val() for component in model.actuator_envelopes},
        "water_reservoir_envelope": model.water_reservoir_envelope.solid.val(),
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid.val(),
        "battery_reference_envelope": model.battery_reference_envelope.solid.val(),
        **{component.name: component.solid.val() for component in model.visual_keepouts},
    }
    intersections = {
        name: round(v1._intersection_volume(module, target), 8)
        for name, target in keepouts.items()
    }

    result = PrimaryControlHapticArchitectureV4(
        SOURCE_MAIN_SHA,
        base.shell_outer_z_mm,
        base.rest_cap_underside_z_mm,
        material_parts,
        reference_parts,
        base.motion_sweep,
        base.joint_overlap_mm3,
        {name: round(value, 9) for name, value in capture_removed.items()},
        intersections,
        False,
    )
    result.__post_init__()
    return result


def export_primary_control_haptic_architecture_v4(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_primary_control_haptic_architecture_v4()
    for name, shape in architecture.material_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_MANUFACTURED.step"))
    for name, shape in architecture.reference_parts:
        cq.exporters.export(shape, str(output_dir / f"{name}_REFERENCE.step"))
    manifest = architecture.manifest()
    (output_dir / "primary_control_haptic_v4_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
