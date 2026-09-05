"""Exact-main release binding for the Cell 4 mixed-waste backbone realization."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .realized_waste_backbone import (
    AUTHORITY_BLOB_SHA,
    AUTHORITY_REVISION,
    ROUTING_TOPOLOGY_BLOB_SHA,
    RealizedWasteBackbone,
    RealizedWasteBackboneError,
    build_cell4_waste_backbone,
)

SOURCE_MAIN_SHA = "5fce2a43a34d8be49256677a35af60c906dc1653"
SOURCE_ROUTING_STACK_SHA = SOURCE_MAIN_SHA
RELEASE_STATE = "PROVISIONAL_DIGITAL_GEOMETRY_VALIDATION_GATED"


@dataclass(frozen=True, slots=True)
class Cell4WasteBackboneRelease:
    source_routing_stack_sha: str
    authority_revision: str
    authority_blob_sha: str
    routing_topology_blob_sha: str
    realization: RealizedWasteBackbone
    release_state: str = RELEASE_STATE

    def validate(self) -> None:
        if self.source_routing_stack_sha != SOURCE_MAIN_SHA:
            raise RealizedWasteBackboneError("Cell 4 waste realization is stale for current main")
        if self.authority_revision != AUTHORITY_REVISION:
            raise RealizedWasteBackboneError("Cell 4 waste realization is stale for the authority revision")
        if self.authority_blob_sha != AUTHORITY_BLOB_SHA:
            raise RealizedWasteBackboneError("Cell 4 waste realization is stale for the authority blob")
        if self.routing_topology_blob_sha != ROUTING_TOPOLOGY_BLOB_SHA:
            raise RealizedWasteBackboneError("Cell 4 waste realization is stale for the routing topology blob")
        if type(self.realization) is not RealizedWasteBackbone:
            raise RealizedWasteBackboneError("release realization must use the exact RealizedWasteBackbone type")
        self.realization.validate()
        if self.realization.source_git_sha != SOURCE_MAIN_SHA:
            raise RealizedWasteBackboneError("realization source SHA does not match current main")
        if self.realization.authority_revision != self.authority_revision:
            raise RealizedWasteBackboneError("realization authority revision does not match release authority")
        if self.realization.authority_blob_sha != self.authority_blob_sha:
            raise RealizedWasteBackboneError("realization authority blob does not match release authority")
        if self.realization.routing_topology_blob_sha != self.routing_topology_blob_sha:
            raise RealizedWasteBackboneError("realization routing topology blob does not match release topology")
        if self.release_state != RELEASE_STATE:
            raise RealizedWasteBackboneError("Cell 4 waste release cannot promote physical validation")

    @property
    def manifest_sha256(self) -> str:
        self.validate()
        payload = {
            "source_main_sha": self.source_routing_stack_sha,
            "authority_revision": self.authority_revision,
            "authority_blob_sha": self.authority_blob_sha,
            "routing_topology_blob_sha": self.routing_topology_blob_sha,
            "realization_manifest_sha256": self.realization.manifest_sha256,
            "release_state": self.release_state,
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def build_current_cell4_waste_backbone_release() -> Cell4WasteBackboneRelease:
    realization = build_cell4_waste_backbone(source_git_sha=SOURCE_MAIN_SHA)
    release = Cell4WasteBackboneRelease(
        source_routing_stack_sha=SOURCE_MAIN_SHA,
        authority_revision=AUTHORITY_REVISION,
        authority_blob_sha=AUTHORITY_BLOB_SHA,
        routing_topology_blob_sha=ROUTING_TOPOLOGY_BLOB_SHA,
        realization=realization,
    )
    release.validate()
    return release
