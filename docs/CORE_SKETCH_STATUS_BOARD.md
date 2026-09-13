# MASCK ONE Core Sketch status board

Status: **concept-level triage derived from the execution backlog; no physical closure implied**  
Review: 2026-09-12. Exact current source/owner identity must be reconstructed before acting.

## Product decision

**Continue the complete facial-routine hypothesis through bounded proof gates.** The five lanes survive. Full-routine completion, user-product choice, offline use, dock bulk/session wearable, protected anatomy, unpowered release and calm cost-conscious tactile quality remain locked concept intent. These are not achieved-product claims.

The broad convergence review is complete. The program is now in **P0 contract execution / physical feasibility preparation**, not another generic concept-review cycle.

## Binding program deadline

**Production-readiness deadline: 2 April 2027.** This is the fixed program finish line for Masck One. Schedule pressure may change sequencing or scope, but it may not convert missing evidence into a pass, weaken protected-anatomy or safety requirements, or relabel an unresolved physical gate as complete.

**2 November 2026 is the hard integrated proof and digital-completion checkpoint.** By this date the program must have a truthful, integrated physical alpha demonstrating the core routine path with controlled evidence for the critical feasibility gates, plus a feature-complete release-quality website, real companion app, backend/account path and core routine/product/control algorithms. Any unavailable hardware-dependent digital feature must be capability-gated rather than faked.

After 2 November, the dominant program should shift from proving that the architecture can work to engineering validation, reliability, DFM, supplier/tooling closure, production software hardening and pilot manufacturing.

### Strict phase gates

| Deadline | Mandatory outcome |
|---|---|
| **20 Sep 2026** | Current-source whole-product architecture reconciled. Major owner PRs have explicit disposition. Prototype BOM, procurement list, bench fixtures and measurement methods are frozen enough to build. Website/app implementation lane is active again in parallel. |
| **4 Oct 2026** | First integrated physical alpha hardware and reduced-region bench system assembled. Core fluid, treatment, retention/release, electrical/HMI and thermal functions can be exercised on safe off-face/inert rigs. No digital result may stand in for missing bench evidence. |
| **18 Oct 2026** | Reduced-region clean -> rinse/recover -> leave-on -> non-wiping release sequence has controlled measured runs. Major failure modes have repeatable tests. Full-product alpha revision is built or in final assembly. |
| **1 Nov 2026** | Integrated alpha rehearsal complete. Core product website and app are feature complete, responsive and testable end-to-end against real backend services or explicitly gated hardware adapters. Core routine scheduling, product/session validity, capability/state and safety algorithms have deterministic tests. |
| **2 Nov 2026** | **Integrated proof gate.** Physical alpha demonstrates the core Masck One experience with truthful evidence boundaries. Critical G0-G4 feasibility questions have physical or directly source-bound evidence sufficient to decide continuation. Website, app, backend and core algorithms are demo-ready and release-quality in all non-hardware-gated areas. Public claims match actual evidence. |
| **30 Nov 2026** | EVT1 complete: integrated engineering prototype, measured mass/CG/fluid/power/thermal behavior, fault handling, serviceability and repeatable core routine operation. Highest-risk geometry and electrical/mechanical architecture changes identified. |
| **20 Dec 2026** | EVT2/design convergence: major architecture changes closed or explicitly escalated. Wearable/dock interface, cartridge, retention, treatment, wet/dry separation, thermal path, electronics and firmware interfaces are source-bound. App/device protocol contract frozen enough for real integration. |
| **15 Jan 2027** | DVT build complete. Representative materials/processes used where practical. Human factors, fit/placement, comfort, release, leakage, drain/dry, acoustics/vibration, thermal behavior and routine completion have controlled validation plans and active evidence collection. |
| **12 Feb 2027** | DVT closure target. Product requirements intended for launch are physically validated or removed from launch scope. Reliability, cycle-life, ingress/hygiene/service, battery/runtime and fault tests have quantified results. Website/app/backend are production hardened; real device integration replaces simulated adapters where hardware supports it. |
| **5 Mar 2027** | PVT/pilot build begins from production-intent CAD/BOM/firmware/software. Supplier, tooling, assembly, CTQ, inspection, calibration, traceability, packaging and service processes are documented. No open architecture-level blocker is acceptable. |
| **19 Mar 2027** | Pilot units pass production validation at the agreed sample size. Yield/failure data is recorded, corrective actions are bounded, manufacturing instructions and end-of-line tests are executable, and launch digital systems have production deployment/runbooks. |
| **1 Apr 2027** | Final release-candidate review: no unresolved severity-1 or launch-blocking severity-2 defect, no unowned physical evidence gap, no fake digital capability, BOM/suppliers/tooling/process/test package frozen for controlled production. |
| **2 Apr 2027** | **PRODUCTION READY.** Masck One may be declared production-ready only if the release-candidate definition below is actually satisfied. Missing evidence makes the gate FAIL, not late-by-definition PASS. |

