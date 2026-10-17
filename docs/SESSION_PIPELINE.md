# Prepared-session host integration

`session_pipeline.py` connects the existing product, dock, resource, readiness,
offline journal and completion contracts. It is executable host software and
does not dispatch commands to a wearable. Every result retains
`hardware_execution_authorized: false` and `physical_routine_complete: false`.

## Input and preparation

`prepare_session(authority, session_id, source, now_s=..., network_reachable=...)`
accepts declared records using the existing contracts:

| Source field | Existing contract |
| --- | --- |
| `request` | Exact plan, execution binding and dose windows for CS-016 |
| `demands`, `reservoirs` | Dock dose demands and physical slot/source records |
| `products`, `product_evidence`, `product_context` | Product lifecycle inputs |
| `resource_scenario`, `electrical_envelope` | Whole-session planning inventory and exact stage power/time bounds |
| `current` | Declared wear, service, resource, fault, epoch and local observations |
| `preparation` | Service receipt reference and preparation/observation expiry bounds |
| `manifest`, `cache` | Existing offline resident data contract |

The pipeline derives products and doses instead of trusting cached rows. It
replaces independently requested water, waste, energy and peak-power demands
with conservative calculated requirements. Unknown upper bounds remain unknown.
The current authority content, plan, product identities, source slots and
prepared-dose snapshots must agree. Reported usable water cannot exceed the
declared carried charge or reservoir envelope; battery availability must agree
with the scenario's declared usable-energy bound.

Consumable consistency and whole-product closure are separate. The real
canonical ledger currently has unresolved hardware masses and positions, so an
otherwise well-formed session remains blocked. Tests that exercise a positive
host sequence use an explicitly isolated synthetic ledger. No production option
turns that test substitution on.

## Ordered progress and storage

`record_session_intent` recomputes producers and readiness before recording the
next stage. `record_session_report` records only the corresponding ordered
software report. Changed source data, expired observations or uncertain progress
require service. The adapter currently treats a prepared source snapshot as
fixed; a future hardware integration needs trusted, progress-aware consumption
observations and reconciliation rather than silently changing that snapshot.

`OfflineJournalStore` supplies SQLite WAL transactions, full synchronisation,
immutable session bindings and expected-revision compare-and-swap:

```python
with OfflineJournalStore(database_path) as store:
    store.create(context["journal"])
    candidate = record_session_intent(
        authority, context, source, stage_id,
        now_s=now_s, network_reachable=False,
    )
    store.save(candidate["journal"],
               expected_revision=context["journal"]["revision"])
    context = candidate  # Adopt the intent only after successful commit.
```

`load(session_id)` is a restart boundary. An outstanding intent becomes a
durably stored `SERVICE_REQUIRED` state before return; it cannot be replayed or
completed by a late report. `restore_pipeline` attaches that journal to its
original prepared context and requires a fresh readiness check. The caller must
retain the prepared context and resident configuration separately; this store
persists journals, not the complete application configuration. A whole-database
rollback or malicious writer is not authenticated by the local restore cursor.

## Completion boundary

`assess_session_completion` requires a finished software report sequence and
separately supplied observations bound to the session ID, source snapshot and
preparation receipt. It delegates regional, release and product-evidence checks
to the strict existing completion consumer. Metrology outputs and stage reports
are never converted into accepted bench evidence. An admissible declared record
still does not establish actual execution, human-use suitability or SPF.

Run the integration boundary tests with:

```bash
python -m pytest tests/test_session_pipeline.py tests/test_session_resource_binding.py tests/test_offline_journal_store.py tests/test_session_integration.py tests/test_session_completion_boundary.py
```
