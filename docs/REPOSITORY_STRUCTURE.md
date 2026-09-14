# Repository structure

[Project overview](../README.md) · [Documentation index](README.md)

## Directory map

| Location | Role |
| --- | --- |
| `config/`, `schemas/` | Controlled parameters and contracts |
| `src/masck_one/`, `tests/` | Engineering implementation and verification |
| `generated/` | Generated outputs retained with their evidence context |
| `docs/` | Product rationale, subsystem specifications, planning and evidence records |
| `studies/` | Bounded engineering investigations |
| `website/`, `brand/` | Presentation source and identity assets |
| `.github/workflows/` | Engineering checks and website automation |
| `.site-build/` | Retained website construction scripts and input assets; see its [index](../.site-build/README.md) |

Detailed engineering files retain stable paths because contracts, historical records and active branches refer to them. Public reading order is provided by the documentation index rather than by moving those sources.

Masck One carries two deliberately separate source-of-truth layers:

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

## Development workstream responsibilities

The five scheduled engineering workstreams consume the brand contract as follows. These labels describe AI-assisted development responsibilities, not employees:

- Mechanical: preserve user-facing tactile quality, package thinness and quiet reaction paths while solving actual mechanics.
- Exterior: own surface-language, no-goggle enforcement, control placement and visible CMF integration.
- Wet-Dry: own the real sealed HMI/optical package and keep M-Cut behavior compatible with wet/dry architecture.
- Manufacturing: own tactile/visible CTQs, process feasibility, part-count and cost-pressure closure.
- Integration: own canonical consumption of the brand manifest and reject competing brand/palette/control truths.

These responsibilities keep product identity connected to engineering decisions. The current whole-product work is routed through the [engineering work queue](CORE_SKETCH_START_HERE.md); this list describes how the brand contract is consumed.
