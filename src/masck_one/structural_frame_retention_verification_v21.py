from __future__ import annotations

"""V21 binds retained root evidence to a fresh root rebuild from the supplied model.

V20 proves that the roots name the current actuator-reaction architecture, but a retained
root object can still be altered after construction while preserving that upstream source
digest. V21 independently rebuilds the complete retention-root architecture and requires
its canonical architecture digest to match the supplied root manifest exactly.

Digital provenance/regression evidence only. This does not establish manufactured fit,
strength, fatigue, service force, wear, contamination tolerance, comfort, or safety.
"""

from dataclasses import dataclass
import hmac
import string

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V21"
_SHA256_HEX_LENGTH = 64
_SHA256_HEX_ALPHABET = frozenset(string.digits + "abcdef")


class StructuralFrameRetentionVerificationV21Error(ValueError):
    pass


def _is_canonical_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_HEX_LENGTH
        and all(character in _SHA256_HEX_ALPHABET for character in value)
    )


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV21:
    recorded_root_architecture_sha256: str
    expected_root_architecture_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV21":
        for label, value in (
            ("recorded", self.recorded_root_architecture_sha256),
            ("expected", self.expected_root_architecture_sha256),
        ):
            if not _is_canonical_sha256(value):
                raise StructuralFrameRetentionVerificationV21Error(
                    f"{label} retention-root architecture SHA-256 is invalid"
                )
        if not hmac.compare_digest(
            self.recorded_root_architecture_sha256,
            self.expected_root_architecture_sha256,
        ):
            raise StructuralFrameRetentionVerificationV21Error(
                "retention-root evidence does not match a fresh rebuild from the supplied model"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV21Error(
                "digital root-rebuild provenance is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "recorded_retention_root_architecture_sha256": self.recorded_root_architecture_sha256,
            "expected_retention_root_architecture_sha256": self.expected_root_architecture_sha256,
            "fresh_root_rebuild_match": True,
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v21(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    model: MasckOneModel | None = None,
) -> StructuralFrameRetentionVerificationV21:
    model = build_model() if model is None else model
    roots = build_structural_frame_retention_roots(model=model) if roots is None else roots
    if type(model) is not MasckOneModel or type(roots) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV21Error(
            "exact model and retention-root architecture types are required"
        )

    expected = build_structural_frame_retention_roots(model=model).architecture_sha256
    return StructuralFrameRetentionVerificationV21(
        recorded_root_architecture_sha256=roots.architecture_sha256,
        expected_root_architecture_sha256=expected,
        physical_validation_eligible=False,
    ).validate()
