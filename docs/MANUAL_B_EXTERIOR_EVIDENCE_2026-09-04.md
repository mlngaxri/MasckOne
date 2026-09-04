# Manual B exterior evidence, 2026-09-04

## Source state

- Base: live `main` at `2348fd74e63870f707bb8ce7a9f96a0c4d83d916`.
- Candidate branch: `manual-b/exterior-mvp-convergence-20260904`.
- Exterior schema: `MASCK_ONE_EXTERIOR_SURFACE_V3`.
- Multi-view projection: `docs/generated/manual_b_exterior_multiview.svg`.
- Evidence class: digital CAD convergence only. This is not fit, comfort, seal, cleanability, CMF durability, manufacturing or physical-validation evidence.

## What changed from the released baseline

The released `model.py` shell is a three-station ruled loft. The current Manual B candidate uses five controlled Z stations and a mirrored spline perimeter. It keeps the temple and upper facial field broad, narrows the jaw and softens the chin, while keeping the complete spline inside the authoritative 172 x 210 mm XY envelope.

A defect in the stale PR #59 exterior candidate was also removed. Its inner loft reached the same anterior station as the outer loft, which opened most of the intended frontal field. The corrected candidate terminates the anterior inner cavity one nominal shell wall behind the outer face. The result is a real broad facial field with five actual protected apertures, rather than a perimeter shell whose aperture cuts are mostly ineffective.

## Current visual read

Front: the perimeter is calmer and less generic than the baseline ellipse. The temples remain broad, the sidewalls transition into a narrower jaw, and the chin is soft rather than pointed. The eye apertures remain authority-sized and neutrally canted. No decorative vents, cheek holes, tactical panels or side pods were added.

Three-quarter: depth growth is gradual across five stations instead of a late rear flare. The side mass remains close to the main facial field and does not form an attached pod. The candidate is still intentionally simple because current PCB, charging and thermal hardware envelopes are unresolved.

Side: total shell depth remains compact and the transition is monotonic. No large rear brick or side canister is encoded into the exterior candidate.

Rear: the wearer-side opening remains available for the compliant interface and internal packages. Final rear service mass must be added only after fluid, electronics and service envelopes are bound, and it must remain within the frontal silhouette where practicable.

## Remaining visual defects and next geometry actions

1. The anterior facial field is still broadly planar. It is acceptable as a robust MVP surface candidate, but it is the largest remaining source of a flat product read. The next surface pass should introduce shallow package-aware curvature without reducing wall thickness, protected apertures or internal clearance.
2. The two nostril openings remain visually discrete in wireframe. The final nasal treatment needs a shallow recessive blend so the airway reads as part of one facial field rather than as a respirator intake. The 120 mm2 minimum area and 8 mm local opening cannot be reduced for styling.
3. The mouth aperture is authority-sized and visually prominent in line view. The surrounding lower-face surface and CMF hierarchy should reduce the impression of a separate mouth ring without shrinking the protected opening.
4. The current evidence view shows only the owned shell, not final side and rear package fairings. PCB, charging connector, WARM and COOL hardware envelopes remain deliberately unresolved. No cosmetic fake pods have been added to conceal that uncertainty.
5. Physical HMI placement is reserved on the wearer-right upper-side turnover, outside the primary frontal highlight and wet service grip. Visible switch, LED and sealing geometry remain open until the actual stack is selected.
6. CMF is resolved at hierarchy level, not production material level: light warm-neutral low-satin rigid shell, recessive low-gloss soft interface, quiet matte low-contrast retention and one restrained cool HMI accent. Physical stain, fingerprint, scratch, cleaning and durability evidence remains required.

## Manual A boundary

This candidate does not modify retention, quick release, actuator mounts or coupling, reaction structure, assembly strategy, DFM, tolerance CTQs or final mechanical integration. Those remain Manual A ownership.
