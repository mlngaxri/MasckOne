# Iteration 8 acceptance record

Iteration 8 is mergeable only if the exact pull-request head satisfies all of the following:

1. Authority schema/semantic validation passes.
2. Repository preflight reports Phase 1 / Iteration 8 and `WORN_POSE_CONTRACT = PASS`.
3. The default deterministic regression contains exactly 459 unique poses.
4. Maximum sampled radial translation is 5.0 mm.
5. Maximum sampled absolute roll/pitch/yaw is 4.0°.
6. Independent translational Z remains exactly 0.0 mm and is explicitly classified as not defined by current authority.
7. The regression set contains an exact identity pose.
8. The regression manifest SHA-256 is deterministic across repeated generation.
9. All 459 poses validate against authority limits.
10. All five protected zones can be transformed through the complete regression set without non-finite geometry, producing 2,295 posed-zone bounds.
11. Over-limit radial translation and over-limit per-axis rotation are rejected.
12. Existing authority, spatial, facial-reference, reference-surface, neutral-surface and protected-volume tests remain green.
13. Existing software-verifiable CAD assertions remain green.
14. Dynamic eye, mouth and airway 3D signed-distance evidence gates remain BLOCKED rather than being promoted by the planar regression model.
15. Deterministic CAD smoke generation succeeds.

No merge is permitted solely because code compiles; the exact PR head must pass the repository CI chain.
