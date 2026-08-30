from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from .actuation_architecture import ActuationArchitecture
from .authority import Authority
from .fresh_fluid import FreshFluidArchitecture
from .spatial import Point3
from .waste_architecture import WasteArchitecture
from .wearable_architecture import WearableArchitecture


class AlphaClosureError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class HygieneCavity:
    cavity_id: str
    hygiene_class: str
    drainage_status: str
    drying_status: str
    cleaning_access_status: str
    contamination_boundary_status: str


@dataclass(frozen=True, slots=True)
class AssemblyNode:
    node_id: str
    parent_id: str | None
    joint_status: str
    insertion_trajectory_status: str
    removal_trajectory_status: str
    service_status: str


@dataclass(frozen=True, slots=True)
class DFMContract:
    shell_nominal_wall_mm: float
    shell_development_min_mm: float
    nominal_draft_deg: float
    rib_thickness_ratio_range: tuple[float, float]
    visible_seam_gap_mm: float
    visible_seam_tolerance_mm: float
    flush_mismatch_max_mm: float
    boss_geometry_status: str
    parting_strategy_status: str
    tolerance_stack_status: str
    ctq_register_status: str


@dataclass(frozen=True, slots=True)
class MassLedgerEntry:
    entry_id: str
    quantity: int
    unit_mass_g: float | None
    center_mm: Point3 | None
    source_status: str

    @property
    def known_total_g(self) -> float | None:
        return None if self.unit_mass_g is None else self.quantity * self.unit_mass_g


@dataclass(frozen=True, slots=True)
class QuantitativeLedgers:
    mass_entries: tuple[MassLedgerEntry, ...]
    known_dry_mass_g: float
    mass_ledger_complete: bool
    known_component_cg_mm: Point3 | None
    dry_mass_limit_g: float
    loaded_mass_limit_g: float
    cg_z_limit_mm: float
    pitch_torque_limit_Nm: float
    introduced_liquid_per_cycle_mL: float
    reservoir_gross_mL: float
    cartridge_capacity_target_mL: float
    battery_reference_energy_Wh: float
    runtime_status: str
    thermal_ledger_status: str
    closure_status: str


@dataclass(frozen=True, slots=True)
class ReleaseContract:
    reconstruction_order: tuple[str, ...]
    export_formats: tuple[str, ...]
    drawing_status: str
    release_manifest_status: str
    exact_head_ci_required: bool
    required_physical_gate_iterations: tuple[int, ...]
    integrated_mvp_gate_iteration: int


@dataclass(frozen=True, slots=True)
class AlphaClosure:
    source_architecture_hashes: tuple[str, ...]
    hygiene_cavities: tuple[HygieneCavity, ...]
    assembly_nodes: tuple[AssemblyNode, ...]
    dfm: DFMContract
    ledgers: QuantitativeLedgers
    release: ReleaseContract
    completed_iterations: tuple[int, ...]
    digital_alpha_status: str
    physical_mvp_status: str
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if not self.source_architecture_hashes or any(len(value) != 64 for value in self.source_architecture_hashes):
            raise AlphaClosureError("Alpha closure requires exact source architecture hashes")
        cavity_ids = [cavity.cavity_id for cavity in self.hygiene_cavities]
        if len(cavity_ids) != len(set(cavity_ids)):
            raise AlphaClosureError("Every hygiene cavity must have a unique ID")
        allowed_classes = {"DRY_ALWAYS", "WET_DRAINABLE", "WET_REMOVABLE", "SEALED_NONUSER"}
        if any(cavity.hygiene_class not in allowed_classes for cavity in self.hygiene_cavities):
            raise AlphaClosureError("Every cavity requires exactly one controlled hygiene class")
        node_ids = {node.node_id for node in self.assembly_nodes}
        if len(node_ids) != len(self.assembly_nodes) or "MASCK_ONE_ASSEMBLY" not in node_ids:
            raise AlphaClosureError("Assembly hierarchy requires unique nodes and one controlled root")
        if any(node.parent_id is not None and node.parent_id not in node_ids for node in self.assembly_nodes):
            raise AlphaClosureError("Every assembly parent must exist")
        if self.dfm.rib_thickness_ratio_range[0] > self.dfm.rib_thickness_ratio_range[1]:
            raise AlphaClosureError("DFM rib ratio range must be ordered")
        calculated_known = sum(entry.known_total_g or 0.0 for entry in self.ledgers.mass_entries)
        if not math.isclose(calculated_known, self.ledgers.known_dry_mass_g, abs_tol=1e-9):
            raise AlphaClosureError("Known-mass subtotal must be generated from traceable entries")
        complete = all(entry.unit_mass_g is not None and entry.center_mm is not None for entry in self.ledgers.mass_entries)
        if complete != self.ledgers.mass_ledger_complete:
            raise AlphaClosureError("Mass completeness flag must match ledger evidence")
        if self.completed_iterations != tuple(range(35, 41)):
            raise AlphaClosureError("Alpha closure must cover digital Iterations 35-40")
        if self.release.integrated_mvp_gate_iteration != 64:
            raise AlphaClosureError("Physical MVP gate must remain at roadmap Iteration 64")
        if self.physical_validation_eligible:
            raise AlphaClosureError("Digital Alpha closure cannot become physical MVP evidence")

    @property
    def topology_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "source_architecture_hashes": list(self.source_architecture_hashes),
            "hygiene_cavities": [asdict(cavity) for cavity in self.hygiene_cavities],
            "assembly_nodes": [asdict(node) for node in self.assembly_nodes],
            "dfm": asdict(self.dfm),
            "ledgers": {
                **asdict(self.ledgers),
                "mass_entries": [
                    {
                        **asdict(entry),
                        "center_mm": None if entry.center_mm is None else list(entry.center_mm.as_tuple()),
                        "known_total_g": entry.known_total_g,
                    }
                    for entry in self.ledgers.mass_entries
                ],
                "known_component_cg_mm": (
                    None
                    if self.ledgers.known_component_cg_mm is None
                    else list(self.ledgers.known_component_cg_mm.as_tuple())
                ),
            },
            "release": asdict(self.release),
            "completed_iterations": list(self.completed_iterations),
            "digital_alpha_status": self.digital_alpha_status,
            "physical_mvp_status": self.physical_mvp_status,
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            result["topology_sha256"] = self.topology_sha256
        return result