### Production-ready definition for 2 April 2027

Production ready means ready to enter controlled manufacture of the defined launch configuration, not merely attractive CAD or a working one-off prototype. At minimum:

- production-intent CAD, drawings, BOM, tolerances, materials, finishes and assembly process are frozen;
- critical suppliers and long-lead components are selected with viable sourcing paths;
- physical requirements in launch scope have controlled evidence and traceable acceptance results;
- fit, placement, retention/release, protected anatomy, airway/vision where applicable, fluid containment/recovery, treatment delivery, thermal behavior, electrical safety/fault behavior, battery/runtime, drain/dry/hygiene, service and reliability gates are closed to the level required for the launch scope;
- manufacturing CTQs, incoming inspection, in-process inspection, end-of-line test, calibration, traceability and failure handling are defined;
- pilot/PVT units demonstrate the production process rather than hand-built exceptions;
- firmware and device protocol are versioned and release-candidate quality;
- website, app, backend, account/commercial flows and core algorithms are production deployed or store-ready as applicable, with hardware-dependent capability gating intact;
- public claims remain bounded by evidence and any regulatory/claims work required for the chosen launch claims is complete or those claims are removed;
- no evidence field is silently zero-filled, inferred or promoted from simulation when physical validation is required.

### Deadline discipline

- Dates are hard coordination gates. A missed gate is marked **RED** immediately; the deadline itself is not silently moved.
- Within 24 hours of a RED gate, the conductor must publish the blocker, owner, recovery action and impact on 2 April 2027.
- Critical-path work outranks polish. Existential physical proof, safety, source-bound integration, reliability and manufacturability outrank discretionary features and CMF refinement.
- Parallelize digital work aggressively where it does not consume the same owners or hide hardware uncertainty.
- Digital completeness cannot create a physical pass. Physical success cannot excuse unfinished production software.
- Any feature that threatens the 2 April production gate without being required for the launch value proposition should be removed from launch scope rather than allowed to destabilize the core product.

Top-level schedule tracking is anchored in GitHub issue #159.

## First proof gates

| Gate | Tasks | State and immediate decision |
|---|---|---|
| G0 required domain and meaningful compatibility | CS-015/014/080/094/291/293 | **PROVE.** CS-015 now has an explicit stage-by-region completion contract. Define representative actual routines/products; no aggregate metric may hide a required untreated region. |
| G1 reduced cross-stage transfer | CS-010/012/013/121/160..165 | **PROVE.** `CORE_SKETCH_REDUCED_REGION_PROOF_PACKAGE.md` defines the BENCH program and measurement philosophy. Next closure requires physical evidence, not more documentation. |
| G2 whole-face contact/support/release | CS-018/050/180/181/271 | **PROVE.** `CORE_SKETCH_CONTACT_OCCLUSION_MATRIX.md` now covers stationary and moving contact classes. Next step is source-binding actual owner geometry/shadows and later whole-face/HUMAN evidence. |
| G3 preservation and prepared-session validity | CS-016/017/095/112/113/191/210 | **Contract SELECTED; preservation PROVE.** CS-016/017 semantics are explicit in `CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md`; implementation and formulation/storage/changeover proof remain open. |
| G4 joint resources and ownership value | CS-053/070/100/108/110/142/291/293 | **PROVE.** `CORE_SKETCH_ROUTINE_RESOURCE_ENVELOPE.md` now requires S0 minimum, S1 normal-PM and S2 demanding-AM closure across fluids, mass/CG/torque, energy, time, dock slots and service. Unknown serum/SPF inputs may not be zero-filled. |
| G5 SPF-containing AM feasibility | CS-170..175 | **PROVE / qualified physical and claims evidence BLOCKED.** Start research early; generic deposition or dose mass cannot establish protection. |

CS-015..018 remain the canonical P0 contracts. Their **definitions are now substantially specified**, but their physical evidence states remain PROVE where applicable. Creating a better contract is not the same as proving the hardware.

## Current P0 artifacts

