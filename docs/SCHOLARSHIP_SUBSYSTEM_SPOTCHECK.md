# Scholarship subsystem spot-check

[Scholarship review snapshot](SCHOLARSHIP_REVIEW_SNAPSHOT.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Project overview](../README.md)

Masck One is pre-commercialisation. Engineering geometry exists and digital checks/frameworks exist, but product-level physical validation has not begun. This page is a compact source spot-check for reviewers, not a subsystem-readiness claim.

| Subsystem area | Representative repository evidence | What a reviewer can verify | Evidence class and boundary |
| --- | --- | --- | --- |
| Face-side geometry | [Parametric model](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | Geometry is generated from inspectable source and checked digitally. | Existing digital engineering evidence only. Does not prove human fit, comfort, sealing, safety or physical performance. |
| Structure and integration | [Structural frame](../src/masck_one/structural_frame.py) | Named structural/integration geometry and subsystem reservations exist in source. | Existing digital engineering evidence only. Does not prove structural strength, manufacturability or production feasibility. |
| Actuation | [Actuator frames](../src/masck_one/actuator_frames.py) and [checks](../tests/test_actuator_frames.py) | Controlled actuation-zone geometry and digital consistency checks exist. | Existing digital engineering evidence only. Does not prove force, lifetime, acoustics, comfort or motion quality. |
| Waste handling | [Mixed-waste backbone](../src/masck_one/realized_waste_backbone.py) | A source-bound digital routing architecture exists and retains validation-gated states. | Existing digital engineering evidence only. Does not prove recovery, leakage, hygiene, cleaning or hydraulic performance. |
| Requirements and evidence controls | [Engineering authority](../config/masck_one_authority.yaml), [authority contract tests](../tests/test_authority_contract.py) and [boundary-release tests](../tests/test_boundary_release.py) | Requirements, duplicated constraints, provenance and digital-only evidence boundaries are machine-checked. | Existing automated digital evidence only. A passing software check is not achieved physical performance or product validation. |
| Documented design decisions | [Whole-product convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem contradictions are classified, assigned and retained with explicit validation gates instead of being hidden by a concept render or code volume. | Existing digital decision evidence only. A recorded trade-off or selected direction is not proof that the resulting architecture works physically or commercially. |

## Current CI boundary

The scholarship-review branch is not presented as a green engineering release. At the prior reviewed head `536373de`, [engineering CI run 34984795371](https://github.com/mlngaxri/MasckOne/actions/runs/34984795371) failed: repository integrity ratchets passed but pinned-commit provenance failed; the engineering job passed source binding, installation, compilation, authority/brand validation and Iterations 11 through 16 preflights, then failed the unit/integration suite. Deterministic CAD smoke and later release checks were therefore skipped. This status is branch evidence, not a physical-performance result, and it must not be generalized to a later head without a new exact-head run.

The purpose of this spot-check is traceability, not completeness or a readiness score. Major subsystem statements lead to concrete source/check evidence, while planned fit, fluid, cleaning and manufacturing work remains planned validation until measurements exist.

Customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance are physical/commercial evidence not yet obtained. None may be inferred from subsystem coverage, framework readiness, synthetic tests, geometry screens or CI status.
