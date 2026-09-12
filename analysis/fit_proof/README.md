# Adversarial fit proof

**Decision: D, DIGITAL INDETERMINATE.** This isolated analysis does not change any
production part, authority, Core Sketch, owner binding, resource ledger or CI.
PR #157's CS018/bench work remains separate and preserved. PR #158 owns this proof.

## What is actually available

Original main `17f7d02c6178af8d33e4dfefb5043b497684ddb3`, geometrically unchanged
at analyzed main `3ccd9128810e6a6f4d01d57067be777345aa1484`, supplies a planar reference mesh,
projected landmarks, protected footprints and a rigid shell. It does not supply
registered anatomical depth, a qualified accommodation envelope, or a passive
alignment/contact law. `sources.json` records exact read-only owner heads and
file blobs. The canonical component registry matches this main's pinned files;
no registry repair was required or performed.

The existing `WornPose` convention is used: radial XY translation at most 5 mm,
each extrinsic XYZ angle at most 4 degrees, Z translation fixed at zero because
authority does not define it. These are pose constraints, **not local anatomical
residual tolerances**. Extra Z travel in the comparison is counterfactual only.

All sixteen morphology ranges are explicitly synthetic adversarial deltas.
They are not human percentiles, supported dimensions or a size chart. The smooth
warped mesh is reference geometry. Neither its interpenetration nor its gap
establishes pressure, comfort or compliance. Folded projected cells are rejected.

## Current executable campaign

`adversarial_fit_study.py` is the current campaign entry point. The earlier
`results/` files are recovered original-main evidence. Current-main results live
in `campaign_3ccd912/`; they are never substituted for the original snapshot.
The source ancestry was reconciled without a force push or subsystem edits;
`RECONCILIATION.json` records the exact merge and why the initial context-only
assessment was insufficient for the repository CI ancestry gate.

```sh
python -m masck_one.adversarial_fit_study generated/fit_study --capabilities
python -m masck_one.adversarial_fit_study analysis/fit_proof/campaign_3ccd912 --verify
python -m masck_one.adversarial_fit_study generated/replay.json --replay analysis/fit_proof/campaign_3ccd912/witnesses/false_surface.json
python -m masck_one.adversarial_fit_study generated/projected.json --replay analysis/fit_proof/campaign_3ccd912/witnesses/nominal.json --projected-screen
```

The current case set contains 50 morphologies, 108 adaptive bound evaluations,
18 eye-spacing bisection steps, 147 nominal starting poses and 36 coupled
morphology/pose starts. Nine capability configurations use the same 50 cases.
There are no human cases or measured physical results.

## Reproduce foundations

In the repository's qualified Python environment:

```sh
python -m pytest tests/test_adversarial_fit_proof.py tests/test_adversarial_fit_geometry.py
python -m masck_one.adversarial_fit_campaign generated/fit_proof/campaign
python -c "from pathlib import Path; from masck_one.adversarial_fit_geometry import export_screen; export_screen(Path('generated/fit_proof/nominal_cad'))"
```

SciPy, NumPy and Matplotlib are analysis runtime dependencies already available
through the CAD environment; runtime versions are recorded. The local nominal
B-rep receipt used CadQuery 2.7.0, not the repository's 2.8.0 qualification runtime.
Treat it as a runtime-specific conservative screen pending the exact CI runtime.
Do not suppress a geometry exception or use an invalid Boolean as zero volume.

## Proof limits and useful contradictions

The rigid registration minimizes the largest of five landmark residuals. It does
not average an unsuccessful mouth or nostril relationship into an eye success.
SLSQP produces a best attempted candidate; failure to converge is not a proof
that no registration exists. A separate invariant supplies a rigorous lower
bound for every rigid transform:

`max residual >= max_ij |distance(face_i,face_j) - distance(target_i,target_j)| / 2`.

The 1, 3 and 5 mm capacity bands are sensitivity inputs, **not qualified fit or
safety thresholds**. At a hypothetical 3 mm local capacity, eye-spacing delta
6.000045776 mm already has an invariant lower bound of 3.000022334 mm. The
candidate/nonpassing ray bracket is 0.000045777 mm. This is one explored ray,
not a global smallest facial perturbation or a population claim.

A width delta of 8 mm combined with eye-spacing delta 6 mm needs approximately
4.465116 mm minimax accommodation, although either change alone fits inside
that hypothetical 3 mm capacity. A coupled adversarial search produced a
9.053348 mm rigid-invariant lower bound. This cannot be repaired by rotating or
translating the same rigid landmark layout.

An asymmetry case is more deceptive: landmark residual is about 0.384511 mm,
yet the posed synthetic surface spans about 9.974751 mm in Z relative to the
planar reference. A low landmark error must not certify seal or contact fit.

Two labeled eye datums have rank 5 in unconstrained 6DOF rigid placement. A
rotation about their joining line remains unobserved. A third noncollinear
relationship removes that geometric null mode. This is a requirement on a future
alignment strategy, not a claim that the current wearable has those datums or
that adding a sensor would solve retention.

