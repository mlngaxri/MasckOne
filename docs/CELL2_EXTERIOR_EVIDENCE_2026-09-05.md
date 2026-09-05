# Cell 2 exterior evidence, 2026-09-05

## Live source reconstruction

- Accepted base at branch creation: `main` `5fce2a43a34d8be49256677a35af60c906dc1653`, merge of PR #67 passive-waste-routing baseline repair.
- Legacy exterior PR #62 remains open and stale. It was treated only as a source candidate.
- Current released `src/masck_one/model.py` still uses a three-station ruled elliptical shell that grows to the 172 x 210 mm outer envelope.
- This Cell 2 branch does not edit Cell 3 mechanism/retention work, Cell 4 routing work, power/electronics/HMI branches, authority, protected-region definitions or fluid geometry.

## Implemented geometry delta

The rigid exterior candidate is rebuilt as a five-station smooth non-ruled spline loft. The upper field remains broad while the lower side mass, jaw and chin taper continuously. The late generic elliptical flare is removed. The wearer-side cavity remains open and the anterior cavity terminates one nominal wall behind the visible field so the protected apertures cut real openings.

Authority remains unchanged: outer XY envelope, nominal shell wall, eye aperture dimensions/cant, mouth aperture dimensions and nostril minimum opening derivation are consumed from `config/masck_one_authority.yaml`.

The integration layer substitutes only `rigid_shell` into the current accepted product model. Every other component and topology remains current-main geometry.

## Before / after digital B-rep inspection

A local CadQuery 2.8.0 reconstruction of the exact released and candidate shell algorithms was built and inspected before release work.

| Digital metric | Released ruled shell | Cell 2 candidate |
| --- | ---: | ---: |
| B-rep valid | yes | yes |
| X span, mm | 172.0000002 | 160.9588512 |
| Y span, mm | 210.0000002 | 206.8670772 |
| Z span, mm | 22.0000002 | 22.0000002 |
| Solid volume, mm3 | 62994.6253 | 66701.3596 |

These are kernel inspection values, not manufacturing tolerances or physical evidence.

Actual B-rep projections were inspected in near-front, both three-quarter, side, rear/wearer-side and top views. The largest removed prototype cue is the released generic oval/late-flare silhouette. The candidate reads as a broader upper facial field with controlled lower taper and no added pod, vent, panel or decorative mechanism language. The remaining largest exterior cue is the broadly planar anterior field; package-aware shallow facial curvature remains a later bounded Cell 2 surface pass rather than being faked before package/service closure.

`masck_one.exterior_evidence.render_exterior_view_evidence()` renders eight SVG projections directly from the candidate B-rep and writes a manifest with validity, volume, bounding box and exact projection directions. CI regressions execute this renderer rather than relying on hand-drawn evidence.

## Geometry and release guards

Targeted regressions protect:

- monotonic smooth station progression;
- authority-envelope containment;
- valid positive-volume B-rep generation;
- retained anterior facial field with two eyes, two nostrils and one mouth opening;
- preservation of the accepted component set with only the rigid shell substituted;
- material geometric difference from the released ruled shell;
- candidate STEP export through the normal release exporter;
- deterministic generation of eight actual B-rep SVG evidence views.

## Evidence boundary

This is digital CAD exterior convergence only. It does not establish fit, comfort, facial seal, cleansing efficacy, liquid recovery, leakage, skin compatibility, chemical resistance, wet grip, stain resistance, scratch resistance, cleanability, production material, color match, tooling feasibility, dimensional process capability or physical durability.

## DIGITAL_HANDOFF_DELTA

Future product renders should no longer depict the released full-envelope generic oval / late rear flare as the preferred exterior. Use the Cell 2 broad-upper-field, tapered-jaw, soft-chin silhouette only after this branch is released. No new performance or CMF claim is enabled by this geometry change.
