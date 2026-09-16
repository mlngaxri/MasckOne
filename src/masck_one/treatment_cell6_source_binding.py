from __future__ import annotations

"""Exact source identity for the treatment stack's consumed Cell 6 counterfaces.

This module supersedes only the stale source bindings embedded in the earlier
live117 reconciliation study. The earlier treatment calculations remain prior
digital evidence and are not reclassified as current physical evidence.

Counterface geometry is pinned by whole-file Git blob. The protected-anatomy zone
builder is pinned separately by canonical symbol source, because Cell 6 may move that
implementation between files without changing what treatment consumes: the current
frame owner splits ``structural_frame_realization`` into a thin source-identity
adapter plus a preserved ``_structural_frame_realization_impl`` blob and re-aliases
the module, so a whole-file pin on the imported module path would report drift that
did not occur, while no pin at all would let the consumed zone geometry change
silently. Neither outcome is acceptable on a protected-anatomy input, so the pin
follows the symbol.
"""

import ast
import hashlib
import inspect
import json
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_CELL6_SOURCE_BINDING_V2"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
RELEASED_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
CELL6_HEAD_SHA = "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
TREATMENT_PREMERGE_HEAD_SHA = "0073fc33d0605ea84e5322111d10a457585bdb59"
TREATMENT_CELL6_MERGE_CHECKPOINT_SHA = "d070d927d03aa995fd7d34e86dc2629a5b37a5b4"
SUPERSEDES_SOURCE_BINDING = "MASCK_ONE_TREATMENT_LIVE117_RECONCILIATION_V1_SOURCE_IDENTITY_ONLY"

# The Cell 6 owner head whose consumed sources were verified identical to the pinned
# geometry-source head. This records forward compatibility only. It does not claim the
# treatment geometry was re-derived against this head, and it is not a live-owner
# currency claim: a newer Cell 6 head must be re-verified before promotion.
CELL6_VERIFIED_COMPATIBLE_HEAD_SHA = "a248c814d10fb8cd73da83d0b40ace2309a93997"
CELL6_VERIFIED_COMPATIBLE_SEMANTICS = (
    "CONSUMED_SOURCE_IDENTITY_UNCHANGED_AT_THAT_HEAD_NOT_A_REDERIVATION_OR_LIVE_CURRENCY_CLAIM"
)

CONSUMED_COUNTERFACE_BLOB_SHA1 = {
    "src/masck_one/structural_frame_actuator_mates.py": "3cedc1a0032b418d9e02592bb4996e29dc9632b7",
    "src/masck_one/structural_frame_actuator_reactions.py": "dae953807584b97747cf3f936271e019b6746d4f",
    "src/masck_one/structural_frame_carrier_interfaces.py": "81ecaa0e6b924d128d8c83bcde6a12c868f0f318",
    "src/masck_one/structural_frame_carrier_preload.py": "83338cceb2adde4855e7e67ba9e96255d32ca00b",
    "src/masck_one/structural_frame_carrier_landing.py": "a7497537b3851883dc3efa2766f395c2f4b070a0",
    "src/masck_one/structural_frame_carrier_detent.py": "693d4f6cbbc915ec2e6e6ea8ae069f0f8969cb5d",
}

# treatment_mounted_four_zone imports this private Cell 6 symbol and builds every
# protected-anatomy zone solid that the station nominal/operational/service collision
# screens measure against. It is not a counterface, so it sat outside the counterface
# blob set and was consumed with no source binding at all.
PROTECTED_ZONE_SYMBOL = "_protected_zone_solid"
PROTECTED_ZONE_IMPORT_MODULE = "masck_one.structural_frame_realization"
PROTECTED_ZONE_SOURCE_SHA256 = (
    "0cfb3bf765c91c062694b54d06b2310ab233a24a7aeb3796e70df81910e35d40"
)
# Ordered candidates for the file that carries the implementation. Cell 6 relocated it
# from the imported module into a preserved implementation blob; both layouts must
# resolve to the same pinned symbol source or verification fails closed.
PROTECTED_ZONE_IMPL_CANDIDATE_PATHS = (
    "src/masck_one/_structural_frame_realization_impl.py",
    "src/masck_one/structural_frame_realization.py",
)

HISTORICAL_STALE_BINDINGS = {
    "studies/treatment_live117_reconciliation.py:CELL6_HEAD_SHA": "3e840d52d641b429669928ab9e4c207f08086ca1",
    "src/masck_one/treatment_terminal_kinematic_seat.py:SOURCE_CELL6_HEAD_SHA": "fcccde02b31cc1c4e01136630d92e550e4e09a11",
}

PUSHED_EVIDENCE_STATUS = {
    "contact_equilibrium_zero_preload_wrench_screen": "PUSHED_PRIOR_DIGITAL_EVIDENCE",
    "exact_bezier_terminal_cam_plus_flat_land": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
    "moved_opposed_z_contacts_clearing_central_bridge": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
    "corrected_spring_clamp_exits": "NO_PUSHED_EVIDENCE_FOUND_IN_LIVE_TREATMENT_OWNER_OR_DISCOVERED_TREATMENT_BRANCHES",
}

