# Digital product handoff

This document connects the released engineering state to public-facing website, app and presentation work. It exists to keep digital presentation aligned with the repository without turning design intent into unsupported product claims.

## Source of truth

Before making a public-facing claim, check the current `main` branch and `config/masck_one_authority.yaml`. The project roadmap is in `docs/DEVELOPMENT_ROADMAP.md`, while the broader product direction is described in `docs/PRODUCT_CONCEPT.md`.

The public project README is deliberately shorter than the engineering record. It should remain understandable to a reviewer who has no prior knowledge of Masck One.

## Evidence vocabulary

| State | Meaning |
| --- | --- |
| `MUST_BUILD` | Required by the selected product architecture |
| `SHOULD_BUILD` | Strongly preferred but not yet release-critical |
| `OPTIONAL` | Exploratory or non-essential capability |
| `BLOCKED` | A dependency prevents credible implementation or promotion |
| `FORBIDDEN_CLAIM` | Must not be represented as achieved without new evidence |

These labels describe engineering or communication status. They do not replace physical validation.

## Public-facing product representation

Public material may describe Masck One as an early-stage wearable-and-dock concept exploring automated skincare routines. The complete-routine direction is a product vision, while the first use case still needs to be validated.

The public presentation should clearly distinguish:

- intended product behaviour from demonstrated capability;
- engineering CAD and concept renders from manufactured hardware;
- software or geometry checks from measured physical performance;
- open candidate work from the merged baseline;
- planned validation from completed validation.

## Product imagery

Existing renders can be used to communicate design direction when they are labelled as digital concept or engineering imagery. Do not present them as photographs of a manufactured product, production tooling or validated physical performance.

For scholarship and venture review, the root `README.md` uses existing repository renders with an explicit evidence disclaimer. Further imagery should only be added when it improves understanding rather than making the project appear more mature than it is.

## Product claim boundaries

Do not claim demonstrated comfort, fit, safety, hygiene, product compatibility, leakage performance, routine completion, removal performance, manufacturing readiness, unit economics or customer demand unless the repository contains appropriate current evidence.

A green CI run means that the tested digital contracts passed for that source state. It does not mean the physical product works.

## Retention, removal and companion software

Retention, whole-head removal, companion software and routine personalisation can be described as areas under development where supported by product-intent documents. They should not be phrased as finished features unless the relevant evidence state changes.

## Working process

When updating public-facing material:

1. Read the root `README.md` first so wording stays consistent with the public stage statement.
2. Verify the current engineering authority and relevant owner document.
3. State whether a point is merged baseline, candidate work, product intent or planned validation.
4. Keep Australian spelling consistent across public copy.
5. Prefer short factual explanations over internal workflow terminology.
6. Link technical claims to the smallest useful evidence source.
7. If evidence is missing, say so rather than filling the gap with inference.

The objective is a credible public record of progress, not a more polished version of uncertainty.
