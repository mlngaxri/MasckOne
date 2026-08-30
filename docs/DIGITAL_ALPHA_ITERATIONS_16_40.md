# Digital Alpha architecture: Iterations 16 through 40

## Scope boundary

This candidate builds on the merged Iteration 15 structural-frame topology and continues the repository through the digital Alpha release boundary. It does not claim that the physical MVP is complete or verified.

## Implemented candidate capabilities

| Iteration | Candidate implementation | Evidence boundary |
|---|---|---|
| 16 | Class-A sample pairing and RMS/maximum deviation evaluator | Blocked until an authored, hashed and released Class-A reference exists |
| 17 | Four canonical actuator station frames and H2W development-reference envelopes | Placement and supplier reference are not production freeze |
| 18 | Angle-DOE swept envelopes and collision-preflight hooks | Coupling, flexures, reaction paths and tolerances unresolved |
| 19 | Authority actuation sensitivity register and impedance-rig handoff status | No measured impedance or cleansing-efficacy result |
| 20 | Exact 6.5 mL water-reservoir development envelope and usable-volume contract | Fill, vent, dead volume and service behavior unresolved |
| 21 | Cleanser dose/refill/compatibility/purge architecture | Storage capacity, formulation compatibility and purge geometry unresolved |
| 22 | Separate water/cleanser BP7 development pump envelopes and named route interfaces | Tubing IDs, bend radii, connectors and metering evidence unresolved |
| 23 | Parametric first-manifold topology with 18 water outlets and 6 cleanser outlets | Branch bores, restrictions, pressure drop and flow balance remain rig-gated |
| 24 | Target-only outlet placement and lateral/subsurface groove intent | Groove width, depth, length, distribution and cleansing efficacy remain unresolved |
| 25 | Four target-bound regional waste-acquisition centerlines and transient-buffer handoffs | Gutter/capillary dimensions, buffer capacity and recovery remain rig-gated |
| 26 | Takasago development-reference waste-pump envelope, route handoff and all eight required fault states | Mixed air/liquid/foam performance cannot be inferred from fresh-fluid data |
| 27 | Authority-sized cartridge envelope, keyed/sealed interface contracts and exact 35 mL internal capacity reservation | Retained capacity, leakage, sealing and service behavior remain validation-gated |
| 28 | Stable contracts for every fresh and waste route | Tube ID, bend radius, dead volume and service clearance remain unresolved |
| 29-30 | Off-face retention interfaces and unpowered quick-release safety contract | Member/mechanism geometry and headform/release evidence remain blocked |
| 31-34 | Battery dry-bay, four-control HMI and WARM/COOL reservations | Pack selection, ingress, final HMI semantics and thermal evidence remain blocked |
| 35-37 | Hygiene classification, assembly hierarchy and authority-backed DFM contract | Drainage, trajectories, bosses, tooling and tolerance stacks require realized parts |
| 38 | Automatic mass/CG, fluid, power and thermal ledgers | Missing components prevent false mass, torque, runtime or thermal closure |
| 39-40 | Hashed STEP/JSON reconstruction manifest and digital Alpha release gate | Drawings and physical MVP remain blocked by roadmap gates 41-64 |

## Generated CAD additions

The standard CLI exports waste-acquisition centerline references, the waste-pump packaging envelope, the 35 mL cartridge capacity reservation and official-frame-derived retention interface references. `build_report.json` and `release_manifest.json` contain hashes and the complete digital Alpha manifest while remaining explicit that generated geometry is not physical validation.

## Verification

Run:

```bash
python -m masck_one.quarter_preflight
python -m pytest
python -m masck_one.cli --output generated
```

Candidate promotion still requires exact-head GitHub CI. Physical gates remain blocked until the required registered anatomy, material characterization, supplier data, rigs and measurements exist.
