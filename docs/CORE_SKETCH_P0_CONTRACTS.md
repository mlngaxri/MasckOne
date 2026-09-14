# Whole-routine P0 contracts

This is the current Core Sketch contract entry point on the existing PR #148 lineage. It is **non-authoritative concept logic, not device control**. Engineering YAML, protected geometry and accepted physical evidence retain their authority. None of the functions below authorizes hardware. A supplied evidence record is a scoped declaration for checking logical consistency, not a verified signature, a measurement or a certification.

The recovered convergence review remains the reasoning record. This increment makes its five shared obligations executable. Source hashes are generated from actual input bytes; volatile owner-head observations live in the dated source snapshot and never become release provenance.

## One producer per shared contract

| Contract | Writing owner | Key consumers | Current implementation |
|---|---|---|---|
| Completion and coverage | Lane 1 facial delivery | Lanes 3, 4, 5 | `assess_completion` |
| Contact, occlusion and film-preserving transition | Lane 1 facial delivery | Lane 3 geometry and release; Lane 5 treatment | `assess_contacts` |
| Prepared session and readiness | Lane 4 Routine OS | Lane 2 preparation; Lane 3 physical control | `assess_readiness`, `invalidate` |
| Complete-routine resources | Lane 5 conductor | Lanes 1, 2, 4 | `assess_resources`, canonical mass-ledger overlay |
| Preservation, carryover and changeover | Lane 2 dock/product service | Lanes 1, 4, 5 | `assess_integrity` |

The canonical manifest is `docs/contracts/core_sketch_convergence.json`. A contract path includes a JSON fragment, so two lanes are not assigned simultaneous writing authority over one interface. Shared implementation changes stay reviewed through the concept/conductor lineage. Geometry owners keep their existing source ownership. No owner is instructed to copy a competing counterpart or cartridge.

## 1. COMPLETE is a matrix, not a percentage

The conceptual catalog includes forehead, bilateral temple/cheek/jaw, nose skin, upper-lip surround and chin, with separate protected eye, nostril and mouth records. These are coverage bookkeeping regions, **not registered anatomy, clinical boundaries, dimensions or permission to treat near an opening**. Existing protected B-reps always prevail. A future registered catalog must partition the supported facial domain without holes; its version changes the plan digest and invalidates prior context evidence.

Each selected stage has an obligation for every catalog region. A region is REQUIRED, PROTECTED, or EXCLUDED under a qualified product/safety exclusion. Inaccessibility caused by the device is a blocker, never an exclusion. Temple versus cheek or other informal boundaries cannot be adjusted to conceal a support footprint. Unknown subregions fail the cell, even if the parent region reports 100 percent coverage. Ear, neck, body and decorative cosmetics remain outside the stated facial routine; no facial SPF claim replaces other exposed-area protection.

| Stage | What its region cell must establish |
|---|---|
| CLEAN | Removal process reaches the cell; a cycle counter or aggregate result is insufficient. |
| RINSE/RECOVER | Residual cleansing product and free liquid are accounted for locally; recovery flow alone is insufficient. |
| Each LEAVE-ON | That exact product is deposited under its supported application profile in the cell. |
| MOISTURISE | Required film is deposited and survives later stages. |
| FACIAL SPF, when selected | Separate claim-quality evidence covers exact product, method, amount, uniformity and film survival. Ordinary surrogate success cannot supply it. |
| SETTLE | The relevant film meets its supported settling condition locally. No universal wait time is invented. |
| RELEASE | The entire normal removal path preserves the required final layer in the cell. |

The plan digest binds stage order, products, exclusions and spatial obligations. Unsupported required products, missing/unreachable cells, interrupted progress or incomplete release prevent COMPLETE. Emergency disengagement remains available independently and records PARTIAL, never a routine success. An off-face reduced-region record can at most establish reduced-sequence consistency. Whole-face completion additionally requires accepted BENCH and HUMAN registration and region evidence; SPF requires REG_CLAIM evidence. Those records do not exist in this candidate.

## 2. Every contact can be an occluder

The inventory includes skin seals, perimeter contact, support pads, retention reactions, massage islands, thermal surfaces, optical carriers, fluid-distribution surfaces and stationary bridges. Every class is represented through PLACEMENT, CLEAN, RINSE/RECOVER, TREAT, LEAVE-ON, SETTLE and RELEASE. Current unresolved instance IDs, footprints and transitions are deliberately UNKNOWN, not implicitly clear. A claim that a class is absent needs a source-bound digital absence record.

For every instance and affected cell the producer must bind:

1. the contact/occlusion footprint and phase;
2. how it uncovers before application, and which supported stage reaches that footprint;
3. where the device reaction load goes during the handoff;
4. the complete later motion and normal removal path;
5. the measured film-survival evidence for those motions.

Retracting massage islands alone cannot satisfy this. A stationary thermal plate or seal can still block the final film. No global retraction distance or mechanism is selected here. The contract permits sequential contact handoff only when the entire previously covered area is serviced and later structures do not wipe it. Contact-force, fit and human-use proof remain with qualified validation; this code supplies none.

## 3. PREPARED is not READY NOW

`assess_readiness(request, receipt, current, now_s)` recomputes from the exact plan. It binds routine revision, schedule context, ordered stages, hardware/authority/profile identity, required product identities and assignments, the actual dose records, local service history and resource observations. Market or formulation identity cannot be invented: unresolved identity prevents a validated execution profile.

