# Scholarship subsystem spot-check

[Scholarship review snapshot](SCHOLARSHIP_REVIEW_SNAPSHOT.md) · [Evidence guide](EVIDENCE_GUIDE.md) · [Project overview](../README.md)

Masck One is pre-commercialisation. Engineering geometry exists and digital checks/frameworks exist, but product-level physical validation has not begun. This page is a compact source spot-check for reviewers, not a subsystem-readiness claim.

| Subsystem area | Representative repository evidence | What a reviewer can verify | Boundary |
| --- | --- | --- | --- |
| Face-side geometry | [Parametric model](../src/masck_one/model.py) and [model checks](../tests/test_model.py) | Geometry is generated from inspectable source and checked digitally. | Does not prove human fit, comfort, sealing, safety or physical performance. |
| Structure and integration | [Structural frame](../src/masck_one/structural_frame.py) | Named structural/integration geometry and subsystem reservations exist in source. | Does not prove structural strength, manufacturability or production feasibility. |
| Actuation | [Actuator frames](../src/masck_one/actuator_frames.py) and [checks](../tests/test_actuator_frames.py) | Controlled actuation-zone geometry and digital consistency checks exist. | Does not prove force, lifetime, acoustics, comfort or motion quality. |
| Waste handling | [Mixed-waste backbone](../src/masck_one/realized_waste_backbone.py) | A source-bound digital routing architecture exists and retains validation-gated states. | Does not prove recovery, leakage, hygiene, cleaning or hydraulic performance. |
| Requirements and evidence controls | [Engineering authority](../config/masck_one_authority.yaml), [authority contract tests](../tests/test_authority_contract.py) and [boundary-release tests](../tests/test_boundary_release.py) | Requirements, duplicated constraints, provenance and digital-only evidence boundaries are machine-checked. | A passing software check is not achieved physical performance or product validation. |

The purpose of this spot-check is traceability. Major subsystem statements lead to concrete source/check evidence, while unresolved physical and commercial questions remain explicitly outside the claim.