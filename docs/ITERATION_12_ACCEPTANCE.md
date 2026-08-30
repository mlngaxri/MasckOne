# Phase 2 Iteration 12 acceptance contract

Iteration 12 is accepted only when all digitally verifiable conditions below pass on the exact pull-request head.

## Required digital conditions

1. The boundary topology is bound to the exact current facial-surface, coverage and compliant-interface hashes.
2. The controlled boundary set contains the outer perimeter, both eyes, mouth and both nostrils.
3. Every controlled boundary is exactly one closed edge loop on the current development mesh.
4. Every protected-aperture edge separates one contact triangle from one matching protected-region triangle.
5. No mesh edge belongs to more than one controlled boundary.
6. No protected region reaches the outer development perimeter unexpectedly.
7. No numeric transition width or general interface thickness is introduced without authority.
8. The 3.0 mm eye inner-edge roll is preserved only as a rigid-edge design reference, not a compliant-profile parameter.
9. Neutral left/right eye and nostril boundary discretizations remain sagittally balanced.
10. The topology is deterministic and SHA-256 identified.
11. The topology remains ineligible for anatomical, seal, ingress, pressure or efficacy validation.
12. Existing authority, core preflight, Iteration-11 nasal preflight, unit/integration tests and deterministic CAD smoke build continue to pass.

## Explicitly unresolved after Iteration 12

The following are not acceptance failures because the current authority/evidence cannot close them yet:

- compliant perimeter width and profile;
- aperture-edge compliant width and profile;
- non-nasal-lobe membrane thickness;
- interface material and constitutive behavior;
- compression/preload;
- seal effectiveness and leakage;
- 3D anatomical conformity;
- facial pressure and membrane strain;
- dynamic eye, mouth and airway safety;
- cleansing efficacy.

These remain controlled downstream gates and must not be represented as passed by the Iteration-12 topology.
