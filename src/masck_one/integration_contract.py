"""Edit-ownership map for concurrent autonomous sprint lanes.

This module answers exactly one question: *which lane is allowed to edit which
source paths*. It exists so parallel workers do not silently overwrite each
other's subsystem implementations.

It deliberately does NOT record live pull-request state. Pull-request numbers,
branch heads and base commits are owned by GitHub and change many times per
day; a copy compiled into this repository is stale within hours and, because it
is emitted into ``build_report.json``, a stale copy ships false provenance in
released evidence. Read live state from the GitHub API instead.

The only commit identifiers kept here are ones that are immutable by
construction: merge commits that are already in ``main``'s history. Those
cannot drift.
"""

from __future__ import annotations

from copy import deepcopy
import re

from . import _contracts


_SHA40 = re.compile(r"^[0-9a-f]{40}$")

# Paths the integration lane may edit. These are release/provenance/packaging
# seams, never subsystem implementation.
_INTEGRATION_OWNS = (
    ".github/workflows/ci.yml",
    "src/masck_one/export.py",
    "src/masck_one/integration_contract.py",
    "src/masck_one/release_package.py",
    "src/masck_one/step_integrity.py",
)

# Paths where the integration lane and a subsystem owner must coordinate.
_SHARED_RELEASE_SEAMS = (
    "src/masck_one/cli.py",
    "src/masck_one/component_registry.py",
)

_CONTRACT = {
    "schema": "MASCK_ONE_SPRINT_EDIT_OWNERSHIP_V2",
    "role": "EDIT_OWNERSHIP_AND_NAVIGATION_ONLY",
    "live_github_is_authoritative_for_pr_and_branch_state": True,
    "volatile_state_deliberately_omitted": [
        "pull_request_number",
        "branch_head_sha",
        "branch_base_sha",
        "pull_request_stacking",
    ],
    # Immutable: already merged into main's history.
    "released_main_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
    "integration_lane": {
        "owns": list(_INTEGRATION_OWNS),
        "shared_release_seams": list(_SHARED_RELEASE_SEAMS),
        "rule": (
            "Integrate source graph, release provenance, package/export and whole-product "
            "coexistence only. Do not redesign subsystem implementation for convenience."
        ),
    },
    "owner_lanes": {
        "structural_frame": {
            "branch": "cell6/structural-frame-reaction-loop-v1",
            "implementation_paths": ["src/masck_one/structural_frame_*.py"],
        },
        "treatment_mechanics": {
            "branch": "codex/treatment-live117-reconcile-20260909",
            "implementation_paths": [
                "src/masck_one/treatment_*.py",
                "studies/treatment_*.py",
                "studies/treatment_*.cjs",
            ],
            "depends_on_lane": "structural_frame",
            "status_note": "TREATMENT_OWNED_GEOMETRY_GATES_STACK_ON_STRUCTURAL_OWNER",
        },
        "primary_hmi": {
            "branch": "codex/buttery-primary-hmi-20260909",
            "implementation_paths": [
                "src/masck_one/primary_control_haptic*.py",
                "studies/primary_control_haptic_profile.py",
            ],
        },
        "exterior": {
            "branch": "cell2/exterior-green-baseline-20260905",
            "implementation_paths": [
                "src/masck_one/exterior_*.py",
                "src/masck_one/rear_service_skin.py",
                "src/masck_one/integrated_product.py",
            ],
            "status_note": "DIVERGED_FROM_CURRENT_MAIN_RECONCILIATION_REQUIRED",
        },
        "wet_dry_source_graph": {
            "branch": "cell4/wet-electrical-source-graph-20260906",
            "implementation_paths": ["src/masck_one/wet_electrical_*.py"],
            "status_note": "DIVERGED_FROM_CURRENT_MAIN_RECONCILIATION_REQUIRED",
        },
        "warm_cool_package": {
            "branch": "scheduled/warm-cool-package-20260909",
            "implementation_paths": ["src/masck_one/warm_cool_package.py"],
        },
        "waste_cartridge": {
            "branch": "sol-high/cartridge-service-20260909",
            "implementation_paths": [
                "src/masck_one/realized_waste_cartridge.py",
                "src/masck_one/cartridge_service_corridor.py",
                "src/masck_one/cartridge_fusion_handoff.py",
                "scripts/export_cartridge_fusion_handoff.py",
            ],
            "status_note": (
                "INSTALLED_EXTRACTION_REMAINS_BLOCKED_PENDING_RELEASED_FRAME_BREP_AND_INTERFACES"
            ),
        },
        "retention_quick_release": {
            "branch": "sol-high/retention-quick-release-20260909",
            "implementation_paths": ["src/masck_one/mechanical_interface_graph.py"],
            "shared_owner_binding_paths": [
                "src/masck_one/structural_frame_retention_roots.py"
            ],
            "depends_on_lane": "structural_frame",
            "status_note": (
                "RETENTION GRAPH OWNS LOAD_PATH SELECTION WHILE STRUCTURAL FRAME "
                "RETAINS ROOT_BREP OWNERSHIP"
            ),
        },
        "brand_identity": {
            "released_merge_sha": "ff76a17fa25276a401fbe57ad02564b771fa1865",
            "implementation_paths": [
                "config/masck_brand_authority.yaml",
                "schemas/masck_brand_authority.schema.json",
                "brand/assets/",
                "src/masck_one/brand_identity.py",
            ],
        },
        "cad_export_infrastructure": {
            "released_merge_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "implementation_paths": list(_INTEGRATION_OWNS) + [
                "src/masck_one/component_registry.py"
            ],
        },
    },
    "evidence_firewall": (
        "This receipt records digital source and edit ownership only. It does not establish "
        "physical feel, comfort, safety, wear, fatigue, acoustics, ingress, thermal/electrical "
        "safety, supplier capability, manufacturing capability or production readiness."
    ),
}

