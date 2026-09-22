from __future__ import annotations

"""V27: fail closed if the accepted transverse sampler is silently coarsened."""

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re

from . import retention_quick_release_tactile_v16 as v16
from . import retention_quick_release_tactile_v17 as v17
from . import retention_quick_release_tactile_v26 as v26

SCHEMA = "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V27"
SUPERSEDES_SCHEMA = v26.SCHEMA
_EXPECTED_ALIGNED_RADII = tuple(index / 8.0 for index in range(9))
_EXPECTED_INTERSTITIAL_RADII = tuple((index + 0.5) / 8.0 for index in range(8))
_EXPECTED_ANGLES = 32
_EXPECTED_PHASE_RAD = math.pi / _EXPECTED_ANGLES
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_TOL = 1e-15


class RetentionQuickReleaseTactileV27Error(ValueError):
    pass


def _resolution_binding() -> str:
    if tuple(v16.POLAR_RADII) != _EXPECTED_ALIGNED_RADII:
        raise RetentionQuickReleaseTactileV27Error("aligned radial schedule was coarsened or changed")
    if int(v16.POLAR_ANGLES) != _EXPECTED_ANGLES:
        raise RetentionQuickReleaseTactileV27Error("aligned angular resolution was coarsened or changed")
    if tuple(v17.INTERSTITIAL_RADII) != _EXPECTED_INTERSTITIAL_RADII:
        raise RetentionQuickReleaseTactileV27Error("interstitial radial schedule was coarsened or changed")
    if int(v17.INTERSTITIAL_ANGLES) != _EXPECTED_ANGLES:
        raise RetentionQuickReleaseTactileV27Error("interstitial angular resolution was coarsened or changed")
    if not math.isclose(float(v17.ANGLE_PHASE_RAD), _EXPECTED_PHASE_RAD, rel_tol=0.0, abs_tol=_TOL):
        raise RetentionQuickReleaseTactileV27Error("interstitial angular phase no longer bisects aligned rays")
    records = {
        "aligned_radii": [format(value, ".12f") for value in _EXPECTED_ALIGNED_RADII],
        "aligned_angles": _EXPECTED_ANGLES,
        "interstitial_radii": [format(value, ".12f") for value in _EXPECTED_INTERSTITIAL_RADII],
        "interstitial_angles": _EXPECTED_ANGLES,
        "interstitial_phase_rad": format(_EXPECTED_PHASE_RAD, ".15f"),
        "max_radial_step_fraction": format(1.0 / 8.0, ".12f"),
        "max_aligned_angular_step_rad": format(2.0 * math.pi / _EXPECTED_ANGLES, ".15f"),
    }
    return sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class RetentionQuickReleaseTactileV27:
    prior: v26.RetentionQuickReleaseTactileV26
    sampler_resolution_sha256: str

    def validate(self) -> "RetentionQuickReleaseTactileV27":
        self.prior.validate()
        digest = _resolution_binding()
        if not isinstance(self.sampler_resolution_sha256, str) or _DIGEST_RE.fullmatch(self.sampler_resolution_sha256) is None:
            raise RetentionQuickReleaseTactileV27Error("sampler resolution digest must be canonical lowercase SHA-256")
        if self.sampler_resolution_sha256 != digest:
            raise RetentionQuickReleaseTactileV27Error("sampler resolution digest is stale")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = self.prior.manifest()
        payload.pop("manifest_sha256", None)
        payload["schema"] = SCHEMA
        payload["supersedes_schema"] = SUPERSEDES_SCHEMA
        payload["transverse_sampler_resolution_binding"] = {
            "aligned_radial_interval_count": 8,
            "aligned_angular_ray_count": _EXPECTED_ANGLES,
            "interstitial_radial_ring_count": 8,
            "interstitial_angular_ray_count": _EXPECTED_ANGLES,
            "interstitial_half_ray_phase_rad": _EXPECTED_PHASE_RAD,
            "sampler_resolution_sha256": self.sampler_resolution_sha256,
            "criterion": "ACCEPTED_TRANSVERSE_SAMPLER_CANNOT_SILENTLY_COARSEN_OR_LOSE_HALF_CELL_PHASE",
            "scope": "SAMPLED_DIGITAL_BREP_RESOLUTION_PROVENANCE_NOT_CONTINUOUS_CLEARANCE_OR_PHYSICAL_VALIDATION",
        }
        payload["physical_validation_eligible"] = False
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_retention_quick_release_tactile_v27() -> RetentionQuickReleaseTactileV27:
    prior = v26.build_retention_quick_release_tactile_v26()
    return RetentionQuickReleaseTactileV27(prior, _resolution_binding()).validate()
