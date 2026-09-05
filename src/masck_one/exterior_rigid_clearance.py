from __future__ import annotations

"""Cell 2 rigid-shell cuts bound directly to released protected-face footprints.

The protected-volume layer already owns the conservative XY hard envelopes. This module
only consumes those envelopes to remove rigid exterior material. It does not create a
second safety geometry truth, a soft facial interface, anatomical depth evidence, fit
validation, or physical clearance evidence.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .exterior_surface import _ellipse_cutter
from .facial_surface import build_planar_development_surface
from .protected_volumes import ProtectedVolumeSet, build_protected_volumes


SCHEMA = "MASCK_ONE_CELL2_RIGID_PROTECTED_FACE_CLEARANCE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
EXPECTED_ZONE_IDS = (
    "MASCK_ONE-PROTECTED-EYE-LEFT",
    "MASCK_ONE-PROTECTED-EYE-RIGHT",
    "MASCK_ONE-PROTECTED-MOUTH",
    "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
    "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
)
EVIDENCE_STATUS = (
    "DIGITAL_RIGID_MATERIAL_EXCLUSION_AGAINST_RELEASED_2P5D_PROTECTED_FOOTPRINTS_"
    "NOT_ANATOMICAL_FIT_DYNAMIC_CLEARANCE_OR_PHYSICAL_SAFETY_EVIDENCE"
)


class RigidProtectedClearanceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RigidClearanceOpening:
    zone_id: str
    target: str
    shape: str
    center_mm: tuple[float, float]
    envelope_wh_mm: tuple[float, float]
    angle_deg: float
    source_path: str

    def __post_init__(self) -> None:
        if self.zone_id not in EXPECTED_ZONE_IDS:
            raise RigidProtectedClearanceError("unexpected protected-zone identity")
        if self.shape not in {"ELLIPSE", "CIRCLE"}:
            raise RigidProtectedClearanceError("unsupported rigid-clearance opening shape")
        if len(self.center_mm) != 2 or len(self.envelope_wh_mm) != 2:
            raise RigidProtectedClearanceError("rigid-clearance opening requires XY center and WH envelope")
        values = (*self.center_mm, *self.envelope_wh_mm, self.angle_deg)
        if any(not math.isfinite(float(value)) for value in values):
            raise RigidProtectedClearanceError("rigid-clearance geometry must be finite")
        if self.envelope_wh_mm[0] <= 0.0 or self.envelope_wh_mm[1] <= 0.0:
            raise RigidProtectedClearanceError("rigid-clearance envelope dimensions must be positive")
        if not self.target.strip() or not self.source_path.strip():
            raise RigidProtectedClearanceError("rigid-clearance provenance text must be nonblank")

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "zone_id": self.zone_id,
            "target": self.target,
            "shape": self.shape,
            "center_mm": list(self.center_mm),
            "envelope_wh_mm": list(self.envelope_wh_mm),
            "angle_deg": self.angle_deg,
            "source_path": self.source_path,
        }


def build_current_protected_volumes(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
) -> ProtectedVolumeSet:
    """Reconstruct the released planar protected set when a model set is not supplied."""
    surface = build_planar_development_surface(authority)
    return build_protected_volumes(authority, facial_reference, surface)


def _validate_protected_source(protected_volumes: ProtectedVolumeSet) -> None:
    if type(protected_volumes) is not ProtectedVolumeSet:
        raise RigidProtectedClearanceError("rigid exterior requires exact ProtectedVolumeSet source")
    if not protected_volumes.source_surface_id.strip():
        raise RigidProtectedClearanceError("protected source surface identity must be nonblank")
    if "DEVELOPMENT_HARD_ENVELOPE" not in protected_volumes.evidence_status:
        raise RigidProtectedClearanceError("protected source lost development hard-envelope status")
    if "3D_DYNAMIC_GEOMETRY_BLOCKED" not in protected_volumes.evidence_status:
        raise RigidProtectedClearanceError("protected source cannot imply resolved 3D dynamic safety")

    zone_ids = tuple(volume.zone.zone_id for volume in protected_volumes.all)
    if zone_ids != EXPECTED_ZONE_IDS:
        raise RigidProtectedClearanceError("protected-zone identity or order changed; rebind Cell 2 exterior")
    for volume in protected_volumes.all:
        if volume.zone.evidence_status != protected_volumes.evidence_status:
            raise RigidProtectedClearanceError("protected-zone evidence status drifted from its source set")
        if volume.z_policy != "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE":
            raise RigidProtectedClearanceError("protected-zone Z policy changed; rebind Cell 2 exterior")
        if volume.anatomical_validation_eligible:
            raise RigidProtectedClearanceError("development protected source cannot imply anatomical validation")


def rigid_clearance_openings(
    protected_volumes: ProtectedVolumeSet,
) -> tuple[RigidClearanceOpening, ...]:
    _validate_protected_source(protected_volumes)
    openings = tuple(
        RigidClearanceOpening(
            zone_id=volume.zone.zone_id,
            target=volume.zone.anatomical_target,
            shape=volume.zone.shape,
            center_mm=(volume.zone.center.x, volume.zone.center.y),
            envelope_wh_mm=(volume.zone.envelope_width_mm, volume.zone.envelope_height_mm),
            angle_deg=volume.zone.angle_deg,
            source_path=volume.zone.source_path,
        )
        for volume in protected_volumes.all
    )
    if len(openings) != len(EXPECTED_ZONE_IDS):
        raise RigidProtectedClearanceError("all five protected rigid openings are required")
    return openings


def cut_rigid_hard_envelopes(
    shell: cq.Workplane,
    protected_volumes: ProtectedVolumeSet,
) -> cq.Workplane:
    """Remove rigid material through every released planar protected footprint."""
    if shell.solids().size() != 1 or not shell.val().isValid():
        raise RigidProtectedClearanceError("input exterior must be one valid solid")

    result = shell
    for opening in rigid_clearance_openings(protected_volumes):
        width, height = opening.envelope_wh_mm
        x_mm, y_mm = opening.center_mm
        result = result.cut(
            _ellipse_cutter(
                width,
                height,
                x_mm,
                y_mm,
                angle_deg=opening.angle_deg,
            )
        )

    if result.solids().size() != 1 or not result.val().isValid():
        raise RigidProtectedClearanceError(
            "protected-face rigid cuts must preserve one valid connected shell"
        )
    return result


def rigid_clearance_manifest(
    authority: Authority,
    protected_volumes: ProtectedVolumeSet,
) -> dict[str, object]:
    openings = rigid_clearance_openings(protected_volumes)
    return {
        "schema": SCHEMA,
        "authority_revision": str(authority.get("project", "authority_revision")),
        "coordinate_frame": WORLD_FRAME_ID,
        "protected_source_surface_id": protected_volumes.source_surface_id,
        "protected_evidence_status": protected_volumes.evidence_status,
        "openings": [opening.manifest() for opening in openings],
        "rigid_material_policy": "NO_RIGID_MATERIAL_INSIDE_RELEASED_PLANAR_HARD_ENVELOPE_XY",
        "z_policy": "CONSUME_UNBOUNDED_PROTECTED_XY_POLICY_BY_THROUGH_CUTTING_CURRENT_RIGID_SHELL",
        "visual_aperture_policy": (
            "AUTHORITY_VISUAL_APERTURES_REMAIN_CONTROLLED_REFERENCES;"
            "NONRIGID_VISIBLE_INTERFACE_GEOMETRY_UNRESOLVED_NOT_INVENTED"
        ),
        "physical_validation_eligible": False,
        "evidence_status": EVIDENCE_STATUS,
    }
