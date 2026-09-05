from __future__ import annotations

"""Release-facing semantics for the Cell 3 retention load-path package.

Prompt 11 V1 owns the actual carrier, clevis, pin, clip and handoff-lug B-reps. This
module does not recreate or move that geometry. It binds the exact V1 source/package
and exposes a stricter release contract that distinguishes three cases explicitly:
retained positive attachment, integral material continuity and an attachment feature
whose mating counterpart is still unrealized.

It also prevents the pin-removal service bound from being misread as proof of a complete
carrier-removal trajectory. Physical load, fatigue, fit, wet use and release performance
remain validation gates.
"""

from dataclasses import dataclass
from hashlib import sha1, sha256
import json
from pathlib import Path

from .occipital_stabilizer import (
    CENTRAL_REAR_PACKAGE_KEEP_OUT_CENTER_MM,
    CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM,
    SOURCE_AUTHORITY_BLOB_SHA,
)
from .retention_load_path import (
    ATTACHMENT_FEATURE_OPEN,
    ATTACHMENT_INTEGRAL,
    ATTACHMENT_PINNED,
    CAPTURE_PIN_SERVICE_WITHDRAWAL_MM,
    RetentionLoadPathPackage,
    build_retention_load_path,
    export_retention_load_path,
)

SCHEMA = "MASCK_ONE_CELL3_RETENTION_LOAD_PATH_RELEASE_V2"
SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA = "6c851aafe1a7f5e2a33fc8214c0cadb79d12c6ff"
SOURCE_MODEL_GIT_BLOB_SHA = "9e7fa6c71ac28cc45ebb502444bf6c0ea49f7894"
DIGITAL_ONLY = "DIGITAL_LOAD_PATH_RELEASE_SEMANTICS_NOT_STRUCTURAL_OR_SERVICE_VALIDATION"


class RetentionLoadPathReleaseError(ValueError):
    pass


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return sha1(header + raw).hexdigest()


def _assert_source_blobs() -> None:
    module_dir = Path(__file__).resolve().parent
    expected = {
        module_dir / "retention_load_path.py": SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA,
        module_dir / "model.py": SOURCE_MODEL_GIT_BLOB_SHA,
        module_dir.parents[1] / "config" / "masck_one_authority.yaml": SOURCE_AUTHORITY_BLOB_SHA,
    }
    for path, expected_sha in expected.items():
        observed = _git_blob_sha(path)
        if observed != expected_sha:
            raise RetentionLoadPathReleaseError(
                f"{path.name} changed; retention load-path release requires explicit rebind"
            )


def _edge_manifest(edge) -> dict[str, object]:
    source = edge.manifest()
    attachment_class = str(source["attachment_class"])
    closed = bool(source["load_transfer_digitally_closed"])

    if attachment_class == ATTACHMENT_FEATURE_OPEN:
        if closed:
            raise RetentionLoadPathReleaseError(
                "open counterpart edge cannot be digitally load-transfer closed"
            )
        positive_attachment = False
        positive_feature = True
        counterpart_realized: bool | None = False
        integral_continuity = False
    elif attachment_class == ATTACHMENT_PINNED:
        if not closed:
            raise RetentionLoadPathReleaseError(
                "realized pinned load edge unexpectedly remains open"
            )
        positive_attachment = True
        positive_feature = True
        counterpart_realized = True
        integral_continuity = False
    elif attachment_class == ATTACHMENT_INTEGRAL:
        if not closed:
            raise RetentionLoadPathReleaseError(
                "integral material load edge unexpectedly remains open"
            )
        positive_attachment = False
        positive_feature = False
        counterpart_realized = None
        integral_continuity = True
    else:
        positive_attachment = False
        positive_feature = False
        counterpart_realized = None
        integral_continuity = False

    return {
        **source,
        "positive_attachment": positive_attachment,
        "positive_attachment_feature_realized": positive_feature,
        "mating_counterpart_realized": counterpart_realized,
        "integral_material_continuity": integral_continuity,
    }


