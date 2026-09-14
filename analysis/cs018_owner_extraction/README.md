# CS-018 exact owner extraction checkpoint

The canonical extractor now reads thermal, exterior and fluid owners. It verifies
the requested full commit against the checkout before and after execution, rejects
tracked changes, and verifies every loaded owner module against its committed
regular Git blob. Merely hashing altered worktree bytes is no longer a source
attestation. Existing output directories are preserved rather than mixed with a
new source run.

| Owner | Exact-source readout | Still unresolved |
| --- | --- | --- |
| Thermal #143 | 14 material candidates and 12 separately classified references, all valid B-reps | Installed facial transform, registered action footprints and physical behavior |
| Exterior #70 | One valid candidate shell B-rep | Registered contact/occlusion cells and whole-product fit |
| Fluid #104 | Bound route graph and 25 loaded source modules | Manufactured contact/seal B-reps and affected-cell footprints |

`owner_geometry_STEP.zip` preserves the actual STEP files and extraction manifests
from these runs. Thermal and exterior files retain owner coordinates without a
new transform. The fluid folder contains a graph manifest only. No reference is
promoted to manufactured material. These are digital review candidates, not a
selected whole-product assembly or instructions for human use.

The adjacent JSON reports bind owner head, tree, loaded module paths, blob IDs,
SHA-256, extractor SHA-256 and runtime. `validation.json` records 16 focused
source-boundary tests and three actual producer checks, all passing. The local
runtime is Python 3.12.14/CadQuery 2.7.0; qualified current-head CI is separate.
The preceding compiler checkpoint's complete green CI is preserved in
`../cs018_capabilities/ci_d79bb03.json`.

To reproduce in an isolated clean checkout of the owner commit named in its JSON,
with that owner's dependencies installed:

```sh
PYTHONPATH=/absolute/owner-checkout/src python tools/cs018_owner_extract.py \
  thermal /absolute/owner-checkout /absolute/new-output-directory FULL_OWNER_COMMIT
```

Use `exterior` or `fluid` for the other adapters. Exit 0 means geometry extraction
ran, not integration approval. The fluid graph deliberately exits 2 while contact
geometry is unresolved. Unsupported owners, failed producers and source failures
also exit 2 with explicit machine-readable status. Every extraction retains
`capability_status: UNRESOLVED_OWNER_CAPABILITY`, `physical_result: null` and
`human_use_eligible: false`.

The frame owner moved after the previous compiler snapshot. The new
`observed_heads.json` and `frame_movement_binding.json` preserve the resulting
`STALE_PRODUCER_HEAD` refusal. The historical snapshot has not been silently
relabelled current.

Next critical work is to register these owner instances to the shared cell domain,
derive actual phase/channel and incidental footprints, reconcile the moved frame
with treatment and retention, and complete the source-bound contact/release matrix.
Measured off-face transfer/recovery/film evidence and whole-session mass, fluid,
energy and time inputs remain separate open proof gates.
