from __future__ import annotations

"""Cell 11 rebind of the released Cell 5 waste-cartridge DFM audit.

PR #95 intentionally failed closed if any cartridge realization source appeared. Cell 11
now supplies such a source, so this adapter preserves the exact released audit implementation
in ``waste_cartridge_dfm_legacy.py`` and changes only the provenance boundary needed to
inspect the candidate. The released package proxy remains excluded from development
assembly material and the candidate remains digitally unready while geometric capacity,
device-side retention, wet coupling/seal, continuous service motion, removed-state handling
and DFM/tolerance closure are unresolved.
"""

from dataclasses import replace

from . import waste_cartridge_dfm_legacy as _legacy
from .waste_cartridge_dfm_legacy import *  # noqa: F401,F403
from .model import MasckOneModel, build_model
from .realized_waste_cartridge import (
    BODY_STATUS as CANDIDATE_BODY_STATUS,
    CAPACITY_STATUS as CANDIDATE_CAPACITY_STATUS,
    CLOSURE_STATUS as CANDIDATE_CLOSURE_STATUS,
    HYGIENE_CLASSIFICATION as CANDIDATE_HYGIENE_CLASSIFICATION,
    INLET_STATUS as CANDIDATE_INLET_STATUS,
    KEY_STATUS as CANDIDATE_KEY_STATUS,
    PROTECTED_FACE_STATUS as CANDIDATE_PROTECTED_FACE_STATUS,
    SERVICE_STATUS as CANDIDATE_SERVICE_STATUS,
    build_realized_waste_cartridge,
)


SOURCE_MAIN_SHA = "afe29ff78419b6625dca5594974b6351f6f80e1b"
REALIZED_WASTE_CARTRIDGE_BLOB_SHA = "1e28ea17bf5dd3492c95722780252f8ec74831a8"
LEGACY_AUDIT_BLOB_SHA = "f9788cce30c14600c8a624509153596e46c1e478"

SOURCE_GIT_BLOB_IDENTITIES = (
    *_legacy.SOURCE_GIT_BLOB_IDENTITIES,
    ("src/masck_one/waste_cartridge_dfm_legacy.py", LEGACY_AUDIT_BLOB_SHA),
    ("src/masck_one/realized_waste_cartridge.py", REALIZED_WASTE_CARTRIDGE_BLOB_SHA),
)
EXPECTED_ABSENT_REALIZATION_PATHS = tuple(
    path
    for path in _legacy.EXPECTED_ABSENT_REALIZATION_PATHS
    if path != "src/masck_one/realized_waste_cartridge.py"
)

# The preserved implementation resolves these globals at validation/build time. Rebinding
# them retains all original hostile checks while making the new source an explicit
# provenance participant rather than an unexpected-file bypass.
_legacy.SOURCE_MAIN_SHA = SOURCE_MAIN_SHA
_legacy.SOURCE_GIT_BLOB_IDENTITIES = SOURCE_GIT_BLOB_IDENTITIES
_legacy.EXPECTED_ABSENT_REALIZATION_PATHS = EXPECTED_ABSENT_REALIZATION_PATHS


def _candidate_aware_requirements(audit, candidate):
    shell_interference = float(candidate.current_released_shell_interference_mm3)
    shell_state = (
        f" Candidate body/closure intersects current released shell by {shell_interference:.6f} mm3; "
        "candidate therefore remains standalone review geometry."
        if shell_interference > 1e-7
        else " Candidate body/closure has no current released-shell B-rep intersection, but device dock, retention and service closure remain unresolved."
    )
    states = {
        REQ_BODY_CAVITY_WALLS: (
            "Cell 11 now realizes a source-bound body, separate closure and installed free-cavity B-rep inside the authority package. "
            f"{CANDIDATE_PROTECTED_FACE_STATUS}. Wall seeds remain provisional and the candidate is not development-assembly material.{shell_state}"
        ),
        REQ_GEOMETRIC_CAPACITY: (
            f"Cell 11 protected-face-compliant geometric installed free cavity is {candidate.installed_geometric_free_capacity_mL:.6f} mL against the 35 mL retained-capacity requirement. "
            f"{CANDIDATE_CAPACITY_STATUS}; the digital geometry is short of the requirement and usable/retained liquid behavior remains unverified."
        ),
        REQ_INLET_SEAL_CLOSURE: (
            f"The released route handoff, body inlet bore, separate closure and seal-land reference are realized. {CANDIDATE_INLET_STATUS}; "
            f"{CANDIDATE_CLOSURE_STATUS}."
        ),
        REQ_KEYING_RETENTION: (
            f"A cartridge-side asymmetric key rib is realized. {CANDIDATE_KEY_STATUS}; the device-side counterpart, positive latch/stop and physical retention evidence remain absent."
        ),
        REQ_SERVICE_PATH: (
            f"A mask-removed inferior service reservation and translation direction are explicit. {CANDIDATE_SERVICE_STATUS}; no exact continuous insertion/removal sweep or wet-interface disconnect sequence is released."
        ),
        REQ_REMOVED_STATE: (
            f"Candidate cavity classification is {CANDIDATE_HYGIENE_CLASSIFICATION}, which is an allowed authority hygiene class. Removed-state inlet closure, vent/media containment and handling geometry remain unresolved; CAD does not establish hygiene or leak-tight disposal."
        ),
        REQ_DFM_TOLERANCE_PROCESS: (
            f"Candidate body/closure geometry exists with provisional construction seeds, but no production-intent parting/draft/tooling closure or min-max fit stack is established. {CANDIDATE_BODY_STATUS}."
        ),
    }
    requirements = tuple(
        replace(requirement, current_state=states[requirement.requirement_id])
        for requirement in audit.requirements
    )
    return replace(audit, requirements=requirements)


def _validate_candidate_against_audit(model: MasckOneModel):
    candidate = build_realized_waste_cartridge(model=model)
    manifest = candidate.manifest()
    if manifest["development_assembly_material_eligible"] is not False:
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate cannot silently enter development assembly material")
    if manifest["physical_validation_eligible"] is not False:
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate cannot become physical validation evidence")
    if manifest["fluid_identity"] != "MIXED_AIR_LIQUID_FOAM_CONTAMINANT":
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate lost exact mixed-waste identity")
    if manifest["hygiene_classification"] != CANDIDATE_HYGIENE_CLASSIFICATION:
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate hygiene classification drifted")
    if manifest["geometric_capacity_requirement_met"] is not False:
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate cannot hide the current geometric capacity deficit")
    protected = manifest["protected_zone_intersections_mm3"]
    if type(protected) is not dict or len(protected) != 5 or any(float(value) > 1e-7 for value in protected.values()):
        raise WasteCartridgeDfmError("Cell 11 cartridge candidate must clear all five protected-face hard envelopes")
    return candidate


def build_waste_cartridge_dfm_audit(*, model: MasckOneModel | None = None):
    """Run the preserved PR #95 audit plus the explicit Cell 11 realization rebind."""
    model = model or build_model()
    candidate = _validate_candidate_against_audit(model)
    audit = _legacy.build_waste_cartridge_dfm_audit(model=model)
    audit = _candidate_aware_requirements(audit, candidate)
    audit.validate_current_sources(model=model)
    return audit
