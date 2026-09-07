# Masck One production closure, 7 September 2026

## Disposition

Not ready for production or human-use release. This change repairs export integrity;
it does not constitute final aesthetic, functional or manufacturing acceptance.

Inspected released main: `b3be4c2483f45b2b8dfff6f0c3d9810c2b8511dc`.
Machine authority: `2026-08-30-R1`, Git blob
`2608dda483b995539de422290371c219668a1527`.

## Completed code repairs

1. Preserve the existing baseline mechanical-test repair from PR #129, exact
   commit `0021614f4af74a3a376abd3a3b430e45aba7b41e`. It retains the guard/yoke
   collision and unresolved integrated installation and whole-head removal.
2. Exclude all seven package envelopes from the development material compound.
   Preserve their individual STEP files and label every component's maturity,
   role, volume semantics and assembly participation.
3. Validate component B-reps, engineering assertions, DFM and source bindings
   before publishing. Reject empty, failed or unknown check results.
4. Stage complete exports before replacing the prior package. Publish a manifest
   of file hashes last; a partial or altered package fails verification.
5. Record production readiness separately from software PASS. The current exporter
   rejects `--production` before generating or writing any geometry.

The shell and local nasal membrane remain development geometry. The membrane is
not final conforming anatomy. No component volume is used as a mass estimate or
as usable fluid capacity.

## Material blockers

| Area | Observed condition | Required closure |
| --- | --- | --- |
| Exterior aesthetics and geometry | PR #70 contains the established smooth five-station form, neutral lower face, hidden eye backing and compact rear cover. Its exact head `da14a860e69c48191fc8e8204d895b2b9dd5f469` fails the solid-validity check after the first eye fillet. | Repair the actual B-rep failure, retain protected openings and wall requirements, then inspect regenerated STEP and front/side/rear/section views. |
| Structural frame and actuation | Released frame is a topology contract. Candidate frame/carrier parts do not close all positive cross-system joins, stops and service paths. | Integrated frame, mounts, reaction path, fasteners, stops, tolerances and installation/removal geometry. |
| Retention and service | The mechanical graph preserves a candidate guard/yoke reference overlap of `39.840676 mm3`; integrated factory paths and whole-head removal are unresolved. | A collision-free assembly sequence and service trajectories, followed by physical release validation. |
| Fluid system | Released mixed-waste centerlines exist. Reservoir, pumps, ports, seals and cartridge are not a complete manufacturable fluid assembly. | Selected components, wall/cavity geometry, seal interfaces, route sections, joining processes and validated flow/recovery/leakage. |
| Power and rear enclosure | Rear visual skin does not establish battery/PCB nesting, retention, connection or extraction. | Complete dry-side package, wiring, ingress separation, heat path, power/runtime and service closure. |
| CLEAN, WARM and optional COOL | PR #110 preserves CLEAN-first intent and hardware reservations. Final control count/mapping and WARM hardware/control are unresolved; COOL is optional and local-only. | Explicit interaction decision, selected switch/seal/thermal hardware and verified electrical, thermal and wet-use behavior. |
| Facial interface and airway | Released assertions contain ten evidence blockers including dynamic eye/airway/mouth geometry, airflow, pressure, strain and efficacy. | Registered anatomy and justified material/analysis/test evidence tied to the final assembly. |
| Manufacturing release | Complete supplier BOM, selected materials, production drawings, tolerance stacks and process qualification are absent. | Reviewed manufacturing package and physical verification against the same CAD revision. |

Candidate metadata is evidence of the current development state, not proof of
physical performance. No open candidate was promoted into released product material.

## Verification basis

The existing PR #129 run [34074898394](https://github.com/mlngaxri/MasckOne/actions/runs/34074898394)
passed 757 tests in 25:17 and completed CAD smoke. Its logs include the generated
report and source provenance. This supports only that unchanged prerequisite.

The exterior run [34019895497](https://github.com/mlngaxri/MasckOne/actions/runs/34019895497)
ended with 18 failed, 779 passed and seven errors. The geometry failures report an
invalid solid after protected eye 1; three other failures are the inherited
mechanical tests repaired by #129. CAD smoke was skipped on that exterior head.

The new export changes require their own complete CI run, including the added
STEP round-trip and package-integrity regressions. Earlier green runs are not
evidence for this changed source. Independent review remains required before merge.
