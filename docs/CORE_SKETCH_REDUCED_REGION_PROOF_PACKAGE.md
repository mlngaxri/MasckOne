# MASCK ONE Reduced-Region Whole-Routine Proof Package

Status: **P0 BENCH validation plan; no physical result is claimed by this document**  
Backlog links: CS-010, CS-012, CS-013, CS-014, CS-121, CS-160, CS-161, CS-163.  
Product contract: `docs/CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md`.

## 1. Purpose

Before whole-face CAD expands around serum, moisturiser, SPF, optical and routine intelligence, Masck One must demonstrate the hardest cross-stage behavior on the smallest representative facial region.

The reduced-region proof must answer one question:

> Can one representative curved skin region be cleaned, rinsed/recovered, receive sequential leave-on products, settle, and disengage without unacceptable contamination, pooling, uncovered occlusion islands or removal of the final layer?

The proof is deliberately smaller than a full-face prototype so failures can be understood without whole-product noise.

Success here does **not** validate whole-face fit, comfort, cleanser efficacy, skin-barrier effects, SPF protection, optical safety, thermal safety or commercial readiness.

## 2. Required sequence

The rig shall be capable of executing this ordered state path:

1. `BASELINE / DRY INSPECTION`
2. `CONTACT / SEAL ESTABLISHED`
3. `CLEAN`
4. `RINSE / RECOVER`
5. `POST-RINSE RESIDUAL CHECK`
6. `APPLICATION-CLEAR TRANSITION`
7. `THIN LEAVE-ON`
8. `INTERMEDIATE SETTLE`
9. `THICKER LEAVE-ON / MOISTURISER`
10. `REPRESENTATIVE FINAL LEAVE-ON`
11. `FINAL SETTLE`
12. `NON-WIPING RELEASE`
13. `POST-RELEASE MAPPING`
14. `CLEANUP / CARRYOVER INSPECTION`

Treatment modalities such as massage/WARM/COOL/optical are optional in this P0 rig. They may be inserted only after the basic clean-to-leave-on transition is understood. Do not let optional treatment obscure the existential proof.

## 3. Test article philosophy

Use a curved, repeatable, inspectable test region representing cheek-class curvature rather than a flat plate alone.

The test surface should support:

- reproducible geometry;
- repeatable initial contamination/application conditions;
- visual mapping of deposited product;
- removable/repeatable surface films or coupons;
- weighing before/after where useful;
- safe substitution of tracer fluids during early engineering work;
- later supervised skin testing only after a separate human-use protocol exists.

Early rig work should use safe bench analogs and representative formulation-property families. Do not use a person as the first instrument for debugging uncontrolled fluid, thermal or optical behavior.

## 4. Representative product-property families

The rig should not be optimized around one favorite skincare bottle. Use a small formulation-family matrix representing the practical envelope.

At minimum characterize:

### Family C1: cleanser, gel-like

Purpose: common viscous cleanser behavior.

Record:
- density;
- apparent viscosity/rheology data where available;
- foaming tendency;
- water miscibility;
- residue behavior;
- interaction with rig materials.

### Family C2: cleanser, cream/emulsion-like

Purpose: harder rinse/recovery case than a simple aqueous gel.

### Family L1: watery essence / low-viscosity serum

Purpose: low-viscosity spreading, runoff and boundary-control challenge.

### Family L2: shear-thinning or moderately viscous serum

Purpose: intermediate transport/spread behavior.

### Family L3: lotion / emulsion

Purpose: leave-on coverage with more structure than a serum.

### Family L4: cream / moisturiser

Purpose: thicker final-film challenge.

### Family F1: representative non-SPF final leave-on

Purpose: exercise the last-film preservation problem without prematurely treating sunscreen as solved.

### SPF family

SPF is **not** promoted from this rig. It receives a separate claims-quality program after ordinary leave-on deposition is credible. TGA guidance requires sunscreen to be used according to its label and warns against spraying aerosol sunscreen directly onto the face. A Masck sunscreen stage therefore cannot be validated by generic tracer coverage or dispensed volume alone.

