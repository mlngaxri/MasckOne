from __future__ import annotations

"""V43: bind the declared clearance rectangle to independent metric invariants.

V42 proves the four bound clearance corners equal the declared Cartesian product.
V43 additionally derives the radial and anti-rotation tolerance spans, rectangle
area and diagonal from those bounds and binds them to V42 evidence. This catches
unit/axis or bound drift that can preserve a four-corner set while changing the
engineering tolerance window. This remains digital provenance, not physical
validation or manufactured tolerance-stack closure.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v42 as v42

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V43"
SUPERSEDES_SCHEMA = v42.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV43Error(ValueError):
    pass


def _rectangle_metrics(prior: v42.RetentionQuickReleaseTactileV42) -> tuple[float, float, float, float, str]:
    prior.validate()
    radial_span = prior.radial_maximum_mm - prior.radial_nominal_mm
    side_span = prior.side_maximum_mm - prior.side_nominal_mm
    if not all(math.isfinite(x) and x > 0.0 for x in (radial_span, side_span)):
        raise RetentionQuickReleaseTactileV43Error("clearance tolerance spans must be finite and positive")
    area = radial_span * side_span
    diagonal = math.hypot(radial_span, side_span)
    if not math.isfinite(area) or not math.isfinite(diagonal) or area <= 0.0 or diagonal <= 0.0:
        raise RetentionQuickReleaseTactileV43Error("clearance tolerance rectangle metrics are invalid")
    payload = {
        "radial_span_mm": format(radial_span, ".12f"),
        "side_span_mm": format(side_span, ".12f"),
        "rectangle_area_mm2": format(area, ".12f"),
        "rectangle_diagonal_mm": format(diagonal, ".12f"),
        "v42_tolerance_rectangle_sha256": prior.tolerance_rectangle_sha256,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return radial_span, side_span, area, diagonal, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV43:
    prior: v42.RetentionQuickReleaseTactileV42
    radial_span_mm: float
    side_span_mm: float
    rectangle_area_mm2: float
    rectangle_diagonal_mm: float
    tolerance_metric_binding_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV43":
        expected = _rectangle_metrics(self.prior)
        actual = (self.radial_span_mm, self.side_span_mm, self.rectangle_area_mm2, self.rectangle_diagonal_mm)
        if actual != expected[:4]:
            raise RetentionQuickReleaseTactileV43Error("clearance tolerance rectangle metrics are stale")
        if (
            not isinstance(self.tolerance_metric_binding_sha256, str)
            or _DIGEST_RE.fullmatch(self.tolerance_metric_binding_sha256) is None
            or self.tolerance_metric_binding_sha256 != expected[4]
        ):
            raise RetentionQuickReleaseTactileV43Error("tolerance metric binding digest is stale or invalid")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["declared_clearance_tolerance_metrics"] = {
            "radial_span_mm": self.radial_span_mm,
            "anti_rotation_side_span_mm": self.side_span_mm,
            "rectangle_area_mm2": self.rectangle_area_mm2,
            "rectangle_diagonal_mm": self.rectangle_diagonal_mm,
            "tolerance_metric_binding_sha256": self.tolerance_metric_binding_sha256,
            "criterion": "TOLERANCE_RECTANGLE_METRICS_RECONSTRUCT_EXACTLY_FROM_V42_DECLARED_BOUNDS",
            "scope": "DIGITAL_TOLERANCE_AUTHORITY_PROVENANCE_NOT_MANUFACTURED_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v43() -> RetentionQuickReleaseTactileV43:
    prior = v42.build_retention_quick_release_tactile_v42()
    radial, side, area, diagonal, digest = _rectangle_metrics(prior)
    return RetentionQuickReleaseTactileV43(prior, radial, side, area, diagonal, digest).validate()
