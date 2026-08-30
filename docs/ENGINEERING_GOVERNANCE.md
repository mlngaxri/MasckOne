# Masck One engineering repository governance

## Purpose

This repository is the deterministic digital-engineering implementation of **Masck One**. Source code may encode engineering baselines, calculations, CAD definitions, and validation infrastructure; it must not convert unresolved physical evidence into fictional certainty.

## Authority hierarchy

1. Safety-critical requirements in the controlling Masck One engineering authority.
2. Frozen requirements and frozen architecture.
3. Explicit quantified engineering baselines.
4. Validation-gated parameters.
5. Supplier-dependent parameters.
6. Design/CAD baselines.
7. CAD-closure items.
8. Implementation convenience.

A lower item cannot silently override a higher one.

## Naming rule

The product is **Masck One**. New machine identifiers use `MASCK_ONE`, `masck_one`, or `masck-one` according to context. CI/preflight must fail when legacy product naming reappears in source-controlled text.

## Authority contract

`config/masck_one_authority.yaml` is not treated as an informal bag of numbers. It is validated against `schemas/masck_one_authority.schema.json` before CAD generation is allowed.

The authority contract has two layers:

1. **Structural/schema validation** — required fields, controlled status vocabulary, exact unit registry, value types, array lengths, allowed commercial states, and rejection of uncontrolled additional properties.
2. **Semantic validation** — deterministic cross-field consistency such as duplicated airway values, bilateral neutral-baseline symmetry, fluid-ledger closure, service-capacity margin, ordered ranges, baseline-in-DOE membership, mass-limit ordering, and protected authority classifications.

Duplicate YAML mapping keys are rejected before schema validation. This prevents a later duplicate key from silently overwriting an earlier engineering value during parsing.

A schema or semantic failure is a build blocker. If an intentional engineering change requires a previously invalid relationship, the authority, schema/semantic rule, source justification, and affected tests must be changed together rather than bypassing the validator.

Schema validity is **not** physical validation. It proves only that the digital authority is structurally explicit and internally self-consistent.

## Source versus generated artifacts

The repository stores source authority and code. CAD exports are generated deterministically and are not treated as source authority. The `generated/` directory is ignored except for `.gitkeep`.

## Evidence discipline

A value may be represented digitally before it is physically validated, but its status must remain explicit. `BLOCKED`, `VALIDATION_GATED`, and equivalent states are valid engineering outcomes. A test protocol existing is not the same as a test passing.

## Change discipline

Engineering changes are made upstream first: authority or explicit design-decision record, then schema/semantic validation, regeneration, assertions, tests, and downstream artifacts. Final geometry must not be manually patched in a way that cannot be reproduced from the repository.

## Phase 1 invariant

Phase 1 establishes a reproducible repository foundation. A Phase 1 iteration is complete only if a fresh environment can install the project, authority-contract validation passes, preflight passes, tests pass, Python compilation passes, and the deterministic CAD build still succeeds.
