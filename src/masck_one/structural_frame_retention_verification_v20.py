from __future__ import annotations

"""V20 binds retention roots to the current source reaction architecture.

A retention-root object can be supplied alongside a different MasckOneModel because
runtime type checks alone do not prove common provenance. V20 independently rebuilds
the source reaction architecture from the supplied model and requires the retention
root provenance digest to match it exactly.

Digital provenance evidence only. This does not establish manufactured fit, strength,
comfort, service force, wear, contamination tolerance, or physical safety performance.
"""

from dataclasses import dataclass
import string

from .model import MasckOneModel, build_model
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V20"
_SHA256_HEX_LENGTH = 64
_SHA256_HEX_ALPHABET = frozenset(string.hexdigits.lower())


class StructuralFrameRetentionVerificationV20Error(ValueError):
    pass


def _is_canonical_sha256(value: object) -> bool:
    """Accept only the canonical lowercase hexadecimal representation we emit.

    Length-only validation allowed arbitrary 64-character strings to enter retained
    provenance evidence. Requiring canonical hex keeps the authority boundary fail-closed
    and prevents case/encoding variants from becoming distinct architecture identities.
    """
    return (
        isinstance(value, str)
        and len(value) == _SHA256_HEX_LENGTH
        and value == value.lower()
        and all(character in _SHA256_HEX_ALPHABET for character in value)
    )


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV20:
    recorded_source_sha256: str
    expected_source_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV20":
        for label, value in (
            ("recorded", self.recorded_source_sha256),
            ("expected", self.expected_source_sha256),
        ):
            if not _is_canonical_sha256(value):
                raise StructuralFrameRetentionVerificationV20Error(
                    f"{label} source reaction architecture SHA-256 is invalid"
                )
        if self.recorded_source_sha256 != self.expected_source_sha256:
            raise StructuralFrameRetentionVerificationV20Error(
                "retention roots are not bound to the supplied model's source reaction architecture"
            )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV20Error(
                "digital provenance binding is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "recorded_source_frame_reaction_architecture_sha256": self.recorded_source_sha256,
            "expected_source_frame_reaction_architecture_sha256": self.expected_source_sha256,
            "source_binding_match": True,
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_verification_v20(
    *,
    roots: StructuralFrameRetentionRootArchitecture | None = None,
    model: MasckOneModel | None = None,
) -> StructuralFrameRetentionVerificationV20:
    model = build_model() if model is None else model
    roots = build_structural_frame_retention_roots(model=model) if roots is None else roots
    if type(model) is not MasckOneModel or type(roots) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV20Error(
            "exact model and retention-root architecture types are required"
        )

    expected = build_structural_frame_actuator_reactions(model=model).architecture_sha256
    return StructuralFrameRetentionVerificationV20(
        recorded_source_sha256=roots.source_frame_reaction_architecture_sha256,
        expected_source_sha256=expected,
        physical_validation_eligible=False,
    ).validate()