A preparation receipt is scoped to a state epoch and content digests, with preparation, dose and observation expiry. Required local state includes a trustworthy clock, verified cached profiles, known progress and an available controller. A fresh, validated local preparation receipt can support offline use. Internet and external AI are not execution dependencies.

Every listed invalidation event revokes readiness: routine/schedule change, substitution, reformulation, reassignment, disturbed/expired dose, incomplete changeover, interrupted service, changed resources or thermal state, fault, changed profile/hardware, untrusted clock and partial delivery. Clearing a display flag is not re-preparation. Lowering a resource requirement also changes the request digest and cannot reuse the old receipt.

PREPARED_READY describes valid prepared contents and resources. START_READY additionally needs the independently established wearing/eligibility state. A missing required stage or thermal resource blocks both appropriate checks. Normal physical start uses this distinction later, but **these Python screens are not production firmware or a safety interlock**.

## 4. Full-routine resource envelope

Four **unvalidated planning scenarios** exist: minimum PM, normal PM, demanding AM and demanding PM. Respectively they need at least 2, 3, 5 and 4 distinct product slots under the scenario's selected product roles. Water and waste are separate. These counts are not a frozen six-reservoir architecture; exact-product reuse and simultaneous session isolation remain producer decisions.

The overlay reads live authority and `mass_balance.py`. At this revision the mass constraints are dry <=215 g, loaded <255 g, CG Z <=27.9 mm and datum pitch torque <=0.070 N m. The historical 30 mm limit is superseded by released authority. Loaded mass and CG must satisfy the joint torque constraint, not each in isolation. Neck-joint offset and dynamic load remain unresolved.

The inherited cleaning study requires 3.2 mL face water, 0.8 mL flush and 0.6 mL cleanser, plus up to 0.4 mL initial prime. These are validation-gated targets, not newly validated complete-routine quantities. Before any additional purge, the water planning range is 4.0 to 4.4 mL. The cleaning-only recovered target is 4.14 to 4.60 mL, prior waste and new-stage losses additional. The 35 mL retained-capacity requirement is not proof that the cartridge currently retains that volume.

Every leave-on dose and density, product purge, prior waste, deposited loss, session isolation hardware, usable electrical energy, stage duration and selected thermal requirement stays an explicit input. Unknown means an unbounded/unknown interval, not zero. All four scenarios currently fail to close the full resource envelope. The ~25.988 g known lower contribution in these screens is principally the battery benchmark plus water. It is **not** a wearable mass estimate or remaining mass budget: most hardware, cleanser density and all new products are unresolved.

The screen distinguishes free residual water from intended leave-on film. Fluid moved into internal waste is counted once in on-head inventory; adding its recovered mass a second time is forbidden. Prior retained waste is additional. Future measured location histories must cover prepared, active, post-recovery and fault inventory states; nominal prepared CG alone cannot close wearer torque. Storage and water/waste comparisons are demand-versus-target screens, never verified usable capacities.

Required producer outputs before numerical closure: per-stage peak/energy and serial duration or justified overlap; product quantities and densities; actual cassette/isolation mass and locations; per-cheek thermal initial/end/reset states; fluid transfer locations; purge allocation between dock and wearable; waste age/contents; and available battery energy under selected loads. No supplier-qualified dose, battery performance or thermal capacity is fabricated here.

## 5. Product integrity is more than pumpability

Each product has separate exact identity, characterized behavior, material/storage compatibility, contamination state and application validation. A flow fingerprint may reveal a mismatch; it cannot establish chemical identity, preservation or safe compatibility. Community and AI outputs cannot directly promote VALIDATED.

A complete path inventory names reservoir, metering, session isolation, transfer, outlet and service/waste nodes with exact producer binding. Dead volume cannot be omitted. Shared contact nodes need **ordered product-pair** carryover evidence, including cleanser-to-leave-on and changeover directions. Purge success is product/path/age dependent; there is no universal purge volume or allowable carryover in this contract. Mixed waste retains the passive backflow stage. Fresh, cleanser and leave-on identities cannot silently enter an incompatible circuit.

Product changes invalidate the preparation even if a bottle name is unchanged. Dock storage, decanting, air exposure, residue, hold age, batch/reformulation and downstream wetted surfaces require preservation evidence. Supplier information alone does not validate Masck application; successful dispensing alone does not validate preservation. Unsupported products restrict that routine explicitly, never masquerade as COMPLETE.

## Execute the checks

```sh
PYTHONPATH=src python -m pytest -q tests/test_core_sketch_contracts.py
PYTHONPATH=src python -m masck_one.core_sketch_contracts --output generated/core_sketch --trial docs/contracts/reduced_region_trial_template.json
```

A zero exit from the latter means the **contract structure** is consistent and reports were generated. Read `product_completion`, `contacts`, `resources` and `trial`: unresolved source inputs and the blank trial deliberately remain BLOCKED. Passing synthetic test fixtures are not accepted evidence. Generated SHA-256 bindings change when authority or producer inputs change.

The manifest covers every current backlog P0, including conditional and later P0 items. It does not activate all of them at once. Immediate dependency order: region/cohort contract; all-contact support strategy; reduced-region transition/film/carryover proof; prepared-session preservation and validity; joint resources; whole-face registration and normal release. Facial SPF keeps its independent claims gate visible throughout, so it cannot emerge as a late hidden failure of the AM promise.
