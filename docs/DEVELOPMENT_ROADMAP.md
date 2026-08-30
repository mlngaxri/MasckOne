# Masck One — controlled development roadmap

## Purpose

Masck One is being developed in deliberately small, reviewable iterations. Each iteration should introduce one tightly bounded engineering capability, integrate it with the existing source of truth, add adversarial/regression tests, pass the full repository CI chain, and merge only when the previous digital baseline still closes.

The baseline plan contains **40 iterations** through digital Alpha release readiness. The number is a planning baseline, not an artificial stop rule: a difficult subsystem may be split into smaller iterations if doing so materially improves traceability or safety. Conversely, two later tasks may be combined only if they are genuinely inseparable and can still be reviewed rigorously.

Physical validation remains separate. Completion of this roadmap means the digital engineering system is as complete as it can responsibly be before real prototype evidence becomes the limiting factor; it does not mean the product is physically validated or production-certified.

## Phase 1 — foundations and human-reference geometry

1. Repository integrity, reproducible toolchain and CI. **COMPLETE**
2. Strict machine-authority schema and semantic validation. **COMPLETE**
3. Canonical global coordinates, datums and rigid transforms. **COMPLETE**
4. Facial-reference landmark layer and derived neutral metrics. **COMPLETE**
5. Headform/reference-surface ingestion, units, provenance and registration contract.
6. Neutral facial reference surface generator/import abstraction.
7. Protected eye, mouth and nostril hard-envelope geometry.
8. Worn-pose/misregistration transform engine and hard-envelope regression set.
9. Facial-region segmentation and coverage-analysis mesh.

## Phase 2 — compliant facial interface and nose/T-zone architecture

10. Main compliant facial-interface topology and parameter zones.
11. Dedicated nasal saddle, bridge/dorsum/sidewall and philtrum continuity architecture.
12. Perimeter interface, seal/compliance zones and aperture-edge transitions.
13. Interface-to-structural-frame attachment/clamp architecture.
14. First nonlinear membrane/contact simulation framework with evidence-gated material cards.

## Phase 3 — rigid structure, shell and actuation

15. Functional structural frame topology and mechanical datum network.
16. Exterior engineering surface / Class-A reference workflow and deviation governance.
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

## Phase 8 — CAD release and digital Alpha gate

39. Fusion 360 reconstruction/export integration, named components/parameters, neutral CAD exports, drawings and release manifests.
40. Full-system regression, visual/red-team inspection, validation-protocol package and digital Alpha release-readiness report.

## Mandatory completion rule for every iteration

An iteration is not complete merely because new code exists. Before merge it must, where applicable:

- preserve the machine authority/status distinctions;
- introduce no unsourced physical claims;
- use canonical coordinates and stable IDs;
- add tests for normal behavior and plausible corruption/failure modes;
- retain all previous engineering assertions unless an explicit controlled change justifies otherwise;
- pass authority validation;
- pass repository preflight;
- pass the full unit/integration test suite;
- pass deterministic CAD smoke generation;
- document what was deliberately not attempted;
- leave real-world unknowns marked as evidence gates rather than guessed values;
- pass GitHub Actions on the exact pull-request head before merge.

## Scope-change rule

The roadmap itself is controlled project documentation, but it is not more authoritative than the engineering authority. If a later discovery requires additional iterations, insert them explicitly and explain why. Do not compress work merely to preserve the original count.
