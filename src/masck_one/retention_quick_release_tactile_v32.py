from __future__ import annotations

"""V32: screen longitudinal interstation midpoints at every clearance authority corner.

V30 screens the canonical V12 travel stations across both transverse meshes and all four
nominal/maximum clearance corners. A collision can exist between adjacent longitudinal
stations without appearing at either endpoint. V32 therefore screens every adjacent
station midpoint with the same raw-kernel, fail-closed collision path. This materially
halves the maximum unsampled longitudinal interval, but remains sampled digital evidence
rather than continuous swept-volume proof.
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
from . import retention_quick_release_tactile_v30 as v30
from . import retention_quick_release_tactile_v31 as v31

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V32"
SUPERSEDES_SCHEMA = v31.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV32Error(ValueError):
    pass


def _midpoint_positions() -> tuple[float, ...]:
    stations = v12._canonical_positions()
    if len(stations) < 2 or any(not math.isfinite(x) for x in stations):
        raise RetentionQuickReleaseTactileV32Error("canonical travel schedule is invalid")
    if any(b <= a for a, b in zip(stations, stations[1:])):
        raise RetentionQuickReleaseTactileV32Error("canonical travel schedule must be strictly increasing")
    return tuple((a + b) / 2.0 for a, b in zip(stations, stations[1:]))


def _midpoint_evidence() -> tuple[int, int, float, float, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    stations = v12._canonical_positions()
    midpoints = _midpoint_positions()
    records: list[tuple[str, str, str, str, str, str]] = []
    transverse_samples = 0
    maximum = 0.0
    try:
        for corner, radial, side in v30._clearance_corners(mechanism):
            for family, samples in (("aligned", v16._dense_samples(radial, side)), ("interstitial", v17._interstitial_samples(radial, side))):
                transverse_samples += len(samples)
                for y, z in samples:
                    for x in midpoints:
                        overlap = v30._raw_intersection(mechanism.slider.translate((x, y, z)), mechanism.guide)
                        if overlap > 0.0:
                            raise RetentionQuickReleaseTactileV32Error(
                                f"interstation midpoint at clearance corner {corner} collides with rigid guide"
                            )
                        maximum = max(maximum, overlap)
                        records.append((corner, family, format(x, ".12f"), format(y, ".12f"), format(z, ".12f"), format(overlap, ".12f")))
    except RetentionQuickReleaseTactileV32Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV32Error("interstation midpoint evidence query failed") from exc
    max_interval = max((b - a for a, b in zip(stations, stations[1:])), default=0.0) / 2.0
    payload = {"midpoints": [format(x, ".12f") for x in midpoints], "records": records}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return transverse_samples, len(records), round(maximum, 12), max_interval, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV32:
    prior: v31.RetentionQuickReleaseTactileV31
    midpoint_count: int
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    max_unsampled_longitudinal_interval_mm: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV32":
        self.prior.validate()
        samples, poses, maximum, interval, digest = _midpoint_evidence()
        expected_midpoints = len(v12._canonical_positions()) - 1
        if self.midpoint_count != expected_midpoints or self.midpoint_count != len(_midpoint_positions()):
            raise RetentionQuickReleaseTactileV32Error("interstation midpoint count is stale")
        if self.transverse_sample_count != samples or samples != self.prior.combined_unique_count:
            raise RetentionQuickReleaseTactileV32Error("interstation transverse sample count is stale")
        if self.pose_count != poses or poses != samples * self.midpoint_count:
            raise RetentionQuickReleaseTactileV32Error("interstation midpoint pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or self.max_rigid_guide_intersection_mm3 != maximum or maximum > 0.0:
            raise RetentionQuickReleaseTactileV32Error("interstation midpoint rigid-guide intersection must remain zero")
        if not math.isfinite(self.max_unsampled_longitudinal_interval_mm) or not math.isclose(self.max_unsampled_longitudinal_interval_mm, interval, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV32Error("interstation longitudinal resolution evidence is stale")
        if not isinstance(self.evidence_sha256, str) or _DIGEST_RE.fullmatch(self.evidence_sha256) is None or self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV32Error("interstation midpoint evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["interstation_midpoint_clearance_screen"] = {
            "midpoint_count": self.midpoint_count,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "max_unsampled_longitudinal_interval_mm": self.max_unsampled_longitudinal_interval_mm,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RAW_KERNEL_RIGID_GUIDE_INTERSECTION_AT_ANY_ADJACENT_STATION_MIDPOINT_OR_CLEARANCE_AUTHORITY_CORNER",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v32() -> RetentionQuickReleaseTactileV32:
    prior = v31.build_retention_quick_release_tactile_v31()
    samples, poses, maximum, interval, digest = _midpoint_evidence()
    return RetentionQuickReleaseTactileV32(
        prior=prior,
        midpoint_count=len(_midpoint_positions()),
        transverse_sample_count=samples,
        pose_count=poses,
        max_rigid_guide_intersection_mm3=maximum,
        max_unsampled_longitudinal_interval_mm=interval,
        evidence_sha256=digest,
    ).validate()
