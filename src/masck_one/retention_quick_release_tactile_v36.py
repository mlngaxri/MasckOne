from __future__ import annotations

"""V36: prove the sampled clearance-corner travel lattice has no longitudinal holes.

V30, V32, V33, V34 and V35 split each canonical V12 travel interval across
stations, halves, quarters, eighths and odd sixteenths. This layer reconstructs
the expected 1/16 lattice independently and requires the union of those
authorities to match it exactly. It prevents a future refactor from silently
removing, duplicating or displacing a longitudinal sample while retaining
plausible per-layer counts. This is a sampling-completeness contract, not
continuous swept-volume proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v32 as v32
from . import retention_quick_release_tactile_v33 as v33
from . import retention_quick_release_tactile_v34 as v34
from . import retention_quick_release_tactile_v35 as v35

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V36"
SUPERSEDES_SCHEMA = v35.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TOL = 1e-12


class RetentionQuickReleaseTactileV36Error(ValueError):
    pass


def _expected_lattice() -> tuple[float, ...]:
    stations = v12._canonical_positions()
    if len(stations) < 2 or any(not math.isfinite(x) for x in stations):
        raise RetentionQuickReleaseTactileV36Error("canonical travel schedule is invalid")
    if any(b <= a for a, b in zip(stations, stations[1:])):
        raise RetentionQuickReleaseTactileV36Error("canonical travel schedule must be strictly increasing")
    values = [stations[0]]
    for a, b in zip(stations, stations[1:]):
        values.extend(a + (b - a) * index / 16.0 for index in range(1, 17))
    return tuple(values)


def _actual_lattice() -> tuple[float, ...]:
    values = (
        tuple(v12._canonical_positions())
        + tuple(v32._midpoints())
        + tuple(v33._quarter_positions())
        + tuple(v34._eighth_positions())
        + tuple(v35._sixteenth_positions())
    )
    ordered = sorted(values)
    for left, right in zip(ordered, ordered[1:]):
        if math.isclose(left, right, rel_tol=0.0, abs_tol=_TOL):
            raise RetentionQuickReleaseTactileV36Error("longitudinal authority contains duplicate samples")
    return tuple(ordered)


def _coverage_evidence() -> tuple[int, float, str]:
    expected = _expected_lattice()
    actual = _actual_lattice()
    if len(actual) != len(expected):
        raise RetentionQuickReleaseTactileV36Error("sixteenth lattice sample count is incomplete")
    if any(not math.isclose(a, e, rel_tol=0.0, abs_tol=_TOL) for a, e in zip(actual, expected)):
        raise RetentionQuickReleaseTactileV36Error("longitudinal authorities do not exactly cover the sixteenth lattice")
    max_gap = max((b - a for a, b in zip(actual, actual[1:])), default=0.0)
    payload = {"positions": [format(x, ".12f") for x in actual], "max_gap_mm": format(max_gap, ".12f")}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return len(actual), max_gap, digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV36:
    prior: v35.RetentionQuickReleaseTactileV35
    complete_lattice_position_count: int
    max_longitudinal_sample_gap_mm: float
    coverage_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV36":
        self.prior.validate()
        count, gap, digest = _coverage_evidence()
        if self.complete_lattice_position_count != count:
            raise RetentionQuickReleaseTactileV36Error("complete lattice position count is stale")
        if not math.isfinite(self.max_longitudinal_sample_gap_mm) or not math.isclose(
            self.max_longitudinal_sample_gap_mm, gap, rel_tol=0.0, abs_tol=_TOL
        ):
            raise RetentionQuickReleaseTactileV36Error("longitudinal sample-gap evidence is stale")
        if not math.isclose(
            gap,
            self.prior.max_unsampled_longitudinal_interval_mm,
            rel_tol=0.0,
            abs_tol=_TOL,
        ):
            raise RetentionQuickReleaseTactileV36Error(
                "complete lattice gap disagrees with V35 collision-screen resolution"
            )
        if not isinstance(self.coverage_sha256, str) or _DIGEST_RE.fullmatch(self.coverage_sha256) is None or self.coverage_sha256 != digest:
            raise RetentionQuickReleaseTactileV36Error("lattice coverage digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["longitudinal_sampling_completeness"] = {
            "complete_lattice_position_count": self.complete_lattice_position_count,
            "max_longitudinal_sample_gap_mm": self.max_longitudinal_sample_gap_mm,
            "coverage_sha256": self.coverage_sha256,
            "criterion": "EXACT_UNION_OF_STATION_HALF_QUARTER_EIGHTH_AND_ODD_SIXTEENTH_AUTHORITIES_EQUALS_COMPLETE_SIXTEENTH_LATTICE_AND_MATCHES_V35_COLLISION_SCREEN_RESOLUTION",
            "scope": "SAMPLED_DIGITAL_LONGITUDINAL_COVERAGE_NOT_CONTINUOUS_SWEPT_VOLUME",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_retention_quick_release_tactile_v36() -> RetentionQuickReleaseTactileV36:
    prior = v35.build_retention_quick_release_tactile_v35()
    count, gap, digest = _coverage_evidence()
    return RetentionQuickReleaseTactileV36(
        prior=prior,
        complete_lattice_position_count=count,
        max_longitudinal_sample_gap_mm=gap,
        coverage_sha256=digest,
    ).validate()
