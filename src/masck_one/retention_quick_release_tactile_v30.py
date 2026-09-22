from __future__ import annotations

"""V30: screen coupled nominal/maximum transverse-clearance authority corners.

V29 screens the maximum radial/side pair. Clearance response is not assumed monotonic
for arbitrary B-rep guide geometry, so V30 independently screens all four combinations
of nominal and accepted-maximum radial/side authority across both transverse meshes and
the canonical V12 travel schedule. This is sampled digital packaging evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v29 as v29

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V30"
SUPERSEDES_SCHEMA = v29.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV30Error(ValueError):
    pass


def _clearance_corners(mechanism: v1.RetentionQuickReleaseTactile) -> tuple[tuple[str, float, float], ...]:
    nr = float(mechanism.rail_radial_clearance_mm)
    ns = float(mechanism.anti_rotation_side_clearance_mm)
    mr = float(v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM)
    ms = float(v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM)
    if not all(math.isfinite(x) and x > 0.0 for x in (nr, ns, mr, ms)) or mr < nr or ms < ns:
        raise RetentionQuickReleaseTactileV30Error("invalid clearance authority ordering")
    return (("nominal_nominal", nr, ns), ("nominal_max_side", nr, ms), ("max_radial_nominal", mr, ns), ("max_max", mr, ms))


def _raw_intersection(first, second) -> float:
    """Return kernel overlap without V1's generic small-volume clamp.

    This audit is fail-closed at the B-rep boundary. Both operands must remain one valid,
    positive-volume solid before OCC is queried. That prevents a malformed/empty sampler
    operand from being interpreted as a legitimate zero-clearance result.
    """
    try:
        first_shape = first.val()
        second_shape = second.val()
        for shape in (first_shape, second_shape):
            solids = shape.Solids()
            volume = float(shape.Volume())
            if not shape.isValid() or len(solids) != 1 or not math.isfinite(volume) or volume <= 0.0:
                raise RetentionQuickReleaseTactileV30Error("invalid raw clearance-corner operand")
        result = first_shape.intersect(second_shape)
        if not result.isValid():
            raise RetentionQuickReleaseTactileV30Error("invalid raw clearance-corner intersection result")
        value = float(result.Volume())
    except RetentionQuickReleaseTactileV30Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV30Error("raw clearance-corner intersection query failed") from exc
    if not math.isfinite(value) or value < 0.0:
        raise RetentionQuickReleaseTactileV30Error("invalid raw clearance-corner intersection")
    return value


def _corner_evidence() -> tuple[int, int, float, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    positions = v12._canonical_positions()
    records: list[tuple[str, str, str, str, str, str]] = []
    sample_count = 0
    maximum = 0.0
    try:
        for corner, radial, side in _clearance_corners(mechanism):
            for family, samples in (("aligned", v16._dense_samples(radial, side)), ("interstitial", v17._interstitial_samples(radial, side))):
                sample_count += len(samples)
                for y, z in samples:
                    for x in positions:
                        overlap = _raw_intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                        if overlap > 0.0:
                            raise RetentionQuickReleaseTactileV30Error(f"clearance authority corner {corner} collides with rigid guide")
                        maximum = max(maximum, overlap)
                        records.append((corner, family, format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV30Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV30Error("clearance-corner evidence query failed") from exc
    payload = {"corners": [(n, format(r, ".12f"), format(s, ".12f")) for n, r, s in _clearance_corners(mechanism)], "records": records}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return sample_count, len(records), round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV30:
    prior: v29.RetentionQuickReleaseTactileV29
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV30":
        self.prior.validate()
        samples, poses, maximum, digest = _corner_evidence()
        if self.transverse_sample_count != samples:
            raise RetentionQuickReleaseTactileV30Error("clearance-corner sample count is stale")
        if self.pose_count != poses or poses != samples * len(v12._canonical_positions()):
            raise RetentionQuickReleaseTactileV30Error("clearance-corner pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or self.max_rigid_guide_intersection_mm3 != maximum:
            raise RetentionQuickReleaseTactileV30Error("clearance-corner maximum intersection is stale")
        if maximum > 0.0:
            raise RetentionQuickReleaseTactileV30Error("clearance-corner rigid-guide intersection must remain zero")
        if not isinstance(self.evidence_sha256, str) or _DIGEST_RE.fullmatch(self.evidence_sha256) is None or self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV30Error("clearance-corner evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["clearance_authority_corner_screen"] = {"corner_count": 4, "transverse_sample_count": self.transverse_sample_count, "pose_count": self.pose_count, "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3, "evidence_sha256": self.evidence_sha256, "criterion": "NO_POSITIVE_RAW_KERNEL_RIGID_GUIDE_INTERSECTION_AT_ANY_NOMINAL_MAX_CLEARANCE_AUTHORITY_CORNER", "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK"}
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v30() -> RetentionQuickReleaseTactileV30:
    prior = v29.build_retention_quick_release_tactile_v29()
    samples, poses, maximum, digest = _corner_evidence()
    return RetentionQuickReleaseTactileV30(prior, samples, poses, maximum, digest).validate()
