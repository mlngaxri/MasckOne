# Scholarship review snapshot

[Project overview](../README.md) · [Evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md) · [Subsystem spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md)

Masck One is pre-commercialisation. Engineering geometry exists and digital checks/frameworks exist; product-level physical validation has not begun. This page is the canonical short reviewer path and separates digital engineering evidence from planned validation and evidence not yet obtained.

Engineering-source links below are pinned to audited live engineering revision `b4a105ea4483a6285be7d55fd527baea30ce6412`. Scholarship documentation may advance independently and must not be read as a newer engineering release.

## 60-second evidence map

| Claim a reviewer may test | Representative evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/src/masck_one/model.py) and [model checks](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/tests/test_model.py) | Inspectable, code-generated geometry and digital integrity checks exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/config/masck_one_authority.yaml) and [authority contract tests](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/tests/test_authority_contract.py) | Controlled values and dependent sources can be checked for consistency and rejected when they disagree. | Consistency does not prove the values are correct, safe or achieved by hardware. |
| Engineering evidence is source-bound | [Boundary-release tests](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/tests/test_boundary_release.py) | Revision identity and digital-only evidence boundaries are checked so stale evidence can fail closed. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions are documented | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/b4a105ea4483a6285be7d55fd527baea30ce6412/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) | Cross-subsystem conflicts, trade-offs, unresolved dependencies and validation gates are recorded. | A documented decision is not proof the architecture works physically or commercially. |
| Major subsystem work is inspectable | [Subsystem evidence spot-check](SCHOLARSHIP_SUBSYSTEM_SPOTCHECK.md) | Representative facial-interface, structure, actuation, waste and evidence-control work can be audited quickly. | Coverage is not subsystem readiness. |

Representative requirements include nostril/airway opening constraints, fluid-volume ledgers, waste-cartridge capacity, quick release, mass and pitch-torque limits. Automated authority checks deliberately reject inconsistent or unsupported states. These checks verify repository consistency and provenance, not measured airway, fluid, fit, release or cartridge performance. Requirements marked `VALIDATION_GATED` remain unproven until qualifying evidence exists.

## Evidence classes

| Evidence class | Current position |
| --- | --- |
| Existing digital engineering evidence | Controlled requirements, parametric CAD, automated checks, source binding, documented design decisions and representative subsystem geometry exist in the repository. |
| Planned validation | Structured customer interviews, focused analysis, physical fit/workflow work, core fluid testing, hygiene/cleaning investigation and initial manufacturing-cost modelling are planned. Plans, fixtures, protocols and frameworks are not completed results. |
| Physical/commercial evidence not yet obtained | Customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance remain unproven. |

Synthetic tests, geometry screens, simulation frameworks and software checks stay digital evidence unless qualifying physical measurements exist.

## Engineering discipline, not code volume

The repository uses machine-readable requirements, source binding, automated contradiction checks, documented trade-offs and explicit `UNKNOWN`, `VALIDATION_GATED`, blocked or reference-only states. Major subsystem exploration spans facial interface and treatment mechanics, storage and delivery, waste recovery, retention and structure, actuation, electronics and controls, and dock/preparation concepts. This demonstrates system-level digital engineering work, not completed or physically compatible subsystems.

AI is used extensively to accelerate implementation, exploration, documentation and code-based CAD. Founder judgement owns venture direction, requirements, priorities, trade-offs and final system-level decisions. AI output and passing software checks are not physical evidence.

## Current limitations

The repository does not currently prove customer demand or willingness to pay; comfort or population fit; hygiene, cleaning or maintenance practicality; real fluid delivery, leakage or recovery behaviour; product safety; manufacturing feasibility or production capability; unit economics or a viable commercial model; or product-level physical performance.

A founder-reported informal survey of around 20 people remains preliminary because its underlying questionnaire, recruitment method and raw responses are not repository evidence. It does not establish demand, willingness to pay, a validated segment or product-market fit.

## Current CI boundary

Live engineering `main` is `b4a105ea4483a6285be7d55fd527baea30ce6412`. No pull-request workflow run or combined commit status is associated with that exact revision, so it is not presented here as CI-qualified. The scholarship-review head likewise had no associated pull-request workflow run when reconstructed for this update.

An older workflow result can support only the exact revision and checks it actually ran. It cannot qualify current `main`, later documentation, skipped stages or physical performance.

## Next evidence gates

The next stage should reduce uncertainty rather than add feature breadth. Structured customer interviews should determine whether one repeated routine problem is strong enough to justify a focused first use case. If it survives that gate, focused fit/workflow work and repeatable core fluid testing should test the narrow physical assumptions. Hygiene and cleaning investigation should test whether maintenance erases the intended convenience benefit. Initial sourced manufacturing-cost modelling should test whether the surviving scope has a plausible commercial path.

Weak evidence should narrow, redesign or reject the relevant use case rather than be hidden by further digital development. See the [next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md) and [evidence matrix](SCHOLARSHIP_EVIDENCE_MATRIX.md).
