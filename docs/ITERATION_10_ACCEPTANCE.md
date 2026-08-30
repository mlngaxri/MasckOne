# Masck One — Iteration 10 acceptance gate

## Scope

Iteration 10 is complete only when the repository contains a deterministic main compliant-interface topology derived from the existing facial coverage mesh and preserves all current safety/evidence boundaries.

## Mandatory digital acceptance criteria

The exact PR head must satisfy all of the following:

- machine engineering authority loads and validates with zero schema/semantic issues;
- repository preflight returns `PASS` and identifies Phase 2 / Iteration 10;
- every facial coverage triangle is assigned to exactly one interface parameter zone;
- target/contact and protected/non-contact intent agree for every assignment;
- protected eye, mouth and both nostril/airway regions remain explicit no-material openings;
- contact area conserves the Iteration-9 target area within 1e-8 mm²;
- protected-opening area conserves the Iteration-9 protected area within 1e-8 mm²;
- T-zone contact area conserves the Iteration-9 T-zone target area within 1e-8 mm²;
- the current development contact field has exactly one edge-connected component;
- the nose-to-upper-lip/philtrum target remains present and contact-intended;
- the authority-backed nasal-lobe thickness remains 0.30 mm with the 0.25/0.30/0.35 mm DOE;
- that nasal-lobe thickness is **not** assigned numerically across the whole central T-zone before its dedicated subsystem boundary exists;
- interface topology remains explicitly ineligible as anatomical/contact-validation evidence;
- topology SHA-256 identity is deterministic across repeated builds;
- all pre-existing digitally verifiable engineering assertions remain `PASS`;
- evidence-gated facial pressure, membrane strain and cleansing efficacy remain `BLOCKED` rather than being fabricated as passes;
- full unit/integration test suite passes;
- deterministic CAD smoke generation passes on the exact PR head;
- no legacy product naming appears in source-controlled text.

## Adversarial requirements

Tests must fail if a developer attempts to:

- add a numeric DOE thickness to a zone whose nominal thickness is unresolved;
- convert a protected nostril region into a contact target;
- omit the philtrum target;
- produce a non-deterministic topology hash;
- promote the Iteration-10 topology to anatomical validation evidence.

## Physical-evidence boundary

Passing this gate is a **digital topology milestone**, not a fit or cleansing validation milestone. It does not close facial pressure, membrane strain, airflow, dynamic anatomical clearance, cleansing efficacy, durability, hygiene or material qualification.

## Promotion rule

Do not merge Iteration 10 until GitHub CI is green on the exact current PR head. If CI discovers a defect, correct the underlying implementation or an invalid test assumption; do not weaken engineering criteria merely to obtain a green run.