def _carrier_rear_package_x_separation(source: RetentionLoadPathPackage) -> dict[str, float]:
    center_x = float(CENTRAL_REAR_PACKAGE_KEEP_OUT_CENTER_MM[0])
    half_x = float(CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM[0]) / 2.0
    keepout_xmin = center_x - half_x
    keepout_xmax = center_x + half_x

    left_xmax = float(source.left.carrier.solid.val().BoundingBox().xmax)
    right_xmin = float(source.right.carrier.solid.val().BoundingBox().xmin)
    left_gap = keepout_xmin - left_xmax
    right_gap = right_xmin - keepout_xmax
    if left_gap <= 0.0 or right_gap <= 0.0:
        raise RetentionLoadPathReleaseError(
            "retention carrier encroaches Prompt 08 central rear package keepout in X"
        )
    return {
        "wearer_left_mm": left_gap,
        "wearer_right_mm": right_gap,
    }


@dataclass(frozen=True, slots=True)
class RetentionLoadPathRelease:
    source: RetentionLoadPathPackage

    @property
    def release_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(include_sha=False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        source_manifest = self.source.manifest()
        edges = tuple(_edge_manifest(edge) for edge in self.source.edges)
        open_edges = tuple(
            str(edge["edge_id"])
            for edge in edges
            if not bool(edge["load_transfer_digitally_closed"])
        )
        closed_edges = tuple(
            str(edge["edge_id"])
            for edge in edges
            if bool(edge["load_transfer_digitally_closed"])
        )
        positive_attachment_edges = tuple(
            str(edge["edge_id"]) for edge in edges if bool(edge["positive_attachment"])
        )
        integral_edges = tuple(
            str(edge["edge_id"])
            for edge in edges
            if bool(edge["integral_material_continuity"])
        )
        rear_package_gap = _carrier_rear_package_x_separation(self.source)

        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_retention_load_path_git_blob_sha": SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA,
            "source_model_git_blob_sha": SOURCE_MODEL_GIT_BLOB_SHA,
            "source_authority_git_blob_sha": SOURCE_AUTHORITY_BLOB_SHA,
            "source_retention_load_path_package_sha256": self.source.package_sha256,
            "source_current_main_sha": source_manifest["source_current_main_sha"],
            "source_prompt10_head_sha": source_manifest["source_prompt10_head_sha"],
            "source_authority_blob_sha": source_manifest["source_authority_blob_sha"],
            "source_authority_revision": source_manifest["source_authority_revision"],
            "coordinate_frame_id": source_manifest["coordinate_frame_id"],
            "source_frame_retention_reservation_id": source_manifest[
                "source_frame_retention_reservation_id"
            ],
            "source_geometry_binding": {
                "package_sha256": self.source.package_sha256,
                "release_facing_semantics_owned_by_this_v2_contract": True,
                "v1_geometry_bytes_modified_by_v2": False,
            },
            "load_path_graph": {
                "nodes": [node.manifest() for node in self.source.nodes],
                "edges": list(edges),
                "digitally_closed_edge_ids": list(closed_edges),
                "open_or_nonload_edge_ids": list(open_edges),
                "positive_attachment_edge_ids": list(positive_attachment_edges),
                "integral_material_continuity_edge_ids": list(integral_edges),
                "occipital_to_local_carrier_positive_path_closed": True,
                "crown_lug_integral_to_local_carrier": True,
                "crown_positive_attachment_feature_realized": True,
                "crown_to_head_positive_attachment_realized": False,
                "crown_to_head_path_closed": False,
                "facial_handoff_lug_integral_to_local_carrier": True,
                "facial_positive_attachment_feature_realized": True,
                "facial_reaction_to_front_perimeter_positive_attachment_realized": False,
                "facial_reaction_to_front_perimeter_path_closed": False,
                "whole_retention_load_path_closed": False,
            },
            "rear_packaging_discipline": {
                "source_keepout_center_xyz_mm": list(CENTRAL_REAR_PACKAGE_KEEP_OUT_CENTER_MM),
                "source_keepout_xyz_mm": list(CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM),
                "carrier_x_separation_mm": rear_package_gap,
                "strict_x_separating_plane_proof": True,
                "clearance_is_load_transfer": False,
            },
            "service_maturity": {
                "capture_pin_withdrawal_travel_mm": CAPTURE_PIN_SERVICE_WITHDRAWAL_MM,
                "capture_pin_motion_proof": (
                    "CONSERVATIVE_TWO_STATE_AXIS_ALIGNED_BOUND_OVER_COMPLETE_PURE_Y_TRANSLATION"
                ),
                "capture_pin_motion_is_exact_swept_brep": False,
                "carrier_separation_trajectory_realized": False,
                "carrier_separation_clearance_validated": False,
                "wearer_service_allowed": False,
                "powered_service_allowed": False,
                "reset_requires_both_capture_pins_and_both_clips_reseated": True,
            },
            "service_sequence_release_semantics": [
                {
                    "step": 1,
                    "action": "GAIN_CARRIER_SERVICE_ACCESS_IF_A_COVER_IS_LATER_REALIZED",
                    "cover_geometry_currently_realized": False,
                },
                {
                    "step": 2,
                    "action": "REMOVE_BOTH_CAPTURE_C_CLIPS_MASK_REMOVED_UNPOWERED",
                },
                {
                    "step": 3,
                    "action": "WITHDRAW_BOTH_CAPTURE_PINS_POSITIVE_Y_WITHIN_CONTROLLED_BOUND",
                    "travel_mm": CAPTURE_PIN_SERVICE_WITHDRAWAL_MM,
                },
                {
                    "step": 4,
                    "action": "CARRIER_SEPARATION_TRAJECTORY_UNRESOLVED",
                    "service_clearance_validated": False,
                },
                {
                    "step": 5,
                    "action": "REASSEMBLY_REQUIRES_BOTH_PINS_AND_BOTH_CLIPS_RESEATED",
                },
            ],
            "clearance_checks": [check.manifest() for check in self.source.clearance_checks],
            "four_zone_actuation_preserved": source_manifest["four_zone_actuation_preserved"],
            "assembly_in_development_compound": False,
            "assembly_exclusion_reason": source_manifest["assembly_exclusion_reason"],
            "unresolved_digital_requirements": sorted(
                set(source_manifest["unresolved_digital_requirements"])
                | {
                    "CARRIER_NONTELEPORTING_SEPARATION_AND_REASSEMBLY_TRAJECTORY",
                }
            ),
            "physical_validation_eligible": False,
            "unresolved_physical_gates": source_manifest["unresolved_physical_gates"],
            "evidence_status": DIGITAL_ONLY,
        }
        if include_sha:
            payload["release_sha256"] = self.release_sha256
        return payload


