# Iteration 16 acceptance: exterior engineering surface and Class-A reference workflow

## Scope

Iteration 16 adds the controlled comparison workflow between future engineering exterior-surface samples and a future authored/released Class-A reference. It does not author the industrial-design surface itself and does not claim manufacturing, cosmetic, tactile or physical validation.

## Authority consumed

- `manufacturing.a_surface.rms_deviation_max_mm = 0.25`
- `manufacturing.a_surface.max_deviation_mm = 0.75`
- existing `CAD_CLOSURE` status is preserved.

## Implemented contract

- stable sample IDs with exact one-to-one pairing;
- duplicate, empty, mismatched and non-finite sample data rejection;
- deterministic RMS and maximum Euclidean deviation calculation;
- explicit released-source asset SHA-256, surface ID, reference revision and release status;
- a second SHA-256 that binds release eligibility to the exact canonical reference-sample manifest used by the numeric comparison;
- a deterministic release-record SHA-256 that binds surface ID, revision, source-asset identity, reference-sample identity and release status into one auditable released-reference identity;
- deviation reports record the exact engineering-sample manifest, reference-sample manifest, source-asset SHA-256, released surface ID/revision and release-record SHA-256 used to produce the result;
- canonical sample manifests use sorted sample IDs, millimetre coordinates and exact `float.hex()` coordinate serialization, with signed zero normalized because `+0.0` and `-0.0` are geometrically identical;
- released SHA-256 values must use canonical lowercase hexadecimal form;
- substituted or stale reference samples are rejected even when sample IDs and other release metadata otherwise look valid;
- numerical pass without a released reference remains blocked;
- numerical failure remains failure even if a reference is released;
- physical-validation eligibility is explicitly false.

## Provenance boundary

The source CAD asset and its comparison-sample derivative are separate controlled identities. `source_asset_sha256` identifies the released source artifact. `reference_sample_manifest_sha256` identifies the exact derivative samples accepted by this workflow. `release_record_sha256` identifies the complete released-reference record containing both identities plus the surface ID, revision and release state. The evaluator independently recomputes the sample-manifest hash and refuses release-level CAD closure when the supplied samples do not match that recorded manifest.

The resulting `SurfaceDeviationReport` also carries the engineering-sample manifest. A downstream consumer can therefore determine exactly which engineering sample set was compared against exactly which released-reference record instead of receiving only numeric RMS/max values detached from their inputs.

This prevents a released metadata record for surface A from being combined with numerically convenient or stale samples from surface B, and prevents a valid numeric report from losing its source/revision identity when passed downstream. It does not yet prove how the derivative samples were generated from the source CAD asset. A future controlled sampler/export workflow should bind that transformation when real Class-A authoring is introduced.

## Evidence boundary

This iteration does not establish a Class-A surface, appearance quality, toolability, mold fidelity, texture, gloss, seam perception, manufacturability or physical dimensional capability. A future released reference must be authored, revision-controlled and hashed before the CAD-closure status can become eligible. Manufacturing evidence remains separate.

## Verification

Run:

```bash
python -m masck_one.surface_workflow_preflight
python -m pytest
python -m masck_one.cli --output generated
```

The adversarial suite includes same-ID/different-geometry substitution, single-coordinate stale-derivative mutation, duplicate/mismatched IDs, invalid/noncanonical hashes, non-finite coordinates, release-record mutation, engineering-input traceability and attempted physical-evidence promotion.

Promotion requires exact-head GitHub CI success.
