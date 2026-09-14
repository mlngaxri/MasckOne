# Masck One binding program timeline

Status: **binding coordination schedule; evidence requirements remain controlling**  
Issued: 2026-09-12  
Final production-readiness deadline: **2 April 2027**

This schedule is the cross-product deadline contract for Masck One hardware, physical validation, firmware/control logic, routine/product algorithms, website, companion app, backend, manufacturing readiness and release evidence.

It does not override `config/masck_one_authority.yaml`, protected-anatomy/safety requirements, released engineering source, physical validation requirements or truthful claim boundaries. A deadline cannot turn missing evidence into a pass.

## Non-negotiable program gates

### 20 September 2026: build-ready architecture

- Reconstruct and reconcile the live whole-product source graph.
- Give every material owner PR an explicit disposition: release path, repair, supersede, or blocked dependency.
- Close enough digital geometry to order/build first integrated prototypes without relying on contradictory branches.
- Freeze the first physical prototype BOM, bench fixtures, instrumentation plan and procurement list.
- Start the website/app/backend lane in parallel. The old 1 September directive that autonomous website/app work is stopped is superseded by the 12 September 2026 program deadline directive.

### 4 October 2026: first integrated physical alpha

- Assemble a physical alpha or mechanically representative integrated stack.
- Assemble the reduced-region bench rig and required measurement tooling.
- Exercise fluid delivery/recovery, treatment motion, retention/release, HMI/electrical behavior and thermal functions on safe off-face or inert fixtures as appropriate.
- Record failures quantitatively. Do not replace absent measurements with simulation.
- Website shell, app architecture, backend schema and core state/capability interfaces must be running in real code.

### 18 October 2026: core physical sequence proven on bench

- Obtain controlled measured runs for the required sequence: clean -> rinse/recover -> leave-on -> settle -> non-wiping release.
- Close or reproduce dominant leakage, pooling, occlusion, wipe, carryover, support-loss and protected-boundary failure modes.
- Build or enter final assembly of the integrated wearable alpha revision.
- Routine scheduling, product/session validity, offline execution, capability/state and safety logic must have deterministic tests.

### 1 November 2026: integrated rehearsal complete

- Run the intended 2 November demo/proof flow end to end.
- Website is feature complete, responsive, performant and visually release-quality.
- App is a real maintained iOS/Android application, not a static mockup.
- Backend account/reservation paths work end to end.
- Hardware-dependent app states are capability-gated and cannot leak simulated telemetry as real data.
- Core routine/product/control algorithms are feature complete for the current launch architecture and have hostile/regression tests.

### 2 November 2026: hard integrated proof and digital-completion checkpoint

By this date Masck One must have:

- a truthful integrated physical alpha demonstrating the core product experience;
- controlled physical evidence for the highest-risk feasibility questions, especially cross-stage transfer, fluid handling, contact/support/release and critical resource closure;
- an evidence-backed decision on any architecture that still blocks whole-product feasibility;
- a release-quality website in all non-hardware-gated areas;
- a real companion app with final visual/interaction states for supported, unsupported, connected, disconnected, worn, not-worn and unknown capability states;
- real backend/account/reservation behavior;
- feature-complete core routine, product/session-validity and device capability algorithms;
- public copy and visuals that match the actual evidence state.

The intended meaning of this gate is that the program is no longer asking only "can Masck One work at all?". After this date the main burden should move to engineering validation, reliability, manufacturability, production software and scale-up.

This gate is not permission to pretend that lifetime, reliability, human factors, manufacturing or regulatory work is already complete.

### 30 November 2026: EVT1

- Integrated engineering prototype operates the core routine repeatedly.
- Measure mass, CG, torque, fluids, retained fluid, waste, energy, thermal behavior, timing and release reserves.
- Exercise normal and credible fault states.
- Verify service access, cartridge handling, wet/dry segregation and basic hygiene/drain paths.
- Record actual prototype configuration, firmware/software versions and evidence provenance.
- Identify all architecture-level changes still required before design convergence.

### 20 December 2026: EVT2 and architecture convergence

- Close or explicitly escalate major architecture changes.
- Source-bind wearable/dock interfaces, cartridge, treatment, retention, structure, thermal path, electronics, fluidics and service geometry.
- Freeze the device/app protocol sufficiently for real hardware integration.
- Complete website/app/backend functional QA for all non-hardware-gated paths.
- Freeze launch-scope algorithm interfaces and versioning.

### 15 January 2027: DVT build

- Build design-validation units with representative materials and production-intent processes where practical.
- Begin controlled validation of fit/placement, comfort, retention/release, protected anatomy, leakage, fluid distribution/recovery, treatment delivery, thermal behavior, drain/dry, acoustics/vibration and routine completion.
- Run battery/runtime, electrical/fault and interrupted-session validation.
- Bind test results to exact hardware/software revisions.
- Real device integration must replace simulated adapters wherever the hardware capability now exists.

