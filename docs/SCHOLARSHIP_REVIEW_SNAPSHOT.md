# Scholarship review snapshot

[Venture snapshot](VENTURE_SNAPSHOT.md) · [Project overview](../README.md) · [Visual evidence quicklook](VISUAL_EVIDENCE_QUICKLOOK.md) · [Venture progress](VENTURE_PROGRESS.md) · [Claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md) · [Execution timeline](SCHOLARSHIP_EXECUTION_TIMELINE.md) · [Customer discovery](CUSTOMER_DISCOVERY.md) · [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md)

I am developing Masck One as a pre-commercialisation venture exploring whether selected parts of a facial-skincare routine can be made less hands-on through a wearable device and supporting dock. I have developed engineering geometry, requirements, code-based CAD, automated checks and design records. I have not begun product-level physical validation.

For a non-technical scholarship reviewer, I recommend starting with the [one-page venture snapshot](VENTURE_SNAPSHOT.md). It covers my problem and target-user hypotheses, the deliberately unlocked first use case, what I have built, my preliminary customer research, current uncertainties, dated progress and next evidence milestones. This page then provides the shorter audit path into the underlying engineering evidence.

I use this review path to separate what I have built from what still needs customer, physical and commercial evidence. For the fastest visual inspection of the documented architecture and representative traceable digital work, see the [visual evidence quicklook](VISUAL_EVIDENCE_QUICKLOOK.md). For a dated, commit-linked record of execution, see the [execution timeline](SCHOLARSHIP_EXECUTION_TIMELINE.md). For a question-by-question boundary between supported claims, hypotheses and unproven outcomes, see the [claim ledger](SCHOLARSHIP_CLAIM_LEDGER.md).

Engineering-source links below are pinned to live engineering `main` revision `becf782bf809543ba4b83ecab689204b2458de7d`, verified on 18 September 2026. Scholarship documentation may advance independently and must not be read as a newer engineering release.

**Reviewer audit rule:** the cited engineering-owner source at the pinned revision controls the claim. My scholarship prose can explain or narrow that evidence, but it cannot upgrade a target, framework, synthetic result, geometry screen or planned test into achieved physical or commercial evidence.

## How to read the evidence

| Evidence class | What belongs here | What a reviewer may conclude |
| --- | --- | --- |
| Existing digital engineering evidence | Parametric CAD, controlled requirements, automated checks, source-bound records and documented design decisions already present in the repository. | The engineering work exists and can be inspected at the cited revision. |
| Planned validation | Customer interviews, focused analysis, fit prototyping, fluid testing, hygiene/cleaning investigation and manufacturing-cost work that I have defined but not yet completed. | I have explicit next evidence gates, not evidence that those gates have passed. |
| Physical/commercial evidence not yet obtained | Qualifying evidence for customer demand, comfort, hygiene/cleaning practicality, real fluid behaviour, safety, manufacturing feasibility, unit economics and product-level physical performance. | These claims remain unproven and must not be inferred from digital work, synthetic tests or validation frameworks. |

## 60-second engineering evidence map

| Claim a reviewer may test | Representative evidence | What it establishes | Boundary |
| --- | --- | --- | --- |
| Parametric CAD exists | [Parametric model source](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/src/masck_one/model.py) and [model checks](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/tests/test_model.py) | Inspectable, code-generated geometry and digital integrity checks exist. | Not human fit, comfort, safety, manufacturability or physical performance. |
| System requirements are controlled | [Engineering authority](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/config/masck_one_authority.yaml) and [authority contract tests](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/tests/test_authority_contract.py) | Controlled values and dependent sources can be checked for consistency. | Consistency does not prove the values are correct, safe or achieved by hardware. |
| Engineering evidence is source-bound | [Boundary-release tests](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/tests/test_boundary_release.py) | Revision identity and digital-only evidence boundaries are checked. | Not anatomical validity, physical performance or qualification of later revisions by older results. |
| Design decisions are documented | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md) | Records concrete retained principles, including dock-side bulk product with isolated wearable session quantities, unpowered emergency release independent of routine software, and completion defined by required-region application rather than pump counts. It also records 20 classified conflicts with owners and proof gates. | These are documented architecture decisions and problem definitions, not proof that the architecture works physically or commercially. The review itself calls physical feasibility a conditional hypothesis. |
| Major subsystems have inspectable digital coverage | [Whole-product convergence review](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/CORE_SKETCH_CONVERGENCE_REVIEW.md), [Core Sketch one-page architecture](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/CORE_SKETCH_ONE_PAGE.md) and [compliant interface topology](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/COMPLIANT_INTERFACE_TOPOLOGY.md) | My engineering record spans face/interface and treatment, fluids and waste, retention/structure/removal, electronics/controls, dock/service and whole-product interactions. | Coverage is uneven. Presence in CAD, requirements, analysis or design records does not mean a subsystem is complete, integrated, equally mature or physically demonstrated. |
| Missing evidence remains explicit | [Core Sketch status board](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/docs/CORE_SKETCH_STATUS_BOARD.md) | I keep proof gates marked `PROVE`, `BLOCKED`, validation-gated or otherwise unresolved until the required evidence exists; unknown inputs are not silently zero-filled. | A defined gate, protocol or deadline is planned validation, not evidence that the gate has passed. |