## Capture basin and adaptability

The 147 X/Y, RX/RY and Z/RZ starts are numerical seed diagnostics. Every mechanical
capture state remains UNKNOWN: no source-bound contact trajectory, force law,
friction envelope or support-transfer law exists from which to derive attraction,
trapping or a continuous protected-clear path. There are zero *proven* recoverable
states, which does not mean that zero states would physically recover.

The plots explicitly say this. A successful endpoint optimizer is never labeled
passive self-alignment, and initial Z is not smuggled into an existing adjustment.

The capability study compares the current rigid reference, an abstract single
global Z variable, and two proportional reference sizes. It searches pairs from
the explicit scale stencil 0.95/1.00/1.05. Complexity is reported by extra DOFs,
size inventory, user adjustment and subsystem coupling, without an arbitrary
combined score. These reference sizes do not modify protected geometry or create
manufactured sizes. Counts are conditional on the unqualified capacity bands.
No minimum sufficient production adaptability can be selected until local
travel, protected clearance and region-access evidence exist together.

## Owner dependencies and next experiment

- Exterior #70: provide the selected current shell/face registration and accepted
  protected-domain receipt. The released shell's conservative full-footprint
  intersection is recorded separately; it is not silently substituted for #70.
- Frame #117 and retention #141: registered contact locations, allowed adjustment
  and release paths. Force capacity and seating stability need physical evidence.
- Treatment #135: usable current geometry and a contact/reach map. Its unchanged
  owner verification failure is not repaired or repeatedly rerun here.
- Thermal #143: retain accepted digital evidence; provide registered plate
  contact and local accommodation data. A green thermal CI does not prove fit.
- CS015/018: required cells must be mapped to a measured surface and all stationary
  occluders. The exported source-cell inventory remains UNKNOWN for access.

First experiment: an **unpowered, off-face adjustable headform registration
study**, with independent pose metrology and replaceable inert contact references.
Compare the nominal and recorded asymmetry/spacing cases, measure support/seal
travel and false seating, and vary starting pose. Establish measurement
repeatability and contact constraints before testing acquisition. This package
specifies no human trial, cosmetic treatment or human-use acceptance threshold.

## Current decision and strongest findings

The false-seat search supersedes the earlier asymmetry example as the strongest
off-landmark counterexample: a synthetic +12 mm chin perturbation leaves a
0.011256 mm maximum five-landmark residual but 11.963195 mm maximum departure
from the planar surface. A separate sparse-eye solve aligns both eye points
within numerical precision while a +10 mm mouth-position perturbation remains
10 mm wrong. Neither is claimed to be an actual seated wearable state.

With authority-fixed Z and bounded rigid pose, the sparse-eye multistarts did
not reveal distinct near-equal terminal minima. The unconstrained two-eye datum
rank deficiency remains a separate analytic warning. Missing contact mechanics
prevents any physical uniqueness, attraction or trapping conclusion.

| Abstract capability | Candidates inside assumed 1 / 3 / 5 mm landmark capacity |
|---|---|
| Current reference | 16 / 35 / 48 |
| Global Z up to 10 mm | 21 / 37 / 48 |
| Expanded XY radius to 8 mm | 16 / 35 / 48 |
| Expanded XYZ angles to 6 degrees | 16 / 36 / 48 |
| Bilateral normal travel, 5 mm per side | 20 / 36 / 48 |
| Five independent normal intervals, 5 mm | 24 / 39 / 48 |
| Two reference sizes, 1.00 and 1.05 | 18 / 41 / 49 |
| Three reference sizes, 0.95 / 1.00 / 1.05 | 18 / 43 / 50 |
| Two sizes plus five local normal intervals | 27 / 43 / 49 |

These are optimistic landmark-interface relaxations, not qualified fit fractions.
Expanded XY or rotation ranges are counterfactual authority changes, not new DOFs
in the current rigid-body pose model. Five floating targets are not a proved
whole-face mechanism. Cost counts are explicit scenarios; required donning
precision, force paths, actual user effort and material compliance remain unknown.
The frontier is partial-information and capacity-dependent. No production
adaptability change is justified yet. Larger XY travel gives no benefit here;
normal travel cannot repair in-plane aperture-spacing incompatibility.

All three sampled conservative projected-domain screens intersect the released
shell. The nominal mouth common is 2927.805477 mm3; the two eye commons are about
2235.085 mm3 each. These reference prisms preserve full authority footprints
through the tested shell depth. They do not establish actual anatomical collision
and are not results for unreleased exterior #70. Required-cell access remains
UNKNOWN, even if a geometric landmark candidate exists.

The single next experiment is specified in [NEXT_EXPERIMENT.md](NEXT_EXPERIMENT.md).
Read the current campaign manifest and test receipts before reusing results.
A green tooling test is not a green fit decision.