### 12 February 2027: DVT closure target

- Every launch-scope physical requirement is validated, has a justified bounded exception with owner/date, or is removed from launch scope.
- Reliability/cycle-life, ingress/hygiene/service, battery/runtime, thermal fault, retention/release and fluid fault tests have quantified evidence.
- Production software contains no dependency on fake telemetry.
- Website, app and backend are production hardened.
- Customer-facing claims are reconciled against measured evidence.

### 5 March 2027: PVT/pilot begins

- Production-intent CAD, BOM, firmware and software are frozen except controlled change.
- Critical suppliers and long-lead parts have viable sourcing paths.
- Tooling/fixtures, assembly sequence, work instructions, CTQs, inspection, calibration, serialization/traceability, end-of-line test and nonconformance handling are documented.
- Pilot units are built through the intended process rather than hand-built exceptions.
- No unresolved architecture-level blocker is acceptable.

### 19 March 2027: production validation closure

- Pilot/PVT units pass agreed production validation.
- Yield and failure data are recorded and corrective actions are bounded.
- End-of-line tests detect critical assembly/function faults.
- Manufacturing instructions, inspection criteria, calibration and traceability are executable.
- Launch digital systems have production deployment procedures, monitoring, backups and rollback/runbook coverage appropriate to their risk.

### 1 April 2027: final release-candidate review

Required state:

- no unresolved severity-1 defect;
- no launch-blocking severity-2 defect;
- no unowned physical evidence gap;
- no fake or development-only digital capability visible as production truth;
- no unresolved BOM/supplier/tooling/process blocker preventing controlled production;
- all release artifacts identify exact source, hardware, firmware, software and test revisions.

### 2 April 2027: PRODUCTION READY

Masck One may be declared production-ready only if the launch configuration satisfies the production-ready definition below. Missing evidence makes the gate fail. The date must not be used to relabel an incomplete product as ready.

## Production-ready definition

Production ready means ready to enter controlled manufacture of the defined launch configuration, not merely possessing polished CAD, a single working prototype or a finished website.

At minimum:

- production-intent CAD, drawings, BOM, tolerances, materials, finishes and assembly process are frozen;
- critical suppliers, substitutions and long-lead procurement paths are defined;
- physical launch requirements have traceable controlled evidence;
- fit/placement, retention/release, protected anatomy, airway/vision where applicable, fluid containment/recovery, treatment delivery, thermal behavior, electrical/fault behavior, battery/runtime, drain/dry/hygiene, service and reliability gates are closed to the level required by launch scope;
- manufacturing CTQs, inspection, end-of-line test, calibration, traceability and failure handling are defined;
- PVT/pilot units demonstrate the production process rather than hand-built exceptions;
- firmware and device protocol are versioned and release-candidate quality;
- website, app, backend, account/commercial flows and core algorithms are production deployed or store-ready as applicable;
- hardware-dependent digital functions remain capability-gated until real hardware evidence supports them;
- regulatory/claims work required for chosen launch claims is complete, or unsupported claims are removed;
- no physical result is inferred from CAD/simulation alone where physical evidence is required.

## Digital completion definition

For schedule purposes, website/app/algorithm completion means:

- website is direct-deployed, responsive, accessible, performant and visually release-quality;
- website uses current product truth and actual app UI rather than a divergent fake app;
- app runs as a real iOS/Android codebase with production-quality disconnected/unsupported states;
- backend authentication/account/reservation flows are tested end to end;
- device capability, worn-state and command gating fail closed;
- simulated development adapters cannot write production telemetry as if it were real;
- routine scheduling, prepared-session validity, product compatibility/integrity boundaries and device capability/control state machines are versioned and tested;
- live BLE/session/control integration is complete wherever the production hardware exposes those capabilities;
- remaining gated functions are absent or visibly unsupported rather than fabricated.

## Deadline discipline

- Every date above is a hard coordination gate.
- A missed gate is marked RED immediately. The date is not silently moved.
- Within 24 hours of a RED gate, the conductor must publish blocker, owner, recovery action and effect on the 2 April deadline.
- Existential proof and safety outrank polish.
- Whole-product contradictions outrank local optimization.
- Physical evidence outranks claims.
- Digital work should run in parallel when it does not consume the same critical hardware owner.
- Physical success does not excuse unfinished production software.
- Digital completion does not create a physical pass.
- Any nonessential feature that threatens the 2 April production gate should be removed from launch scope rather than destabilize the core product.

Top-level tracking issue: #159.
