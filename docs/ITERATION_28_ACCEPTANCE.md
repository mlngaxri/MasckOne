# Iteration 28 acceptance

## Scope

Complete fresh/waste routing accounting contract for bend radius, dead volume and service clearance.

## Controlled result

Iteration 28 introduces a fail-closed route evidence model. A route may bind controlled centerline length and tube inner diameter to compute geometric dead volume. Bend-radius and service-clearance checks only produce `DIGITAL_PASS` or `DIGITAL_FAIL` when both the measured/generated geometry value and its controlled requirement are present. Missing inputs remain `VALIDATION_GATED`.

The routing closure is provenance-bound to the exact Iteration 27 waste-cartridge architecture SHA and exposes a deterministic architecture digest for downstream consumers. Route identities are unique and source/sink interface identities are explicit.

## Evidence firewall

No tubing bend radius, tube diameter, route length, service clearance, hydraulic performance, priming performance, purge performance, pressure loss, mixed-phase transport behavior, kink resistance, fatigue life, assembly success or service success is invented by this module. Numeric inputs reject booleans, non-finite values and non-positive dimensions.

A calculated dead volume is geometry accounting only. It is not measured retained volume, prime volume, purge volume or hydraulic evidence.

## Remaining closure

Iteration 28 is not promoted complete by this first contract alone. Integration must bind the actual fresh and waste route manifests and generated route geometry, then run exact-head CI and hostile provenance/change-propagation review. Supplier minimum bend-radius data and physical service evidence remain evidence-gated where unavailable.
