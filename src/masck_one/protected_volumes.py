from __future__ import annotations

from dataclasses import dataclass
import math

from .anatomy import FacialReferenceLayer
from .authority import Authority
from .facial_surface import FacialSurface
from .spatial import Point2, Point3


class ProtectedVolumeError(ValueError):
    """Raised when a protected-zone definition violates the safety geometry contract."""


@dataclass(frozen=True, slots=True)
class PlanarProtectedZone:
    """Conservative 2D protected footprint extruded conceptually through unresolved depth.

    Iteration 7 deliberately separates an authority-derived XY hard envelope from a
    future anatomically measured 3D keep-out. The planar footprint is useful for
    outlet/region/topology exclusion now, but cannot close dynamic 3D safety gates.
    """

    zone_id: str
    anatomical_target: str
    shape: str
    center: Point2
    aperture_width_mm: float
    aperture_height_mm: float
    required_rigid_clearance_mm: float
    angle_deg: float
    authority_status: str
    evidence_status: str
    source_path: str

    def __post_init__(self) -> None:
        for label, value in {
            "zone_id": self.zone_id,
            "anatomical_target": self.anatomical_target,
            "authority_status": self.authority_status,
            "evidence_status": self.evidence_status,
            "source_path": self.source_path,
        }.items():
            if not str(value).strip():
                raise ProtectedVolumeError(f"{label} must be non-empty")
        if self.shape not in {"ELLIPSE", "CIRCLE"}:
            raise ProtectedVolumeError(f"Unsupported protected-zone shape {self.shape!r}")
        for label, value in {
            "aperture_width_mm": self.aperture_width_mm,
            "aperture_height_mm": self.aperture_height_mm,
            "required_rigid_clearance_mm": self.required_rigid_clearance_mm,
            "angle_deg": self.angle_deg,
        }.items():
            number = float(value)
            if not math.isfinite(number):
                raise ProtectedVolumeError(f"{label} must be finite")
            object.__setattr__(self, label, number)
        if self.aperture_width_mm <= 0.0 or self.aperture_height_mm <= 0.0:
            raise ProtectedVolumeError("Protected-zone aperture dimensions must be positive")
        if self.required_rigid_clearance_mm < 0.0:
            raise ProtectedVolumeError("Protected-zone clearance cannot be negative")
        if self.shape == "CIRCLE" and not math.isclose(
            self.aperture_width_mm,
            self.aperture_height_mm,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ProtectedVolumeError("Circular protected zones require equal aperture width/height")

    @property
    def envelope_width_mm(self) -> float:
        return self.aperture_width_mm + 2.0 * self.required_rigid_clearance_mm

    @property
    def envelope_height_mm(self) -> float:
        return self.aperture_height_mm + 2.0 * self.required_rigid_clearance_mm

    @property
    def aperture_area_mm2(self) -> float:
        return math.pi * (self.aperture_width_mm / 2.0) * (self.aperture_height_mm / 2.0)

    @property
    def envelope_area_mm2(self) -> float:
        return math.pi * (self.envelope_width_mm / 2.0) * (self.envelope_height_mm / 2.0)

    def _local_xy(self, point: Point2) -> tuple[float, float]:
        dx = point.x - self.center.x
        dy = point.y - self.center.y
        angle = math.radians(-self.angle_deg)
        c, s = math.cos(angle), math.sin(angle)
        return c * dx - s * dy, s * dx + c * dy

    def contains_xy(self, point: Point2, *, include_boundary: bool = True) -> bool:
        local_x, local_y = self._local_xy(point)
        a = self.envelope_width_mm / 2.0
        b = self.envelope_height_mm / 2.0
        normalized = (local_x / a) ** 2 + (local_y / b) ** 2
        return normalized <= 1.0 + 1e-12 if include_boundary else normalized < 1.0 - 1e-12

    def contains_aperture_xy(self, point: Point2, *, include_boundary: bool = True) -> bool:
        local_x, local_y = self._local_xy(point)
        a = self.aperture_width_mm / 2.0
        b = self.aperture_height_mm / 2.0
        normalized = (local_x / a) ** 2 + (local_y / b) ** 2
        return normalized <= 1.0 + 1e-12 if include_boundary else normalized < 1.0 - 1e-12

    def conservative_radial_margin_xy_mm(self, point: Point2) -> float:
        """Return a conservative radial margin from the protected envelope.

        Positive values are outside the envelope, zero is on it, and negative values
        are inside. The value scales normalized ellipse radius by the smaller semi-axis,
        so it is deliberately conservative and is not an exact Euclidean ellipse distance.
        """

        local_x, local_y = self._local_xy(point)
        a = self.envelope_width_mm / 2.0
        b = self.envelope_height_mm / 2.0
        normalized_radius = math.sqrt((local_x / a) ** 2 + (local_y / b) ** 2)
        return (normalized_radius - 1.0) * min(a, b)

    def mirrored_across_sagittal(self) -> "PlanarProtectedZone":
        return PlanarProtectedZone(
            zone_id=self.zone_id,
            anatomical_target=self.anatomical_target,
            shape=self.shape,
            center=self.center.mirrored_across_sagittal(),
            aperture_width_mm=self.aperture_width_mm,
            aperture_height_mm=self.aperture_height_mm,
            required_rigid_clearance_mm=self.required_rigid_clearance_mm,
            angle_deg=-self.angle_deg,
            authority_status=self.authority_status,
            evidence_status=self.evidence_status,
            source_path=self.source_path,
        )


@dataclass(frozen=True, slots=True)
class ProtectedVolume:
    """2.5D safety exclusion whose Z extent remains deliberately unresolved."""

    zone: PlanarProtectedZone
    z_policy: str = "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE"
    anatomical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.z_policy != "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE":
            raise ProtectedVolumeError(f"Unsupported z_policy {self.z_policy!r}")
        if self.anatomical_validation_eligible:
            raise ProtectedVolumeError(
                "Iteration-7 analytical protected volumes cannot be promoted to anatomical validation evidence"
            )

    def contains_point(self, point: Point3) -> bool:
        """Conservatively excludes the XY footprint for any Z until depth evidence exists."""

        return self.zone.contains_xy(Point2(point.x, point.y))


@dataclass(frozen=True, slots=True)
class ProtectedVolumeSet:
    eye_left: ProtectedVolume
    eye_right: ProtectedVolume
    mouth: ProtectedVolume
    nostril_left: ProtectedVolume
    nostril_right: ProtectedVolume
    source_surface_id: str
    evidence_status: str

    @property
    def all(self) -> tuple[ProtectedVolume, ...]:
        return (
            self.eye_left,
            self.eye_right,
            self.mouth,
            self.nostril_left,
            self.nostril_right,
        )

    def by_id(self, zone_id: str) -> ProtectedVolume:
        for volume in self.all:
            if volume.zone.zone_id == zone_id:
                return volume
        raise KeyError(zone_id)

    def excluded_xy(self, point: Point2) -> bool:
        return any(volume.zone.contains_xy(point) for volume in self.all)

    def manifest(self) -> dict[str, object]:
        return {
            "source_surface_id": self.source_surface_id,
            "evidence_status": self.evidence_status,
            "zones": [
                {
                    "zone_id": volume.zone.zone_id,
                    "target": volume.zone.anatomical_target,
                    "shape": volume.zone.shape,
                    "center_mm": list(volume.zone.center.as_tuple()),
                    "aperture_wh_mm": [volume.zone.aperture_width_mm, volume.zone.aperture_height_mm],
                    "required_rigid_clearance_mm": volume.zone.required_rigid_clearance_mm,
                    "envelope_wh_mm": [volume.zone.envelope_width_mm, volume.zone.envelope_height_mm],
                    "angle_deg": volume.zone.angle_deg,
                    "z_policy": volume.z_policy,
                    "anatomical_validation_eligible": volume.anatomical_validation_eligible,
                    "authority_status": volume.zone.authority_status,
                    "zone_evidence_status": volume.zone.evidence_status,
                    "source_path": volume.zone.source_path,
                }
                for volume in self.all
            ],
        }


def _nostril_minimum_equivalent_diameter(authority: Authority) -> float:
    minimum_area = authority.number("geometry", "nostrils", "minimum_deformed_area_each_mm2")
    minimum_local_dimension = authority.number("geometry", "nostrils", "minimum_local_opening_dimension_mm")
    area_diameter = math.sqrt(4.0 * minimum_area / math.pi)
    return max(minimum_local_dimension, area_diameter)


def build_protected_volumes(
    authority: Authority,
    facial_reference: FacialReferenceLayer,
    facial_surface: FacialSurface,
) -> ProtectedVolumeSet:
    """Build authority-derived planar hard envelopes without inventing dynamic anatomy."""

    surface_status = (
        "SOURCE_SURFACE_ANATOMICAL_REFERENCE_AVAILABLE"
        if facial_surface.descriptor.anatomical_validation_eligible
        else "SOURCE_SURFACE_NOT_ANATOMICAL_VALIDATION_EVIDENCE"
    )
    evidence_status = f"DEVELOPMENT_HARD_ENVELOPE;{surface_status};3D_DYNAMIC_GEOMETRY_BLOCKED"

    eye_w, eye_h = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    eye_clearance = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")
    eye_cant = authority.number("geometry", "eye", "lateral_cant_deg")
    eye_status = str(authority.get("geometry", "eye", "clearance_status"))

    eye_left_zone = PlanarProtectedZone(
        zone_id="MASCK_ONE-PROTECTED-EYE-LEFT",
        anatomical_target="left eye",
        shape="ELLIPSE",
        center=facial_reference.eye_pair.left.point_xy,
        aperture_width_mm=eye_w,
        aperture_height_mm=eye_h,
        required_rigid_clearance_mm=eye_clearance,
        angle_deg=-eye_cant,
        authority_status=eye_status,
        evidence_status=evidence_status,
        source_path="geometry.eye",
    )
    eye_right_zone = PlanarProtectedZone(
        zone_id="MASCK_ONE-PROTECTED-EYE-RIGHT",
        anatomical_target="right eye",
        shape="ELLIPSE",
        center=facial_reference.eye_pair.right.point_xy,
        aperture_width_mm=eye_w,
        aperture_height_mm=eye_h,
        required_rigid_clearance_mm=eye_clearance,
        angle_deg=eye_cant,
        authority_status=eye_status,
        evidence_status=evidence_status,
        source_path="geometry.eye",
    )

    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    mouth_clearance = authority.number("geometry", "mouth", "rigid_dynamic_keepout_clearance_mm")
    mouth_zone = PlanarProtectedZone(
        zone_id="MASCK_ONE-PROTECTED-MOUTH",
        anatomical_target="mouth",
        shape="ELLIPSE",
        center=facial_reference.mouth_center.point_xy,
        aperture_width_mm=mouth_w,
        aperture_height_mm=mouth_h,
        required_rigid_clearance_mm=mouth_clearance,
        angle_deg=0.0,
        authority_status=str(authority.get("geometry", "mouth", "clearance_status")),
        evidence_status=evidence_status,
        source_path="geometry.mouth",
    )

    nostril_diameter = _nostril_minimum_equivalent_diameter(authority)
    nostril_clearance = authority.number("geometry", "nostrils", "rigid_dynamic_keepout_clearance_mm")
    nostril_status = str(authority.get("geometry", "nostrils", "clearance_status"))
    nostril_left_zone = PlanarProtectedZone(
        zone_id="MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
        anatomical_target="left nostril/airway",
        shape="CIRCLE",
        center=facial_reference.nostril_pair.left.point_xy,
        aperture_width_mm=nostril_diameter,
        aperture_height_mm=nostril_diameter,
        required_rigid_clearance_mm=nostril_clearance,
        angle_deg=0.0,
        authority_status=nostril_status,
        evidence_status=evidence_status,
        source_path="geometry.nostrils+safety.airway",
    )
    nostril_right_zone = PlanarProtectedZone(
        zone_id="MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
        anatomical_target="right nostril/airway",
        shape="CIRCLE",
        center=facial_reference.nostril_pair.right.point_xy,
        aperture_width_mm=nostril_diameter,
        aperture_height_mm=nostril_diameter,
        required_rigid_clearance_mm=nostril_clearance,
        angle_deg=0.0,
        authority_status=nostril_status,
        evidence_status=evidence_status,
        source_path="geometry.nostrils+safety.airway",
    )

    return ProtectedVolumeSet(
        eye_left=ProtectedVolume(eye_left_zone),
        eye_right=ProtectedVolume(eye_right_zone),
        mouth=ProtectedVolume(mouth_zone),
        nostril_left=ProtectedVolume(nostril_left_zone),
        nostril_right=ProtectedVolume(nostril_right_zone),
        source_surface_id=facial_surface.descriptor.surface_id,
        evidence_status=evidence_status,
    )