# The integration lane owns release seams; the release-infrastructure lane is the
# same set of paths under a released identity, so it is exempt from the
# disjointness rule that applies between subsystem lanes.
_RELEASE_INFRASTRUCTURE_LANES = frozenset({"cad_export_infrastructure"})


class IntegrationContractError(RuntimeError):
    """Raised when the sprint edit-ownership map is internally inconsistent."""


def _validate(manifest: dict[str, object]) -> None:
    lanes = manifest["owner_lanes"]
    if not isinstance(lanes, dict) or not lanes:
        raise IntegrationContractError("owner_lanes must be a non-empty mapping")

    seen: dict[str, str] = {}
    for key, lane in lanes.items():
        if not isinstance(lane, dict):
            raise IntegrationContractError(f"integration owner lane {key} is malformed")

        for field, value in lane.items():
            if field.endswith("_sha"):
                if not isinstance(value, str) or _SHA40.fullmatch(value) is None:
                    raise IntegrationContractError(
                        f"integration owner lane {key} has malformed {field}"
                    )

        paths = lane.get("implementation_paths")
        if not isinstance(paths, list) or not paths:
            raise IntegrationContractError(
                f"integration owner lane {key} has malformed implementation paths"
            )
        for path in paths:
            _contracts.non_empty_text(
                path, f"lane {key} implementation path", IntegrationContractError
            )

        dependency = lane.get("depends_on_lane")
        if dependency is not None and dependency not in lanes:
            raise IntegrationContractError(
                f"integration owner lane {key} depends on unknown lane {dependency!r}"
            )

        if key in _RELEASE_INFRASTRUCTURE_LANES:
            continue

        # Two subsystem lanes claiming the same implementation path is a real
        # collision: whichever lands second silently overwrites the first.
        for path in paths:
            if path in seen:
                raise IntegrationContractError(
                    f"implementation path {path!r} is claimed by both "
                    f"{seen[path]!r} and {key!r}"
                )
            seen[path] = key

    # The integration lane must never own subsystem implementation.
    integration_owned = set(manifest["integration_lane"]["owns"])
    for key, lane in lanes.items():
        if key in _RELEASE_INFRASTRUCTURE_LANES:
            continue
        collision = integration_owned.intersection(lane["implementation_paths"])
        if collision:
            raise IntegrationContractError(
                f"integration lane claims subsystem implementation owned by {key!r}: "
                f"{sorted(collision)}"
            )


def integration_contract_manifest() -> dict[str, object]:
    manifest = deepcopy(_CONTRACT)
    _validate(manifest)
    return manifest
