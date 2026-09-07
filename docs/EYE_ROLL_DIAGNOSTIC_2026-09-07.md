# Exterior eye-roll investigation, 7 September 2026

Source candidate: PR #70, commit `da14a860e69c48191fc8e8204d895b2b9dd5f469`.
Disposition: unresolved. None of these experiments is production geometry.

The existing candidate fails solid validity after the first 3.0 mm eye fillet.
Three bounded experiments preserved the authority radius, all protected openings,
wall tests and the 2500 mm3 added-volume ceiling.

| Experiment | Observed result | Acceptance |
| --- | --- | --- |
| Sequential fillets with documented kernel repair | First eye becomes one valid solid; the second operation reports no suitable fillet edges. | Rejected |
| Paired fillets with kernel repair, 5.5 mm support band | Produces one valid solid, but the final construction fails the existing added-volume limit. | Rejected |
| Paired fillets, 5.0 mm hidden support band | Final solid is valid, its outer bounds are unchanged, and added volume is 2244.091722441355 mm3. The eye-roll regression finds only two matching edges where it requires at least three. | Rejected pending geometric feature verification |

The last candidate's baseline volume is 54995.54428985515 mm3 and final volume is
57239.636012296505 mm3. These are geometric volumes, not mass or usable capacity.
The test run stops at the first failed eye-roll regression; the remaining targeted
tests were not accepted or presumed to pass.

A valid solid is insufficient to establish the specified inner roll. The next
construction must retain the real eye treatment and pass protected-region,
wall, opening, volume, STEP and visual checks. Reducing or deleting the failing
expectation without stronger geometric evidence is not a repair.

Evidence:

- [Sequential investigation](https://github.com/mlngaxri/MasckOne/actions/runs/34084814737)
- [Paired investigation](https://github.com/mlngaxri/MasckOne/actions/runs/34084997529)
- [Smaller support investigation](https://github.com/mlngaxri/MasckOne/actions/runs/34085228389)
- [CadQuery shape repair API](https://cadquery.readthedocs.io/en/latest/classreference.html#cadquery.Shape.fix)

The source implementation of the exterior is unchanged. The diagnostic script
applies temporary in-process substitutions and is not an approved CAD producer.
