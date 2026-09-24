from __future__ import annotations

"""V28: prove the realized transverse meshes actually implement the bound V27 schedule.

V27 binds sampler constants and V26 binds realized mesh identity, but those contracts were
not cross-bound. A sampler implementation could therefore drift while retaining the same
constants, symmetry and sample count. V28 independently reconstructs the expected aligned
and interstitial point sets from the accepted schedule and declared clearances, then requires
exact quantized set equality with the realized V16/V17 meshes.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile as v1
from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v27 as v27

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V28"
SUPERSEDES_SCHEMA = v27.SCHEMA
_QUANTUM = 10**12
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_EXPECTED_ANGLES = 32


class RetentionQuickReleaseTactileV28Error(ValueError):
    pass


def _key(point: tuple[float, float]) -> tuple[int, int]:
    y, z = point
    if not (math.isfinite(y) and math.isfinite(z)):
        raise RetentionQuickReleaseTactileV28Error("transverse mesh contains non-finite coordinate")
    return round(y * _QUANTUM), round(z * _QUANTUM)


def _expected_aligned(radial: float, side: float) -> set[tuple[int, int]]:
    points: list[tuple[float, float]] = [(0.0, 0.0)]
    for ring in range(1, 9):
        radius = radial * ring / 8.0
        for index in range(_EXPECTED_ANGLES):
            theta = 2.0 * math.pi * index / _EXPECTED_ANGLES
            point = (radius * math.cos(theta), radius * math.sin(theta))
            if abs(point[0]) <= side + 1e-12:
                points.append(point)
    clipped_side = min(side, radial)
    points.extend(((clipped_side, 0.0), (-clipped_side, 0.0)))
    if side < radial:
        z_intersection = math.sqrt(max(0.0, radial * radial - side * side))
        points.extend(((side, z_intersection), (side, -z_intersection), (-side, z_intersection), (-side, -z_intersection)))
    return {_key(point) for point in points}


def _expected_interstitial(radial: float, side: float) -> set[tuple[int, int]]:
    points: list[tuple[float, float]] = []
    phase = math.pi / _EXPECTED_ANGLES
    for ring in range(8):
        radius = radial * (ring + 0.5) / 8.0
        for index in range(_EXPECTED_ANGLES):
            theta = phase + 2.0 * math.pi * index / _EXPECTED_ANGLES
            point = (radius * math.cos(theta), radius * math.sin(theta))
            if abs(point[0]) <= side + 1e-12:
                points.append(point)
    return {_key(point) for point in points}


def _implementation_binding() -> tuple[int, int, str]:
    radial = float(v1.SPOOL_RAIL_RADIAL_CLEARANCE_MM)
    side = float(v1.ANTI_ROTATION_SIDE_CLEARANCE_MM)
    if not all(math.isfinite(value) and value > 0.0 for value in (radial, side)):
        raise RetentionQuickReleaseTactileV28Error("declared transverse clearances must be finite and positive")
    expected_aligned = _expected_aligned(radial, side)
    expected_interstitial = _expected_interstitial(radial, side)
    actual_aligned = {_key(point) for point in v16._dense_samples(radial, side)}
    actual_interstitial = {_key(point) for point in v17._interstitial_samples(radial, side)}
    if actual_aligned != expected_aligned:
        raise RetentionQuickReleaseTactileV28Error("realized aligned mesh no longer implements the bound V27 schedule")
    if actual_interstitial != expected_interstitial:
        raise RetentionQuickReleaseTactileV28Error("realized interstitial mesh no longer implements the bound V27 schedule")
    records = {
        "aligned": sorted(actual_aligned),
        "interstitial": sorted(actual_interstitial),
        "radial_clearance": format(radial, ".12f"),
        "side_clearance": format(side, ".12f"),
    }
    digest = sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return len(actual_aligned), len(actual_interstitial), digest


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV28:
    prior: v27.RetentionQuickReleaseTactileV27
    aligned_bound_count: int
    interstitial_bound_count: int
    implementation_binding_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV28":
        self.prior.validate()
        aligned, interstitial, digest = _implementation_binding()
        if self.aligned_bound_count != aligned or self.interstitial_bound_count != interstitial:
            raise RetentionQuickReleaseTactileV28Error("realized mesh bound counts are stale")
        if not isinstance(self.implementation_binding_sha256, str) or _DIGEST_RE.fullmatch(self.implementation_binding_sha256) is None:
            raise RetentionQuickReleaseTactileV28Error("implementation binding digest must be canonical lowercase SHA-256")
        if self.implementation_binding_sha256 != digest:
            raise RetentionQuickReleaseTactileV28Error("implementation binding digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_sampler_implementation_binding"] = {
            "aligned_bound_count": self.aligned_bound_count,
            "interstitial_bound_count": self.interstitial_bound_count,
            "implementation_binding_sha256": self.implementation_binding_sha256,
            "criterion": "REALIZED_TRANSVERSE_MESHES_EXACTLY_IMPLEMENT_BOUND_V27_SCHEDULE",
            "scope": "SAMPLED_DIGITAL_BREP_IMPLEMENTATION_PROVENANCE_NOT_CONTINUOUS_CLEARANCE_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v28() -> RetentionQuickReleaseTactileV28:
    prior = v27.build_retention_quick_release_tactile_v27()
    aligned, interstitial, digest = _implementation_binding()
    return RetentionQuickReleaseTactileV28(prior, aligned, interstitial, digest).validate()
