# Iteration 14 acceptance record

## Scope

Iteration 14 establishes a deterministic, solver-agnostic nonlinear membrane/contact simulation framework. It provides evidence-gated material cards, a complete sensitivity-case matrix, controlled result fields, mesh-refinement convergence checks and explicit linkage to the current attachment and facial-reference revisions.

## Required acceptance conditions

Promotion requires the exact pull-request head to pass all applicable repository gates, including authority validation, repository preflight, prior subsystem preflights, the Iteration-14 contact-simulation preflight, the full unit/integration suite and deterministic CAD smoke generation.

The framework itself must satisfy all of the following:

- exact binding to the current Iteration-13 attachment topology SHA-256 and registered facial-mesh SHA-256;
- exactly 12 controlled preload/friction cases from 6, 9, 12 and 15 N crossed with friction coefficients 0.20, 0.40 and 0.60;
- explicit coarse, medium and fine mesh identities without unsupported element-size invention;
- default compliant-interface material card contains no fabricated constitutive parameters;
- material-dependent solver execution remains blocked until an evidence-eligible material card exists;
- evidence-eligible material cards require a selected Yeoh or Ogden model family, sourced parameters, source reference and source SHA-256;
- bridge/cheek pressure and membrane-strain limits are read from the machine authority rather than duplicated as independent source values;
- numerical convergence requires less than 5% p95-pressure change and less than 3% local peak-strain change;
- convergence comparisons reject different case identities and material-card revisions;
- synthetic regression fixtures are explicitly labelled synthetic and remain non-physical evidence;
- no simulation result can be marked physical-validation eligible;
- pressure, strain, comfort, fit and product-safety gates remain unpromoted.

## Current blocked dependency

A physically meaningful nonlinear contact solve is intentionally blocked because the repository does not yet contain an evidence-eligible compliant-interface constitutive material card. Appropriate coupon-derived or otherwise defensible source data is required before solver execution can generate design evidence.

This blocker does not prevent completion of Iteration 14 because the roadmap scope is the simulation framework itself, not fabricated material-dependent results. The framework is designed to accept the real material card later without changing its evidence discipline.

## Deliberately not attempted

Iteration 14 does not select a production silicone grade, invent Yeoh/Ogden constants, establish a measured friction coefficient, define a validated facial preload, prove anatomical representativeness, prove pressure/strain compliance or close human-fit/comfort requirements.

## Downstream dependency

Iteration 15 may proceed with structural-frame topology while material characterization remains separately evidence-gated. Later physical material characterization and headform/contact validation must feed released data back through this framework before pressure or strain status can be promoted.
