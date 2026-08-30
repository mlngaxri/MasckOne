# Masck One contact simulation framework

## Scope

Iteration 14 creates the first controlled nonlinear membrane/contact analysis framework for Masck One. It defines the case matrix, material-card evidence contract, result schema, convergence rules and authority-linked pressure/strain fields required for later solver execution.

It does not fabricate silicone constitutive constants, run a physically meaningful nonlinear analysis without an evidence-eligible material card, or claim that pressure, strain, comfort, fit or safety requirements have passed.

## Upstream binding

The framework records the exact Iteration-13 interface-attachment topology SHA-256 and registered facial-mesh SHA-256. This prevents later simulation results from being silently associated with a different attachment or facial-reference revision.

The current neutral facial surface remains a development representation and is not automatically anatomical validation evidence.

## Material-card contract

The framework supports Yeoh- and Ogden-family hyperelastic cards. A material card can become evidence-eligible only when it contains:

- an explicitly selected constitutive model family;
- sourced constitutive parameters;
- parameter units and source references;
- a released source reference;
- a SHA-256 binding to the source evidence.

The default compliant-interface card is intentionally unresolved. It contains no constitutive constants, has `BLOCKED_PENDING_EVIDENCE_ELIGIBLE_CONSTITUTIVE_DATA` status, and makes solver execution not ready.

A non-evidence material card carrying numeric constitutive constants is rejected. This prevents placeholder silicone values from being mistaken for engineering evidence.

## Controlled sensitivity matrix

Iteration 14 defines four preload cases:

- 6 N
- 9 N
- 12 N
- 15 N

and three friction-coefficient sensitivity cases:

- 0.20
- 0.40
- 0.60

The Cartesian product creates 12 deterministic analysis-case identities. These values define a sensitivity framework only. They are not measured Masck One preload or friction values, and they do not promote the Iteration-13 unresolved interface preload into a product specification.

## Mesh refinement framework

Three semantic refinement identities are defined:

- `MESH_LEVEL_COARSE`
- `MESH_LEVEL_MEDIUM`
- `MESH_LEVEL_FINE`

No unsupported physical element size is assigned at this stage. Solver-specific meshing can later bind actual meshes to these refinement levels with revision and provenance.

## Required result fields

The controlled result contract includes:

- bridge p95 contact pressure;
- cheek p95 contact pressure;
- membrane p95 strain;
- membrane local maximum strain;
- analysis-case identity;
- mesh-level identity;
- exact material-card SHA-256;
- result provenance;
- explicit synthetic-regression-fixture status;
- physical-validation eligibility, fixed false for Iteration-14 simulation outputs.

Authority limits are carried into the framework without being treated as passing results:

- bridge p95 pressure: <= 4 kPa;
- bridge steady pressure: <= 6 kPa;
- cheek p95 pressure: <= 5 kPa;
- dynamic pressure: < 8 kPa;
- membrane p95 strain: <= 20%;
- local membrane maximum strain: <= 35%.

These limits remain validation-gated.

## Numerical convergence

The framework requires mesh-refinement comparison to satisfy both of the following numerical criteria:

- less than 5% relative change in the maximum of bridge and cheek p95 pressure change;
- less than 3% relative change in local maximum strain.

A numerical convergence pass means only that the selected numerical outputs are stable against the compared mesh refinement under the same case and material-card revision. It is not a manufacturing tolerance, material-validation result, physical-validation result or product-safety pass.

Comparisons across different case IDs or different material-card revisions are rejected as invalid convergence comparisons.

## Synthetic regression fixtures

Tests use explicitly labelled synthetic numeric result fixtures to verify result parsing and convergence logic. Those values are software fixtures only. They are not predictions of Masck One physical behavior and cannot be promoted to product evidence.

## Solver handoff

The current implementation is solver-agnostic. Once an evidence-eligible material card and appropriate registered geometry are available, a downstream solver adapter can consume the controlled case definitions and produce results conforming to the result contract.

Before any pressure or strain result can influence design release, the solver path must additionally establish appropriate element formulation, contact formulation, boundary conditions, material calibration, mesh convergence, geometry representativeness, result provenance and comparison to physical evidence where required.

## Evidence boundary

Iteration 14 does not close:

- constitutive material validation;
- human fit;
- facial pressure;
- membrane strain;
- comfort;
- airway clearance;
- fluid ingress;
- durability;
- cleansing efficacy;
- product safety.

The framework prepares a traceable path for those later decisions while keeping them blocked until defensible evidence exists.
