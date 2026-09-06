"""Transitive released-source integrity for Cell 10 cleanser reconstruction.

These blobs are not additional design authority. They are the released producer chain
whose movement can change the rebuilt cleanser storage/pump/manifold/distribution graph
or the six released cleanser outlet datums. Any movement requires an explicit Cell 10
reconstruction and rebind before prior evidence can be reused.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

RELEASED_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"

TRANSITIVE_RELEASED_PRODUCER_BLOBS: tuple[tuple[str, str, str], ...] = (
    ("AUTHORITY_SCHEMA", "schemas/masck_one_authority.schema.json", "58accbe48619058cb99ab51a0387cf01874c3717"),
    ("AUTHORITY_LOADER", "src/masck_one/authority.py", "6866e3a428dab8b32b5a1d9e58da78b8f5aa1aa2"),
    ("MODEL", "src/masck_one/model.py", "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"),
    ("ANATOMY", "src/masck_one/anatomy.py", "872d1e5be1b9ce9baa5b63cb53462eb7b36f40ab"),
    ("FACIAL_SURFACE", "src/masck_one/facial_surface.py", "764f6f65b83ac7709d959bb0f37f861c90ea2794"),
    ("COVERAGE", "src/masck_one/coverage.py", "4a8cec4d94db97e63f634a94dd8c90094f3afcb0"),
    ("INTERFACE_TOPOLOGY", "src/masck_one/interface_topology.py", "38b7c932f71a8675d45d098ac65154f98ff8bbb5"),
    ("INTERFACE_BOUNDARIES", "src/masck_one/interface_boundaries.py", "496c9b50867ca0bb319175d1d2e47caf4bc4fb64"),
    ("BOUNDARY_RELEASE", "src/masck_one/boundary_release.py", "34a49eed2c521d55e48ac187c2dd33dc9e22a3e3"),
    ("INTERFACE_ATTACHMENT", "src/masck_one/interface_attachment.py", "c161f99ddd3473f3b9dde30ec73397a72915191a"),
    ("STRUCTURAL_FRAME", "src/masck_one/structural_frame.py", "bda5ba87d232c0e6a22e200975a80414a10c9a83"),
    ("WATER_RESERVOIR", "src/masck_one/water_reservoir.py", "6c14a37d07855550f0bd502e8308ed46682bc19c"),
    ("PROTECTED_VOLUMES", "src/masck_one/protected_volumes.py", "ff2b9b288559f9b268e5d08a1d6c78335f745cf1"),
    ("SPATIAL", "src/masck_one/spatial.py", "8c1106b523fef5111009cc56236a53e3bc5ee10e"),
    ("WORN_POSE", "src/masck_one/worn_pose.py", "9d4ed65246fbc92ac577ce38bceb95cd2253607b"),
)

_GIT_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


class CleanserSourceIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TransitiveReleasedProducer:
    producer_id: str
    path: str
    blob_sha: str

    def __post_init__(self) -> None:
        if type(self.producer_id) is not str or not self.producer_id or self.producer_id != self.producer_id.strip():
            raise CleanserSourceIntegrityError("producer ID must be exact nonblank text")
        if type(self.path) is not str or not self.path or self.path != self.path.strip():
            raise CleanserSourceIntegrityError("producer path must be exact nonblank text")
        if type(self.blob_sha) is not str or _GIT_SHA_RE.fullmatch(self.blob_sha) is None:
            raise CleanserSourceIntegrityError("producer blob must be canonical lowercase 40-hex Git identity")

    def manifest(self) -> dict[str, str]:
        return {
            "producer_id": self.producer_id,
            "path": self.path,
            "blob_sha": self.blob_sha,
        }


def build_transitive_released_producers() -> tuple[TransitiveReleasedProducer, ...]:
    producers = tuple(TransitiveReleasedProducer(*item) for item in TRANSITIVE_RELEASED_PRODUCER_BLOBS)
    ids = tuple(item.producer_id for item in producers)
    paths = tuple(item.path for item in producers)
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise CleanserSourceIntegrityError("transitive released producer identities and paths must be unique")
    return producers
