# MASCK ONE Core Sketch Feature Matrix

Status: **feature inventory derived from Core Sketch v1**  
Date: 2026-09-10

This matrix exists so product/design/engineering work can quickly see what belongs in the stable concept, what is conditional, and what is rejected. Detailed acceptance criteria live in `CORE_SKETCH_EXECUTION_BACKLOG.md`.

| Feature / behavior | Tier | Concept state | Required for V1 identity? | Primary proof |
|---|---|---:|---:|---|
| Complete supported facial routine in one wear session | A | LOCKED | Yes | BENCH + HUMAN |
| No required manual facial finish after normal completion | A | LOCKED | Yes | BENCH + HUMAN |
| Cleanse | A | SELECTED | Yes | BENCH + HUMAN |
| Fresh-water rinse / spent-fluid recovery | A | SELECTED | Yes | BENCH |
| Leave-on serum/treatment application | A | SELECTED | Yes | BENCH + HUMAN |
| Moisturizer application | A | SELECTED | Yes | BENCH + HUMAN |
| Non-wiping transition/release | A | SELECTED | Yes | BENCH + HUMAN |
| User’s own skincare products | A | LOCKED | Yes | Product coverage + BENCH |
| Dock-held bulk products | A | LOCKED | Yes | DIGITAL + BENCH |
| On-head session quantities only | A | LOCKED | Yes | DIGITAL + BENCH |
| Grab → place → self-align → start → remove → return | A | LOCKED | Yes | HUMAN |
| Calm rigid/semi-rigid premium facial object | A | LOCKED | Yes | ID review + HUMAN |
| Large clean eye openings | A | LOCKED | Yes | DIGITAL + HUMAN |
| Real airway / protected anatomy | A | engineering-controlled | Yes | DIGITAL + BENCH/HUMAN |
| Offline normal operation | A | LOCKED | Yes | SOFTWARE + BENCH |
| Physical emergency release | A | LOCKED | Yes | BENCH + HUMAN |
| Inspectable hygienic facial interface | A | SELECTED | Yes | BENCH + HUMAN |
| Scheduled AM/PM/day routines | B | SELECTED | Strongly yes | SOFTWARE + HUMAN |
| Today-only routine overrides | B | SELECTED | Yes | SOFTWARE + HUMAN |
| Product barcode/QR identification | B | EXPLORE | Supporting | SOFTWARE/data |
| Label/OCR/manual product identification | B | EXPLORE | Supporting | SOFTWARE/data |
| KNOWN / CHARACTERISED / VALIDATED / RESTRICTED states | B | LOCKED | Yes for compatibility system | DOC + SOFTWARE |
| Physical product-behavior calibration/check | B | PROVE | Yes for broad compatibility | BENCH |
| Community-assisted product characterization | C | SELECTED with opt-in | No | PRIVACY + data quality |
| AI product identification/orchestration | B | SELECTED/bounded | No for offline cached use | SOFTWARE/evidence |
| Deterministic dose/compatibility/safety bounds | A | LOCKED | Yes | SOFTWARE + BENCH |
| Product reformulation detection | B | EXPLORE | Important | SOFTWARE + BENCH |
| Massage / physical treatment | B | SELECTED optional stage | No for existential first proof | BENCH + HUMAN |
| Deliberate WARM | B | SELECTED optional stage | No for existential first proof | BENCH + HUMAN |
| Deliberate COOL | B | EXPLORE optional stage | No | BENCH + HUMAN |
| Red / NIR optical treatment | B | SELECTED subject to claims proof | No for existential first proof | OPTICAL + safety |
| Deep-NIR ~1072 nm benchmark | B | EXPLORE | No | Evidence + optical proof |
| Facial SPF application | B | TARGET / high-rigor PROVE | Strong strategic target | REG/CLAIM + BENCH |
| Travel module compatibility | C | EXPLORE | No | Concept/packaging |
| Compact premium home dock | A/B | SELECTED | Yes | ID + packaging + HUMAN |
| Automatic dock service/preparation | B | SELECTED | Yes | BENCH |
| Quiet Opal-neutral status grammar | B | SELECTED | Yes | HUMAN |
| Minimal haptics | C | SELECTED | Supporting | HUMAN |
| Routine completion sound | C | optional, likely off-by-default | No | HUMAN |
| App history | C | SELECTED | No | SOFTWARE |
| Product depletion forecasting | C | SELECTED if evidence supports precision | No | BENCH/SOFTWARE |
| User-controlled telemetry contribution | C | SELECTED opt-in | No | PRIVACY |
| Makeup removal | — | REJECTED for V1 | No | — |
| Proprietary MASCK skincare requirement | — | REJECTED | No | — |
| VR-style halo / rear counterweight pod | — | REJECTED | No | — |
| Flexible silicone LED-mask archetype | — | REJECTED | No | — |
| RGB status bars | — | REJECTED | No | — |
| Talking mask / voice assistant | — | REJECTED | No | — |
| Beauty/pore/acne scoring by default | — | REJECTED | No | — |
| UV sanitation as marketing theater | — | REJECTED | No | — |
| Decorative vents/panelization | — | REJECTED | No | — |
| Visible product plumbing | — | REJECTED | No | — |
| Direct aerosol sunscreen as default | — | REJECTED | No | — |
| Extra-dose hardware buttons | — | REJECTED | No | — |

## Reading rule

A `SELECTED` feature is still subject to engineering feasibility and physical validation. `LOCKED` means the product intent should survive refinement, not that the underlying implementation is already solved.
