from __future__ import annotations

"""V42: prove the four clearance corners span the declared tolerance rectangle.

V40/V41 bind four unique clearance coordinates to collision and transverse-mesh
evidence. V42 closes the remaining authority gap by independently reconstructing the
Cartesian product of nominal/maximum radial and anti-rotation clearances and requiring
the bound corner set to equal that rectangle exactly. This is tolerance-authority
provenance, not manufactured tolerance-stack or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v41 as v41

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V42"
SUPERSEDES_SCHEMA = v41.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV42Error(ValueError):
    pass


def _declared_rectangle() -> tuple[tuple[float, float], ...]:
    mechanism = v1.build_retention_quick_release_tactile()
    radial = (float(mechanism.rail_radial_clearance_mm), float(v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM))
    side = (float(mechanism.anti_rotation_side_clearance_mm), float(v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM))
    if any(not math.isfinite(value) or value <= 0.0 for value in radial + side):
        raise RetentionQuickReleaseTactileV42Error("declared clearance bounds must be finite and positive")
    if radial[1] < radial[0] or side[1] < side[0]:
        raise RetentionQuickReleaseTactileV42Error("declared maximum clearance fell below nominal authority")
    if radial[0] == radial[1] or side[0] == side[1]:
        raise RetentionQuickReleaseTactileV42Error("declared clearance rectangle must have nonzero extent on both axes")
    return tuple(sorted((r, s) for r in radial for s in side))


def _bound_rectangle(prior: v41.RetentionQuickReleaseTactileV41) -> tuple[tuple[float, float], ...]:
    manifest = prior.manifest()
    binding = manifest.get("clearance_corner_collision_mesh_binding")
    if not isinstance(binding, dict):
        raise RetentionQuickReleaseTactileV42Error("V41 clearance-corner binding is missing")
    corners = binding.get("clearance_corners")
    if not isinstance(corners, list) or len(corners) != 4:
        raise RetentionQuickReleaseTactileV42Error("V41 must expose exactly four clearance corners")
    coordinates: list[tuple[float, float]] = []
    for corner in corners:
        if not isinstance(corner, dict):
            raise RetentionQuickReleaseTactileV42Error("clearance corner record is invalid")
        radial = corner.get("radial_clearance_mm")
        side = corner.get("anti_rotation_side_clearance_mm")
        if isinstance(radial, bool) or isinstance(side, bool) or not isinstance(radial, (int, float)) or not isinstance(side, (int, float)):
            raise RetentionQuickReleaseTactileV42Error("clearance corner coordinates must be numeric")
        pair = (float(radial), float(side))
        if any(not math.isfinite(value) or value <= 0.0 for value in pair):
            raise RetentionQuickReleaseTactileV42Error("clearance corner coordinates must be finite and positive")
        coordinates.append(pair)
    if len(set(coordinates)) != 4:
        raise RetentionQuickReleaseTactileV42Error("clearance corner coordinates must remain unique")
    return tuple(sorted(coordinates))


def _rectangle_binding(prior: v41.RetentionQuickReleaseTactileV41) -> tuple[float, float, float, float, str]:
    expected = _declared_rectangle()
    actual = _bound_rectangle(prior)
    if actual != expected:
        raise RetentionQuickReleaseTactileV42Error("bound clearance corners do not equal declared nominal/maximum tolerance rectangle")
    radial_values = sorted({pair[0] for pair in expected})
    side_values = sorted({pair[1] for pair in expected})
    payload = {
        "radial_nominal_mm": format(radial_values[0], ".12f"),
        "radial_maximum_mm": format(radial_values[1], ".12f"),
        "side_nominal_mm": format(side_values[0], ".12f"),
        "side_maximum_mm": format(side_values[1], ".12f"),
        "corners": [[format(r, ".12f"), format(s, ".12f")] for r, s in expected],
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return radial_values[0], radial_values[1], side_values[0], side_values[1], digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV42:
    prior: v41.RetentionQuickReleaseTactileV41
    radial_nominal_mm: float
    radial_maximum_mm: float
    side_nominal_mm: float
    side_maximum_mm: float
    tolerance_rectangle_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV42":
        self.prior.validate()
        values = _rectangle_binding(self.prior)
        expected = values[:4]
        actual = (self.radial_nominal_mm, self.radial_maximum_mm, self.side_nominal_mm, self.side_maximum_mm)
        if actual != expected:
            raise RetentionQuickReleaseTactileV42Error("clearance tolerance bounds are stale")
        if not isinstance(self.tolerance_rectangle_sha256, str) or _DIGEST_RE.fullmatch(self.tolerance_rectangle_sha256) is None:
            raise RetentionQuickReleaseTactileV42Error("tolerance rectangle digest must be canonical lowercase SHA-256")
        if self.tolerance_rectangle_sha256 != values[4]:
            raise RetentionQuickReleaseTactileV42Error("tolerance rectangle digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["declared_clearance_tolerance_rectangle"] = {
            "radial_nominal_mm": self.radial_nominal_mm,
            "radial_maximum_mm": self.radial_maximum_mm,
            "anti_rotation_side_nominal_mm": self.side_nominal_mm,
            "anti_rotation_side_maximum_mm": self.side_maximum_mm,
            "corner_count": 4,
            "tolerance_rectangle_sha256": self.tolerance_rectangle_sha256,
            "criterion": "BOUND_CLEARANCE_CORNERS_EQUAL_EXACT_CARTESIAN_PRODUCT_OF_DECLARED_NOMINAL_AND_MAXIMUM_CLEARANCE_AUTHORITIES",
            "scope": "DIGITAL_TOLERANCE_AUTHORITY_PROVENANCE_NOT_MANUFACTURED_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v42() -> RetentionQuickReleaseTactileV42:
    prior = v41.build_retention_quick_release_tactile_v41()
    radial_nominal, radial_maximum, side_nominal, side_maximum, digest = _rectangle_binding(prior)
    return RetentionQuickReleaseTactileV42(prior, radial_nominal, radial_maximum, side_nominal, side_maximum, digest).validate()
