from __future__ import annotations

from dataclasses import dataclass
import math

from .authority import Authority
from .spatial import CanonicalDatums, Point2, Point3, authority_point2


class FacialReferenceError(ValueError):
    """Raised when facial-reference data violates the engineering contract."""


@dataclass(frozen=True, slots=True)
class PlanarLandmark:
    """Authority-defined facial landmark projection in canonical XY coordinates.

    Important: `point_xy` does NOT claim a physical Z coordinate on a human face.
    Iteration 4 preserves the authority exactly by keeping unresolved 3D depth
    undefined until a registered facial/headform surface exists.
    """

    id: str
    anatomical_name: str
    point_xy: Point2
    authority_status: str
    source_path: str
    bilateral_group: str | None = None
    side: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise FacialReferenceError("Landmark id must be non-empty")
        if not self.anatomical_name.strip():
            raise FacialReferenceError(f"Landmark {self.id!r} requires an anatomical name")
        if not self.authority_status.strip():
            raise FacialReferenceError(f"Landmark {self.id!r} requires an authority status")
        if not self.source_path.strip():
            raise FacialReferenceError(f"Landmark {self.id!r} requires source provenance")
        if self.side not in {None, "left", "right", "midline"}:
            raise FacialReferenceError(f"Landmark {self.id!r} has unsupported side {self.side!r}")
        if self.side == "midline" and not math.isclose(self.point_xy.x, 0.0, abs_tol=1e-12):
            raise FacialReferenceError(f"Midline landmark {self.id!r} must lie on X=0")
        if self.side == "left" and not self.point_xy.x < 0.0:
            raise FacialReferenceError(f"Left landmark {self.id!r} must have X < 0")
        if self.side == "right" and not self.point_xy.x > 0.0:
            raise FacialReferenceError(f"Right landmark {self.id!r} must have X > 0")

    @property
    def has_resolved_depth(self) -> bool:
        return False

    def as_projected_point3(self, *, z_reference_mm: float) -> Point3:
        """Return a plotting/CAD reference point only, never an anatomical 3D claim.

        The caller must explicitly supply a visualization/reference-plane Z value.
        Requiring this argument prevents a silent `Z = 0` anatomical assumption.
        This method exists for datum graphics/debug exports; it must not substitute
        for future headform/surface registration.
        """

        return self.point_xy.with_z(z_reference_mm)


@dataclass(frozen=True, slots=True)
class BilateralLandmarkPair:
    """Left/right landmarks that are expected to be neutral-baseline mirror projections."""

    group: str
    left: PlanarLandmark
    right: PlanarLandmark

    def __post_init__(self) -> None:
        if self.left.side != "left" or self.right.side != "right":
            raise FacialReferenceError(f"Bilateral pair {self.group!r} must contain left/right landmarks")
        if self.left.bilateral_group != self.group or self.right.bilateral_group != self.group:
            raise FacialReferenceError(f"Bilateral pair {self.group!r} has inconsistent group metadata")
        mirrored = self.left.point_xy.mirrored_across_sagittal()
        if mirrored != self.right.point_xy:
            raise FacialReferenceError(
                f"Bilateral pair {self.group!r} is not symmetric in the current neutral CAD baseline: "
                f"left={self.left.point_xy.as_tuple()}, right={self.right.point_xy.as_tuple()}"
            )

    @property
    def center_spacing_mm(self) -> float:
        return abs(self.right.point_xy.x - self.left.point_xy.x)

    @property
    def common_y_mm(self) -> float:
        if not math.isclose(self.left.point_xy.y, self.right.point_xy.y, abs_tol=1e-12):
            raise FacialReferenceError(f"Bilateral pair {self.group!r} does not share a common Y coordinate")
        return self.left.point_xy.y

    @property
    def midpoint(self) -> Point2:
        return Point2(
            (self.left.point_xy.x + self.right.point_xy.x) / 2.0,
            (self.left.point_xy.y + self.right.point_xy.y) / 2.0,
        )


@dataclass(frozen=True, slots=True)
class FacialReferenceMetrics:
    """Purely derived neutral-baseline metrics; these are not independent authority values."""

    interpupillary_center_spacing_mm: float
    nostril_center_spacing_mm: float
    eye_line_y_mm: float
    nostril_line_y_mm: float
    mouth_center_y_mm: float
    eye_to_nostril_line_vertical_mm: float
    nostril_to_mouth_center_vertical_mm: float
    eye_to_mouth_center_vertical_mm: float


