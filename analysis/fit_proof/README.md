# Adversarial fit proof

**Decision: D, DIGITAL INDETERMINATE.** This isolated analysis does not change any
production part, authority, Core Sketch, owner binding, resource ledger or CI.
PR #157's CS018/bench work remains separate and preserved. PR #158 owns this proof.

## What is actually available

Main `17f7d02c6178af8d33e4dfefb5043b497684ddb3` supplies a planar reference mesh,
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

## Reproduce

In the repository's qualified Python environment:

```sh
python -m pytest tests/test_adversarial_fit_proof.py tests/test_adversarial_fit_geometry.py
python -m masck_one.adversarial_fit_campaign generated/fit_proof/campaign
python -m masck_one.adversarial_fit_campaign generated/fit_proof/replay.json --replay analysis/fit_proof/results/smallest_conditional_witness.json
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
