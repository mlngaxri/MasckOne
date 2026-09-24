# Waste cartridge owner consolidation, 2026-09-09

## Selected owner and source boundary

This branch reconciles the existing Cell 11 cartridge lineage onto released main
`42fa11818184cde998c6df25d7c46d4fb0e4c3eb`. The lineage parents are PR #115 head
`96397f9e1142224979bfc43717ccf325d07fc21f` and blind-service checkpoint
`e8541d0c99fe3106802df644a795fc07db7e7864`.

The current main blobs consumed by the cartridge geometry remain byte-identical to
the source-bound Cell 11 candidate: authority, schema, model, protected volumes,
waste acquisition, waste-cartridge contract, waste-pump architecture, realized
waste backbone and its release wrapper. The cartridge continues to preserve
acquisition -> waste pump -> passive backflow -> cartridge. No bypass is introduced.

## Architecture decision

Selected: `SUPPORTED_FORMED_LINER_SHALLOW_REINFORCED_CLOSURE`.

Superseded as a selected design: the historical 1.2 mm thick tray/deep-plug
topology. Its 27.4016290784 mL geometric cavity remains historical evidence only
and is not a production or retained-capacity result.

The supported-liner candidate keeps the blind lateral key, shallow closure,
reinforced inlet socket, vent/media reservation, dry retention islands and
bilateral sliding-bolt geometry from the strongest checkpoint. The nominal
connected free-space construction remains subject to an exact-head rebuild gate
and must stay at or above the authority 35 mL geometric threshold.

Geometric cavity volume is not retained-liquid capacity. Retained capacity,
leakage, recovery, foam behavior, hygiene, durability, bond process, film process,
tolerance capability and physical service behavior remain unmeasured or validation
gated.

## Current-main service rebind

The blind-service checkpoint used a realized Cell 6 frame candidate from PR #117.
That frame B-rep is not released on current main and is not reused as current
geometry. Current main `src/masck_one/structural_frame.py` is still a topology and
datum contract with no released cross-section or material B-rep.

The oblique `(0,+30,-45) mm` translation proof is retained only for obstacles that
can be rebound to current main: released shell, nasal geometry, actuator packages,
water package and battery package. Its conservative convex swept references remain
separate from manufactured material. Installed extraction and blind insertion stay
blocked until a released frame B-rep and the cartridge/device interfaces can be
checked continuously.

## Fusion handoff

The cartridge handoff exports one STEP per named candidate material component,
separate reference STEP bodies, explicit world/local frames, service datums,
intended fixed/prismatic joints and a deterministic JSON manifest with STEP
round-trip evidence and file hashes.

Candidate material: body, closure, left/right bolts, left/right guides and blind
key tongue.

Reference only: geometric cavity, seal land, vent reservation, key channel,
retention pockets, dry-retention reservation, inlet handoff, service enclosures and
service sweeps.

Nothing in the Fusion handoff changes canonical whole-product development-assembly
membership. Production release remains blocked.
