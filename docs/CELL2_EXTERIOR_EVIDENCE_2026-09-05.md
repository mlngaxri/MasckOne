# Cell 2 exterior evidence, 2026-09-05

## Live source reconstruction

- Accepted base is `main` `628ec5f5766937433b1bdf8f30edc372924cf41e`, including released PR #68 mixed-waste backbone geometry.
- Legacy exterior PR #62 remains source material only and is not release authority.
- Cell 2 owns the current PR #70 rigid-shell candidate only. No Cell 3, Cell 4, authority, protected-region, fluid, electrical or HMI source is edited by this pass.
- Current Cell 3 PR #71 release/reset geometry remains posterior to Cell 2 shell material beginning at Z 0. Its exact latch sweep remains within X `[73.5,100.0]`, Y `[-5.0,5.0]`, Z `[-22.5,-15.5]` mm, with reset keepout extending only to approximately Z `-13.0` mm.
- Current Cell 4 cleanser candidate PR #80 remains non-authoritative. Its material envelope ends at Z 16 mm while the Cell 2 crown inner-material guard remains approximately Z 20.1 mm.
- Exterior evidence uses canonical external frame ID `MASCK_ONE_AUTHORITY_WORLD_MM`, matching the frozen +X wearer-right, +Y superior, +Z anterior authority basis.

## Implemented exterior geometry

The rigid exterior is a deterministic five-station smooth non-ruled shell with a low-gradient compound anterior crown. Peak side mass occurs at the interior Z 16 mm station and the visible anterior perimeter tapers again by Z 22 mm. Authored station scales remain X `[1.000, 1.030, 1.045, 1.050, 1.015]` and Y `[0.991, 1.005, 1.019, 1.029, 1.004]` against the authority functional-frame baseline.

The lower face remains deliberately neutral. A broad shallow mouth/philtrum recession and separate chin softening suppress a centered muzzle or robotic-chin cue without changing the authority mouth aperture.

The superior field now removes the previous localized visor-like brow ridge. The former broad horizontal brow lift is replaced by a small two-dimensional brow transition plus a broad forehead-continuity field. The central nasal valley decays more gradually into this superior field, and an additional superior control row extends interpolation into the forehead region. No visor seam, panel edge, bezel, vent or extra visible part is introduced.

Authority remains unchanged: outer XY envelope 172 x 210 mm, shell nominal wall 1.8 mm with 1.5 mm absolute development minimum, eye aperture 46 x 30 mm with 4 degree cant, mouth aperture 58 x 32 mm, and the current nostril opening derivation.

## Actual B-rep inspection

CadQuery reconstruction of the current superior candidate gives one valid solid at approximately 163.603323 x 208.060777 x 27.206243 mm. The XY span is unchanged from the prior accepted Cell 2 proportion pass and remains inside the authority 172 x 210 mm envelope. Shell intersection with the released 74 x 36 x 20 mm waste-cartridge envelope centered at `(0,-80,8)` is 0.0 mm3.

The centerline superior control field changes materially without increasing the upper package envelope. At normalized Y 0.12, the local brow ridge above the interpolation of neighboring Y 0.00 and Y 0.24 controls decreases from approximately 0.805 mm to approximately 0.378 mm. The superior centerline drop from Y 0.12 to Y 0.36 decreases from approximately 2.847 mm to approximately 2.076 mm. Visible crown relief is approximately 5.206 mm above the Z 22 side-body station and therefore remains inside the existing 5.2 to 6.4 mm digital guard.

Front, both three-quarter, both side, rear/wearer-side, top, bottom and center YZ/XZ evidence is generated directly from the B-rep. The superior change reads as a continuous forehead-to-brow surface rather than a local brow ledge while retaining the global silhouette and all protected-aperture centers and sizes.

## Package and geometry checks

Targeted regressions protect:

- peak side mass before the anterior station and material anterior-perimeter taper;
- authority XY containment and one valid positive-volume B-rep solid;
- bounded crown relief;
- protected eye, nostril and mouth centerlines;
- zero shell intersection with the released waste-cartridge envelope;
- lower-face neutrality limits;
- superior brow-ridge and forehead-continuity limits;
- superior control reach into the forehead transition zone;
- canonical `MASCK_ONE_AUTHORITY_WORLD_MM` evidence-frame identity;
- deterministic multi-view and center-section generation.

The current digital wall checks are development regressions, not a production thickness certificate. Fit, comfort, seal, cleanability and material/process validation remain physical or downstream digital gates.

## Evidence boundary

This is digital CAD exterior convergence only. It does not establish fit, comfort, facial seal, cleansing efficacy, liquid recovery, leakage, skin compatibility, chemical resistance, wet grip, stain resistance, scratch resistance, cleanability, production material, color match, tooling feasibility, dimensional process capability or physical durability.

## DIGITAL_HANDOFF_DELTA

If released, future physical depiction should use the continuous forehead-to-brow surface, tapered midbody and neutral lower-face field of the exact released shell. No performance or CMF claim boundary changes.
