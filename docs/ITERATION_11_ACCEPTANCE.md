# Iteration 11 acceptance gate — dedicated nasal subsystem

Iteration 11 is complete only when the exact pull-request head satisfies every applicable item below.

## Upstream integrity

- Engineering authority validates with zero schema/semantic issues.
- Canonical coordinates and datums remain unchanged.
- Facial-reference, neutral-surface, protected-volume, worn-pose, coverage and Iteration-10 compliant-interface tests remain green.
- The nasal subsystem references the exact upstream surface, coverage and interface SHA-256 identities.

## Functional partition

- Every active `T_ZONE_NOSE_PHILTRUM` triangle is assigned exactly once.
- The nasal assignment set equals the corresponding Iteration-10 interface contact set.
- No protected nostril/airway triangle is assigned to a nasal contact role.
- The full central-target area is conserved within tolerance.
- All five controlled roles are populated: bridge/dorsum, left sidewall, right sidewall, lobe and philtrum.
- Left/right sidewall areas remain balanced on the neutral sagittally symmetric development baseline.
- The philtrum role remains present.

## Thickness authority

- `NASAL_LOBE` alone receives the authority-backed 0.30 mm center thickness and 0.25/0.30/0.35 mm DOE.
- Bridge/dorsum, both sidewalls and philtrum carry no invented numeric thickness.
- No downstream code silently aliases the local lobe thickness to the entire central T-zone.

## CAD correction

- The previous broad 0.30 mm trapezoidal saddle is no longer the generated nasal thickness reference.
- The generated component is explicitly named `nasal_lobe_membrane_reference`.
- Its status is `DEVELOPMENT_LOCAL_THICKNESS_REFERENCE`.
- Its nominal Z thickness is exactly 0.30 mm.
- The full conservative nostril protected footprints are removed from the local lobe reference.
- The generated solid remains explicitly non-anatomical and non-production-final.

## Evidence boundary

Iteration 11 must **not** report any of the following as passed based on topology/CAD alone:

- dynamic airway signed distance;
- deformed airway area;
- airflow pressure drop;
- nasal collapse resistance;
- nasal liquid-ingress safety;
- facial pressure;
- membrane strain;
- cleansing efficacy;
- human fit.

These remain real downstream digital/physical evidence gates.

## Verification sequence

The pull-request head must pass, in order:

1. Python compilation.
2. Engineering-authority validation.
3. Existing repository preflight.
4. Iteration-11 nasal subsystem preflight.
5. Complete unit/integration test suite.
6. Deterministic CAD smoke generation.
7. Software-verifiable engineering assertions with zero `FAIL` results.
8. GitHub Actions conclusion `success` on the exact head commit.

A failure is corrected at its cause. Acceptance criteria are not weakened merely to obtain a green build.
