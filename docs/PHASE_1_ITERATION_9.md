# Phase 1 / Iteration 9 — facial-region segmentation and coverage-analysis mesh

## Completed engineering scope

Iteration 9 establishes the deterministic surface partition and metrics that later cleansing mechanisms and physical evidence will use.

The implementation adds:

- triangle-level facial surface segmentation;
- stable active/protected/T-zone region identifiers;
- conservative protected-zone triangle exclusion;
- a development T-zone boundary derived from existing authority geometry rather than new anatomical claims;
- explicit nose-to-upper-lip/philtrum target continuity;
- full 3D triangle-area accounting;
- area-conservation assertions;
- area-weighted aggregate and T-zone coverage metrics;
- edge-connected largest-uncovered-hole calculation;
- direct consumption of the authority's 90% aggregate, 90% T-zone and 100 mm² unexplained-hole thresholds;
- deterministic segmentation and evaluation hashes;
- evidence-aware numeric result states;
- rejection of protected/unknown triangle IDs as cleansing targets;
- model, assertion, preflight and public API integration;
- adversarial/unit tests;
- engineering documentation and merge acceptance criteria.

## Explicit evidence boundary

The exact biological T-zone boundary is not frozen by the current authority, so the Iteration-9 T-zone is labelled as a CAD-closure development baseline. The current facial surface is also synthetic and non-anatomical. Consequently, even a 100% geometric screen cannot close the `CLEANSING_COVERAGE` product requirement.

That requirement remains validation-gated until actual cleansing-mechanism coverage and physical spatial-efficacy evidence are mapped onto appropriate registered anatomy.