def _mass_ledgers(
    authority: Authority,
    actuation: ActuationArchitecture,
    fluid: FreshFluidArchitecture,
    waste: WasteArchitecture,
    wearable: WearableArchitecture,
) -> QuantitativeLedgers:
    entries = []
    for station in actuation.stations:
        entries.append(
            MassLedgerEntry(
                station.station_id,
                1,
                station.reference.mass_g,
                station.local_frame.origin,
                station.reference.supplier_status,
            )
        )
    for station in fluid.pump_stations:
        entries.append(
            MassLedgerEntry(
                station.station_id,
                1,
                station.reference.mass_g,
                station.center_mm,
                station.reference.role_status,
            )
        )
    entries.extend(
        (
            MassLedgerEntry(
                waste.pump_station.station_id,
                1,
                4.0,
                waste.pump_station.center_mm,
                "TAKASAGO_SDMP_APPROXIMATE_DEVELOPMENT_REFERENCE_MASS",
            ),
            MassLedgerEntry(
                "BATTERY_REFERENCE",
                1,
                wearable.dry_bay.benchmark_mass_g,
                wearable.dry_bay.battery_center_mm,
                wearable.dry_bay.production_selection_status,
            ),
        )
    )
    for unknown_id in (
        "RIGID_SHELL_AND_CLASS_A",
        "STRUCTURAL_FRAME",
        "COMPLIANT_INTERFACE",
        "FLUID_RESERVOIRS_MANIFOLDS_TUBES_AND_FLUID",
        "WASTE_CARTRIDGE_AND_RETAINED_CONTENT",
        "RETENTION_AND_QUICK_RELEASE",
        "ELECTRONICS_HMI_AND_THERMAL",
        "FASTENERS_SEALS_HARNESS_AND_ADHESIVES",
    ):
        entries.append(MassLedgerEntry(unknown_id, 1, None, None, "MASS_AND_CAD_CENTER_UNRESOLVED"))
    entry_tuple = tuple(entries)
    known = sum(entry.known_total_g or 0.0 for entry in entry_tuple)
    weighted = [entry for entry in entry_tuple if entry.known_total_g is not None and entry.center_mm is not None]
    cg = None
    if known > 0.0:
        cg = Point3(
            sum(entry.known_total_g * entry.center_mm.x for entry in weighted) / known,
            sum(entry.known_total_g * entry.center_mm.y for entry in weighted) / known,
            sum(entry.known_total_g * entry.center_mm.z for entry in weighted) / known,
        )
    voltage = authority.number("battery_reference", "nominal_voltage_V")
    capacity_Ah = authority.number("battery_reference", "capacity_mAh") / 1000.0
    return QuantitativeLedgers(
        entry_tuple,
        known,
        False,
        cg,
        authority.number("mass", "dry_target_max_g"),
        authority.number("mass", "loaded_absolute_max_g"),
        authority.number("mass", "cg_z_max_mm"),
        authority.number("mass", "pitch_torque_max_Nm"),
        fluid.introduced_liquid_mL,
        fluid.reservoir.gross_volume_mL,
        waste.cartridge.retained_capacity_target_mL,
        voltage * capacity_Ah,
        "BLOCKED_UNTIL_MODE_CURRENT_DUTY_CYCLES_AND_REAL_PACK_BEHAVIOR_ARE_CONTROLLED",
        "BLOCKED_UNTIL_HEATER_COOLING_AMBIENT_AND_FAULT_LOADS_ARE_CONTROLLED",
        "INCOMPLETE_NO_MASS_CG_TORQUE_RUNTIME_OR_THERMAL_PASS_CLAIM",
    )


