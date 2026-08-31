"""Fail-closed binding between tolerance stacks and collision geometry.

Digital geometry only. This contract prevents a clearance stack from being
reused after either moving or protected geometry changes, or across frames.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from .mechanism_tolerance import ClearanceStack

_SHA = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[A-Z][A-Z0-9_]{0,63}")


def _sha(name: str, value: object) -> str:
    # Provenance values cross an equality/hash trust boundary. Reject subclasses
    # rather than preserving caller-controlled __eq__/__ne__/__hash__ behavior.
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError(f"{name} must be exact built-in canonical lowercase SHA-256")
    return value


def _id(name: str, value: object) -> str:
    # Same exact-type rule as SHA identities: controlled IDs must have built-in
    # immutable string equality semantics before any comparison or hashing.
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"{name} must be exact built-in canonical ASCII uppercase identity")
    return value


@dataclass(frozen=True)
class CollisionClearanceBinding:
    """Binds one scalar clearance proof to both exact geometry participants."""

    binding_id: str
    coordinate_frame_id: str
    moving_geometry_sha256: str
    protected_geometry_sha256: str
    clearance_stack: ClearanceStack

    def __post_init__(self) -> None:
        object.__setattr__(self, "binding_id", _id("binding_id", self.binding_id))
        object.__setattr__(self, "coordinate_frame_id", _id("coordinate_frame_id", self.coordinate_frame_id))
        object.__setattr__(self, "moving_geometry_sha256", _sha("moving_geometry_sha256", self.moving_geometry_sha256))
        object.__setattr__(self, "protected_geometry_sha256", _sha("protected_geometry_sha256", self.protected_geometry_sha256))
        if type(self.clearance_stack) is not ClearanceStack:
            raise TypeError("clearance_stack must be exact ClearanceStack")
        if self.clearance_stack.coordinate_frame_id != self.coordinate_frame_id:
            raise ValueError("clearance stack frame does not match collision frame")
        # The stack's source geometry is the deterministic composite identity of
        # both collision participants, not either participant in isolation.
        if self.clearance_stack.source_geometry_sha256 != self.composite_geometry_sha256:
            raise ValueError("clearance stack is not bound to exact collision geometry pair")

    @property
    def composite_geometry_sha256(self) -> str:
        payload = {
            "coordinate_frame_id": self.coordinate_frame_id,
            "moving_geometry_sha256": self.moving_geometry_sha256,
            "protected_geometry_sha256": self.protected_geometry_sha256,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()

    def assert_positive_clearance(
        self,
        *,
        current_moving_geometry_sha256: str,
        current_protected_geometry_sha256: str,
        coordinate_frame_id: str,
    ) -> float:
        moving = _sha("current_moving_geometry_sha256", current_moving_geometry_sha256)
        protected = _sha("current_protected_geometry_sha256", current_protected_geometry_sha256)
        frame = _id("coordinate_frame_id", coordinate_frame_id)
        if frame != self.coordinate_frame_id:
            raise RuntimeError("collision clearance coordinate-frame mismatch")
        if moving != self.moving_geometry_sha256:
            raise RuntimeError("stale moving mechanism geometry provenance")
        if protected != self.protected_geometry_sha256:
            raise RuntimeError("stale protected-region geometry provenance")
        return self.clearance_stack.assert_positive_clearance(
            current_geometry_sha256=self.composite_geometry_sha256,
            coordinate_frame_id=frame,
        )

    @property
    def provenance_sha256(self) -> str:
        payload = {
            "binding_id": self.binding_id,
            "coordinate_frame_id": self.coordinate_frame_id,
            "moving_geometry_sha256": self.moving_geometry_sha256,
            "protected_geometry_sha256": self.protected_geometry_sha256,
            "clearance_stack_provenance_sha256": self.clearance_stack.provenance_sha256,
            "evidence": "DIGITAL_GEOMETRY_ONLY",
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")).hexdigest()
