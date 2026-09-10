from __future__ import annotations

"""Mounted four-zone V10: source-correct verification successor to V9.

V10 does not introduce another physical treatment architecture. It deliberately
reuses the selected V9 station geometry and current V4 guided-datum stack, while
correcting two evidence-layer defects that prevented promotion:

- the V9 manifest still named an older Cell 6 head after the treatment owner had
  already rebound the active datum architecture to the newer Cell 6 owner head;
- the old V9 wording implied every source face was prism-swept even though exact
  planar/cylindrical faces tangent to translation generate zero 3-D swept volume and
  must be excluded analytically before OpenCascade prism construction.

Manufactured B-reps, datum/load-path intent, 40 Hz treatment motion, service travel,
protected regions and collision thresholds are unchanged. Physical force, friction,
wear, fatigue, wet contamination, acoustic behavior and subjective feel remain
validation gates.
"""

import json
from pathlib import Path

import cadquery as cq

from . import treatment_mounted_four_zone_v9 as v9
from .treatment_terminal_datum_preload_v4 import (
    SOURCE_CELL6_HEAD_SHA as DATUM_SOURCE_CELL6_HEAD_SHA,
    TerminalDatumPreloadV4Architecture,
)
from .treatment_mounted_four_zone import MountedFourZoneArchitecture

SCHEMA_V10 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V10"
SOURCE_MAIN_SHA = v9.SOURCE_MAIN_SHA
SOURCE_CELL6_HEAD_SHA = DATUM_SOURCE_CELL6_HEAD_SHA
SOURCE_FAILURE_EVIDENCE_HEAD = v9.SOURCE_FAILURE_EVIDENCE_HEAD


class TreatmentMountedFourZoneV10Error(v9.TreatmentMountedFourZoneV9Error):
    pass


def build_mounted_four_zone_architecture_v10(
    **kwargs,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadV4Architecture]:
    architecture, datums = v9.build_mounted_four_zone_architecture_v9(**kwargs)
    if datums.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentMountedFourZoneV10Error(
            "V10 terminal datums are not bound to the active Cell 6 owner head"
        )
    return architecture, datums


def fusion_handoff_manifest_v10(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadV4Architecture,
) -> dict[str, object]:
    payload = v9.fusion_handoff_manifest(architecture, datums)
    payload.update(
        {
            "schema": "MASCK_ONE_TREATMENT_FUSION_HANDOFF_V3",
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
            "verification_successor": SCHEMA_V10,
            "reference_sweep_semantics": (
                "BOOLEAN_FREE_ENDPOINT_AND_POSITIVE_FACE_PRISM_COMPOUNDS; "
                "ANALYTICALLY_ZERO_VOLUME_PLANAR_OR_CYLINDRICAL_TANGENT_FACE_SWEEPS_EXCLUDED_BEFORE_KERNEL; "
                "POSITIVE_REFERENCE_SOLIDS_AND_COLLISION_COMMONS_REMAIN_STRICT"
            ),
        }
    )
    return payload


def manifest_v10(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadV4Architecture,
) -> dict[str, object]:
    if datums.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
        raise TreatmentMountedFourZoneV10Error("cannot manifest stale terminal datum source")

    payload = v9.manifest_v9(architecture, datums)
    payload.update(
        {
            "schema": SCHEMA_V10,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
            "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
            "supersedes": v9.SCHEMA_V9,
            "V9_status": (
                "SUPERSEDED_AS_PROMOTION_CANDIDATE_FOR_STALE_CELL6_HEAD_DECLARATION_AND_"
                "PRE_TANGENT_FILTER_REFERENCE_SWEEP_WORDING; PHYSICAL_GEOMETRY_REUSED"
            ),
            "verification_revision": (
                "MANUFACTURED_BREPS_STRICT; SOURCE_CELL6_HEAD_REBOUND_TO_ACTIVE_OWNER; "
                "BOOLEAN_FREE_TRANSLATION_REFERENCE_WITH_ANALYTIC_ZERO_VOLUME_TANGENT_FACE_FILTER; "
                "COLLISION_SOLID_PAIR_VOLUMETRIC; NO_COLLISION_OR_VALIDITY_THRESHOLD_WEAKENED"
            ),
            "physical_architecture_changed_from_v9": False,
            "physical_validation_eligible": False,
        }
    )
    payload["fusion_handoff"] = fusion_handoff_manifest_v10(architecture, datums)
    return payload


def export_mounted_four_zone_architecture_v10(output_dir: Path) -> dict[str, object]:
    """Export the selected V9 material geometry with V10 evidence metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, datums = build_mounted_four_zone_architecture_v10()
    datum_map = {row.reaction_id: row for row in datums.stations}
    installed_station_shapes: list[cq.Shape] = []
    handoff = fusion_handoff_manifest_v10(architecture, datums)

    for station in architecture.stations:
        slug = station.reaction_id.lower()
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)

        for name, shape in material.items():
            suffix = "REFERENCE" if name.endswith("_spring_installed") else "MANUFACTURED"
            cq.exporters.export(
                shape,
                str(output_dir / f"{slug}_{name}_{suffix}.step"),
            )

        for free_name in ("terminal_x_spring_free", "terminal_z_spring_free"):
            cq.exporters.export(
                reference[free_name],
                str(output_dir / f"{slug}_{free_name}_MANUFACTURED.step"),
            )

        installed = cq.Compound.makeCompound(list(material.values()))
        installed_station_shapes.append(installed)
        cq.exporters.export(
            installed,
            str(output_dir / f"{slug}_installed_station_assembly.step"),
        )
        cq.exporters.export(
            station.operational_sweep,
            str(output_dir / f"{slug}_operational_sweep_REFERENCE.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_service_sweep_REFERENCE.step"),
        )

        station_manifest = {
            "reaction_id": station.reaction_id,
            "terminal_datum": datum_map[station.reaction_id].manifest(),
            "fusion_handoff": next(
                row
                for row in handoff["stations"]
                if row["reaction_id"] == station.reaction_id
            ),
        }
        (output_dir / f"{slug}_fusion_manifest_v10.json").write_text(
            json.dumps(station_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    cq.exporters.export(
        cq.Compound.makeCompound(installed_station_shapes),
        str(output_dir / "treatment_four_zone_installed_assembly_v10.step"),
    )

    manifest = manifest_v10(architecture, datums)
    (output_dir / "treatment_mounted_four_zone_v10_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "treatment_fusion_handoff_v3.json").write_text(
        json.dumps(manifest["fusion_handoff"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