- `CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md` — required-region completion, all-contact transition, prepared-session validity, product integrity and resource invariants.
- `contracts/core_sketch_p0_convergence_v1.json` + `tests/test_core_sketch_p0_convergence_contract.py` — machine-readable concept/evidence guard; explicitly non-engineering authority.
- `CORE_SKETCH_REDUCED_REGION_PROOF_PACKAGE.md` — smallest useful physical proof program.
- `CORE_SKETCH_CONTACT_OCCLUSION_MATRIX.md` — contact/support phase and shadow contract.
- `CORE_SKETCH_ROUTINE_RESOURCE_ENVELOPE.md` — whole-session resource ledger and current-authority reconciliation snapshot.
- `CORE_SKETCH_P0_OWNER_TRIAGE.md` — dated canonical owner/CI classification and routing.

## Existing owners continue bounded work

At the owner triage snapshot:

- **Treatment #135:** current observed head had no exact-head PR-triggered workflow receipt returned. Keep strict geometry/service/protected-region issues with treatment owner; provide contact/shadow evidence into CS-018.
- **Cartridge #140:** exact-head engineering CI is red because the Cell 5 DFM audit detects newly present `realized_waste_cartridge.py` and requires source rebind. This is an authority/provenance gate, not physical cartridge-failure evidence.
- **HMI #144:** exact observed head has green engineering CI. Preserve unchanged evidence; current-main/source reconciliation and physical tactile validation remain separate gates.
- **Retention #141:** current observed head had no exact-head PR-triggered workflow receipt returned. Preserve owner and extend normal-release acceptance to film preservation without weakening emergency release.
- **Dry-side #142:** exact-head engineering CI is red with 842 passed / 1 failed. The hostile escaped-route object is rejected, but clip-engagement rejection fires before the expected dry-bay containment predicate. Repair predicate independence/order without weakening either requirement.
- **Thermal #143:** exact observed head has green engineering CI. Physical containment/contact/condensation/reset/comfort/safety remain open; provide exact facial contact footprints and resource inputs.
- **Frame #117:** exact observed run was cancelled rather than failed. Rerun unchanged head if still valid; do not mutate geometry in response to a cancellation alone.

These observations are dated. `CORE_SKETCH_P0_OWNER_TRIAGE.md` owns the interpretation; live GitHub wins when an owner moves.

## Immediate execution order

1. **BENCH:** execute/rehearse the reduced-region measurement methods and then the clean-to-leave-on proof. Documentation alone can no longer close G1.
2. **DIGITAL:** source-bind the CS-018 contact/occlusion matrix to actual current treatment, thermal, fluid/seal and retention geometry.
3. **DIGITAL + BENCH inputs:** populate the S0/S1/S2 routine resource envelope with real dose, dead-volume, retained-fluid, package-mass and energy inputs; leave missing inputs visibly unknown.
4. **BENCH / formulation:** define practical product-family envelope, preservation and carryover criteria.
5. **DIGITAL/software:** implement CS-016 prepared-session validity/offline logic and hostile invalidation cases.
6. **OWNER REPAIRS IN PARALLEL:** cartridge DFM rebind, dry-side hostile predicate repair, exact-head receipts for treatment/retention, bounded HMI/current-main reconciliation, structural rerun if still source-valid.
7. **WHOLE FACE / HUMAN:** expand successful reduced-region behavior to sizing, placement, vision, comfort and complete required-region coverage.
8. **REG/CLAIM:** keep SPF on its separate higher-rigor track after ordinary leave-on deposition/release is credible.

## Deferred commitment

Whole-product digital/Fusion freeze, full-system physical alpha, human safety/comfort/efficacy, formulation preservation, SPF protection, measured tactile feel and production approval remain BLOCKED by their specific evidence gates. Optional modalities and discretionary CMF refinement do not outrank G0..G5. Their quality constraints still apply to every candidate.

The [convergence review](CORE_SKETCH_CONVERGENCE_REVIEW.md) records the broad contradictions and kill/pivot conditions. The [P0 feasibility contracts](CORE_SKETCH_P0_FEASIBILITY_CONTRACTS.md) define the execution invariants. The [backlog](CORE_SKETCH_EXECUTION_BACKLOG.md) owns canonical CS IDs and detailed acceptance; this board must not become a competing task registry.

## Lane 1 bounded implementation, 2026-09-11

Draft PR #154 implements an unpowered off-face CS-018 fixture and a deterministic regional cleansing simulation. See `CS018_FACIAL_INTERFACE_CANDIDATE.md` and `REGIONAL_CLEANSING_CONTROLLER.md`. Twelve individual coupon cells have geometric access accounting; actual owner shadows and unresolved reaction paths remain explicit. CS-015/018 remain PROVE/BLOCKED for whole-face physical completion. No human-use operating table or registered human size family is released. Routine OS and prepared-session producers retain their canonical ownership.