Exact consumer products can later be added as characterised examples, but the proof matrix should remain property-family driven.

## 5. Instrumentation and evidence capture

Every run should produce a traceable run record containing:

- rig revision;
- surface/coupon revision;
- contact-interface revision;
- product-family IDs and exact products if used;
- product lot/batch where practical for later work;
- initial and final mass measurements when the method supports them;
- commanded dose and independently measured delivered dose where possible;
- recovered waste mass/volume;
- residual liquid mass/volume estimate where possible;
- stage timestamps;
- ambient temperature;
- product temperature;
- photographs before, between critical stages and after release;
- mapped coverage image/region record;
- observed leaks/pooling/stringing/bridging;
- post-run contamination/carryover result;
- explicit PASS/FAIL/INCONCLUSIVE per criterion rather than one overall subjective score.

Do not convert missing measurements to zero.

## 6. Coverage measurement

The rig must expose whether supports or seals leave untreated islands.

For each required region/cell in the reduced-region coverage map, classify the result after each relevant stage:

- `COMPLETE`
- `THIN_OR_DISCONTINUOUS`
- `POOLED`
- `OCCLUDED`
- `WIPED_OR_REMOVED`
- `OUTSIDE_REQUIRED_REGION`
- `UNKNOWN`

A simple average percentage is secondary. Any persistent required-region `OCCLUDED`, `WIPED_OR_REMOVED` or `UNKNOWN` result blocks the clean-to-leave-on proof.

Use tracers or imaging methods suitable to the bench material only where they do not materially change the fluid behavior being studied. If a tracer changes rheology/wetting, record that run as a method-development result rather than product evidence.

## 7. Rinse/recovery and cleanser carryover

The post-rinse state must be measured separately from waste-pump activity.

Required questions:

- How much cleanser remains on the surface after the nominal rinse/recovery stage?
- Where does residue remain?
- Does residue concentrate near seals/supports/edges?
- Does residual cleanser mix visibly or measurably into the first leave-on layer?
- Does additional rinse improve carryover while creating unacceptable residual wetness or time burden?

Select quantitative carryover acceptance metrics only after measurement-method repeatability is demonstrated.

Initial promotion rule:

> No whole-face architecture freeze until the team can distinguish an adequately recovered surface from a contaminated one with a reproducible measurement method.

## 8. Product-to-product carryover

Exercise at least:

- L1 -> L4;
- L2 -> L4;
- L4 -> F1;
- repeated same-product sessions;
- product changeover between dissimilar families.

Inspect both directions of contamination:

1. downstream film contamination on the face-side surface;
2. back-contamination toward stored or prepared product.

The second is particularly important: successful facial deposition must not silently contaminate another reservoir/session dose.

## 9. Occlusion and contact-state experiment

The rig should contain representative contact elements that deliberately create realistic occlusion islands.

Run at least these concept cases:

### Case A: contact never clears

Purpose: negative control. Demonstrate that a stationary support creates a visible untreated island and therefore cannot satisfy the whole-routine contract without another strategy.

### Case B: contact clears before leave-on

Purpose: test whether the newly exposed area can be coated without disturbing already treated surrounding regions.

### Case C: contact transfers/repositions between stages

Purpose: test whether staged support transfer can preserve stability while eliminating persistent occlusion.

### Case D: secondary application after contact exit

Purpose: test a mechanism-neutral route for filling previously occluded skin after support clears.

The rig is not required to select the final production mechanism. It must identify which functional strategies remain credible.

## 10. Non-wiping release experiment

The last stage is not complete until removal has been tested.

For every final-film run capture:

- coverage map immediately before release;
- release path/state;
- coverage map immediately after release;
- mass transfer to the departing contact/interface where measurable;
- streaking or directional redistribution;
- edge pickup;
- any region touched after its final coating;
- whether release required excessive peeling/dragging.

Define `film_survival_fraction` only after a repeatable measurement method exists. Until then, use mapped before/after evidence and explicit uncertainty.

