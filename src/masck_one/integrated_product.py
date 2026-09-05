from __future__ import annotations

"""Cell 2 exterior integration against the current accepted product model.

Only the rigid exterior shell is replaced. All other current-main component geometry,
protected volumes and digital topology remain owned by their existing lanes.
"""

from dataclasses import replace

from .authority import Authority, load_authority
from .exterior_inferior_turnover import (
    build_inferior_turnover_exterior_shell,
    inferior_turnover_manifest,
)
from .exterior_surface import exterior_surface_manifest
from .model import Component, MasckOneModel, build_model


MVP_EXTERIOR_STATUS = "CELL2_MVP_EXTERIOR_CANDIDATE"


def build_mvp_product_candidate(authority: Authority | None = None) -> MasckOneModel:
    """Build accepted product truth with only the Cell 2 rigid shell substituted."""
    baseline = build_model(authority)
    refined_shell = Component(
        name="rigid_shell",
        solid=build_inferior_turnover_exterior_shell(
            baseline.authority,
            baseline.facial_reference,
        ),
        status=MVP_EXTERIOR_STATUS,
        notes=(
            "Cell 2 five-station smooth exterior with tightened cheek/temple mass, "
            "localized rear B-side wall reserve and a broad anterior-only inferior "
            "turnover. Protected apertures and wall requirements remain authority-derived. "
            "Soft-interface geometry, fit, comfort, seal, cleanability, tooling and CMF "
            "durability remain unresolved or unvalidated."
        ),
    )
    return replace(baseline, shell=refined_shell)


def integrated_exterior_manifest(authority: Authority | None = None) -> dict[str, object]:
    authority = authority or load_authority()
    manifest = dict(exterior_surface_manifest(authority))
    manifest["final_shell_construction"] = inferior_turnover_manifest(authority)
    manifest["integration_status"] = MVP_EXTERIOR_STATUS
    manifest["integration_policy"] = (
        "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL"
    )
    manifest["foreign_lane_geometry_modified"] = False
    return manifest
