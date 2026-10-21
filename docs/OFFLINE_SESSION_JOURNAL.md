# CS-016 offline session journal and producer consistency

Engineering branch: `engineering/lane4-offline-runtime-20261014`, based on released main `faae3cec` (14 October 2026). Lane 4 owns the new host-only journal and routine/product producers. Existing hardware controller and HMI owner branches are untouched.

## Problem and hypothesis

The product lifecycle producer previously reported a bound row as `VALIDATED` and `RESOLVED` even when the catalogue SKU or market contradicted that binding. Its outer blockers warned of the mismatch, but a downstream consumer reading only the rows could accept the wrong product. Routine resolution and offline manifest generation also discarded definition blockers, allowing a PM SPF definition to become an apparently complete session. Offline cache equality alone did not establish that both cache and manifest belonged to the current hardware/profile/authority context.

The change makes those contradictions fail closed and provides a deterministic versioned software journal for ordered progress and interruption. Acceptance requires that stale preparation, product contradiction, absent local information, mismatched revisions, unexpected states, stage skip/replay and uncertain delivery cannot advance a session. Network availability must not alter the result.

## Implemented behavior

- `session_product_records` emits `UNSUPPORTED`/`UNKNOWN` and no promoter for a bound SKU, market or identity-version mismatch. The existing readiness consumer rejects the row even if the producer's outer blockers are ignored.
- Routine-definition blockers propagate into session resolution and offline assessment. An invalid definition cannot claim completion of its scheduled routine.
- The offline manifest snapshots resident records, preserves definition blockers, checks its content digest and requires the complete canonical residency list.
- `offline_session.plan_session` consumes the existing request, preparation receipt and current-observation schemas through `assess_readiness`. Placement/start eligibility remains an explicit requirement.
- `record_intent` rechecks receipt expiry, actual observations, local data and applicability before each simulated intent. A changed request, preparation receipt or manifest requires a new prepared session.
- `record_stage_report` permits only the outstanding stage, requires a unique report id and records a software report rather than measured delivery.
- A restored outstanding intent becomes uncertain delivery and latches `SERVICE_REQUIRED`. Interruption and clock rollback preserve progress and require service/re-preparation. No replay or resume API exists. A separately trusted session/revision restore cursor can reject intact stale or cross-session serialized records.
- Even a full report sequence remains `physical_routine_complete: false` and `hardware_execution_authorized: false`. Physical completion remains the existing coverage/contact/evidence predicate's responsibility.

## Offline applicability envelope

The generic `routine_schedule` manifest remains usable independently. The new journal requires these additional applicability fields inside its resident records, matching the execution request:

| Resident key | Journal-required context |
| --- | --- |
| `routine_revision`, `profile_revision`, `hardware_revision` | Matching text value, or object with matching `revision` text |
| `authority_digest` | Matching text value, or object with matching `digest` text |
| `stage_parameters` | Object with matching `plan_digest` |
| `dose_windows` | Object with `dose_requirements_digest = digest(request['dose_requirements'])` |
| `protected_region_map` | Object with matching `plan_digest` |
| `fault_response_table` | Object with matching `hardware_revision` and `authority_digest` |

The manifest's routine id, routine revision and schedule context must also match the request binding. Equality between two stale copies is insufficient. These fields identify applicability; they do not validate the values or physical limits inside a profile. No safety limit is added or changed.

## Integration and persistence

Lane 2 remains the producer of preparation/transfer receipts and dose rows. The journal consumes the existing readiness contract without editing dock preparation, authority, shared contracts, firmware or HMI. Additional receipt fields are preserved by whole-record digests. Lane 5's resource work remains separate; current resource availability is checked through the existing readiness gate.

This is pure host logic, not a hardware runner, embedded scheduler, app/backend connection or filesystem transaction manager. All records and tests are synthetic or declared inputs. A future separately reviewed adapter must atomically persist each returned intent before controller dispatch, enforce a single writer and monotonic journal revision, and provide a trusted time/observation source. A digest detects accidental mutation; it does not authenticate a writer. Replay checks require a separately trusted restore cursor; without that cursor an old, otherwise intact journal cannot be identified as stale. There is no claim that a software report proves a fluid dose, film or sunscreen protection. Unknown remote recalls remain an explicit offline-update policy dependency; received local restrictions cannot pass readiness.

## Reproducible verification

Use controlled Python 3.13 and repository dependencies:

```bash
python -m pytest tests/test_offline_session.py tests/test_routine_product_intelligence.py tests/test_core_sketch_contracts.py tests/test_routine_completion.py
PYTHONPATH=src python -m masck_one.preflight
```

The initial environment lacked pytest; after dependency installation the existing 203 targeted tests passed. The final targeted suite passes with 259 tests including the new adversarial regressions. The broader contracts, program-position, convergence and authority suite passed 324 tests before the final two malformed-manifest regressions were added. Repository preflight exits successfully with all checks passing. This verifies software behavior and source consistency, not hardware performance or a closed G3 physical gate.

## Remaining work

The next executable integration task is a durable single-writer adapter with compare-and-swap/revision checks and crash injection, then an explicit preparation-transfer receipt adapter when Lane 2's measured handoff contract is reviewed. Hardware routing remains blocked on the existing control owner's integration and validated observation sources. Product preservation, dose metrology, facial layering, non-wiping removal and SPF performance require separately recorded physical evidence. No bench or human testing was performed.
