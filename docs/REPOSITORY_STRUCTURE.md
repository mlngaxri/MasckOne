# Repository structure

Masck One now carries two deliberately separate source-of-truth layers:

## 1. Engineering authority

`config/masck_one_authority.yaml`

Owns engineering dimensions, coordinate conventions, protected regions, performance targets and validation-gated requirements.

Supporting code and contracts remain under:

- `src/masck_one/`
- `schemas/`
- `tests/`
- `generated/`

Do not move mature engineering modules simply to make the tree look cleaner. Source stability and deterministic import paths are more important than cosmetic folder churn.

## 2. Brand and product identity authority

`config/masck_brand_authority.yaml`

Owns parent/product naming, master-mark role, product designation role, interaction-language intent, CMF direction, anti-goggle exterior language and cost-discipline principles.

Supporting brand sources are under:

- `brand/assets/` for editable vector identity studies;
- `docs/BRAND_ARCHITECTURE.md` for human design rationale;
- `src/masck_one/brand_identity.py` for strict machine consumption;
- `tests/test_brand_identity.py` for hostile identity regressions;
- `generated/brand_identity.json` for deterministic release evidence.

## Precedence

Engineering authority always wins where safety, geometry, protected anatomy, physical validation, thermal/electrical/wet-dry boundaries or actual manufacturability conflict with brand intent.

Brand authority should still actively constrain user-facing work. A technically valid exterior that becomes goggle-like, visually tactical, needlessly noisy, over-branded or mechanically cheap should be treated as a design regression rather than accepted simply because it passes geometric checks.

## Product ownership

The repository remains the engineering repository for **Masck One**. It is not being turned into a speculative monorepo for every hypothetical future MASCK product.

The broader parent brand is represented so that Masck One does not accidentally hard-code the company identity to its first form factor. Future products should get separate repositories or clearly separated packages only when they actually exist.

## Scheduled builder ownership

The five scheduled builders should consume the brand contract as follows:

- Mechanical: preserve user-facing tactile quality, package thinness and quiet reaction paths while solving actual mechanics.
- Exterior: own surface-language, no-goggle enforcement, control placement and visible CMF integration.
- Wet-Dry: own the real sealed HMI/optical package and keep M-Cut behavior compatible with wet/dry architecture.
- Manufacturing: own tactile/visible CTQs, process feasibility, part-count and cost-pressure closure.
- Integration: own canonical consumption of the brand manifest and reject competing brand/palette/control truths.

This division keeps the brand physically embedded without creating a sixth builder lane that only writes style documents.
