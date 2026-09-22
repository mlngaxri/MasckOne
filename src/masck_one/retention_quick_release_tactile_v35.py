from __future__ import annotations

"""V35: screen sixteenth-travel positions at every clearance authority corner.

V30 and V32-V34 cover the 1/8 longitudinal grid at all four nominal/maximum
clearance corners. V35 adds the eight odd sixteenth-grid positions from V21,
reducing the largest unsampled longitudinal interval at those corners to one
sixteenth of a canonical interval. This remains sampled digital B-rep evidence,
not continuous swept-volume or manufactured-stack proof.
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
from . import retention_quick_release_tactile_v21 as v21
from . import retention_quick_release_tactile_v30 as v30
from . import retention_quick_release_tactile_v34 as v34

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V35"
SUPERSEDES_SCHEMA = v34.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV35Error(ValueError):
    pass


def _sixteenth_positions() -> tuple[float, ...]:
    stations = v12._canonical_positions()
    if len(stations) < 2 or any(not math.isfinite(x) for x in stations):
        raise RetentionQuickReleaseTactileV35Error("canonical travel schedule is invalid")
    if any(b <= a for a, b in zip(stations, stations[1:])):
        raise RetentionQuickReleaseTactileV35Error("canonical travel schedule must be strictly increasing")
    positions = tuple(
        a + (b - a) * fraction
        for a, b in zip(stations, stations[1:])
        for fraction in tuple(index / 16.0 for index in range(1, 16, 2))
    )
    inherited = v21._sixteenth_positions()
    if len(positions) != len(inherited) or any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
        for a, b in zip(positions, inherited)
    ):
        raise RetentionQuickReleaseTactileV35Error(
            "sixteenth-travel schedule disagrees with inherited V21 authority"
        )
    return positions


def _sixteenth_evidence() -> tuple[int, int, float, float, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    stations = v12._canonical_positions()
    positions = _sixteenth_positions()
    records: list[tuple[str, str, str, str, str, str]] = []
    transverse_samples = 0
    maximum = 0.0
    try:
        for corner, radial, side in v30._clearance_corners(mechanism):
            for family, samples in (
                ("aligned", v16._dense_samples(radial, side)),
                ("interstitial", v17._interstitial_samples(radial, side)),
            ):
                transverse_samples += len(samples)
                for y, z in samples:
                    for x in positions:
                        overlap = v30._raw_intersection(
                            mechanism.slider.translate((x, y, z)), mechanism.guide
                        )
                        if overlap > 0.0:
                            raise RetentionQuickReleaseTactileV35Error(
                                f"sixteenth-travel pose at clearance corner {corner} collides with rigid guide"
                            )
                        maximum = max(maximum, overlap)
                        records.append(
                            (corner, family, format(x, ".12f"), format(y, ".12f"),
                             format(z, ".12f"), format(overlap, ".12f"))
                        )
    except RetentionQuickReleaseTactileV35Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV35Error(
            "sixteenth-travel evidence query failed"
        ) from exc
    max_interval = max((b - a for a, b in zip(stations, stations[1:])), default=0.0) / 16.0
    payload = {"positions": [format(x, ".12f") for x in positions], "records": records}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return transverse_samples, len(records), round(maximum, 12), max_interval, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV35:
    prior: v34.RetentionQuickReleaseTactileV34
    sixteenth_position_count: int
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    max_unsampled_longitudinal_interval_mm: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV35":
        self.prior.validate()
        samples, poses, maximum, interval, digest = _sixteenth_evidence()
        expected = 8 * (len(v12._canonical_positions()) - 1)
        if self.sixteenth_position_count != expected or self.sixteenth_position_count != len(_sixteenth_positions()):
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel position count is stale")
        if self.transverse_sample_count != samples or samples != self.prior.transverse_sample_count:
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel transverse sample count is stale")
        if self.pose_count != poses or poses != samples * self.sixteenth_position_count:
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or self.max_rigid_guide_intersection_mm3 != maximum or maximum > 0.0:
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel rigid-guide intersection must remain zero")
        if not math.isfinite(self.max_unsampled_longitudinal_interval_mm) or not math.isclose(
            self.max_unsampled_longitudinal_interval_mm, interval, rel_tol=0.0, abs_tol=1e-12
        ):
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel longitudinal resolution evidence is stale")
        if not isinstance(self.evidence_sha256, str) or _DIGEST_RE.fullmatch(self.evidence_sha256) is None or self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV35Error("sixteenth-travel evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["sixteenth_travel_clearance_corner_screen"] = {
            "sixteenth_position_count": self.sixteenth_position_count,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "max_unsampled_longitudinal_interval_mm": self.max_unsampled_longitudinal_interval_mm,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RAW_KERNEL_RIGID_GUIDE_INTERSECTION_AT_ANY_SIXTEENTH_TRAVEL_POSE_OR_CLEARANCE_AUTHORITY_CORNER",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v35() -> RetentionQuickReleaseTactileV35:
    prior = v34.build_retention_quick_release_tactile_v34()
    samples, poses, maximum, interval, digest = _sixteenth_evidence()
    return RetentionQuickReleaseTactileV35(
        prior=prior,
        sixteenth_position_count=len(_sixteenth_positions()),
        transverse_sample_count=samples,
        pose_count=poses,
        max_rigid_guide_intersection_mm3=maximum,
        max_unsampled_longitudinal_interval_mm=interval,
        evidence_sha256=digest,
    ).validate()
