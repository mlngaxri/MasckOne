# Iteration 16 acceptance: exterior engineering surface and Class-A reference workflow

## Scope

Iteration 16 adds the controlled comparison workflow between future engineering exterior-surface samples and a future authored/released Class-A reference. It does not author the industrial-design surface itself and does not claim manufacturing, cosmetic, tactile or physical validation.

## Authority consumed

- `manufacturing.a_surface.rms_deviation_max_mm = 0.25`
- `manufacturing.a_surface.max_deviation_mm = 0.75`
- existing `CAD_CLOSURE` status is preserved.

## Implemented contract

- stable sample IDs with exact one-to-one pairing;
- duplicate, empty, mismatched and non-finite sample data rejection;
- deterministic RMS and maximum Euclidean deviation calculation;
- SHA-256, revision and explicit release-status contract for any reference that is allowed to participate in release-level CAD closure;
- numerical pass without a released reference remains blocked;
- numerical failure remains failure even if a reference is released;
- physical-validation eligibility is explicitly false.

## Evidence boundary

This iteration does not establish a Class-A surface, appearance quality, toolability, mold fidelity, texture, gloss, seam perception, manufacturability or physical dimensional capability. A future released reference must be authored, revision-controlled and hashed before the CAD-closure status can become eligible. Manufacturing evidence remains separate.

## Verification

Run:

```bash
python -m masck_one.surface_workflow_preflight
python -m pytest
python -m masck_one.cli --output generated
```

Promotion requires exact-head GitHub CI success.
