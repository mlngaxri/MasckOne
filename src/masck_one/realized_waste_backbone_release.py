"""Live-source release binding for the Cell 4 mixed-waste backbone realization."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .authority import Authority
from .boundary_release import build_verified_interface_boundary_topology
from .cleanser_storage import build_cleanser_storage_architecture
from .distribution_geometry import (
    DistributionGeometryArchitecture,
    build_distribution_geometry_architecture,
)
from .distribution_manifold import build_distribution_manifold_architecture
from .fresh_pump_packaging import build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .model import build_model
from .realized_waste_backbone import (
    RealizedWasteBackbone,
    RealizedWasteBackboneError,
    build_cell4_waste_backbone,
)
from .structural_frame import StructuralFrameTopology, build_structural_frame_topology
from .water_reservoir import build_water_reservoir_architecture
from .waste_acquisition import (
    WasteAcquisitionArchitecture,
    build_waste_acquisition_architecture,
)
from .waste_pump_architecture import (
    WastePumpArchitecture,
    WastePumpArchitectureError,
    build_waste_pump_architecture,
)

AUTHORED_AGAINST_MAIN_SHA = "5fce2a43a34d8be49256677a35af60c906dc1653"
RELEASE_STATE = "PROVISIONAL_DIGITAL_GEOMETRY_VALIDATION_GATED"


@dataclass(frozen=True, slots=True)
class CurrentWasteRoutingSources:
    authority: Authority
    frame: StructuralFrameTopology
    distribution: DistributionGeometryArchitecture
    acquisition: WasteAcquisitionArchitecture
    architecture: WastePumpArchitecture

    def validate(self) -> None:
        if type(self.authority) is not Authority:
            raise RealizedWasteBackboneError("current authority must use the exact Authority type")
        if type(self.frame) is not StructuralFrameTopology:
            raise RealizedWasteBackboneError("current frame must use the exact StructuralFrameTopology type")
        if type(self.distribution) is not DistributionGeometryArchitecture:
            raise RealizedWasteBackboneError(
                "current distribution must use the exact DistributionGeometryArchitecture type"
            )
        if type(self.acquisition) is not WasteAcquisitionArchitecture:
            raise RealizedWasteBackboneError(
                "current acquisition must use the exact WasteAcquisitionArchitecture type"
            )
        if type(self.architecture) is not WastePumpArchitecture:
            raise RealizedWasteBackboneError(
                "current waste routing must use the exact WastePumpArchitecture type"
            )
        try:
            self.architecture.validate_current_sources(
                authority=self.authority,
                acquisition=self.acquisition,
                distribution=self.distribution,
                frame=self.frame,
            )
        except WastePumpArchitectureError as exc:
            raise RealizedWasteBackboneError(
                "current upstream waste routing source graph is stale or corrupted"
            ) from exc


def build_current_waste_routing_sources() -> CurrentWasteRoutingSources:
    """Reconstruct the current repository-rooted waste routing source graph."""
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    fresh_pumps = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pumps,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pumps,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    architecture = build_waste_pump_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    sources = CurrentWasteRoutingSources(
        authority=model.authority,
        frame=frame,
        distribution=distribution,
        acquisition=acquisition,
        architecture=architecture,
    )
    sources.validate()
    return sources


@dataclass(frozen=True, slots=True)
class Cell4WasteBackboneRelease:
    authored_against_git_sha: str
    source_waste_pump_architecture_sha256: str
    realization: RealizedWasteBackbone
    release_state: str = RELEASE_STATE

    def validate_invariants(self) -> None:
        if (
            type(self.authored_against_git_sha) is not str
            or len(self.authored_against_git_sha) != 40
            or any(c not in "0123456789abcdef" for c in self.authored_against_git_sha)
        ):
            raise RealizedWasteBackboneError(
                "authored-against Git provenance must be exact lowercase 40-hex"
            )
        if (
            type(self.source_waste_pump_architecture_sha256) is not str
            or len(self.source_waste_pump_architecture_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.source_waste_pump_architecture_sha256)
        ):
            raise RealizedWasteBackboneError(
                "source waste-pump architecture digest must be exact lowercase SHA-256"
            )
        if type(self.realization) is not RealizedWasteBackbone:
            raise RealizedWasteBackboneError(
                "release realization must use the exact RealizedWasteBackbone type"
            )
        self.realization.validate()
        if self.realization.source_git_sha != self.authored_against_git_sha:
            raise RealizedWasteBackboneError(
                "realization Git provenance does not match release provenance"
            )
        if (
            self.realization.source_waste_pump_architecture_sha256
            != self.source_waste_pump_architecture_sha256
        ):
            raise RealizedWasteBackboneError(
                "realization routing digest does not match release routing digest"
            )
        if self.release_state != RELEASE_STATE:
            raise RealizedWasteBackboneError(
                "Cell 4 waste release cannot promote physical validation"
            )

    def validate_current_sources(self, sources: CurrentWasteRoutingSources) -> None:
        self.validate_invariants()
        if type(sources) is not CurrentWasteRoutingSources:
            raise RealizedWasteBackboneError(
                "current routing sources must use the exact CurrentWasteRoutingSources type"
            )
        sources.validate()
        architecture = sources.architecture
        current_digest = architecture.architecture_sha256
        if self.source_waste_pump_architecture_sha256 != current_digest:
            raise RealizedWasteBackboneError(
                "Cell 4 waste realization is stale for the current waste-pump architecture"
            )
        if self.realization.authority_revision != architecture.source_authority_revision:
            raise RealizedWasteBackboneError(
                "Cell 4 waste realization is stale for the current authority revision"
            )
        realized_routes = tuple(
            (
                route.segment_id,
                route.stage,
                route.fluid_identity,
                route.source_interface_id,
                route.target_interface_id,
            )
            for route in self.realization.routes
        )
        current_routes = tuple(
            (
                route.route_id,
                route.stage,
                route.phase_semantics,
                route.source_interface_id,
                route.target_interface_id,
            )
            for route in architecture.routes
        )
        if realized_routes != current_routes:
            raise RealizedWasteBackboneError(
                "realized route bindings do not match the current upstream waste-pump architecture"
            )

    def manifest(
        self,
        *,
        sources: CurrentWasteRoutingSources | None = None,
    ) -> dict[str, object]:
        current = build_current_waste_routing_sources() if sources is None else sources
        self.validate_current_sources(current)
        return {
            "authored_against_git_sha": self.authored_against_git_sha,
            "source_waste_pump_architecture_sha256": self.source_waste_pump_architecture_sha256,
            "authority_revision": self.realization.authority_revision,
            "realization_manifest_sha256": self.realization.manifest_sha256,
            "release_state": self.release_state,
        }

    def manifest_sha256(
        self,
        *,
        sources: CurrentWasteRoutingSources | None = None,
    ) -> str:
        payload = self.manifest(sources=sources)
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def build_current_cell4_waste_backbone_release(
    *,
    sources: CurrentWasteRoutingSources | None = None,
) -> Cell4WasteBackboneRelease:
    current = build_current_waste_routing_sources() if sources is None else sources
    current.validate()
    architecture = current.architecture
    realization = build_cell4_waste_backbone(
        source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=architecture.architecture_sha256,
        authority_revision=architecture.source_authority_revision,
    )
    release = Cell4WasteBackboneRelease(
        authored_against_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=architecture.architecture_sha256,
        realization=realization,
    )
    release.validate_current_sources(current)
    return release