PHYSICAL_VALIDATION_ELIGIBLE = False


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def canonical_symbol_source(text: str) -> str:
    """Canonical consumed-source form: LF endings, no leading or trailing blank space.

    ``inspect.getsource`` keeps the trailing newline and ``ast.get_source_segment``
    drops it. Both must hash alike or the same unchanged symbol would verify from one
    reader and fail from the other. Interior bytes are never normalised.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def symbol_source_sha256(text: str) -> str:
    return hashlib.sha256(canonical_symbol_source(text).encode("utf-8")).hexdigest()


def extract_symbol_source(module_text: str, symbol: str) -> str:
    """Return the exact source segment defining ``symbol`` at module level."""
    tree = ast.parse(module_text)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol:
            segment = ast.get_source_segment(module_text, node)
            if segment is None:
                raise ValueError(f"could not recover the source segment defining {symbol}")
            return segment
    raise ValueError(f"{symbol} is not defined at module level in the given source")


def verify_consumed_counterface_blobs(repo_root: str | Path) -> dict[str, str]:
    root = Path(repo_root)
    observed: dict[str, str] = {}
    for relative, expected in CONSUMED_COUNTERFACE_BLOB_SHA1.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        actual = git_blob_sha1(path.read_bytes())
        if actual != expected:
            raise ValueError(f"source binding mismatch for {relative}: expected {expected}, got {actual}")
        observed[relative] = actual
    return observed


def verify_consumed_protected_zone_source(repo_root: str | Path) -> dict[str, str]:
    """Bind the consumed protected-anatomy zone builder to its pinned symbol source.

    Fails closed. A relocated implementation file is accepted only when the symbol it
    defines is byte-identical to the pinned source; a changed symbol is refused even if
    the file path is unchanged.
    """
    root = Path(repo_root)
    observed: dict[str, str] = {}
    for relative in PROTECTED_ZONE_IMPL_CANDIDATE_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        try:
            source = extract_symbol_source(path.read_text(encoding="utf-8"), PROTECTED_ZONE_SYMBOL)
        except (SyntaxError, ValueError):
            continue
        digest = symbol_source_sha256(source)
        observed[relative] = digest
        if digest == PROTECTED_ZONE_SOURCE_SHA256:
            return {
                "path": relative,
                "symbol": PROTECTED_ZONE_SYMBOL,
                "symbol_source_sha256": digest,
                "carrier_blob_sha1": git_blob_sha1(path.read_bytes()),
            }
    raise ValueError(
        f"consumed protected-anatomy builder {PROTECTED_ZONE_SYMBOL} does not match the "
        f"treatment source binding {PROTECTED_ZONE_SOURCE_SHA256}; "
        f"observed={observed or 'SYMBOL_NOT_FOUND_IN_ANY_CANDIDATE_PATH'}"
    )


def verify_runtime_protected_zone_binding() -> dict[str, str]:
    """Bind the actually imported protected-zone builder to its pinned symbol source.

    This is the binding with teeth: it follows the real import, so a re-aliased module,
    a relocated implementation or a monkeypatched replacement is caught regardless of
    what any file on disk contains.
    """
    from .structural_frame_realization import _protected_zone_solid

    try:
        source = inspect.getsource(_protected_zone_solid)
    except (OSError, TypeError) as error:
        raise ValueError(
            f"imported {PROTECTED_ZONE_SYMBOL} has no recoverable source, so the consumed "
            "protected-anatomy geometry cannot be bound"
        ) from error
    digest = symbol_source_sha256(source)
    if digest != PROTECTED_ZONE_SOURCE_SHA256:
        raise ValueError(
            f"imported {PROTECTED_ZONE_SYMBOL} does not match the treatment source "
            f"binding: expected {PROTECTED_ZONE_SOURCE_SHA256}, got {digest}"
        )
    return {
        "symbol": PROTECTED_ZONE_SYMBOL,
        "import_module": PROTECTED_ZONE_IMPORT_MODULE,
        "symbol_source_sha256": digest,
        "resolved_source_file": str(inspect.getsourcefile(_protected_zone_solid)),
    }


def manifest() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "coordinate_frame_id": WORLD_FRAME_ID,
        "released_main_sha": RELEASED_MAIN_SHA,
        "cell6_head_sha": CELL6_HEAD_SHA,
        "cell6_verified_compatible_head_sha": CELL6_VERIFIED_COMPATIBLE_HEAD_SHA,
        "cell6_verified_compatible_semantics": CELL6_VERIFIED_COMPATIBLE_SEMANTICS,
        "treatment_premerge_head_sha": TREATMENT_PREMERGE_HEAD_SHA,
        "treatment_cell6_merge_checkpoint_sha": TREATMENT_CELL6_MERGE_CHECKPOINT_SHA,
        "consumed_counterface_blob_sha1": dict(CONSUMED_COUNTERFACE_BLOB_SHA1),
        "consumed_protected_zone_symbol": PROTECTED_ZONE_SYMBOL,
        "consumed_protected_zone_import_module": PROTECTED_ZONE_IMPORT_MODULE,
        "consumed_protected_zone_source_sha256": PROTECTED_ZONE_SOURCE_SHA256,
        "consumed_protected_zone_binding_rule": (
            "SYMBOL_SOURCE_PINNED_NOT_CARRIER_FILE_BLOB; RELOCATION_ALLOWED_CHANGE_REFUSED"
        ),
        "supersedes_source_binding": SUPERSEDES_SOURCE_BINDING,
        "historical_stale_bindings": dict(HISTORICAL_STALE_BINDINGS),
        "pushed_evidence_status": dict(PUSHED_EVIDENCE_STATUS),
        "authority_rule": "V2_IS_CURRENT_FOR_SOURCE_IDENTITY_ONLY; PRIOR_RECONCILIATION_CALCULATIONS_REMAIN_PRIOR_DIGITAL_EVIDENCE",
        "physical_validation_eligible": PHYSICAL_VALIDATION_ELIGIBLE,
        "physical_validation": "OPEN; SOURCE_PROVENANCE_IS_NOT_FORCE_COMFORT_FATIGUE_WEAR_ACOUSTIC_OR_SUPPLIER_EVIDENCE",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    payload["binding_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