A release architecture fails the P0 proof if broad required regions are visibly stripped or if the only way to preserve the layer is an impractical user maneuver inconsistent with Grab -> Place -> Start -> Remove -> Done.

## 11. Leakage and protected-boundary analogs

The reduced rig must include no-go boundary channels representing migration toward protected anatomy.

These are analog boundaries, not proof of eye/nose/mouth safety.

Record:

- any liquid crossing the boundary;
- maximum observed migration distance;
- pooling adjacent to the boundary;
- behavior during contact-state transition;
- behavior during removal.

Any uncontrolled repeated migration toward a protected-boundary analog blocks whole-face expansion until the architecture changes.

## 12. Stage-specific failure modes

### CLEAN

Fail if:
- product cannot be distributed over the required region;
- uncontrolled runoff occurs;
- the contact architecture leaves unexplained untouched areas;
- residue is driven into protected-boundary analogs.

### RINSE/RECOVER

Fail if:
- cleanser residue cannot be distinguished from an adequately recovered surface;
- residue creates obvious contamination of the first leave-on;
- recovery creates uncontrolled leakage/pooling;
- acceptable recovery requires an ownership/time burden inconsistent with the product.

### THIN LEAVE-ON

Fail if:
- most dose runs to a local low point;
- coverage cannot reach previously occluded areas;
- protected-boundary control is not credible.

### THICK LEAVE-ON / MOISTURISER

Fail if:
- material bridges/clumps instead of forming a usable film;
- application requires forces/contact that later destroy the film;
- required surface cannot be reached.

### FINAL LEAVE-ON + RELEASE

Fail if:
- release materially strips broad required regions;
- support/seal islands remain untreated;
- final surface condition depends on manual rubbing after removal.

## 13. Minimum repetition plan

Method-development runs are not counted as evidence runs.

Once methods are repeatable, each selected formulation-family sequence should be repeated enough to expose run-to-run variation rather than relying on a single attractive demonstration. The exact sample count must be selected with the eventual measurement variance; do not invent statistical confidence before variance data exists.

At minimum, require repeated successful runs across:

- nominal cheek curvature;
- a more prominent curvature condition;
- a flatter curvature condition;
- nominal contact preload state;
- plausible low/high contact or standoff condition;
- at least one warm and one cooler normal-use ambient/product condition if fluid behavior changes materially.

## 14. Promotion gates

### Gate RR-1: method credible

Pass when coverage, mass/recovery and carryover methods are repeatable enough to distinguish obvious success/failure.

### Gate RR-2: clean-to-first-leave-on transition

Pass when cleanser can be followed by a thin leave-on without obvious uncontrolled residue, pooling or protected-boundary migration.

### Gate RR-3: multi-layer application

Pass when thin + thicker leave-on layers can be applied sequentially over the required map, including previously occluded regions.

### Gate RR-4: final film survives release

Pass when the final mapped layer remains materially present after a realistic hands-off release path and no manual facial finish is required by the rig concept.

### Gate RR-5: representative family robustness

Pass when the same architecture works across selected representative formulation families rather than only one hand-picked product.

Only after RR-1..RR-5 pass should Lane 1 recommend whole-face application architecture expansion.

## 15. What this proof does not close

Even a successful reduced-region campaign does not close:

- whole-face coverage;
- periorbital/nasal/perioral human safety;
- comfort;
- skin barrier preservation;
- clinical efficacy;
- SPF protection;
- thermal treatment safety;
- optical safety/efficacy;
- long-term hygiene;
- product/material compatibility lifetime;
- wearable mass/CG;
- manufacturing capability.

Each remains separately gated.

## 16. Kill/pivot interpretation

One failed rig does not kill Masck One. Failure should identify which functional assumption broke.

Escalate to product review when repeated credible architectures cannot solve one or more of:

- cleanser-to-leave-on contamination;
- previously occluded-region application;
- thin-fluid boundary control;
- thick-product distribution;
- final-film preservation during release;
- practical compatibility across commercially useful formulation families.

If those repeatedly fail together, the issue is no longer a local mechanism problem; it challenges the complete-routine proposition itself.
