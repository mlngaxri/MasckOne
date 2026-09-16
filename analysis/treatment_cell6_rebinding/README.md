# Treatment -> Cell 6 rebinding evidence

Records what was verified when the treatment stack's consumed Cell 6 sources were
checked against the current Cell 6 owner head. `rebinding_evidence.json` is generated
from git and is reproducible from the two heads it names.

## Claimed

Every source the treatment stack consumes from Cell 6 is **identical** at the pinned
geometry-source head `2d5ace19` and at the verified head `a248c814`:

- all six counterfaces in `CONSUMED_COUNTERFACE_BLOB_SHA1`, by whole-file Git blob;
- `_protected_zone_solid`, by canonical symbol source.

The consequence is narrow and useful: rebinding treatment onto the current Cell 6 owner
requires **no geometry re-derivation**, because nothing treatment consumes changed.

## Not claimed

- That the treatment geometry was re-derived against `a248c814`. It was not.
- That `a248c814` is the live owner head for all time. A newer Cell 6 head must be
  re-verified; this record is evidence about two named heads, nothing more.
- Any physical validation. Source provenance is not force, comfort, fatigue, wear,
  acoustic, leakage or supplier evidence.

## Why the protected-zone builder is pinned by symbol, not by file blob

`treatment_mounted_four_zone` imports the private Cell 6 symbol `_protected_zone_solid`
and builds every protected-anatomy zone the station collision screens measure against.
Cell 6 has since split `structural_frame_realization` into a thin source-identity
adapter plus a preserved `_structural_frame_realization_impl`, re-aliasing the module
through `sys.modules`.

So the implementation **moved path while keeping blob `5e626e73`**, and the imported
path now carries a different blob (`d8928fb4`) that contains no geometry at all. A
whole-file pin on the imported path would report drift that did not happen; no pin
would let the zone geometry change silently. The pin therefore follows the symbol:
relocation is accepted, change is refused.

## Hazard this creates for other consumers

Any consumer that pins `src/masck_one/structural_frame_realization.py` by path and blob
is invalidated by that relocation, and the obvious repair is wrong. "Refresh the blob at
the recorded path" resolves to `d8928fb4`, which is the 14-line adapter: the binding
would then cover **no frame geometry whatsoever** while still reading as current. The
correct target is `_structural_frame_realization_impl.py`, blob `5e626e73`, which is the
preserved implementation.
