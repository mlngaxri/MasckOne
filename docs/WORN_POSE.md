# Masck One worn-pose and misregistration contract

## Purpose

Iteration 8 establishes one deterministic software representation of how the facial reference may be misregistered relative to the nominal Masck One device frame. The objective is to make every later hard-envelope, clearance, coverage and fit regression consume the same pose semantics.

This module is an engineering regression framework. It is **not** a measured donning-distribution model and it is not human-fit evidence.

## Authority limits

The current machine authority defines:

- maximum planar/radial misregistration: **5.0 mm**;
- maximum rotation: **4.0° about each canonical axis**.

The current authority does not define an independent Z-translation allowance. Iteration 8 therefore fixes translational Z to exactly `0.0 mm` and records the policy as:

`NOT_DEFINED_BY_CURRENT_AUTHORITY_FIXED_ZERO`

This is deliberate. An unsupported Z allowance must not be invented merely to make the regression space look six-dimensional.

## Pose definition

`WornPose` represents anatomy relative to the nominal device frame using:

- `translation_x_mm`
- `translation_y_mm`
- `roll_x_deg`
- `pitch_y_deg`
- `yaw_z_deg`

All axes and signs inherit `MASCK_ONE_GLOBAL`:

- +X = wearer's right
- +Y = superior
- +Z = anterior

Rotation uses the repository-wide fixed/global extrinsic XYZ convention implemented by `RigidTransform.from_extrinsic_xyz`.

## Hard-envelope deterministic regression set

`generate_hard_envelope_regression_set(...)` creates a repeatable boundary/interior screen.

The default set contains:

- one zero-translation state;
- 16 equally spaced directions on the full 5.0 mm radial translation boundary;
- three values for each rotational degree of freedom: `-4°`, `0°`, `+4°`.

Therefore:

`(1 + 16) × 3³ = 17 × 27 = 459 poses`

The ordering is deterministic and the complete set is SHA-256 signed at the manifest level so accidental ordering/value drift is detectable.

## What the 459 states mean

The 459-state set is deliberately labelled:

`DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION`

It is useful for:

- regression testing after geometry changes;
- ensuring boundary conditions are represented;
- transforming protected-zone samples consistently;
- catching sign/order mistakes;
- deterministic comparisons between code revisions.

It is not:

- a continuous proof over every possible pose;
- a Monte Carlo fit model;
- a probability statement;
- a substitute for measured donning data;
- a substitute for representative headforms or human testing.

## Protected-zone transforms

Iteration 8 can sample the neutral boundary of each planar protected zone and transform it through any accepted `WornPose`.

For the five current protected targets and 459 regression poses, the default regression therefore evaluates **2,295 posed zone bounds** before later geometric checks are added.

The current protected zones remain Z-unbounded because Iteration 7 deliberately refused to invent anatomical depth. Boundary samples use `Z=0` only as a mathematical transform reference plane. Rotation may produce nonzero Z coordinates even though translational Z remains zero.

## Failure rules

The software rejects:

- non-finite pose values;
- radial XY translation exceeding 5.0 mm;
- any roll, pitch or yaw magnitude exceeding 4.0°;
- duplicate deterministic pose states;
- regression direction counts below four;
- non-finite boundary-reference Z values.

The radial constraint is evaluated as `sqrt(x²+y²)`, not independently per axis. A pose such as `(4 mm, 4 mm)` therefore correctly fails even though neither coordinate alone exceeds 5 mm.

## Dynamic anatomical safety status

Iteration 8 does **not** convert the eye, airway or mouth signed-distance validation gates to PASS.

Those remain blocked because the project still lacks registered, evidence-eligible dynamic 3D anatomical surfaces for:

- eye/expression states;
- mouth/jaw/speech states;
- deformable airway/nasal states.

The worn-pose engine is the transform infrastructure those future surfaces will use once they exist.

## Later Monte Carlo model

The controlling engineering authority also describes a provisional stochastic donning-analysis concept. That later analysis must remain separate from this deterministic screen and must use measured/justified distributions before probability results are treated as evidence.

No probability of fit or safety is inferred from the 459 deterministic states.

## Change control

Changing any of the following is a system-level change requiring regression review:

- radial misregistration limit;
- rotational limit;
- Z-translation policy;
- coordinate convention;
- Euler convention;
- radial boundary sampling strategy;
- regression-state ordering;
- evidence-status classification.

Downstream protected-volume, coverage, interface, fluid and structural checks must consume this module rather than recreating pose rules independently.
