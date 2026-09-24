# Off-face bench record contract, revision 2

This is an evidence-ingestion contract for inert, unpowered, off-face equipment.
It establishes no human-fit, skincare, thermal, optical or production result.
The supplied record and source-context templates contain no measurements,
qualified coupons, accepted thresholds or run attestations.

## Independent article context

The fourth input to `fit_metrology_records` is now a versioned source context.
It binds the exact release commit, rig revision, fixture revision, surface witness,
test mode, source hashes and complete coupon identity map. The analyzer compares
every field against the run. A hash map alone is insufficient. An acquisition
record requires a nonempty, correctly formed expected coupon map.

The context must come from the accepted article configuration, independently of
the record being evaluated. Copying a record's declarations into a second file
does not qualify them. The analyzer checks agreement and syntax; establishing the
physical article's identity remains the laboratory's evidence responsibility.

## Measured-run attestation

For `BENCH_MEASURED`, the independent qualification registry must contain a
qualified `BENCH_RUN` receipt with evidence class `BENCH`. Its SHA-256 must equal
`run_payload_hash(record, source_context)`. That canonical payload contains every
record field except the self-referencing `run_receipt`, plus the entire expected
source context. Changing the run, mode, article, observation, uncertainty,
criterion receipt or artifact identity invalidates the attestation.

The registry is the external trust boundary. The analyzer neither creates nor
qualifies registry entries. A matching hash proves content binding, not that a
measurement was performed. Synthetic test registries remain software fixtures.

Calibration, processing-method and criteria receipts remain independently
required. The full-field scan must also be hashed from its actual bytes. The CLI
only reads artifacts within the record directory. A run attestation cannot
replace that file check or authorize a path outside that directory.

A synthetic record always has `physical_result=null`. A measured record with
missing or unqualified evidence also has `physical_result=null`. An accepted
measured classification applies only to its qualified off-face bench criterion.

## Execution and migration

In the repository environment:

```sh
python -m masck_one.fit_metrology_records record.json criteria.json registry.json source_context.json
```

Record revision 1 and its prior schema/template remain in `history/` for audit.
They are not accepted as revision 2 evidence. Migration requires independently
reconstructing the article context and obtaining an actual run-specific evidence
receipt; changing the version string is insufficient.

Guard contact must be an observed JSON boolean. Text such as `"false"`, numeric
zero, malformed SHA-256 values and a prepopulated physical verdict are rejected.
No acceptance limit, geometry tolerance, measured uncertainty or protected domain
was relaxed by this revision.
