# Phase 2 — Iteration 11A: CAD thickness verification hardening

## Reason for inserted iteration

Iteration 11 passed its exact-head engineering CI and was merged. During the failure/fix cycle, the OpenCascade bounding box for the 0.30 mm nasal-lobe development reference reported a Z span approximately **0.0000014 mm (1.4 nm)** larger than the authored extrusion. The design parameter itself had not changed; the difference came from B-rep bounding-box tolerance bookkeeping.

The first corrective pass allowed a controlled **0.000002 mm (2 nm)** B-rep diagnostic budget. That was sufficient to make the regression numerically correct, but it still left the bounding box as the primary geometric thickness measurement.

Iteration 11A improves the verification architecture rather than merely accepting the looser comparison.

## Engineering correction

`Component.horizontal_planar_face_span_z_mm()` now measures the separation of horizontal planar support faces for constant-thickness planar development solids. This is the primary authored-geometry check for the local nasal-lobe reference.

`Component.brep_bounding_span_z_mm()` remains available as a separate OpenCascade kernel diagnostic. Its numerical budget is explicitly not a product, manufacturing, drawing or process tolerance.

The two checks are intentionally separate:

- authored planar-face separation error budget: `1e-10 mm` numerical implementation check;
- B-rep bounding-span error budget: `2e-6 mm` kernel diagnostic check.

Neither value is a physical manufacturing tolerance.

## Regression coverage

The model tests, nasal preflight and main engineering assertions now require both:

1. the support-plane separation to preserve the authority-backed 0.30 mm local lobe thickness within the tight software geometry budget; and
2. the OpenCascade bounding span to remain within its separate numerical diagnostic budget.

A dedicated test prevents future code from accidentally treating the bounding-box inflation as the authoritative membrane thickness.

## Evidence boundary

This iteration does not promote the 0.30 mm value to a validated production thickness and does not close material, strain, pressure, durability, fit, airflow or cleansing-efficacy gates. It only hardens deterministic CAD verification of the already-authorized development parameter.
