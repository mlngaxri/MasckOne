# Masck One — Phase 2, Iteration 10

## Main compliant facial-interface topology and parameter zones

**Development status:** implementation candidate pending exact-head CI and merge.

Iteration 10 is the first Phase-2 step that turns the human-reference geometry from Phase 1 into an explicit skin-contact architecture.

### Added

- `src/masck_one/interface_topology.py`
  - stable interface-zone IDs;
  - one-to-one coverage-triangle assignment;
  - contact versus protected-opening semantics;
  - exact area-conservation checks;
  - contact-component analysis;
  - authority-backed nasal-lobe thickness metadata;
  - deterministic topology SHA-256;
  - strict refusal to promote topology into fit/material/efficacy evidence.
- integrated `MasckOneModel.compliant_interface_topology`;
- engineering assertion `COMPLIANT_INTERFACE_TOPOLOGY`;
- preflight contract `COMPLIANT_INTERFACE_CONTRACT`;
- public lazy-loading API exports;
- adversarial and integration tests;
- engineering documentation and acceptance gate.

### Key design decision

The current authority specifies **0.30 mm** at the nasal-lobe center with a **0.25 / 0.30 / 0.35 mm** DOE, but it does not yet provide a deterministic geometric boundary for the dedicated nasal-lobe subsystem.

Iteration 10 therefore stores that numeric thickness as an authority-backed subsystem parameter while leaving the entire `INTERFACE_T_ZONE_NOSE_PHILTRUM` zone without a global numeric thickness.

This prevents a superficially convenient but technically unjustified mistake: treating one local nasal-lobe value as the thickness of the entire nose/T-zone membrane.

### Safety/coverage decision

The interface topology preserves all five current protected openings:

- left eye;
- right eye;
- mouth;
- left nostril/airway;
- right nostril/airway.

At the same time, the skin between the nose and upper lip remains an active cleansing/contact target. The nostrils themselves are protected; the surrounding external skin is not silently omitted.

### Deliberately not attempted

Iteration 10 does not define the detailed 3D nasal saddle, bridge/dorsum/sidewall shape, perimeter sealing geometry, aperture-edge roll/transition geometry, clamp attachment, nonlinear membrane material model or contact-pressure solution. Those belong to Iterations 11–14.

No new physical claim is created by this iteration.
