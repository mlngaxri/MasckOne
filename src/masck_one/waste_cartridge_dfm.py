"""Cell 11 source rebind; all physical and outstanding DFM gates remain closed."""
from dataclasses import replace
from . import waste_cartridge_dfm_legacy as _legacy
from .waste_cartridge_dfm_legacy import *  # noqa: F401,F403
from .realized_waste_cartridge import build_realized_waste_cartridge

SOURCE_MAIN_SHA='b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc'
REALIZED_WASTE_CARTRIDGE_BLOB_SHA='cac2ed2839a2f0a567b8470adbeb080369a6b963'
LEGACY_AUDIT_BLOB_SHA='f9788cce30c14600c8a624509153596e46c1e478'
SOURCE_GIT_BLOB_IDENTITIES=(
    *_legacy.SOURCE_GIT_BLOB_IDENTITIES,
    ('src/masck_one/waste_cartridge_dfm_legacy.py',LEGACY_AUDIT_BLOB_SHA),
    ('src/masck_one/realized_waste_cartridge.py',REALIZED_WASTE_CARTRIDGE_BLOB_SHA),
)
EXPECTED_ABSENT_REALIZATION_PATHS=tuple(p for p in _legacy.EXPECTED_ABSENT_REALIZATION_PATHS
                                      if p!='src/masck_one/realized_waste_cartridge.py')
_legacy.SOURCE_MAIN_SHA=SOURCE_MAIN_SHA
_legacy.SOURCE_GIT_BLOB_IDENTITIES=SOURCE_GIT_BLOB_IDENTITIES
_legacy.EXPECTED_ABSENT_REALIZATION_PATHS=EXPECTED_ABSENT_REALIZATION_PATHS

def build_waste_cartridge_dfm_audit(*,model=None):
    audit=_legacy.build_waste_cartridge_dfm_audit(model=model)
    candidate=build_realized_waste_cartridge(model=model)
    candidate.validate()
    states={
        REQ_BODY_CAVITY_WALLS:'Valid supported-liner body and shallow closure clear the released shell and five protected prisms. Film/process capability and registered anatomy remain unresolved.',
        REQ_GEOMETRIC_CAPACITY:f'Connected, material-exclusive principal cavity is {candidate.installed_geometric_free_capacity_mL:.9f} mL. Dry bolt sockets and vent/media reservation are excluded. Nominal geometric threshold is met; retained-liquid capacity remains validation-gated.',
        REQ_INLET_SEAL_CLOSURE:'Exact mixed-waste route handoff, reinforced inlet bore and continuous closure bond land exist. Selected wet coupling, liner/collar joining, seal process and leakage remain unresolved.',
        REQ_KEYING_RETENTION:'Asymmetric key channel, dry sockets, bilateral bolts and guide geometry exist. Local axial bolt sweeps are analyzed separately; device-frame attachment, capture/access and loads remain unresolved.',
        REQ_SERVICE_PATH:'Local bolt release does not establish installed-device extraction. Current shell interferes with proposed translational service paths; no product service PASS is issued.',
        REQ_REMOVED_STATE:'Vent/filter reservation is deducted from cavity. Removed-state inlet/vent closure and handling containment remain unresolved.',
        REQ_DFM_TOLERANCE_PROCESS:'A one-degree formed liner DOE replaces uniform thick walls and deep plug. Seeds are not supplier/process capability. Seal/retention min-max fits and physical evidence remain unresolved.',
    }
    return replace(audit,requirements=tuple(replace(r,current_state=states[r.requirement_id]) for r in audit.requirements))