@dataclass(frozen=True, slots=True)
class FacialReferenceLayer:
    """Typed semantic facial-reference layer derived from current machine authority only."""

    datums: CanonicalDatums
    eye_pair: BilateralLandmarkPair
    nostril_pair: BilateralLandmarkPair
    mouth_center: PlanarLandmark
    reference_kind: str
    source_revision: str

    def __post_init__(self) -> None:
        if self.reference_kind != "NEUTRAL_2D_CAD_BASELINE_PROJECTION":
            raise FacialReferenceError(f"Unexpected reference kind {self.reference_kind!r}")
        if not self.source_revision.strip():
            raise FacialReferenceError("Facial reference requires source authority revision")
        ids = [landmark.id for landmark in self.landmarks]
        if len(ids) != len(set(ids)):
            raise FacialReferenceError("Facial landmark IDs must be unique")
        if not math.isclose(self.eye_pair.midpoint.x, 0.0, abs_tol=1e-12):
            raise FacialReferenceError("Neutral eye-pair midpoint must lie on the canonical sagittal plane")
        if not math.isclose(self.nostril_pair.midpoint.x, 0.0, abs_tol=1e-12):
            raise FacialReferenceError("Neutral nostril-pair midpoint must lie on the canonical sagittal plane")
        if self.mouth_center.side != "midline":
            raise FacialReferenceError("Mouth center must be explicitly classified as a midline landmark")

    @property
    def landmarks(self) -> tuple[PlanarLandmark, ...]:
        return (
            self.eye_pair.left,
            self.eye_pair.right,
            self.nostril_pair.left,
            self.nostril_pair.right,
            self.mouth_center,
        )

    @property
    def metrics(self) -> FacialReferenceMetrics:
        eye_y = self.eye_pair.common_y_mm
        nostril_y = self.nostril_pair.common_y_mm
        mouth_y = self.mouth_center.point_xy.y
        return FacialReferenceMetrics(
            interpupillary_center_spacing_mm=self.eye_pair.center_spacing_mm,
            nostril_center_spacing_mm=self.nostril_pair.center_spacing_mm,
            eye_line_y_mm=eye_y,
            nostril_line_y_mm=nostril_y,
            mouth_center_y_mm=mouth_y,
            eye_to_nostril_line_vertical_mm=eye_y - nostril_y,
            nostril_to_mouth_center_vertical_mm=nostril_y - mouth_y,
            eye_to_mouth_center_vertical_mm=eye_y - mouth_y,
        )

    def by_id(self, landmark_id: str) -> PlanarLandmark:
        for landmark in self.landmarks:
            if landmark.id == landmark_id:
                return landmark
        raise KeyError(landmark_id)

    def unresolved_3d_landmarks(self) -> tuple[str, ...]:
        return tuple(landmark.id for landmark in self.landmarks if not landmark.has_resolved_depth)


def _landmark(
    authority: Authority,
    *,
    landmark_id: str,
    anatomical_name: str,
    point_path: tuple[str, ...],
    status_path: tuple[str, ...],
    bilateral_group: str | None = None,
    side: str | None = None,
) -> PlanarLandmark:
    return PlanarLandmark(
        id=landmark_id,
        anatomical_name=anatomical_name,
        point_xy=authority_point2(authority, *point_path),
        authority_status=str(authority.get(*status_path)),
        source_path=".".join(point_path),
        bilateral_group=bilateral_group,
        side=side,
    )


def build_facial_reference(authority: Authority, datums: CanonicalDatums | None = None) -> FacialReferenceLayer:
    """Build the Iteration-4 facial reference without inventing unsourced 3D anatomy."""

    datums = datums or CanonicalDatums.from_authority(authority)

    eye_left = _landmark(
        authority,
        landmark_id="MASCK_ONE-LMK-EYE-LEFT-CENTER",
        anatomical_name="left eye visual-aperture center reference",
        point_path=("geometry", "eye", "centers_mm", "left"),
        status_path=("geometry", "eye", "center_status"),
        bilateral_group="EYE_CENTER_PAIR",
        side="left",
    )
    eye_right = _landmark(
        authority,
        landmark_id="MASCK_ONE-LMK-EYE-RIGHT-CENTER",
        anatomical_name="right eye visual-aperture center reference",
        point_path=("geometry", "eye", "centers_mm", "right"),
        status_path=("geometry", "eye", "center_status"),
        bilateral_group="EYE_CENTER_PAIR",
        side="right",
    )
    nostril_left = _landmark(
        authority,
        landmark_id="MASCK_ONE-LMK-NOSTRIL-LEFT-CENTER",
        anatomical_name="left nostril opening center reference",
        point_path=("geometry", "nostrils", "centers_mm", "left"),
        status_path=("geometry", "nostrils", "center_status"),
        bilateral_group="NOSTRIL_CENTER_PAIR",
        side="left",
    )
    nostril_right = _landmark(
        authority,
        landmark_id="MASCK_ONE-LMK-NOSTRIL-RIGHT-CENTER",
        anatomical_name="right nostril opening center reference",
        point_path=("geometry", "nostrils", "centers_mm", "right"),
        status_path=("geometry", "nostrils", "center_status"),
        bilateral_group="NOSTRIL_CENTER_PAIR",
        side="right",
    )
    mouth_center = _landmark(
        authority,
        landmark_id="MASCK_ONE-LMK-MOUTH-CENTER",
        anatomical_name="mouth visual-aperture center reference",
        point_path=("geometry", "mouth", "center_mm"),
        status_path=("geometry", "mouth", "center_status"),
        side="midline",
    )

    return FacialReferenceLayer(
        datums=datums,
        eye_pair=BilateralLandmarkPair("EYE_CENTER_PAIR", eye_left, eye_right),
        nostril_pair=BilateralLandmarkPair("NOSTRIL_CENTER_PAIR", nostril_left, nostril_right),
        mouth_center=mouth_center,
        reference_kind="NEUTRAL_2D_CAD_BASELINE_PROJECTION",
        source_revision=str(authority.get("project", "authority_revision")),
    )
