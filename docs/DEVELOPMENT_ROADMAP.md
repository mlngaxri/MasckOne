# Masck One — controlled development roadmap

## Purpose

Masck One is being developed in deliberately small, reviewable iterations. Each iteration introduces a bounded engineering capability, integrates it with the existing source of truth, adds adversarial/regression tests where digitally possible, and passes the applicable verification gate before promotion.

The current baseline contains **90 iterations** from repository foundation through production-release readiness. This is a planning baseline, not an artificial stop rule. Any subsystem may be split into smaller iterations if doing so improves safety, traceability, verification or change control. Work is never compressed merely to preserve the count.

Digital completion is not physical validation. Physical evidence, supplier evidence, accredited compliance work and controlled manufacturing evidence must remain separate status gates.

## Phase 1 — foundations and human-reference geometry

1. Repository integrity, reproducible toolchain and CI. **COMPLETE**
2. Strict machine-authority schema and semantic validation. **COMPLETE**
3. Canonical global coordinates, datums and rigid transforms. **COMPLETE**
4. Facial-reference landmark layer and derived neutral metrics. **COMPLETE**
5. Headform/reference-surface ingestion, units, provenance and registration contract. **COMPLETE**
6. Neutral facial reference surface generator/import abstraction. **COMPLETE**
7. Protected eye, mouth and nostril hard-envelope geometry. **COMPLETE**
8. Worn-pose/misregistration transform engine and hard-envelope regression set. **COMPLETE**
9. Facial-region segmentation and coverage-analysis mesh. **COMPLETE**

## Phase 2 — compliant facial interface and nose/T-zone architecture

10. Main compliant facial-interface topology and parameter zones. **COMPLETE**
11. Dedicated nasal saddle, bridge/dorsum/sidewall and philtrum continuity architecture. **COMPLETE**
12. Perimeter interface, seal/compliance zones and aperture-edge transitions. **RELEASE CANDIDATE — EXACT-HEAD CI REQUIRED**
13. Interface-to-structural-frame attachment/clamp architecture.
14. First nonlinear membrane/contact simulation framework with evidence-gated material cards.

## Phase 3 — rigid structure, shell and actuation

15. Functional structural frame topology and mechanical datum network.
16. Exterior engineering surface/Class-A reference workflow and deviation governance.
17. Four actuator local frames, supplier/development envelopes and mounts.
18. Actuator coupling, flexure/load paths, swept volumes and collision assertions.
19. Actuation parameter/sensitivity framework and impedance-test handoff.

## Phase 4 — fresh fluid delivery

20. Water reservoir architecture, fill/vent/usable-volume/service geometry.
21. Cleanser storage, refill, compatibility metadata and purge architecture.
22. Water/cleanser pump packaging and tubing-interface architecture.
23. Parametric manifold branching/metering model.
24. Skin-facing lateral distribution grooves and protected-region outlet-direction rules.

## Phase 5 — waste acquisition and containment

25. Facial waste gutters, capillary paths and regional transient buffers.
26. Mixed-phase waste-pump packaging, routing and fault-state architecture.
27. Waste cartridge keyed insertion, sealing, internal capacity reservation and service geometry.
28. Complete fresh/waste routing, bend-radius, dead-volume and service-clearance checks.

## Phase 6 — retention, power, HMI and thermal reservations

29. Halo/occipital/crown-support architecture and retention load paths.
30. Mechanical one-handed unpowered quick-release architecture and pinch/hair keep-outs.
31. Battery/electronics dry-bay packaging, swelling/fault clearances and harness routes.
32. Four-button physical HMI, seals, tactile differentiation and service indication envelopes.
33. WARM implementation envelope, temperature-sensing/limiting geometry and thermal-model hooks.
34. COOL experimental reservation, condensation/dew-point model and architecture comparison hooks.

## Phase 7 — manufacturing, assembly and quantitative closure

35. Wet/dry cavity classification, seals, drainage/drying and hygiene/service architecture.
36. Full assembly hierarchy, joints, insertion/removal trajectories and interference engine.
37. Manufacturing/DFM geometry: walls, ribs, bosses, draft, parting strategy, tolerance/CTQ register.
38. Automatic mass/CG/pitch-torque, fluid, power and thermal ledgers tied to the generated CAD revision.

## Phase 8 — digital Alpha release

39. Fusion 360 reconstruction/export integration, named components/parameters, neutral CAD exports, drawings and release manifests.
40. Full-system digital regression, visual/red-team inspection, validation-protocol package and Alpha release-readiness report.

