"""Cell 11 current-main rebind of the fail-closed waste-cartridge DFM audit.

The legacy Cell 5 audit remains the release-gate implementation. This adapter
source-binds it to the consolidated supported-liner owner and updates only the
reported current states. It does not promote the candidate into the released
whole-product assembly or convert geometric cavity into retained capacity.
"""
from dataclasses import replace

from . import waste_cartridge_dfm_legacy as _legacy
from .waste_cartridge_dfm_legacy import *  # noqa: F401,F403
from .realized_waste_cartridge import build_realized_waste_cartridge

SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
REALIZED_WASTE_CARTRIDGE_BLOB_SHA = "324447c16307cb930358c1cf32a6f1a56d829d8e"
SERVICE_CORRIDOR_BLOB_SHA = "55c2e04d9ae025ac32c9a435673ecd1d0001d802"
LEGACY_AUDIT_BLOB_SHA = "f9788cce30c14600c8a624509153596e46c1e478"

SOURCE_GIT_BLOB_IDENTITIES = (
    *_legacy.SOURCE_GIT_BLOB_IDENTITIES,
    ("src/masck_one/waste_cartridge_dfm_legacy.py", LEGACY_AUDIT_BLOB_SHA),
    ("src/masck_one/realized_waste_cartridge.py", REALIZED_WASTE_CARTRIDGE_BLOB_SHA),
    ("src/masck_one/cartridge_service_corridor.py", SERVICE_CORRIDOR_BLOB_SHA),
)
EXPECTED_ABSENT_REALIZATION_PATHS = tuple(
    path
    for path in _legacy.EXPECTED_ABSENT_REALIZATION_PATHS
    if path != "src/masck_one/realized_waste_cartridge.py"
)

_legacy.SOURCE_MAIN_SHA = SOURCE_MAIN_SHA
_legacy.SOURCE_GIT_BLOB_IDENTITIES = SOURCE_GIT_BLOB_IDENTITIES
_legacy.EXPECTED_ABSENT_REALIZATION_PATHS = EXPECTED_ABSENT_REALIZATION_PATHS


def build_waste_cartridge_dfm_audit(*, model=None):
    resolved_model = model or build_model()
    audit = _legacy.build_waste_cartridge_dfm_audit(model=resolved_model)
    candidate = build_realized_waste_cartridge(model=resolved_model)
    candidate.validate()
    candidate_manifest = candidate.manifest()

    if candidate_manifest["retained_capacity_mL"] is not None:
        raise WasteCartridgeDfmError(
            "candidate geometric cavity cannot become retained capacity in DFM rebind"
        )
    if candidate_manifest["development_assembly_material_eligible"] is not False:
        raise WasteCartridgeDfmError(
            "candidate cartridge cannot bypass development-assembly release ownership"
        )

    states = {
        REQ_BODY_CAVITY_WALLS: (
            "Source-bound supported-liner body and shallow closure are valid connected "
            "candidate B-reps inside the package and clear the released shell/protected "
            "regions. Film forming, joining, tolerance and process capability remain unresolved."
        ),
        REQ_GEOMETRIC_CAPACITY: (
            f"Connected material-exclusive geometric free cavity is "
            f"{candidate.installed_geometric_free_capacity_mL:.9f} mL. Dry retention and "
            "vent/media reservations are excluded. The geometric threshold is met; "
            "retained-liquid capacity remains physical-validation gated."
        ),
        REQ_INLET_SEAL_CLOSURE: (
            "The exact mixed-waste route handoff, reinforced inlet bore, shallow closure and "
            "bond/seal land candidate geometry exist. Wet coupling selection, joining process, "
            "seal capability and leakage remain unresolved."
        ),
        REQ_KEYING_RETENTION: (
            "The asymmetric blind key channel, bilateral dry sockets, bolts and guide candidate "
            "geometry exist. Device-side attachment, capture/access, min-max fits, loads, wear "
            "and physical feel remain unresolved."
        ),
        REQ_SERVICE_PATH: (
            "A source-bound continuous oblique reference sweep is available against current-main "
            "shell/package obstacles, but released main has no structural-frame B-rep and the "
            "key/bolt/wet interfaces are unresolved. No installed extraction or blind-insertion "
            "PASS is issued."
        ),
        REQ_REMOVED_STATE: (
            "Vent/media reservation is deducted from geometric cavity. Removed-state inlet/vent "
            "closure, handling containment, hygiene classification and wet disposal behavior "
            "remain unresolved."
        ),
        REQ_DFM_TOLERANCE_PROCESS: (
            "A one-degree supported formed-liner DOE with shallow closure replaces the impossible "
            "thick tray/deep plug as selected candidate geometry. DOE dimensions are not supplier "
            "capability. Critical seal/retention/device fit stacks and physical process evidence "
            "remain unresolved."
        ),
    }

    rebound = replace(
        audit,
        requirements=tuple(
            replace(requirement, current_state=states[requirement.requirement_id])
            for requirement in audit.requirements
        ),
    )
    rebound.validate_current_sources(model=resolved_model)
    return rebound