### Representative controlled requirements

These examples show how I turn product intent into auditable engineering targets without presenting the targets as achieved performance. All are inspectable in the pinned [engineering authority](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/config/masck_one_authority.yaml).

| Example | Controlled value | Repository status | Plain-language meaning |
| --- | --- | --- | --- |
| Nostrils / airway opening | at least 120 mm² each and 8 mm local opening | engineering baseline for opening geometry; pressure-drop and collapse evidence remains gated | The digital design reserves a minimum opening. It does not prove breathing safety on a wearer. |
| External liquid leakage | no more than 50 µL per cycle | engineering baseline | I define a leakage limit. No physical cycle has demonstrated it. |
| Waste recovery | at least 90% recovery and no more than 400 µL residual free liquid | validation-gated | I have defined a measurable recovery target, but qualifying fluid testing has not occurred. |
| Quick release | no more than 2 s; one-hand, wet and unpowered operation required | frozen safety requirement; force remains validation-gated | I specify emergency removal behaviour before testing; I do not claim it as demonstrated. |
| Loaded mass | no more than 255 g | project requirement | I have set a controlled mass ceiling; this does not establish comfort or a manufactured mass result. |

### Representative automated checks

The pinned [authority contract tests](https://github.com/mlngaxri/MasckOne/blob/becf782bf809543ba4b83ecab689204b2458de7d/tests/test_authority_contract.py) deliberately introduce controlled inconsistencies and require the validator to reject them. Representative examples are intentionally small enough to audit quickly:

| Check | Deliberate inconsistency | What rejection demonstrates | What it does not demonstrate |
| --- | --- | --- | --- |
| Airway duplication check | Changes one copy of the minimum airway area from 120 to 121 mm² | Duplicated controlled requirements cannot silently drift apart. | That 120 mm² is physiologically safe or physically achieved. |
| Clean-cycle ledger check | Changes the nominal introduced-liquid total to an inconsistent value | Dependent fluid-budget values must reconcile with their source quantities. | Real delivery accuracy, leakage, recovery or cleaning performance. |
| Cartridge-capacity check | Reduces retained capacity below the controlled ledger requirement | The digital authority rejects an internally under-capacity cartridge specification. | Manufactured cartridge capacity, sealing or waste behaviour. |
| Protected-classification check | Promotes an actuation architecture to an engineering baseline where the authority forbids that status | Evidence classifications cannot be silently promoted beyond their controlled state. | Physical readiness or validation of the actuation architecture. |

I use these checks for fail-closed consistency checking and evidence-state discipline. They can expose contradictions in the digital engineering record. I do not treat them as verification of customer demand, wearer comfort, hygiene, real fluid behaviour, safety, manufacturing capability, cost or physical performance.

### Current CI boundary

Exact engineering revision `becf782bf809543ba4b83ecab689204b2458de7d` has a completed successful `Masck One engineering CI` GitHub Actions run from the `main` push on 18 September 2026 ([run 1858](https://github.com/mlngaxri/MasckOne/actions/runs/35293789374)). This records that the workflow passed for that exact digital revision. I do not treat it as converting software checks, synthetic tests, geometry screens or validation frameworks into physical validation, and it does not qualify later revisions automatically.

## Evidence boundary

I have not yet obtained qualifying evidence for customer demand or willingness to pay; comfort or population fit; hygiene, cleaning or maintenance practicality; real fluid delivery, leakage or recovery behaviour; product safety; manufacturing feasibility; viable unit economics; or product-level physical performance. I treat each of these as unproven, rather than inferring them from the digital engineering record.

I treat synthetic tests, geometry screens, simulation frameworks and software checks as digital evidence unless qualifying physical measurements exist. Rapid digital progress should not be interpreted as rapid physical validation.

## Evidence before expansion

I do not want the broader wearable-and-dock vision to determine first-product scope. I want customer evidence to earn the right to test a focused use case physically. Focused physical evidence should then earn the right to investigate a product architecture more deeply. Customer value plus sourced cost evidence should earn the right to consider broader scope.

If the evidence is weak, I should narrow, change or reject a use case rather than hide that weakness behind additional feature development.

## How scholarship support converts to evidence

I would use scholarship support for structured customer validation, prototype materials and test equipment for focused fit, fluid and cleaning questions, and manufacturing and cost investigation. I am not assuming a funding amount or outcome. My purpose is to replace important assumptions with evidence, not to make the concept look more complete.

## My role, AI and collaboration

I use AI extensively to accelerate implementation, research, alternative generation and engineering exploration. I retain responsibility for venture direction, requirements, priorities, trade-offs and final decisions. I also expect specialist human expertise and collaboration to be important for hardware, manufacturing, IP, fundraising and market entry.

See [Venture progress](VENTURE_PROGRESS.md) for the fuller reviewer-facing progression and [Next-stage evidence plan](SCHOLARSHIP_NEXT_STAGE.md) for the evidence gates.
