# Masck One facial-reference and landmark contract

## Scope

Phase 1 / Iteration 4 creates the first semantic facial-reference layer used by Masck One engineering code.

It is intentionally conservative: it converts only facial landmark coordinates that already exist in the machine authority into typed, named, traceable objects. It does **not** invent a 3D human face, nose shape, eye depth, mouth depth, cheek curvature, bridge height, facial width distribution, or population-fit claim.

## Why this layer exists

Before this iteration, eye, nostril and mouth coordinates were numerical arrays consumed directly by CAD code. The coordinates were already authority-controlled, but they were not yet represented as anatomical entities with stable IDs, provenance, side classification and explicit limitations.

That creates several long-term risks:

- a later subsystem could use a coordinate without knowing whether it represented an eye center, aperture center or anatomical landmark;
- a left/right coordinate could be swapped silently;
- a 2D authority projection could be mistaken for a resolved 3D point;
- duplicated derived distances could drift from the source points;
- headform registration could overwrite rather than augment the original CAD baseline;
- asymmetric measured faces could be forced incorrectly into a symmetric baseline assumption.

Iteration 4 removes those ambiguities before a real facial surface is introduced.

## Current landmark set

The current authority supports exactly five neutral 2D landmark projections:

- `MASCK_ONE-LMK-EYE-LEFT-CENTER`
- `MASCK_ONE-LMK-EYE-RIGHT-CENTER`
- `MASCK_ONE-LMK-NOSTRIL-LEFT-CENTER`
- `MASCK_ONE-LMK-NOSTRIL-RIGHT-CENTER`
- `MASCK_ONE-LMK-MOUTH-CENTER`

Their source paths are preserved in each object.

No additional facial landmark is created merely because it would be convenient for modeling.

## Current coordinates

The landmark layer reads its values directly from the machine authority at runtime.

The current authority revision resolves the planar coordinates as:

| Landmark | X mm | Y mm | Authority status |
|---|---:|---:|---|
| left eye center reference | -31.5 | 35.0 | CAD_BASELINE |
| right eye center reference | 31.5 | 35.0 | CAD_BASELINE |
| left nostril center reference | -10.5 | -7.5 | CAD_BASELINE |
| right nostril center reference | 10.5 | -7.5 | CAD_BASELINE |
| mouth center reference | 0.0 | -50.0 | CAD_BASELINE |

This table is explanatory documentation only. The code does not treat the table as an independent source of truth.

## 2D does not mean Z = 0 anatomy

This is the most important rule in Iteration 4.

The current landmark coordinates are represented as `Point2` values in canonical X/Y coordinates because the authority does not specify their physical 3D depth on a human face.

Therefore:

- `(-31.5, 35.0)` is an authority-controlled eye-center projection;
- it is **not** automatically `(-31.5, 35.0, 0.0)` on a physical face;
- `Z = 0` may be used explicitly for visualization/debug datum graphics, but that projected point remains marked as unresolved in 3D;
- future headform/surface registration must resolve Z from an identified source surface rather than silently assuming zero.

All five current landmarks report unresolved 3D depth.

## Bilateral baseline symmetry

The current neutral CAD baseline is symmetric for the eye-center and nostril-center pairs.

The Iteration-4 bilateral pair type therefore verifies:

- left landmark has negative X;
- right landmark has positive X;
- both have the same Y;
- sagittal mirroring of the left planar point equals the right planar point;
- pair metadata identifies both landmarks as belonging to the same bilateral group.

This validation applies only to the neutral CAD baseline. It does **not** claim that real human faces are symmetric.

When asymmetric scanned/headform data are introduced, those data must be represented separately rather than altered to satisfy this baseline symmetry helper.

## Midline classification

The mouth-center reference is explicitly classified as a midline landmark and must satisfy `X = 0` in the neutral baseline.

Future bridge, philtrum, chin or other midline landmarks may be added only when they have an explicit engineering source/status.

## Derived neutral metrics

Several useful dimensions are calculated directly from the current landmark coordinates:

- eye-center spacing: `63.0 mm`
- nostril-center spacing: `21.0 mm`
- eye line Y: `35.0 mm`
- nostril line Y: `-7.5 mm`
- mouth-center Y: `-50.0 mm`
- eye-to-nostril vertical separation: `42.5 mm`
- nostril-to-mouth vertical separation: `42.5 mm`
- eye-to-mouth vertical separation: `85.0 mm`

These are **derived values**, not independent requirements. They must never be copied into the machine authority as separate frozen numbers unless a future authority revision deliberately promotes them.

If a source landmark changes under formal engineering change control, these metrics update automatically.

## Stable semantic IDs

Landmark IDs are designed to remain stable when geometry implementations change.

For example, a future headform registration may resolve the left-eye reference to a 3D point on a reference surface. That should not create an unrelated new meaning for the ID.

Where the meaning itself changes—for example from visual-aperture center reference to a different anatomical feature—a new ID must be created rather than silently reusing the old one.

## Source provenance

Each landmark contains:

- stable landmark ID;
- anatomical/engineering description;
- typed planar coordinate;
- authority status;
- exact authority source path;
- side classification;
- bilateral-group metadata where applicable.

The complete facial-reference layer also records the authority revision from which it was built.

## Integration with the model

Every generated `MasckOneModel` now contains:

`model.facial_reference`

This means later subsystems can depend on one semantic facial-reference object rather than reopening raw authority paths independently.

Existing shell/aperture geometry is intentionally unchanged in Iteration 4. The model integration adds semantic structure, not a redesign.

## Failure behavior

The facial-reference layer rejects:

- empty landmark IDs;
- missing anatomical names;
- missing authority status;
- missing source provenance;
- unsupported side labels;
- left landmarks with non-negative X;
- right landmarks with non-positive X;
- midline landmarks off X = 0;
- duplicated landmark IDs;
- incorrectly assembled bilateral pairs;
- neutral baseline pairs that fail current sagittal symmetry.

These failures are tested.

## What remains unresolved

Iteration 4 deliberately leaves the following unresolved:

- 3D depth of all current facial landmarks;
- reference face/headform surface;
- eye corners and dynamic eyelid geometry;
- nasal bridge/dorsum/tip/alar-surface landmarks;
- philtrum geometry;
- mouth corners and dynamic lip/jaw geometry;
- forehead, cheek, chin and jaw landmarks;
- population distribution;
- facial asymmetry;
- expression states;
- headform-to-global registration;
- skin-contact surface normals;
- geodesic distances over a real face surface.

These are later roadmap items and must not be filled with visually plausible guesses.

## Next dependency

Iteration 5 can now implement the **headform/reference-surface ingestion and registration contract**.

That iteration should define how an external mesh/STEP/scan declares source units, handedness, axes, revision/hash and rigid transform into `MASCK_ONE_GLOBAL`, while preserving the planar authority landmarks as the original design baseline.