## Phase 9 — physical subsystem evidence

41. Actuator/membrane bench-rig design and measured characterization.
42. Pump/manifold metering-rig design and measured characterization.
43. Nasal airflow and liquid-ingress rig.
44. Eye/mouth ingress and fault-fluid rig.
45. Waste mixed-phase acquisition rig.
46. Cartridge retained-capacity and leakage rig.
47. Retention, pressure and quick-release headform rig.
48. WARM thermal-fault and COOL feasibility rigs.
49. Material coupon characterization and constitutive-data release.
50. Integrated Alpha procurement and supplier evidence reconciliation.

## Phase 10 — integrated Alpha build

51. Integrated Alpha mechanical assembly.
52. Alpha firmware/control-state implementation.
53. Alpha electrical/protection integration verification by appropriately qualified engineering review/testing.
54. Alpha fluid commissioning and calibration.
55. Alpha dry functional verification.
56. Alpha wet functional verification.

## Phase 11 — Alpha validation and correction

57. P0 safety validation sweep.
58. Fit/headform matrix evaluation.
59. Pressure/contact verification.
60. Actuation/membrane performance verification.
61. Fluid distribution and nose/T-zone coverage verification.
62. Waste recovery and residual-liquid verification.
63. Alpha failure analysis, dependency propagation and architecture correction freeze.
64. **Integrated MVP design/build gate.**

## Phase 12 — MVP implementation

65. MVP CAD revision incorporating Alpha evidence.
66. MVP production-intent component selection.
67. MVP electronics/PCB revision.
68. MVP firmware revision and fault-state verification.
69. MVP prototype/process definition.
70. MVP pilot-parts procurement.
71. MVP assembly fixtures and controlled work instructions.
72. MVP build batch.

## Phase 13 — MVP verification

73. MVP dimensional inspection.
74. MVP leak/ingress verification.
75. MVP airflow/airway verification.
76. MVP thermal/electrical safety verification.
77. MVP cleansing-efficacy bench validation.
78. MVP durability/service-cycle testing.
79. MVP hygiene, drying and cleanability testing.
80. MVP usability/fit pilot after prerequisite safety closure.

## Phase 14 — production-product closure

81. MVP evidence reconciliation and requirement/status update.
82. Human-factors corrections.
83. Industrial-design refinement constrained by measured engineering evidence.
84. Final one-size/two-size architecture decision.
85. Production actuator decision.
86. Production pump/fluidic component decision.
87. Production battery/pack architecture decision.
88. Production cartridge/consumable architecture decision.
89. Production architecture design freeze and manufacturing/compliance handoff package.
90. **Final product production-release gate.**

## What the Iteration-90 gate means

Iteration 90 is not an assertion that unrestricted mass production can begin automatically. It is the design-release gate at which the product architecture, production-intent geometry, major suppliers/components, requirements, verification evidence and manufacturing handoff are sufficiently closed to enter or complete the controlled production/compliance ramp.

Accredited regulatory/compliance testing, supplier qualification, first-article evidence, tooling/process validation, packaging validation, pilot production/PVT, final manufacturing quality controls and launch readiness remain real-world gates. If those activities uncover a design issue, new controlled iterations are inserted rather than concealing the change behind the Iteration-90 label.

## Mandatory completion rule for every iteration

An iteration is not complete merely because new code, CAD or a physical part exists. Before promotion it must, where applicable:

- preserve machine-authority/status distinctions;
- introduce no unsourced physical claim;
- use canonical coordinates and stable IDs;
- add tests for normal behavior and plausible corruption/failure modes;
- retain previous engineering assertions unless a controlled change explicitly supersedes them;
- pass authority validation;
- pass repository preflight;
- pass the full applicable unit/integration test suite;
- pass deterministic CAD smoke generation where geometry is affected;
- document what was deliberately not attempted;
- leave real-world unknowns as evidence gates rather than guessed values;
- propagate upstream changes through dependent calculations and geometry;
- require the applicable GitHub CI status to pass on the exact PR head before software/CAD merge;
- require measured/supplier/compliance evidence before any physical-status promotion.

## Scope-change rule

The roadmap is controlled project documentation but is not more authoritative than the engineering authority or measured evidence. If later discoveries require additional iterations, insert them explicitly and explain the dependency. Do not compress work merely to preserve the original number.
