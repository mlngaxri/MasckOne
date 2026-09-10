"""Draft screen: can the moulded shell actually leave the tool?

A beautiful B-rep is not a manufacturable part. `ENGINEERING_GOVERNANCE` and the
design brief both insist that a substantive change be inspected for mould
direction, undercuts and draft before it is believed. Nothing in the repository
did that, so the shell could be exported, round-trip verified to 1e-7 mm3, and
still be a part that cannot eject.

This module measures draft on the released geometry rather than asserting it.

Draft and texture are coupled
-----------------------------
Draft is not one number. A polished face releases at well under a degree; a
textured one drags unless the draft grows with the texture depth, at roughly
one degree per 0.025 mm of texture. The Masck One exterior is specified as a
fine satin moulded-in finish, and the faces where that finish matters most are
the aperture edges the wearer looks through and touches. Those are exactly the
faces measured here.

What this is not
----------------
A geometric screen, not a mould-flow or ejection simulation. It measures the
angle between each face and a declared pull direction. It says nothing about
fill, packing, warp, shrink, ejector layout, gate position, weld lines, or
whether a given texture actually releases on a given resin. Those need a tool
maker and a moulding simulation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class MoldabilityError(ValueError):
    """Raised when a draft screen input or contract is invalid."""


EVIDENCE_STATUS = "GEOMETRIC_DRAFT_SCREEN_NOT_MOULD_FLOW_OR_EJECTION_SIMULATION"

# The shell is lofted along +Z and every aperture cutter is extruded along +Z,
# so +Z is the declared pull direction. Declaring it makes the assumption
# checkable instead of implicit.
PULL_DIRECTION = (0.0, 0.0, 1.0)

# Planning minima. A polished face releases at ~0.5 deg; texture adds roughly
# 1 deg per 0.025 mm of depth. A fine satin at 0.025-0.050 mm therefore wants
# 1.5-2.5 deg on top, which is where the textured minimum comes from.
MIN_DRAFT_POLISHED_DEG = 0.5
MIN_DRAFT_TEXTURED_DEG = 2.5
TEXTURE_DRAFT_DEG_PER_MM = 40.0  # ~1 deg per 0.025 mm

# A face this close to parallel with the pull cannot release at all.
ZERO_DRAFT_TOLERANCE_DEG = 0.05


class Finish(Enum):
    POLISHED = "POLISHED"
    FINE_SATIN = "FINE_SATIN"


def required_draft_deg(finish: Finish, texture_depth_mm: float = 0.0) -> float:
    """Minimum draft for a finish, growing with texture depth."""

    if not isinstance(finish, Finish):
        raise MoldabilityError("finish must be a Finish")
    depth = float(texture_depth_mm)
    if not math.isfinite(depth) or depth < 0.0:
        raise MoldabilityError("texture_depth_mm must be finite and non-negative")
    if finish is Finish.POLISHED:
        return MIN_DRAFT_POLISHED_DEG
    return MIN_DRAFT_POLISHED_DEG + TEXTURE_DRAFT_DEG_PER_MM * depth


def draft_angle_deg(normal, pull=PULL_DIRECTION) -> float:
    """Angle between a face and the pull direction.

    0 deg means the face is parallel to the pull and drags on the whole way out;
    90 deg means it is perpendicular and releases immediately.
    """

    vector = (float(normal.x), float(normal.y), float(normal.z))
    magnitude = math.sqrt(sum(component * component for component in vector))
    if magnitude == 0.0 or not math.isfinite(magnitude):
        raise MoldabilityError("face normal must be finite and non-zero")
    dot = sum(a * b for a, b in zip(vector, pull))
    angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / magnitude))))
    return abs(90.0 - angle)


@dataclass(frozen=True, slots=True)
class FaceDraft:
    index: int
    geom_type: str
    draft_deg: float
    area_mm2: float

    @property
    def is_zero_draft(self) -> bool:
        return self.draft_deg < ZERO_DRAFT_TOLERANCE_DEG

    def manifest(self) -> dict[str, object]:
        return {
            "index": self.index,
            "geom_type": self.geom_type,
            "draft_deg": round(self.draft_deg, 4),
            "area_mm2": round(self.area_mm2, 4),
            "zero_draft": self.is_zero_draft,
        }


@dataclass(frozen=True)
class DraftScreen:
    """Per-face draft measured on a real solid against a declared pull."""

    component_name: str
    pull_direction: tuple[float, float, float]
    required_draft_deg: float
    faces: tuple[FaceDraft, ...]

    @property
    def total_area_mm2(self) -> float:
        return math.fsum(face.area_mm2 for face in self.faces)

    @property
    def zero_draft_faces(self) -> tuple[FaceDraft, ...]:
        return tuple(face for face in self.faces if face.is_zero_draft)

    @property
    def undrafted_faces(self) -> tuple[FaceDraft, ...]:
        return tuple(
            face for face in self.faces if face.draft_deg < self.required_draft_deg
        )

    @property
    def zero_draft_area_fraction(self) -> float:
        total = self.total_area_mm2
        return 0.0 if total <= 0 else math.fsum(
            f.area_mm2 for f in self.zero_draft_faces
        ) / total

    @property
    def minimum_draft_deg(self) -> float:
        return min(face.draft_deg for face in self.faces)

    def manifest(self) -> dict[str, object]:
        return {
            "schema": "MASCK_ONE_DRAFT_SCREEN_V1",
            "evidence_status": EVIDENCE_STATUS,
            "component": self.component_name,
            "pull_direction": list(self.pull_direction),
            "required_draft_deg": self.required_draft_deg,
            "face_count": len(self.faces),
            "minimum_draft_deg": round(self.minimum_draft_deg, 4),
            "zero_draft_face_count": len(self.zero_draft_faces),
            "zero_draft_area_mm2": round(
                math.fsum(f.area_mm2 for f in self.zero_draft_faces), 4
            ),
            "zero_draft_area_fraction": round(self.zero_draft_area_fraction, 6),
            "undrafted_face_count": len(self.undrafted_faces),
            "faces": [face.manifest() for face in self.faces],
            "not_evidence_of": [
                "mould filling, packing or warp",
                "ejection force or scuffing",
                "texture release on a specific resin",
                "gate, runner or ejector layout",
                "weld-line position or strength",
            ],
        }


def screen_component_draft(
    component,
    *,
    finish: Finish = Finish.FINE_SATIN,
    texture_depth_mm: float = 0.040,
    pull=PULL_DIRECTION,
) -> DraftScreen:
    """Measure draft on every face of a component's solid."""

    solid = component.solid.val()
    faces: list[FaceDraft] = []
    for index, face in enumerate(solid.Faces()):
        try:
            draft = draft_angle_deg(face.normalAt(), pull)
        except Exception as exc:  # a face with no evaluable normal is a finding
            raise MoldabilityError(
                f"{component.name} face {index} has no evaluable normal: {exc}"
            ) from exc
        faces.append(FaceDraft(index, face.geomType(), draft, float(face.Area())))

    if not faces:
        raise MoldabilityError(f"{component.name} has no faces to screen")

    return DraftScreen(
        component_name=component.name,
        pull_direction=tuple(float(v) for v in pull),
        required_draft_deg=required_draft_deg(finish, texture_depth_mm),
        faces=tuple(faces),
    )
