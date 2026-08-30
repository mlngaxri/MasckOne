# Phase 1 / Iteration 8 — worn-pose and misregistration engine

## Completed engineering scope

Iteration 8 implements the authority-bounded worn-pose transform layer used by later hard-envelope, fit and coverage work.

The implementation adds:

- `WornPoseLimits` sourced from the machine authority;
- `WornPose` with explicit XY translation and extrinsic XYZ rotation semantics;
- radial translation validation rather than independent-axis approximation;
- explicit non-invention of Z translation;
- deterministic 459-state hard-envelope regression generation;
- SHA-256 regression manifests;
- exact identity-pose discovery;
- protected-zone boundary sampling;
- protected-zone transformation and posed bounding diagnostics;
- model integration;
- software assertion integration;
- preflight integration;
- lazy public API exposure;
- adversarial/unit tests;
- engineering documentation and merge acceptance criteria.

## Explicit evidence boundary

The deterministic 459-state screen is not a measured distribution and is not used to claim population fit or safety probability. Dynamic anatomical eye, mouth and airway signed-distance checks remain blocked pending registered evidence-eligible 3D anatomical geometry and appropriate validation.
