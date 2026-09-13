# CS-018 source-bound cleansing capability intake

Status: digitally verified source and compiler intake logic. Physical validation required.

The pretriaged CS-018 integration task requires actual owner footprints before
the cleansing scheduler's declared topology can represent hardware. The new
`cleansing_capabilities.compile_source_bound_plan` entry point reads committed
owner records and calls the existing scheduler. It accepts no caller Actions.
The scheduler algorithm and its ceilings are unchanged.

## Source boundary

`contracts/cs018_cleansing_sources_v1.json` is a read-only source index, not
engineering authority. It binds 27 source files across released main and the
existing treatment, thermal, retention, frame, exterior and fluid owner lineages.
The fluid source is PR #104. Historical PR #157 snapshots and receipts remain
unchanged.

An independently refreshed `live_heads` inventory must match every pinned owner
commit. A producer move invalidates its intake even when the consumed file bytes
are unchanged. A cached inventory proves freshness only at its observation.
Neither this module nor a caller can declare an old inventory current.

The reader uses full Git commits, regular blobs, literal paths and disabled Git
replacement objects. It verifies blob IDs and SHA-256 against the source index.
It reads committed bytes; edits in a checkout cannot narrow a footprint.

Each producer supplies its own committed
`docs/contracts/cs018_cleansing_capabilities_v1.json`. The contract is:

| Field | Required content |
| --- | --- |
| `schema`, `owner` | `CS018_OWNER_CLEANSING_CAPABILITIES_V1` and the matching owner |
| `status`, `evidence`, `physical_result` | `DIGITAL_REGISTERED`, `DIGITAL`, and explicit `null` |
| `source_files` | Path, Git blob and SHA-256 for every consumed source; includes every source-index binding |
| `domain_id` | The same registered cell domain across all owners and caller regions |
| `actions` | The complete common action catalog, including explicit entries for stationary owners |

Every action row supplies `action_id`, `kind`, `channel_id`, `motion` (`MOVING`
or `STATIONARY`), `role`, `evidence_status` (`DIGITAL_REGISTERED`), nonempty
`evidence_paths`, and explicit `target_cells`, `incidental_cells`,
`affected_cells` and `blocked_cells`. Evidence paths must refer to verified
source files in that producer commit. A producer must establish the cell
registration and complete footprint before publishing this status. A string
label or a committed hash does not itself prove geometry or physical behavior.

Targets and incidental cells must be disjoint, and their union must equal the
recorded affected cells. Unknown lists and nonempty blocked cells block intake.
Exactly one owner is the `ACTUATOR` for each action. Other roles are `SUPPORT`,
`OCCLUDER`, `FLUID_SEAL` or explicitly empty `NO_CONTACT`. Non-actuator burden is
explicitly null. The actuator supplies every `Burden` field and a positive
integer `complexity`; missing values are not filled with zeros.

The bridge unions all owners' affected cells for each action. Every owner must
report on every action, with matching phase and channel. Missing entries never
mean clear. Unmapped, multiply mapped, protected or excluded affected cells
block intake. Qualified policy envelopes and session resource budgets remain
separate requirements of the existing scheduler.

## Current result and reproduction

`analysis/cs018_capabilities/current_source_binding.json` records verified source
blobs for all seven owners. All seven capability artifacts are currently absent,
so every owner has an explicit `UNRESOLVED_OWNER_CAPABILITY` row and no Actions
are emitted. Existing geometry producers are not executed or promoted by this
checkpoint. This is a source-intake checkpoint, not closure of the CS-018 hardware
matrix, continuous support paths, or whole-face access.

After fetching the owner commits, reproduce the recorded source observation:

```sh
python tools/cs018_capability_preflight.py \
  --live-heads analysis/cs018_capabilities/observed_heads.json
```

Expected exit status is 2 with seven unresolved owner rows. For a current decision,
first refresh the separate head inventory from the canonical GitHub branches.
After producer records exist, `--regions` supplies the registered region map.

Hostile tests use synthetic Git repositories. They verify incidental contact,
omitted owners/actions/cells, moved producer heads, exact source mismatches,
uncommitted edits, symlinks, ambiguous JSON, domain mismatch, protected/excluded
contact, missing burdens and deterministic compilation. Synthetic successful
plans retain `human_use_eligible: false` and `physical_result: null`.

The next owner work is to derive registered footprint records from actual
geometry, including dependencies, stationary contacts, occlusion and incidental
effects. Producer CI success, registered geometry, support capacity, cleansing,
deposition, film survival, leakage, fit and comfort remain separate evidence.
