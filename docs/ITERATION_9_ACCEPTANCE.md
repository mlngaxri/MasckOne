# Iteration 9 acceptance record

Iteration 9 is mergeable only if the exact pull-request head satisfies all applicable gates below.

1. Authority schema and semantic validation remain PASS.
2. Repository preflight reports Phase 1 / Iteration 9 and `COVERAGE_MESH_CONTRACT = PASS`.
3. Every source facial-surface triangle maps to exactly one coverage cell with a stable contiguous triangle index.
4. Total surface area equals active-target area plus protected area within `1e-8 mm²` numerical tolerance.
5. Active target area is non-zero.
6. T-zone active target area is non-zero.
7. Nose-to-upper-lip/philtrum development target area is non-zero.
8. Protected eye, mouth and nostril/airway cells can never be active target cells.
9. Authority coverage thresholds are consumed exactly: aggregate 90%, T-zone 90%, maximum unexplained hole 100 mm².
10. T-zone development segmentation is explicitly classified as CAD closure, not anatomical validation evidence.
11. The central T-zone stem and forehead crossbar meet without an unexplained Y gap.
12. The development segmentation is bilaterally balanced on the current neutral symmetric mesh within numerical tolerance.
13. Coverage percentages are area-weighted rather than triangle-count weighted.
14. Largest unexplained hole is computed from edge-connected uncovered target components.
15. Unknown or protected triangle IDs are rejected as covered-target inputs.
16. Full synthetic target coverage yields a 100% / 100% / 0 mm² numeric screen but remains `NUMERIC_SCREEN_PASS_NOT_PRODUCT_VALIDATION` on the current surface.
17. Empty synthetic coverage fails the numeric gate and exposes a nonzero uncovered component.
18. Segmentation and evaluation hashes are deterministic.
19. `COVERAGE_MESH_TOPOLOGY` is a software PASS while `CLEANSING_COVERAGE` remains BLOCKED pending mechanism and physical efficacy evidence.
20. All prior authority, coordinate, facial-reference, surface-ingestion, protected-volume and worn-pose tests remain green.
21. Deterministic CAD smoke generation succeeds without an intentional product-geometry change.

An iteration cannot be merged merely because its new unit tests pass; the exact PR head must pass the full repository CI chain.
