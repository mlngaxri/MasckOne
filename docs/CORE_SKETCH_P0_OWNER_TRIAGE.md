# MASCK ONE P0 Owner-Lane Triage

Status: **dated integration triage; not subsystem engineering authority**  
Observed released main: `eb8ba26c57222320210fa7eb15f4d69e1563cf64`  
Purpose: preserve one owner truth per subsystem while the Core Sketch expands to the complete-routine architecture.

This file records what the whole-product conductor should ask each canonical owner to do next. It does not take over those branches. Exact heads and CI states become stale as soon as an owner moves; reconstruct live GitHub before acting.

**Provenance notation:** unmerged owner heads below are intentionally shown as abbreviated navigation SHAs rather than immutable 40-character commit pins. Repository integrity policy reserves full commit pins for commits that are ancestors of the tested release lineage. Resolve each live PR/branch before using its current exact head.

## 1. Triage rule

Use four distinct states and do not collapse them:

- **GREEN RECEIPT**: exact observed owner head has a successful PR-triggered engineering CI receipt. This is digital evidence only.
- **RED RECEIPT**: exact observed owner head has a failed CI receipt with a concrete failing gate.
- **CANCELLED RECEIPT**: CI did not finish and therefore is neither pass nor geometry failure evidence.
- **NO EXACT-HEAD RECEIPT FOUND**: current owner head exists, but the checked PR-triggered workflow query returned no run for that exact SHA. This is not a pass and not a failure.

Physical validation remains separate in all four states.

## 2. Live owner table

| Area | Canonical PR / observed head | Exact-head CI state observed | Concrete next action | Core Sketch relationship |
| --- | --- | --- | --- | --- |
| Treatment / massage interface | PR #135 `b3a224770f72` | **NO EXACT-HEAD RECEIPT FOUND** | Keep current owner. Preserve prior strict B-rep/service/protected-region failures as unresolved until this exact head produces a receipt. Add source-bound face-contact/shadow outputs for CS-018 rather than redesigning treatment in the conductor. | Lane 1 implementation input; Lane 5 consumes treatment state. |
| Waste cartridge / service | PR #140 `7052bb79dfe7` | **RED RECEIPT**, run `34469594921` | Repair the Cell 5 DFM/source-binding seam for the newly present `src/masck_one/realized_waste_cartridge.py`; do not redesign the selected supported-liner/service architecture merely because the audit detected a new realization source. Then rerun exact-head chain. | Lane 2 subordinate package. Also supplies waste/service variables to whole-routine resource envelope. |
| Retention / quick release | PR #141 `13dff9efb2be` | **NO EXACT-HEAD RECEIPT FOUND** | Keep canonical retention lineage. Obtain exact-head CI. Separately extend acceptance to normal non-wiping release/support-transfer requirements without weakening emergency/unpowered release. | Lane 3 subordinate package; must consume Lane 1 film-survival evidence. |
| Dry-side package / harness | PR #142 `6ee47ecba639` | **RED RECEIPT**, run `34447995905` | Repair the hostile validation ordering/message contract in `test_hostile_route_escaping_dry_bay_is_rejected` without weakening dry-bay containment or route/support requirements. The escaped route is rejected, but currently for `harness support reservation must engage the route envelope` before the expected `escapes current dry-bay` predicate. Rerun full chain afterward. | Lane 3/5 packaging input and energy/interconnect contributor. |
| WARM / COOL thermal package | PR #143 `d2b82e50d5bf` | **GREEN RECEIPT**, run `34425183989` | Reuse exact-head digital evidence while unchanged. Do not promote containment, contact resistance, condensation, reset, comfort or thermal safety without physical evidence. Supply exact contact footprints/states to CS-018 and resource/energy/reset inputs to Lane 5. | Lane 5 treatment package; face-contact implications consumed by Lane 1. |
| Primary HMI | PR #144 `9fb64aa4753d` | **GREEN RECEIPT**, run `34448194076` | Preserve mechanism geometry/evidence on unchanged head. Promotion still requires bounded reconciliation to current released main/source identities where PR provenance is stale; physical force, friction, wobble, sealing, acoustics, lifetime and subjective feel remain open. | Lane 3 subordinate package. Do not let HMI work block P0 facial-delivery proof unless it affects safe routine start/release. |
| Structural frame / reaction loop | PR #117 `fe8e73a20026` | **CANCELLED RECEIPT**, run `34411088277` | Rerun unchanged exact head unless a concrete new source/main invalidation requires rebind. A cancelled full-test job is not a digital geometry failure. Supply current face/support interfaces and mass locations when requested by CS-018/resource work. | Lane 5 integration dependency; upstream for treatment/retention. |

## 3. Exact red-receipt interpretation

### 3.1 Cartridge PR #140

Observed CI passes checkout, tested-source provenance, compile, authority/brand validation and preflights before unit/integration failure.

