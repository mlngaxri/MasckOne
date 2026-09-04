from __future__ import annotations

"""Manual B integrated product candidate.

The default released model remains untouched while this candidate proves that the
refined exterior can wrap the current authoritative physical package without deleting
or replacing Manual A owned mechanism components. Once exact-head CI and integration
review are green, the final integration owner can promote the shell deliberately.
"""

from dataclasses import replace

from .authority import Authority, load_authority
from .exterior_surface import build_refined_exterior_shell, exterior_surface_manifest
from .model import Component, MasckOneModel, build_model


MVP_EXTERIOR_STATUS = "CAD_MVP_EXTERIOR_CANDIDATE"


def build_mvp_product_candidate(authority: Authority | None = None) -> MasckOneModel:
    """Build current main physical truth with only the exterior shell replaced."""
    baseline = build_model(authority)
    refined_shell = Component(
        name="rigid_shell",
        solid=build_refined_exterior_shell(baseline.authority, baseline.facial_reference),
        status=MVP_EXTERIOR_STATUS,
        notes=(
            "Five-station smooth non-ruled Manual B exterior. Protected apertures and "
            "nominal wall remain authority-derived. Fit, comfort, seal, cleanability, "
            "Class-A, tooling and CMF durability remain unvalidated."
        ),
    )
    return replace(baseline, shell=refined_shell)


def integrated_exterior_manifest(authority: Authority | None = None) -> dict[str, object]:
    authority = authority or load_authority()
    manifest = dict(exterior_surface_manifest(authority))
    manifest["integration_status"] = MVP_EXTERIOR_STATUS
    manifest["integration_policy"] = (
        "CURRENT_MAIN_COMPONENT_SET_PRESERVED_EXCEPT_RIGID_SHELL"
    )
    manifest["manual_a_geometry_modified"] = False
    return manifest
