from __future__ import annotations

"""Retention quick-release V22: bind the complete sixteenth-grid travel coverage.

V18-V21 distribute the interior 1/16 travel grid across independent midpoint,
quarter, eighth and odd-sixteenth screens. V22 audits those schedules as one set,
proving that every canonical interval has exactly the intended 17-point grid and
that no accumulated travel gap exceeds one sixteenth of the canonical interval.
This is schedule/provenance evidence only; it does not promote sampled B-rep
checks to continuous swept-volume or physical proof.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v12 as v12
from . import retention_quick_release_tactile_v18 as v18
from . import retention_quick_release_tactile_v19 as v19
from . import retention_quick_release_tactile_v20 as v20
from . import retention_quick_release_tactile_v21 as v21

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V22"
SUPERSEDES_SCHEMA = v21.SCHEMA
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class RetentionQuickReleaseTactileV22Error(ValueError):
    pass


def _complete_sixteenth_grid() -> tuple[float, ...]:
    canonical = v12._canonical_positions()
    if len(canonical) < 2 or any(b <= a for a, b in zip(canonical, canonical[1:])):
        raise RetentionQuickReleaseTactileV22Error("canonical release schedule cannot define complete grid")

    supplied = set(canonical)
    supplied.update(v18._midpoint_positions())
    supplied.update(v19._quarter_positions())
    supplied.update(v20._eighth_positions())
    supplied.update(v21._sixteenth_positions())

    expected: list[float] = []
    for interval_index, (a, b) in enumerate(zip(canonical, canonical[1:])):
        interval = [a + (b - a) * index / 16.0 for index in range(17)]
        if interval_index:
            interval = interval[1:]
        expected.extend(interval)

    actual = tuple(sorted(supplied))
    if len(actual) != len(expected) or any(not math.isclose(a, b, rel_tol=0.0, abs_tol=1e-12) for a, b in zip(actual, expected)):
        raise RetentionQuickReleaseTactileV22Error("accumulated travel screens do not form the complete sixteenth grid")
    return actual


def _coverage_evidence() -> tuple[int, float, float, str]:
    grid = _complete_sixteenth_grid()
    canonical = v12._canonical_positions()
    canonical_step = max((b - a) / 16.0 for a, b in zip(canonical, canonical[1:]))
    gaps = tuple(b - a for a, b in zip(grid, grid[1:]))
    if not gaps or any(not math.isfinite(gap) or gap <= 0.0 for gap in gaps):
        raise RetentionQuickReleaseTactileV22Error("complete travel grid contains an invalid gap")
    maximum_gap = max(gaps)
    if maximum_gap > canonical_step + 1e-12:
        raise RetentionQuickReleaseTactileV22Error("complete travel grid exceeds sixteenth-step gap bound")
    records = [format(position, ".12f") for position in grid]
    digest = sha256(json.dumps(records, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return len(grid), round(maximum_gap, 12), round(canonical_step, 12), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV22:
    prior: v21.RetentionQuickReleaseTactileV21
    complete_grid_point_count: int
    maximum_travel_gap_mm: float
    maximum_allowed_gap_mm: float
    schedule_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV22":
        self.prior.validate()
        point_count, maximum_gap, allowed_gap, digest = _coverage_evidence()
        if self.complete_grid_point_count != point_count:
            raise RetentionQuickReleaseTactileV22Error("complete-grid point count is stale")
        if not math.isfinite(self.maximum_travel_gap_mm) or not math.isclose(self.maximum_travel_gap_mm, maximum_gap, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV22Error("maximum travel gap is stale")
        if not math.isfinite(self.maximum_allowed_gap_mm) or not math.isclose(self.maximum_allowed_gap_mm, allowed_gap, rel_tol=0.0, abs_tol=1e-12):
            raise RetentionQuickReleaseTactileV22Error("maximum allowed travel gap is stale")
        if self.maximum_travel_gap_mm > self.maximum_allowed_gap_mm + 1e-12:
            raise RetentionQuickReleaseTactileV22Error("travel coverage exceeds sixteenth-step gap bound")
        if not _DIGEST_RE.fullmatch(self.schedule_sha256):
            raise RetentionQuickReleaseTactileV22Error("schedule digest must be canonical lowercase SHA-256")
        if self.schedule_sha256 != digest:
            raise RetentionQuickReleaseTactileV22Error("complete-grid schedule digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["complete_sixteenth_grid_audit"] = {
            "complete_grid_points_mm": list(_complete_sixteenth_grid()),
            "complete_grid_point_count": self.complete_grid_point_count,
            "maximum_travel_gap_mm": self.maximum_travel_gap_mm,
            "maximum_allowed_gap_mm": self.maximum_allowed_gap_mm,
            "schedule_sha256": self.schedule_sha256,
            "criterion": "EXACT_COMPLETE_SIXTEENTH_GRID_AND_NO_TRAVEL_GAP_ABOVE_ONE_SIXTEENTH_CANONICAL_INTERVAL",
            "scope": "SCHEDULE_PROVENANCE_AUDIT_OF_SAMPLED_DIGITAL_BREP_EVIDENCE_NOT_CONTINUOUS_SWEPT_VOLUME_TOLERANCE_STACK_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v22() -> RetentionQuickReleaseTactileV22:
    prior = v21.build_retention_quick_release_tactile_v21()
    point_count, maximum_gap, allowed_gap, digest = _coverage_evidence()
    return RetentionQuickReleaseTactileV22(prior, point_count, maximum_gap, allowed_gap, digest).validate()
