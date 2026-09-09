from __future__ import annotations

from copy import deepcopy
import re


_SHA40 = re.compile(r"^[0-9a-f]{40}$")

_CONTRACT = {
    "schema": "MASCK_ONE_AUTONOMOUS_SPRINT_INTEGRATION_CONTRACT_V1",
    "snapshot_date": "2026-09-09",
    "snapshot_role": "NAVIGATION_AND_EDIT_OWNERSHIP_ONLY",
    "live_github_supersedes_snapshot": True,
    "released_main_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
    "integration_lane": {
        "branch": "sol-high/integration-freeze-20260909",
        "owns": [
            ".github/workflows/ci.yml",
            "src/masck_one/export.py",
            "src/masck_one/integration_contract.py",
            "src/masck_one/release_package.py",
            "src/masck_one/step_integrity.py",
        ],
        "shared_release_seams": [
            "src/masck_one/cli.py",
            "src/masck_one/component_registry.py",
        ],
        "rule": (
            "Integrate source graph, release provenance, package/export and whole-product "
            "coexistence only. Do not redesign subsystem implementation for convenience."
        ),
    },
    "owner_lanes": {
        "structural_frame": {
            "pr": 117,
            "branch": "cell6/structural-frame-reaction-loop-v1",
            "head_sha": "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            "base_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "implementation_paths": ["src/masck_one/structural_frame_*.py"],
        },
        "treatment_mechanics": {
            "pr": 135,
            "branch": "codex/treatment-live117-reconcile-20260909",
            "head_sha": "43c3866eea56801696068ad4e417d5b21498682d",
            "base_sha": "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            "implementation_paths": [
                "src/masck_one/treatment_*.py",
                "studies/treatment_*.py",
                "studies/treatment_*.cjs",
            ],
            "status_note": "STACKED_ON_STRUCTURAL_OWNER_WITH_TREATMENT_OWNED_RED_GEOMETRY_GATES",
        },
        "primary_hmi": {
            "pr": None,
            "branch": "codex/buttery-primary-hmi-20260909",
            "head_sha": "5c2b5f030f8d205e108a828fed53d43293f518f4",
            "base_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "implementation_paths": [
                "src/masck_one/primary_control_haptic*.py",
                "studies/primary_control_haptic_profile.py",
            ],
        },
        "exterior": {
            "pr": 70,
            "branch": "cell2/exterior-green-baseline-20260905",
            "head_sha": "152312fe6eced419eef4e1e58c33df09fd0710ea",
            "base_sha": "ff76a17fa25276a401fbe57ad02564b771fa1865",
            "implementation_paths": [
                "src/masck_one/exterior_*.py",
                "src/masck_one/rear_service_skin.py",
                "src/masck_one/integrated_product.py",
            ],
            "status_note": "DIVERGED_FROM_CURRENT_MAIN_RECONCILIATION_REQUIRED",
        },
        "wet_dry_source_graph": {
            "pr": 104,
            "branch": "cell4/wet-electrical-source-graph-20260906",
            "head_sha": "484f25e0f04bba9aa27a598155dcf6d701b2a2ef",
            "base_sha": "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc",
            "implementation_paths": ["src/masck_one/wet_electrical_*.py"],
            "status_note": "DIVERGED_FROM_CURRENT_MAIN_RECONCILIATION_REQUIRED",
        },
        "warm_cool_package": {
            "pr": 138,
            "branch": "scheduled/warm-cool-package-20260909",
            "head_sha": "61b4da28f8fbd45fc1a9885db4366f8506d2043e",
            "base_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "implementation_paths": ["src/masck_one/warm_cool_package.py"],
            "status_note": "HOLD_PENDING_EXACT_RELEASE_PROVENANCE_GATE",
        },
        "waste_cartridge": {
            "pr": 140,
            "branch": "sol-high/cartridge-service-20260909",
            "head_sha": "7bf392eb2c5fb7e6b2c3a23c86bbbdfb1cc7f94f",
            "base_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "supersedes_pr": 115,
            "implementation_paths": [
                "src/masck_one/realized_waste_cartridge.py",
                "src/masck_one/cartridge_service_corridor.py",
                "src/masck_one/cartridge_fusion_handoff.py",
                "scripts/export_cartridge_fusion_handoff.py",
            ],
            "status_note": (
                "CURRENT_MAIN_BOUND_CONSOLIDATED_OWNER_WITH_DIRECT_FUSION_HANDOFF; "
                "INSTALLED_EXTRACTION_REMAINS_BLOCKED_PENDING_RELEASED_FRAME_BREP_AND_INTERFACES"
            ),
        },
        "retention_quick_release": {
            "pr": 141,
            "branch": "sol-high/retention-quick-release-20260909",
            "head_sha": "331c2ad246cffe3828feb9f4f1f9c067d4d99d24",
            "base_sha": "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be",
            "stacked_on_pr": 117,
            "donor_pr": 92,
            "implementation_paths": [
                "src/masck_one/mechanical_interface_graph.py",
            ],
            "shared_owner_binding_paths": [
                "src/masck_one/structural_frame_retention_roots.py",
            ],
            "status_note": (
                "STACKED_CONSOLIDATION_OVER_STRUCTURAL_OWNER; RETENTION GRAPH OWNS LOAD_PATH "
                "SELECTION_WHILE STRUCTURAL FRAME RETAINS ROOT_BREP OWNERSHIP"
            ),
        },
        "brand_identity": {
            "released_pr": 134,
            "released_head_sha": "c4cb42795a874ad0165ac8028c4c7133e5e53f7f",
            "released_merge_sha": "ff76a17fa25276a401fbe57ad02564b771fa1865",
            "implementation_paths": [
                "config/masck_brand_authority.yaml",
                "schemas/masck_brand_authority.schema.json",
                "brand/assets/",
                "src/masck_one/brand_identity.py",
            ],
        },
        "cad_export_infrastructure": {
            "released_pr": 130,
            "released_head_sha": "2b64b004bbc212317dbeef46525dd77dc79ba4a7",
            "released_merge_sha": "42fa11818184cde998c6df25d7c46d4fb0e4c3eb",
            "implementation_paths": [
                "src/masck_one/export.py",
                "src/masck_one/release_package.py",
                "src/masck_one/step_integrity.py",
                "src/masck_one/component_registry.py",
                ".github/workflows/ci.yml",
            ],
        },
    },
    "evidence_firewall": (
        "This receipt records digital source and edit ownership only. It does not establish "
        "physical feel, comfort, safety, wear, fatigue, acoustics, ingress, thermal/electrical "
        "safety, supplier capability, manufacturing capability or production readiness."
    ),
}


def integration_contract_manifest() -> dict[str, object]:
    manifest = deepcopy(_CONTRACT)
    for key, lane in manifest["owner_lanes"].items():
        if not isinstance(lane, dict):
            raise RuntimeError(f"integration owner lane {key} is malformed")
        for field, value in lane.items():
            if field.endswith("_sha") and value is not None:
                if not isinstance(value, str) or _SHA40.fullmatch(value) is None:
                    raise RuntimeError(f"integration owner lane {key} has malformed {field}")
        paths = lane.get("implementation_paths")
        if not isinstance(paths, list) or not paths or any(
            not isinstance(path, str) or not path for path in paths
        ):
            raise RuntimeError(f"integration owner lane {key} has malformed implementation paths")
    return manifest
