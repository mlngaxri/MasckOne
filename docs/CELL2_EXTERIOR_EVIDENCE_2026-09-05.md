# Cell 2 exterior evidence, 2026-09-05

## Live source reconstruction

- Accepted base remains `main` `5fce2a43a34d8be49256677a35af60c906dc1653`, merge of PR #67 passive-waste-routing baseline repair.
- Legacy exterior PR #62 remains source material only and is not release authority.
- Released `src/masck_one/model.py` still carries the three-station ruled elliptical shell; PR #70 replaces only the integrated `rigid_shell` candidate.
- Current Cell 4 PR #68 has advanced to `f4d366ab4ee819cc6be79186c5cc77ef89519fa9`. Its commits after the previously screened `c9844b53630494066313424806809d56e185c53c` change verification only, not realized mixed-waste route geometry. Route A remains wearer-left/inferior and its full provisional envelope remains below the approximately Z 20.1 mm crown inner-material guard.
- Current Cell 3 PR #71 has advanced to `5ba496a0ac45ea30631aee869d25498eff6679a5`. Its changes after the previously screened release geometry add reset/export verification without enlarging the right-side withdrawal reservation. The reservation remains X [73.5, 100.0], Y [-5.0, 5.0], Z [-22.5, -15.5] mm and remains posterior-disjoint from Cell 2 shell material beginning at Z 0.
- No Cell 3, Cell 4, authority, protected-region, fluid, electrical or HMI source is edited by this Cell 2 pass.

## Implemented global proportion delta

The rigid exterior remains a deterministic five-station smooth non-ruled shell with a low-gradient compound anterior crown, but the side-body progression is no longer near-parallel.

Peak side mass now occurs at the interior Z 16 mm station and the visible anterior perimeter tapers again by Z 22 mm. Authored station scales are X `[1.000, 1.030, 1.045, 1.050, 1.015]` and Y `[0.991, 1.005, 1.019, 1.029, 1.004]` against the live functional-frame baseline. This carries depth into the temple, cheek and jaw volume rather than placing a shallow crown on a constant-depth plate.

The lower profile is broadened only through the cartridge band and includes an additional near-chin control point. That change keeps the jaw tapered while moving shell material outside the accepted cartridge envelope and avoiding the hard lower termination produced by the first package-clear candidate.

The existing 5.8 mm compound crown remains, including brow/upper-cheek lift, a recessive nasal valley and continuous lower-face curvature. Authority remains unchanged: the 172 x 210 mm outer XY envelope, shell wall baselines, eye aperture dimensions/cant, mouth aperture and nostril opening derivation are consumed from `config/masck_one_authority.yaml`.

## Actual B-rep inspection

CadQuery 2.8.0 reconstruction of the exact current algorithms was inspected in front, both three-quarter, both side, rear/wearer-side, top, bottom and center-section views.

| Digital metric | Reviewed head `ff809963...` | Current global-proportion candidate |
| --- | ---: | ---: |
| B-rep valid | yes | yes |
| Solid count | 1 | 1 |
| X span, mm | 160.958851 | 163.603323 |
| Y span, mm | 206.867077 | 208.060777 |
| Z span, mm | 27.570690 | 27.570579 |
| Visible anterior relief above Z 22, mm | 5.570690 | 5.570579 |
| Shell / accepted waste-cartridge intersection, mm3 | approximately 604.234 | 0.0 |

These are digital-kernel inspection values, not manufacturing tolerances or physical evidence.

The material side/top change is also visible in actual B-rep sections rather than only in authored scale values. At Z 16 mm the shell section spans approximately 163.450 x 208.056 mm. At Z 21.5 mm it spans approximately 158.861 x 203.893 mm, giving about 4.589 mm width taper and 4.163 mm height taper before the compound crown. The side and top projections therefore carry midbody fullness into a tapered anterior perimeter rather than retaining the prior near-parallel slab silhouette.

Front and three-quarter views preserve the broad upper field, tapered lower face and one continuous facial surface without pods, raised aperture rings, vents, decorative panels or exposed mechanisms. The final lower transition was visually rechecked after adding the near-chin control point so package clearance did not create a robotic chin cue.

`masck_one.exterior_evidence.render_exterior_view_evidence()` renders eight SVG projections and two center sections directly from the candidate B-rep and writes validity, volume, bounding box, projection directions, section specifications and exact file hashes. CI executes that renderer rather than relying on hand-drawn evidence.

## Package and geometry checks

Targeted regressions and exact-geometry inspection protect:

- peak side mass before the anterior station and a material anterior perimeter taper;
- containment inside the authority XY envelope;
- one valid positive-volume B-rep solid;
- bounded 5.2 to 6.4 mm visible crown relief;
- open centerlines through both eyes, both nostrils and the mouth across the checked Z range;
- absolute zero nontrivial shell intersection with the released 74 x 36 x 20 mm waste-cartridge envelope centered at `(0, -80, 8)` mm;
- crown separation from the current package Z envelopes;
- preservation of the accepted component set with only the rigid shell substituted;
- deterministic STEP export and deterministic multi-view/section generation.

The current control-net wall guard remains a development regression, not a production thickness certificate. Final-shell minimum-thickness proof remains a separate digital freeze gate and no production-process claim is made here.

## Evidence boundary

This is digital CAD exterior convergence only. It does not establish fit, comfort, facial seal, cleansing efficacy, liquid recovery, leakage, skin compatibility, chemical resistance, wet grip, stain resistance, scratch resistance, cleanability, production material, color match, tooling feasibility, dimensional process capability or physical durability.

## DIGITAL_HANDOFF_DELTA

If released, future product depiction should use the broad-upper-field, tapered-jaw shell with midbody depth and a tapered compound anterior perimeter rather than the released generic oval/flat-face candidate. No performance or CMF claim boundary changes.