def build_alpha_closure(
    authority: Authority,
    actuation: ActuationArchitecture,
    fluid: FreshFluidArchitecture,
    waste: WasteArchitecture,
    wearable: WearableArchitecture,
    source_hashes: tuple[str, ...],
) -> AlphaClosure:
    hygiene_classes = tuple(str(value) for value in authority.get("manufacturing", "hygiene_classes"))
    if hygiene_classes != ("DRY_ALWAYS", "WET_DRAINABLE", "WET_REMOVABLE", "SEALED_NONUSER"):
        raise AlphaClosureError("Machine authority hygiene-class order changed")
    cavities = (
        HygieneCavity("BATTERY_DRY_BAY", "DRY_ALWAYS", "NO_NORMAL_WET_PATH", "DRY_BOUNDARY_REQUIRED", "NONUSER_CELL_BAY", "SEPARATE_FROM_ALL_WET_ROUTES"),
        HygieneCavity("ELECTRONICS_DRY_BAY", "SEALED_NONUSER", "NO_DRAIN_RELY_ON_VALIDATED_SEAL", "SEALED_CAVITY", "NONUSER_SERVICE", "INGRESS_BOUNDARY_VALIDATION_REQUIRED"),
        HygieneCavity("FRESH_FLUID_RESERVOIR", "WET_REMOVABLE", "REMOVAL_DRAIN_PATH_UNRESOLVED", "DRYING_ACCESS_UNRESOLVED", "REFILL_CLEANING_ACCESS_REQUIRED", "FRESH_SIDE_ONLY"),
        HygieneCavity("FRESH_MANIFOLD_AND_GROOVES", "WET_DRAINABLE", "ENGINEERED_DRAINAGE_UNRESOLVED", "DRYING_TIME_AND_PATH_UNRESOLVED", "MANIFOLD_SERVICE_POLICY_UNRESOLVED", "SEPARATE_FROM_WASTE_AND_DRY_BAYS"),
        HygieneCavity("WASTE_ACQUISITION_PATHS", "WET_DRAINABLE", "ENGINEERED_DRAINAGE_UNRESOLVED", "DRYING_TIME_AND_PATH_UNRESOLVED", "CREVICE_AND_RESIDUE_ACCESS_UNRESOLVED", "CONTAMINATED_WASTE_BOUNDARY"),
        HygieneCavity("WASTE_CARTRIDGE", "WET_REMOVABLE", "REMOVAL_CONTAINS_RETAINED_FLUID", "OFF_DEVICE_DRYING_POLICY_UNRESOLVED", "KEYED_USER_SERVICE_REQUIRED", "ENCLOSED_REPLACEABLE_WASTE_BOUNDARY"),
        HygieneCavity("ACTUATOR_CAVITIES", "DRY_ALWAYS", "FAULT_DRAIN_DIVERSION_UNRESOLVED", "DRY_BOUNDARY_REQUIRED", "SERVICE_ACCESS_UNRESOLVED", "SEPARATE_FROM_FLUID_ROUTES"),
    )
    nodes = (
        AssemblyNode("MASCK_ONE_ASSEMBLY", None, "ROOT", "NOT_APPLICABLE", "NOT_APPLICABLE", "CONTROLLED_TOP_LEVEL"),
        AssemblyNode("FACIAL_SHELL_SUBASSEMBLY", "MASCK_ONE_ASSEMBLY", "FRAME_ATTACHMENT_CONTRACT", "NORMAL_TO_FACE_UNRESOLVED", "NORMAL_FROM_FACE_UNRESOLVED", "SERVICE_SEQUENCE_UNRESOLVED"),
        AssemblyNode("COMPLIANT_INTERFACE_SUBASSEMBLY", "FACIAL_SHELL_SUBASSEMBLY", "PERIMETER_CLAMP_CONTRACT", "SEAL_COMPRESSION_PATH_UNRESOLVED", "PEEL_REMOVAL_PATH_UNRESOLVED", "WET_REMOVABLE_POLICY_UNRESOLVED"),
        AssemblyNode("FRESH_FLUID_SUBASSEMBLY", "FACIAL_SHELL_SUBASSEMBLY", "ROUTE_INTERFACE_CONTRACT", "TUBE_AND_PUMP_INSERTION_UNRESOLVED", "SERVICE_REMOVAL_UNRESOLVED", "PURGE_AND_REPLACEMENT_POLICY_UNRESOLVED"),
        AssemblyNode("WASTE_SUBASSEMBLY", "FACIAL_SHELL_SUBASSEMBLY", "ROUTE_AND_CARTRIDGE_INTERFACE_CONTRACT", "KEYED_INSERTION_UNRESOLVED", "CONTAINED_REMOVAL_UNRESOLVED", "CONTAMINATION_CONTROL_UNRESOLVED"),
        AssemblyNode("RETENTION_SUBASSEMBLY", "MASCK_ONE_ASSEMBLY", "OFF_FACE_SUPPORT_INTERFACE", "DONNING_PATH_UNRESOLVED", "QUICK_RELEASE_PATH_UNRESOLVED", "RESET_AND_INSPECTION_UNRESOLVED"),
        AssemblyNode("DRY_BAY_SUBASSEMBLY", "RETENTION_SUBASSEMBLY", "SEALED_NONUSER_INTERFACE", "PACK_INSTALLATION_UNRESOLVED", "QUALIFIED_SERVICE_ONLY", "INGRESS_INSPECTION_UNRESOLVED"),
    )
    dfm = DFMContract(
        authority.number("geometry", "shell_nominal_wall_mm"),
        authority.number("geometry", "shell_absolute_development_min_mm"),
        authority.number("manufacturing", "mold_draft_nominal_deg"),
        tuple(float(value) for value in authority.get("manufacturing", "rib_thickness_ratio_range")),
        authority.number("geometry", "visible_seam", "gap_mm"),
        authority.number("geometry", "visible_seam", "tolerance_mm"),
        authority.number("geometry", "visible_seam", "flush_mismatch_max_mm"),
        "BOSS_DIAMETER_HEIGHT_FILLET_AND_FASTENER_SELECTION_UNRESOLVED",
        "PARTING_LINES_TOOL_ACTIONS_AND_SHUT_OFFS_UNRESOLVED",
        "TOLERANCE_STACK_SCHEMA_DEFINED_NUMERIC_STACKS_REQUIRE_REALIZED_PART_GEOMETRY",
        "AUTHORITY_REQUIREMENTS_CARRIED_FORWARD_PART_LEVEL_CTQS_REQUIRE_RELEASED_GEOMETRY",
    )
    release = ReleaseContract(
        (
            "IMPORT_AUTHORITY_AND_REGISTERED_REFERENCE",
            "RECONSTRUCT_DATUMS_AND_PROTECTED_VOLUMES",
            "RECONSTRUCT_INTERFACE_BOUNDARIES_AND_FRAME_TOPOLOGY",
            "RECONSTRUCT_ACTUATION_AND_FLUID_PACKAGING",
            "RECONSTRUCT_WEARABLE_RESERVATIONS_AND_ASSEMBLY_HIERARCHY",
            "VERIFY_HASHED_MANIFEST_AND_STEP_EXPORTS",
        ),
        ("STEP_AP242_DEVELOPMENT_EXPORT", "JSON_HASHED_RELEASE_MANIFEST"),
        "PRODUCTION_DRAWINGS_BLOCKED_PENDING_REALIZED_PART_DFM_AND_TOLERANCE_CLOSURE",
        "DETERMINISTIC_SOURCE_HASH_STEP_CHECKSUM_AND_EVIDENCE_GATE_MANIFEST_REQUIRED",
        True,
        tuple(range(41, 51)),
        64,
    )
    return AlphaClosure(
        source_hashes,
        cavities,
        nodes,
        dfm,
        _mass_ledgers(authority, actuation, fluid, waste, wearable),
        release,
        tuple(range(35, 41)),
        "DIGITAL_ALPHA_ARCHITECTURE_RELEASE_CANDIDATE_EXACT_HEAD_CI_REQUIRED",
        "BLOCKED_PENDING_PHYSICAL_EVIDENCE_ALPHA_BUILD_VALIDATION_AND_ITERATION64_GATE",
    )
