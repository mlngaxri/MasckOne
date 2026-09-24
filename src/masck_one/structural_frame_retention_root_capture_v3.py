from __future__ import annotations

"""Installation-demand audit for the controlled split-retainer throat.

V2 prevents nominal radial escape by making the free throat narrower than the pin
shaft. That necessarily means radial installation over the shaft requires elastic
opening. V3 makes that deformation demand explicit rather than silently treating
the nominal CAD as directly assemblable. It does not assume a retainer material or
claim that the required deflection is physically acceptable.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from .structural_frame_retention_roots import CLEVIS_PIN_RADIUS_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V3"
_MIN_POSITIVE_DEMAND_MM = 0.02


class StructuralFrameRetentionRootCaptureV3Error(ValueError):
    pass


def _installation_demand() -> tuple[float, float, float, float]:
    shaft_diameter = 2.0 * CLEVIS_PIN_RADIUS_MM
    free_throat = capture_v2.CLIP_THROAT_WIDTH_MM
    total_opening = shaft_diameter - free_throat
    per_arm = total_opening / 2.0
    opening_ratio = total_opening / free_throat
    values = (shaft_diameter, total_opening, per_arm, opening_ratio)
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV3Error("retainer installation demand must be finite and positive")
    if total_opening <= _MIN_POSITIVE_DEMAND_MM:
        raise StructuralFrameRetentionRootCaptureV3Error("retainer installation demand is not meaningfully positive")
    return shaft_diameter, total_opening, per_arm, opening_ratio


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV3:
    source_capture_v2_sha256: str
    pin_shaft_diameter_mm: float
    free_throat_width_mm: float
    required_total_throat_opening_mm: float
    required_per_arm_displacement_mm: float
    required_opening_ratio: float
    evidence_sha256: str
    elastic_installation_required: bool = True
    material_deflection_validated: bool = False
    insertion_force_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV3":
        v2 = capture_v2.build_structural_frame_retention_root_capture_v2()
        shaft, opening, per_arm, ratio = _installation_demand()
        if self.source_capture_v2_sha256 != v2.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV3Error("source capture V2 evidence is stale")
        expected = (round(shaft, 12), capture_v2.CLIP_THROAT_WIDTH_MM, round(opening, 12), round(per_arm, 12), round(ratio, 12))
        actual = (self.pin_shaft_diameter_mm, self.free_throat_width_mm, self.required_total_throat_opening_mm, self.required_per_arm_displacement_mm, self.required_opening_ratio)
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV3Error("retainer elastic-installation demand evidence is stale")
        if self.elastic_installation_required is not True:
            raise StructuralFrameRetentionRootCaptureV3Error("controlled throat requires elastic opening for radial installation")
        payload = {
            "source_capture_v2_sha256": self.source_capture_v2_sha256,
            "pin_shaft_diameter_mm": self.pin_shaft_diameter_mm,
            "free_throat_width_mm": self.free_throat_width_mm,
            "required_total_throat_opening_mm": self.required_total_throat_opening_mm,
            "required_per_arm_displacement_mm": self.required_per_arm_displacement_mm,
            "required_opening_ratio": self.required_opening_ratio,
            "elastic_installation_required": self.elastic_installation_required,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV3Error("capture V3 evidence digest is stale")
        if self.material_deflection_validated is not False or self.insertion_force_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV3Error("geometric opening demand is not material, force, or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_capture_v2_sha256": self.source_capture_v2_sha256,
            "pin_shaft_diameter_mm": self.pin_shaft_diameter_mm,
            "free_throat_width_mm": self.free_throat_width_mm,
            "required_total_throat_opening_mm": self.required_total_throat_opening_mm,
            "required_per_arm_displacement_mm": self.required_per_arm_displacement_mm,
            "required_opening_ratio": self.required_opening_ratio,
            "installation_status": "ELASTIC_OPENING_REQUIRED_MATERIAL_AND_FORCE_UNVALIDATED",
            "elastic_installation_required": self.elastic_installation_required,
            "material_deflection_validated": self.material_deflection_validated,
            "insertion_force_validated": self.insertion_force_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v3() -> StructuralFrameRetentionRootCaptureV3:
    v2 = capture_v2.build_structural_frame_retention_root_capture_v2()
    shaft, opening, per_arm, ratio = _installation_demand()
    payload = {
        "source_capture_v2_sha256": v2.evidence_sha256,
        "pin_shaft_diameter_mm": round(shaft, 12),
        "free_throat_width_mm": capture_v2.CLIP_THROAT_WIDTH_MM,
        "required_total_throat_opening_mm": round(opening, 12),
        "required_per_arm_displacement_mm": round(per_arm, 12),
        "required_opening_ratio": round(ratio, 12),
        "elastic_installation_required": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV3(
        v2.evidence_sha256,
        round(shaft, 12),
        capture_v2.CLIP_THROAT_WIDTH_MM,
        round(opening, 12),
        round(per_arm, 12),
        round(ratio, 12),
        digest,
        True,
        False,
        False,
        False,
    ).validate()
