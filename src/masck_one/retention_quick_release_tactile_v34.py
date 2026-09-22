from __future__ import annotations

"""V34: screen eighth-travel positions at every clearance authority corner.

V30, V32 and V33 cover canonical, midpoint and quarter positions at all four
nominal/maximum clearance corners. V34 adds the four remaining eighth-grid
positions from V20, reducing the largest unsampled longitudinal interval at
those corners to one eighth of a canonical interval. This remains sampled
digital B-rep evidence, not continuous swept-volume or manufactured-stack proof.
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
from . import retention_quick_release_tactile_v20 as v20
from . import retention_quick_release_tactile_v30 as v30
from . import retention_quick_release_tactile_v33 as v33

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V34"
SUPERSEDES_SCHEMA = v33.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV34Error(ValueError):
    pass


def _eighth_positions() -> tuple[float, ...]:
    stations = v12._canonical_positions()
    if len(stations) < 2 or any(not math.isfinite(x) for x in stations):
        raise RetentionQuickReleaseTactileV34Error("canonical travel schedule is invalid")
    if any(b <= a for a, b in zip(stations, stations[1:])):
        raise RetentionQuickReleaseTactileV34Error("canonical travel schedule must be strictly increasing")
    positions = tuple(
        a + (b - a) * fraction
        for a, b in zip(stations, stations[1:])
        for fraction in (0.125, 0.375, 0.625, 0.875)
    )
    inherited = v20._eighth_positions()
    if len(positions) != len(inherited) or any(
        not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12)
        for a, b in zip(positions, inherited)
    ):
        raise RetentionQuickReleaseTactileV34Error(
            "eighth-travel schedule disagrees with inherited V20 authority"
        )
    return positions


def _eighth_evidence() -> tuple[int, int, float, float, str]:
    mechanism = v1.build_retention_quick_release_tactile()
    stations = v12._canonical_positions()
    positions = _eighth_positions()
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
                            raise RetentionQuickReleaseTactileV34Error(
                                f"eighth-travel pose at clearance corner {corner} collides with rigid guide"
                            )
                        maximum = max(maximum, overlap)
                        records.append(
                            (corner, family, format(x, ".12f"), format(y, ".12f"),
                             format(z, ".12f"), format(overlap, ".12f"))
                        )
    except RetentionQuickReleaseTactileV34Error:
        raise
    except Exception as exc:
        raise RetentionQuickReleaseTactileV34Error(
            "eighth-travel evidence query failed"
        ) from exc
    max_interval = max((b - a for a, b in zip(stations, stations[1:])), default=0.0) / 8.0
    payload = {"positions": [format(x, ".12f") for x in positions], "records": records}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return transverse_samples, len(records), round(maximum, 12), max_interval, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV34:
    prior: v33.RetentionQuickReleaseTactileV33
    eighth_position_count: int
    transverse_sample_count: int
    pose_count: int
    max_rigid_guide_intersection_mm3: float
    max_unsampled_longitudinal_interval_mm: float
    evidence_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV34":
        self.prior.validate()
        samples, poses, maximum, interval, digest = _eighth_evidence()
        expected = 4 * (len(v12._canonical_positions()) - 1)
        if self.eighth_position_count != expected or self.eighth_position_count != len(_eighth_positions()):
            raise RetentionQuickReleaseTactileV34Error("eighth-travel position count is stale")
        if self.transverse_sample_count != samples or samples != self.prior.transverse_sample_count:
            raise RetentionQuickReleaseTactileV34Error("eighth-travel transverse sample count is stale")
        if self.pose_count != poses or poses != samples * self.eighth_position_count:
            raise RetentionQuickReleaseTactileV34Error("eighth-travel pose count is stale")
        if not math.isfinite(self.max_rigid_guide_intersection_mm3) or self.max_rigid_guide_intersection_mm3 != maximum or maximum > 0.0:
            raise RetentionQuickReleaseTactileV34Error("eighth-travel rigid-guide intersection must remain zero")
        if not math.isfinite(self.max_unsampled_longitudinal_interval_mm) or not math.isclose(
            self.max_unsampled_longitudinal_interval_mm, interval, rel_tol=0.0, abs_tol=1e-12
        ):
            raise RetentionQuickReleaseTactileV34Error("eighth-travel longitudinal resolution evidence is stale")
        if not isinstance(self.evidence_sha256, str) or _DIGEST_RE.fullmatch(self.evidence_sha256) is None or self.evidence_sha256 != digest:
            raise RetentionQuickReleaseTactileV34Error("eighth-travel evidence digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["eighth_travel_clearance_corner_screen"] = {
            "eighth_position_count": self.eighth_position_count,
            "transverse_sample_count": self.transverse_sample_count,
            "pose_count": self.pose_count,
            "max_rigid_guide_intersection_mm3": self.max_rigid_guide_intersection_mm3,
            "max_unsampled_longitudinal_interval_mm": self.max_unsampled_longitudinal_interval_mm,
            "evidence_sha256": self.evidence_sha256,
            "criterion": "NO_POSITIVE_RAW_KERNEL_RIGID_GUIDE_INTERSECTION_AT_ANY_EIGHTH_TRAVEL_POSE_OR_CLEARANCE_AUTHORITY_CORNER",
            "scope": "SAMPLED_DIGITAL_BREP_SCREEN_NOT_CONTINUOUS_SWEPT_VOLUME_OR_MANUFACTURING_TOLERANCE_STACK",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v34() -> RetentionQuickReleaseTactileV34:
    prior = v33.build_retention_quick_release_tactile_v33()
    samples, poses, maximum, interval, digest = _eighth_evidence()
    return RetentionQuickReleaseTactileV34(
        prior=prior,
        eighth_position_count=len(_eighth_positions()),
        transverse_sample_count=samples,
        pose_count=poses,
        max_rigid_guide_intersection_mm3=maximum,
        max_unsampled_longitudinal_interval_mm=interval,
        evidence_sha256=digest,
    ).validate()
