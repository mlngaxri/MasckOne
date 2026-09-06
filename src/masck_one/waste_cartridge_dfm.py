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
import math

from . import waste_cartridge_dfm_legacy as _legacy
from .waste_cartridge_dfm_legacy import *  # noqa: F401,F403
from .model import MasckOneModel, build_model
from .realized_waste_cartridge import (
    BODY_STATUS as CANDIDATE_BODY_STATUS,
    BODY_WALL_SEED_MM,
    CAPACITY_STATUS as CANDIDATE_CAPACITY_STATUS,
    CLOSURE_STATUS as CANDIDATE_CLOSURE_STATUS,
    HYGIENE_CLASSIFICATION as CANDIDATE_HYGIENE_CLASSIFICATION,
    INLET_STATUS as CANDIDATE_INLET_STATUS,
    KEY_STATUS as CANDIDATE_KEY_STATUS,
    PACKAGE_CENTER_WORLD_MM,
    PACKAGE_ENVELOPE_XYZ_MM,
    PROTECTED_FACE_STATUS as CANDIDATE_PROTECTED_FACE_STATUS,
    RETAINED_CAPACITY_REQUIREMENT_ML,
    SERVICE_STATUS as CANDIDATE_SERVICE_STATUS,
    _box,
    _protected_prism,
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


def capacity_feasibility_metrics(*, model: MasckOneModel | None = None) -> dict[str, float | str | bool]:
    """Return deterministic geometric capacity ceilings without promoting fluid performance.

    The first ceiling uses the complete authority package minus only the exact protected-mouth
    prism. The second is deliberately generous to the current 1.2 mm construction seed: it
    applies that seed only to the four in-plane package walls and protected-mouth boundary,
    while granting the cavity the full 20 mm package Z height with zero floor, lid, closure,
    key, vent or coupling material. If even that second ceiling misses 35 mL, the current
    wall seed cannot meet the geometric requirement without an architecture change.
    """
    model = model or build_model()
    package = _box(PACKAGE_ENVELOPE_XYZ_MM, PACKAGE_CENTER_WORLD_MM)
    mouth_zone = model.protected_volumes.mouth.zone
    mouth_exact = _protected_prism(mouth_zone)

    package_volume_mL = float(package.val().Volume()) / 1000.0
    protected_excluded_mL = float(package.val().intersect(mouth_exact.val()).Volume()) / 1000.0
    protected_compliant_upper_mL = package_volume_mL - protected_excluded_mL

    wall = float(BODY_WALL_SEED_MM)
    zero_floor_lid_inner = _box(
        (
            PACKAGE_ENVELOPE_XYZ_MM[0] - 2.0 * wall,
            PACKAGE_ENVELOPE_XYZ_MM[1] - 2.0 * wall,
            PACKAGE_ENVELOPE_XYZ_MM[2],
        ),
        PACKAGE_CENTER_WORLD_MM,
    )
    mouth_wall = _protected_prism(mouth_zone, radial_offset_mm=wall)
    wall_seed_zero_floor_lid_upper_mL = (
        float(zero_floor_lid_inner.val().cut(mouth_wall.val()).Volume()) / 1000.0
    )
    retained = float(RETAINED_CAPACITY_REQUIREMENT_ML)
    protected_margin_mL = protected_compliant_upper_mL - retained
    wall_seed_margin_mL = wall_seed_zero_floor_lid_upper_mL - retained

    numeric = {
        "package_external_volume_mL": package_volume_mL,
        "protected_mouth_excluded_package_volume_mL": protected_excluded_mL,
        "protected_compliant_package_geometric_upper_bound_mL": protected_compliant_upper_mL,
        "protected_compliant_package_margin_to_retained_requirement_mL": protected_margin_mL,
        "current_wall_seed_zero_floor_lid_geometric_upper_bound_mL": wall_seed_zero_floor_lid_upper_mL,
        "current_wall_seed_zero_floor_lid_margin_to_retained_requirement_mL": wall_seed_margin_mL,
    }
    if any(not math.isfinite(value) for value in numeric.values()):
        raise WasteCartridgeDfmError("capacity feasibility metrics must remain finite")
    if package_volume_mL <= 0.0 or protected_excluded_mL < 0.0:
        raise WasteCartridgeDfmError("capacity feasibility package accounting is invalid")
    if not 0.0 <= protected_compliant_upper_mL <= package_volume_mL:
        raise WasteCartridgeDfmError("protected-compliant package capacity ceiling is invalid")
    if not 0.0 <= wall_seed_zero_floor_lid_upper_mL <= protected_compliant_upper_mL:
        raise WasteCartridgeDfmError("wall-seed capacity ceiling is invalid")

    return {
        **numeric,
        "retained_capacity_requirement_mL": retained,
        "package_geometry_can_theoretically_fit_requirement": protected_margin_mL >= 0.0,
        "current_wall_seed_can_fit_requirement_even_with_zero_floor_lid": wall_seed_margin_mL >= 0.0,
        "evidence_status": (
            "DETERMINISTIC_GEOMETRIC_UPPER_BOUNDS_ONLY_NOT_USABLE_RETAINED_LIQUID_OR_PHYSICAL_PERFORMANCE"
        ),
    }


def _candidate_aware_requirements(audit, candidate, capacity_metrics):
    shell_interference = float(candidate.current_released_shell_interference_mm3)
    shell_state = (
        f" Candidate body/closure intersects current released shell by {shell_interference:.6f} mm3; "
        "candidate therefore remains standalone review geometry."
        if shell_interference > 1e-7
        else " Candidate body/closure has no current released-shell B-rep intersection, but device dock, retention and service closure remain unresolved."
    )
    protected_upper = float(capacity_metrics["protected_compliant_package_geometric_upper_bound_mL"])
    wall_upper = float(capacity_metrics["current_wall_seed_zero_floor_lid_geometric_upper_bound_mL"])
    states = {
        REQ_BODY_CAVITY_WALLS: (
            "Cell 11 now realizes a source-bound body, separate closure and installed free-cavity B-rep inside the authority package. "
            f"All five protected-face hard envelopes are clear: {CANDIDATE_PROTECTED_FACE_STATUS}. "
            f"Wall seeds remain provisional and the candidate is not development-assembly material.{shell_state}"
        ),
        REQ_GEOMETRIC_CAPACITY: (
            f"Cell 11 protected-face-compliant geometric installed free cavity is {candidate.installed_geometric_free_capacity_mL:.6f} mL against the 35 mL retained-capacity requirement. "
            f"The full package minus only the exact protected-mouth hard envelope has a {protected_upper:.6f} mL geometric ceiling, so package placement alone does not make 35 mL impossible. "
            f"However the current {BODY_WALL_SEED_MM:.1f} mm in-plane/protected-boundary wall seed has only a {wall_upper:.6f} mL deliberately generous zero-floor/lid ceiling, below 35 mL; current wall topology therefore cannot close capacity without architecture change. "
            f"{CANDIDATE_CAPACITY_STATUS}; geometric ceilings are not usable or retained liquid performance."
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
    capacity_metrics = capacity_feasibility_metrics(model=model)
    audit = _legacy.build_waste_cartridge_dfm_audit(model=model)
    audit = _candidate_aware_requirements(audit, candidate, capacity_metrics)
    audit.validate_current_sources(model=model)
    return audit
