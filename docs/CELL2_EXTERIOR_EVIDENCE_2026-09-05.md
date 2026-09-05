# Cell 2 exterior evidence, 2026-09-05

## Live source reconstruction

- Accepted base at branch creation and at this increment: `main` `5fce2a43a34d8be49256677a35af60c906dc1653`, merge of PR #67 passive-waste-routing baseline repair.
- Legacy exterior PR #62 remains source material only and is not release authority.
- Current released `src/masck_one/model.py` still uses the three-station ruled elliptical shell; this branch replaces only the integrated `rigid_shell` candidate.
- Current Cell 4 realized mixed-waste routing remains wearer-left/inferior, approximately X -62 to -24, Y -82 to -32, Z 12 to 16 mm. The new exterior crown begins conservatively at approximately Z 20.1 mm on the inner side, so this anterior-only form increment does not wrap around that route reservation.
- Current Cell 3 right quick-release latch remains rearward on the wearer-right side, with its release-critical solids around negative Z. This Cell 2 increment does not alter rear or retention geometry.
- No Cell 3, Cell 4, authority, protected-region, fluid, electrical or HMI source is edited here.

## Implemented geometry delta

The rigid exterior remains a five-station smooth non-ruled spline loft with the accepted broad upper field, continuously tapered jaw and soft chin. The anterior closure is now a broader low-gradient compound crown rather than a shallow faceplate-like field.

The bounded crown change increases authored base height from 4.8 mm to 5.8 mm, broadens its normalized radial field to 0.525 X and 0.520 Y, and reduces falloff power to 1.15. The existing landmark-driven brow/upper-cheek lift, recessive nasal valley and lower-face continuity remain. Nasal recession and lower-face lift are adjusted only within that same anterior field. No outer XY station, protected aperture, wearer-side cavity, rear mass or service boundary is enlarged.

Authority remains unchanged: outer XY envelope, nominal shell wall, eye aperture dimensions/cant, mouth aperture dimensions and nostril minimum opening derivation are consumed from `config/masck_one_authority.yaml`.

## Before / after digital B-rep inspection

Local CadQuery 2.8.0 reconstruction of the exact branch algorithms was generated and visually inspected in front, both three-quarter, both side, rear/wearer-side, top, bottom, center YZ and center XZ views.

| Digital metric | Released ruled shell | Previous Cell 2 compound crown | Current broader crown |
| --- | ---: | ---: | ---: |
| B-rep valid | yes | yes | yes |
| X span, mm | 172.0000002 | 160.9588512 | 160.9588512 |
| Y span, mm | 210.0000002 | 206.8670772 | 206.8670772 |
| Z span, mm | 22.0000002 | 26.552549 | 27.570690 |

These are kernel inspection values, not manufacturing tolerances or physical evidence.

The released generic oval/late-flare cue remains removed. Compared with the previous compound-crown head, the current change adds roughly 1.02 mm of visible Z relief without increasing the XY silhouette. Side and top projections show a broader, lower-gradient facial volume instead of a near-slab profile. Front and three-quarter views retain one continuous facial field, with no pod, raised aperture ring, vent, panel or mechanism-display language added.

The remaining form is intentionally shallow and recessive around the nasal openings. The digital result does not establish facial fit, seal, comfort or cleansing performance.

`masck_one.exterior_evidence.render_exterior_view_evidence()` renders eight SVG projections and two center sections directly from the candidate B-rep and writes a manifest with validity, volume, bounding box, projection directions, section specifications and exact file hashes. CI regressions execute this renderer rather than relying on hand-drawn evidence.

## Geometry and release guards

Targeted regressions protect:

- monotonic smooth station progression;
- authority-envelope containment with unchanged X/Y silhouette controls;
- valid positive-volume single-solid B-rep generation;
- a bounded 5.2 to 6.4 mm visible anterior-relief corridor so the face cannot regress toward a slab or grow into an excessive dome;
- retained openings through both eyes, both nostrils and the mouth;
- conservative anterior separation from the current accepted actuator, water, waste-cartridge and battery package envelopes;
- preservation of the accepted component set with only the rigid shell substituted;
- material geometric difference from the released ruled shell;
- candidate STEP export through the normal release exporter;
- deterministic generation of eight B-rep SVG projections plus center YZ/XZ sections.

## Evidence boundary

This is digital CAD exterior convergence only. It does not establish fit, comfort, facial seal, cleansing efficacy, liquid recovery, leakage, skin compatibility, chemical resistance, wet grip, stain resistance, scratch resistance, cleanability, production material, color match, tooling feasibility, dimensional process capability or physical durability.

## DIGITAL_HANDOFF_DELTA

If this branch is released, future product depiction should use the broad-upper-field, tapered-jaw, soft-chin silhouette with the shallow compound anterior facial crown rather than the released generic oval/flat-face candidate. No performance or CMF claim boundary changes.