The concrete failure is a DFM audit/source-ownership gate:

`WasteCartridgeDfmError: new waste-cartridge realization source appeared at src/masck_one/realized_waste_cartridge.py; rebind the Cell 5 DFM audit`

This is valuable fail-closed behavior. It says a new realization source appeared outside the audit's accepted binding. It does **not** prove the physical supported-liner cartridge, shuttle, bolts or wet nose are geometrically or physically bad.

Owner action: rebind/audit the new source in the existing Cell 11/Cell 5 authority seam, preserve material/reference semantics, then rerun exact-head CI.

### 3.2 Dry-side PR #142

Observed CI passes checkout, tested-source provenance, compile, authority/brand validation and all Iteration 11–16 preflights. Full pytest reaches:

`842 passed, 1 failed, 4 subtests passed`.

The failing hostile test translates the route envelope +20 mm in X and expects the validation to reject it specifically because it escapes the current dry-bay package. Validation does reject the hostile object, but the first raised invariant is instead:

`harness support reservation must engage the route envelope`

Therefore the red receipt currently demonstrates **predicate ordering / hostile-test contract mismatch**, not that an escaped route was accepted.

Owner action: make the intended containment invariant independently testable/ordered so the hostile case proves dry-bay escape rejection while retaining the support-engagement invariant. Do not weaken either check or simply loosen the regex to hide which gate fired.

## 4. No-receipt interpretation

Treatment and retention current heads were found live, but no PR-triggered workflow receipt was returned for those exact SHAs during this triage.

Do not write:

- "CI failed";
- "CI passed";
- "geometry is bad";
- "geometry is good".

Use prior receipts only as evidence for the exact older heads they tested. If the current head changed source/geometry, it needs its own evidence.

## 5. Core Sketch P0 ownership requests

### Lane 1: Complete-Routine Facial Delivery

Request from existing owners rather than duplicating them:

- treatment exact face-facing shadow footprints and phase states;
- thermal exact face-contact footprint/state when WARM/COOL participates;
- retention/facial-support contacts that remain during leave-on and release;
- water/cleanser face-side geometry that can trap or carry residue.

Lane 1 then owns the canonical CS-015/CS-018 required-region/contact map.

### Lane 2: Dock / Product Handling

Preserve PR #140 as the cartridge/service owner. The new complete-routine dock layer must not create a second waste-cartridge architecture.

Lane 2 additionally owns product-preservation/changeover implementation under CS-017 and supplies:

- bulk-slot model;
- session-dose packaging overhead;
- dead volume;
- purge/changeover waste;
- preparation/service timing.

### Lane 3: Wearable / Human Factors

Preserve PR #141 retention and PR #144 HMI lineages. Expand acceptance rather than forking:

- release must be both safe and film-preserving in normal operation;
- emergency release remains safety-first;
- HMI must eventually pass physical feel/usability validation;
- full-routine added hardware must close current mass/CG/torque constraints.

### Lane 4: Routine OS / Product Intelligence

This remains genuinely new top-level work. Its immediate P0 task is to implement/test CS-016 prepared-session validity and the product-evidence semantics without pretending cloud/AI availability is required for normal use.

### Lane 5: Whole-Product Conductor

Do not spend this lane repairing every local red test. Its immediate job is to maintain:

- the complete-routine resource ledger;
- shared-interface ownership;
- P0 proof order;
- source/authority reconciliation;
- exact distinction between digital, bench, human, regulatory and supplier evidence.

## 6. Immediate dependency order after this triage

1. Execute the reduced-region proof methods/rig plan for CLEAN -> RINSE/RECOVER -> thin leave-on -> thicker leave-on -> final leave-on -> SETTLE -> non-wiping release.
2. Source-bind the CS-018 all-contact/occlusion matrix to actual treatment, thermal, seal/fluid and retention contact footprints.
3. Populate S0/S1/S2 whole-routine resource ledger with real owner inputs; unknown leave-on/SPF quantities remain unknown until evidence exists.
4. Close representative product-family, preservation and carryover measurement methods under CS-014/CS-017.
5. Implement CS-016 prepared-session validity/offline logic as a versioned software/data contract.
6. Let canonical owners repair their bounded red/no-receipt states in parallel; do not wait for optional polish to begin P0 physical proof.
7. Expand to whole-face region coverage only after reduced-region behavior is credible.
8. Keep facial SPF separate until ordinary leave-on deposition and release preservation are credible, then run its dedicated regulatory/application proof.

## 7. Promotion rule

No owner lane becomes product-complete merely because its local CI is green. Conversely, a local provenance/hostile-test red receipt does not automatically invalidate the product architecture.

Final Core Sketch integration remains blocked until the P0 complete-routine proof gates are closed at their required evidence classes and all current release/source identities are reconciled.
