from __future__ import annotations

"""Cell 2 exterior integration against the current accepted product model.

The current-main component set is preserved. Cell 2 substitutes only the rigid facial
shell in the product model and separately owns one visible rear-service skin candidate.
The rear skin is kept outside the released component model until the owning dry-side
package and attachment geometry are reconciled to its tighter visual envelope.
"""

from dataclasses import dataclass, replace

import cadquery as cq

from .authority import Authority, load_authority
from .exterior_eye_roll import (
    build_eye_rolled_exterior_shell,
    eye_inner_roll_manifest,
)
from .exterior_inferior_turnover import inferior_turnover_manifest
from .exterior_rigid_clearance import rigid_clearance_manifest
from .exterior_surface import exterior_surface_manifest
from .model import Component, MasckOneModel, build_model
from .protected_volumes import ProtectedVolumeSet
from .rear_service_skin import (
    RearServiceSkin,
    build_rear_service_skin,
    rear_service_skin_manifest,
)


MVP_EXTERIOR_STATUS = "CELL2_MVP_EXTERIOR_CANDIDATE"


@dataclass(frozen=True, slots=True)
class Cell2ExteriorAssembly:
    """Cell 2-owned visible geometry without claiming foreign-lane package closure."""

    model: MasckOneModel
    rear_service_skin: RearServiceSkin

    @property
    def visible_compound(self) -> cq.Compound:
        compound = cq.Compound.makeCompound(
            [
                self.model.shell.solid.val(),
                self.rear_service_skin.cover.val(),
            ]
        )
        if not compound.isValid() or len(compound.Solids()) != 2:
            raise ValueError("Cell 2 visible assembly must contain shell and rear skin")
        return compound


def build_mvp_product_candidate(authority: Authority | None = None) -> MasckOneModel:
    """Build accepted product truth with only the Cell 2 rigid shell substituted."""
    baseline = build_model(authority)
    refined_shell = Component(
        name="rigid_shell",
        solid=build_eye_rolled_exterior_shell(
            baseline.authority,
            baseline.facial_reference,
            baseline.protected_volumes,
        ),
        status=MVP_EXTERIOR_STATUS,
        notes=(
            "Cell 2 five-station smooth exterior with tightened cheek/temple mass, "
            "localized rear B-side wall reserve, broad anterior-only inferior turnover, "
            "progressive lateral-crown feathering, released planar protected-face hard "
            "envelopes removed from rigid material and the authority 3.0 mm rigid eye "
            "edge roll applied at the resulting hard opening. Authority visual apertures "
            "remain controlled references for a future non-rigid visible interface. "
            "Soft-interface geometry, fit, comfort, seal, cleanability, tooling and CMF "
            "durability remain unresolved or unvalidated."
        ),
    )
    return replace(baseline, shell=refined_shell)


def build_cell2_exterior_assembly(authority: Authority | None = None) -> Cell2ExteriorAssembly:
    """Build the current Cell 2 visible shell plus bounded rear-service skin."""
    model = build_mvp_product_candidate(authority)
    rear_service_skin = build_rear_service_skin(model.authority)
    return Cell2ExteriorAssembly(model=model, rear_service_skin=rear_service_skin)


def integrated_exterior_manifest(
    authority: Authority | None = None,
    *,
    protected_volumes: ProtectedVolumeSet | None = None,
) -> dict[str, object]:
    authority = authority or load_authority()
    protected = protected_volumes
    if protected is None:
        protected = build_model(authority).protected_volumes
    manifest = dict(exterior_surface_manifest(authority))
    manifest["final_shell_construction"] = inferior_turnover_manifest(authority)
    manifest["rigid_protected_face_clearance"] = rigid_clearance_manifest(
        authority,
        protected,
    )
    manifest["eye_inner_edge_roll"] = eye_inner_roll_manifest(authority)
    manifest["rear_service_skin"] = rear_service_skin_manifest(authority)
    manifest["integration_status"] = MVP_EXTERIOR_STATUS
    manifest["integration_policy"] = (
        "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL;"
        "CELL2_REAR_SERVICE_SKIN_REMAINS_SEPARATE_PENDING_DRY_SIDE_PACKAGE_REFLOW"
    )
    manifest["foreign_lane_geometry_modified"] = False
    return manifest