def build_retention_load_path_release(
    source: RetentionLoadPathPackage | None = None,
) -> RetentionLoadPathRelease:
    _assert_source_blobs()
    source = source or build_retention_load_path()
    release = RetentionLoadPathRelease(source)

    graph = release.manifest(include_sha=False)["load_path_graph"]
    edges = graph["edges"]
    for edge in edges:
        attachment_class = edge["attachment_class"]
        if attachment_class == ATTACHMENT_FEATURE_OPEN:
            if edge["positive_attachment"] is not False:
                raise RetentionLoadPathReleaseError(
                    "unrealized counterpart cannot be labelled as a positive attachment"
                )
            if edge["positive_attachment_feature_realized"] is not True:
                raise RetentionLoadPathReleaseError(
                    "open handoff must retain its realized attachment-feature identity"
                )
        elif attachment_class == ATTACHMENT_PINNED:
            if edge["positive_attachment"] is not True:
                raise RetentionLoadPathReleaseError(
                    "realized retained-pin edge must remain a positive attachment"
                )
        elif attachment_class == ATTACHMENT_INTEGRAL:
            if edge["positive_attachment"] is not False or edge["integral_material_continuity"] is not True:
                raise RetentionLoadPathReleaseError(
                    "integral material edge must not masquerade as a discrete attachment"
                )
    if graph["whole_retention_load_path_closed"] is not False:
        raise RetentionLoadPathReleaseError("whole retention path cannot close before counterparts exist")
    return release


def export_retention_load_path_release(
    output_dir: str | Path,
    release: RetentionLoadPathRelease,
) -> tuple[Path, ...]:
    """Export unchanged V1 geometry and replace only its release-facing manifest semantics."""
    outputs = export_retention_load_path(output_dir, release.source)
    root = Path(output_dir)
    manifest_path = root / "retention_load_path_manifest.json"
    manifest_path.write_text(
        json.dumps(release.manifest(), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if not manifest_path.is_file() or manifest_path.stat().st_size <= 0:
        raise RetentionLoadPathReleaseError("failed to write retention load-path release manifest")
    return outputs
