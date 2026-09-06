from __future__ import annotations

"""Observed non-authoritative wet/electrical candidate landscape.

GitHub metadata heads are recorded only to invalidate stale integration evidence.
Unmerged candidates never become release authority through this receipt.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re


SCHEMA = "MASCK_ONE_CELL4_WET_ELECTRICAL_CANDIDATE_LANDSCAPE_V1"
SOURCE_MAIN_SHA = "b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc"
OBSERVED_AT_UTC = "2026-09-06T07:27:00Z"
EVIDENCE_STATUS = (
    "OBSERVED_GITHUB_CANDIDATE_IDENTITY_ONLY_NOT_RELEASED_AUTHORITY_GEOMETRY_"
    "CI_REVIEW_SUPPLIER_OR_PHYSICAL_EVIDENCE"
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_REPO_ROOT = Path(__file__).resolve().parents[2]


class WetElectricalCandidateLandscapeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CandidateHead:
    cell: int
    pr_number: int
    head_sha: str
    base_sha: str
    role: str
    disposition: str
    source_path: str | None
    geometry_consumed: bool = False

    def __post_init__(self) -> None:
        if type(self.cell) is not int or self.cell < 4 or self.cell > 14:
            raise WetElectricalCandidateLandscapeError(
                "candidate cell must be an exact int in Cell 4 to 14"
            )
        if type(self.pr_number) is not int or self.pr_number <= 0:
            raise WetElectricalCandidateLandscapeError(
                "candidate PR number must be a positive exact int"
            )
        if type(self.head_sha) is not str or _SHA40.fullmatch(self.head_sha) is None:
            raise WetElectricalCandidateLandscapeError(
                "candidate head must be canonical lowercase 40-hex"
            )
        if type(self.base_sha) is not str or _SHA40.fullmatch(self.base_sha) is None:
            raise WetElectricalCandidateLandscapeError(
                "candidate base must be canonical lowercase 40-hex"
            )
        for label, value in (("role", self.role), ("disposition", self.disposition)):
            if type(value) is not str or not value or value != value.strip():
                raise WetElectricalCandidateLandscapeError(
                    f"{label} must be exact nonblank text"
                )
        if self.source_path is not None and (
            type(self.source_path) is not str
            or not self.source_path.startswith("src/masck_one/")
        ):
            raise WetElectricalCandidateLandscapeError(
                "candidate source_path must be a masck_one source path or None"
            )
        if type(self.geometry_consumed) is not bool or self.geometry_consumed:
            raise WetElectricalCandidateLandscapeError(
                "unmerged candidate geometry must remain unconsumed"
            )

    @property
    def based_on_live_main(self) -> bool:
        return self.base_sha == SOURCE_MAIN_SHA

    def manifest(self) -> dict[str, object]:
        self.__post_init__()
        return {
            "cell": self.cell,
            "pr_number": self.pr_number,
            "head_sha": self.head_sha,
            "base_sha": self.base_sha,
            "based_on_live_main": self.based_on_live_main,
            "role": self.role,
            "disposition": self.disposition,
            "source_path": self.source_path,
            "geometry_consumed": self.geometry_consumed,
        }


CANDIDATE_HEADS = (
    CandidateHead(
        4, 80,
        "6e3e05812406620072b37f54827b8345ed55ccea",
        "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30",
        "CLEANSER_STORAGE_SERVICE_GEOMETRY",
        "STALE_BASE_REWORK_NOT_RELEASED",
        "src/masck_one/realized_cleanser_storage.py",
    ),
    CandidateHead(
        4, 85,
        "668727ad2676a7d41f095878ff5d9110c8f7a44a",
        "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30",
        "FRESH_WATER_PUMP_SCREENING_PACKAGE",
        "STALE_BASE_REBASE_REQUIRED_NOT_RELEASED",
        "src/masck_one/realized_fresh_water_pump.py",
    ),
    CandidateHead(
        4, 94,
        "1eb826fe859c6d5ee6dc0097aa58a67944bb530b",
        "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30",
        "CLEANSER_PUMP_SCREENING_PACKAGE",
        "STALE_BASE_REBASE_REQUIRED_NOT_RELEASED",
        "src/masck_one/realized_cleanser_pump.py",
    ),
    CandidateHead(
        4, 96,
        "2626a4f5c3b971b7caf5b384a44c262489ccf128",
        "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30",
        "MIXED_WASTE_PUMP_SCREENING_PACKAGE",
        "STALE_BASE_REBASE_REQUIRED_NOT_RELEASED",
        "src/masck_one/realized_waste_pump.py",
    ),
    CandidateHead(
        4, 100,
        "f788284d4a4e9f30d0e35b1ceea6c716e74a5e16",
        "21cf8c4fb8ca0d20ddb58f90bcee6275bc98ca30",
        "PASSIVE_BACKFLOW_SCREENING_PACKAGE",
        "STALE_BASE_REFERENCE_ONLY_CANDIDATE_NOT_RELEASED",
        "src/masck_one/realized_passive_backflow.py",
    ),
    CandidateHead(
        9, 107,
        "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "FRESH_WATER_SOURCE_GEOMETRY",
        "PRE_121_BASE_REBASE_REQUIRED_SPECIALIST_CANDIDATE_NOT_RELEASED",
        "src/masck_one/realized_fresh_water_source.py",
    ),
    CandidateHead(
        10, 125,
        "3703f9b45defc91e05fbbe4516d28cd012db2efd",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "CLEANSER_CASSETTE_RECONCILIATION",
        "PRE_121_BASE_REBASE_REQUIRED_SPECIALIST_CANDIDATE_NOT_RELEASED",
        "src/masck_one/cleanser_cassette_reconciliation.py",
    ),
    CandidateHead(
        11, 115,
        "4da053e57534c98617b9e8abfae7a35436a3718c",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "MIXED_WASTE_CARTRIDGE_GEOMETRY",
        "PRE_121_BASE_REBASE_REQUIRED_DRAFT_SPECIALIST_CANDIDATE_NOT_RELEASED",
        "src/masck_one/realized_waste_cartridge.py",
    ),
    CandidateHead(
        12, 111,
        "fa017c8379dabaefeecf53bf770858bebfde3067",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "DRY_SIDE_PACKAGE_GEOMETRY",
        "PRE_121_BASE_REBASE_REQUIRED_SPECIALIST_CANDIDATE_NOT_RELEASED",
        "src/masck_one/dry_side_package.py",
    ),
    CandidateHead(
        13, 113,
        "dde7348002d13da77049dc1d540d79d389aac09f",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "HARNESS_ENDPOINT_INVENTORY",
        "PRE_121_BASE_REBASE_REQUIRED_SPECIALIST_RECEIPT_NOT_ROUTE_GEOMETRY_NOT_RELEASED",
        "src/masck_one/harness_endpoint_inventory.py",
    ),
    CandidateHead(
        14, 110,
        "7b32c674860cab87cbdd1f7e3303a4ce53515e95",
        "afe29ff78419b6625dca5594974b6351f6f80e1b",
        "PHYSICAL_HMI_WARM_THERMAL_DECISION_PACKAGE",
        "PRE_121_BASE_REBASE_REQUIRED_REFERENCE_PACKAGE_CANDIDATE_NOT_RELEASED",
        "src/masck_one/physical_hmi_thermal.py",
    ),
)

SPECIALIST_CELLS_WITH_PUBLISHED_HEADS = (9, 10, 11, 12, 13, 14)
SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS: tuple[int, ...] = ()

LINEAGE_DISPOSITION = (
    {
        "domain": "FRESH_WATER_SOURCE",
        "strongest_current_candidate_pr": 107,
        "relation": "PRE_121_BASE_SUCCESSOR_TO_HISTORICAL_75_78_SOURCE_LINEAGE",
        "remaining_dependency": (
            "POST_121_REBASE_RELEASED_PUMP_AND_MANIFOLD_WORLD_DATUMS_BEFORE_COMPLETE_ROUTE_CENTERLINES"
        ),
    },
    {
        "domain": "CLEANSER_SOURCE",
        "strongest_current_candidate_pr": 125,
        "relation": "PRE_121_BASE_CASSETTE_SUCCESSOR_CONSUMES_80_STORAGE_GEOMETRY_WITHOUT_PROMOTING_STALE_BRANCH",
        "remaining_dependency": "POST_121_REBASE_FRAME_ATTACHMENT_PUMP_AND_MANIFOLD_GEOMETRY",
    },
    {
        "domain": "MIXED_WASTE",
        "strongest_current_candidate_pr": 115,
        "relation": (
            "PRE_121_BASE_CARTRIDGE_SUCCESSOR_DOES_NOT_SUPERSEDE_STALE_96_100_"
            "PUMP_BACKFLOW_PACKAGES"
        ),
        "remaining_dependency": (
            "POST_121_REBASE_CARTRIDGE_CAPACITY_REDESIGN_CURRENT_MAIN_PUMP_PASSIVE_BACKFLOW_"
            "ACQUISITION_AND_NONTELEPORTING_SERVICE_GEOMETRY"
        ),
    },
    {
        "domain": "DRY_SIDE",
        "strongest_current_candidate_pr": 111,
        "relation": "PRE_121_BASE_DRY_SIDE_PACKAGE_CANDIDATE_REPLACES_MANUAL_B_AS_DONOR_TARGET",
        "remaining_dependency": (
            "POST_121_REBASE_FRAME_POSITIVE_ATTACHMENT_DOOR_RETENTION_SEAL_ELECTRICAL_SAFETY_AND_"
            "PRODUCTION_PACKAGE_SELECTION"
        ),
    },
    {
        "domain": "HARNESS_BULKHEAD",
        "strongest_current_candidate_pr": 113,
        "relation": "PRE_121_BASE_ENDPOINT_INVENTORY_ONLY_NO_ROUTE_GEOMETRY",
        "remaining_dependency": (
            "POST_121_REBASE_RELEASED_ELECTRICAL_MATING_DATUMS_WET_DRY_BULKHEAD_AND_"
            "NONTELEPORTING_HARNESS_ROUTES"
        ),
    },
    {
        "domain": "HMI_WARM_THERMAL",
        "strongest_current_candidate_pr": 110,
        "relation": "PRE_121_BASE_REFERENCE_PACKAGE_AND_DECISION_STATE_ONLY",
        "remaining_dependency": (
            "POST_121_REBASE_FINAL_CONTROL_MAPPING_SWITCH_SEAL_WARM_HARDWARE_POWER_SAFETY_"
            "DRY_SIDE_AND_HARNESS_HANDOFF"
        ),
    },
)


def _digest(payload: object) -> str:
    return sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_candidate_producers_absent() -> None:
    for candidate in CANDIDATE_HEADS:
        if candidate.source_path is None:
            continue
        if (_REPO_ROOT / candidate.source_path).exists():
            raise WetElectricalCandidateLandscapeError(
                "candidate producer appeared in checked-out release tree: "
                f"PR #{candidate.pr_number} {candidate.source_path}; reconstruct before promotion"
            )


def build_candidate_landscape_manifest() -> dict[str, object]:
    expected_specialist_cells = (9, 10, 11, 12, 13, 14)
    if tuple(candidate.cell for candidate in CANDIDATE_HEADS if candidate.cell >= 9) != expected_specialist_cells:
        raise WetElectricalCandidateLandscapeError("specialist published-head set changed")
    if SPECIALIST_CELLS_WITH_PUBLISHED_HEADS != expected_specialist_cells:
        raise WetElectricalCandidateLandscapeError("published specialist-cell set changed")
    if SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS != ():
        raise WetElectricalCandidateLandscapeError("absent specialist-cell set changed")
    if set(SPECIALIST_CELLS_WITH_PUBLISHED_HEADS) & set(SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS):
        raise WetElectricalCandidateLandscapeError("specialist presence sets overlap")
    for candidate in CANDIDATE_HEADS:
        candidate.__post_init__()
    _require_candidate_producers_absent()
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "source_main_sha": SOURCE_MAIN_SHA,
        "observed_at_utc": OBSERVED_AT_UTC,
        "candidate_heads": [candidate.manifest() for candidate in CANDIDATE_HEADS],
        "specialist_cells_with_published_heads": list(SPECIALIST_CELLS_WITH_PUBLISHED_HEADS),
        "specialist_cells_without_published_heads": list(SPECIALIST_CELLS_WITHOUT_PUBLISHED_HEADS),
        "lineage_disposition": list(LINEAGE_DISPOSITION),
        "candidate_geometry_consumed": False,
        "evidence_status": EVIDENCE_STATUS,
    }
    payload["manifest_sha256"] = _digest(payload)
    return payload
