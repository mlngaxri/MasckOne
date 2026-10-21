from __future__ import annotations

"""Source-current standalone release bundle for Cell 6 manufactured geometry.

This module deliberately does not rebind the canonical development assembly. It
collects the frame-owned exporters that already produce positive B-rep geometry,
verifies their emitted STEP and manifest artifacts, and reports the exact
standalone geometry that still requires assembly rebind.
"""

import json
from pathlib import Path

import cadquery as cq

from .structural_frame_actuator_reactions_export import export_structural_frame_actuator_reactions
from .structural_frame_crown_support import export_structural_frame_crown_support
from .structural_frame_dry_package_supports import export_structural_frame_dry_package_supports
from .structural_frame_retention_roots import export_retention_root_counterparts
from .structural_frame_shell_joint_service import export_structural_frame_shell_joint_service


SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RELEASE_EXPORT_V1"

EXPORTED_STEP_FILES = (
    "structural_frame_with_four_actuator_reaction_counterparts.step",
    "structural_frame_with_bilateral_retention_roots.step",
    "retention_root_wearer_left_capture_pin.step",
    "retention_root_wearer_left_split_retainer.step",
    "retention_root_wearer_right_capture_pin.step",
    "retention_root_wearer_right_split_retainer.step",
    "structural_frame_crown_support.step",
    "structural_frame_crown_wearer_left_capture_pin.step",
    "structural_frame_crown_wearer_left_split_retainer.step",
    "structural_frame_crown_wearer_right_capture_pin.step",
    "structural_frame_crown_wearer_right_split_retainer.step",
    "structural_frame_with_battery_support_counterparts.step",
    "battery_left_support.step",
    "battery_right_support.step",
    "structural_frame_shell_with_joint_service_reliefs.step",
    "frame_shell_joint_superior_left_pin_withdraw_sweep.step",
    "frame_shell_joint_superior_left_clip_install_sweep.step",
    "frame_shell_joint_superior_right_pin_withdraw_sweep.step",
    "frame_shell_joint_superior_right_clip_install_sweep.step",
    "frame_shell_joint_inferior_left_pin_withdraw_sweep.step",
    "frame_shell_joint_inferior_left_clip_install_sweep.step",
    "frame_shell_joint_inferior_right_pin_withdraw_sweep.step",
    "frame_shell_joint_inferior_right_clip_install_sweep.step",
)

CONSTITUENT_MANIFEST_FILES = (
    "structural_frame_actuator_reactions_manifest.json",
    "structural_frame_retention_roots_manifest.json",
    "structural_frame_crown_support_manifest.json",
    "structural_frame_dry_package_supports_manifest.json",
    "structural_frame_shell_joint_service_manifest.json",
)

RELEASE_MANIFEST_FILE = "structural_frame_release_export_manifest.json"
EXPORTED_MANIFEST_FILES = (*CONSTITUENT_MANIFEST_FILES, RELEASE_MANIFEST_FILE)

STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND = (
    "STRUCTURAL_FRAME_FOUR_ACTUATOR_REACTION_COUNTERPARTS_V1",
    "STRUCTURAL_FRAME_BILATERAL_RETENTION_ROOTS_V1",
    "STRUCTURAL_FRAME_BILATERAL_CROWN_SUPPORT_V1",
    "STRUCTURAL_FRAME_BILATERAL_DRY_PACKAGE_SUPPORTS_V1",
    "STRUCTURAL_FRAME_SHELL_WITH_JOINT_SERVICE_RELIEFS_V1",
)


class StructuralFrameReleaseExportError(ValueError):
    pass


def _validate_step(path: Path) -> None:
    if not path.is_file() or path.stat().st_size <= 0:
        raise StructuralFrameReleaseExportError(f"missing declared Cell 6 STEP: {path.name}")
    imported = cq.importers.importStep(str(path))
    value = imported.val()
    if not value.isValid() or not value.Solids() or float(value.Volume()) <= 0.0:
        raise StructuralFrameReleaseExportError(f"invalid declared Cell 6 STEP: {path.name}")


def _validate_manifest(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise StructuralFrameReleaseExportError(f"missing declared Cell 6 manifest: {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("physical_validation_eligible") is not False:
        raise StructuralFrameReleaseExportError(
            f"Cell 6 manifest weakened physical-evidence firewall: {path.name}"
        )
    return payload


def _reject_non_portable(value: object, trail: str = "report") -> None:
    """Refuse a release report that carries a machine-local path.

    Serialisation would fail on it anyway; naming the key turns an encoder
    TypeError into a statement about which producer leaked the path.
    """

    if isinstance(value, Path):
        raise StructuralFrameReleaseExportError(
            f"release report carries a filesystem path at {trail}: {value}"
        )
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_portable(item, f"{trail}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_non_portable(item, f"{trail}[{index}]")


def export_structural_frame_release_bundle(output_dir: str | Path) -> dict[str, object]:
    """Emit and verify the source-current standalone Cell 6 release bundle."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # These five do not agree on what to return: one yields the paths it wrote,
    # one a short {architecture_sha256, manifest_file, step_file} summary, and
    # the rest the manifest itself. The release report is built from the
    # manifests read back off disk instead, so it describes the artefacts that
    # actually shipped rather than three different producer conventions.
    export_structural_frame_actuator_reactions(output_dir)
    export_retention_root_counterparts(output_dir)
    export_structural_frame_crown_support(output_dir)
    export_structural_frame_dry_package_supports(output_dir)
    export_structural_frame_shell_joint_service(output_dir)

    for filename in EXPORTED_STEP_FILES:
        _validate_step(output_dir / filename)

    manifest_payloads = {
        filename: _validate_manifest(output_dir / filename)
        for filename in CONSTITUENT_MANIFEST_FILES
    }

    if manifest_payloads["structural_frame_retention_roots_manifest.json"].get(
        "source_frame_reaction_architecture_sha256"
    ) != manifest_payloads["structural_frame_actuator_reactions_manifest.json"].get(
        "architecture_sha256"
    ):
        raise StructuralFrameReleaseExportError(
            "retention-root release manifest is not source-chained to exported frame reactions"
        )
    if manifest_payloads["structural_frame_crown_support_manifest.json"].get(
        "source_retention_root_architecture_sha256"
    ) != manifest_payloads["structural_frame_retention_roots_manifest.json"].get(
        "architecture_sha256"
    ):
        raise StructuralFrameReleaseExportError(
            "crown-support release manifest is not source-chained to exported retention roots"
        )

    report = {
        "schema": SCHEMA,
        "exported_step_files": list(EXPORTED_STEP_FILES),
        "exported_manifest_files": list(EXPORTED_MANIFEST_FILES),
        "standalone_physical_geometry_pending_assembly_rebind": list(
            STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND
        ),
        "digital_topology": {
            filename.removesuffix("_manifest.json"): payload
            for filename, payload in sorted(manifest_payloads.items())
        },
        "physical_validation_eligible": False,
        "evidence_scope": "DIGITAL_BREP_AND_RELEASE_PROVENANCE_ONLY",
    }
    # A filesystem path in a release report is two defects at once: it is not
    # JSON, and it names a directory that only existed on the machine that
    # built it. Fail with the offending key rather than a bare TypeError from
    # the encoder.
    _reject_non_portable(report)
    (output_dir / RELEASE_MANIFEST_FILE).write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return report
